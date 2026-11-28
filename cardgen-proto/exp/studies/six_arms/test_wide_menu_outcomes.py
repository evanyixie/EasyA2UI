import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import wide_menu_outcomes

    return wide_menu_outcomes


def test_sealed_first_choice_and_oracle(study, tmp_path, monkeypatch):
    runner = study.menu_model_runner

    def store(path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        data = runner.blob(obj)
        path.write_bytes(data)
        return study.digest(data)

    cohort, program, rows, replies = [], {}, [], []
    for i, (state, opts, response) in enumerate(
        [
            ("multiple", ["good", "bad"], '{"choice":"bad"}'),
            ("multiple", ["unclear", "bad"], '{"choice":"unclear"}'),
            ("multiple", ["bad", "good"], '{"choice":"bad","choice":"good"}'),
            ("multiple", ["bad", "good"], None),
            ("forced", ["good"], None),
            ("empty", [], None),
            ("content_transport_unknown", [], None),
            ("content_rejected", [], None),
        ]
    ):
        tid = f"synthetic-{i}"
        case = {
            "task_id": tid,
            "status": state,
            "family": f"group-{i // 2}",
            "options": opts,
        }
        cohort.append(case)
        if not opts:
            continue
        file = tmp_path / "shared" / f"{tid}.json"
        wire_sha = store(
            file,
            {
                "canvas": {"width_vp": 300, "height_vp": 150},
                "content": {},
                "choices": [{"id": k, "tree": {"id": k}} for k in opts],
            },
        )
        case["wire_sha256"] = wire_sha
        case["private_input_sha256"] = store(
            tmp_path / "private_inputs" / f"{tid}.json",
            {"source": {}, "entry": {"status": "valid"}},
        )
        program[tid] = {"choice": opts[0], "elapsed_ms": i + 1, "wire_sha256": wire_sha}
        if state == "forced":
            continue
        index_row = {
            "task_id": tid,
            "options": opts,
            "wire_sha256": wire_sha,
            "wire_path": str(file),
        }
        rows.append(index_row)
        if response is None:
            continue
        seat = tmp_path / "model" / "seats" / study.digest(tid.encode())
        messages = [
            {"role": "system", "content": runner.SYSTEM},
            {"role": "user", "content": file.read_text()},
        ]
        req = store(seat / "request.json", {**runner.SERVICE, "messages": messages})
        store(seat / "intent.json", {"request_sha256": req})
        valid = i != 2
        usage = {"total_tokens": 12, "prompt_tokens": 9, "completion_tokens": 3}
        receipt = {
            "decision_ms": i + 31,
            "http_ms": i + 30,
            "http_status": 200,
            "local_intents": 1,
            "actual_model": runner.SERVICE["model"],
            "status": "selected" if valid else "invalid_response",
            "choice": json.loads(response)["choice"] if valid else None,
            "usage": usage,
            "confirmed_requests": 1,
            "request_id": f"id-{i}",
        }
        response_body = {
            "choices": [{"message": {"content": response}}],
            "usage": usage,
            "model": runner.SERVICE["model"],
        }
        store(seat / "http.json", {"receipt": receipt, "answer": response_body})
        item = {**receipt, **{k: v for k, v in index_row.items() if k != "wire_path"}}
        store(seat / "result.json", item)
        replies.append(item)
    idx = store(tmp_path / "index.json", {"rows": rows})
    store(
        tmp_path / "model/plan.json",
        {
            "rows": len(rows),
            "index_sha256": idx,
            "service": runner.SERVICE,
            "system": runner.SYSTEM,
            "endpoint": runner.API,
            "attempts_per_multi_choice": 1,
            "runner_sha256": study.digest(Path(runner.__file__).read_bytes()),
        },
    )
    ch = store(tmp_path / "cohort.private.json", {"cases": cohort})
    ph = store(tmp_path / "program_choices.json", program)
    answer_log = b"".join(runner.blob(r) for r in replies)
    (tmp_path / "model/choices.jsonl").write_bytes(answer_log)
    mh = study.digest(answer_log)
    calls = []

    def score(engine, content, source, entry, tree):
        calls.append(tree["id"])
        return SimpleNamespace(
            strict_verdict={"good": "pass", "bad": "fail", "unclear": "unknown"}[
                tree["id"]
            ]
        )

    monkeypatch.setattr(study.portable_enhanced_layout, "score_tree", score)
    monkeypatch.setattr(study, "measure_identity", lambda engine: {})
    private = tmp_path / "decisions.jsonl"
    out = study.evaluate(
        tmp_path, ch, ph, mh, None, expected_tasks=8, private_rows=private
    )
    assert len(private.read_text().splitlines()) == 8
    assert len(calls) == out["candidate_count"] == 9
    assert out["multiple"]["tasks"] == 4
    assert out["all_assigned"]["shared_unknown_pairs_contribute_zero_difference"] == 2
    assert out["all_assigned"]["program_minus_model_pass_count_bounds"] == [0, 1]
    assert out["multiple_with_known_pass_and_fail"]["tasks"] == 3
    assert out["requests"]["known_tokens"]["total_tokens"] == 36
    assert out["choice_timing_multiple"]["paired_model_minus_program"] == {
        "n": 3,
        "median_ms": 30,
    }
    assert out["choice_dispositions_multiple"] == {
        "selected": 2,
        "invalid_choice": 1,
        "not_attempted": 1,
    }
    # Any compromised menu invalidates the entire join before a single candidate is judged.
    calls.clear()
    (tmp_path / "shared/synthetic-1.json").write_text("{}")
    with pytest.raises(ValueError, match="Digest"):
        study.evaluate(tmp_path, ch, ph, mh, None, expected_tasks=8)
    assert not calls


def test_known_http_failure_and_uncertain_transport(study, tmp_path):
    runner = study.menu_model_runner
    wire = b"{}"
    task = "synthetic-transport"
    folder = tmp_path / "model/seats" / study.digest(task.encode())
    folder.mkdir(parents=True)
    plan = {"system": runner.SYSTEM, "service": runner.SERVICE}
    messages = [
        {"role": "system", "content": runner.SYSTEM},
        {"role": "user", "content": "{}"},
    ]
    raw = runner.blob({**runner.SERVICE, "messages": messages})
    (folder / "request.json").write_bytes(raw)
    (folder / "intent.json").write_text(
        json.dumps({"request_sha256": study.digest(raw)})
    )
    for code, disposition in [(401, "http_error"), (None, "transport_unknown")]:
        receipt = {
            "http_status": code,
            "http_ms": 2,
            "decision_ms": 3,
            "confirmed_requests": 1 if code else None,
            "status": "transport_unknown",
            "choice": None,
        }
        row = {**receipt, "task_id": task, "local_intents": 1}
        (folder / "result.json").write_text(json.dumps(row))
        (folder / "http.json").write_text(
            json.dumps({"receipt": receipt, "answer": None})
        )
        assert study.verify_receipt(tmp_path, plan, row, wire) == disposition
