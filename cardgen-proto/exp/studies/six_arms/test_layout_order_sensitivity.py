from dataclasses import replace

import pytest
from layout_order_sensitivity import CONSTANT, KEYS, observe, replay, summarize


def outcome(value, decision):
    return ({p: value for p in replay.POLICIES}, {p: decision for p in replay.POLICIES})


def test_byte_comparison_requires_two_outputs_and_preserves_unknown_decisions():
    first = [outcome("a", "pass"), outcome("b", "pass"), outcome("a", "pass")]
    second = [
        outcome(None, "unknown"),
        outcome(None, "no_policy_hit"),
        outcome("c", "pass"),
    ]
    rows = [
        ("one", "2x2", dict(zip(KEYS, group, strict=True))) for group in (first, second)
    ]
    result = summarize(rows)
    assert result["tasks"] == 1
    for policy in replay.POLICIES:
        group = result[policy]
        assert group["any_different_positive_sha_inputs"] == 1
        assert group["any_different_positive_sha_tasks"] == 1
        assert group["pairs"]["original_vs_constant"] == {
            "changed_decision": 1,
            "different_sha": 1,
            "neither_artifact": 1,
            "one_artifact": 0,
            "same_sha": 0,
        }
        assert group["pairs"]["original_vs_content_sha256"]["one_artifact"] == 1
        assert group["pairs"]["original_vs_content_sha256"]["same_sha"] == 1
        assert group["decisions"]["original"]["unknown"] == 1


def test_unique_input_reused_but_each_original_receipt_checked():
    content = {"size": "2x4", "text": "合成"}
    digest = replay.canonical_sha(content)
    draw = replay.LayoutInput(
        "k", "L2", "2x4", "ready", {"status": "valid"}, {}, content, None, None
    )
    draws = [
        draw,
        replace(draw, donor="L3", status="structure_unknown"),
        replace(draw, donor="L4", status="content_rejected", content=None),
    ]
    hashes, statuses = outcome("x", "pass")
    baseline = {
        "content_sha256": digest,
        "program": hashes,
        "program_decisions": statuses,
    }
    sealed = {("k", donor): baseline.copy() for donor in ("L2", "L3")}
    calls = []

    def select(order_key, c, s, e):
        calls.append(order_key)
        return hashes, statuses

    rows, count = observe(draws, sealed, select)
    assert count == 2 and len(rows) == 1 and calls == ["k", CONSTANT, digest]
    sealed["k", "L3"]["program"] = outcome("y", "pass")[0]
    with pytest.raises(ValueError, match="sealed verdict or artifact"):
        observe(draws, sealed, select)
