"""领域偏倚交叉表纯合成测试，不读取真实答案。"""

import copy

import pytest

from p1_domain_bias import render_markdown, summarize_domain_bias


def records():
    p1 = [
        {"case_id": "A", "eligible": True},
        {"case_id": "B", "eligible": True},
        {
            "case_id": "C",
            "eligible": False,
            "criteria": [
                {
                    "code": "P1_C1_MESSAGES",
                    "status": "fail",
                    "evidence": {"reason": "MISSING_ARTIFACT"},
                },
            ],
        },
    ]
    p4 = [
        {"case_id": "A", "domain_status": "classified", "domain": ["weather", "time"]},
        {"case_id": "B", "domain_status": "no_data_candidates", "domain": []},
        {"case_id": "C", "domain_status": "classified", "domain": ["weather"]},
    ]
    return p1, p4


def test_all_requests_including_missing_artifact_remain_in_denominators():
    p1, p4 = records()
    result = summarize_domain_bias(p1, p4, [])
    assert result["total_requests"] == 3
    assert result["cohort_denominators"] == {
        "eligible": 2,
        "missing_artifact": 1,
        "other_not_eligible": 0,
    }
    assert result["new_exclusions"] == 0
    weather = next(row for row in result["by_domain"] if row["domain"] == "weather")
    assert weather["by_cohort"]["eligible"]["count"] == 1
    assert weather["by_cohort"]["eligible"]["denominator"] == 2
    assert weather["by_cohort"]["eligible"]["percentage"] == 50
    assert weather["by_cohort"]["missing_artifact"]["count"] == 1


def test_multiple_labels_overlap_without_inflating_case_denominators():
    p1, p4 = records()
    result = summarize_domain_bias(p1, p4, [])
    assert len(result["by_domain"]) == 2
    assert result["known_canonical_domain_cases"]["eligible"]["count"] == 1
    assert (
        sum(row["by_cohort"]["eligible"]["count"] for row in result["by_domain"]) == 2
    )
    assert result["unknown_canonical_domain_cases"]["eligible"]["case_ids"] == ["B"]


def test_unparsed_declarations_do_not_erase_known_label_or_guess_unknown_label():
    p1, p4 = records()
    unresolved = [{"case_id": "A"}, {"case_id": "B"}, {"case_id": "A"}]
    result = summarize_domain_bias(p1, p4, unresolved)
    assert result["unparsed_declaration_cases"]["eligible"]["count"] == 2
    assert result["unparsed_overlap_known_canonical"] == 1
    assert result["unparsed_overlap_unknown_canonical"] == 1
    assert result["unknown_canonical_domain_cases"]["eligible"]["count"] == 1
    assert {row["domain"] for row in result["by_domain"]} == {"weather", "time"}


def test_zero_cohort_denominator_has_null_percentage_not_zero():
    p1, p4 = records()
    result = summarize_domain_bias(p1[:2], p4[:2], [])
    assert result["by_domain"][0]["by_cohort"]["missing_artifact"]["percentage"] is None
    assert result["by_domain"][0]["by_cohort"]["missing_artifact"]["denominator"] == 0


def test_non_missing_exclusion_remains_a_separate_observed_cohort():
    p1, p4 = records()
    p1[2]["criteria"] = []
    result = summarize_domain_bias(p1, p4, [])
    assert result["cohort_denominators"]["other_not_eligible"] == 1
    assert result["cohort_denominators"]["missing_artifact"] == 0


@pytest.mark.parametrize("bad", [None, "true", 1])
def test_eligibility_cannot_be_guessed_from_falsy_or_truthy_values(bad):
    p1, p4 = records()
    p1[0]["eligible"] = bad
    with pytest.raises(ValueError, match="explicitly boolean"):
        summarize_domain_bias(p1, p4, [])


def test_p1_p4_coverage_must_match():
    p1, p4 = records()
    with pytest.raises(ValueError, match="same cases"):
        summarize_domain_bias(p1, p4[:2], [])


def test_unknown_status_cannot_assert_an_observed_domain():
    p1, p4 = records()
    p4[1]["domain"] = ["guessed"]
    with pytest.raises(ValueError, match="unknown domain status"):
        summarize_domain_bias(p1, p4, [])


@pytest.mark.parametrize("labels", [[], None, ["weather", "weather"], ["weather", ""]])
def test_classified_labels_must_be_present_unique_and_nonempty(labels):
    p1, p4 = records()
    p4[0]["domain"] = labels
    with pytest.raises(ValueError):
        summarize_domain_bias(p1, p4, [])


def test_unknown_case_declaration_is_not_silently_dropped():
    p1, p4 = records()
    with pytest.raises(ValueError, match="unknown case"):
        summarize_domain_bias(p1, p4, [{"case_id": "Foreign"}])


def test_source_rows_not_modified_and_report_retains_unknown_boundary():
    p1, p4 = records()
    frozen = copy.deepcopy((p1, p4))
    result = summarize_domain_bias(p1, p4, [])
    assert (p1, p4) == frozen
    text = render_markdown(result)
    assert "不能当成无业务数据" in text
    assert "分母固定" in text
    assert "不检验显著性" in text
    assert result["statistical_inference"] == "not_performed_descriptive_only"
    assert result["human_validation"] == "not_performed"
