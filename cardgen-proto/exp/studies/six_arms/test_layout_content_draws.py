import pytest
from layout_content_draws import DONORS, summarize


def rows(task, values):
    return [
        {
            "task": task,
            "donor": donor,
            "status": status,
            "model": model,
            "program": program,
        }
        for donor, (status, model, program) in zip(DONORS, values, strict=True)
    ]


def test_missing_structure_preserves_observed_program_result_and_pair_denominator():
    incomplete = rows(
        "sample",
        [
            ("structure_unknown", None, True),
            ("content_unknown", None, None),
            ("content_rejected", None, None),
            ("ready", False, True),
        ],
    )
    ready = rows("complete", [("ready", True, False)] * 4)
    result = summarize(incomplete + ready)
    pairs = result["all"]
    assert (pairs["assigned_draws"], pairs["compared"]) == (8, 5)
    assert (pairs["model_only"], pairs["program_only"]) == (4, 1)
    assert pairs["program_pass_when_model_structure_unknown"] == 1
    assert result["tasks_by_complete_pairs"] == {1: 1, 4: 1}
    assert result["tasks_with_four_complete_pairs"] == [
        {"model_passes": 4, "program_passes": 0, "tasks": 1}
    ]


def test_four_observations_from_same_task_require_all_four_donors():
    records = rows("sample", [("ready", False, False)] * 4)
    with pytest.raises(ValueError, match="donor"):
        summarize(records[:3] + records[:1])


def test_unobserved_content_and_structure_have_different_attainable_differences():
    from augmented_content_draws import POLICIES, aggregate

    def each(value):
        return dict.fromkeys(POLICIES, value)

    samples = [
        {"task": "a", "status": "content_rejected"},
        {"task": "b", "status": "content_unknown"},
        {
            "task": "c",
            "status": "structure_unknown",
            "program": each("example-program-output"),
            "program_decisions": each("pass"),
        },
        {
            "task": "d",
            "status": "ready",
            "model": each(None),
            "program": each(None),
            "model_decisions": {"compatible": "stage_rejected", "standard": "unknown"},
            "program_decisions": each("no_policy_hit"),
        },
    ]
    report = aggregate(samples)
    assert report["standard"]["ready_program_minus_model_extreme_counts"] == [-1, 0]
    assert report["standard"][
        "accepted_content_program_minus_model_extreme_counts"
    ] == [-1, 1]
    assert report["standard"]["all_scheduled_program_minus_model_extreme_counts"] == [
        -2,
        2,
    ]
    assert report["compatible"]["all_scheduled_program_minus_model_extreme_counts"] == [
        -1,
        2,
    ]
