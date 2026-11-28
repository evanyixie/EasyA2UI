from pathlib import Path

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import cost_frontier

    return cost_frontier


def row(status, total, native=False):
    return {
        "calls": [
            {
                "tokens": {
                    "prompt_tokens": 0 if total is not None else None,
                    "completion_tokens": total,
                    "total_tokens": total,
                },
                "attempts": 1 if total is not None else None,
            }
        ],
        "status": status,
        "native_screen_pass": native,
        "elapsed_ms": 1500,
    }


def test_shared_usage_excludes_the_whole_unmetered_task_and_charges_failed_attempts(
    study,
):
    tasks = ["one", "two", "three"]
    grid = {(t, a): row("accepted", 4, True) for t in tasks for a in study.ARMS}
    grid["two", "L1"] = row("geometry_unresolved", 10, True)
    grid["two", "L6"] = row("geometry_unknown", 9)
    grid["three", "L2"] = row("callback_failed", None)
    result = study.panels(grid, tasks, study.ARMS)
    assert result["shared_tasks"] == 2
    assert result["arms"]["L1"]["tokens_per_technical_pass"] == 14
    assert result["arms"]["L1"]["tokens_per_native_screen_pass"] == 7
    assert result["arms"]["L6"]["unknown_technical"] == 1
    assert study.panels(grid, tasks, ("L5", "L6"))["shared_tasks"] == 3
    assert "tokens_per_assigned" not in study.totals([grid["three", "L2"]])


def test_pareto_equal_points_undefined_cost_and_receipt_integrity(study):
    rows = {
        a: {"budget": cost, "pass": good, "assigned": 10}
        for a, cost, good in (
            ("a", 2, 3),
            ("b", 2, 3),
            ("c", 3, 2),
            ("d", None, 0),
            ("e", 1, 2),
        )
    }
    assert study.frontier(rows, "pass", "budget") == ["a", "b", "e"]
    broken = row("accepted", 4)["calls"]
    broken[0]["tokens"]["completion_tokens"] = 3
    with pytest.raises(ValueError, match="Inconsistent"):
        study.usage(broken)
