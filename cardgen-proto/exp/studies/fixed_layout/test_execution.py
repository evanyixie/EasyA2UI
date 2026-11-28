"""最小合成源覆盖回放缺件、发送断点和封存输出边界。"""

import json
from types import SimpleNamespace

import pytest

import evidence
import run


def runtime_for_test(monkeypatch, replay):
    monkeypatch.setattr(run, "REPLAY", replay, raising=False)
    monkeypatch.setattr(
        run,
        "runtime",
        SimpleNamespace(
            model="synthetic",
            api="unused",
            signature=lambda obj: json.dumps(obj, sort_keys=True),
            dependencies=dict,
        ),
        raising=False,
    )


@pytest.mark.parametrize(
    ("export", "state"),
    [
        ({}, "offline_response_missing"),
        ({"messages.json": []}, "offline_response_missing"),
        ({"response.body": {}}, "offline_prompt_missing"),
        ({"messages.json": [1], "response.body": {}}, "offline_prompt_mismatch"),
    ],
)
def test_incomplete_replay_is_unknown(tmp_path, monkeypatch, export, state):
    replay = tmp_path / "replay"
    target = replay / "synthetic" / "structure"
    target.mkdir(parents=True)
    for name, obj in export.items():
        evidence.atomic(target / name, obj)
    runtime_for_test(monkeypatch, replay)
    freeze = {
        p.relative_to(replay).as_posix(): evidence.sha(p) for p in target.iterdir()
    }
    monkeypatch.setattr(run, "REPLAY_HASHES", freeze, raising=False)
    dest = tmp_path / "results" / "synthetic" / "model_model" / "calls" / "structure"
    raw, receipt = run.exchange(None, dest, "structure", [])
    assert (
        raw is None and receipt["state"] == state and receipt["physical_attempts"] == 0
    )


def test_dispatch_intent_and_saved_response_are_not_resent(tmp_path, monkeypatch):
    runtime_for_test(monkeypatch, None)
    req = []
    dest = tmp_path / "calls"
    evidence.atomic(dest / "messages.json", req)
    intent = {
        "stage": "geometry",
        "prompt_sha256": evidence.digest(run.runtime.signature(req).encode()),
        "physical_attempts": None,
        "http_status": None,
        "state": "dispatch_intent",
    }
    evidence.atomic(dest / "call.json", intent)
    answer, receipt = run.exchange(None, dest, "geometry", req)
    assert answer is None and receipt["physical_attempts"] is None
    envelope = json.dumps(
        {"choices": [{"message": {"content": "synthetic recovered answer"}}]}
    ).encode()
    (dest / "response.body").write_bytes(envelope)
    evidence.atomic(
        dest / "call.json",
        {
            **intent,
            "state": "http_returned",
            "http_status": 200,
            "physical_attempts": 1,
            "expected_body_sha256": evidence.digest(envelope),
        },
    )
    answer, receipt = run.exchange(None, dest, "geometry", req)
    assert answer == "synthetic recovered answer" and receipt["physical_attempts"] == 1
    assert receipt["envelope_sha256"] == evidence.digest(envelope)
    (dest / "response.body").write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="摘要不符"):
        run.exchange(None, dest, "geometry", req)


def test_freeze_does_not_replace_unrelated_evidence(tmp_path, monkeypatch):
    runtime_for_test(monkeypatch, None)
    monkeypatch.setattr(run, "ROOT", tmp_path, raising=False)
    original = tmp_path / "blind_map.json"
    original.write_bytes(b"existing record")
    with pytest.raises(ValueError, match="新的输出"):
        run.lock_frame({}, [], [])
    assert (
        original.read_bytes() == b"existing record"
        and not (tmp_path / "freeze.json").exists()
    )
    with pytest.raises(ValueError, match="重叠"):
        evidence.protect_seal(tmp_path, tmp_path / "anonymous" / "new-review")
    evidence.protect_seal(tmp_path, tmp_path / "independent_audit")


def test_replay_source_changed_after_freeze(tmp_path, monkeypatch):
    target = tmp_path / "export" / "synthetic" / "structure"
    target.mkdir(parents=True)
    evidence.atomic(target / "messages.json", [])
    runtime_for_test(monkeypatch, tmp_path / "export")
    monkeypatch.setattr(run, "REPLAY_HASHES", {}, raising=False)
    with pytest.raises(RuntimeError, match="冻结后变化"):
        run.exchange(
            None,
            tmp_path / "synthetic" / "model_model" / "calls" / "structure",
            "structure",
            [],
        )


def test_live_request_receipt_can_be_replayed_without_another_post(
    tmp_path, monkeypatch
):
    runtime_for_test(monkeypatch, None)

    class Transport:
        def __init__(self):
            self.calls = 0

        def post(self, endpoint, json):
            self.calls += 1
            return SimpleNamespace(
                status_code=200,
                headers={},
                content=b'{"choices":[{"message":{"content":"first response"}}]}',
            )

    transport = Transport()
    folder = tmp_path / "first-stage"
    for _ in range(2):
        answer, receipt = run.exchange(transport, folder, "structure", [])
        assert answer == "first response" and receipt["physical_attempts"] == 1
    assert transport.calls == 1


def test_scoring_result_preserves_existing_file(tmp_path):
    report = tmp_path / "frozen-score.json"
    evidence.atomic(report, {"first": True}, exclusive=True)
    with pytest.raises(FileExistsError):
        evidence.atomic(report, {"first": False}, exclusive=True)
    assert evidence.read(report) == {"first": True}
