from copy import deepcopy
from functools import lru_cache

import pytest
from formal_repair_receipts import digest, read_exit
from harness_v2 import program_stages
from portable_layout_engine import load_engine
from repair import evidence
from repair.test_native_repair import card, leaf


def artifact(raw, errors=()):
    return {
        "sha256": digest(raw),
        "text": raw.decode(),
        "checks": {"errors": list(errors)},
    }


def test_no_artifact_and_source_rejection_are_distinct():
    run = {
        "status": "stopped",
        "first_native": None,
        "final_native": None,
        "exit": {"status": "not_reached", "rounds": []},
    }
    row = read_exit(run, evidence)
    assert row["exit_status"] == "not_reached" and row["before"] is None
    first = artifact(b"{}", ["source"])
    run.update(first_native=first, final_native=first)
    run["exit"]["status"] = "skipped_source_check"
    row = read_exit(run, evidence)
    assert (row["exit_status"], row["before"], row["rounds"]) == (
        "skipped_source_check",
        None,
        [],
    )
    run["final_native"] = None
    with pytest.raises(ValueError, match="availability"):
        read_exit(run, evidence)


@pytest.fixture
def geometry(monkeypatch):
    pytest.importorskip("PIL")
    from portable_layout_smoke import smoke_fonts

    try:
        regular, bold = smoke_fonts()
    except ValueError as exc:
        pytest.skip(str(exc))
    for key in ("SIX_ARMS_MEASURE_PY", "GENUI_ROOT"):
        monkeypatch.delenv(key, raising=False)
    for key, path in (("REGULAR", regular), ("BOLD", bold)):
        monkeypatch.setenv("SIX_ARMS_FONT_" + key, str(path))
        monkeypatch.setattr(program_stages, key, path)
    monkeypatch.setattr(program_stages, "MEASURE_FILE", None)
    monkeypatch.setattr(
        program_stages, "_measure", lru_cache(program_stages._measure.__wrapped__)
    )
    return load_engine().evidence


def synthetic_run(raw, geometry):
    final, report = geometry.native.repair(raw)
    for attempt in report["rounds"]:
        attempt["candidate"] = artifact(
            geometry.encode(geometry.replay_changes(raw, attempt))
        )
    return {
        "first_native": artifact(raw),
        "final_native": artifact(final),
        "status": "synthetic",
        "exit": report,
    }


def test_acceptance_vs_postcheck_rollback(geometry):
    run = synthetic_run(card(["a"], [leaf("a", "X", 10)]), geometry)
    row = read_exit(run, geometry, replay_geometry=True)
    assert row["committed"] and row["rounds"][0]["committed"] and row["after"] == []
    proposal = deepcopy(run["final_native"])
    proposal["checks"]["errors"] = ["test postcheck"]
    run["exit"].update(uncommitted_native=proposal, effective_candidate_committed=False)
    run.update(
        final_native=run["first_native"], failed_stage="post_repair_output_check"
    )
    row = read_exit(run, geometry, replay_geometry=True)
    assert row["rounds"][0]["accepted"] and row["rounds"][0]["rolled_back"]
    assert not row["committed"] and row["after"] == row["before"]


def test_candidate_changes_start_from_original_and_new_is_not_worsened(geometry):
    run = synthetic_run(
        card(["a", "b"], [leaf("a", "X", 10), leaf("b", "Y", 28)], height=54), geometry
    )
    row = read_exit(run, geometry, replay_geometry=True)
    assert row["exit_status"] == "unresolved" and len(row["rounds"]) == 2
    assert row["before"] == row["after"] and all(
        r["rolled_back"] for r in row["rounds"]
    )
    first = run["exit"]["rounds"][0]
    assert first["introduced_by_repair"]
    first["worsened"] = first["introduced_by_repair"]
    with pytest.raises(ValueError, match="delta"):
        read_exit(run, geometry)
    first["candidate"]["text"] += " "
    with pytest.raises(ValueError, match="SHA"):
        read_exit(run, geometry)


def test_unsupported_and_clean_have_different_denominators(geometry):
    clean = read_exit(
        synthetic_run(card(["a"], [leaf("a", "X")]), geometry),
        geometry,
        replay_geometry=True,
    )
    unsupported = read_exit(
        synthetic_run(b"{}", geometry), geometry, replay_geometry=True
    )
    assert (clean["before"], clean["after"]) == ([], [])
    assert (unsupported["before"], unsupported["after"]) == (None, None)
