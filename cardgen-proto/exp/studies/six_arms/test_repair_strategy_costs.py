import json

import pytest
from repair_strategy_costs import count, digest, followup_call, pairs, summarize


def call(value, attempts=1, rid="returned"):
    tokens = {
        "prompt_cache_hit_tokens": value,
        "prompt_cache_miss_tokens": value,
        "prompt_tokens": 2 * value if value is not None else None,
        "completion_tokens": value,
        "total_tokens": 3 * value if value is not None else None,
    }
    return {"attempts": attempts, "provider": rid, "tokens": tokens}


def test_actual_additional_requests_and_complete_pairs_use_same_tasks():
    original = count([call(2)])
    repaired = original + count([call(3)])
    unknown = count([call(None, None, None)])
    observed = {"a": repaired, "b": original + unknown, "c": original, "d": unknown}
    comparator = {
        "a": count([call(1)]),
        "b": count([call(2)]),
        "c": unknown,
        "d": unknown,
    }
    group = summarize(list(observed.values()))
    assert group["total_tokens"] == 27
    assert (
        group["unknown_usage_calls"] == group["unknown_physical_attempt_intents"] == 2
    )
    assert group["tasks_with_complete_usage"] == 2
    pair = pairs(observed, comparator)
    assert (
        pair["complete_usage_pairs"],
        pair["left_only_missing"],
        pair["right_only_missing"],
        pair["both_missing"],
    ) == (1, 1, 1, 1)
    assert (
        pair["L1_M"]["total_tokens"] == 15 and pair["comparator"]["total_tokens"] == 3
    )
    assert pair["median_L1_M_minus_comparator"]["total_tokens"] == 12
    assert (
        pairs({"a": unknown}, {"a": original})["median_L1_M_minus_comparator"][
            "total_tokens"
        ]
        is None
    )
    with pytest.raises(ValueError, match="roster"):
        pairs({"a": original}, {"b": original})


def write(path, obj):
    raw = json.dumps(obj).encode()
    path.write_bytes(raw)
    return digest(raw)


def slot_fixture(slot, success):
    slot.mkdir()
    msg = write(slot / "messages.json", ["example"])
    intent = {
        "stage": "r1",
        "messages_sha256": msg,
        "local_request_id": "local",
        "started_utc": "test",
    }
    write(slot / "intent.json", intent)
    u = call(7)["tokens"] if success else None
    if u:
        u["prompt_tokens_details"] = {"cached_tokens": 7}
    receipt = write(
        slot / "call.json",
        {
            "stage": "r1",
            "physical_attempts": 1 if success else None,
            "http_status": 200 if success else None,
            "request_id": "id" if success else None,
            "usage": u,
        },
    )
    raw = write(slot / "response.txt", "reply") if success else None
    write(
        slot / "seal.json",
        {
            **intent,
            "receipt_sha256": receipt,
            "state": "completed" if success else "failed",
            "raw_sha256": raw,
        },
    )
    return {
        "round": 1,
        "common_pass": False if success else None,
        "added_tokens": 21 if success else None,
    }


def test_rejected_candidate_is_charged_once_and_receipt_substitution_rejected(tmp_path):
    slot = tmp_path / "r1"
    rr = slot_fixture(slot, True)
    loc, pro = set(), set()
    c = followup_call(slot, rr, loc, pro)
    assert count([c])["total_tokens"] == 21 and count([c])["provider_ids"] == 1
    with pytest.raises(ValueError, match="local"):
        followup_call(slot, rr, loc, pro)
    with pytest.raises(ValueError, match="provider ID"):
        followup_call(slot, rr, set(), pro)
    (slot / "response.txt").write_bytes(b"different")
    with pytest.raises(ValueError, match="hash mismatch"):
        followup_call(slot, rr, set(), set())


def test_transport_intent_is_not_a_confirmed_request_or_zero_usage(tmp_path):
    slot = tmp_path / "r1"
    rr = slot_fixture(slot, False)
    c = count([followup_call(slot, rr, set(), set())])
    assert (c["request_intents"], c["metered_requests"], c["unknown_usage_calls"]) == (
        1,
        0,
        1,
    )
    assert (
        c["confirmed_physical_attempts"],
        c["unknown_physical_attempt_intents"],
    ) == (0, 1)
    rr["added_tokens"] = 0
    with pytest.raises(ValueError, match="unknown"):
        followup_call(slot, rr, set(), set())
