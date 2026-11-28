from pathlib import Path

import pytest


@pytest.fixture
def timing(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import formal_stage_timing

    return formal_stage_timing


def stage(owner, wall, *, callback=None, call=None):
    return {
        "owner": owner,
        "wall_ms": wall,
        "callback_ms": callback,
        "status": "completed",
        "call": call,
    }


def seat(stages, elapsed, *, exit_reached=False, exit_ms=None):
    return {
        "stages": stages,
        "elapsed_ms": elapsed,
        "status": "completed" if exit_reached else "stage_rejected",
        "exit_reached": exit_reached,
        "exit_ms": exit_ms,
    }


def test_nested_clocks_are_not_added_and_failed_transport_is_unknown(timing):
    returned = {"provider": "response", "attempts": 1, "http_ms": 8}
    lost = {"provider": None, "attempts": None, "http_ms": 20}
    a = seat(
        {
            "content": stage("model_extract", 11, callback=10, call=returned),
            "structure": stage("program_route", 2),
        },
        17,
        exit_reached=True,
        exit_ms=3,
    )
    b = seat({"content": stage("model_extract", 22, callback=21, call=lost)}, 23)
    b["status"] = "callback_failed"
    b["stages"]["content"]["status"] = "callback_failed"
    result = timing.aggregate("L6", [a, b])
    assert result["unattributed_elapsed_ms"]["sum_ms"] == 2
    assert result["elapsed_ms"]["sum_ms"] == 40
    assert result["exit_not_reached"] == 1
    content = result["stages"]["content"]
    assert content["attempted"] == content["logged_model_intents"] == 2
    assert (
        content["known_physical_attempts"]
        == content["unknown_physical_attempt_intents"]
        == 1
    )
    assert content["stage_status"] == {"completed": 1, "callback_failed": 1}
    assert content["receipt_http_ms"]["sum_ms"] == 28
    assert content["callback_wall_ms"]["sum_ms"] == 31
    assert content["wall_ms"]["sum_ms"] == 33
    assert result["stages"]["structure"]["not_reached"] == 1
    assert result["stages"]["structure"]["callback_wall_ms"]["eligible"] == 0


def test_early_stop_and_missing_duration_have_different_denominators(timing):
    baseline = seat(
        {"content": stage("model_extract", 8), "structure": stage("model_free", 6)}, 15
    )
    later = seat(
        {"content": stage("model_extract", 8), "structure": stage("program_route", 2)},
        11,
    )
    early = seat({"content": stage("model_extract", 8)}, 9)
    result = timing.adjacent({"a": baseline, "b": baseline}, {"a": early, "b": later})
    assert result["structure"]["all_assigned_difference_sum_ms"] == -10
    assert result["structure"]["both_reached_right_minus_left_ms"]["p50_ms"] == -4
    assert result["structure"]["both_reached_right_minus_left_ms"]["eligible"] == 1
    assert result["structure"]["both_completed_right_minus_left_ms"]["eligible"] == 1
    assert result["elapsed"]["both_reached_right_minus_left_ms"]["p50_ms"] == -5
    later["stages"]["structure"]["status"] = "stage_rejected"
    later["stages"]["structure"]["wall_ms"] = None
    later.update(exit_reached=True, exit_ms=None)
    assert timing.residual(later) is None
    result = timing.adjacent({"a": baseline, "b": baseline}, {"a": early, "b": later})
    assert (
        result["structure"]["missing_pair_clocks"]
        == result["exit"]["missing_pair_clocks"]
        == 1
    )
    assert result["structure"]["all_assigned_difference_sum_ms"] is None
    assert result["structure"]["both_reached_right_minus_left_ms"]["observed"] == 0
    assert result["structure"]["both_completed_right_minus_left_ms"]["eligible"] == 0


def test_quantile_and_unavailable_clocks(timing):
    stats = timing.distribution([None, 1, 3, 6])
    assert (stats["p50_ms"], stats["p95_ms"], stats["sum_ms"], stats["unknown"]) == (
        3,
        5.7,
        10,
        1,
    )
    assert timing.distribution([])["sum_ms"] is None
    with pytest.raises(ValueError, match="Invalid clock"):
        timing.distribution([-0.1])
    with pytest.raises(ValueError, match="Unpaired"):
        timing.adjacent({"a": {}}, {})


def test_stage_mismatch_fails_closed(timing, tmp_path):
    record = {"execution": {"stages": [{"stage": "emit"}]}}
    with pytest.raises(ValueError, match="sequence"):
        timing.project(record, {"arm": "L2", "steps": []}, tmp_path)
