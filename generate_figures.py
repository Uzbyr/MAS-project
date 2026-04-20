# =============================================================================
# Group: Yoan Di Cosmo
# Project: Self-organization of robots in a hostile environment (MAS 2025-2026)
# Date of creation: 2026-04-20
# Member(s): Yoan Di Cosmo
# File: generate_figures.py - Produce every image used in the README.
# =============================================================================
#
# Outputs (saved under ./images/):
#   pipeline.png            : custom matplotlib pipeline diagram
#   grid_layout.png         : schematic of zones + disposal cell
#   waste_dynamics.png      : single-seed run trace
#   step1_vs_step2.png      : 20-seed completion-time boxplot
#   bonus_dynamics.png      : BONUS 1 - mean waste curves with ±1 std band
#   bonus_robot_count.png   : BONUS 2 - disposed / remaining vs robots per type
#   bonus_comm_range.png    : BONUS 3 - disposed vs communication range
#   bonus_distribution.png  : BONUS 4 - histogram of disposed over 100 runs
#
# Run:   python generate_figures.py
#
# Scenarios for bonus experiments (chosen to mirror the wider grid used in
# reference repos so communication range has room to vary):
#   grid = 30 x 10, n_wastes = 20, max_steps = 300, 3G/2Y/2R unless swept.
# =============================================================================

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

from model import RobotMission

OUT = "images"
os.makedirs(OUT, exist_ok=True)

BONUS_KW = dict(width=30, height=10, n_wastes=20)
BONUS_STEPS = 300


# =============================================================================
# 1. Custom pipeline diagram
# =============================================================================
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(11, 3.6))

    zone_colors = ["#e8f5e9", "#fff8e1", "#ffebee"]
    zone_titles = ["Zone z1\nlow radioactivity", "Zone z2\nmedium radioactivity",
                   "Zone z3\nhigh radioactivity"]
    for i, (c, t) in enumerate(zip(zone_colors, zone_titles)):
        ax.add_patch(patches.FancyBboxPatch(
            (i * 4, 0.5), 3.6, 3,
            boxstyle="round,pad=0.05", linewidth=1.2,
            edgecolor="#666", facecolor=c))
        ax.text(i * 4 + 1.8, 3.2, t, ha="center", va="top",
                fontsize=11, fontweight="bold")

    # Robots inside their allowed zones
    ax.text(1.8, 2.3, "GreenAgent", ha="center", color="#1b5e20", fontsize=10,
            fontweight="bold")
    ax.text(1.8, 1.9, "collects 2 green\ntransforms -> yellow",
            ha="center", va="center", fontsize=8.5)

    ax.text(5.8, 2.3, "YellowAgent", ha="center", color="#b57a00", fontsize=10,
            fontweight="bold")
    ax.text(5.8, 1.9, "collects 2 yellow\ntransforms -> red",
            ha="center", va="center", fontsize=8.5)

    ax.text(9.8, 2.3, "RedAgent", ha="center", color="#b71c1c", fontsize=10,
            fontweight="bold")
    ax.text(9.8, 1.9, "collects 1 red\nputs it in disposal",
            ha="center", va="center", fontsize=8.5)

    # Drop-arrows between zones
    arrow_style = dict(arrowstyle="->", linewidth=1.8, color="#333",
                       connectionstyle="arc3,rad=0.0")
    ax.annotate("", xy=(4, 1.3), xytext=(3.6, 1.3), arrowprops=arrow_style)
    ax.text(3.8, 1.05, "drops yellow", ha="center", fontsize=8, style="italic")
    ax.annotate("", xy=(8, 1.3), xytext=(7.6, 1.3), arrowprops=arrow_style)
    ax.text(7.8, 1.05, "drops red", ha="center", fontsize=8, style="italic")

    # Disposal marker
    ax.add_patch(patches.FancyBboxPatch(
        (12.0, 0.5), 1.6, 3,
        boxstyle="round,pad=0.05", linewidth=1.2,
        edgecolor="#444", facecolor="#212121"))
    ax.text(12.8, 2.0, "DISPOSAL\nCELL", ha="center", va="center",
            color="white", fontweight="bold", fontsize=10)
    ax.annotate("", xy=(12, 1.3), xytext=(11.6, 1.3), arrowprops=arrow_style)
    ax.text(11.8, 1.05, "delivers", ha="center", fontsize=8, style="italic")

    # Mass-conservation caption underneath
    ax.text(6.8, -0.1,
            r"mass conservation: $N$ green $\to$ $N/2$ yellow $\to$ $N/4$ red $\to$ $N/4$ disposed",
            ha="center", va="top", fontsize=9, style="italic", color="#555")

    ax.set_xlim(-0.3, 14)
    ax.set_ylim(-0.8, 4.2)
    ax.axis("off")
    plt.tight_layout()
    path = f"{OUT}/pipeline.png"
    plt.savefig(path, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"wrote {path}")


# =============================================================================
# 2. Grid layout - redone with labels OUTSIDE the grid so nothing overlaps
# =============================================================================
def fig_grid_layout():
    W, H = 12, 8
    zone_w = W // 3
    fig, ax = plt.subplots(figsize=(11, 5.2))

    colors = ["#e8f5e9", "#fff8e1", "#ffebee"]
    names = ["z1", "z2", "z3"]

    # 1. fill zones first
    for i in range(3):
        ax.add_patch(patches.Rectangle((i * zone_w, 0), zone_w, H,
                                       facecolor=colors[i], edgecolor="none",
                                       zorder=1))

    # 2. cell grid lines ON TOP of zones (visible now)
    for x in range(W + 1):
        lw = 1.6 if x in (0, zone_w, 2 * zone_w, W) else 0.5
        color = "#555" if x in (0, zone_w, 2 * zone_w, W) else "#bbb"
        ax.plot([x, x], [0, H], color=color, linewidth=lw, zorder=2)
    for y in range(H + 1):
        lw = 1.6 if y in (0, H) else 0.5
        color = "#555" if y in (0, H) else "#bbb"
        ax.plot([0, W], [y, y], color=color, linewidth=lw, zorder=2)

    # 3. zone labels above the grid
    for i, n in enumerate(names):
        ax.text(i * zone_w + zone_w / 2, H + 0.45, n,
                ha="center", va="bottom", fontsize=15, fontweight="bold")
    for i, r in enumerate(["[0.00, 0.33)", "[0.33, 0.66)", "[0.66, 1.00]"]):
        ax.text(i * zone_w + zone_w / 2, H + 1.4, r,
                ha="center", va="bottom", fontsize=9.5, color="#555")

    # 4. example waste markers (just to make the grid feel concrete)
    #    a couple greens in z1, a yellow at the z1/z2 border, a red in z3
    for p, color in [
        ((1, 2), "#2e7d32"), ((2, 5), "#2e7d32"), ((3, 1), "#2e7d32"),
        ((3, 4), "#f9a825"),
        ((9, 3), "#c62828"),
    ]:
        ax.scatter(p[0] + 0.5, p[1] + 0.5, s=110, color=color,
                   edgecolors="white", linewidths=1.5, zorder=3)

    # 5. disposal cell
    ax.add_patch(patches.Rectangle((W - 1, 4), 1, 1,
                                   facecolor="#212121", edgecolor="black",
                                   linewidth=1.4, zorder=3))
    ax.text(W - 0.5, 4.5, "X", ha="center", va="center",
            color="white", fontsize=14, fontweight="bold", zorder=4)
    ax.annotate("disposal cell\n(random y on x=11)",
                xy=(W - 0.5, 4.5), xytext=(W + 1.1, 5.5),
                va="center", fontsize=10,
                arrowprops=dict(arrowstyle="->", color="#111"))

    # 6. waste legend
    ax.scatter([], [], s=110, color="#2e7d32", edgecolors="white",
               linewidths=1.5, label="green waste")
    ax.scatter([], [], s=110, color="#f9a825", edgecolors="white",
               linewidths=1.5, label="yellow waste")
    ax.scatter([], [], s=110, color="#c62828", edgecolors="white",
               linewidths=1.5, label="red waste")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0),
              fontsize=9, framealpha=0.9)

    # 7. zone-access bars below the grid
    bar_y = -1.1
    for (y_off, width, color, label, reach) in [
        (0.0,   zone_w, "#66bb6a", "Green robot",  "z1"),
        (-0.7,  2 * zone_w, "#f9a825", "Yellow robot", "z1 + z2"),
        (-1.4,  W, "#ef5350", "Red robot",   "any zone"),
    ]:
        ax.add_patch(patches.Rectangle((0, bar_y + y_off), width, 0.45,
                                       facecolor=color, alpha=0.9, zorder=3))
        ax.text(width / 2, bar_y + y_off + 0.22, label,
                ha="center", va="center", fontsize=9.5,
                color="white", fontweight="bold", zorder=4)
        ax.text(W + 0.3, bar_y + y_off + 0.22, f"→ can enter {reach}",
                va="center", fontsize=9, color="#333")

    ax.text(-0.2, bar_y + 0.7, "Zone access:", ha="left", va="bottom",
            fontsize=10, fontweight="bold", color="#333")

    ax.set_xlim(-0.5, W + 5.2)
    ax.set_ylim(bar_y - 1.8, H + 2.3)
    ax.set_xticks([0, zone_w, 2 * zone_w, W])
    ax.set_xticklabels(["0", str(zone_w), str(2 * zone_w), str(W)])
    ax.set_yticks([])
    ax.set_aspect("equal")
    ax.set_title("Grid layout  (width = 12, height = 8, 3 vertical zones)",
                 pad=18, fontsize=13)
    ax.spines[["top", "right", "left"]].set_visible(False)
    plt.tight_layout()
    path = f"{OUT}/grid_layout.png"
    plt.savefig(path, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"wrote {path}")


# =============================================================================
# 3. Single-run waste dynamics
# =============================================================================
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
    axes[0].set_title("Wastes over time (seed=42, step 2 on)")
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


# =============================================================================
# 4. Step1 vs Step2 boxplot (20 seeds, default scenario)
# =============================================================================
def fig_step1_vs_step2(n_seeds=20, max_steps=800):
    configs = [("no-comm", False, 0), ("comm, global", True, 0),
               ("comm, range=5", True, 5)]
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
    axes[0].boxplot(data, tick_labels=[lbl for lbl, *_ in configs])
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
    print("Step1-vs-Step2 summary:")
    for lbl, *_ in configs:
        st = np.array(results[lbl]["steps"])
        print(f"  {lbl:<18} mean={st.mean():.1f} std={st.std():.1f} min={st.min()} max={st.max()}")


# =============================================================================
# BONUS 1: Average waste dynamics with ±1 std shaded band
# =============================================================================
def _run_collect_series(n_seeds, steps, **kw):
    """Run n_seeds simulations and collect per-step metrics into aligned arrays."""
    greens, yellows, reds, disposed, msgs = [], [], [], [], []
    for seed in range(n_seeds):
        m = RobotMission(seed=seed, **kw)
        for _ in range(steps):
            if not m.running:
                break
            m.step()
        df = m.datacollector.get_model_vars_dataframe()
        # Pad with final values so every run has `steps+1` samples
        padded = df.reindex(range(steps + 1)).ffill()
        greens.append(padded["green_wastes"].values)
        yellows.append(padded["yellow_wastes"].values)
        reds.append(padded["red_wastes"].values)
        disposed.append(padded["disposed"].values)
        msgs.append(padded["messages_active"].values)
    return (np.array(greens), np.array(yellows), np.array(reds),
            np.array(disposed), np.array(msgs))


def fig_bonus_dynamics(n_seeds=30, steps=BONUS_STEPS):
    g, y, r, d, _ = _run_collect_series(
        n_seeds, steps,
        n_green=3, n_yellow=2, n_red=2,
        communication=True, comm_range=0,
        **BONUS_KW)
    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = np.arange(steps + 1)
    for arr, color, label in [
        (g, "#2e7d32", "green waste"),
        (y, "#f9a825", "yellow waste"),
        (r, "#c62828", "red waste"),
        (d, "#424242", "disposed"),
    ]:
        mean, std = arr.mean(axis=0), arr.std(axis=0)
        ax.plot(x, mean, color=color, linewidth=2, label=label)
        ax.fill_between(x, mean - std, mean + std, color=color, alpha=0.18)
    ax.set_title(f"Average waste dynamics over {n_seeds} seeds (shaded = ±1 std)")
    ax.set_xlabel("simulation step")
    ax.set_ylabel("count")
    ax.legend(loc="upper right")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    path = f"{OUT}/bonus_dynamics.png"
    plt.savefig(path, dpi=130)
    plt.close()
    print(f"wrote {path}")
    return {"final_disposed_mean": float(d[:, -1].mean()),
            "final_disposed_std": float(d[:, -1].std())}


# =============================================================================
# BONUS 2: Performance vs robot count
# =============================================================================
def fig_bonus_robot_count(counts=(1, 3, 5, 7, 10), n_seeds=30, steps=BONUS_STEPS):
    rows = []
    for n in counts:
        dispo, remain = [], []
        for seed in range(n_seeds):
            m = RobotMission(seed=seed,
                             n_green=n, n_yellow=n, n_red=n,
                             communication=True, comm_range=0,
                             **BONUS_KW)
            for _ in range(steps):
                if not m.running:
                    break
                m.step()
            dispo.append(m.n_disposed)
            remain.append(m._count_waste("green") + m._count_waste("yellow")
                          + m._count_waste("red"))
        rows.append({"n": n,
                     "disposed_mean": np.mean(dispo),
                     "disposed_std": np.std(dispo),
                     "remaining_mean": np.mean(remain),
                     "remaining_std": np.std(remain)})
    df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.errorbar(df["n"], df["disposed_mean"], yerr=df["disposed_std"],
                marker="o", linewidth=2, capsize=4, color="#2e7d32",
                label="disposed (mean ±1 std)")
    ax.errorbar(df["n"], df["remaining_mean"], yerr=df["remaining_std"],
                marker="s", linewidth=2, capsize=4, color="#c62828",
                label="remaining (mean ±1 std)")
    ax.set_xlabel("robots per type (n_green = n_yellow = n_red)")
    ax.set_ylabel("count")
    ax.set_title(f"Performance vs robot count ({n_seeds} seeds / point, {steps} steps)")
    ax.set_xticks(list(counts))
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    path = f"{OUT}/bonus_robot_count.png"
    plt.savefig(path, dpi=130)
    plt.close()
    print(f"wrote {path}")
    print("robot-count table:")
    print(df.round(2).to_string(index=False))
    return df


# =============================================================================
# BONUS 3: Communication range sweep
# =============================================================================
def fig_bonus_comm_range(ranges=(0, 2, 5, 10, 20), n_seeds=30, steps=BONUS_STEPS):
    """range = 0 means no communication. Range > 0 uses Manhattan cutoff.
    (In the model, comm_range=0 with communication=True means 'global';
    here we explicitly pass communication=False for the 0 point to get the
    true baseline, and communication=True with explicit cutoff otherwise.)"""
    rows = []
    # Baseline: communication fully off
    dispo = []
    for seed in range(n_seeds):
        m = RobotMission(seed=seed, n_green=3, n_yellow=2, n_red=2,
                         communication=False, comm_range=0, **BONUS_KW)
        for _ in range(steps):
            if not m.running:
                break
            m.step()
        dispo.append(m.n_disposed)
    rows.append({"range": 0, "disposed_mean": np.mean(dispo),
                 "disposed_std": np.std(dispo)})
    # Non-zero ranges
    for r in ranges:
        if r == 0:
            continue
        dispo = []
        for seed in range(n_seeds):
            m = RobotMission(seed=seed, n_green=3, n_yellow=2, n_red=2,
                             communication=True, comm_range=r, **BONUS_KW)
            for _ in range(steps):
                if not m.running:
                    break
                m.step()
            dispo.append(m.n_disposed)
        rows.append({"range": r, "disposed_mean": np.mean(dispo),
                     "disposed_std": np.std(dispo)})
    df = pd.DataFrame(rows).sort_values("range").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.errorbar(df["range"], df["disposed_mean"], yerr=df["disposed_std"],
                marker="o", linewidth=2, capsize=4, color="#1565c0")
    ax.set_xlabel("communication range (Manhattan; 0 = no communication)")
    ax.set_ylabel("mean disposed")
    ax.set_title(f"Impact of communication range ({n_seeds} seeds / point)")
    ax.set_xticks(list(df["range"]))
    ax.grid(alpha=0.3)
    plt.tight_layout()
    path = f"{OUT}/bonus_comm_range.png"
    plt.savefig(path, dpi=130)
    plt.close()
    print(f"wrote {path}")
    print("comm-range table:")
    print(df.round(2).to_string(index=False))
    return df


# =============================================================================
# BONUS 4: Distribution over 100 runs
# =============================================================================
def fig_bonus_distribution(n_seeds=100, steps=BONUS_STEPS):
    dispo, remain = [], []
    for seed in range(n_seeds):
        m = RobotMission(seed=seed, n_green=3, n_yellow=2, n_red=2,
                         communication=True, comm_range=0, **BONUS_KW)
        for _ in range(steps):
            if not m.running:
                break
            m.step()
        dispo.append(m.n_disposed)
        remain.append(m._count_waste("green") + m._count_waste("yellow")
                      + m._count_waste("red"))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    axes[0].hist(dispo, bins=range(0, max(dispo) + 2),
                 color="#2e7d32", edgecolor="white", align="left")
    axes[0].axvline(np.mean(dispo), color="k", linestyle="--",
                    label=f"mean={np.mean(dispo):.2f}")
    axes[0].set_xlabel("red wastes disposed")
    axes[0].set_ylabel("# runs")
    axes[0].set_title(f"Disposed over {n_seeds} runs "
                      f"(mean={np.mean(dispo):.2f}, std={np.std(dispo):.2f})")
    axes[0].legend()
    axes[0].grid(alpha=0.3, axis="y")

    axes[1].hist(remain, bins=range(0, max(remain) + 2),
                 color="#c62828", edgecolor="white", align="left")
    axes[1].axvline(np.mean(remain), color="k", linestyle="--",
                    label=f"mean={np.mean(remain):.2f}")
    axes[1].set_xlabel("remaining wastes (grid + carried)")
    axes[1].set_ylabel("# runs")
    axes[1].set_title(f"Remaining over {n_seeds} runs "
                      f"(mean={np.mean(remain):.2f}, std={np.std(remain):.2f})")
    axes[1].legend()
    axes[1].grid(alpha=0.3, axis="y")

    plt.tight_layout()
    path = f"{OUT}/bonus_distribution.png"
    plt.savefig(path, dpi=130)
    plt.close()
    print(f"wrote {path}")
    print(f"distribution: disposed mean={np.mean(dispo):.2f} std={np.std(dispo):.2f}"
          f" range=[{min(dispo)}, {max(dispo)}]")
    print(f"              remaining mean={np.mean(remain):.2f} std={np.std(remain):.2f}"
          f" range=[{min(remain)}, {max(remain)}]")
    return {"disposed_mean": float(np.mean(dispo)),
            "disposed_std": float(np.std(dispo)),
            "disposed_min": int(min(dispo)),
            "disposed_max": int(max(dispo)),
            "remaining_mean": float(np.mean(remain)),
            "remaining_std": float(np.std(remain))}


# =============================================================================
# BONUS 5: Collection-time metric vs communication range
# =============================================================================
# Uses the new `avg_green_collect_time` / `avg_yellow_collect_time` reporters
# to quantify directly WHY communication helps: it shortens the gap between
# the 1st and 2nd pickup that each robot needs before it can transform.
def fig_bonus_collection_time(ranges=(0, 2, 5, 10, 20),
                              n_seeds=30, steps=BONUS_STEPS):
    """Two-panel figure exposing the 'selection bias' of the collection-time
    metric: communication enables MORE pairings (left panel: transform counts
    rise), which includes the harder ones (right panel: avg time per completed
    pairing rises). Together they say: with comms, we finish pairs we couldn't
    have finished at all before."""
    rows = []
    for r in ranges:
        greens, yellows, g2y, y2r = [], [], [], []
        for seed in range(n_seeds):
            comm = r > 0
            m = RobotMission(seed=seed, n_green=3, n_yellow=2, n_red=2,
                             communication=comm, comm_range=r, **BONUS_KW)
            for _ in range(steps):
                if not m.running:
                    break
                m.step()
            greens.append(m._avg_interval("green"))
            yellows.append(m._avg_interval("yellow"))
            g2y.append(m.green_to_yellow_transforms)
            y2r.append(m.yellow_to_red_transforms)
        rows.append({"range": r,
                     "green_mean": np.mean(greens),
                     "green_std":  np.std(greens),
                     "yellow_mean": np.mean(yellows),
                     "yellow_std":  np.std(yellows),
                     "g2y_mean": np.mean(g2y),
                     "g2y_std":  np.std(g2y),
                     "y2r_mean": np.mean(y2r),
                     "y2r_std":  np.std(y2r)})
    df = pd.DataFrame(rows)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))

    # Left: throughput (# completed transformations per run)
    axes[0].errorbar(df["range"], df["g2y_mean"], yerr=df["g2y_std"],
                     marker="o", linewidth=2, capsize=4, color="#2e7d32",
                     label="green -> yellow transforms")
    axes[0].errorbar(df["range"], df["y2r_mean"], yerr=df["y2r_std"],
                     marker="s", linewidth=2, capsize=4, color="#b57a00",
                     label="yellow -> red transforms")
    axes[0].set_xlabel("communication range (0 = off)")
    axes[0].set_ylabel("avg completed transformations per run")
    axes[0].set_title("Pipeline throughput")
    axes[0].set_xticks(list(df["range"]))
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    # Right: per-pair collection time (only counts pairings that COMPLETED)
    axes[1].errorbar(df["range"], df["green_mean"], yerr=df["green_std"],
                     marker="o", linewidth=2, capsize=4, color="#2e7d32",
                     label="green collection time")
    axes[1].errorbar(df["range"], df["yellow_mean"], yerr=df["yellow_std"],
                     marker="s", linewidth=2, capsize=4, color="#b57a00",
                     label="yellow collection time")
    axes[1].set_xlabel("communication range (0 = off)")
    axes[1].set_ylabel("avg steps between 1st and 2nd pickup")
    axes[1].set_title("Per-pair search cost (completed pairings only)")
    axes[1].set_xticks(list(df["range"]))
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    fig.suptitle(f"Communication enables harder pairings ({n_seeds} seeds)",
                 fontsize=12, y=1.02)
    plt.tight_layout()
    path = f"{OUT}/bonus_collection_time.png"
    plt.savefig(path, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"wrote {path}")
    print("collection-time + throughput table:")
    print(df.round(2).to_string(index=False))
    return df


# =============================================================================
# BONUS 6: Per-zone exploration coverage over time
# =============================================================================
def fig_bonus_zone_coverage(n_seeds=30, steps=BONUS_STEPS):
    """Averaged visited-ratio per zone across seeds, as a function of step."""
    z1, z2, z3 = [], [], []
    for seed in range(n_seeds):
        m = RobotMission(seed=seed, n_green=3, n_yellow=2, n_red=2,
                         communication=True, comm_range=0, **BONUS_KW)
        for _ in range(steps):
            if not m.running:
                break
            m.step()
        df = m.datacollector.get_model_vars_dataframe()
        padded = df.reindex(range(steps + 1)).ffill()
        z1.append(padded["visited_z1"].values)
        z2.append(padded["visited_z2"].values)
        z3.append(padded["visited_z3"].values)
    z1, z2, z3 = np.array(z1), np.array(z2), np.array(z3)

    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = np.arange(steps + 1)
    for arr, color, label in [
        (z1, "#2e7d32", "zone z1 (green)"),
        (z2, "#f9a825", "zone z2 (yellow)"),
        (z3, "#c62828", "zone z3 (red)"),
    ]:
        mean, std = arr.mean(axis=0), arr.std(axis=0)
        ax.plot(x, mean, color=color, linewidth=2, label=label)
        ax.fill_between(x, mean - std, mean + std, color=color, alpha=0.18)
    ax.set_title(f"Per-zone exploration coverage over time ({n_seeds} seeds, shaded = ±1 std)")
    ax.set_xlabel("simulation step")
    ax.set_ylabel("fraction of zone visited by at least one robot")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    path = f"{OUT}/bonus_zone_coverage.png"
    plt.savefig(path, dpi=130)
    plt.close()
    print(f"wrote {path}")
    print(f"final coverage (step {steps}):  z1={z1[:, -1].mean():.2f}"
          f"  z2={z2[:, -1].mean():.2f}  z3={z3[:, -1].mean():.2f}")


# =============================================================================
# Main
# =============================================================================
if __name__ == "__main__":
    fig_pipeline()
    fig_grid_layout()
    fig_waste_dynamics()
    fig_step1_vs_step2()
    print("\n=== BONUS experiments (30x10 grid, 20 greens, 300 steps) ===\n")
    fig_bonus_dynamics()
    print()
    fig_bonus_robot_count()
    print()
    fig_bonus_comm_range()
    print()
    fig_bonus_distribution()
    print()
    fig_bonus_collection_time()
    print()
    fig_bonus_zone_coverage()
