"""Render the public aggregate without opening task records (Matplotlib 3.10.7)."""

import argparse
import json
from pathlib import Path


def draw(report, output):
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

    cohort = report["six_arm_complete_usage"]
    n = cohort["shared_tasks"]
    arms = cohort["arms"]
    fig, axes = plt.subplots(1, 2, figsize=(9.3, 3.7), sharey=True)
    fig.subplots_adjust(left=0.08, right=0.975, top=0.81, bottom=0.23, wspace=0.20)
    panels = (
        ("technical_pass", "A    Common technical checks"),
        ("native_screen_pass", "B    On-device control checks"),
    )
    colors = {"L1": "#744098", "L5": "#00796d", "L6": "#b24f10"}
    label_offsets = {
        "technical_pass": {"L2": (-1, 8), "L3": (-2, -14), "L4": (-1, 8)},
        "native_screen_pass": {"L2": (7, 5), "L3": (-3, -15)},
    }
    for ax, (endpoint, title) in zip(axes, panels):
        cost = "tokens_per_" + endpoint
        efficient = set(cohort["frontiers"][endpoint][cost])
        for arm, row in arms.items():
            if row[cost] is None:
                continue
            x, y = row[cost], 100 * row[endpoint] / n
            color = colors.get(arm, "#536174")
            ax.scatter(x, y, s=52, c=color, zorder=3, linewidths=0)
            if arm in efficient:
                ax.scatter(
                    x,
                    y,
                    s=113,
                    facecolors="none",
                    edgecolors=color,
                    linewidths=1,
                    zorder=3,
                )
            dx, dy = label_offsets[endpoint].get(arm, (5, 7))
            ax.annotate(
                arm,
                (x, y),
                xytext=(dx, dy),
                textcoords="offset points",
                fontsize=9,
                fontweight="bold",
                color=color,
            )
        ax.set_title(title, loc="left", fontsize=11.5, fontweight="bold", pad=12)
        ax.set_xscale("log")
        ax.set_xlim(2800, 110000)
        ax.xaxis.set_major_locator(
            FixedLocator([3000, 5000, 10000, 20000, 50000, 100000])
        )
        ax.xaxis.set_major_formatter(
            FuncFormatter(lambda value, _: f"{value / 1000:g}k")
        )
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_ylim(0, 80)
        ax.set_yticks([0, 20, 40, 60, 80])
        ax.set_axisbelow(True)
        ax.grid(axis="y", color="#dce2e6", linewidth=0.7)
        ax.spines[["right", "top"]].set_visible(False)
        for edge in ("bottom", "left"):
            ax.spines[edge].set_color("#96a0a9")
        ax.tick_params(labelsize=8, length=3, color="#96a0a9")
    axes[0].set_ylabel("Tasks with an observed pass (%)", fontsize=9)
    fig.text(
        0.525,
        0.105,
        "Total model tokens / observed pass (log scale)",
        ha="center",
        fontsize=10,
    )
    fig.text(
        0.08,
        0.025,
        f"Same {n} tasks in both panels. Rings mark non-dominated arms for the plotted axes.",
        fontsize=8,
        color="#425063",
    )
    fig.savefig(output, dpi=220, metadata={"Software": "EasyA2UI cost-frontier study"})
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("public_summary", type=Path)
    parser.add_argument("figure", type=Path)
    args = parser.parse_args()
    draw(json.loads(args.public_summary.read_bytes()), args.figure)
