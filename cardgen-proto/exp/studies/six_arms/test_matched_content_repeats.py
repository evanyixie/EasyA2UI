import json

import pytest
from matched_content_repeats import (
    Draw,
    comparisons,
    dimensions,
    report_agreement,
    sha,
    technical,
    verified_response,
)

SOURCE = {
    "candidate_actions": [
        {
            "id": "a1",
            "capabilityId": "open",
            "handler": {"call": "test", "args": {"which": "one"}},
        }
    ]
}


def plan(rows, actions=(), title="Example"):
    return {
        "size": "2x2",
        "domain": "test",
        "title": title,
        "items": rows,
        "actions": list(actions),
    }


def draw(semantic, first="bytes", direct=True):
    return Draw(
        "test",
        "raw",
        "valid_unchanged" if semantic else "rejected_unchanged",
        semantic,
        first,
        direct,
    )


def test_fact_multisets_ignore_ids_and_order_but_preserve_duplicates_and_literal_source():
    a = {
        "id": "field_1",
        "text": "10",
        "path": "/a",
        "role": "primary",
        "entity": "alpha",
    }
    b = {
        "id": "field_2",
        "text": "10",
        "path": "/b",
        "role": "secondary",
        "entity": "beta",
    }
    x = dimensions(plan([a, b]), SOURCE)
    y = dimensions(
        plan([dict(b, id="field_4"), dict(a, id="field_3", role="secondary")]), SOURCE
    )
    cmp = comparisons(x, y)
    assert cmp["selected_fact_multiset"]
    assert not cmp["fact_order_given_same_facts_two_or_more_distinct"]
    assert not cmp["literal_item_roles_given_same_facts_and_complete_role_tags"]
    assert cmp["literal_item_entities_given_same_facts_and_complete_entity_tags"]
    assert not cmp["entire_effective_contract_with_ids"]
    assert not comparisons(x, dimensions(plan([a, b, dict(a, id="third")]), SOURCE))[
        "selected_fact_multiset"
    ]
    literal = dimensions(plan([{"id": "field_1", "text": "10"}, b]), SOURCE)
    assert not comparisons(x, literal)["selected_fact_multiset"]


def test_missing_tags_no_action_and_singleton_order_not_scored_as_equal():
    state = dimensions(
        plan([{"id": "x", "text": "Static fact"}]), {"candidate_actions": []}
    )
    metrics = comparisons(state, state)
    assert metrics["selected_action_ids"]
    assert metrics["literal_item_roles_given_same_facts_and_complete_role_tags"] is None
    assert (
        metrics["literal_item_entities_given_same_facts_and_complete_entity_tags"]
        is None
    )
    assert metrics["fact_order_given_same_facts_two_or_more_distinct"] is None
    assert metrics["selected_action_ids_when_candidates_available"] is None
    assert metrics["registered_action_capabilities_when_either_selected"] is None


def test_action_label_and_registered_target_are_distinct():
    a = {"id": "a1", "label": "Open"}
    x = dimensions(plan([], [a]), SOURCE)
    y = dimensions(
        plan(
            [],
            [dict(a, label="View", handler=SOURCE["candidate_actions"][0]["handler"])],
        ),
        SOURCE,
    )
    m = comparisons(x, y)
    assert m["registered_action_targets_when_either_selected"]
    assert m["registered_action_capabilities_when_either_selected"]
    assert not m["action_wording_given_same_nonempty_actions"]
    assert m["action_order_given_same_actions_two_or_more_distinct"] is None


def test_distinguish_contract_rejection_from_valid_downstream_disagreement_and_weight_tasks():
    a = dimensions(plan([], title="A"), SOURCE)
    b = dimensions(plan([], title="B"), SOURCE)
    first = [draw(a), draw(a), draw(a)]
    second = [draw(a), draw(b, None, False), draw(None, None, False)]
    out = technical([first, second, []])
    assert out["eligible_tasks"] == 2
    assert out["tasks_by_observed_draw_count"] == {0: 1, 3: 2}
    assert out["discordant_pairs_by_content"] == {
        "one_content_rejected": 1,
        "both_valid_same_fact_and_action_sets": 1,
    }
    summary = report_agreement([first, second, []])["title_wording"]
    assert summary["eligible_pairs"] == 4
    assert summary["equal_pairs"] == 3
    assert summary["mean_within_task_pair_agreement"] == 0.5
    with pytest.raises(ValueError, match="identical effective contract"):
        technical([[draw(a), draw(a, None, False)]])


def test_rejected_raw_content_is_an_observed_response_and_failed_transport_has_no_vote(
    tmp_path,
):
    d = tmp_path / "calls/content"
    d.mkdir(parents=True)
    prompt = b'["synthetic"]'
    wire = b"malformed content"
    c = {
        "stage": "content",
        "physical_attempts": 1,
        "http_status": 200,
        "request_id": "distinct",
        "requested_model": "deepseek-flash",
        "returned_model": "deepseek-flash",
    }
    receipt = json.dumps(c).encode()
    seal = {
        "state": "completed",
        "stage": "content",
        "raw_sha256": sha(wire),
        "messages_sha256": sha(prompt),
        "receipt_sha256": sha(receipt),
    }
    (d / "messages.json").write_bytes(prompt)
    (d / "response.txt").write_bytes(wire)
    (d / "call.json").write_bytes(receipt)
    (d / "seal.json").write_text(json.dumps(seal))
    step = {
        "stage": "content",
        "status": "stage_rejected",
        "raw_sha256": sha(wire),
        "receipt": c,
        "messages": json.loads(prompt),
    }
    assert verified_response(tmp_path, {"stages": [step]}) == (prompt, wire, "distinct")
    (d / "response.txt").unlink()
    c = {
        "stage": "content",
        "http_status": None,
        "request_id": None,
        "error_class": "ConnectError",
    }
    receipt = json.dumps(c).encode()
    (d / "call.json").write_bytes(receipt)
    (d / "seal.json").write_text(
        json.dumps(
            dict(seal, state="failed", raw_sha256=None, receipt_sha256=sha(receipt))
        )
    )
    step.update(status="callback_failed", raw_sha256=None, receipt=c)
    assert verified_response(tmp_path, {"stages": [step]}) == (prompt, None, None)
    (d / "messages.json").write_bytes(prompt + b"\n")
    with pytest.raises(ValueError, match="seal"):
        verified_response(tmp_path, {"stages": [step]})
