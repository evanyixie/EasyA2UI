from itertools import product
from pathlib import Path

import pytest


@pytest.fixture
def stats(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import composite_cost_stats

    return composite_cost_stats


def grid(stats, n):
    return {
        (t, a, p): {
            "task": t,
            "family": "f" + str(int(t) // 2),
            "arm": a,
            "phase": p,
            "protocol": True,
            "geometry": True,
            "a4a_hits": 4,
            "a4a_total": 5,
            "total_tokens": 10 if p == stats.PHASES[1] else None,
        }
        for t, a, p in product(map(str, range(n)), stats.ARMS, stats.PHASES)
    }


@pytest.mark.parametrize(
    ("hits", "total", "protocol", "geometry", "expected"),
    [
        (3, 5, True, True, ("pass", "fail", "fail")),
        (4, 5, True, True, ("pass", "pass", "fail")),
        (5, 5, True, True, ("pass", "pass", "pass")),
        (0, 5, True, True, ("fail",) * 3),
        (0, 0, True, True, ("unknown",) * 3),
        (None, 0, True, True, ("unknown",) * 3),
        (None, 5, True, True, ("unknown",) * 3),
        (4, None, True, True, ("unknown",) * 3),
        (None, None, False, None, ("fail",) * 3),
        (5, 5, None, True, ("unknown",) * 3),
        (0, 5, None, True, ("fail",) * 3),
    ],
)
def test_thresholds_and_three_valued_qualification(
    stats, hits, total, protocol, geometry, expected
):
    row = {
        "a4a_hits": hits,
        "a4a_total": total,
        "protocol": protocol,
        "geometry": geometry,
    }
    assert tuple(stats.qualifies(row, p) for p in stats.THRESHOLDS) == expected


def test_cost_bounds_with_unknown_qualifiers_and_missing_token_receipts(stats):
    assert stats.cost_bounds(19, 0, 0, 2) == {
        "exact_tokens_per_qualified": None,
        "lower_if_positive": 9.5,
        "upper_if_positive": 19,
        "zero_qualified_possible": True,
        "positive_qualified_possible": True,
    }
    assert stats.cost_bounds(100, 2, 2, 3)["upper_if_positive"] is None
    zero = stats.cost_bounds(100, 0, 0, 0)
    assert (
        zero["lower_if_positive"]
        is zero["upper_if_positive"]
        is zero["exact_tokens_per_qualified"]
        is None
    )
    assert not zero["positive_qualified_possible"]
    assert stats.cost_bounds(10, 0, 2, 2)["exact_tokens_per_qualified"] == 5
    assert stats.cost_bounds(0, 0, 1, 1)["exact_tokens_per_qualified"] == 0


def test_common_metering_filters_tasks_but_not_failing_seats(stats):
    rows = grid(stats, 4)
    first, final = stats.PHASES
    rows["0", "L5", final].update(total_tokens=None, known_tokens=7)
    rows["1", "L6", final].update(total_tokens=None)
    rows["2", "L1", final].update(total_tokens=None)
    rows["1", "L5", final].update(protocol=False, total_tokens=17)
    rows["2", "L5", final].update(geometry=None)
    rows["3", "L5", final].update(a4a_hits=None)
    result = stats.summarize(rows.values(), expected_tasks=4)
    panels = result["phases"][final]
    assert {k: v["assigned_tasks"] for k, v in panels.items()} == {
        "all_assigned": 4,
        "six_arm_meter_complete": 1,
        "L4_L5_meter_complete": 3,
        "L5_L6_meter_complete": 2,
    }
    assert set(panels["L4_L5_meter_complete"]["arms"]) == {"L4", "L5"}
    a = panels["all_assigned"]["arms"]["L5"]
    assert (
        a["metering"]["known_accounted_tokens"] == 44
        and a["metering"]["all_assigned_tokens"] is None
    )
    q = a["thresholds"]["80"]
    assert (q["pass"], q["fail"], q["unknown"]) == (1, 1, 2)
    assert q["qualified_count_bounds"] == [1, 3]
    assert (
        q["b4_tokens"]["lower_if_positive"] == 44 / 3
        and q["b4_tokens"]["upper_if_positive"] is None
    )
    p = panels["L4_L5_meter_complete"]["arms"]["L5"]
    assert p["metering"]["all_assigned_tokens"] == 37 and p["thresholds"]["80"][
        "qualified_count_bounds"
    ] == [0, 2]
    pair = panels["L4_L5_meter_complete"]["paired"]["L4_L5"]["80"]
    assert pair["rows_left_columns_right"]["pass"] == {
        "fail": 1,
        "pass": 0,
        "unknown": 2,
    }
    assert pair["right_minus_left_qualified_count_bounds"] == [-3, -1]
    first_arm = result["phases"][first]["all_assigned"]["arms"]["L5"]
    assert (
        "metering" not in first_arm and "b4_tokens" not in first_arm["thresholds"]["80"]
    )


def test_all_costs_for_failed_work_remain_in_exact_numerator(stats):
    rows = grid(stats, 2)
    rows["1", "L4", stats.PHASES[1]].update(geometry=False, total_tokens=90)
    q = stats.summarize(rows.values())["phases"][stats.PHASES[1]]["all_assigned"][
        "arms"
    ]["L4"]["thresholds"]["80"]
    assert q["pass"] == 1 and q["b4_tokens"]["exact_tokens_per_qualified"] == 100


def test_empty_vs_missing_a4a_and_unmetered_cohort(stats):
    rows = grid(stats, 2)
    for r in rows.values():
        r.update(
            a4a_hits=0 if r["task"] == "0" else None,
            a4a_total=0 if r["task"] == "0" else None,
            total_tokens=None,
        )
    p = stats.summarize(rows.values())["phases"][stats.PHASES[1]]
    a = p["all_assigned"]["arms"]["L6"]
    assert a["a4a"] == {"known_fraction": 0, "empty_reference": 1, "missing_counts": 1}
    assert a["thresholds"]["80"]["qualified_count_bounds"] == [0, 2]
    assert a["metering"]["all_assigned_tokens"] is None
    assert p["six_arm_meter_complete"]["assigned_tasks"] == 0


@pytest.mark.parametrize(
    "update",
    [
        {"geometry": 0},
        {"protocol": "pass"},
        {"a4a_hits": 6},
        {"a4a_total": 0},
        {"total_tokens": False},
        {"total_tokens": -1},
        {"a4a_hits": 3.1},
        {"known_tokens": 11},
        {"family": "changed"},
        {"a4a_total": 7},
    ],
)
def test_invalid_rows_rejected(stats, update):
    rows = grid(stats, 1)
    rows["0", "L3", stats.PHASES[1]].update(update)
    with pytest.raises(ValueError):
        stats.summarize(rows.values())


def test_grid_validation(stats):
    rows = list(grid(stats, 2).values())
    for bad, n in [(rows[:-1], 2), (rows + [rows[0]], 2), (rows, 219)]:
        with pytest.raises(ValueError):
            stats.summarize(bad, expected_tasks=n)
