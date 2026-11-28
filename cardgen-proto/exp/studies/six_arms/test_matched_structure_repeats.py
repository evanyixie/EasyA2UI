import json
from types import SimpleNamespace

import pytest
from matched_structure_repeats import (
    Observation,
    Reply,
    anchor,
    archived,
    missing_response,
    replay,
    sha,
    summary,
)


def test_absence_has_no_byte_identity_and_groups_keep_their_denominator():
    a = Observation("tree-a", "card-a", True)
    b = Observation("tree-b", "card-b", False)
    c = Observation("tree-c", None, False)
    result = summary([[a, a, b], [c, a], [c, c]])
    assert result["tasks"] == 3
    assert result["structure_calls"] == 7
    assert result["first_availability_by_task"] == {"all": 1, "some": 1, "none": 1}
    assert result["direct_pass_by_task"] == {"some": 2, "none": 1}
    assert result["tasks_with_structure_variation"] == 2
    assert result["tasks_with_different_available_first_bytes"] == 1
    pairs = result["all_within_task_pairs"]
    assert pairs["pairs"] == 5
    assert pairs["both_first_present"] == 3
    assert pairs["same_first_bytes_when_both_present"] == 1
    assert pairs["different_first_bytes_when_both_present"] == 2
    assert pairs["both_first_absent"] == 1
    assert pairs["first_presence_disagrees"] == 1
    assert result["l5_anchor_vs_alternative"]["only_alternative_direct_pass"] == 1
    assert result["l5_anchor_vs_alternative"]["only_anchor_direct_pass"] == 1


def test_archive_verifies_exact_message_bytes_and_physical_call(tmp_path):
    messages = [{"role": "user", "content": "test"}]
    call = {
        "stage": "structure",
        "physical_attempts": 1,
        "http_status": 200,
        "requested_model": "deepseek-flash",
        "returned_model": "deepseek-flash",
        "request_id": "independent-call",
    }
    prompt, receipt, wire = (
        json.dumps(messages).encode(),
        json.dumps(call).encode(),
        b"{}",
    )
    for path, data in (
        ("messages.json", prompt),
        ("response.txt", wire),
        ("call.json", receipt),
    ):
        (tmp_path / path).write_bytes(data)
    (tmp_path / "seal.json").write_text(
        json.dumps(
            {
                "state": "completed",
                "stage": "structure",
                "messages_sha256": sha(prompt),
                "raw_sha256": sha(wire),
                "receipt_sha256": sha(receipt),
            }
        )
    )
    stage = {
        "stage": "structure",
        "raw_sha256": sha(wire),
        "status": "completed",
        "messages": messages,
        "receipt": call,
        "product": {},
    }
    assert archived(tmp_path, stage) == Reply(prompt, wire, call["request_id"], {})
    (tmp_path / "messages.json").write_bytes(prompt + b"\n")
    with pytest.raises(ValueError, match="archive"):
        archived(tmp_path, stage)


def test_replay_rejects_changed_message_even_when_engine_absorbs_the_callback_exception():
    def engine(arm, source, callback, registry_case):
        assert arm == "L5"
        try:
            callback("content", ["content"])
            callback("structure", ["changed"])
        except ValueError:
            return {"stages": []}
        raise AssertionError("changed prompt accepted")

    with pytest.raises(ValueError, match="incomplete"):
        replay(
            SimpleNamespace(engine=SimpleNamespace(execute_case=engine)),
            {},
            {},
            Reply(b'["content"]', b"{}", "one", {}),
            Reply(b'["structure"]', b"{}", "two", {}),
        )


def test_missing_anchor_artifact_must_agree_with_disk(tmp_path):
    stopped = {
        "source_canonical_sha256": "same",
        "status": "stage_rejected",
        "failed_stage": "geometry",
        "stages_completed": ["content", "structure"],
        "first_native": None,
        "final_native": None,
        "first_native_after_entry_repair": None,
        "exit": {"status": "not_reached"},
    }
    anchor(stopped, stopped, tmp_path)
    (tmp_path / "first_native.a2ui.jsonl").write_bytes(b"unexpected")
    with pytest.raises(ValueError, match="on-disk"):
        anchor(stopped, stopped, tmp_path)


def test_matching_failed_transport_is_missing_and_never_a_structure_repeat(tmp_path):
    prompt, receipt = b'["frozen"]', b'{"http_status":null}'
    (tmp_path / "messages.json").write_bytes(prompt)
    (tmp_path / "call.json").write_bytes(receipt)
    (tmp_path / "seal.json").write_text(
        json.dumps(
            {
                "state": "failed",
                "messages_sha256": sha(prompt),
                "receipt_sha256": sha(receipt),
                "raw_sha256": None,
            }
        )
    )
    target = Reply(prompt, b"{}", "independent", {})
    failed = {"messages": ["frozen"], "receipt": json.loads(receipt)}
    assert missing_response(tmp_path, failed, target) == "same_message_missing_reply"
    (tmp_path / "response.txt").write_bytes(b"unregistered")
    with pytest.raises(ValueError, match="unverified missing"):
        missing_response(tmp_path, failed, target)
