from pathlib import Path

import pytest


@pytest.fixture
def census(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import button_pixel_census

    return button_pixel_census


def test_unobservable_and_literal_dots(census):
    row = {
        "state": "cropped",
        "blind_id": "x",
        "source_label": "Open",
        "native_text": "Open",
        "source_label_ellipsis": False,
    }
    yes, no = {"x": "ellipsis"}, {"x": "no_ellipsis"}
    assert census.observed(row, yes, yes) == "ellipsis"
    assert census.observed(row, yes, no) == "unknown"
    assert (
        census.observed({**row, "source_label_ellipsis": True}, yes, yes) == "unknown"
    )
    assert census.observed({**row, "native_text": ""}, no, no) == "unknown"
    assert census.observed({**row, "state": "outside_or_clipped"}, {}, {}) == "unknown"
    assert census.classify_card(["unknown", "ellipsis"], True) == "ellipsis"
    assert census.endpoint(True, "no_button") == (1, 1)
    assert census.endpoint(True, "unknown") == (0, 1)
    assert census.endpoint(None, "no_artifact") == (0, 1)
    assert census.endpoint(None, "ellipsis") == (0, 0)


def test_paired_uncertainty_and_cross_checkpoint_reuse(census):
    seats, buttons, tech = [], [], []
    for arm in census.ARMS:
        for cp in census.CHECKPOINTS:
            row = {"task": "a", "arm": arm, "checkpoint": cp, "artifact_sha256": "src"}
            has_button = arm in ("L5", "L6")
            seats.append({**row, "source_button_count": int(has_button)})
            tech.append(
                {
                    "task_id": "a",
                    "arm": arm,
                    "checkpoint": cp,
                    "artifact_sha256": "src",
                    "tech_pass": has_button,
                }
            )
            if has_button:
                buttons.append(
                    {
                        **row,
                        "button_id": "first",
                        "source_label": "Open",
                        "source_label_ellipsis": False,
                        "native_text": "Open",
                        "state": "cropped",
                        "blind_id": arm,
                    }
                )
    read = [
        {"blind_id": "L5", "verdict": "uncertain"},
        {"blind_id": "L6", "verdict": "ellipsis"},
    ]
    executions = [
        {
            "task_id": "a",
            "arm": arm,
            "status": "accepted" if arm in ("L5", "L6") else "stage_rejected",
        }
        for arm in census.ARMS
    ]
    result = census.summarize(seats, buttons, read, read, tech, executions)
    assert result["distinct_button_crops_read"] == 2
    paired = result["paired"][census.CHECKPOINTS[0]]["L5_L6"]
    assert (paired["left_minus_right_min"], paired["left_minus_right_max"]) == (0, 1)
    with pytest.raises(ValueError, match="Incomplete blinded readings"):
        census.summarize(seats, buttons, read[:1], read, tech, executions)
    with pytest.raises(ValueError, match="Duplicate"):
        census.summarize(seats, buttons + [buttons[0]], read, read, tech, executions)


def test_caption_multiset_missing_artifacts_and_unknown_reasons(census):
    # Reordering keeps the first multiset; repeating a different label changes the second.
    pair_labels = [
        (["A", "A", "B"], ["B", "A", "A"]),
        (["A", "A", "B"], ["B", "B", "A"]),
        (["A"], None),
        (None, ["A"]),
        (None, None),
        (None, ["clipped", "absent", "unimaged"]),
    ]
    no_pixel = {
        "clipped": "outside_or_clipped",
        "absent": "button_absent",
        "unimaged": "no_capture",
    }
    seats, buttons, technical, executions = [], [], [], []
    for i, (lhs, rhs) in enumerate(pair_labels):
        for arm in census.ARMS:
            labels = {"L5": lhs, "L6": rhs}.get(arm)
            executions.append(
                {
                    "task_id": i,
                    "arm": arm,
                    "status": "accepted" if labels else "stage_rejected",
                }
            )
            for cp in census.CHECKPOINTS:
                base = {
                    "task": i,
                    "arm": arm,
                    "checkpoint": cp,
                    "artifact_sha256": "src" if labels else None,
                }
                seats.append(
                    {**base, "source_button_count": len(labels) if labels else None}
                )
                technical.append(
                    {
                        "task_id": i,
                        "arm": arm,
                        "checkpoint": cp,
                        "artifact_sha256": base["artifact_sha256"],
                        "tech_pass": bool(labels),
                    }
                )
                for j, label in enumerate(labels or []):
                    buttons.append(
                        {
                            **base,
                            "button_id": str(j),
                            "source_label": label,
                            "native_text": label,
                            "source_label_ellipsis": False,
                            "state": no_pixel.get(label, "cropped"),
                            "blind_id": None if label in no_pixel else "yes",
                        }
                    )
    vote = [{"blind_id": "yes", "verdict": "ellipsis"}]
    result = census.summarize(seats, buttons, vote, vote, technical, executions)
    for cp in census.CHECKPOINTS:
        pair = result["paired"][cp]["L5_L6"]
        assert pair["artifact_availability"] == {
            "both": 2,
            "left_only": 1,
            "right_only": 2,
            "neither": 1,
        }
        assert (
            pair["left_ellipsis_right_no_artifact"]
            == pair["left_no_artifact_right_ellipsis"]
            == 1
        )
        assert pair["left_ellipsis_right_ellipsis"] == 2
        assert (
            pair["determinate_same_captions_with_multiplicity"]
            == pair["same_captions_left_ellipsis_right_ellipsis"]
            == 1
        )
        assert result["button_unknown_by_reason"][cp]["all"] == dict.fromkeys(
            no_pixel.values(), 1
        )
