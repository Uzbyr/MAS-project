# =============================================================================
# Group: Yoan Di Cosmo
# Project: Self-organization of robots in a hostile environment (MAS 2025-2026)
# Date of creation: 2026-04-20
# Member(s): Yoan Di Cosmo
# File: generate_figures.py - Produce the images used in the README.
# =============================================================================
#
# Outputs (saved under ./images/):
#   - waste_dynamics.png   : one run, waste counts + disposals + messages
#   - step1_vs_step2.png   : 20-seed comparison boxplot and disposal bar
#   - grid_layout.png      : schematic of zones + disposal cell
#
# Run:    python generate_figures.py
# =============================================================================

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from model import RobotMission

OUT = "images"
os.makedirs(OUT, exist_ok=True)


# --------------------------------------------------------------------- 1. run
def fig_waste_dynamics():
    m = RobotMission(width=12, height=8, n_green=3, n_yellow=2, n_red=2,
                     n_wastes=8, communication=True, seed=42)
    for _ in range(400):
        if not m.running:
            break
        m.step()
    df = m.datacollector.get_model_vars_dataframe()

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    df[["green_wastes", "yellow_wastes", "red_wastes", "disposed"]].plot(
        ax=axes[0], color=["#2e7d32", "#f9a825", "#c62828", "#424242"],
        linewidth=2)
    axes[0].set_title("Wastes over time (step 2, seed=42)")
    axes[0].set_xlabel("simulation step")
    axes[0].set_ylabel("count")
    axes[0].grid(alpha=0.3)

    df[["messages_active"]].plot(ax=axes[1], color="#1565c0", linewidth=2,
                                 legend=False)
    axes[1].set_title("Active messages on board")
    axes[1].set_xlabel("simulation step")
    axes[1].set_ylabel("count")
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    path = f"{OUT}/waste_dynamics.png"
    plt.savefig(path, dpi=130)
    plt.close()
    print(f"wrote {path}  (completed in {m.steps} steps, disposed={m.n_disposed})")


# ---------------------------------------------------------- 2. multi-seed
def fig_step1_vs_step2(n_seeds=20, max_steps=800):
    configs = [
        ("no-comm",           False, 0),
        ("comm, global",      True,  0),
        ("comm, range=5",     True,  5),
    ]
    results = {lbl: {"steps": [], "disposed": []} for lbl, *_ in configs}

    for seed in range(n_seeds):
        for label, comm, rng in configs:
            m = RobotMission(width=12, height=8, n_green=3, n_yellow=2, n_red=2,
                             n_wastes=8, communication=comm, comm_range=rng,
                             seed=seed)
            for _ in range(max_steps):
                if not m.running:
                    break
                m.step()
            results[label]["steps"].append(m.steps)
            results[label]["disposed"].append(m.n_disposed)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    data = [results[lbl]["steps"] for lbl, *_ in configs]
    axes[0].boxplot(data, labels=[lbl for lbl, *_ in configs])
    axes[0].set_title(f"Completion time ({n_seeds} seeds)")
    axes[0].set_ylabel("steps to clear environment")
    axes[0].grid(alpha=0.3, axis="y")
    axes[0].tick_params(axis="x", rotation=10)

    means = [np.mean(results[lbl]["disposed"]) for lbl, *_ in configs]
    colors = ["#ef5350", "#66bb6a", "#42a5f5"]
    axes[1].bar(range(len(configs)), means, color=colors)
    axes[1].set_xticks(range(len(configs)))
    axes[1].set_xticklabels([lbl for lbl, *_ in configs], rotation=10)
    axes[1].set_ylabel("mean disposed")
    axes[1].set_title("Mean red wastes disposed per run")
    axes[1].grid(alpha=0.3, axis="y")

    plt.tight_layout()
    path = f"{OUT}/step1_vs_step2.png"
    plt.savefig(path, dpi=130)
    plt.close()
    print(f"wrote {path}")
    # Also print a summary table for the README
    print("\nSummary over %d seeds:" % n_seeds)
    print(f"{'config':<18} {'mean':>6} {'std':>6} {'min':>5} {'max':>5}")
    for lbl, *_ in configs:
        st = np.array(results[lbl]["steps"])
        print(f"{lbl:<18} {st.mean():>6.1f} {st.std():>6.1f} {st.min():>5d} {st.max():>5d}")


# ---------------------------------------------------------- 3. grid layout
def fig_grid_layout():
    fig, ax = plt.subplots(figsize=(9, 3.6))
    W, H = 12, 8
    zone_w = W // 3
    colors = {"z1": "#e8f5e9", "z2": "#fff8e1", "z3": "#ffebee"}
    labels = {"z1": "z1  low radioactivity\n[0.00, 0.33)\ngreen waste spawns here",
              "z2": "z2  medium radioactivity\n[0.33, 0.66)",
              "z3": "z3  high radioactivity\n[0.66, 1.00]\nwaste disposal cell here"}

    for i, z in enumerate(["z1", "z2", "z3"]):
        ax.add_patch(patches.Rectangle((i * zone_w, 0), zone_w, H,
                                       facecolor=colors[z], edgecolor="#888"))
        ax.text(i * zone_w + zone_w / 2, H / 2, labels[z],
                ha="center", va="center", fontsize=10)

    # disposal marker
    ax.scatter([W - 0.5], [H / 2], marker="X", s=300, color="#222",
               zorder=5, label="disposal cell")

    # robot zones annotation
    ax.annotate("Green robot ⟵ z1 only", xy=(zone_w / 2, -0.8),
                ha="center", fontsize=9, color="#2e7d32")
    ax.annotate("Yellow robot ⟵ z1 + z2", xy=(1.5 * zone_w, -0.8),
                ha="center", fontsize=9, color="#b57a00")
    ax.annotate("Red robot ⟵ any zone", xy=(2.5 * zone_w, -0.8),
                ha="center", fontsize=9, color="#c62828")

    ax.set_xlim(0, W)
    ax.set_ylim(-2, H)
    ax.set_xticks(range(0, W + 1, zone_w))
    ax.set_yticks([])
    ax.set_title("Grid layout (width=12, height=8)")
    ax.set_aspect("equal")

    plt.tight_layout()
    path = f"{OUT}/grid_layout.png"
    plt.savefig(path, dpi=130)
    plt.close()
    print(f"wrote {path}")


if __name__ == "__main__":
    fig_waste_dynamics()
    fig_step1_vs_step2()
    fig_grid_layout()
