# =============================================================================
# Group: Yoan Di Cosmo
# Project: Self-organization of robots in a hostile environment (MAS 2025-2026)
# Date of creation: 2026-04-20
# Member(s): Yoan Di Cosmo
# File: batch_run.py - Multi-seed comparison: Step 1 (no comm) vs Step 2 (comm)
# =============================================================================
#
# Runs the same scenario many times with different seeds, under two regimes
# (communication on / off), collects per-run completion time and disposal
# count, and produces a comparison chart.
#
# Usage:
#     python batch_run.py                       # 15 seeds per config, default
#     python batch_run.py --n-seeds 30          # more statistical power
#     python batch_run.py --no-plot --csv out.csv
# =============================================================================

import argparse
import time

import pandas as pd
import matplotlib.pyplot as plt

from model import RobotMission


def run_one(seed, *, max_steps, communication, comm_range, **kwargs):
    """Run a single simulation to completion (or until max_steps). Returns a
    dict of summary metrics."""
    model = RobotMission(seed=seed, communication=communication,
                         comm_range=comm_range, **kwargs)
    t0 = time.time()
    for _ in range(max_steps):
        if not model.running:
            break
        model.step()
    wall = time.time() - t0
    return {
        "seed": seed,
        "communication": communication,
        "comm_range": comm_range,
        "steps": int(model.steps),
        "disposed": model.n_disposed,
        "finished": not model.running,
        "wall_s": wall,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-seeds", type=int, default=15,
                        help="Number of runs per configuration")
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--width", type=int, default=12)
    parser.add_argument("--height", type=int, default=8)
    parser.add_argument("--n-green", type=int, default=3)
    parser.add_argument("--n-yellow", type=int, default=2)
    parser.add_argument("--n-red", type=int, default=2)
    parser.add_argument("--n-wastes", type=int, default=8)
    parser.add_argument("--csv", type=str, default=None,
                        help="If set, write per-run results to this CSV")
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    base_kwargs = dict(
        width=args.width, height=args.height,
        n_green=args.n_green, n_yellow=args.n_yellow, n_red=args.n_red,
        n_wastes=args.n_wastes,
    )

    configs = [
        {"label": "Step 1 (no comm)", "communication": False, "comm_range": 0},
        {"label": "Step 2 (comm, global)", "communication": True, "comm_range": 0},
        {"label": "Step 2 (comm, range=5)", "communication": True, "comm_range": 5},
    ]

    rows = []
    for cfg in configs:
        print(f"\n--- {cfg['label']} ---")
        for seed in range(args.n_seeds):
            r = run_one(seed=seed, max_steps=args.max_steps,
                        communication=cfg["communication"],
                        comm_range=cfg["comm_range"],
                        **base_kwargs)
            r["config"] = cfg["label"]
            rows.append(r)
            print(f"  seed={seed:2d}  steps={r['steps']:4d}  disposed={r['disposed']}"
                  f"  finished={r['finished']}")

    df = pd.DataFrame(rows)
    print("\n=== Summary (completed runs only) ===")
    summary = (df[df["finished"]]
               .groupby("config")
               .agg(mean_steps=("steps", "mean"),
                    std_steps=("steps", "std"),
                    median_steps=("steps", "median"),
                    mean_disposed=("disposed", "mean"),
                    completion_rate=("finished", "count")))
    summary["completion_rate"] = summary["completion_rate"] / args.n_seeds
    print(summary.round(2))

    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"\nWrote {args.csv}")

    if args.no_plot:
        return

    # Box + bar comparison
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # Boxplot of completion times per config (only finished runs)
    finished = df[df["finished"]]
    configs_order = [c["label"] for c in configs]
    data = [finished[finished["config"] == c]["steps"].values for c in configs_order]
    axes[0].boxplot(data, labels=configs_order)
    axes[0].set_ylabel("steps to completion")
    axes[0].set_title(f"Completion time over {args.n_seeds} seeds")
    axes[0].tick_params(axis="x", rotation=15)

    # Bar of mean disposed (over all runs, finished or not)
    means = df.groupby("config")["disposed"].mean().reindex(configs_order)
    axes[1].bar(range(len(means)), means.values)
    axes[1].set_xticks(range(len(means)))
    axes[1].set_xticklabels(means.index, rotation=15)
    axes[1].set_ylabel("mean disposed")
    axes[1].set_title("Mean disposals per run")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
