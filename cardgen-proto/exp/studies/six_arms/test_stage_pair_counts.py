from pathlib import Path

import pytest


def test_technical_yield_keeps_unknowns_and_arm_identity(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms.technical_yield import ARMS, summarize

    roster = [
        {
            "task_id": "one",
            "family": "a",
            "size": "2x2",
            "included_in_217_sensitivity": True,
        }
    ]
    rows = [
        {
            "task_id": "one",
            "arm": arm,
            "status": state,
            "elapsed_ms": 15,
            "failed_stage": None,
        }
        for arm, state in zip(
            ARMS,
            (
                "geometry_unknown",
                "callback_failed",
                "artifact_checks_rejected",
                "geometry_unresolved",
                "accepted",
                "stage_rejected",
            ),
            strict=True,
        )
    ]
    result = summarize(roster, rows)["all_assigned"]
    assert result["arms"]["L1"]["accepted_count_range"] == [0, 1]
    assert result["arms"]["L2"]["accepted_count_range"] == [0, 1]
    assert result["arms"]["L3"]["accepted_count_range"] == [0, 0]
    assert result["paired_technical_only"]["L6_minus_L5"]["only_L5_pass"] == 1
    assert result["paired_technical_only"]["L5_minus_L2"]["pairs_with_missing"] == 1
    with pytest.raises(ValueError, match="Duplicate"):
        summarize(roster, [*rows, rows[0]])


def test_stage_denominators_and_missing_transport(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms.stage_pair_counts import summarize

    roster = [
        {"task_id": str(i), "family": str(i), "included_in_217_sensitivity": i != 3}
        for i in range(4)
    ]
    rows = [
        {"task": "0", "reach": "upstream_not_reached"},
        {
            "task": "1",
            "reach": "paired",
            "model_terminal": "accepted",
            "program_terminal": "stage_rejected",
        },
        {
            "task": "2",
            "reach": "paired",
            "model_terminal": "callback_failed",
            "program_terminal": "accepted",
        },
        {
            "task": "3",
            "reach": "paired",
            "model_terminal": "accepted",
            "program_terminal": "accepted",
        },
    ]
    out = summarize(rows, roster)
    assert out["all"]["assigned"] == 4
    assert out["all"]["reached"] == 3
    assert out["source_verified"]["reached"] == 2
    assert out["all"]["outcomes_model_then_program"] == {
        "pass/fail": 1,
        "missing/pass": 1,
        "pass/pass": 1,
    }
    assert out["all"]["paired_terminal"][
        "all_assigned_difference_bounds_B_minus_A"
    ] == [-1 / 3, 0]
    with pytest.raises(ValueError, match="exactly once"):
        summarize(rows[:-1] + rows[:1], roster)
