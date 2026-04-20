# =============================================================================
# Group: Yoan Di Cosmo
# Project: Self-organization of robots in a hostile environment (MAS 2025-2026)
# Date of creation: 2026-04-20
# Member(s): Yoan Di Cosmo
# File: server.py - Solara-based visualization (Mesa 3.x)
# =============================================================================

import solara
from mesa.visualization import SolaraViz, make_space_component, make_plot_component

from model import RobotMission
from agents import GreenAgent, YellowAgent, RedAgent
from objects import Waste, Radioactivity, WasteDisposalZone, GREEN, YELLOW, RED


def _portrayal(agent):
    """Map each agent type to a marker / color in the Solara grid."""
    if isinstance(agent, GreenAgent):
        return {"color": "#1b5e20", "marker": "s", "size": 120, "zorder": 4}
    if isinstance(agent, YellowAgent):
        return {"color": "#f9a825", "marker": "s", "size": 120, "zorder": 4}
    if isinstance(agent, RedAgent):
        return {"color": "#b71c1c", "marker": "s", "size": 120, "zorder": 4}
    if isinstance(agent, Waste):
        color = {GREEN: "#81c784", YELLOW: "#fff176", RED: "#e57373"}[agent.color]
        return {"color": color, "marker": "o", "size": 60, "zorder": 3}
    if isinstance(agent, WasteDisposalZone):
        return {"color": "#000000", "marker": "X", "size": 200, "zorder": 2}
    if isinstance(agent, Radioactivity):
        # Background tiles: very transparent shade per zone
        shade = {1: "#e8f5e9", 2: "#fff8e1", 3: "#ffebee"}[agent.zone]
        return {"color": shade, "marker": "s", "size": 400, "zorder": 1}
    return {"color": "black", "marker": "o", "size": 20}


# --- Model parameters exposed as UI sliders ----------------------------------
model_params = {
    "width": {"type": "SliderInt", "value": 12, "label": "Grid width",
              "min": 6, "max": 30, "step": 3},
    "height": {"type": "SliderInt", "value": 8, "label": "Grid height",
               "min": 4, "max": 20, "step": 1},
    "n_green": {"type": "SliderInt", "value": 3, "label": "# green robots",
                "min": 0, "max": 10, "step": 1},
    "n_yellow": {"type": "SliderInt", "value": 2, "label": "# yellow robots",
                 "min": 0, "max": 10, "step": 1},
    "n_red": {"type": "SliderInt", "value": 2, "label": "# red robots",
              "min": 0, "max": 10, "step": 1},
    "n_wastes": {"type": "SliderInt", "value": 8, "label": "# initial green wastes",
                 "min": 0, "max": 30, "step": 1},
    "communication": {"type": "Checkbox", "value": True, "label": "Communication (step 2)"},
    "comm_range": {"type": "SliderInt", "value": 0, "label": "Comm range (0 = global)",
                   "min": 0, "max": 30, "step": 1},
    "seed": 42,
}


model = RobotMission(
    width=12, height=8,
    n_green=3, n_yellow=2, n_red=2,
    n_wastes=8,
    communication=True, comm_range=0,
    seed=42,
)

SpaceGraph = make_space_component(_portrayal)
WastePlot = make_plot_component(["green_wastes", "yellow_wastes", "red_wastes", "disposed"])
MessagesPlot = make_plot_component(["messages_active"])

page = SolaraViz(
    model,
    components=[SpaceGraph, WastePlot, MessagesPlot],
    model_params=model_params,
    name="RobotMission - Yoan Di Cosmo (MAS 2025-2026)",
)
