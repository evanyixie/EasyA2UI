from itertools import product
from pathlib import Path

import pytest


@pytest.fixture
def stats(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import font_coverage_stats

    return font_coverage_stats


def grid(stats, n):
    return {
        (t, a, p): {
            "task": str(t),
            "family": str(t // 2),
            "layout_size": "2x2" if t % 2 else "2x4",
            "arm": a,
            "phase": p,
            "has_artifact": True,
            "a4_hits": 4,
            "a4_total": 5,
            "a4_status": "measured",
            "edge_ok": True,
            "display_min": 12,
        }
        for t, a, p in product(range(n), stats.ARMS, stats.PHASES)
    }


def test_joint_partial_proof_and_missing_delivery(stats):
    rows = grid(stats, 6)
    p = stats.PHASES[0]
    for t, change in enumerate(
        (
            {},
            {"display_min": None, "known_min": 11},
            {"display_min": None, "known_min": 9, "edge_ok": None},
            {"display_min": None, "known_min": 12},
            {"display_min": 9, "a4_hits": 3, "edge_ok": False},
            {
                "display_min": None,
                "edge_ok": False,
                "has_artifact": False,
                "a4_status": "no_artifact",
                "a4_hits": 0,
            },
        )
    ):
        rows[t, "L1", p].update(change)
    out = stats.summarize(rows.values(), expected_tasks=6)["phases"][p]["arms"]["L1"]
    assert out["12"]["joint_states"] == {
        "complete_pass": 1,
        "complete_fail": 1,
        "partial_fail": 2,
        "unresolved": 1,
        "no_artifact": 1,
    }
    assert out["12"]["all_three_measured"] == 2
    assert out["12"]["all_three_thresholds_decided"] == 3
    assert out["12"]["dimension_counts_among_delivered"]["A3"] == {
        "pass": 1,
        "fail": 3,
        "unknown": 1,
    }
    assert out["12"]["known_failed_dimensions_among_delivered"] == {
        "A3": 2,
        "A2+A3+A4a": 1,
    }
    assert out["12"]["assigned_pass_count_bounds"] == [1, 2]
    assert out["10"]["assigned_pass_count_bounds"] == [1, 3]


def test_tradeoff_direction_and_fractional_threshold_without_rounding(stats):
    rows = grid(stats, 6)
    final = stats.PHASES[1]
    for i, h, f in [
        (0, 5, 10),
        (1, 3, 10),
        (2, 5, 12),
        (3, 4, None),
        (4, 5, None),
        (5, 3, 14),
    ]:
        rows[i, "L5", final].update(a4_hits=h, display_min=f)
    out = stats.summarize(rows.values())
    pair = out["phases"][final]["paired"]["L5_vs_L4"]
    assert pair["both_artifacts_and_coverage"] == 6
    assert pair["both_fonts_and_coverage"] == 4
    assert pair["equal_coverage_including_missing_font"] == 1
    assert pair["minimum_font_on_higher_coverage_side"] == {
        "smaller": 2,
        "equal": 1,
        "larger": 1,
        "unknown": 1,
    }
    cell = out["within_arm_first_to_final"]["L5"][
        "rows_coverage_change_columns_font_change"
    ]
    assert cell["increased"] == {"increased": 0, "equal": 1, "decreased": 1}
    assert cell["decreased"] == {"increased": 1, "equal": 0, "decreased": 1}
    assert sum(sum(c.values()) for c in cell.values()) == 4
    exact = grid(stats, 1)
    for row in exact.values():
        row.update(a4_hits=1999, a4_total=2500)
    assert (
        stats.summarize(exact.values())["phases"][final]["arms"]["L5"]["12"][
            "joint_states"
        ]["complete_fail"]
        == 1
    )


def test_empty_reference_and_missing_font_cannot_pass(stats):
    rows = grid(stats, 1)
    for r in rows.values():
        r.update(
            a4_hits=None, a4_total=0, a4_status="empty_reference", display_min=None
        )
    out = stats.summarize(rows.values())
    assert out["within_arm_first_to_final"]["L2"]["both_artifacts_and_coverage"] == 0
    assert (
        out["phases"]["raw_first"]["arms"]["L2"]["10"]["joint_states"]["unresolved"]
        == 1
    )


@pytest.mark.parametrize(
    "bad",
    [
        {"display_min": False},
        {"display_min": float("nan")},
        {"known_min": 8},
        {"known_min": 0},
        {"edge_ok": "true"},
        {"a4_hits": 6},
        {"a4_hits": True},
        {"has_artifact": False},
        {"a4_status": "missing_reference"},
        {"layout_size": "2x4"},
    ],
)
def test_bad_rows_fail(stats, bad):
    rows = grid(stats, 2)
    rows[1, "L2", "raw_first"].update(bad)
    with pytest.raises(ValueError):
        stats.summarize(rows.values())
