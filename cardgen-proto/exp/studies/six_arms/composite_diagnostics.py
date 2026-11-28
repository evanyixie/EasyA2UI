"""Explain final C-04 decisions and cross-tabulate independent Web text clipping."""

from collections import Counter
from itertools import product
from pathlib import Path

from six_arms import composite_cost_stats as stats
from six_arms.composite_inputs import edge_evidence
from six_arms.fixed_content_repeats import check

FINAL = "after_common_repair"
THRESHOLD = 80
CLIP = ("present", "absent", "unknown")
REASONS = (
    "no_artifact",
    "coverage_below_80",
    "frame_overflow",
    "protocol",
    "multiple_observed_failures",
    "indeterminate",
)


def coverage_state(row):
    # Use the same exact integer threshold and empty-reference convention as the main table.
    return stats.qualifies({**row, "protocol": True, "geometry": True}, THRESHOLD)


def clipping_signal(row, edge, measures):
    check(
        (row["task"], row["family"], row["arm"], "final")
        == tuple(edge[k] for k in ("task", "family", "arm", "phase")),
        "Wrong Edge seat",
    )
    sha = edge["artifact_sha256"]
    check(row["artifact_sha256"] == sha, "B4 and Edge artifact hashes differ")
    if edge["status"] == "missing":
        check(
            sha is None
            and "observation_key" not in edge
            and row["absence_reason"] is not None
            and row["geometry"] is None,
            "Missing artifact mismatch",
        )
        return "unknown"
    key = edge["observation_key"]
    check(
        sha and key in {f"2x2-{sha}", f"2x4-{sha}"} and row["absence_reason"] is None,
        "Mismatched artifact observation",
    )
    obs = measures[key]
    check(obs["key"] == key, "Wrong browser observation")
    if edge["status"] == "unsupported":
        check(
            obs["state"] == "unassessed" and row["geometry"] is None,
            "Inconsistent unsupported geometry",
        )
        return "unknown"
    n, clipped = edge["text_nodes"], obs["clipped_text_nodes"]
    check(
        edge["status"] == obs["state"] == "measured"
        and n == obs["expected_text_nodes"] == obs["measured_text_nodes"]
        and type(clipped) is int
        and 0 <= clipped <= n
        and obs["above4_nodes"] == edge["above4_nodes"]
        and row["geometry"] is (None if not n else edge["above4_nodes"] == 0),
        "Incomplete or inconsistent Edge observation",
    )
    if not n:
        return "unknown"
    return "present" if clipped else "absent"


def reason(row, coverage, decision):
    if row["absence_reason"] is not None:
        check(decision == "fail", "Unexpected primary decision for missing artifact")
        return "no_artifact"
    failed = [
        key
        for key, hit in (
            ("coverage_below_80", coverage == "fail"),
            ("frame_overflow", row["geometry"] is False),
            ("protocol", row["protocol"] is False),
        )
        if hit
    ]
    if not failed:
        check(decision == "unknown", "Expected a failed or unresolved opposite arm")
        return "indeterminate"
    check(decision == "fail", "Observed failure is inconsistent with primary decision")
    return failed[0] if len(failed) == 1 else "multiple_observed_failures"


def arm_panel(cases):
    counts = Counter((decision, clip) for row, decision, coverage, clip in cases)
    return {
        "assigned": len(cases),
        "both_decisions_known": sum(
            n for (d, c), n in counts.items() if d != "unknown" and c != "unknown"
        ),
        "qualified_by_horizontal_clip": {
            d: {c: counts[d, c] for c in CLIP} for d in stats.STATES
        },
    }


def pair_panel(left, right, tasks, grid):
    directions = {}
    available = Counter()
    both_emitted = 0
    for winner, other in ((left, right), (right, left)):
        counts, no_artifact, opposite_states = Counter(), Counter(), Counter()
        for task in tasks:
            _, winner_decision, _, _ = grid[task, winner]
            row, decision, coverage, _ = grid[task, other]
            if winner_decision == "pass" and decision != "pass":
                counts[reason(row, coverage, decision)] += 1
                opposite_states[decision] += 1
                if row["absence_reason"] is not None:
                    no_artifact[row["absence_reason"]] += 1
        directions[winner] = {
            "opposite_failed": opposite_states["fail"],
            "opposite_unknown": opposite_states["unknown"],
            "opposite_reason": {k: counts[k] for k in REASONS},
            "no_artifact_breakdown": dict(sorted(no_artifact.items())),
        }
    for t in tasks:
        a, b = grid[t, left], grid[t, right]
        if all(r[0]["absence_reason"] is None for r in (a, b)):
            both_emitted += 1
            if all(r[2] != "unknown" and r[0]["geometry"] is not None for r in (a, b)):
                available[a[1], b[1]] += 1
    return {
        "left": left,
        "right": right,
        "assigned_pairs": len(tasks),
        "only_one_confirmed_qualified": directions,
        "both_artifacts": both_emitted,
        "both_artifacts_and_assessable_coverage_geometry": {
            "pairs": available.total(),
            "left_vs_right": {
                a: {b: available[a, b] for b in stats.STATES} for a in stats.STATES
            },
            "left_pass": sum(n for (a, b), n in available.items() if a == "pass"),
            "right_pass": sum(n for (a, b), n in available.items() if b == "pass"),
        },
    }


def diagnose(rows, edges, measures):
    grid, families = {}, {}
    for row in rows:
        if row["phase"] != FINAL:
            continue
        stats.validate(row)
        t, a = row["task"], row["arm"]
        check(
            (t, a) not in grid
            and families.setdefault(t, row["family"]) == row["family"],
            "Duplicate or inconsistent B4 seat",
        )
        clip = clipping_signal(row, edges[t, a, "final"], measures)
        grid[t, a] = (row, stats.qualifies(row, THRESHOLD), coverage_state(row), clip)
    check(
        set(grid)
        == set(product(families, stats.ARMS))
        == {(t, a) for t, a, p in edges if p == "final"}
        and bool(grid),
        "Incomplete final grid",
    )
    return {
        "checkpoint": FINAL,
        "coverage_threshold_percent": THRESHOLD,
        "scope": "Horizontal clipping means at least one measured Web Text node exceeds its own box horizontally by >4 CSS px. Only Text nodes are measured. This secondary observation does not change C-04. An observed failure can coexist with an unmeasured condition. Opposite unknown and opposite fail are reported separately.",
        "arms": {a: arm_panel([grid[t, a] for t in families]) for a in stats.ARMS},
        "pairs": {f"{a}_{b}": pair_panel(a, b, families, grid) for a, b in stats.PAIRS},
    }


def diagnostic_report(rows, root):
    """Read only the publicly pinned Edge observation ledger; rows are the existing B4 receipts."""
    edges, measurements = edge_evidence(Path(root))
    return diagnose(rows, edges, measurements)
