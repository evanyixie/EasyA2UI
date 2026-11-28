"""Paper A5. Summarize source support on emitted cards with observable numeric fragments."""

from collections import Counter, defaultdict
from fractions import Fraction
from itertools import product
from random import Random
from statistics import quantiles

from fixed_layout.paired_analysis import N_BOOT, SEED
from six_arms.composite_cost_stats import ARMS, PAIRS, PHASES

STATES = (
    "measured",
    "empty_data",
    "no_artifact",
    "unresolved_text",
    "missing_reference",
)
SOURCES = ("fact_only_supported", "query_only_supported", "both_supported")
COUNTS = (
    "total",
    "supported",
    "strict_supported",
    "snapshot_supported_extra",
    *SOURCES,
)
RULES = ("original", "strict", "original_plus_snapshot")


def _validate(metrics):
    state = metrics["status"]
    if state not in STATES:
        raise ValueError("Unknown numeric-evidence status")
    values = [metrics[k] for k in COUNTS]
    if any(v is not None and (type(v) is not int or v < 0) for v in values):
        raise ValueError("Numeric-evidence counts must be nonnegative integers or null")
    total, supported, strict, extra, *source_counts = values
    if state == "measured":
        valid = (
            None not in values
            and total > 0
            and supported + extra <= total
            and strict <= total
            and sum(source_counts) == supported
        )
    elif state == "empty_data":
        valid = all(v == 0 for v in values)
    elif state == "missing_reference":
        valid = (total is None or total > 0) and all(v is None for v in values[1:])
    else:
        valid = all(v is None for v in values)
    if not valid:
        raise ValueError(
            "Numeric-evidence counts contradict their status or source attribution"
        )


def _counts(metrics):
    return (
        metrics["supported"],
        metrics["strict_supported"],
        metrics["supported"] + metrics["snapshot_supported_extra"],
    )


def arm_summary(metrics_list):
    """Summarize one population of numeric-evidence records, including excluded cards."""
    metrics = list(metrics_list)
    for m in metrics:
        _validate(m)
    counts = Counter(m["status"] for m in metrics)
    usable = [m for m in metrics if m["status"] == "measured"]
    total = sum(m["total"] for m in usable)
    numerators = [_counts(m) for m in usable]
    rules = {}
    for i, rule in enumerate(RULES):
        hits = [n[i] for n in numerators]
        ratios = [Fraction(h, m["total"]) for h, m in zip(hits, usable, strict=True)]
        rules[rule] = {
            "supported_fragments": sum(hits),
            "unsupported_fragments": total - sum(hits),
            "micro_mean": sum(hits) / total if total else None,
            "macro_mean": float(sum(ratios) / len(ratios)) if ratios else None,
            "cards_with_no_supported_fragments": ratios.count(0),
            "cards_with_all_fragments_supported": ratios.count(1),
        }
    return {
        "assigned_cards": len(metrics),
        "measured_cards": len(usable),
        "excluded_cards": len(metrics) - len(usable),
        "status_counts": {s: counts[s] for s in STATES},
        "total_measured_fragments": total,
        "original_source_fragments": {k: sum(m[k] for m in usable) for k in SOURCES},
        "cards_with_query_only_support": sum(
            m["query_only_supported"] > 0 for m in usable
        ),
        "snapshot_supported_extra": sum(m["snapshot_supported_extra"] for m in usable),
        "cards_with_snapshot_extra": sum(
            m["snapshot_supported_extra"] > 0 for m in usable
        ),
        "support": rules,
    }


def _paired_estimate(values):
    """Equal weight per task. Draw whole families with replacement, preserving pair identities."""
    left = sum((l for _, l, _ in values), Fraction(0))
    right = sum((r for _, _, r in values), Fraction(0))
    n = len(values)
    groups = defaultdict(list)
    wins = Counter()
    for family, l, r in values:
        groups[family].append(r - l)
        wins["right" if r > l else "left" if l > r else "tie"] += 1
    result = {
        "left_macro_mean": float(left / n) if n else None,
        "right_macro_mean": float(right / n) if n else None,
        "right_minus_left_macro_difference": float((right - left) / n) if n else None,
        "wins": {label: wins[label] for label in ("left", "right", "tie")},
        "paired_family_percentile_ci95": None,
    }
    if len(groups) < 2:
        result["interval_status"] = "fewer_than_two_measured_families"
        return result
    clusters = [(sum(groups[f]), len(groups[f])) for f in sorted(groups)]
    if len({s / m for s, m in clusters}) == 1:
        result["interval_status"] = "no_between_family_mean_variation"
        return result
    # Point estimates and win/tie decisions above use exact fractions. Floating-point
    # group totals avoid doing arbitrary-precision arithmetic 10,000 times per family.
    clusters = [(float(s), m) for s, m in clusters]
    rng = Random(SEED)
    estimates = []
    for _ in range(N_BOOT):
        draw = rng.choices(clusters, k=len(clusters))
        estimates.append(sum(s for s, _ in draw) / sum(m for _, m in draw))
    q = quantiles(estimates, n=1000, method="inclusive")
    result["paired_family_percentile_ci95"] = [q[24], q[974]]
    result["interval_status"] = "measured_pairs_only"
    return result


def _pair(grid, families, phase, left_arm, right_arm):
    values = {rule: [] for rule in RULES}
    eligibility = Counter()
    paired_families = set()
    for task, family in families.items():
        l, r = grid[task, left_arm, phase], grid[task, right_arm, phase]
        measured = l["status"] == "measured", r["status"] == "measured"
        eligibility[measured] += 1
        if not all(measured):
            continue
        paired_families.add(family)
        for rule, lh, rh in zip(RULES, _counts(l), _counts(r), strict=True):
            values[rule].append(
                (family, Fraction(lh, l["total"]), Fraction(rh, r["total"]))
            )
    return {
        "left_arm": left_arm,
        "right_arm": right_arm,
        "assigned_pairs": len(families),
        "measured_pairs": eligibility[True, True],
        "left_only_measured": eligibility[True, False],
        "right_only_measured": eligibility[False, True],
        "neither_measured": eligibility[False, False],
        "families_with_measured_pairs": len(paired_families),
        "support": {rule: _paired_estimate(v) for rule, v in values.items()},
    }


def _first_to_final(grid, families, arm):
    states = Counter()
    scores = []
    count_changes = []
    for task, family in families.items():
        first, final = (grid[task, arm, phase] for phase in PHASES)
        pair = first["status"], final["status"]
        states[pair] += 1
        if pair != ("measured", "measured"):
            continue
        scores.append(
            (
                family,
                Fraction(first["supported"], first["total"]),
                Fraction(final["supported"], final["total"]),
            )
        )
        count_changes.append(final["total"] - first["total"])
    estimate = _paired_estimate(scores)
    n = len(scores)
    return {
        "assigned": len(families),
        "both_measured": n,
        "rows_first_columns_final": {
            first: {final: states[first, final] for final in STATES} for first in STATES
        },
        "original_support": {
            "first_macro_mean": estimate["left_macro_mean"],
            "final_macro_mean": estimate["right_macro_mean"],
            "mean_final_minus_first": estimate["right_minus_left_macro_difference"],
            "increased": estimate["wins"]["right"],
            "unchanged": estimate["wins"]["tie"],
            "decreased": estimate["wins"]["left"],
            "paired_family_percentile_ci95": estimate["paired_family_percentile_ci95"],
            "interval_status": estimate["interval_status"],
        },
        "fragment_count": {
            "mean_final_minus_first": sum(count_changes) / n if n else None,
            "increased": sum(d > 0 for d in count_changes),
            "unchanged": count_changes.count(0),
            "decreased": sum(d < 0 for d in count_changes),
        },
    }


def summary(rows, *, expected_tasks=None):
    """Accept the frozen complete grid. No task, family, fragment or text is emitted."""
    grid, families = {}, {}
    for row in rows:
        task, family, arm, phase = (row[k] for k in ("task", "family", "arm", "phase"))
        if any(not isinstance(v, str) or not v.strip() for v in (task, family)):
            raise ValueError("Missing task or family")
        key = task, arm, phase
        if arm not in ARMS or phase not in PHASES or key in grid:
            raise ValueError("Duplicate or invalid numeric-evidence seat")
        if families.setdefault(task, family) != family:
            raise ValueError("Task has different families across seats")
        grid[key] = row["metrics"]
    if not families or (expected_tasks is not None and len(families) != expected_tasks):
        raise ValueError("Expected the registered task count")
    if set(grid) != set(product(families, ARMS, PHASES)):
        raise ValueError("Expected all six arms and both checkpoints for every task")
    phases = {}
    for phase in PHASES:
        phases[phase] = {
            "arms": {a: arm_summary(grid[t, a, phase] for t in families) for a in ARMS},
            "paired": {
                f"{r}_minus_{l}": _pair(grid, families, phase, l, r) for l, r in PAIRS
            },
        }
    return {
        "assigned_tasks": len(families),
        "bootstrap": {
            "seed": SEED,
            "replicates": N_BOOT,
            "interval": "inclusive percentile 95%",
        },
        "basis": (
            "C-01 and C-03 exclude missing artifacts and empty numeric data from precision. "
            "Arm micro means pool measured fragments. Macro means weight each measured card equally. "
            "The original rule tests reference or query support; strict uses its own recorded counts. "
            "The sample diagnostic adds strict snapshot matches among originally unsupported fragments. "
            "Pairwise differences subtract the left arm from the right on tasks with both cards measurable. "
            "The interval resamples entire families and uses the task-weighted mean paired difference. "
            "Within-arm changes pair the same task at the first and final checkpoints. Only pairs "
            "with measured data at both checkpoints enter score and fragment-count changes."
        ),
        "phases": phases,
        "within_arm_first_to_final": {
            a: _first_to_final(grid, families, a) for a in ARMS
        },
    }
