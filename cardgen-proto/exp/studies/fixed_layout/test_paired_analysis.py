import pytest

from paired_analysis import analyze


def roster(*families):
    return [{"task_id": str(i), "family_id": k} for i, k in enumerate(families)]


def decisions(*values):
    return [
        {"task_id": str(i), "A": a, "B": b, "missing_reason": "测试用缺测"}
        for i, (a, b) in enumerate(values)
    ]


def test_paired_difference_and_family_direction():
    base = roster("g0", "g0", "g1", "g2")
    votes = decisions(("fail", "pass"), ("fail", "pass"), ("pass", "fail"), ("pass", "pass"))
    original = analyze(base, votes)
    assert original["all_assigned_point_difference"] == 0.25
    assert original["equal_family_weight_sensitivity_difference"] == 0
    assert original["only_B_program_pass"] == 2
    assert original["only_A_model_pass"] == 1
    assert original == analyze(base[::-1], votes[::-1])
    lo, hi = original["paired_cluster_percentile_ci95"]
    assert lo <= 0.25 <= hi


def test_missing_is_not_failure():
    base = roster("x", "y")
    results = analyze(base, decisions(("pass", "missing"), ("missing", "pass")))
    assert results["all_assigned_point_difference"] is None
    assert results["all_assigned_difference_bounds_B_minus_A"] == [-0.5, 0.5]
    assert results["both_fail"] == 0


def test_all_missing_has_no_score():
    result = analyze(roster("x"), decisions(("missing", "missing")))
    assert result["complete_pairs"] == 0
    assert result["all_assigned_difference_bounds_B_minus_A"] == [-1, 1]
    assert result["paired_cluster_percentile_ci95"] is None


def test_selector_and_end_to_end_denominators():
    votes = decisions(("fail", "fail"), ("fail", "pass"))
    votes[0].update(pre_admission="shared_blocked", admission_reason="不可表达的冻结合同")
    votes[1]["pre_admission"] = "admitted"
    result = analyze(roster("x", "y"), votes)
    assert result["all_assigned_point_difference"] == 0.5
    assert result["descriptive_difference_on_pre_admitted_pairs"] == 1
    votes[0]["A"] = "pass"
    with pytest.raises(ValueError):
        analyze(roster("x", "y"), votes)


def test_identical_arms_no_spurious_equivalence_interval():
    result = analyze(roster("x", "y"), decisions(("pass", "pass"), ("fail", "fail")))
    assert result["all_assigned_point_difference"] == 0
    assert result["paired_cluster_percentile_ci95"] is None


@pytest.mark.parametrize(
    "votes",
    [
        [],
        [{"task_id": "0", "A": "pass", "B": "pass"}] * 2,
        [{"task_id": "1", "A": "pass", "B": "pass"}],
        [{"task_id": "0", "A": "pass", "B": "missing"}],
        [{"task_id": "0", "A": "pass", "B": "unrecognized"}],
    ],
)
def test_rejects_invalid_or_silent_omissions(votes):
    with pytest.raises(ValueError):
        analyze(roster("x"), votes)
