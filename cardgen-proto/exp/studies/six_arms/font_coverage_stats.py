"""Joint diagnostics for Web overflow, declared minimum font size, and A4a coverage."""

from collections import Counter
from itertools import product
from math import isfinite

from six_arms.composite_cost_stats import ARMS, PAIRS, PHASES

LINES = (10, 12)
DIRECTIONS = ("decreased", "equal", "increased")


def _direction(a, b):
    return "increased" if b > a else "decreased" if b < a else "equal"


def _validate(row):
    present, font, edge = row["has_artifact"], row["display_min"], row["edge_ok"]
    if type(present) is not bool or (edge is not None and type(edge) is not bool):
        raise ValueError("Expected boolean artifact presence and nullable Web geometry")
    if font is not None and (
        type(font) not in (int, float) or not isfinite(font) or font <= 0 or not present
    ):
        raise ValueError("Invalid declared minimum font")
    observed = row.get("known_min")
    if observed is not None and (
        type(observed) not in (int, float)
        or not isfinite(observed)
        or observed <= 0
        or not present
        or (font is not None and observed != font)
    ):
        raise ValueError(
            "Invalid partial minimum or conflict with the complete font evidence"
        )
    h, n = row["a4_hits"], row["a4_total"]
    if any(v is not None and (type(v) is not int or v < 0) for v in (h, n)):
        raise ValueError("Invalid reference coverage counts")
    if h is not None and (n is None or h > n):
        raise ValueError("Reference hits exceed the known denominator")
    status = row.get("a4_status", row.get("a4a_status"))
    if status == "measured" and (not present or h is None or not n):
        raise ValueError(
            "A measured coverage fraction needs an artifact and a positive denominator"
        )
    if status == "no_artifact" and present:
        raise ValueError("Conflicting artifact presence")
    if status not in (
        None,
        "measured",
        "no_artifact",
        "empty_reference",
        "missing_reference",
        "unresolved_text",
    ):
        raise ValueError("Unknown reference coverage status")
    if present and h is not None and n and status not in (None, "measured"):
        raise ValueError("Coverage fraction conflicts with its status")
    if not present and (edge is True or (h is not None and h > 0)):
        raise ValueError(
            "An absent artifact cannot have observed coverage or passing geometry"
        )


def _coverage(row):
    """A nonempty observed reference fraction; a missing delivery has no observed card."""
    if row["has_artifact"] and row["a4_hits"] is not None and row["a4_total"]:
        return row["a4_hits"], row["a4_total"]
    return None


def _checks(rows, line):
    states = Counter()
    failed = Counter()
    dimensions = {k: Counter() for k in ("A2", "A3", "A4a")}
    for row in rows:
        if not row["has_artifact"]:
            states["no_artifact"] += 1
            continue
        frac = _coverage(row)
        terms = {
            "A2": row["edge_ok"],
            "A3": row["display_min"] >= line
            if row["display_min"] is not None
            else False
            if row.get("known_min") is not None and row["known_min"] < line
            else None,
            "A4a": None if frac is None else 100 * frac[0] >= 80 * frac[1],
        }
        for name, value in terms.items():
            dimensions[name][
                "unknown" if value is None else "pass" if value else "fail"
            ] += 1
        incomplete = None in terms.values() or row["display_min"] is None
        states["all_three_thresholds_decided"] += None not in terms.values()
        known_failures = [k for k, v in terms.items() if v is False]
        if known_failures:
            failed["+".join(known_failures)] += 1
            states["partial_fail" if incomplete else "complete_fail"] += 1
        else:
            states["unresolved" if incomplete else "complete_pass"] += 1
    return {
        "assigned": len(rows),
        "joint_states": {
            k: states[k]
            for k in (
                "complete_pass",
                "complete_fail",
                "partial_fail",
                "unresolved",
                "no_artifact",
            )
        },
        "all_three_measured": states["complete_pass"] + states["complete_fail"],
        "all_three_thresholds_decided": states["all_three_thresholds_decided"],
        "assigned_pass_count_bounds": [
            states["complete_pass"],
            states["complete_pass"] + states["unresolved"],
        ],
        "dimension_counts_among_delivered": {
            k: {v: c[v] for v in ("pass", "fail", "unknown")}
            for k, c in dimensions.items()
        },
        "known_failed_dimensions_among_delivered": dict(sorted(failed.items())),
    }


def _compare(pairs, *, stages):
    counts = Counter()
    cells = Counter()
    higher_font = Counter()
    for left, right in pairs:
        counts["assigned"] += 1
        if not (left["has_artifact"] and right["has_artifact"]):
            continue
        counts["both_artifacts"] += 1
        a, b = _coverage(left), _coverage(right)
        if a is None or b is None:
            continue
        counts["both_artifacts_and_coverage"] += 1
        ca, cb = a[0] * b[1], b[0] * a[1]
        if ca == cb:
            counts["equal_coverage"] += 1
        fa, fb = left["display_min"], right["display_min"]
        if fa is None or fb is None:
            counts["missing_font_with_paired_coverage"] += 1
            if ca != cb:
                higher_font["unknown"] += 1
            continue
        counts["both_fonts_and_coverage"] += 1
        cells[_direction(ca, cb), _direction(fa, fb)] += 1
        if ca != cb:
            lower, higher = (fa, fb) if ca < cb else (fb, fa)
            higher_font[_direction(lower, higher)] += 1
    out = {
        k: counts[k]
        for k in (
            "assigned",
            "both_artifacts",
            "both_artifacts_and_coverage",
            "both_fonts_and_coverage",
            "missing_font_with_paired_coverage",
        )
    }
    if stages:
        out["rows_coverage_change_columns_font_change"] = {
            c: {f: cells[c, f] for f in DIRECTIONS} for c in DIRECTIONS
        }
    else:
        out["equal_coverage_including_missing_font"] = counts["equal_coverage"]
        out["minimum_font_on_higher_coverage_side"] = {
            "smaller": higher_font["decreased"],
            "equal": higher_font["equal"],
            "larger": higher_font["increased"],
            "unknown": higher_font["unknown"],
        }
    return out


def summarize(rows, *, expected_tasks=None):
    """One row per task × arm × checkpoint. Publish counts only."""
    grid, design, reference = {}, {}, {}
    for row in rows:
        task, family, arm, phase, size = (
            row[k] for k in ("task", "family", "arm", "phase", "layout_size")
        )
        if any(not isinstance(v, str) or not v.strip() for v in (task, family, size)):
            raise ValueError("Missing task, family or declared layout size")
        if arm not in ARMS or phase not in PHASES or (task, arm, phase) in grid:
            raise ValueError("Duplicate or unexpected layout seat")
        if design.setdefault(task, (family, size)) != (family, size):
            raise ValueError("Inconsistent task family or canvas size")
        _validate(row)
        if reference.setdefault(task, row["a4_total"]) != row["a4_total"]:
            raise ValueError("The same task has different coverage denominators")
        grid[task, arm, phase] = row
    if not design or (expected_tasks is not None and len(design) != expected_tasks):
        raise ValueError("Expected the registered task count")
    if set(grid) != set(product(design, ARMS, PHASES)):
        raise ValueError("Incomplete layout measurement grid")
    phases = {}
    for p in PHASES:
        phases[p] = {
            "arms": {
                a: {
                    str(line): _checks([grid[t, a, p] for t in design], line)
                    for line in LINES
                }
                for a in ARMS
            },
            "paired": {
                f"{r}_vs_{l}": _compare(
                    ((grid[t, l, p], grid[t, r, p]) for t in design), stages=False
                )
                for l, r in PAIRS
            },
        }
    return {
        "tasks": len(design),
        "task_counts_by_layout_size": dict(
            sorted(Counter(s for _, s in design.values()).items())
        ),
        "basis": (
            "A2 is measured Web geometry; A3 is the declared font minimum of all display Text and Button "
            "nodes; A4a requires reference-value coverage of at least 80%. At full assignment an absent card "
            "fails delivery. A partially observed font set can establish a threshold failure as soon as "
            "one known size is below that threshold. In a present card, an observed failed condition decides the conjunction. "
            "Joint partial failures only identify observed failing dimensions. Cross-arm and before/after "
            "comparisons include the same tasks with two artifacts and observed coverage at both ends. "
            "The before/after matrix additionally requires two measured minimum font sizes."
        ),
        "phases": phases,
        "within_arm_first_to_final": {
            a: _compare(
                ((grid[t, a, PHASES[0]], grid[t, a, PHASES[1]]) for t in design),
                stages=True,
            )
            for a in ARMS
        },
    }
