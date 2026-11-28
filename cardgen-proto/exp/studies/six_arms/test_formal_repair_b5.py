from pathlib import Path

import pytest


@pytest.fixture
def metrics(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import formal_repair_b5, repair_budget

    return formal_repair_b5, repair_budget


def example_money(program, states):
    return {
        "model_eligibility": "awaiting_first_repair",
        "first_common": False,
        "program_common": program,
        "model_common": states[-1],
        "model_rounds": [
            {
                "round": k,
                "common_pass": v,
                "candidate_sha256": None if v is None else "present",
                "added_tokens": None if v is None else k * 10,
            }
            for k, v in enumerate(states, 1)
        ],
    }


def test_one_more_attempt_is_not_charged_to_program_success(metrics):
    _, budget = metrics
    rows = [
        example_money(True, (False, True)),
        example_money(False, (False, True)),
        example_money(False, (True,)),
        example_money(False, (False, None)),
        {"model_eligibility": "no_first_artifact"},
    ]
    x = budget.replay(rows)
    assert x["assigned"] == 5
    assert x["program_only"]["pass"] == 1
    assert x["model_budget_1"]["pass"] == 1
    assert x["model_budget_2"]["pass"] == 3
    assert x["program_first_budget_1"]["pass"] == 2
    full = x["program_first_budget_2"]
    assert (full["pass"], full["fail"], full["undetermined"]) == (3, 0, 1)
    assert full["total"] == {
        "request_intents": 5,
        "candidate_received": 4,
        "rescued": 2,
        "metered_responses": 4,
        "metered_tokens": 50,
    }
    assert full["rounds"][1]["request_intents"] == 2


@pytest.mark.parametrize("states", [(True, False), (False,), (None, True)])
def test_rejects_broken_archive_sequence(metrics, states):
    with pytest.raises(ValueError):
        metrics[1].replay([example_money(False, states)])


def test_geometry_issues_are_counted_per_proposal_and_once_per_end_card(metrics):
    b5, _ = metrics
    old = [{"id": "p", "code": "width"}]
    new = [{"id": "p", "code": "height"}, {"id": "p", "code": "line_count"}]
    base = {
        "task": "sample",
        "arm": "L1",
        "first_sha256": "same",
        "final_sha256": "same",
        "committed": False,
        "exit_status": "unresolved",
        "before": old,
        "after": old,
    }
    proposal = {
        "round": 1,
        "committed": False,
        "actions": [{}],
        "introduced_by_repair": new,
        "worsened": old,
    }
    row = {**base, "rounds": [proposal, {**proposal, "round": 2}]}
    summary = b5.indicators([row])
    assert summary["new_node_code_pairs_summed_over_proposals"] == 4
    assert summary["nodes_with_new_violations_summed_over_proposals"] == 2
    assert (
        summary["seats_with_a_proposal_introducing_a_violation"]
        == summary["tried_and_returned_original"]
        == 1
    )
    assert summary["seats_with_new_violations_in_final_artifact"] == 0
    assert summary["proposals_worsening_existing_geometry_violations"] == 2
    absent = {
        **base,
        "before": None,
        "after": None,
        "first_sha256": None,
        "final_sha256": None,
        "rounds": [],
    }
    x = b5.indicators([absent])
    assert x["original_and_final_geometry_assessed"] == 0
    assert x["actions_per_proposal"] is None
    with pytest.raises(ValueError, match="assignment"):
        b5.summarize([row], expected=1)
