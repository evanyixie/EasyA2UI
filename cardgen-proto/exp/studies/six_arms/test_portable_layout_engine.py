"""Public synthetic fixtures for the real program stages and native exit."""

import json
import os
import subprocess
import sys
from copy import deepcopy
from functools import lru_cache

import pytest
from portable_layout_engine import HERE, load_engine
from space_allocation import pair_allocations


def test_bounded_allocations_follow_frozen_preference_order():
    pairs = pair_allocations(100, 4)
    assert pairs[:3] == ((48, 48), (38.25, 57.75), (57.5, 38.5))
    assert all(a + b == 96 and a > 4 and b > 4 for a, b in pairs)
    assert len(set(pairs)) == len(pairs)
    assert pair_allocations(8, 0) == ()
    with pytest.raises(ValueError):
        pair_allocations(20.1, 3)


def demo_fonts():
    pytest.importorskip("PIL")
    from portable_layout_smoke import smoke_fonts

    try:
        return smoke_fonts()
    except ValueError as e:
        pytest.skip(str(e))


def test_two_synthetic_sizes_in_fresh_process(tmp_path):
    regular, bold = demo_fonts()
    env = {
        key: os.environ[key]
        for key in ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "LANG", "LC_ALL")
        if key in os.environ
    }
    cmd = [
        sys.executable,
        "-B",
        str(HERE / "portable_layout_smoke.py"),
        "--regular",
        str(regular),
        "--bold",
        str(bold),
    ]
    result = subprocess.run(
        cmd, check=True, stdout=subprocess.PIPE, env=env, cwd=tmp_path
    )
    receipt = json.loads(result.stdout)
    assert receipt["new_model_calls"] == receipt["new_device_calls"] == 0
    assert [(c["size"], c["data_items"], c["actions"]) for c in receipt["cases"]] == [
        ("2x2", 1, 1),
        ("2x4", 2, 1),
    ]
    for case in receipt["cases"]:
        assert case["policy_decisions"] == {"compatible": "pass", "standard": "pass"}
        assert case["first_sha256"] == case["final_sha256"]


def test_exit_retains_source_rejection_repair_candidates_and_unknown(monkeypatch):
    regular, bold = demo_fonts()
    from harness_v2 import program_stages as program
    from portable_enhanced_layout import advance
    from portable_layout_smoke import samples

    for key in ("SIX_ARMS_MEASURE_PY", "GENUI_ROOT"):
        monkeypatch.delenv(key, raising=False)
    for key, value in (("REGULAR", regular), ("BOLD", bold)):
        monkeypatch.setenv("SIX_ARMS_FONT_" + key, str(value))
        monkeypatch.setattr(program, key, value)
    monkeypatch.setattr(program, "MEASURE_FILE", None)
    monkeypatch.setattr(program, "_measure", lru_cache(program._measure.__wrapped__))
    engine = load_engine()
    source, content = next(samples(engine))
    messages = engine.program.program_route(content)
    for phase in ("geometry", "theme", "emit"):
        messages = advance(engine, phase, content, messages, source)

    def mutate(modification):
        updated = deepcopy(messages)
        button = next(
            n
            for n in updated[1]["updateComponents"]["components"]
            if n["component"] == "Button"
        )
        modification(button)
        state = {"entry": {"status": "valid_unchanged"}}
        engine._finish(updated, source, state)
        return state

    wrong_action = mutate(
        lambda b: b.update(onClick=[{"call": "anotherAction", "args": {}}])
    )
    assert wrong_action["status"] == "artifact_checks_rejected"
    assert wrong_action["exit"]["status"] == "skipped_source_check"
    repaired = mutate(lambda b: b["styles"].update(height=5))
    assert repaired["status"] == "accepted"
    assert repaired["exit"]["status"] == "repaired"
    assert repaired["first_native"]["sha256"] != repaired["final_native"]["sha256"]
    assert repaired["exit"]["rounds"][-1]["candidate"] == repaired["final_native"]
    unknown = mutate(lambda b: b["styles"].update(unregisteredStyle=1))
    assert unknown["status"] == "geometry_unknown"
    assert unknown["exit"]["status"] == "unsupported"
