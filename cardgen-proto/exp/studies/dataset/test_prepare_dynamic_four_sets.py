from copy import deepcopy

from prepare_dynamic_four_sets import (
    allocate,
    balanced_size_counts,
    content_payload,
    planned_counts,
    prepare_tasks,
    relation_families,
    validate_assignment,
)


def record(identity, value):
    return {
        "case_id": identity,
        "size": "2x2",
        "D": 1,
        "A": 0,
        "items": [
            {
                "count": 1,
                "name": "注释名称",
                "sources": [
                    {
                        "type": "bound_text",
                        "content": "{{ ${/data/value} }}",
                        "bindings": [{"path": "/data/value", "sample_value": value}],
                    }
                ],
            }
        ],
        "supporting_text": [],
        "actions": [],
        "source_hashes": {"compact": identity},
    }


def test_same_capability_parameters_do_not_merge_different_selected_content():
    inputs = {
        key: {
            "input": {
                "candidateDataBindings": [{"capabilityId": "same", "arguments": {}}]
            },
            "pre_exposed": False,
        }
        for key in ("one", "two")
    }
    result = prepare_tasks([record("one", 1), record("two", 999)], inputs)
    assert len(result) == 2


def test_strict_candidate_duplicate_keeps_all_reference_artifacts():
    inputs = {
        key: {"input": {"userQuery": "原始需求"}, "pre_exposed": False}
        for key in ("one", "two")
    }
    first, second = record("one", 1), record("two", 1)
    first["styles"] = {"fontSize": 18}
    second["styles"] = {"fontSize": 30}
    before = deepcopy((first, second))
    tasks = prepare_tasks([first, second], inputs)
    assert len(tasks) == 1
    assert tasks[0]["source_case_ids"] == ["one", "two"]
    assert len(tasks[0]["reference_artifacts"]) == 2
    assert (first, second) == before
    assert "styles" not in content_payload(first)


def test_same_content_different_user_preferences_is_retained_but_related():
    inputs = {
        key: {"input": {"userQuery": preference}, "pre_exposed": False}
        for key, preference in (("one", "指定红色"), ("two", "指定蓝色"))
    }
    tasks = prepare_tasks([record("one", 1), record("two", 1)], inputs)
    assert len(tasks) == 2
    families = relation_families(tasks)
    assert len(families) == 1 and len(families[0]["task_ids"]) == 2


def test_planned_counts_preserve_main_experiment_targets_and_report_reserve_gap():
    targets = {"dev": 100, "report": 250, "extension": 60, "reserve": 84}
    assert planned_counts(429, targets) == {
        "dev": 100,
        "report": 250,
        "extension": 60,
        "reserve": 19,
    }


def test_size_counts_balance_population_across_all_four_sets():
    tasks = [{"size": "2x2"} for _ in range(330)] + [{"size": "2x4"} for _ in range(99)]
    quota = {"dev": 100, "report": 250, "extension": 60, "reserve": 19}
    result = balanced_size_counts(tasks, quota)
    assert result == {
        "dev": {"2x2": 77, "2x4": 23},
        "report": {"2x2": 192, "2x4": 58},
        "extension": {"2x2": 46, "2x4": 14},
        "reserve": {"2x2": 15, "2x4": 4},
    }


def test_grouped_assignment_is_deterministic_complete_and_keeps_development_exposure():
    tasks = [
        {
            "task_id": f"r{index}",
            "source_case_ids": [f"case{index}"],
            "size": "2x2" if index < 8 else "2x4",
            "D": index % 3 + 1,
            "A": index % 2,
            "input_sha256": str(index),
            "selected_content_sha256": str(index),
            "known_development_exposed": index == 0,
        }
        for index in range(12)
    ]
    tasks[1]["input_sha256"] = tasks[0]["input_sha256"]
    families = relation_families(tasks)
    targets = {"dev": 4, "report": 4, "extension": 2, "reserve": 2}
    allocation = allocate(tasks, families, 23, targets)
    assert allocation == allocate(tasks, families, 23, targets)
    assert {"r0", "r1"} <= set(allocation["dev"])
    result = validate_assignment(tasks, families, allocation, targets)
    assert result["candidate_tasks_covered"] == 12
    assert result["exact_input_or_content_cross_set_overlap"] == 0
    assert result["independent_sample_count"] is None
