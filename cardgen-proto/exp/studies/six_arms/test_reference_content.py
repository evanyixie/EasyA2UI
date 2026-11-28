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


@pytest.mark.parametrize(
    "ids",
    [
        ("s", "s", "other"),
        ("s", "other", "s"),
        ("other", "s", "s"),
        ("", "", ""),
        (None, None, None),
    ],
)
def test_invalid_surface_never_contributes_reference_facts(metric, ids):
    card = example("72", {"v": "72"})
    for message, surface in zip(card, ids, strict=True):
        next(iter(message.values()))["surfaceId"] = surface
    raw = json.dumps(card)
    with pytest.raises(ValueError, match="surface"):
        metric.read_reference(raw)
    assert metric.coverage(raw, {"72": ()}) == (None, 1, "unresolved_text")


@pytest.mark.parametrize("path", [False, 0, {}, [], "", None, "data", "/data~2"])
def test_invalid_model_path_is_not_a_known_empty_or_root_value(metric, path):
    raw = json.dumps(example("文字", {}, data_path=path))
    with pytest.raises(ValueError, match="pointer"):
        metric.read_reference(raw)
    assert metric.coverage(raw, {"文字": ()}) == (None, 1, "unresolved_text")


def test_omitted_path_uses_legacy_root_and_escaped_path_resolves(metric):
    card = example({"path": "/v"}, {"v": 20})
    del card[2]["updateDataModel"]["path"]
    raw = json.dumps(card)
    assert metric.read_reference(raw) == {"20": {"/v"}}
    assert metric.coverage(raw, metric.read_reference(raw)) == (1, 1, "measured")
    raw = json.dumps(example({"path": "/a~1b/c~0d"}, {"c~d": 20}, data_path="/a~1b"))
    assert metric.read_reference(raw) == {"20": {"/a~1b/c~0d"}}
    assert metric.coverage(raw, metric.read_reference(raw)) == (1, 1, "measured")


def test_empty_reference_literal_card_and_missing_source_are_distinct(metric):
    for value in (0, 0.0, False, None, "", [], {}):
        raw = json.dumps(example("完整的字面卡", value))
        assert metric.read_reference(raw) == {}
        assert metric.coverage(raw, {}) == (None, 0, "empty_reference")
    assert metric.coverage(None, {}) == (0, 0, "no_artifact")
    assert metric.coverage(None, None) == (None, None, "missing_reference")
    assert metric.read_reference(json.dumps(example("", {"array": [0, 0.0]}))) == {
        "0": {"/array/0"},
        "0.0": {"/array/1"},
    }
    card = example("", None)
    del card[2]["updateDataModel"]["value"]
    with pytest.raises(ValueError, match="value"):
        metric.read_reference(json.dumps(card))


def test_unknown_component_representation_is_not_measured_as_absent_text(metric):
    card = example("72", {"sample": "72"})
    node = card[1]["updateComponents"]["components"][1]
    for kind in ("TextView", {"Text": {"text": {"literalString": "72"}}}):
        node["component"] = kind
        raw = json.dumps(card)
        assert metric.read_reference(raw) == {"72": {"/sample"}}
        assert metric.coverage(raw, metric.read_reference(raw)) == (
            None,
            1,
            "unresolved_text",
        )
    node["component"] = "Image"
    del node["content"]
    raw = json.dumps(card)
    assert metric.coverage(raw, metric.read_reference(raw)) == (0, 1, "measured")


def test_legacy_matcher_counts_literals_across_adjacent_text_nodes(metric):
    card = example("7", {"sample": "72"})
    card[1]["updateComponents"]["components"][2] = {
        "component": "Text",
        "id": "button",
        "content": "2",
    }
    raw = json.dumps(card)
    assert metric.coverage(raw, metric.read_reference(raw)) == (1, 1, "measured")
