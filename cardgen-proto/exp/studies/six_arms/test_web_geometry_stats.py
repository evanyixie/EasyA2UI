from itertools import product
from pathlib import Path

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import web_geometry_stats

    return web_geometry_stats


def seats(study, cases):
    return {
        (t, p, a): {
            "task": t,
            "family": family,
            "phase": p,
            "arm": a,
            "status": "missing",
            "overflow_px": None,
            "above4_nodes": None,
            "text_nodes": None,
        }
        for (t, family), p, a in product(cases, study.PHASES, study.ARMS)
    }


def measured(row, px=0, above=0, text=1):
    row.update(status="measured", overflow_px=px, above4_nodes=above, text_nodes=text)


def test_matched_pairs_exclude_unknowns_and_zero_text_by_phase(study):
    grid = seats(
        study, [(f"q{i}", "group" if i <= 2 else f"group{i}") for i in range(1, 6)]
    )
    measured(grid["q1", "first", "L4"], 10, 2, 2)
    measured(grid["q1", "first", "L5"], 4)
    measured(grid["q1", "first", "L6"], 7, 1)
    measured(grid["q2", "first", "L4"])
    measured(grid["q2", "first", "L5"], 8, 0)  # Two separate 4px edges may sum to 8.
    measured(grid["q3", "first", "L5"], text=0)
    measured(grid["q3", "first", "L4"], 5, 1)
    grid["q4", "first", "L5"]["status"] = "browser_error"
    grid["q5", "first", "L4"]["status"] = "unsupported"
    measured(grid["q5", "first", "L5"])
    measured(grid["q4", "final", "L4"], 10, 1)
    measured(grid["q4", "final", "L5"])

    report = study.build_report(grid.values())
    l5 = report["by_phase_arm"]["first"]["L5"]
    assert l5["assigned"] == 5 and l5["statuses"]["measured"] == 4
    assert l5["statuses"]["browser_error"] == l5["measured_zero_text_cards"] == 1
    assert l5["measured_cards_with_text"] == l5["text_nodes"] == 3
    assert l5["cards_with_any_overflow"] == 2 and l5["cards_with_any_node_above4"] == 0
    assert l5["total_overflow_px"] == 12 and l5["median_overflow_px_per_card"] == 4
    comparison = report["paired"]["first"]["L5_minus_L4"]
    assert [
        comparison[k]
        for k in (
            "available_both",
            "available_left_only",
            "available_right_only",
            "available_neither",
        )
    ] == [2, 1, 1, 1]
    px = comparison["overflow_px"]
    assert px["known_task_pairs"] == 2 and px["families_with_known_pairs"] == 1
    assert px["paired_median_difference"] == 1
    assert px["task_weighted_cluster_bootstrap_ci95"] == [1, 1]
    assert comparison["above4_nodes"]["paired_median_difference"] == -1
    assert (
        report["paired"]["final"]["L5_minus_L4"]["overflow_px"][
            "paired_median_difference"
        ]
        == -10
    )
    assert (
        report["paired"]["first"]["L6_minus_L5"]["overflow_px"][
            "paired_median_difference"
        ]
        == 3
    )
    assert report == study.build_report(reversed(list(grid.values())))


def test_absent_seat_is_not_an_observed_zero(study):
    grid = seats(study, [("t", "g")])
    report = study.build_report(grid.values())
    arm = report["by_phase_arm"]["first"]["L1"]
    assert arm["statuses"]["missing"] == 1
    assert arm["total_overflow_px"] is arm["median_overflow_px_per_card"] is None
    assert report["paired"]["first"]["L5_minus_L4"]["overflow_px"] == {
        "assigned": 1,
        "known_task_pairs": 0,
        "missing_task_pairs": 1,
    }
    with pytest.raises(ValueError, match="Duplicate"):
        study.build_report([*grid.values(), next(iter(grid.values()))])
    grid.pop(("t", "first", "L1"))
    with pytest.raises(ValueError, match="Missing assigned"):
        study.build_report(grid.values())


def test_inconsistent_counts_and_assignment_raise(study):
    grid = seats(study, [("t", "g")])
    row = grid["t", "final", "L1"]
    row["above4_nodes"] = 0
    with pytest.raises(ValueError, match="Unmeasured"):
        study.build_report(grid.values())
    for px, above, n in [(4, 1, 1), (12, 2, 1), (1, 0, 0), (True, 0, 1), (-1, 0, 1)]:
        measured(row, px, above, n)
        with pytest.raises(ValueError):
            study.build_report(grid.values())
    measured(row, 5, 1, 1)
    row["family"] = "other"
    with pytest.raises(ValueError, match="family"):
        study.build_report(grid.values())
