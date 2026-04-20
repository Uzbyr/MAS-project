# =============================================================================
# Group: Yoan Di Cosmo
# Project: Self-organization of robots in a hostile environment (MAS 2025-2026)
# Date of creation: 2026-04-20
# Member(s): Yoan Di Cosmo
# File: run.py - Headless batch run + matplotlib plot of key metrics
# =============================================================================
#
# Usage:
#     python run.py                         # default 200-step run, shows chart
#     python run.py --no-communication      # disable message board
#     python run.py --steps 500 --seed 7    # custom run
#
# For the interactive visualization, run:
#     solara run server.py
# =============================================================================

import argparse

import matplotlib.pyplot as plt

from model import RobotMission


def main():
    parser = argparse.ArgumentParser(description="RobotMission headless run")
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--width", type=int, default=12)
    parser.add_argument("--height", type=int, default=8)
    parser.add_argument("--n-green", type=int, default=3)
    parser.add_argument("--n-yellow", type=int, default=2)
    parser.add_argument("--n-red", type=int, default=2)
    parser.add_argument("--n-wastes", type=int, default=8)
    parser.add_argument("--no-communication", action="store_true")
    parser.add_argument("--comm-range", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-plot", action="store_true",
                        help="Do not open the matplotlib chart")
    args = parser.parse_args()

    model = RobotMission(
        width=args.width, height=args.height,
        n_green=args.n_green, n_yellow=args.n_yellow, n_red=args.n_red,
        n_wastes=args.n_wastes,
        communication=not args.no_communication,
        comm_range=args.comm_range,
        seed=args.seed,
    )

    for _ in range(args.steps):
        if not model.running:
            break
        model.step()

    df = model.datacollector.get_model_vars_dataframe()
    print(df.tail(10))
    print(f"\nFinished in {model.steps} steps. Disposed: {model.n_disposed}")

    if args.no_plot:
        return

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    df[["green_wastes", "yellow_wastes", "red_wastes", "disposed"]].plot(
        ax=axes[0], title="Wastes over time"
    )
    axes[0].set_xlabel("step")
    axes[0].set_ylabel("count")
    df[["messages_active"]].plot(ax=axes[1], title="Active messages on board")
    axes[1].set_xlabel("step")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
