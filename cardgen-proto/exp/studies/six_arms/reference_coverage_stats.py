"""A4a alone, from existing per-seat evidence at the two frozen checkpoints."""

from collections import Counter, defaultdict
from itertools import product
from math import fsum

from six_arms.composite_cost_stats import ARMS, PHASES, THRESHOLDS


def _check_coverage(row):
    status, hits, total = (row[k] for k in ("a4a_status", "a4a_hits", "a4a_total"))
    if (
        status in ("missing_reference", "empty_reference")
        and "absence_reason" not in row
    ):
        raise ValueError(
            "A missing or empty reference requires a separate artifact presence record"
        )
    reason = row.get("absence_reason")
    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
        raise ValueError("Invalid artifact absence reason")
    if any(v is not None and (type(v) is not int or v < 0) for v in (hits, total)):
        raise ValueError("A4a counts must be nonnegative integers or null")
    if hits is not None and (total is None or hits > total):
        raise ValueError("Invalid A4a fraction")
    if status == "measured":
        valid = bool(total) and hits is not None and row.get("absence_reason") is None
    elif status == "no_artifact":
        valid = hits == 0 and total is not None
    elif status == "empty_reference":
        valid = total == 0 and hits is None
    elif status == "missing_reference":
        valid = total is None and hits is None
    elif status == "unresolved_text":
        valid = bool(total) and hits is None and row.get("absence_reason") is None
    else:
        raise ValueError("Unknown A4a evidence status")
    if not valid:
        raise ValueError(
            "A4a evidence status conflicts with counts or artifact absence"
        )


def _arm(rows):
    measured = []
    no_artifact = Counter()
    unknown = Counter()
    unknown_fact_slots = 0
    total_facts = 0
    missing_denominators = 0
    for row in rows:
        status, total = row["a4a_status"], row["a4a_total"]
        if total is None:
            missing_denominators += 1
        else:
            total_facts += total
        reason = row.get("absence_reason")
        if reason is not None or status == "no_artifact":
            no_artifact[reason or "unspecified"] += 1
        elif status == "measured":
            measured.append((row["a4a_hits"], total))
        else:
            unknown[status] += 1
            if total is not None:
                unknown_fact_slots += total

    count, assigned, unassessed = len(measured), len(rows), sum(unknown.values())
    hits = sum(h for h, _ in measured)
    measured_facts = sum(n for _, n in measured)
    fractions = fsum(h / n for h, n in measured)
    passes = {str(p): sum(100 * h >= p * n for h, n in measured) for p in THRESHOLDS}
    all_thresholds = {}
    for p, lo in passes.items():
        hi = lo + unassessed
        all_thresholds[p] = {
            "known_pass": lo,
            "known_fail": assigned - hi,
            "unknown": unassessed,
            "pass_count_bounds": [lo, hi],
            "pass_rate_bounds": [lo / assigned, hi / assigned],
        }
    return {
        "assigned": assigned,
        "emitted_measured": {
            "cards": count,
            "hits": hits,
            "total_facts": measured_facts,
            "micro_mean": hits / measured_facts if measured_facts else None,
            "macro_mean": fractions / count if count else None,
            "threshold_pass_counts": passes,
        },
        "no_artifact": sum(no_artifact.values()),
        "no_artifact_by_reason": dict(sorted(no_artifact.items())),
        "emitted_unknown": unassessed,
        "emitted_unknown_by_reason": dict(sorted(unknown.items())),
        "all_assigned": {
            "thresholds": all_thresholds,
            "macro_score_bounds": [
                fractions / assigned,
                (fractions + unassessed) / assigned,
            ],
            "missing_fact_denominators": missing_denominators,
            "known_total_facts": total_facts,
            "micro_mean_bounds_if_denominator_complete": (
                [hits / total_facts, (hits + unknown_fact_slots) / total_facts]
                if not missing_denominators and total_facts
                else None
            ),
        },
    }


def a4a_report(rows):
    """Each task must occur once for every arm and phase. No identifiers are emitted."""
    seen, totals, groups = set(), {}, defaultdict(list)
    for row in rows:
        task, arm, phase = (row[k] for k in ("task", "arm", "phase"))
        if (
            not isinstance(task, str)
            or not task.strip()
            or arm not in ARMS
            or phase not in PHASES
        ):
            raise ValueError("Invalid task, arm or checkpoint")
        key = (task, arm, phase)
        if key in seen:
            raise ValueError("Duplicate coverage seat")
        seen.add(key)
        _check_coverage(row)
        if totals.setdefault(task, row["a4a_total"]) != row["a4a_total"]:
            raise ValueError(
                "Task reference denominator differs among arms or checkpoints"
            )
        groups[phase, arm].append(row)
    if not seen or seen != set(product(totals, ARMS, PHASES)):
        raise ValueError("Expected a complete task-by-arm-by-checkpoint design")
    return {
        "tasks": len(totals),
        "basis": (
            "A4a reference-value coverage. Emitted, measurable cards supply the observed means. "
            "On all assigned seats an absent artifact contributes zero delivery, and a present artifact "
            "with an unknown score contributes [0,1] to the macro-score and threshold bounds. "
            "The micro mean weights individual reference facts; a known empty reference contributes "
            "no facts. An unknown reference size or zero total makes the full micro bound unavailable."
        ),
        "phases": {p: {a: _arm(groups[p, a]) for a in ARMS} for p in PHASES},
    }
