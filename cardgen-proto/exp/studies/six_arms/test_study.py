"""冻结、离线执行与回放的合成回归。开发原输入、远端服务和设备均无需访问。"""

import pytest

import choice
import emit_fidelity
import paired_replay
import study


def test_complete_synthetic_arms_and_emission(tmp_path):
    batch, out = tmp_path / "run", tmp_path / "replayed"
    arms = ("L1", "L2", "L3", "L4")
    study.freeze(study.FIXTURE, batch, arms)
    study.execute(batch, "fixture")
    assert study.replay(batch, None, out)
    rows = study.frozen_calls.read(out / "replay.json")["seats"]
    assert {r["arm"]: len(r["requests"]) for r in rows} == {
        "L1": 1,
        "L2": 5,
        "L3": 4,
        "L4": 3,
    }
    assert all(
        r["card_bytes_equal"] and r["original_status"] == "artifact_checks_pass"
        for r in rows
    )
    pairs = paired_replay.run_pairs(batch, tmp_path / "paired", ("L2", "L3"))
    assert all(row["status"] == "compared" for row in pairs["rows"])
    assert pairs["timing"]["emit"]["model_http_ms"]["median"] is None
    counts = emit_fidelity.audit_run(batch)["counts"]
    assert counts == {
        arm: {"not_applicable_one_shot" if arm == "L1" else "matched": 1}
        for arm in arms
    }
    call = batch / "garden-demo/L2/content/response.txt"
    call.write_bytes(call.read_bytes() + b" ")
    assert not study.replay(batch, None, tmp_path / "changed")
    changed = study.frozen_calls.read(tmp_path / "changed/replay.json")["seats"]
    assert (
        next(r["result"] for r in changed if r["arm"] == "L2")
        == "unsealed_or_changed_archive"
    )


def test_missing_seat_or_changed_source(tmp_path):
    batch = tmp_path / "run"
    study.freeze(study.FIXTURE, batch, ("L1",))
    assert not study.replay(batch, None, tmp_path / "missing")
    assert (
        study.frozen_calls.read(tmp_path / "missing/replay.json")["seats"][0]["result"]
        == "unexecuted"
    )
    (batch / "sources/garden-demo.json").write_bytes(b"{}")
    with pytest.raises(ValueError):
        study.verified(batch)


def test_every_model_request_must_match_its_original_seat(tmp_path):
    batch = tmp_path / "run"
    study.freeze(study.FIXTURE, batch, ("L2",))
    study.execute(batch, "fixture")
    calls = study.frozen_calls.FrozenCalls(batch, "garden-demo", "L2", synthetic=True)
    with pytest.raises(
        study.frozen_calls.MissingHistoricalResponse, match="different_messages"
    ):
        calls("content", [{"role": "user", "content": "无关请求"}])
    with pytest.raises(ValueError, match="重复调用"):
        calls("content", [])


def test_l5_l6_with_external_reference_engine(tmp_path):
    try:
        study.program_stages.measurement_files()
    except RuntimeError:
        pytest.skip("需设置外部参考测量模块与两份字体文件")
    batch = tmp_path / "run"
    study.freeze(study.FIXTURE, batch, ("L4", "L5", "L6"))
    study.execute(batch, "fixture")
    assert study.replay(batch, None, tmp_path / "replay")
    rows = study.frozen_calls.read(tmp_path / "replay/replay.json")["seats"]
    assert all(row["card_bytes_equal"] for row in rows)
    assert {r["arm"]: len(r["requests"]) for r in rows} == {"L4": 3, "L5": 2, "L6": 1}
    result = paired_replay.run_pairs(batch, tmp_path / "geometry", ("L4",))
    assert result["rows"][0]["recorded_model"]["reproduced_original_bytes"]


def test_content_only_replay_and_unknown(tmp_path):
    batch = tmp_path / "choice"
    choice.freeze(study.FIXTURE, batch)
    start = choice.perform(batch, "score")
    assert start["groups"]["all"]["model"]["unknown_cases"] == 1
    assert start["groups"]["all"]["program"]["unknown_cases"] == 1
    program = choice.perform(batch, "program")
    assert program["groups"]["all"]["program"]["valid"] == 1
    assert program["groups"]["all"]["model"]["unknown_cases"] == 1
    done = choice.perform(batch, "fixture")
    assert done == choice.perform(batch, "score")
    assert done["model_source"] == "fixture"
    assert done["rows"][0]["model"]["receipt"]["physical_attempts"] == 0
    assert done["groups"]["all"]["model"]["all_required_cases"] == 1
    archive = batch / "garden-demo/calls/content_only/response.txt"
    archive.write_bytes(b"{}")
    with pytest.raises(ValueError, match="首答投影"):
        choice.perform(batch, "score")
