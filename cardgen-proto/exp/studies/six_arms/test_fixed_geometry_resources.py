from pathlib import Path

import pytest


@pytest.fixture
def metrics(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import fixed_geometry_resources

    return fixed_geometry_resources


def observation(m, task, model, program, metered=True):
    tokens = (
        {
            "prompt_tokens": 15,
            "completion_tokens": 6,
            "total_tokens": 21,
            "prompt_cache_hit_tokens": 10,
            "prompt_cache_miss_tokens": 5,
        }
        if metered
        else dict.fromkeys(m.cost.METER)
    )
    return {
        "task": task,
        "model_ms": model,
        "program_ms": program,
        "callback_ms": model - 1,
        "http_ms": model - 2,
        "model_status": "completed" if metered else "callback_failed",
        "messages_sha256": "identical_messages",
        "call": {
            "local": task,
            "provider": task if metered else None,
            "attempts": 1 if metered else None,
            "http_status": 200 if metered else None,
            "tokens": tokens,
        },
    }


def test_paired_time_and_unconfirmed_usage_are_distinct(metrics):
    m = metrics
    rows = [
        observation(m, "a", 100, 10),
        observation(m, "b", 50, 49),
        observation(m, "c", 10, 2, False),
    ]
    out = m.summarize(rows, 5)
    clocks = out["all_attempted_geometry"]
    assert clocks["model_geometry_wall_ms"]["p50_ms"] == 50
    assert clocks["program_geometry_wall_ms"]["p50_ms"] == 10
    assert clocks["model_minus_program_same_tree_ms"]["p50_ms"] == 8
    assert clocks["original_official_post_wall_ms"]["observed"] == 3
    assert (
        out["same_trees_with_received_model_response"]["model_geometry_wall_ms"][
            "observed"
        ]
        == 2
    )
    assert (out["same_tree_reached"], out["upstream_unreached"]) == (3, 2)
    assert out["known_geometry_usage"]["total_tokens"] == 42
    assert out["known_geometry_usage"]["unknown_usage_calls"] == 1
    assert out["requests"]["known_physical_attempts"] == 2
    assert out["requests"]["unconfirmed_physical_attempt_counts"] == 1
    assert (
        out["requests"]["identical_message_groups_with_multiple_confirmed_responses"]
        == 1
    )
    assert out["requests"]["distinct_provider_response_ids"] == 2


def test_actual_response_cannot_be_reused_as_a_second_call(metrics):
    rows = [observation(metrics, "a", 30, 2), observation(metrics, "b", 60, 4)]
    rows[1]["call"]["provider"] = rows[0]["call"]["provider"]
    with pytest.raises(ValueError, match="reused"):
        metrics.summarize(rows, 2)


def test_changed_tree_is_rejected_before_reading_any_model_receipts(metrics, tmp_path):
    up = {
        "content": {"product": {"title": "x"}},
        "structure": {"product": {"kind": "column"}},
        "geometry": {},
    }
    outcome = {"execution": {"stages": [{"stage": k, **v} for k, v in up.items()]}}
    pair = {
        "state": "paired",
        "new_model_calls": 0,
        "upstream_sha256": {"content": "other", "structure": "tree"},
    }
    with pytest.raises(ValueError, match="different content or tree"):
        metrics.read_stage(tmp_path, outcome, pair, {})


def test_upstream_failure_has_no_zero_geometry_time(metrics, tmp_path):
    outcome = {"execution": {"stages": [{"stage": "content"}], "stages_completed": []}}
    assert (
        metrics.read_stage(tmp_path, outcome, {"state": "upstream_not_reached"}, {})
        is None
    )
    outcome["execution"]["stages"].append({"stage": "geometry"})
    with pytest.raises(ValueError, match="Unreached"):
        metrics.read_stage(tmp_path, outcome, {"state": "upstream_not_reached"}, {})
