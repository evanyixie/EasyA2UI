import json
from pathlib import Path

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import fixed_content_repeats

    return fixed_content_repeats


def test_missing_artifacts_are_not_equal_productions(study):
    all_missing = study.consistency([None] * 10)
    assert all_missing["none_observed"] == 1
    assert all_missing["all_ten_identical"] == all_missing["all_ten_observed"] == 0
    partial = study.consistency(["x"] * 9 + [None])
    assert partial["partially_observed"] == 1 and partial["all_ten_identical"] == 0
    assert study.consistency(["x", "y"] * 5)["two_or_more_observed_variants"] == 1
    with pytest.raises(ValueError, match="Incomplete"):
        study.consistency(["x"] * 9)


def test_ten_failures_remain_visible_separately_from_tree_stability(study):
    common = {"structure": "tree", "ms": 0.4, "layout_ms": 0.9}
    missing = {
        **common,
        "first": None,
        "final": None,
        "status": "stage_rejected",
        "failed_stage": "geometry",
        "accepted": False,
    }
    present = {
        **common,
        "first": "imageA",
        "final": "imageA",
        "status": "accepted",
        "failed_stage": None,
        "accepted": True,
    }
    mixed = [{**present, "first": "imageB"}] + [present] * 8 + [missing]
    out = study.summarize([[missing] * 10, mixed])
    assert out["agreement"]["structure"]["all_ten_identical"] == 2
    assert out["agreement"]["first"]["all_ten_identical"] == 0
    assert out["agreement"]["first"]["two_or_more_observed_variants"] == 1
    assert out["technical"]["tasks_by_accepted_draws"] == {0: 1, 9: 1}
    assert out["technical"]["accepted_draws"] == 9


def test_single_observed_model_reply_cannot_be_reassigned(study, tmp_path):
    call = tmp_path / "calls" / "structure"
    call.mkdir(parents=True)
    messages = [{"role": "user", "content": "synthetic"}]
    wire = study.canonical(messages)
    (call / "messages.json").write_bytes(wire)
    (call / "response.txt").write_bytes(b"[]")
    receipt = {
        "stage": "structure",
        "actual_payload_sha256": study.digest(
            study.canonical({**study.WIRE, "messages": messages})
        ),
        "physical_attempts": 1,
        "endpoint": "https://api.deepseek.com/chat/completions",
        "http_status": 200,
        "returned_model": study.WIRE["model"],
        "request_id": "unique-test",
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }
    (call / "call.json").write_text(json.dumps(receipt), encoding="utf-8")
    record = {
        "receipt": receipt,
        "messages": messages,
        "raw_sha256": study.digest(b"[]"),
    }
    seen = set()
    from collections import Counter

    statuses, usage = Counter(), Counter()
    study.add_provider_observation(tmp_path, wire, record, seen, statuses, usage)
    assert (
        seen == {"unique-test"} and usage["total_tokens"] == 7 and statuses["200"] == 1
    )
    with pytest.raises(ValueError, match="Reused"):
        study.add_provider_observation(tmp_path, wire, record, seen, statuses, usage)
