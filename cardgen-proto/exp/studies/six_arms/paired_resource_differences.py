"""Paper §4.4: paired executor-time and metered token differences on the formal batch."""

import argparse
import json
import random
from collections import defaultdict
from decimal import Decimal
from itertools import groupby
from math import isfinite
from pathlib import Path
from statistics import median, quantiles

from fixed_layout.paired_analysis import N_BOOT, SEED
from six_arms.cost_frontier import TECH_LEDGER, usage
from six_arms.technical_yield import ARMS, read_lines

PINS = {
    "analysis/roster.jsonl": "ffcecb4ce1cf0f0fb0ea9e3a43140c1b119420f619d335ad621bd2063e9a39c2",
    TECH_LEDGER: "8a14e60a953e8b7e445df7985c7512ceefff94f0fcc404cc62bf6a6c51f83e72",
}
TABLE = (
    Path(__file__).resolve().parents[4]
    / "paper/out/tables/paired_resource_differences.json"
)


def signed_rank(differences):
    """Exact two-sided conditional sign randomization with tied average ranks."""
    nonzero = sorted((d for d in differences if d), key=abs)
    weights = []
    positive = 0
    for _, tied in groupby(nonzero, key=abs):
        values = list(tied)
        # Twice the mean of the consecutive 1-based ranks occupied by this tie.
        rank = 2 * len(weights) + 1 + len(values)
        weights.extend([rank] * len(values))
        positive += rank * sum(v > 0 for v in values)
    negative = sum(weights) - positive
    tail = min(positive, negative)
    # Number of sign allocations yielding each (doubled) rank sum through the observed tail.
    counts = [1] + [0] * tail
    for rank in weights:
        for subtotal in range(tail, rank - 1, -1):
            counts[subtotal] += counts[subtotal - rank]
    return {
        "nonzero": len(weights),
        "zeros": len(differences) - len(weights),
        "w_positive": positive / 2,
        "w_negative": negative / 2,
        "p_two_sided": min(1.0, 2 * sum(counts) / 2 ** len(weights))
        if weights
        else None,
    }


def metric_values(row):
    elapsed = row["elapsed_ms"]
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not isfinite(elapsed)
        or elapsed < 0
    ):
        raise ValueError("Missing or invalid terminal wall time")
    micros = Decimal(str(elapsed)) * 1000
    if micros != micros.to_integral_value():
        raise ValueError("Elapsed time precision changed")
    counts, missing = usage(row["calls"])
    return {
        "executor_ms": int(micros),
        "prompt_tokens": None if missing else counts["prompt_tokens"],
        "completion_tokens": None if missing else counts["completion_tokens"],
    }


def describe(by_family, assigned, scale):
    groups = [by_family[key] for key in sorted(by_family)]
    deltas = [v for group in groups for v in group]
    if not deltas:
        return {
            "assigned": assigned,
            "known_task_pairs": 0,
            "missing_task_pairs": assigned,
        }
    rng = random.Random(SEED)
    estimates = [
        median([v for g in rng.choices(groups, k=len(groups)) for v in g]) / scale
        for _ in range(N_BOOT)
    ]
    cuts = quantiles(estimates, n=1000, method="inclusive")
    family_medians = [median(g) for g in groups]
    return {
        "assigned": assigned,
        "known_task_pairs": len(deltas),
        "missing_task_pairs": assigned - len(deltas),
        "families_with_known_pairs": len(groups),
        "paired_median_difference": median(deltas) / scale,
        "task_weighted_cluster_bootstrap_ci95": [
            round(cuts[24], 6),
            round(cuts[974], 6),
        ],
        "query_signed_rank": signed_rank(deltas),
        "equal_family_median_difference": median(family_medians) / scale,
        "family_median_signed_rank": signed_rank(family_medians),
    }


def analyze(roster, rows):
    tasks = {r["task_id"]: r for r in roster}
    grid = {(r["task_id"], r["arm"]): metric_values(r) for r in rows}
    if (
        len(tasks) != len(roster)
        or len(rows) != len(grid)
        or set(grid) != {(t, a) for t in tasks for a in ARMS}
        or any(r["state"] != "terminal" for r in rows)
        or any(not r["family"] for r in roster)
    ):
        raise ValueError(
            "Expected one terminal seat per assigned arm and a family for every task"
        )
    results = {}
    for cohort, selected in (
        ("all_assigned", roster),
        ("source_217", [r for r in roster if r["included_in_217_sensitivity"]]),
    ):
        results[cohort] = {}
        for left, right in (("L5", "L4"), ("L6", "L5")):
            paired = {}
            for metric, scale in (
                ("executor_ms", 1000),
                ("prompt_tokens", 1),
                ("completion_tokens", 1),
            ):
                families = defaultdict(list)
                for r in selected:
                    task = r["task_id"]
                    a, b = grid[task, left][metric], grid[task, right][metric]
                    if a is not None and b is not None:
                        families[r["family"]].append(a - b)
                paired[metric] = describe(families, len(selected), scale)
            results[cohort][f"{left}_minus_{right}"] = paired
    return {
        "scope": "Original whole-request arms, including failures and early stops. Wall time ends at the executor and excludes rendering. "
        "B3 requires a complete meter for both seats. A negative paired difference favors the first arm on resource use only.",
        "method": "Medians of within-query differences. Resample whole families with replacement, then take the median across all sampled queries. "
        "Wilcoxon exact two-sided conditional on the nonzero absolute differences, using average ranks for ties. "
        "The query test assumes independent symmetric signs; the family sensitivity uses one median difference per family. "
        "P values are descriptive and unadjusted for multiple comparisons. Intervals apply to measurable pairs.",
        "bootstrap": {
            "replicates": N_BOOT,
            "seed": SEED,
            "interval": "percentile 95% inclusive",
        },
        "source_sha256": PINS,
        "cohorts": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_root", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Write anonymous results to a new file. Default verifies the published table.",
    )
    args = parser.parse_args()
    report = analyze(
        *(read_lines(args.formal_root / name, pin) for name, pin in PINS.items())
    )
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(
                json.dumps(
                    report,
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                    allow_nan=False,
                )
                + "\n"
            )
    elif json.loads(TABLE.read_bytes()) != report:
        raise ValueError("Paired resource table differs from the sealed data")
    print("Verified paired executor time and separate input/output token differences.")
