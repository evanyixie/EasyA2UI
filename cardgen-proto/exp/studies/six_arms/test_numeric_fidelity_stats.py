from itertools import product
from pathlib import Path

import pytest


@pytest.fixture
def stats(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import numeric_fidelity_stats

    return numeric_fidelity_stats


def measured(total, *, fact=0, query=0, both=0, strict=0, extra=0):
    return {
        "status": "measured",
        "total": total,
        "supported": fact + query + both,
        "fact_only_supported": fact,
        "query_only_supported": query,
        "both_supported": both,
        "strict_supported": strict,
        "snapshot_supported_extra": extra,
    }


def unavailable(stats, status, total=None):
    default = 0 if status == "empty_data" else None
    out = {k: default for k in stats.COUNTS}
    out.update(status=status, total=default if total is None else total)
    return out


def grid(stats, cases):
    return {
        (t, a, p): {
            "task": t,
            "family": f,
            "arm": a,
            "phase": p,
            "metrics": dict(metrics),
        }
        for (t, f, metrics), a, p in product(cases, stats.ARMS, stats.PHASES)
    }


def test_unknowns_and_two_averages_are_distinct(stats):
    def status(k, n=None):
        return unavailable(stats, k, n)

    rows = grid(
        stats,
        [
            ("one", "x", measured(1, query=1, strict=1)),
            ("two", "x", measured(5, fact=1, both=1, strict=1, extra=2)),
            ("three", "y", measured(4, strict=2, extra=4)),
            ("empty", "y", status("empty_data")),
            ("unknown", "y", status("unresolved_text")),
            ("absent", "z", status("no_artifact")),
            ("ref", "z", status("missing_reference", 7)),
        ],
    )
    finals = stats.summary(rows.values(), expected_tasks=7)["phases"][
        "after_common_repair"
    ]
    out = finals["arms"]["L5"]
    assert out == stats.arm_summary(
        r["metrics"]
        for r in rows.values()
        if r["arm"] == "L5" and r["phase"] == stats.PHASES[1]
    )
    assert out["assigned_cards"] == 7
    assert out["measured_cards"] == 3
    assert out["excluded_cards"] == 4
    assert out["status_counts"] == {
        k: (3 if k == "measured" else 1) for k in stats.STATES
    }
    assert out["total_measured_fragments"] == 10
    assert out["original_source_fragments"] == {
        "fact_only_supported": 1,
        "query_only_supported": 1,
        "both_supported": 1,
    }
    assert out["cards_with_query_only_support"] == 1
    assert out["snapshot_supported_extra"] == 6
    for name, micro, macro, all_supported, none in (
        ("original", 0.3, (1 + 0.4) / 3, 1, 1),
        ("strict", 0.4, (1 + 0.2 + 0.5) / 3, 1, 0),
        ("original_plus_snapshot", 0.9, (1 + 0.8 + 1) / 3, 2, 0),
    ):
        x = out["support"][name]
        assert x["micro_mean"] == pytest.approx(micro)
        assert x["macro_mean"] == pytest.approx(macro)
        assert x["cards_with_all_fragments_supported"] == all_supported
        assert x["cards_with_no_supported_fragments"] == none


def test_family_resampling_preserves_dependence_and_uses_only_paired_tasks(stats):
    cases = [(f"t{i}", "large", measured(1)) for i in range(9)]
    cases.extend(
        [
            ("negative", "small", measured(1, fact=1)),
            ("left", "u", measured(1)),
            ("right", "u", measured(1)),
            ("neither", "v", measured(1)),
        ]
    )
    rows = grid(stats, cases)
    final = stats.PHASES[1]
    for i in range(9):
        rows[f"t{i}", "L5", final]["metrics"] = measured(1, query=1)
    rows["negative", "L5", final]["metrics"] = measured(1)
    for task, arm in (
        ("left", "L5"),
        ("right", "L4"),
        ("neither", "L4"),
        ("neither", "L5"),
    ):
        rows[task, arm, final]["metrics"] = unavailable(stats, "empty_data")
    report = stats.summary(rows.values(), expected_tasks=13)
    panel = report["phases"][final]["paired"]["L5_minus_L4"]
    assert panel["assigned_pairs"] == 13
    assert panel["measured_pairs"] == 10
    assert panel["families_with_measured_pairs"] == 2
    assert (
        panel["left_only_measured"]
        == panel["right_only_measured"]
        == panel["neither_measured"]
        == 1
    )
    result = panel["support"]["original"]
    assert result["wins"] == {"right": 9, "left": 1, "tie": 0}
    assert result["left_macro_mean"] == 0.1 and result["right_macro_mean"] == 0.9
    assert result["right_minus_left_macro_difference"] == 0.8
    # Drawing the single all-negative family twice is frequent enough to define the lower tail.
    assert result["paired_family_percentile_ci95"] == [-1.0, 1.0]
    first_result = report["phases"][stats.PHASES[0]]["paired"]["L5_minus_L4"][
        "support"
    ]["original"]
    assert first_result["right_minus_left_macro_difference"] == 0
    assert first_result["paired_family_percentile_ci95"] is None
    assert report == stats.summary(reversed(list(rows.values())))


def test_fraction_comparison_does_not_round_a_difference_into_a_tie(stats):
    total = 2**60
    rows = grid(
        stats,
        [
            ("n", "one", measured(total, fact=total)),
            ("equal", "one", measured(6, fact=2)),
        ],
    )
    for phase in stats.PHASES:
        rows["n", "L6", phase]["metrics"] = measured(total, fact=total - 1)
        rows["equal", "L6", phase]["metrics"] = measured(3, fact=1)
    out = stats.summary(rows.values())["phases"]["raw_first"]["paired"]["L6_minus_L5"][
        "support"
    ]["original"]
    assert out["wins"] == {"left": 1, "right": 0, "tie": 1}
    assert out["right_minus_left_macro_difference"] == -1 / (2 * total)
    assert out["interval_status"] == "fewer_than_two_measured_families"


def test_zero_measurements_do_not_get_perfect_or_zero_precision(stats):
    rows = grid(stats, [("t", "f", unavailable(stats, "empty_data"))])
    stage = stats.summary(rows.values())["phases"]["raw_first"]
    arm = stage["arms"]["L1"]
    assert arm["support"]["original"]["micro_mean"] is None
    assert arm["support"]["original"]["macro_mean"] is None
    assert arm["support"]["original"]["cards_with_no_supported_fragments"] == 0
    assert arm["support"]["original"]["cards_with_all_fragments_supported"] == 0
    pair = stage["paired"]["L6_minus_L5"]["support"]["original"]
    assert pair["right_minus_left_macro_difference"] is None


def test_checkpoint_changes_can_cancel_despite_individual_gains_and_losses(stats):
    rows = grid(
        stats,
        [
            ("up", "x", measured(2)),
            ("down", "y", measured(4, fact=4)),
            ("equal", "z", measured(2, fact=1)),
            ("acquired", "x", unavailable(stats, "no_artifact")),
            ("lost", "x", measured(2, fact=1)),
            ("unread", "z", unavailable(stats, "unresolved_text")),
        ],
    )
    final = stats.PHASES[1]
    for task, result in (
        ("up", measured(4, fact=4)),
        ("down", measured(2)),
        ("acquired", measured(2, fact=1)),
        ("lost", unavailable(stats, "empty_data")),
        ("unread", unavailable(stats, "missing_reference", 1)),
    ):
        rows[task, "L5", final]["metrics"] = result
    report = stats.summary(rows.values())
    for p in stats.PHASES:
        assert (
            report["phases"][p]["arms"]["L5"]["support"]["original"]["macro_mean"]
            == 0.5
        )
    result = report["within_arm_first_to_final"]["L5"]
    assert result["assigned"] == 6 and result["both_measured"] == 3
    state = result["rows_first_columns_final"]
    assert state["measured"]["measured"] == 3
    assert state["no_artifact"]["measured"] == state["measured"]["empty_data"] == 1
    assert state["unresolved_text"]["missing_reference"] == 1
    assert sum(sum(row.values()) for row in state.values()) == 6
    for measure in ("original_support", "fragment_count"):
        assert result[measure]["mean_final_minus_first"] == 0
        assert [
            result[measure][k] for k in ("increased", "unchanged", "decreased")
        ] == [1, 1, 1]
    assert (
        report["within_arm_first_to_final"]["L6"]["original_support"]["increased"] == 0
    )


@pytest.mark.parametrize(
    "bad",
    [
        {"total": 0},
        {"supported": True},
        {"supported": 2},
        {"strict_supported": 4},
        {"snapshot_supported_extra": 3},
        {"fact_only_supported": -1},
        {"fact_only_supported": None},
        {"status": "unknown"},
        {"status": "empty_data"},
        {"status": "missing_reference"},
        {"status": "no_artifact"},
        {"status": "unresolved_text"},
    ],
)
def test_invalid_evidence_rejected(stats, bad):
    rows = grid(stats, [("x", "g", measured(3, fact=1))])
    next(iter(rows.values()))["metrics"].update(bad)
    with pytest.raises(ValueError):
        stats.summary(rows.values())


def test_incomplete_duplicate_and_unmatched_families_are_rejected(stats):
    rows = list(grid(stats, [("n", "f", measured(3, strict=3))]).values())
    for bad in (
        [],
        rows[:-1],
        [*rows, rows[0]],
        [{**rows[0], "family": "different"}, *rows[1:]],
    ):
        with pytest.raises(ValueError):
            stats.summary(bad)
    with pytest.raises(ValueError, match="task count"):
        stats.summary(rows, expected_tasks=2)
