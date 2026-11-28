"""C-04/B4. Aggregate protocol, geometry and A4a evidence without an answer key."""

from collections import Counter
from itertools import product

from six_arms.technical_yield import ARMS

PHASES = ("raw_first", "after_common_repair")
THRESHOLDS = (60, 80, 100)
PAIRS = (("L4", "L5"), ("L5", "L6"))
STATES = ("pass", "fail", "unknown")


def validate(row):
    if row["arm"] not in ARMS or row["phase"] not in PHASES:
        raise ValueError("Unknown arm or phase")
    if not all(isinstance(row[k], str) and row[k].strip() for k in ("task", "family")):
        raise ValueError("Missing case or family")
    if any(
        row[k] is not None and type(row[k]) is not bool
        for k in ("protocol", "geometry")
    ):
        raise ValueError("Protocol and geometry must be true, false or null")
    if any(
        row[k] is not None and (type(row[k]) is not int or row[k] < 0)
        for k in ("a4a_hits", "a4a_total", "total_tokens")
    ):
        raise ValueError("Counts must be nonnegative integers or null")
    hits, total = row["a4a_hits"], row["a4a_total"]
    if hits is not None and total is not None and hits > total:
        raise ValueError("A4a hits exceed the reference count")
    subtotal = row.get("known_tokens")
    if subtotal is not None and (
        type(subtotal) is not int
        or subtotal < 0
        or (row["total_tokens"] is not None and subtotal != row["total_tokens"])
    ):
        raise ValueError("Invalid known token subtotal")


def qualifies(row, pct):
    """An observed failed condition decides the conjunction even if another is unknown."""
    hits, total = row["a4a_hits"], row["a4a_total"]
    coverage = None if hits is None or not total else 100 * hits >= pct * total
    checks = (row["protocol"], row["geometry"], coverage)
    if False in checks:
        return "fail"
    return "unknown" if None in checks else "pass"


def cost_bounds(known_tokens, unknown_meter, low, high):
    """Bounds conditional on at least one qualified card. A zero denominator is undefined."""
    lower = known_tokens / high if high else None
    upper = known_tokens / max(1, low) if high and not unknown_meter else None
    return {
        "exact_tokens_per_qualified": known_tokens / low
        if low and low == high and not unknown_meter
        else None,
        "lower_if_positive": lower,
        "upper_if_positive": upper,
        "zero_qualified_possible": low == 0,
        "positive_qualified_possible": high > 0,
    }


def arm_summary(rows, final):
    out = {
        "assigned": len(rows),
        "a4a": {
            "known_fraction": sum(
                r["a4a_hits"] is not None and bool(r["a4a_total"]) for r in rows
            ),
            "empty_reference": sum(r["a4a_total"] == 0 for r in rows),
            "missing_counts": sum(
                r["a4a_total"] is None or (r["a4a_total"] > 0 and r["a4a_hits"] is None)
                for r in rows
            ),
        },
        "thresholds": {},
    }
    if final:
        meters = [r["total_tokens"] for r in rows if r["total_tokens"] is not None]
        partial = [
            r["known_tokens"]
            for r in rows
            if r["total_tokens"] is None and r.get("known_tokens") is not None
        ]
        known_tokens = sum(meters) + sum(partial)
        unknown_meter = len(rows) - len(meters)
        out["metering"] = {
            "known_complete_seat_tokens": sum(meters),
            "reported_subtotals_on_incomplete_seats": sum(partial),
            "incomplete_seats_with_subtotal": len(partial),
            "known_accounted_tokens": known_tokens,
            "known_seats": len(meters),
            "missing_or_incomplete_seats": unknown_meter,
            "all_assigned_tokens": None if unknown_meter else known_tokens,
        }
    for pct in THRESHOLDS:
        counts = Counter(qualifies(r, pct) for r in rows)
        low = counts["pass"]
        high = low + counts["unknown"]
        record = {s: counts[s] for s in STATES}
        record["qualified_count_bounds"] = [low, high]
        if final:
            record["b4_tokens"] = cost_bounds(known_tokens, unknown_meter, low, high)
        out["thresholds"][str(pct)] = record
    return out


def paired_summary(left, right):
    result = {}
    for pct in THRESHOLDS:
        counts = Counter(
            (qualifies(a, pct), qualifies(b, pct))
            for a, b in zip(left, right, strict=True)
        )
        # Pointwise sharp count bounds with no assumption about unknown counterpart outcomes.
        low = sum(
            n * (int(r == "pass") - int(l != "fail")) for (l, r), n in counts.items()
        )
        high = sum(
            n * (int(r != "fail") - int(l == "pass")) for (l, r), n in counts.items()
        )
        result[str(pct)] = {
            "rows_left_columns_right": {
                l: {r: counts[l, r] for r in STATES} for l in STATES
            },
            "right_minus_left_qualified_count_bounds": [low, high],
        }
    return result


def panel(grid, families, tasks, arms, phase):
    by_arm = {a: [grid[t, a, phase] for t in tasks] for a in arms}
    return {
        "assigned_tasks": len(tasks),
        "distinct_families": len({families[t] for t in tasks}),
        "arms": {
            a: arm_summary(rows, phase == PHASES[1]) for a, rows in by_arm.items()
        },
        "paired": {
            f"{l}_{r}": paired_summary(by_arm[l], by_arm[r])
            for l, r in PAIRS
            if l in by_arm and r in by_arm
        },
    }


def summarize(rows, *, expected_tasks=None):
    """Rows have task/family/arm/phase, bool|null protocol/geometry and three nullable counts.

    total_tokens is the entire seat's meter, including unsuccessful work. Use null when
    any call is unmetered. Optional known_tokens is that seat's reported subtotal.
    Its numerator is used for the final phase only.
    """
    grid, families, reference_totals = {}, {}, {}
    for row in rows:
        validate(row)
        t, a, p = row["task"], row["arm"], row["phase"]
        if (t, a, p) in grid or families.setdefault(t, row["family"]) != row["family"]:
            raise ValueError("Duplicate seat or inconsistent family")
        if (
            row["a4a_total"] is not None
            and reference_totals.setdefault(t, row["a4a_total"]) != row["a4a_total"]
        ):
            raise ValueError("A4a reference count differs for the same task")
        grid[t, a, p] = row
    tasks = sorted(families)
    if (
        not tasks
        or (expected_tasks is not None and len(tasks) != expected_tasks)
        or set(grid) != set(product(tasks, ARMS, PHASES))
    ):
        raise ValueError("Expected complete, phase-matched six-arm assignments")
    first, final = PHASES
    panels = {"all_assigned": panel(grid, families, tasks, ARMS, final)}
    for name, arms in (
        ("six_arm_meter_complete", ARMS),
        ("L4_L5_meter_complete", PAIRS[0]),
        ("L5_L6_meter_complete", PAIRS[1]),
    ):
        eligible = [
            t
            for t in tasks
            if all(grid[t, a, final]["total_tokens"] is not None for a in arms)
        ]
        panels[name] = panel(grid, families, eligible, arms, final)
    return {
        "primary_threshold_percent": 80,
        "coverage_basis": "A4a only. A4b has no independently supplied must-show labels in this analysis.",
        "qualification": "Protocol passes AND measured geometry passes AND A4a hits / reference count reaches threshold. Empty references and missing counts make coverage unknown. A known failed condition settles a failure.",
        "cost": "Final spent tokens across all assigned seats, including failures, divided by qualified cards. The lower numerator includes fully metered seats and any known subtotals supplied for incomplete seats. Remaining unmetered cost is nonnegative and has no assumed upper bound. Conditional bounds require >=1 qualified card. No cost is defined for zero qualifying cards. No first-phase cost is estimated.",
        "phases": {
            first: {"all_assigned": panel(grid, families, tasks, ARMS, first)},
            final: panels,
        },
    }
