"""Aggregate A2 browser measurements at the task level (paper §4.3–4.4)."""

from collections import Counter, defaultdict
from itertools import product
from statistics import median

from six_arms.paired_resource_differences import ARMS, N_BOOT, SEED, describe

PHASES = ("first", "final")
STATUSES = ("measured", "missing", "unsupported", "browser_error")
METRICS = ("overflow_px", "above4_nodes")


def validate_row(row):
    """Diagnostic counts are integers because the browser rounds each edge in CSS px."""
    if (
        row["phase"] not in PHASES
        or row["arm"] not in ARMS
        or row["status"] not in STATUSES
    ):
        raise ValueError("Unknown phase, arm or measurement status")
    if not all(isinstance(row[k], str) and row[k].strip() for k in ("task", "family")):
        raise ValueError("Missing task or family")
    if row["status"] != "measured":
        if any(row.get(k) is not None for k in METRICS):
            raise ValueError("Unmeasured seats cannot have overflow measurements")
        return
    px, above4, text = (row[k] for k in (*METRICS, "text_nodes"))
    if any(type(v) is not int or v < 0 for v in (px, above4, text)):
        raise ValueError("Expected nonnegative integer pixel and node counts")
    if above4 > text or px < 5 * above4 or (text == 0 and px != 0):
        raise ValueError("Inconsistent measured overflow quantities")


def eligible(row):
    return row["status"] == "measured" and row["text_nodes"] > 0


def summarize(rows):
    counts = Counter(r["status"] for r in rows)
    text = [r for r in rows if eligible(r)]
    return {
        "assigned": len(rows),
        "statuses": {s: counts[s] for s in STATUSES},
        "measured_zero_text_cards": counts["measured"] - len(text),
        "measured_cards_with_text": len(text),
        "text_nodes": sum(r["text_nodes"] for r in text),
        "cards_with_any_overflow": sum(r["overflow_px"] > 0 for r in text),
        "cards_with_any_node_above4": sum(r["above4_nodes"] > 0 for r in text),
        "total_overflow_px": sum(r["overflow_px"] for r in text) if text else None,
        "total_above4_nodes": sum(r["above4_nodes"] for r in text) if text else None,
        "median_overflow_px_per_card": median(r["overflow_px"] for r in text)
        if text
        else None,
        "median_above4_nodes_per_card": median(r["above4_nodes"] for r in text)
        if text
        else None,
    }


def paired(grid, tasks, phase, left, right):
    differences = {name: defaultdict(list) for name in METRICS}
    availability = Counter()
    for task in tasks:
        a, b = grid[task, phase, left], grid[task, phase, right]
        ka, kb = eligible(a), eligible(b)
        availability[ka, kb] += 1
        if ka and kb:
            for name in METRICS:
                differences[name][a["family"]].append(a[name] - b[name])
    return {
        "available_both": availability[True, True],
        "available_left_only": availability[True, False],
        "available_right_only": availability[False, True],
        "available_neither": availability[False, False],
        **{
            name: describe(families, len(tasks), 1)
            for name, families in differences.items()
        },
    }


def build_report(rows):
    """Expect a complete first/final × six-arm roster with explicit unknown states."""
    grid = {}
    families = {}
    for row in rows:
        validate_row(row)
        task = row["task"]
        key = (task, row["phase"], row["arm"])
        if key in grid:
            raise ValueError("Duplicate checkpoint seat")
        if families.setdefault(task, row["family"]) != row["family"]:
            raise ValueError("Inconsistent task family")
        grid[key] = row
    tasks = sorted(families)
    if not tasks or set(grid) != set(product(tasks, PHASES, ARMS)):
        raise ValueError("Missing assigned seats; supply explicit missing statuses")
    return {
        "tasks": len(tasks),
        "families": len(set(families.values())),
        "assigned_per_phase": len(tasks) * len(ARMS),
        "scope": "Edge/Blink CSS text-box overflow relative to the artifact's declared root rectangle. Measured zero-text cards "
        "are counted separately and excluded from overflow comparisons. No imputation for missing artifacts, "
        "unsupported rendering or browser errors. First and final checkpoints remain separate.",
        "units": "overflow_px sums rounded outward CSS pixels across text nodes and edges. above4_nodes counts "
        "each text node once if at least one rounded edge strictly exceeds four CSS pixels.",
        "paired_method": "Negative left-minus-right favors the first arm on overflow only. The median of "
        "within-task differences is estimated on common measurable text-bearing pairs. "
        "The percentile interval resamples whole families. Two-sided signed-rank p values "
        "are unadjusted and descriptive; family sensitivity uses one median per family.",
        "bootstrap": {
            "replicates": N_BOOT,
            "seed": SEED,
            "interval": "percentile 95% inclusive",
        },
        "by_phase_arm": {
            p: {a: summarize([grid[t, p, a] for t in tasks]) for a in ARMS}
            for p in PHASES
        },
        "paired": {
            p: {
                f"{a}_minus_{b}": paired(grid, tasks, p, a, b)
                for a, b in (("L5", "L4"), ("L6", "L5"))
            }
            for p in PHASES
        },
    }
