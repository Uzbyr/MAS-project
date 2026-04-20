# =============================================================================
# Group: Yoan Di Cosmo
# Project: Self-organization of robots in a hostile environment (MAS 2025-2026)
# Date of creation: 2026-04-20
# Member(s): Yoan Di Cosmo
# File: objects.py - Passive agents (no behavior): Waste, Radioactivity, Disposal
# =============================================================================

import mesa


# -- Waste color constants ----------------------------------------------------
GREEN = "green"
YELLOW = "yellow"
RED = "red"

WASTE_COLORS = (GREEN, YELLOW, RED)


class Waste(mesa.Agent):
    """A piece of waste. Three possible colors: green, yellow, red.

    Wastes do not act (no `step` method). The environment (Model) is in
    charge of moving them (when carried by a robot) or removing them
    (when transformed or disposed of).
    """

    def __init__(self, model, color):
        super().__init__(model)
        assert color in WASTE_COLORS
        self.color = color
        # Whether this waste is currently carried by a robot. When carried,
        # the waste is removed from the grid and lives on the robot.
        self.carried_by = None

    def __repr__(self):
        return f"Waste<{self.color}, id={self.unique_id}>"


class Radioactivity(mesa.Agent):
    """Marks a grid cell with its zone (1, 2, 3) and radioactivity level.

    Robots use the radioactivity attribute to infer in which zone they are,
    without needing direct access to the model's zone boundaries.
    """

    # Radioactivity ranges (inclusive lower, exclusive upper):
    #   z1 -> [0.00, 0.33)
    #   z2 -> [0.33, 0.66)
    #   z3 -> [0.66, 1.00]
    def __init__(self, model, zone, level):
        super().__init__(model)
        assert zone in (1, 2, 3)
        self.zone = zone
        self.level = float(level)

    def __repr__(self):
        return f"Radioactivity<z{self.zone}, lvl={self.level:.2f}>"


class WasteDisposalZone(mesa.Agent):
    """A single cell in the far-east strip of the grid where red wastes are
    definitively stored. It has no behavior.
    """

    def __init__(self, model):
        super().__init__(model)
        # Collected red wastes (for metrics). Not actively used by logic.
        self.stored = 0

    def __repr__(self):
        return f"DisposalZone<stored={self.stored}>"
