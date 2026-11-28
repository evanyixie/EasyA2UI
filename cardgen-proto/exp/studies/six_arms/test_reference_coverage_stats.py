from itertools import product
from pathlib import Path

import pytest


@pytest.fixture
def stats(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import reference_coverage_stats

    return reference_coverage_stats


def grid(stats, evidence):
    return [
        {
            "task": f"task-{i}",
            "arm": a,
            "phase": p,
            "a4a_status": status,
            "a4a_hits": hits,
            "a4a_total": total,
            "absence_reason": reason,
        }
        for (i, (status, hits, total, reason)), a, p in product(
            enumerate(evidence), stats.ARMS, stats.PHASES
        )
    ]


def test_observed_means_and_full_assignment_bounds(stats):
    rows = grid(
        stats,
        [
            ("measured", 1, 1, None),
            ("measured", 3, 5, None),
            ("no_artifact", 0, 2, "transport_failed"),
            ("unresolved_text", None, 2, None),
            ("empty_reference", None, 0, None),
            ("empty_reference", None, 0, "stage_rejected"),
        ],
    )
    one = stats.a4a_report(rows)["phases"]["raw_first"]["L1"]
    assert one["emitted_measured"] == {
        "cards": 2,
        "hits": 4,
        "total_facts": 6,
        "micro_mean": 4 / 6,
        "macro_mean": 0.8,
        "threshold_pass_counts": {"60": 2, "80": 1, "100": 1},
    }
    assert one["no_artifact_by_reason"] == {"stage_rejected": 1, "transport_failed": 1}
    assert one["emitted_unknown_by_reason"] == {
        "empty_reference": 1,
        "unresolved_text": 1,
    }
    all_rows = one["all_assigned"]
    assert all_rows["thresholds"]["80"] == {
        "known_pass": 1,
        "known_fail": 3,
        "unknown": 2,
        "pass_count_bounds": [1, 3],
        "pass_rate_bounds": [1 / 6, 0.5],
    }
    assert all_rows["macro_score_bounds"] == pytest.approx([1.6 / 6, 3.6 / 6])
    assert all_rows["micro_mean_bounds_if_denominator_complete"] == [0.4, 0.6]


def test_absent_and_unmeasurable_references(stats):
    rows = grid(
        stats,
        [
            ("missing_reference", None, None, None),
            ("missing_reference", None, None, "stage_rejected"),
        ],
    )
    one = stats.a4a_report(rows)["phases"]["after_common_repair"]["L3"]
    assert one["emitted_measured"]["micro_mean"] is None
    assert one["emitted_measured"]["macro_mean"] is None
    assert one["all_assigned"]["missing_fact_denominators"] == 2
    assert one["all_assigned"]["micro_mean_bounds_if_denominator_complete"] is None
    assert one["all_assigned"]["thresholds"]["60"]["pass_count_bounds"] == [0, 1]
    assert one["emitted_unknown"] == one["no_artifact"] == 1
    zero = stats.a4a_report(grid(stats, [("empty_reference", None, 0, None)]))
    assert (
        zero["phases"]["raw_first"]["L6"]["all_assigned"][
            "micro_mean_bounds_if_denominator_complete"
        ]
        is None
    )


def test_checkpoint_separation_and_unrounded_threshold(stats):
    rows = grid(stats, [("measured", 1999, 2500, None)])
    for row in rows:
        if row["phase"] == "after_common_repair" and row["arm"] == "L4":
            row["a4a_hits"] = 2000
    report = stats.a4a_report(reversed(rows))
    assert (
        report["phases"]["after_common_repair"]["L4"]["emitted_measured"][
            "threshold_pass_counts"
        ]["80"]
        == 1
    )
    assert (
        report["phases"]["raw_first"]["L4"]["emitted_measured"][
            "threshold_pass_counts"
        ]["80"]
        == 0
    )
    assert (
        report["phases"]["after_common_repair"]["L5"]["emitted_measured"][
            "threshold_pass_counts"
        ]["80"]
        == 0
    )


@pytest.mark.parametrize(
    "mutation",
    [
        {"a4a_hits": True},
        {"a4a_hits": 2},
        {"a4a_status": "unresolved_text"},
        {"a4a_status": "not_a_state"},
        {"absence_reason": "transport_failed"},
        {"a4a_total": 2},
        {"a4a_total": None},
        {"task": ""},
        {"phase": "other"},
    ],
)
def test_inconsistent_counts_or_evidence_rejected(stats, mutation):
    rows = grid(stats, [("measured", 1, 1, None)])
    rows[0].update(mutation)
    with pytest.raises(ValueError):
        stats.a4a_report(rows)


def test_incomplete_or_repeated_design_rejected(stats):
    rows = grid(stats, [("measured", 0, 1, None)])
    for invalid in ([], rows[1:], [*rows, rows[0]]):
        with pytest.raises(ValueError):
            stats.a4a_report(invalid)


def test_unknown_reference_needs_an_independent_presence_record(stats):
    rows = grid(stats, [("missing_reference", None, None, None)])
    del rows[0]["absence_reason"]
    with pytest.raises(ValueError, match="presence"):
        stats.a4a_report(rows)
