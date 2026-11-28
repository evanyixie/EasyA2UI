import json
from pathlib import Path

import pytest


@pytest.fixture
def metric(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import reference_content

    return reference_content


def example(text, value, *, data_path="/"):
    return [
        {"createSurface": {"surfaceId": "s"}},
        {
            "updateComponents": {
                "surfaceId": "s",
                "root": "root",
                "components": [
                    {"component": "Column", "id": "root", "children": ["t", "button"]},
                    {"component": "Text", "id": "t", "content": text},
                    {"component": "Button", "id": "button", "label": "按钮文字"},
                ],
            }
        },
        {"updateDataModel": {"surfaceId": "s", "path": data_path, "value": value}},
    ]


def test_legacy_excludes_machine_keys_and_boolean_splits_once_per_value(metric):
    data = {
        "id": "机器码",
        "a/b~": ["周一，晴", "周二，晴"],
        "extra": "x" * 21,
        "count": 0,
        "urgent": True,
        "another": "周一",
        "last": " / ",
    }
    facts = metric.read_reference(json.dumps(example("", data, data_path="/data")))
    assert set(facts) == {"周一", "晴", "周二", "0", "/"}
    assert facts["晴"] == {"/data/a~1b~0/0", "/data/a~1b~0/1"}
    assert metric.registered_value_support(
        facts, {"/data/a~1b~0/0": "周一，晴", "/else": "周二", "/data/count": 0}
    ) == {
        "total": 5,
        "same_value_any_candidate": 4,
        "same_value_same_path": 3,
    }


def test_rendered_values_not_binding_names_and_button_labels(metric):
    text = "{{ ${/level} + '％ ' + ${/title} }}"
    raw = "\n".join(
        json.dumps(line) for line in example(text, {"level": 68, "title": "电量"})
    )
    assert metric.coverage(raw, {"68%": (), "8": (), "电量": (), "按钮文字": ()}) == (
        2,
        4,
        "measured",
    )
    assert metric.coverage(
        json.dumps(example({"path": "/v"}, {"v": "三天"})), {"三天": ()}
    ) == (1, 1, "measured")
    assert metric.coverage(
        json.dumps(example({"path": "/missing"}, {})), {"例": ()}
    ) == (None, 1, "unresolved_text")
    assert metric.coverage(raw, {}) == (None, 0, "empty_reference")
    assert metric.coverage(raw, None) == (None, None, "missing_reference")
    assert metric.coverage(None, {"x": ()}) == (0, 1, "no_artifact")


def test_reachable_implicit_root_with_nested_data_model(metric):
    card = example({"path": "/data/item"}, {"item": "三天"}, data_path="/data")
    g = card[1]["updateComponents"]
    del g["root"]
    g["components"][0]["id"] = "layout"
    assert metric.coverage(json.dumps(card), {"三天": ()}) == (1, 1, "measured")


def test_orphan_text_is_not_visible_and_multiple_model_messages_are_unknown(metric):
    card = example("内容", {})
    card[1]["updateComponents"]["components"].append(
        {"id": "else", "component": "Text", "content": "不在树"}
    )
    for messages in (card, card + [card[-1]]):
        assert metric.coverage(json.dumps(messages), {"不在树": ()}) == (
            None,
            1,
            "unresolved_text",
        )
