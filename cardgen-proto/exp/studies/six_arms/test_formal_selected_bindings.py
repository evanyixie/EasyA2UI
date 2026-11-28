from pathlib import Path

import pytest


@pytest.fixture
def audit(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import formal_selected_bindings

    return formal_selected_bindings


def seat(task, arm, wanted, *, emitted, matched=()):
    paths = frozenset(wanted) if wanted is not None else None
    present = paths if emitted and paths else frozenset()
    return {
        "task": task,
        "arm": arm,
        "wanted": paths,
        "emitted": emitted,
        "captured": emitted,
        "exit_reason": "stage_rejected/geometry",
        "present": present,
        "confirmed": frozenset(matched),
        "entry": "stage_rejected" if wanted is None else "valid_unchanged",
        "absent": frozenset(),
        "unresolved": frozenset(),
    }


def test_all_seats_and_accepted_path_denominators(audit):
    rows = [
        seat("r", "L5", None, emitted=False),
        seat("a", "L5", {"/x", "/y"}, emitted=False),
        seat("b", "L5", [], emitted=True),
        seat("c", "L5", {"/x", "/y"}, emitted=True, matched=["/x"]),
    ]
    result = audit.counts(rows)
    n = result["counts"]
    assert n["seats"] == 4 and n["accepted_selections"] == 3
    assert (
        n["selected_task_paths"] == 4 and n["selected_task_paths_without_artifact"] == 2
    )
    assert (
        n["accepted_without_dynamic_paths"] == 1 and n["all_selected_referenced"] == 1
    )
    assert (
        n["native_confirmed_task_paths"] == 1
        and n["all_selected_native_confirmed"] == 0
    )


def test_same_path_pairs_keep_one_sided_artifacts_and_separate_missing_control(audit):
    rows = [
        seat("a", "L5", ["/x"], emitted=True, matched=["/x"]),
        seat("a", "L6", ["/x"], emitted=False),
        seat("b", "L5", ["/x"], emitted=True, matched=["/x"]),
        seat("b", "L6", ["/x"], emitted=True),
        seat("c", "L5", ["/x"], emitted=True, matched=["/x"]),
        seat("c", "L6", ["/y"], emitted=True, matched=["/y"]),
    ]
    result = audit.paired(rows, "L5", "L6")
    assert result["assigned"] == 3 and result["same_nonempty_selected_path_set"] == 2
    assert result["artifact_availability_on_same_nonempty_set"] == {
        "both": 1,
        "only_first": 1,
    }
    assert (
        result["both_emitted_same_nonempty_set"] == result["only_first_confirmed"] == 1
    )
    with pytest.raises(ValueError, match="Duplicate"):
        audit.paired([*rows, rows[0]], "L5", "L6")
