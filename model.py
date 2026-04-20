# =============================================================================
# Group: Yoan Di Cosmo
# Project: Self-organization of robots in a hostile environment (MAS 2025-2026)
# Date of creation: 2026-04-20
# Member(s): Yoan Di Cosmo
# File: model.py - RobotMission model: grid, zones, step, do(action)
# =============================================================================

import random

import mesa
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

from objects import Waste, Radioactivity, WasteDisposalZone, GREEN, YELLOW, RED
from agents import (
    RobotAgent, GreenAgent, YellowAgent, RedAgent,
    ACT_MOVE, ACT_PICKUP, ACT_TRANSFORM, ACT_DROP, ACT_WAIT,
)


class RobotMission(mesa.Model):
    """Main model. The grid is divided into three vertical zones (z1 west,
    z3 east). Green wastes spawn in z1; the disposal cell sits in z3.

    Parameters
    ----------
    width, height : int
        Grid dimensions. `width` should be divisible by 3 for clean zoning.
    n_green, n_yellow, n_red : int
        Number of robots of each type.
    n_wastes : int
        Initial count of green wastes spawned in z1.
    communication : bool
        If True, step-2 message board is active (robots broadcast waste drops
        and disposal discoveries). If False, robots only use their own memory.
    comm_range : int
        Manhattan range at which a message reaches a recipient (0 = global).
    seed : int | None
        Random seed for reproducibility.
    """

    def __init__(self, width=12, height=8,
                 n_green=3, n_yellow=2, n_red=2,
                 n_wastes=8, n_yellow_wastes=0, n_red_wastes=0,
                 communication=True, comm_range=0,
                 seed=None):
        super().__init__(seed=seed)
        assert width % 3 == 0, "width should be divisible by 3"
        self.width = width
        self.height = height
        self.grid = MultiGrid(width, height, torus=False)

        self.communication = communication
        self.comm_range = comm_range
        # Message board: list of messages {type, color, pos, sender_id, ttl}
        self.message_board = []
        # TTL (in steps) after which a message is deleted.
        self.message_ttl = 30

        self.zone_width = width // 3
        self.n_wastes_initial = n_wastes

        # --- Counters (exposed via DataCollector) --------------------------
        self.n_disposed = 0
        self.green_to_yellow_transforms = 0
        self.yellow_to_red_transforms = 0
        # Collection-time tracking: for each robot & collect-color, remember
        # the step when it picked up its first unit. On second pickup, the
        # interval is appended to _collection_intervals[color] and the entry
        # is cleared. A drop of a collect-color waste also clears.
        self._first_pick_step = {}                  # {(robot_id, color): step}
        self._collection_intervals = {GREEN: [], YELLOW: [], RED: []}

        # --- build environment ---
        self._place_radioactivity()
        self.disposal_pos = self._place_disposal()
        self._spawn_wastes(n_green=n_wastes, n_yellow=n_yellow_wastes,
                           n_red=n_red_wastes)
        self._spawn_robots(n_green, n_yellow, n_red)

        # --- data collection ---
        self.datacollector = DataCollector(
            model_reporters={
                # Global counts (legacy - used by existing plots)
                "green_wastes":    lambda m: m._count_waste(GREEN),
                "yellow_wastes":   lambda m: m._count_waste(YELLOW),
                "red_wastes":      lambda m: m._count_waste(RED),
                # On-grid vs carried split
                "green_on_grid":   lambda m: m._count_waste_on_grid(GREEN),
                "yellow_on_grid":  lambda m: m._count_waste_on_grid(YELLOW),
                "red_on_grid":     lambda m: m._count_waste_on_grid(RED),
                "green_carried":   lambda m: m._count_waste_carried(GREEN),
                "yellow_carried":  lambda m: m._count_waste_carried(YELLOW),
                "red_carried":     lambda m: m._count_waste_carried(RED),
                # Pipeline throughput
                "disposed":        lambda m: m.n_disposed,
                "g_to_y_transforms": lambda m: m.green_to_yellow_transforms,
                "y_to_r_transforms": lambda m: m.yellow_to_red_transforms,
                # Communication
                "messages_active": lambda m: len(m.message_board),
                # Exploration coverage per zone (union of every robot's visited set)
                "visited_z1":      lambda m: m._visited_ratio_for_zone(1),
                "visited_z2":      lambda m: m._visited_ratio_for_zone(2),
                "visited_z3":      lambda m: m._visited_ratio_for_zone(3),
                # Pairing efficiency - average steps between 1st and 2nd pickup
                "avg_green_collect_time":  lambda m: m._avg_interval(GREEN),
                "avg_yellow_collect_time": lambda m: m._avg_interval(YELLOW),
            }
        )
        self.running = True
        self.datacollector.collect(self)

    # -------------------------------------------------------------- environment
    def _zone_for_x(self, x):
        if x < self.zone_width:
            return 1
        if x < 2 * self.zone_width:
            return 2
        return 3

    def _random_level_for_zone(self, zone):
        if zone == 1:
            return random.uniform(0.0, 0.33)
        if zone == 2:
            return random.uniform(0.33, 0.66)
        return random.uniform(0.66, 1.0)

    def _place_radioactivity(self):
        """Place a Radioactivity marker on every cell so that a robot standing
        anywhere can perceive the zone from its cell contents."""
        for x in range(self.width):
            zone = self._zone_for_x(x)
            for y in range(self.height):
                level = self._random_level_for_zone(zone)
                rad = Radioactivity(self, zone=zone, level=level)
                self.grid.place_agent(rad, (x, y))

    def _place_disposal(self):
        """Place a single WasteDisposalZone marker somewhere on the east edge
        (x = width-1, y random). Returns its position."""
        y = random.randrange(self.height)
        pos = (self.width - 1, y)
        disposal = WasteDisposalZone(self)
        self.grid.place_agent(disposal, pos)
        return pos

    def _spawn_wastes(self, n_green=0, n_yellow=0, n_red=0):
        """Place wastes in their native zones:
        green in z1, yellow in z2, red in z3 (but NOT on the disposal cell).
        """
        for _ in range(n_green):
            x = random.randrange(0, self.zone_width)
            y = random.randrange(self.height)
            self.grid.place_agent(Waste(self, color=GREEN), (x, y))
        for _ in range(n_yellow):
            x = random.randrange(self.zone_width, 2 * self.zone_width)
            y = random.randrange(self.height)
            self.grid.place_agent(Waste(self, color=YELLOW), (x, y))
        for _ in range(n_red):
            # Keep red wastes off the disposal cell at init
            while True:
                x = random.randrange(2 * self.zone_width, self.width)
                y = random.randrange(self.height)
                if (x, y) != self.disposal_pos:
                    break
            self.grid.place_agent(Waste(self, color=RED), (x, y))

    def _spawn_robots(self, n_green, n_yellow, n_red):
        for _ in range(n_green):
            a = GreenAgent(self)
            x = random.randrange(0, self.zone_width)
            y = random.randrange(self.height)
            self.grid.place_agent(a, (x, y))
        for _ in range(n_yellow):
            a = YellowAgent(self)
            x = random.randrange(0, 2 * self.zone_width)
            y = random.randrange(self.height)
            self.grid.place_agent(a, (x, y))
        for _ in range(n_red):
            a = RedAgent(self)
            x = random.randrange(0, self.width)
            y = random.randrange(self.height)
            self.grid.place_agent(a, (x, y))

    # ----------------------------------------------------------------- percepts
    def _cell_contents(self, pos):
        """Return a list of string tags describing what is on `pos`."""
        tags = []
        for agent in self.grid.get_cell_list_contents([pos]):
            if isinstance(agent, Waste):
                tags.append(f"waste_{agent.color}")
            elif isinstance(agent, WasteDisposalZone):
                tags.append("disposal")
            elif isinstance(agent, Radioactivity):
                tags.append(f"radio_z{agent.zone}")
            elif isinstance(agent, RobotAgent):
                tags.append(f"robot_{agent.__class__.__name__}")
        return tags

    def percepts_of(self, agent):
        """Build the percepts dictionary for an agent. Includes the cell the
        agent stands on plus its Moore 8-neighborhood (diagonals included)."""
        x, y = agent.pos
        neighbors = {}
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    neighbors[(nx, ny)] = {"contents": self._cell_contents((nx, ny))}
        return {
            "self_pos": agent.pos,
            "self_cell": {"contents": self._cell_contents(agent.pos)},
            "neighbors": neighbors,
            "inventory": [w.color for w in agent.inventory],
        }

    # ------------------------------------------------------------ action engine
    def do(self, agent, action):
        """Execute (or reject) an action requested by `agent`. Returns fresh
        percepts (the same structure as `percepts_of`).
        """
        act_type = action.get("type", ACT_WAIT)

        if act_type == ACT_MOVE:
            self._try_move(agent, action.get("dir", (0, 0)))
        elif act_type == ACT_PICKUP:
            self._try_pickup(agent, action.get("color"))
        elif act_type == ACT_TRANSFORM:
            self._try_transform(agent)
        elif act_type == ACT_DROP:
            self._try_drop(agent, action.get("color"))
        # ACT_WAIT: do nothing.
        return self.percepts_of(agent)

    # ---------- feasibility checks + effects
    def _try_move(self, agent, direction):
        dx, dy = direction
        if dx == 0 and dy == 0:
            return False
        x, y = agent.pos
        nx, ny = x + dx, y + dy
        if not (0 <= nx < self.width and 0 <= ny < self.height):
            return False
        # Zone constraint: we infer the zone from the destination cell's radioactivity.
        dest_zone = self._zone_for_x(nx)
        if dest_zone > agent.ZONE_MAX:
            return False
        self.grid.move_agent(agent, (nx, ny))
        return True

    def _try_pickup(self, agent, color):
        # Capacity: agents can carry up to 2 units of their collected color, or
        # 1 produced unit on top, or 1 red for a RedAgent.
        if color is None:
            return False
        # Find a matching waste on the cell
        for obj in list(self.grid.get_cell_list_contents([agent.pos])):
            if isinstance(obj, Waste) and obj.color == color and obj.carried_by is None:
                # Capacity rule per agent type
                if not self._can_pickup(agent, color):
                    return False
                # Inventory count of this color BEFORE pickup
                prev_same_color = sum(1 for w in agent.inventory
                                      if w.color == color)
                self.grid.remove_agent(obj)
                obj.carried_by = agent
                agent.inventory.append(obj)
                # --- collection-time tracking (collect_color only) ---------
                if color == agent.COLLECT_COLOR and agent.PRODUCE_COLOR is not None:
                    key = (agent.unique_id, color)
                    if prev_same_color == 0:
                        # first unit of collect_color picked
                        self._first_pick_step[key] = self.steps
                    elif prev_same_color == 1 and key in self._first_pick_step:
                        # second unit -> interval completed
                        interval = self.steps - self._first_pick_step[key]
                        self._collection_intervals[color].append(interval)
                        del self._first_pick_step[key]
                # Step-2 broadcast: tell peers the waste is gone so they can
                # forget it and avoid wasted trips to phantom locations.
                self._broadcast({"type": "waste_gone", "pos": agent.pos,
                                 "color": color, "sender_id": agent.unique_id})
                return True
        return False

    def _can_pickup(self, agent, color):
        inv_colors = [w.color for w in agent.inventory]
        if isinstance(agent, RedAgent):
            # A red robot only ever carries one red waste
            return color == RED and len(inv_colors) == 0
        # Green/Yellow: up to CAPACITY of collect color, 0 produce when collecting
        if color == agent.COLLECT_COLOR:
            return inv_colors.count(agent.COLLECT_COLOR) < agent.CAPACITY \
                   and agent.PRODUCE_COLOR not in inv_colors
        return False

    def _try_transform(self, agent):
        if isinstance(agent, RedAgent):
            return False  # red robots do not transform
        inv_colors = [w.color for w in agent.inventory]
        if inv_colors.count(agent.COLLECT_COLOR) < agent.CAPACITY:
            return False
        # Consume CAPACITY collect wastes, produce 1 produce waste.
        removed = 0
        keep = []
        for w in agent.inventory:
            if w.color == agent.COLLECT_COLOR and removed < agent.CAPACITY:
                removed += 1
                w.remove()  # unregister the consumed Waste from the model
            else:
                keep.append(w)
        agent.inventory = keep
        produced = Waste(self, color=agent.PRODUCE_COLOR)
        produced.carried_by = agent
        agent.inventory.append(produced)
        # --- transformation counters ---------------------------------------
        if agent.COLLECT_COLOR == GREEN:
            self.green_to_yellow_transforms += 1
        elif agent.COLLECT_COLOR == YELLOW:
            self.yellow_to_red_transforms += 1
        # Transforming consumes the paired wastes -> clear any pending
        # first-pick timing for this robot on the collect color.
        self._first_pick_step.pop((agent.unique_id, agent.COLLECT_COLOR), None)
        return True

    def _try_drop(self, agent, color):
        # Find a carried waste of matching color
        for w in list(agent.inventory):
            if w.color == color:
                # Disposal: if we drop a red on the disposal cell, it's gone
                if color == RED and agent.pos == self.disposal_pos:
                    agent.inventory.remove(w)
                    w.carried_by = None
                    w.remove()  # unregister from model
                    # "Put away" forever
                    disposal = self._disposal_agent()
                    if disposal is not None:
                        disposal.stored += 1
                    self.n_disposed += 1
                    # Broadcast for step-2 logging
                    self._broadcast({"type": "disposed", "pos": agent.pos,
                                     "color": RED, "sender_id": agent.unique_id})
                    return True
                # Otherwise drop it back on the grid
                agent.inventory.remove(w)
                w.carried_by = None
                self.grid.place_agent(w, agent.pos)
                # Dropping our collect-color invalidates any pending
                # first-pick timing (deadlock-break path).
                if color == agent.COLLECT_COLOR:
                    self._first_pick_step.pop(
                        (agent.unique_id, agent.COLLECT_COLOR), None)
                # Step-2 broadcast
                self._broadcast({"type": "waste_at", "pos": agent.pos,
                                 "color": color, "sender_id": agent.unique_id})
                return True
        return False

    def _disposal_agent(self):
        for a in self.grid.get_cell_list_contents([self.disposal_pos]):
            if isinstance(a, WasteDisposalZone):
                return a
        return None

    # ------------------------------------------------------------ communication
    def _broadcast(self, msg):
        """Push a message on the shared board with a TTL."""
        if not self.communication:
            return
        msg = dict(msg)
        msg["ttl"] = self.message_ttl
        self.message_board.append(msg)

    def inbox_for(self, agent):
        """Return the messages visible to `agent` (delivered once, then
        considered consumed via TTL decrement in step)."""
        if not self.communication:
            return []
        out = []
        for msg in self.message_board:
            if msg.get("sender_id") == agent.unique_id:
                continue
            if self.comm_range == 0:
                out.append(msg)
                continue
            x1, y1 = agent.pos
            x2, y2 = msg["pos"]
            if abs(x1 - x2) + abs(y1 - y2) <= self.comm_range:
                out.append(msg)
        return out

    def _decay_messages(self):
        if not self.message_board:
            return
        new_board = []
        for msg in self.message_board:
            msg["ttl"] -= 1
            if msg["ttl"] > 0:
                new_board.append(msg)
        self.message_board = new_board

    # ---------------------------------------------------------------- stepping
    def step(self):
        """One simulation step. Activates robots in shuffled order."""
        # Activate only robot agents (passive ones have no step)
        robots = [a for a in self.agents if isinstance(a, RobotAgent)]
        random.shuffle(robots)
        for r in robots:
            r.step()
        self._decay_messages()
        # Note: Mesa 3.x auto-increments `self.steps`, no need to do it manually.
        self.datacollector.collect(self)
        # Stop when everything is cleared from the environment
        if (self._count_waste(GREEN) == 0
                and self._count_waste(YELLOW) == 0
                and self._count_waste(RED) == 0
                and all(len(r.inventory) == 0
                        for r in self.agents if isinstance(r, RobotAgent))):
            self.running = False

    # --------------------------------------------------------------- utilities
    def _count_waste(self, color):
        """Count waste of `color` on the grid + carried by robots."""
        return self._count_waste_on_grid(color) + self._count_waste_carried(color)

    def _count_waste_on_grid(self, color):
        """Wastes of `color` currently sitting on the grid (not carried)."""
        return sum(1 for a in self.agents
                   if isinstance(a, Waste)
                   and a.carried_by is None and a.color == color)

    def _count_waste_carried(self, color):
        """Wastes of `color` currently in some robot's inventory."""
        return sum(1 for a in self.agents if isinstance(a, RobotAgent)
                   for w in a.inventory if w.color == color)

    def _visited_ratio_for_zone(self, zone):
        """Fraction of cells in `zone` that have been visited by at least
        one robot. Unions every robot's `knowledge["visited"]` set."""
        all_visited = set()
        for a in self.agents:
            if isinstance(a, RobotAgent):
                all_visited.update(a.knowledge.get("visited", ()))
        total, hit = 0, 0
        for x in range(self.width):
            if self._zone_for_x(x) != zone:
                continue
            for y in range(self.height):
                total += 1
                if (x, y) in all_visited:
                    hit += 1
        return hit / total if total else 0.0

    def _avg_interval(self, color):
        """Mean steps between 1st and 2nd pickup of `color` for all
        transformations completed so far. Returns 0 if none yet."""
        lst = self._collection_intervals.get(color, [])
        return sum(lst) / len(lst) if lst else 0.0
