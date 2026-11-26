from copy import deepcopy

from size_capability_dedup import deduplicate


def row(identity, *, size="2x2", bindings=None):
    return {
        "case_id": identity,
        "size": size,
        "query": identity,
        "input": {
            "candidateDataBindings": bindings
            if bindings is not None
            else [{"capabilityId": "capability-a", "arguments": {}}]
        },
        "unresolved_capability_fields": [],
    }


def test_cross_size_is_never_deduplicated():
    result = deduplicate([row("A"), row("B", size="2x4")])
    assert len(result["groups"]) == 2


def test_action_and_query_do_not_create_separate_keys():
    first, second = row("A"), row("B")
    second["input"]["candidateEventCandidates"] = [{"action": {"call": "dial"}}]
    result = deduplicate([first, second])
    assert len(result["groups"]) == 1
    assert len(result["groups"][0]["members"]) == 2
    assert first["query"] == "A" and second["query"] == "B"


def test_different_parameters_are_retained():
    first, second = row("A"), row("B")
    second["input"]["candidateDataBindings"][0]["arguments"] = {"city": "different"}
    assert len(deduplicate([first, second])["groups"]) == 2


def test_binding_order_is_ignored_but_duplicate_count_is_preserved():
    first = row(
        "A",
        bindings=[
            {"capabilityId": "one", "arguments": {}},
            {"capabilityId": "two", "arguments": {}},
        ],
    )
    second = deepcopy(first)
    second.update(case_id="B", query="B")
    second["input"]["candidateDataBindings"].reverse()
    third = deepcopy(first)
    third.update(case_id="C", query="C")
    third["input"]["candidateDataBindings"].append(
        {"capabilityId": "one", "arguments": {}}
    )
    assert len(deduplicate([first, second, third])["groups"]) == 2


def test_empty_candidates_and_missing_arguments_are_not_guessed():
    first = row("A", bindings=[])
    second = row("B", bindings=[{"capabilityId": "one"}])
    result = deduplicate([first, second])
    assert result["groups"] == []
    assert len(result["pending"]) == 2


def test_unresolved_extra_declarations_stay_separate():
    first, second = row("A"), row("B")
    second["unresolved_capability_fields"] = ["dataCapabilityIds"]
    result = deduplicate([first, second])
    assert len(result["groups"]) == 1
    assert len(result["groups"][0]["members"]) == 1
    assert len(result["pending"]) == 1
