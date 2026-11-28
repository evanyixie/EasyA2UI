from pathlib import Path

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import formal_arm_content_yield

    return formal_arm_content_yield


def test_successful_repair_does_not_count_as_direct_first_success(study):
    receipt = {
        "exit_status": "repaired",
        "execution_status": "accepted",
        "first_sha256": "original",
        "final_sha256": "committed",
        "before": ["issue"],
    }
    assert study.technical(receipt) == {
        "raw_first": "fail",
        "after_common_repair": "pass",
    }
    receipt.update(exit_status="no_change", before=[])
    assert study.technical(receipt)["raw_first"] == "pass"


@pytest.mark.parametrize(
    "status, expected", [("callback_failed", "missing"), ("stage_rejected", "fail")]
)
def test_no_card_keeps_its_failure_or_transport_evidence(study, status, expected):
    row = {
        "exit_status": "not_reached",
        "execution_status": status,
        "first_sha256": None,
        "final_sha256": None,
    }
    assert set(study.technical(row).values()) == {expected}


def fixture(study):
    roster = {
        "a": {"family": "one", "included_in_217_sensitivity": True},
        "b": {"family": "two", "included_in_217_sensitivity": False},
    }
    rows = []
    for task in roster:
        for phase in study.PHASES:
            for arm in study.ARMS:
                tech = (
                    "fail"
                    if task == "a" and arm == "L4" and phase == "raw_first"
                    else "pass"
                )
                fidelity = "empty_data" if arm == "L4" else "all_sourced"
                if task == "b" and arm == "L5":
                    fidelity = "some_unsourced"
                rows.append(
                    {
                        "task": task,
                        "family": roster[task]["family"],
                        "arm": arm,
                        "phase": phase,
                        "technical": tech,
                        "coverage": "at_least_80",
                        "coverage_state": "measured",
                        "fidelity": fidelity,
                        "joint": study.rq2.joint(tech, "at_least_80", fidelity),
                    }
                )
    return rows, roster


def test_three_state_pair_cohort_and_unknown_bounds(study):
    rows, roster = fixture(study)
    results = study.summarize(rows, roster)
    first = results["all_assigned"]["phases"]["raw_first"]["paired_l5_minus_l4"]
    assert first["states"]["fail"]["pass"] == first["states"]["missing"]["fail"] == 1
    assert first["pairs_with_both_states_known"] == 1
    assert first["certified_difference_rate"] == 0.5
    assert first["latent_difference_rate_bounds"] == [0.0, 0.5]
    final = results["original_sources"]["phases"]["after_common_repair"][
        "paired_l5_minus_l4"
    ]
    assert final["states"]["missing"]["pass"] == 1
    assert final["latent_difference_rate_bounds"] == [0, 1]
    assert final["certified_difference_family_percentile_ci95"] is None


def test_dropped_or_duplicate_checkpoint_is_rejected(study):
    rows, roster = fixture(study)
    with pytest.raises(ValueError, match="Incomplete checkpoint"):
        study.summarize(rows[:-1], roster)
    with pytest.raises(ValueError, match="Duplicate"):
        study.summarize([*rows, rows[-1]], roster)
