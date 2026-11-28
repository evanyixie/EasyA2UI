"""只用合成首轮回执验证分母、分位数、用量与离线回放的区分。"""

import json
import sys
from pathlib import Path

import pytest

import summarize_timing as timing


def put(base, name, value):
    path = base / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf8")
    return timing.sha(path)


def make_batch(root, mode):
    code = "private-synthetic-id"
    line = "a" * 64
    queue = [{"task_id": code, "input_line_sha256": line, "execute": "AB", "n": 1}]
    live = mode == "live"
    hashes = {}
    arm_hashes = {}
    lock = {
        "mode": mode,
        "arms": dict(zip("AB", timing.ARMS, strict=True)),
        "queue": queue,
        "dependencies": {
            "fixed_layout/run.py": timing.sha(Path(timing.__file__).with_name("run.py"))
        },
    }
    freeze = put(root, "freeze.json", lock)
    prep = {
        "status": "accepted",
        "source_row_sha256": line,
        "shared_sha256": "b" * 64,
        "reference_sha256": "c" * 64,
        "adapter_wall_ms": 1,
        "reference_wall_ms": 2,
    }
    key = f"results/{code}/input_receipt.json"
    hashes[key] = put(root, key, prep)
    for arm in timing.ARMS:
        prefix = f"results/{code}/{arm}/"
        rec = {
            "source_row_sha256": line,
            "shared_sha256": prep["shared_sha256"],
            "reference_sha256": prep["reference_sha256"],
            "cell": arm,
            "task_id": code,
            "first_pass": True,
            "status": "artifact_ready",
            "emit_wall_ms": 1,
            "started_utc": "2020-01-01T00:00:00Z",
            "ended_utc": "2020-01-01T00:00:01Z",
        }
        for phase in timing.STAGES:
            item = {"status": "accepted", "wall_ms": 3}
            if arm == "model_model":
                item.update(
                    request_dir=f"calls/{phase}",
                    prompt_sha256="d" * 64,
                    http_status=200 if live else None,
                    http_ms=2 if live else None,
                )
                call = {
                    "stage": phase,
                    **{k: item[k] for k in ("prompt_sha256", "http_status", "http_ms")},
                    "physical_attempts": 1 if live else 0,
                    "usage": None,
                }
                if live:
                    call["usage"] = (
                        {"prompt_tokens": 11, "total_tokens": 14}
                        if phase == "structure"
                        else None
                    )
                    body = prefix + f"calls/{phase}/response.body"
                    hashes[body] = put(root, body, {"usage": call["usage"]})
                    call.update(state="response_recorded", envelope_sha256=hashes[body])
                else:
                    call["source"] = "offline_fixture_or_replay"
                key = prefix + f"calls/{phase}/call.json"
                hashes[key] = put(root, key, call)
            rec[phase] = item
        key = prefix + "receipt.json"
        arm_hashes[key] = put(root, key, rec)
    put(
        root,
        "seal.json",
        {
            "freeze_sha256": freeze,
            "arm_receipt_sha256": arm_hashes,
            "receipts_count": 2,
            "evidence_sha256": {**hashes, **arm_hashes},
        },
    )
    return code


@pytest.mark.parametrize("mode", ["offline_replay", "live"])
def test_live_and_replay_have_distinct_call_accounts(tmp_path, mode):
    private = make_batch(tmp_path, mode)
    summary = timing.build(tmp_path)
    assert private not in json.dumps(summary)
    assert summary["denominators"]["both_raw_artifacts"] == 1
    model = summary["cohorts"]["paired_raw_artifacts"]["model_model"]
    assert model["arm_host_interval_ms"]["p95_ms"] == 1000
    if mode == "offline_replay":
        assert (
            model["http"] is None
            and model["physical_model_requests"] == 0
            and model["offline_stage_records"] == 2
        )
    else:
        group = model["http"]["all_calls"]
        assert group["physical_attempts_known"] == 2
        assert group["tokens"]["total_tokens"] == {
            "observed_calls": 1,
            "missing_calls": 1,
            "known_sum": 14,
        }
        assert group["tokens"]["completion_tokens"]["known_sum"] is None
    assert (
        summary["cohorts"]["paired_raw_artifacts"]["program_program"]["model_calls"]
        == 0
    )


def test_no_overwrite_or_unverifiable_receipt(tmp_path, monkeypatch):
    root = tmp_path / "batch"
    code = make_batch(root, "live")
    target = tmp_path / "summary.json"
    monkeypatch.setattr(
        sys, "argv", ["summarize_timing.py", "--root", str(root), "--out", str(target)]
    )
    timing.main()
    previous = target.read_bytes()
    assert json.loads(previous)["denominators"]["both_raw_artifacts"] == 1
    with pytest.raises(ValueError, match="已存在"):
        timing.main()
    assert target.read_bytes() == previous
    path = root / f"results/{code}/model_model/calls/structure/call.json"
    call = timing.read(path)
    call["usage"]["total_tokens"] = 99
    put(root, path, call)
    with pytest.raises(ValueError, match="证据摘要"):
        timing.build(root)


def test_interpolation_and_incomplete_timing():
    stats = timing.describe([None, 1, 3], 4)
    assert (stats["p50_ms"], stats["p95_ms"]) == (2, 2.9)
    assert (stats["known"], stats["missing"], stats["not_executed"]) == (2, 1, 1)
    assert timing.describe([None], 2)["p95_ms"] is None
    assert (
        timing.arm_interval(
            {"structure": {"replayed_from_persisted_call": True}, "geometry": None}
        )
        is None
    )


def test_restored_stage_keeps_incomplete_public_arm_interval_unknown():
    r = {
        "started_utc": "2020-01-01T00:00:02Z",
        "ended_utc": "2020-01-01T00:00:04Z",
        "structure": {"started_utc": "2020-01-01T00:00:01Z"},
        "geometry": None,
    }
    assert timing.arm_interval(r, "live") is None
    assert timing.arm_interval(r, "historical_live") == 2000
