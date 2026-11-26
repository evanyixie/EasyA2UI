import copy

import pytest

from .method import check, messages, no_duplicate_keys
from .score import evaluate


def test_prompt_uses_complete_identical_source():
    import json

    source = {"query": "测试", "candidate_paths": ["/a"], "sample_data": {}}
    assert json.loads(messages(source)[1]["content"]) == source


def test_closed_ids_and_missing_values():
    source = {"candidate_paths": ["/a"], "candidate_actions": [{"id": "a1"}]}
    answer = {"fact_ids": ["/a"], "action_ids": []}
    assert check(answer, source) == answer
    for key, values in (("fact_ids", ["/a", "/a"]), ("action_ids", ["other"])):
        bad = copy.deepcopy(answer)
        bad[key] = values
        with pytest.raises(ValueError):
            check(bad, source)
    with pytest.raises(ValueError):
        no_duplicate_keys([("fact_ids", []), ("fact_ids", ["/a"])])


def test_alternatives_do_not_double_count_and_unaligned_do_not_score():
    ref = {
        "clauses": [
            {"kind": "required_fact", "alternatives": ["x", "y"], "id": "r", "evidence": "指标"},
            {"kind": "allowed_fact", "alternatives": ["z"]},
        ],
        "excluded": ["w"],
        "sample_missing_candidate_ids": ["x"],
        "unaligned": ["其他需求"],
    }
    e = evaluate({"fact_ids": ["x", "y", "w"], "action_ids": []}, ref)
    assert e["all_required"] and e["hits"]["required_fact"] == 1
    assert e["excluded_selected"] == ["w"] and e["selected_without_sample"] == ["x"]
    assert not evaluate({"fact_ids": ["z"], "action_ids": []}, ref)["all_required"]
    assert (
        evaluate({"fact_ids": [], "action_ids": []}, {**ref, "clauses": []})["all_required"] is None
    )
