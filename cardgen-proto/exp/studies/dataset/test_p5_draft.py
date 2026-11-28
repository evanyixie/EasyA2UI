"""P5合成合同验证；不使用真实金标，不调用模型或手机。"""

import copy
import hashlib

import pytest

from p5_draft import (
    SEEDS,
    audit_split,
    build_drafts,
    human_package,
    population,
    similarity,
)

SMALL = {"dev": 3, "report": 2, "extension": 1, "reserve": 1}


def records(count=7):
    rows = []
    for index in range(count):
        case_id = f"C{index:03d}"
        rows.append(
            {
                "case_id": case_id,
                "source": "online_updated",
                "size": "2x2",
                "p1_status": "PASS",
                "eligible": True,
                "query": chr(0x3400 + index) * 8,
                "input_sha256": hashlib.sha256((case_id + "raw").encode()).hexdigest(),
                "input_view_sha256": hashlib.sha256(
                    (case_id + "view").encode()
                ).hexdigest(),
                "group_id": "g_" + case_id,
                "representative_id": case_id,
                "is_representative": True,
                "layout": "LayoutA",
                "layout_status": "classified",
                "domain": ["calendar"],
                "domain_status": "capability",
                "pre_exposed": False,
            }
        )
    return rows


def proposal():
    return {
        "dev": ["C000", "C001", "C002"],
        "report": ["C003", "C004"],
        "extension": ["C005"],
        "reserve": ["C006"],
    }


def codes(audit):
    return {error.get("code") for error in audit.get("errors", [])}


def test_real_p2_similarity_is_reused_with_exact_normalization():
    assert similarity(" Ａ  B ", "A B") == 1
    assert similarity("", "") == 0
    assert similarity("是", "否") == 0
    assert similarity("风力2级", "风力20级") < 1


def test_all_five_seeds_preserved_and_deterministic_without_formal_freeze():
    result = build_drafts(records(), SMALL)
    assert result == build_drafts(records(), SMALL)
    assert result.get("status") == "DRAFT_PENDING_HUMAN"
    assert result.get("seeds") == list(SEEDS)
    assert [trial.get("seed") for trial in result.get("trials")] == list(SEEDS)
    assert result.get("formal_split_frozen") is False
    assert result.get("p8") == "not_executed"
    assert "not_verified" in result.get("unknown_prior_exposure")
    for trial in result.get("trials"):
        assert trial.get("independent_audit").get("status") == "PASS"
        assert {name: len(ids) for name, ids in trial.get("proposal").items()} == SMALL


def test_default_494_target_is_not_scaled_or_filled_when_one_group_short():
    result = build_drafts(records(493))
    assert result.get("status") == "BLOCKED"
    assert result.get("targets") == {
        "dev": 100,
        "report": 250,
        "extension": 60,
        "reserve": 84,
    }
    assert len(result.get("trials")) == 5
    for trial in result.get("trials"):
        assert trial.get("proposal") is None
        shortage = next(
            error
            for error in trial.get("blockers")
            if error.get("code") == "INSUFFICIENT_INDEPENDENT_GROUPS"
        )
        assert shortage.get("deficit") == 1


def test_member_exposure_forces_whole_group_to_dev_even_when_flag_false():
    rows = records(8)
    member = rows[1]
    member.update(
        case_id="synthetic-exposed",
        registered_exposure=True,
        group_id="g_C000",
        representative_id="C000",
        is_representative=False,
    )
    result = build_drafts(rows, SMALL)
    assert result.get("forced_dev_groups") == 1
    for trial in result.get("trials"):
        assert trial.get("status") == "DRAFT_PENDING_HUMAN"
        assert "C000" in trial.get("proposal").get("dev")
        for split in ("report", "extension", "reserve"):
            assert "C000" not in trial.get("proposal").get(split)


def test_pre_exposed_groups_above_dev_capacity_block_all_seeds():
    rows = records()
    for row in rows[:4]:
        row["pre_exposed"] = True
    result = build_drafts(rows, SMALL)
    assert result.get("status") == "BLOCKED"
    for trial in result.get("trials"):
        assert any(
            error.get("code") == "EXPOSED_GROUPS_EXCEED_DEV"
            for error in trial.get("blockers")
        )


def test_report_leak_threshold_is_strict_at_exact_point_seven():
    rows = records()
    at_boundary = audit_split(rows, proposal(), SMALL, compare=lambda _a, _b: 0.7)
    below = audit_split(rows, proposal(), SMALL, compare=lambda _a, _b: 0.699999)
    assert at_boundary.get("status") == "BLOCKED"
    assert "REPORT_DEV_LEAK" in codes(at_boundary)
    assert below.get("status") == "PASS"


def test_greedy_failure_does_not_relax_leakage_or_claim_global_impossibility():
    rows = records()
    for row in rows:
        row["query"] = "同一个完全相同的合成输入"
    result = build_drafts(rows, SMALL)
    assert result.get("status") == "BLOCKED"
    for trial in result.get("trials"):
        assert trial.get("proposal") is None
        assert "不是全域不可行证明" in trial.get("scope")
        assert trial.get("blockers")[0].get("code") == "REPORT_POOL_AFTER_DEV_TOO_SMALL"


def test_independent_checker_rejects_cross_split_group_and_variant_selection():
    rows = records(8)
    rows[7].update(group_id="g_C000", representative_id="C000", is_representative=False)
    changed = proposal()
    changed["report"] = ["C007", "C004"]
    result = audit_split(rows, changed, SMALL)
    assert "GROUP_REPEATED_OR_CROSSES_SPLITS" in codes(result)
    assert "NON_REPRESENTATIVE_SELECTED" in codes(result)


def test_independent_checker_rejects_ineligible_and_unknown_case():
    rows = records(8)
    rows[7]["eligible"] = False
    changed = proposal()
    changed["report"] = ["C007", "missing"]
    result = audit_split(rows, changed, SMALL)
    assert "UNKNOWN_OR_INELIGIBLE_CASE" in codes(result)


def test_independent_checker_recomputes_similarity_instead_of_trusting_builder():
    rows = records()
    assert audit_split(rows, proposal(), SMALL).get("status") == "PASS"
    rows[3]["query"] = rows[0].get("query")
    result = audit_split(rows, proposal(), SMALL)
    assert "REPORT_DEV_LEAK" in codes(result)


def test_any_exposed_group_outside_dev_is_rejected():
    rows = records()
    rows[3]["pre_exposed"] = True
    result = audit_split(rows, proposal(), SMALL)
    assert "EXPOSED_GROUP_NOT_DEV" in codes(result)


@pytest.mark.parametrize(
    "mutation", ["duplicate_id", "baseline", "bad_domain", "bad_hash"]
)
def test_invalid_input_contract_blocks_without_silent_coercion(mutation):
    rows = records()
    if mutation == "duplicate_id":
        rows[1]["case_id"] = rows[0].get("case_id")
    elif mutation == "baseline":
        rows[0]["source"] = "request_baseline"
    elif mutation == "bad_domain":
        rows[0]["domain"] = [{"unexpected": "object"}]
    else:
        rows[0]["input_sha256"] = "missing"
    result = build_drafts(rows, SMALL)
    assert result.get("status") == "BLOCKED"
    assert result.get("schema_errors")
    assert human_package(rows, result).get("status") == "BLOCKED_INVALID_SCHEMA"


def test_multi_label_domain_kept_and_inference_insufficiency_disclosed():
    rows = records()
    for row in rows:
        row["domain"] = ["calendar", "time"]
    result = build_drafts(rows, SMALL)
    assert any("calendar|time" in key for key in result.get("population_distribution"))
    for trial in result.get("trials"):
        insufficient = trial.get("report_sample_adequacy")
        assert insufficient[0].get("inference_allowed") is False


def test_blank_human_forms_are_independent_and_must_show_has_no_gold_answers():
    rows = records()
    result = build_drafts(rows, SMALL)
    package = human_package(rows, result)
    reviewers = package.get("layout_50_independent_reviewers")
    assert package.get("layout_actual_count") == 7
    assert package.get("layout_agreement_kappa") is None
    assert package.get("gold_review_error_rate") is None
    assert {row.get("case_id") for row in reviewers.get("A")} == {
        row.get("case_id") for row in reviewers.get("B")
    }
    for forms in reviewers.values():
        for row in forms:
            assert row.get("reviewer_name") is None and row.get("human_layout") is None
            assert (
                "layout" not in row
                and "evidence" not in row
                and "candidates" not in row
            )
    for row in package.get("must_show_forms"):
        assert set(row) == {
            "case_id",
            "query",
            "input_view_sha256",
            "required_items",
            "reviewer_name",
            "source_rule",
        }
        assert row.get("required_items") is None


def test_blocked_run_does_not_create_fake_report_must_show_forms():
    rows = records(6)
    result = build_drafts(rows, SMALL)
    package = human_package(rows, result)
    assert package.get("must_show_forms") == []
    assert package.get("report_not_selected_reason") is not None


def test_records_and_group_members_are_not_mutated():
    rows = records()
    before = copy.deepcopy(rows)
    groups, errors = population(rows)
    assert not errors and len(groups) == 7
    build_drafts(rows, SMALL)
    assert rows == before


def test_checker_rejects_unknown_split_names():
    changed = proposal()
    changed["hidden"] = ["C000"]
    assert "INVALID_SPLIT_NAMES" in codes(audit_split(records(), changed, SMALL))


def test_all_five_distribution_ranges_are_reported_without_invented_threshold():
    result = build_drafts(records(), SMALL)
    for split in SMALL:
        spread = result.get("five_seed_stratum_spread").get(split)
        assert spread.get("measured_seed_count") == 5
        assert spread.get("pass_threshold") is None
        assert spread.get("decision") == "pending_human_stability_review"


def test_checker_reports_malformed_manifest_id_without_crashing():
    changed = proposal()
    changed["report"] = [{"invalid": "id"}, "C004"]
    assert "INVALID_SELECTED_ID" in codes(audit_split(records(), changed, SMALL))
