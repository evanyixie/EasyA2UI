from types import SimpleNamespace

import pytest
from six_arms import formal_fixed_geometry_replay as replay


def stage_engine(fail=None):
    calls = []

    def wire(stage, content, tree, source):
        calls.append((stage, content, tree, source))
        if stage == fail:
            raise ValueError("unavailable")
        return stage + "_product"

    def finish(messages, source, result):
        assert messages == "emit_product" and source == {"size": "2x2"}
        result["status"] = "accepted"

    return (
        SimpleNamespace(
            _program_wire=wire,
            model=SimpleNamespace(parse_output=lambda stage, raw, *args: raw),
            STAGE_ERRORS=(ValueError,),
            _finish=finish,
        ),
        calls,
    )


def test_tail_preserves_the_supplied_tree_and_stage_order():
    eng, calls = stage_engine()
    source, content, tree = {"size": "2x2"}, {"items": []}, {"root": "original"}
    assert replay.replay_tail(eng, source, content, tree, {})["status"] == "accepted"
    assert [(p, t) for p, _, t, _ in calls] == [
        ("geometry", tree),
        ("theme", "geometry_product"),
        ("emit", "theme_product"),
    ]
    assert all(c is content and s is source for _, c, _, s in calls)


def test_geometry_rejection_never_emits_a_replacement():
    eng, calls = stage_engine("geometry")
    run = replay.replay_tail(eng, {}, {}, {}, {})
    assert [r[0] for r in calls] == ["geometry"]
    assert run["status"] == "stage_rejected" and run["failed_stage"] == "geometry"
    assert run["first_native"] is None and run["final_native"] is None


@pytest.mark.parametrize(
    ("status", "state"), [("stage_rejected", "fail"), ("callback_failed", "missing")]
)
def test_common_unreached_branches_preserve_unknown(tmp_path, status, state):
    files = {k: tmp_path / k for k in ("first", "final")}
    run = {
        "status": status,
        "failed_stage": "content",
        "first_native": None,
        "final_native": None,
        "exit": {"status": "not_reached", "rounds": []},
    }
    historical = {
        "status": status,
        "failed_stage": "content",
        "exit": "not_reached",
        "first_sha": None,
        "final_sha": None,
    }
    side = replay.branch(run, historical, files, None)
    assert side["first_technical"] == side["final_technical"] == state
    files["first"].write_bytes(b"unregistered")
    with pytest.raises(ValueError, match="Unregistered"):
        replay.branch(run, historical, files, None)


def test_custody_card_is_bound_to_its_full_original_bytes(tmp_path):
    wire = b"one\r\ntwo\r\n"
    sha = replay.digest(wire)
    card = {"text": wire.decode(), "sha256": sha, "checks": {"errors": []}}
    files = {k: tmp_path / k for k in ("first", "final")}
    for path in files.values():
        path.write_bytes(wire)
    evidence = SimpleNamespace(native=SimpleNamespace(MAX_ROUNDS=2))
    run = {
        "status": "accepted",
        "failed_stage": None,
        "first_native": card,
        "final_native": card,
        "exit": {
            "status": "no_change",
            "rounds": [],
            "before": [],
            "after": [],
            "maximum_rounds": 2,
        },
    }
    historical = {
        "status": "accepted",
        "failed_stage": None,
        "exit": "no_change",
        "first_sha": sha,
        "final_sha": sha,
    }
    side = replay.branch(run, historical, files, evidence)
    assert side["final_technical"] == side["first_technical"] == "pass"
    assert side["final"] == side["first"] == wire
    files["final"].write_bytes(wire.replace(b"\r\n", b"\n"))
    with pytest.raises(ValueError, match="hash mismatch"):
        replay.branch(run, historical, files, evidence)
