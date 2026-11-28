from pathlib import Path

import pytest


@pytest.fixture
def modes(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import failure_modes

    return failure_modes


def rejected(phase, message):
    return {
        "status": "stage_rejected",
        "failed_stage": phase,
        "stages": [
            {"stage": phase, "status": "stage_rejected", "error": {"message": message}}
        ],
    }


def test_terminal_cause_uses_first_recorded_failure_and_preserves_unknown(modes):
    terminal_reason = modes.terminal_reason
    assert terminal_reason(
        rejected("content", "items[0] 动态 text 与本路径首帧值不一致")
    ) == ("content", "first_frame_value")
    assert terminal_reason(
        rejected("geometry", "reference_capacity: 完整文字需要 3 行，组件最多允许 2 行")
    ) == ("geometry", "component_lines")
    assert terminal_reason(
        {
            "status": "geometry_unknown",
            "failed_stage": "reference_geometry",
            "exit": {"why": "首帧无法解引用 /an/example"},
        }
    ) == ("unknown", "first_frame_unresolved")
    assert terminal_reason(
        {
            "status": "geometry_unresolved",
            "failed_stage": "reference_geometry",
            "exit": {
                "after": [
                    {"code": "lines"},
                    {"code": "text_height"},
                    {"code": "container_width"},
                ]
            },
        }
    ) == ("reference_geometry", "text_and_container")
    with pytest.raises(ValueError, match="Unrecognized"):
        terminal_reason(rejected("content", "a new rule"))


def test_seats_are_paired_by_task_and_arm_and_report_only_counts(modes):
    seats, records = [], []
    for arm in modes.ARMS:
        outcome = {"status": "accepted", "failed_stage": None}
        if arm == "L6":
            outcome = rejected("content", "items[1].label 含无来源数字 ['3']")
        outcome["arm"] = arm
        seats.append(
            {
                "arm": arm,
                "task_id": "private-key",
                "state": "terminal",
                "status": outcome["status"],
                "failed_stage": outcome["failed_stage"],
            }
        )
        records.append({"arm": arm, "task": "private-key", "execution": outcome})
    result = modes.summarize(seats, reversed(records))
    assert result["l5_l6_paired_stopping_points"] == [
        {"L5": "accepted", "L6": "content", "tasks": 1}
    ]
    assert result["terminal_seats"] == 6
    assert "private-key" not in str(result)
    with pytest.raises(ValueError, match="Missing original"):
        modes.summarize(seats, records[:-1])
    with pytest.raises(ValueError, match="conflicting"):
        modes.summarize(seats, records + records[:1])


def test_native_identity_and_unique_class(modes):
    native_class = modes.native_class
    good, finding, incomplete = modes.NATIVE_CLASSES
    observed = {"execution": {"status": "native_captured"}, "artifact_sha256": "same"}
    original = {"execution": {"final_native": {"sha256": "same"}}}
    screen = {
        "capture": True,
        "artifact_sha256": "same",
        good: True,
        finding: False,
        incomplete: False,
    }
    assert native_class(screen, observed, original) == good
    with pytest.raises(ValueError, match="Ambiguous"):
        native_class({**screen, finding: True}, observed, original)
    with pytest.raises(ValueError, match="artifact"):
        native_class({**screen, "artifact_sha256": "other"}, observed, original)
