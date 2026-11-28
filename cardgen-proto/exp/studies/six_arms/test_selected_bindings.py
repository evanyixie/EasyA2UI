import json
from pathlib import Path

import pytest


@pytest.fixture
def inspect_selected(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms.selected_bindings import inspect_selected

    return inspect_selected


def surface(*leaves):
    root = {"id": "root", "component": "Row", "children": [n["id"] for n in leaves]}
    return [
        {"createSurface": {"surfaceId": "s"}},
        {
            "updateComponents": {
                "surfaceId": "s",
                "root": "root",
                "components": [root, *leaves],
            }
        },
        {
            "updateDataModel": {
                "surfaceId": "s",
                "path": "/data",
                "value": {"level": 8, "left": 8},
            }
        },
    ]


def wire(messages):
    return "\n".join(json.dumps(m, ensure_ascii=False) for m in messages).encode()


def text(value, key="text"):
    return {"id": key, "component": "Text", "content": value}


def test_direct_and_concatenated_references_keep_exact_paths(inspect_selected):
    button = {
        "id": "b",
        "component": "Button",
        "label": """{{ '剩余 ' + ${/data/right} + " / " + ${/data/a~1b} }}""",
        "onClick": [{"args": {"value": {"path": "/data/left"}}}],
    }
    messages = surface(text({"path": "/data/level"}), button, text("8", "literal"))
    expected = {"/data/level", "/data/right", "/data/a~1b", "/data/left"}
    result = inspect_selected(expected, wire(messages))
    assert result["state"] == "complete"
    assert result["present"] == expected - {"/data/left"}
    assert result["absent"] == {"/data/left"} and not result["unresolved"]
    del messages[1]["updateComponents"]["root"]
    assert result == inspect_selected(expected, json.dumps(messages).encode())


@pytest.mark.parametrize(
    "carrier",
    [
        text("前缀 ${/data/left}", "other"),
        text("{{ ${/data/left} * 2 }}", "other"),
        text("{{ ${/data/left} + }}", "other"),
        text({"path": "/bad~2"}, "other"),
        text({"path": "/data/left", "fallback": "8"}, "other"),
        {"id": "other", "component": "Progress", "value": {"path": "/data/left"}},
        {"id": "other", "component": "CustomLabel"},
        {"id": "other", "component": "Button", "label": "8", "template": {}},
        {"id": "other", "component": "Text", "text": {"path": "/data/left"}},
    ],
)
def test_unsupported_carrier_preserves_only_other_confirmed_references(
    inspect_selected, carrier
):
    raw = wire(surface(text({"path": "/data/level"}), carrier))
    result = inspect_selected({"/data/level", "/data/left"}, raw)
    assert result["state"] == "partial"
    assert result["present"] == {"/data/level"} and result["unresolved"] == {
        "/data/left"
    }
    assert not result["absent"]
    assert inspect_selected({"/data/level"}, raw)["state"] == "partial"


@pytest.mark.parametrize(
    "fault",
    ["orphan", "duplicate", "cycle", "dangling", "surface", "model", "duplicate_key"],
)
def test_broken_graph_never_proves_presence_or_absence(inspect_selected, fault):
    messages = surface(text({"path": "/data/level"}))
    graph = messages[1]["updateComponents"]
    root = graph["components"][0]
    if fault == "orphan":
        root["children"] = []
    elif fault == "duplicate":
        graph["components"].append(text("8"))
    elif fault == "cycle":
        root["children"].append("root")
    elif fault == "dangling":
        root["children"].append("missing")
    elif fault == "surface":
        graph["surfaceId"] = "different"
    elif fault == "model":
        del messages[2]["updateDataModel"]["value"]
    raw = wire(messages)
    if fault == "duplicate_key":
        raw = raw.replace(b'"content":', b'"content": "8", "content":')
    result = inspect_selected({"/data/level"}, raw)
    assert (
        result["state"] == "invalid_artifact"
        and result["unresolved"] == result["expected"]
    )
    assert not result["absent"] and not result["present"]


def test_literal_path_and_sample_are_not_dynamic(inspect_selected):
    raw = wire(surface(text("8"), text("/data/level", "literal_path")))
    result = inspect_selected(["/data/level", "/data/level"], raw)
    assert result["expected"] == result["absent"] == {"/data/level"}


@pytest.mark.parametrize("kind", ["Divider", "Image", "CustomContainer", "Text"])
def test_unknown_parent_cannot_make_a_nested_text_a_confirmed_display_reference(
    inspect_selected, kind
):
    messages = surface(
        text({"path": "/data/level"}), {"id": "other", "component": kind}
    )
    graph = messages[1]["updateComponents"]
    graph["components"][-1]["children"] = ["nested"]
    graph["components"].append(text({"path": "/data/left"}, "nested"))
    result = inspect_selected({"/data/level", "/data/left"}, wire(messages))
    assert result["present"] == {"/data/level"}
    assert result["unresolved"] == {"/data/left"}


def test_empty_selection_has_no_denominator_missing_artifact_stays_unknown(
    inspect_selected,
):
    assert inspect_selected([], None)["state"] == "no_selected_paths"
    result = inspect_selected({"/data/level"}, None)
    assert (
        result["state"] == "no_artifact" and result["unresolved"] == result["expected"]
    )
    assert not result["absent"]
    with pytest.raises(ValueError, match="Invalid selected"):
        inspect_selected(["invalid"], None)
