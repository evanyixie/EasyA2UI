"""入口诊断不按按钮标题、载荷去重或样值真假值误计数。"""

import json

import pytest

from audit_gold_action_topology import analyse


def run(tmp_path, nodes, value=None):
    messages = [
        {"updateComponents": {"surfaceId": "s", "root": "root", "components": nodes}},
        {"updateDataModel": {"surfaceId": "s", "path": "/", "value": value or {}}},
    ]
    path = tmp_path / "card.jsonl"
    path.write_text(json.dumps(messages), "utf-8")
    return analyse({"case_id": "opaque", "a2ui_path": str(path), "compact_path": None})


def action(name="open"):
    return [{"call": "clickToIntent", "args": {"intentName": name}}]


def test_theme_foreground_global_action_is_one_entry_without_a_button(tmp_path):
    nodes = [
        {
            "id": "root",
            "component": "Stack",
            "children": ["paint", "__post_theme_foreground"],
        },
        {"id": "paint", "component": "Image"},
        {"id": "__post_theme_foreground", "component": "Column", "onClick": action()},
    ]
    result = run(tmp_path, nodes)
    assert result["A_declared"] == 1
    assert result["actions"][0]["global_root"]
    assert result["A_actual_visible"] is None


@pytest.mark.parametrize("same", [True, False])
def test_nested_actions_are_pending_without_collapsing_regions_by_payload(
    tmp_path, same
):
    nodes = [
        {
            "id": "root",
            "component": "Column",
            "children": ["child"],
            "onClick": action(),
        },
        {
            "id": "child",
            "component": "Row",
            "onClick": action("open" if same else "other"),
        },
    ]
    result = run(tmp_path, nodes)
    assert result["A_declared"] == 2
    assert result["A_distinct_payloads"] == (1 if same else 2)
    assert result["nested_actions"][0]["same_payload"] == same
    assert "global_and_child_actions" in result["risks"]


def test_same_payload_on_separate_nodes_does_not_reduce_entry_count(tmp_path):
    nodes = [
        {"id": "root", "component": "Column", "children": ["one", "two"]},
        {"id": "one", "component": "Row", "onClick": action()},
        {"id": "two", "component": "Row", "onClick": action()},
    ]
    result = run(tmp_path, nodes)
    assert result["A_declared"] == 2
    assert result["A_distinct_payloads"] == 1
    assert result["separate_same_payload"] == [["one", "two"]]


def test_two_handlers_on_one_node_are_one_entry(tmp_path):
    nodes = [
        {"id": "root", "component": "Column", "onClick": [*action(), *action("other")]}
    ]
    result = run(tmp_path, nodes)
    assert result["A_declared"] == 1
    assert "multiple_handlers_one_node" in result["risks"]


@pytest.mark.parametrize("value", [0, False])
def test_zero_and_false_are_valid_sample_values_not_missing_text(tmp_path, value):
    nodes = [
        {"id": "root", "component": "Column", "children": ["value"]},
        {"id": "value", "component": "Text", "content": "{{ ${/data/value} }}"},
    ]
    result = run(tmp_path, nodes, {"data": {"value": value}})
    assert "empty_or_missing_sample_text" not in result["risks"]
    assert result["A_declared"] == 0


def test_empty_literal_and_missing_expression_source_remain_pending(tmp_path):
    nodes = [
        {"id": "root", "component": "Column", "children": ["literal", "expression"]},
        {"id": "literal", "component": "Text", "content": ""},
        {"id": "expression", "component": "Text", "content": "{{ ${/missing} + '%' }}"},
    ]
    result = run(tmp_path, nodes)
    assert "empty_literal_text" in result["risks"]
    assert "empty_or_missing_sample_text" in result["risks"]
    assert result["text_nodes"] == 2
    assert result["A_actual_visible"] is None
