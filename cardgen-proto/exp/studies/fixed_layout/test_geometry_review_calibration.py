import pytest
from geometry_review_calibration import summarize


def seat(task, arm, geometry, votes):
    return {
        "task": task,
        "arm": arm,
        "geometry": geometry,
        "original": votes,
        "final": votes,
        "image_sha256": "a" * 64,
    }


def test_shared_image_preserves_task_pairs_and_missing_vote():
    rows = [
        seat("a", "model_model", "mismatch", ["pass", "pass"]),
        seat("a", "program_program", "verified", ["fail", "fail"]),
        seat("b", "model_model", "verified", [None, "fail"]),
    ]
    result = summarize(rows)
    final = result["final"]
    assert result["pictured_seats"] == 3 and result["unique_images"] == 1
    assert final["paired_technical_vs_human"] == {"program_program/model_model": 1}
    assert final["seats"]["verified"] == {"both_fail": 1, "unresolved": 1}
    assert final["equal_weight_per_image"]["mismatch"]["both_pass"] == pytest.approx(1 / 3, abs=1e-4)


def test_duplicate_seat_cannot_be_treated_as_another_vote():
    row = seat("a", "model_model", "verified", ["fail", "pass"])
    with pytest.raises(ValueError, match="Duplicate seat"):
        summarize([row, row])
