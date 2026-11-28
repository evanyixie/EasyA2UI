"""终点的合成回归，不读取正式或开发题。"""

import copy
import math

import pytest
from endpoint import (
    CONDITIONAL,
    EVIDENCE_KINDS,
    HARD_FAILURES,
    INDEPENDENT,
    PRIMARY_ITEMS,
    assess,
)


def proof(status="pass", kind="contract_audit"):
    return {"status": status, "source_kind": kind, "evidence_ref": "synthetic/receipt"}


def complete(checkpoint="raw_first"):
    primary = {}
    for key in PRIMARY_ITEMS:
        kind = "independent_review" if key in INDEPENDENT else "contract_audit"
        if key in EVIDENCE_KINDS:
            kind = min(EVIDENCE_KINDS[key])
        primary[key] = proof(kind=kind)
    if checkpoint == "after_common_repair":
        primary["common_repair_lineage"] = proof(kind="common_repair_receipt")
    record = {
        "task_id": "synthetic",
        "arm": "anonymous",
        "checkpoint": checkpoint,
        "execution": {
            "status": "artifact_checks_pass",
            "evidence_ref": "synthetic/current",
        },
        "primary_evidence": primary,
        "c04": {
            "protocol": proof(kind="calibrated_protocol"),
            "coverage": {
                "expected_ids": ["a", "b", "c", "d", "e"],
                "inventory_ref": "synthetic/p7",
                "evidence_ref": "synthetic/coverage",
                "observations": {
                    "a": True,
                    "b": True,
                    "c": True,
                    "d": True,
                    "e": False,
                },
            },
            "overflow": {
                "expected_ids": ["title", "body"],
                "inventory_ref": "synthetic/node_inventory",
                "method": "native_glyph_px",
                "evidence_ref": "synthetic/glyphs",
                "observations": {"title": 0, "body": 4},
            },
        },
    }
    subject = {key: record[key] for key in ("task_id", "arm", "checkpoint")}
    subject["artifact_sha256"] = "a" * 64
    record["artifact"] = {"subject": dict(subject), "evidence_ref": "synthetic/bytes"}
    for measured in record["c04"].values():
        measured["subject"] = dict(subject)
    return record


def test_baselines_and_not_in_place():
    row = complete()
    before = copy.deepcopy(row)
    out = assess(row)
    assert out["primary"]["status"] == out["c04"]["status"] == "pass"
    assert out["c04"]["checks"]["must_show_80_percent"]["fraction"] == 0.8
    assert row == before


@pytest.mark.parametrize("state", ["not_run", "no_artifact"])
def test_even_fully_populated_measurements_cannot_score_unexecuted_or_absent_case(
    state,
):
    row = complete()
    row["execution"]["status"] = state
    result = assess(row)["c04"]
    assert result["status"] == "unknown" and result["failed"] == []
    assert result["checks"]["must_show_80_percent"]["fraction"] is None
    assert all(x["status"] == "unknown" for x in result["sensitivity"].values())


def test_rejected_but_emitted_artifact_scored_only_with_matched_measurements():
    row = complete()
    row["execution"]["status"] = "artifact_checks_rejected"
    assert assess(row)["primary"]["status"] == "fail"
    assert assess(row)["c04"]["status"] == "pass"
    del row["artifact"]
    assert assess(row)["c04"]["status"] == "unknown"


@pytest.mark.parametrize(
    "field,value",
    [
        ("checkpoint", "after_common_repair"),
        ("arm", "other"),
        ("task_id", "other"),
        ("artifact_sha256", "b" * 64),
    ],
)
def test_unpaired_measurement_cannot_supply_coverage(field, value):
    row = complete()
    row["c04"]["coverage"]["subject"][field] = value
    result = assess(row)["c04"]
    assert result["status"] == "unknown" and result["unpaired_or_missing_evidence"] == [
        "coverage"
    ]
    assert result["checks"]["max_node_overflow_4px"]["status"] == "pass"
    assert result["checks"]["must_show_80_percent"]["fraction"] is None


def test_wrong_artifact_checkpoint_blocks_both_pass_and_failure():
    row = complete()
    row["artifact"]["subject"]["checkpoint"] = "after_common_repair"
    row["c04"]["overflow"]["observations"]["body"] = 40
    result = assess(row)["c04"]
    assert result["status"] == "unknown" and result["failed"] == []


def test_threshold_sensitivity_uses_common_denominator_and_fixed_four_pixels():
    row = complete()
    cov = row["c04"]["coverage"]["observations"]
    cov["d"] = False
    result = assess(row)["c04"]
    assert result["status"] == "fail"
    assert {key: v["status"] for key, v in result["sensitivity"].items()} == {
        "60_percent": "pass",
        "100_percent": "fail",
    }
    cov.update(d=True, e=True)
    assert assess(row)["c04"]["sensitivity"]["100_percent"]["status"] == "pass"
    row["c04"]["overflow"]["observations"]["body"] = 4.001
    assert all(
        x["status"] == "fail" for x in assess(row)["c04"]["sensitivity"].values()
    )


def test_missing_seat_keeps_denominator_unknown():
    x = assess({"task_id": "x", "arm": "a", "checkpoint": "raw_first"})
    assert x["primary"]["status"] == x["c04"]["status"] == "unknown"
    assert x["c04"]["checks"]["must_show_80_percent"]["fraction"] is None
    assert x["c04"]["checks"]["max_node_overflow_4px"]["max_overflow_px"] is None


@pytest.mark.parametrize("execution", sorted(HARD_FAILURES))
def test_algorithm_rejection_has_priority_over_missing_reviews(execution):
    row = complete()
    row["execution"]["status"] = execution
    row["primary_evidence"].clear()
    row["c04"] = {}
    result = assess(row)
    assert result["primary"]["status"] == "fail"
    assert result["primary"]["failed"] == ["execution"] and result["primary"]["unknown"]
    assert result["c04"]["status"] == "unknown"


@pytest.mark.parametrize(
    "execution", ["transport_failed", "not_run", "device_unavailable"]
)
def test_infrastructure_does_not_establish_algorithm_failure(execution):
    row = complete()
    row["execution"]["status"] = execution
    assert assess(row)["primary"]["status"] == "unknown"
    del row["execution"]["evidence_ref"]
    row["execution"]["status"] = "stage_rejected"
    assert assess(row)["primary"]["status"] == "unknown"


def test_current_checkpoint_has_separate_lineage():
    row = complete("after_common_repair")
    assert assess(row)["primary"]["status"] == "pass"
    del row["primary_evidence"]["common_repair_lineage"]
    assert assess(row)["primary"]["unknown"] == ["common_repair_lineage"]
    row["primary_evidence"]["common_repair_lineage"] = proof(
        "fail", "common_repair_receipt"
    )
    assert assess(row)["primary"]["status"] == "fail"
    row["checkpoint"] = "raw_first"
    with pytest.raises(ValueError):
        assess(row)


def test_independent_judgment_and_actual_click_must_have_correct_source():
    row = complete()
    row["primary_evidence"]["actual_action_destinations"] = proof(kind="screenshot")
    row["primary_evidence"]["independent_business"] = proof(kind="developer_review")
    row["primary_evidence"]["readable_text"] = proof(kind="host_ready")
    assert set(assess(row)["primary"]["unknown"]) == {
        "actual_action_destinations",
        "independent_business",
        "readable_text",
    }


def test_only_evidenced_conditional_na_is_credited():
    row = complete()
    item = "actual_action_destinations"
    row["primary_evidence"][item] = {"status": "not_applicable"}
    assert assess(row)["primary"]["status"] == "unknown"
    row["applicability"] = {
        "actions": {"applies": False, "evidence_ref": "synthetic/frozen"}
    }
    assert assess(row)["primary"]["status"] == "unknown"
    row["applicability"]["actions"]["reason"] = "冻结的动作清单为空"
    row["primary_evidence"]["registered_action_payloads"] = {"status": "not_applicable"}
    assert assess(row)["primary"]["status"] == "pass"
    row["applicability"][CONDITIONAL[item]]["applies"] = True
    assert assess(row)["primary"]["status"] == "unknown"
    row["primary_evidence"]["protocol"] = {"status": "not_applicable"}
    assert "protocol" in assess(row)["primary"]["unknown"]


def test_partial_and_overflow_are_distinct_from_primary():
    row = complete()
    row["primary_evidence"]["must_show_facts"] = proof("fail")
    result = assess(row)
    assert result["primary"]["status"] == "fail" and result["c04"]["status"] == "pass"
    row = complete()
    row["c04"]["overflow"]["observations"]["body"] = 4.01
    result = assess(row)
    assert result["primary"]["status"] == "pass" and result["c04"]["status"] == "fail"


def test_complete_inventory_needed_for_pass_known_violation_remains_failure():
    row = complete()
    cov, over = row["c04"]["coverage"], row["c04"]["overflow"]
    del cov["observations"]["e"]
    over["observations"]["title"] = None
    checks = assess(row)["c04"]["checks"]
    assert checks["must_show_80_percent"]["fraction"] is None
    assert checks["max_node_overflow_4px"]["max_overflow_px"] is None
    assert assess(row)["c04"]["status"] == "unknown"
    over["observations"]["body"] = 5
    assert assess(row)["c04"]["status"] == "fail"
    cov["observations"].update(a=False, b=False)
    assert assess(row)["c04"]["checks"]["must_show_80_percent"]["status"] == "fail"


def test_incomplete_c04_sources_and_wrong_units():
    row = complete()
    row["c04"]["protocol"] = proof(kind="host_ready")
    row["c04"]["coverage"]["expected_ids"] = []
    row["c04"]["overflow"]["method"] = "reference_vp"
    result = assess(row)["c04"]
    assert set(result["unknown"]) == {
        "calibrated_protocol",
        "must_show_80_percent",
        "max_node_overflow_4px",
    }


@pytest.mark.parametrize("invalid", [True, -1, math.nan, math.inf, "4"])
def test_invalid_pixel_numbers_rejected(invalid):
    row = complete()
    row["c04"]["overflow"]["observations"]["body"] = invalid
    with pytest.raises(ValueError):
        assess(row)


def test_unknown_fields_or_duplicate_ids_do_not_silently_change_denominator():
    row = complete()
    row["c04"]["coverage"]["observations"]["undeclared"] = False
    with pytest.raises(ValueError):
        assess(row)
    row = complete()
    row["c04"]["coverage"]["expected_ids"] = ["a", "a"]
    with pytest.raises(ValueError):
        assess(row)
