"""Summarize paired L5 and enhanced-L6 layout decisions on identical fixed content."""

from collections import Counter

from fixed_layout.paired_analysis import analyze


def summarize(rows):
    """Each request has two observed Boolean outcomes and one original family."""
    if not rows:
        raise ValueError("No fixed-content pairs")
    counts = Counter()
    roster, decisions = [], []
    for row in rows:
        model, program = row["l5"], row["l6"]
        if type(model) is not bool or type(program) is not bool:
            raise ValueError("Missing layout decisions cannot be counted as rejections")
        counts[model, program] += 1
        roster.append({"task_id": row["task"], "family_id": row["family"]})
        decisions.append(
            {
                "task_id": row["task"],
                "A": "pass" if model else "fail",
                "B": "pass" if program else "fail",
            }
        )
    interval = analyze(roster, decisions)["paired_cluster_percentile_ci95"]
    net = counts[False, True] - counts[True, False]
    return {
        "requests": len(rows),
        "families": len({row["family"] for row in rows}),
        "l5": counts[True, True] + counts[True, False],
        "l6": counts[True, True] + counts[False, True],
        "both": counts[True, True],
        "only_l5": counts[True, False],
        "only_l6": counts[False, True],
        "neither": counts[False, False],
        "net_l6_minus_l5": net,
        "net_percentage_points": round(100 * net / len(rows), 3),
        "family_bootstrap_ci95_pp": [round(100 * x, 3) for x in interval]
        if interval
        else None,
    }
