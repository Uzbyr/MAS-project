# =============================================================================
# Group: Yoan Di Cosmo
# Project: Self-organization of robots in a hostile environment (MAS 2025-2026)
# Date of creation: 2026-04-20
# Member(s): Yoan Di Cosmo
# File: agents.py - Robot agents (Green, Yellow, Red) with percepts/deliberate/do
# =============================================================================
#
# Each robot implements the standard loop:
#       update(self.knowledge, percepts)
#       action = deliberate(self.knowledge)
#       percepts = self.model.do(self, action)
#
# `deliberate` only reads from its `knowledge` argument - no external state.
# =============================================================================

import random

import mesa

from objects import GREEN, YELLOW, RED


# ---------- Action constants --------------------------------------------------
# Actions are represented as small dictionaries. This keeps them self-describing
# and easy to extend later (e.g. with a target, a message, ...).
ACT_MOVE = "MOVE"
ACT_PICKUP = "PICKUP"
ACT_TRANSFORM = "TRANSFORM"
ACT_DROP = "DROP"
ACT_WAIT = "WAIT"

# Direction vectors
DIR_N = (0, 1)
DIR_S = (0, -1)
DIR_E = (1, 0)
DIR_W = (-1, 0)


def _zone_of(level):
    """Map a radioactivity level to a zone id (1, 2 or 3)."""
    if level < 0.33:
        return 1
    if level < 0.66:
        return 2
    return 3


# ---------- Base Robot class --------------------------------------------------
class RobotAgent(mesa.Agent):
    """Common behavior for all robots. Concrete subclasses override the
    `deliberate` method and set the class attribute `ZONE_MAX` (furthest
    zone the robot is allowed to enter) and `COLLECT_COLOR` / `PRODUCE_COLOR`.
    """

    # The zone to which this robot is confined (inclusive). Override in subclasses.
    ZONE_MAX = 1
    # Waste color this robot collects to transform.
    COLLECT_COLOR = GREEN
    # Waste color produced after transformation (None for Red: no transform).
    PRODUCE_COLOR = YELLOW
    # Capacity: how many COLLECT_COLOR units before transforming.
    CAPACITY = 2

    def __init__(self, model):
        super().__init__(model)
        # Inventory: list of Waste instances carried by the robot.
        self.inventory = []
        # Beliefs / memory of the agent (the "knowledge" parameter of deliberate).
        self.knowledge = {
            "pos": None,                 # filled on first percepts
            "zone_max": self.ZONE_MAX,
            "collect_color": self.COLLECT_COLOR,
            "produce_color": self.PRODUCE_COLOR,
            "capacity": self.CAPACITY,
            "inventory_colors": [],      # colors only (deliberate doesn't touch Waste objs)
            "last_percepts": {},         # percepts from previous do()
            "last_action": None,
            "known_wastes": {},          # {pos: color} seen but not picked
            # The disposal zone is a fixed landmark of the mission, so robots
            # know its position a priori (same as knowing "where the secure
            # area is"). They still have to reach it themselves.
            "disposal_pos": getattr(model, "disposal_pos", None),
            "visited": set(),            # already-visited cells (for exploration)
            "grid_width": model.grid.width,
            "grid_height": model.grid.height,
            "messages": [],              # incoming messages (step 2)
            "idle_with_singleton": 0,    # counter: how many steps stuck with 1 waste
            "skip_pickup_until": {},     # {pos: step} avoid re-picking recent drops
            "step": 0,                   # local step counter
        }

    # ---------------------------------------------------------------- step loop
    def step(self):
        """Standard perceive -> update knowledge -> deliberate -> do loop."""
        percepts = self.model.percepts_of(self)
        self._update_knowledge(percepts)
        action = self.deliberate(self.knowledge)
        new_percepts = self.model.do(self, action)
        # Store for next step (some subclasses use it).
        self.knowledge["last_percepts"] = new_percepts
        self.knowledge["last_action"] = action

    # -------------------------------------------------- knowledge update helper
    def _update_knowledge(self, percepts):
        """Fold fresh percepts into the knowledge base. Called by `step`, not by
        `deliberate`. This keeps deliberate side-effect free."""
        self.knowledge["pos"] = percepts["self_pos"]
        inv_colors = [w.color for w in self.inventory]
        self.knowledge["inventory_colors"] = inv_colors
        self.knowledge["last_percepts"] = percepts
        self.knowledge["visited"].add(percepts["self_pos"])

        # Track how long we have been carrying a single COLLECT_COLOR waste
        # without making progress (used to break pairing deadlocks).
        if (inv_colors == [self.COLLECT_COLOR]
                and self.COLLECT_COLOR is not None
                and self.PRODUCE_COLOR is not None):
            self.knowledge["idle_with_singleton"] += 1
        else:
            self.knowledge["idle_with_singleton"] = 0

        # Register a drop cooldown if we just dropped a singleton here
        self.knowledge["step"] += 1
        last = self.knowledge.get("last_action") or {}
        last_pos = self.knowledge.get("last_pos_before_action")
        if last.get("type") == "DROP" and last_pos is not None:
            # Don't re-pick what we just dropped for a few steps
            self.knowledge["skip_pickup_until"][last_pos] = self.knowledge["step"] + 8
        # Purge expired cooldowns
        cur = self.knowledge["step"]
        self.knowledge["skip_pickup_until"] = {
            p: t for p, t in self.knowledge["skip_pickup_until"].items() if t > cur
        }
        # Remember where we were this step (so next step's cooldown update sees it)
        self.knowledge["last_pos_before_action"] = percepts["self_pos"]

        # Remember waste and disposal positions we see
        for pos, cell in percepts["neighbors"].items():
            wastes_here = [c for c in cell["contents"] if c == "waste_green"
                           or c == "waste_yellow" or c == "waste_red"]
            # Store the (last) waste color we saw at that position, if any
            color = None
            for tag in cell["contents"]:
                if tag.startswith("waste_"):
                    color = tag.split("_", 1)[1]
            if color is not None:
                self.knowledge["known_wastes"][pos] = color
            else:
                # No waste anymore at that cell
                self.knowledge["known_wastes"].pop(pos, None)
            if "disposal" in cell["contents"]:
                self.knowledge["disposal_pos"] = pos

        # Consume any messages delivered by the model this step. We do NOT
        # persist them beyond the current deliberation - the info they carry
        # has already been merged into known_wastes above via percepts-like
        # handling below. This prevents stale messages from misleading later.
        inbox = self.model.inbox_for(self)
        self.knowledge["messages"] = list(inbox)  # overwrite, don't accumulate
        # Fold message-reported wastes into known_wastes immediately
        for msg in inbox:
            mtype = msg.get("type")
            if mtype == "waste_at":
                self.knowledge["known_wastes"][msg["pos"]] = msg["color"]
            elif mtype == "waste_gone":
                # Peer picked up a waste - forget it
                self.knowledge["known_wastes"].pop(msg["pos"], None)
            elif mtype == "disposed":
                self.knowledge["known_wastes"].pop(msg["pos"], None)

    # ----------------------------------------------------- deliberate (virtual)
    def deliberate(self, knowledge):  # pragma: no cover - overridden
        raise NotImplementedError


# ---------- Shared deliberation helpers ---------------------------------------
# These are stand-alone functions so that `deliberate` stays pure: it receives
# `knowledge` and computes an action without touching any external state.

def _in_zone(pos, zone_max, grid_width):
    """True if cell `pos` is within a robot with `zone_max` allowance.

    Zones are horizontal thirds of the grid going west -> east.
    """
    x, _ = pos
    z_width = grid_width // 3
    z1_end = z_width
    z2_end = 2 * z_width
    if zone_max == 1:
        return x < z1_end
    if zone_max == 2:
        return x < z2_end
    return True


def _zone_east_frontier(zone_max, grid_width):
    """East-most x coordinate reachable by the robot (for drop-off)."""
    z_width = grid_width // 3
    if zone_max == 1:
        return z_width - 1
    if zone_max == 2:
        return 2 * z_width - 1
    return grid_width - 1


def _move_toward(pos, target, zone_max, grid_width, grid_height, visited=None):
    """Return one of DIR_N/S/E/W heading toward `target` while respecting the
    zone boundary. Falls back to a random legal direction when already aligned.
    """
    x, y = pos
    tx, ty = target
    candidates = []
    if tx > x:
        candidates.append(DIR_E)
    elif tx < x:
        candidates.append(DIR_W)
    if ty > y:
        candidates.append(DIR_N)
    elif ty < y:
        candidates.append(DIR_S)

    # Filter illegal (out of grid / out of zone) moves
    legal = []
    for dx, dy in candidates:
        nx, ny = x + dx, y + dy
        if not (0 <= nx < grid_width and 0 <= ny < grid_height):
            continue
        if not _in_zone((nx, ny), zone_max, grid_width):
            continue
        legal.append((dx, dy))

    if legal:
        return random.choice(legal)
    # No greedy move -> pick any legal direction
    return _random_legal_move(pos, zone_max, grid_width, grid_height, visited)


def _random_legal_move(pos, zone_max, grid_width, grid_height, visited=None):
    x, y = pos
    dirs = [DIR_N, DIR_S, DIR_E, DIR_W]
    random.shuffle(dirs)
    unvisited = []
    legal = []
    for dx, dy in dirs:
        nx, ny = x + dx, y + dy
        if not (0 <= nx < grid_width and 0 <= ny < grid_height):
            continue
        if not _in_zone((nx, ny), zone_max, grid_width):
            continue
        legal.append((dx, dy))
        if visited is not None and (nx, ny) not in visited:
            unvisited.append((dx, dy))
    if unvisited:
        return unvisited[0]
    if legal:
        return legal[0]
    return (0, 0)  # stuck


def _pick_nearest(pos, positions):
    if not positions:
        return None
    px, py = pos
    return min(positions, key=lambda p: abs(p[0] - px) + abs(p[1] - py))


# ---------- Concrete agent classes --------------------------------------------
class GreenAgent(RobotAgent):
    """Lives in z1, collects green waste, transforms 2 green -> 1 yellow,
    then carries the yellow waste east until it crosses into z2's border and
    drops it there for a YellowAgent to pick up.
    """

    ZONE_MAX = 1
    COLLECT_COLOR = GREEN
    PRODUCE_COLOR = YELLOW

    def deliberate(self, knowledge):
        return _deliberate_collector(knowledge)


class YellowAgent(RobotAgent):
    """Lives in z1+z2, collects yellow waste, transforms 2 yellow -> 1 red,
    then carries the red waste east to drop it on the z2/z3 border for a
    RedAgent to pick up.
    """

    ZONE_MAX = 2
    COLLECT_COLOR = YELLOW
    PRODUCE_COLOR = RED

    def deliberate(self, knowledge):
        return _deliberate_collector(knowledge)


class RedAgent(RobotAgent):
    """Lives anywhere. Picks up a single red waste and transports it to the
    disposal zone on the east edge.
    """

    ZONE_MAX = 3
    COLLECT_COLOR = RED
    PRODUCE_COLOR = None  # no transformation
    CAPACITY = 1          # only carries one red at a time

    def deliberate(self, knowledge):
        return _deliberate_red(knowledge)


# ---------- Deliberate functions (pure: only read `knowledge`) ----------------
def _deliberate_collector(knowledge):
    """Shared priority cascade for Green and Yellow agents.

    1. If we have CAPACITY of COLLECT_COLOR -> TRANSFORM.
    2. If we carry a PRODUCE_COLOR waste, head east and DROP at the frontier.
    3. If waste of our color is on our cell -> PICKUP.
    4. If we know of a waste of our color -> move toward it.
    5. Else, explore legal unvisited cells.
    """
    inv = knowledge["inventory_colors"]
    collect = knowledge["collect_color"]
    produce = knowledge["produce_color"]
    pos = knowledge["pos"]
    zmax = knowledge["zone_max"]
    gw, gh = knowledge["grid_width"], knowledge["grid_height"]
    frontier_x = _zone_east_frontier(zmax, gw)
    percepts = knowledge["last_percepts"]
    visited = knowledge["visited"]

    # 1. Transform if full
    if inv.count(collect) >= knowledge["capacity"]:
        return {"type": ACT_TRANSFORM}

    # 2. Carry produced waste east, drop at frontier
    if produce in inv:
        if pos[0] >= frontier_x:
            return {"type": ACT_DROP, "color": produce}
        return {"type": ACT_MOVE, "dir": DIR_E}

    # 3. Waste of our color on this cell? (skip if we just dropped here)
    here = percepts.get("self_cell", {}).get("contents", [])
    skip = knowledge.get("skip_pickup_until", {})
    if f"waste_{collect}" in here and pos not in skip:
        return {"type": ACT_PICKUP, "color": collect}

    # 4. Head toward a known waste of our color (from memory or messages)
    known = [p for p, c in knowledge["known_wastes"].items() if c == collect]
    # Also incorporate any messages pointing to our color
    for msg in knowledge["messages"]:
        if msg.get("type") == "waste_at" and msg.get("color") == collect:
            known.append(msg["pos"])
    target = _pick_nearest(pos, known)
    if target is not None:
        return {"type": ACT_MOVE,
                "dir": _move_toward(pos, target, zmax, gw, gh, visited)}

    # 4b. Deadlock break: we have a lone collect-color waste and we do not
    # know where to find another. Drop it back on the grid after waiting long
    # enough so other robots of our type may find it (also triggers a message
    # broadcast in step 2). Threshold kept small to stay reactive.
    if collect in inv and knowledge["idle_with_singleton"] >= 15:
        return {"type": ACT_DROP, "color": collect}

    # 5. Explore - prefer going east (most wastes accumulate there after
    #    transformations happen in z1 and get dropped at the frontier).
    return {"type": ACT_MOVE,
            "dir": _random_legal_move(pos, zmax, gw, gh, visited)}


def _deliberate_red(knowledge):
    """Priority cascade for RedAgent.

    1. If carrying red AND we know the disposal cell -> move there; at disposal -> DROP.
    2. If a red waste is on our cell -> PICKUP.
    3. If we know a red waste position -> move toward it.
    4. Else explore z3 preferentially (the last zone is where reds are dropped).
    """
    inv = knowledge["inventory_colors"]
    pos = knowledge["pos"]
    zmax = knowledge["zone_max"]
    gw, gh = knowledge["grid_width"], knowledge["grid_height"]
    percepts = knowledge["last_percepts"]
    visited = knowledge["visited"]
    disposal = knowledge["disposal_pos"]

    # 1. Carrying red
    if RED in inv:
        if disposal is not None:
            if pos == disposal:
                return {"type": ACT_DROP, "color": RED}
            return {"type": ACT_MOVE,
                    "dir": _move_toward(pos, disposal, zmax, gw, gh, visited)}
        # No known disposal -> move east to find it
        return {"type": ACT_MOVE, "dir": DIR_E}

    # 2. Red waste on this cell?
    here = percepts.get("self_cell", {}).get("contents", [])
    if "waste_red" in here:
        return {"type": ACT_PICKUP, "color": RED}

    # 3. Known red waste -> go get it
    known_reds = [p for p, c in knowledge["known_wastes"].items() if c == RED]
    for msg in knowledge["messages"]:
        if msg.get("type") == "waste_at" and msg.get("color") == RED:
            known_reds.append(msg["pos"])
    target = _pick_nearest(pos, known_reds)
    if target is not None:
        return {"type": ACT_MOVE,
                "dir": _move_toward(pos, target, zmax, gw, gh, visited)}

    # 4. Explore, biased east: red wastes are dropped on the z2/z3 border by
    #    yellow robots, so the east half of the grid is the productive area.
    if pos[0] < 2 * (gw // 3):
        return {"type": ACT_MOVE, "dir": DIR_E}
    return {"type": ACT_MOVE,
            "dir": _random_legal_move(pos, zmax, gw, gh, visited)}
