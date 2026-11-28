"""Offline controls for the exact Windows runner sealed before the model-selector batch."""

import json
import os
from pathlib import Path

import httpx
import pytest

FROZEN = "788212c2613d4fe09862aee9ddb2f4ac3e4baad24ddcc9129f92b26103500977"
# The original runner issued this request to a MockTransport for this synthetic
# menu, including its unnormalized CRLF, leading spaces and UTF-8 label.
SYNTHETIC_WIRE = (
    '  { "choices": [{"id":"X"},{"id":"Y"}], "label": "字号" }\r\n'.encode()
)
SYNTHETIC_REQUEST = "932f4a6cc1404184a26d9cbec61e24875f2154f22da1971cb65213795adc7384"


@pytest.fixture
def runner(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import menu_model_runner

    # The published execution path uses the registered Windows byte-range
    # lock. On other platforms exercise the same HTTP/file state transitions.
    if os.name != "nt":
        from six_arms.content_choice.transport import seat_lock

        monkeypatch.setattr(menu_model_runner, "writer", seat_lock)
    return menu_model_runner


def row(runner, root, name, ids, raw=None):
    raw = raw if raw is not None else runner.blob({"choices": [{"id": v} for v in ids]})
    source = root / (name + ".json")
    source.write_bytes(raw)
    return {
        "task_id": name,
        "wire_path": str(source),
        "wire_sha256": runner.sha(raw),
        "options": ids,
    }


def freeze(runner, tmp, rows):
    index = tmp / "roster.json"
    index.write_bytes(runner.blob({"rows": rows}))
    dest = tmp / "batch"
    plan = runner.freeze(index, runner.sha(index.read_bytes()), dest)
    assert plan["runner_sha256"] == FROZEN
    return dest


def selected_body(model="deepseek-flash", answer='{"choice":"Y"}'):
    return {
        "choices": [{"message": {"content": answer}, "finish_reason": "stop"}],
        "model": model,
        "id": "mock_id",
        "usage": {"total_tokens": 17},
    }


def test_request_bytes_response_receipts_and_resume(runner, tmp_path):
    rows = [
        row(runner, tmp_path, "none", []),
        row(runner, tmp_path, "forced", ["Y"]),
        row(runner, tmp_path, "select", ["X", "Y"], SYNTHETIC_WIRE),
    ]
    dest = freeze(runner, tmp_path, rows)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200, json=selected_body(), headers={"x-ds-trace-id": "mock_trace"}
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with runner.writer(dest):
            result = runner.run_locked(dest, client)
        with runner.writer(dest):
            assert runner.run_locked(dest, client) == result
    assert result["statuses"] == {"empty": 1, "forced": 1, "selected": 1}
    assert result["local_intents"] == result["confirmed_requests"] == len(calls) == 1
    request = calls[0]
    assert request.method == "POST" and str(request.url) == runner.API
    assert runner.sha(request.content) == SYNTHETIC_REQUEST
    sent = json.loads(request.content)
    assert sent.pop("messages") == [
        {"role": "system", "content": runner.SYSTEM},
        {"role": "user", "content": SYNTHETIC_WIRE.decode()},
    ]
    assert sent == runner.SERVICE
    folder = dest / "seats" / runner.sha(b"select")
    assert (folder / "request.json").read_bytes() == request.content
    assert runner.read(folder / "intent.json")["request_sha256"] == SYNTHETIC_REQUEST
    receipt = runner.read(folder / "result.json")
    assert (receipt["choice"], receipt["request_id"], receipt["actual_model"]) == (
        "Y",
        "mock_trace",
        "deepseek-flash",
    )
    assert receipt["usage"]["total_tokens"] == 17
    assert 0 <= receipt["http_ms"] <= receipt["decision_ms"] + 0.001


@pytest.mark.parametrize(
    "answer",
    [
        '{"choice":"X","choice":"Y"}',
        '{"choice":"Y","reason":"ok"}',
        '{"choice":1}',
        '{"choice":"unknown"}',
        '["Y"]',
        '```json\n{"choice":"Y"}\n```',
    ],
)
def test_strict_decode_rejects_other_answers(runner, answer):
    with pytest.raises(ValueError):
        runner.decode(answer, ["X", "Y"])


@pytest.mark.parametrize("http_status", [401, 402])
def test_stop_does_not_consume_next_seat_or_retry(runner, tmp_path, http_status):
    rows = [row(runner, tmp_path, str(i), ["X", "Y"]) for i in range(2)]
    dest = freeze(runner, tmp_path, rows)
    requests = []

    def handler(req):
        requests.append(req)
        return httpx.Response(http_status)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        for _ in range(2):
            with runner.writer(dest):
                result = runner.run_locked(dest, client)
            assert result["registered"] == 1 and result["unexecuted"] == 1
            assert result["stopped_http"] == http_status
    assert len(requests) == 1
    assert not (dest / "seats" / runner.sha(b"1")).exists()


def test_preexisting_intent_without_response_is_quarantined(runner, tmp_path):
    r = row(runner, tmp_path, "interrupted", ["X", "Y"], SYNTHETIC_WIRE)
    dest = freeze(runner, tmp_path, [r])
    folder = dest / "seats" / runner.sha(b"interrupted")
    folder.mkdir(parents=True)
    (folder / "intent.json").write_bytes(
        runner.blob({"started_utc": "test", "request_sha256": SYNTHETIC_REQUEST})
    )

    def never(request):
        pytest.fail("A prior ambiguous dispatch must not be sent again")

    with (
        httpx.Client(transport=httpx.MockTransport(never)) as client,
        runner.writer(dest),
    ):
        report = runner.run_locked(dest, client)
    assert report["uncertain_request_count"] == 1 and report["confirmed_requests"] == 0
    assert runner.read(folder / "result.json")["status"] == "interrupted_unknown"


def test_wrong_model_and_malformed_answer_are_explicit(runner):
    for reply, expected in (
        (selected_body(model="different-model"), "unexpected_model"),
        (selected_body(answer="not JSON"), "invalid_response"),
    ):
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda _, body=reply: httpx.Response(200, json=body)
            )
        ) as client:
            result, _ = runner.issue(client, b"synthetic", ["X", "Y"])
        assert result["status"] == expected and result["choice"] is None
        assert result["confirmed_requests"] == 1


@pytest.mark.skipif(
    os.name != "nt", reason="Registered writer uses a Windows byte-range lock"
)
def test_only_one_registered_writer(runner, tmp_path):
    with runner.writer(tmp_path), pytest.raises(OSError), runner.writer(tmp_path):
        pytest.fail("Concurrent writers acquired the same batch")
