import json
from pathlib import Path

import pytest


@pytest.fixture
def metric(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import font_declarations

    return font_declarations


OPTIONAL = object()


def leaf(kind, identity, font=OPTIONAL):
    node = {"component": kind, "id": identity}
    node["content" if kind == "Text" else "label"] = {"path": "/missing_value"}
    if font is not OPTIONAL:
        node["styles"] = {"fontSize": font}
    return node


def card(nodes, *, root_font=OPTIONAL, surface="s", root=None):
    base = {"id": "layout", "component": "Column", "children": [n["id"] for n in nodes]}
    if root_font is not OPTIONAL:
        base["styles"] = {"fontSize": root_font}
    update = {"surfaceId": "s", "components": [base, *nodes]}
    if root is not None:
        update["root"] = root
    return [
        {"createSurface": {"surfaceId": "s"}},
        {"updateComponents": update},
        {"updateDataModel": {"surfaceId": surface, "value": {}}},
    ]


def jsonl(obj):
    return "\n".join(json.dumps(m) for m in obj)


def test_legacy_includes_every_declaring_kind_and_strict_separates_text_button(metric):
    doc = card(
        [
            leaf("Text", "t1", 12.0),
            leaf("Text", "t2", 12),
            leaf("Text", "t3", 10),
            leaf("Button", "b1", 9.75),
        ],
        root_font=8,
    )
    result = metric.score(jsonl(doc).encode())
    assert result["status"] == "measured"
    assert result["legacy"] == {
        "min_font": 8,
        "numeric_nodes": 5,
        "below_12fp": 3,
        "below_10fp": 2,
    }
    assert result["text"] == {
        "nodes": 3,
        "declared": 3,
        "missing": 0,
        "invalid": 0,
        "min_font": 10,
        "below_12fp": 1,
        "below_10fp": 0,
        "histogram": {"10": 1, "12": 2},
    }
    assert result["button"] == {
        "nodes": 1,
        "declared": 1,
        "missing": 0,
        "invalid": 0,
        "min_font": 9.75,
        "below_12fp": 1,
        "below_10fp": 1,
        "histogram": {"9.75": 1},
    }


def test_missing_and_inherited_styles_are_not_imputed(metric):
    raw = jsonl(
        card(
            [
                leaf("Text", "t1"),
                leaf("Text", "t2", None),
                leaf("Text", "t3", "14fp"),
                leaf("Button", "b"),
            ],
            root_font=18,
        )
    )
    r = metric.score(raw)
    assert r["legacy"]["min_font"] == 18
    assert r["text"]["missing"] == 1 and r["text"]["invalid"] == 2
    assert r["text"]["min_font"] is None and r["button"]["min_font"] is None
    assert r["button"]["missing"] == 1 and r["button"]["declared"] == 0


def test_historical_bools_and_negative_sizes_are_excluded_in_typed_groups(metric):
    raw = jsonl(
        card(
            [
                leaf("Text", "a", False),
                leaf("Text", "b", -2),
                leaf("Text", "c", 0),
                leaf("Button", "d", 17),
            ]
        )
    )
    r = metric.score(raw)
    assert r["legacy"] == {
        "min_font": -2,
        "below_12fp": 3,
        "below_10fp": 3,
        "numeric_nodes": 4,
    }
    assert r["text"]["invalid"] == 3 and r["text"]["declared"] == 0
    assert r["button"]["min_font"] == 17
    single = metric.score(jsonl(card([leaf("Button", "b", True)])))["legacy"]
    assert type(single["min_font"]) is int and single["min_font"] == 1


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_values_never_export_non_json_floats(metric, invalid):
    r = metric.score(jsonl(card([leaf("Text", "t", invalid), leaf("Text", "u", 10)])))
    assert r["legacy"] is None
    assert r["text"]["invalid"] == 1 and r["text"]["min_font"] == 10
    json.dumps(r, allow_nan=False)


def test_absent_invalid_and_known_tree_with_zero_text_remain_distinct(metric):
    absent = metric.score(None)
    assert absent == {
        "status": "no_artifact",
        "legacy": None,
        "text": None,
        "button": None,
    }
    assert metric.score("broken") == {**absent, "status": "unresolved_tree"}
    r = metric.score(jsonl(card([leaf("Button", "b", 14)])))
    assert r["status"] == "measured" and r["text"]["nodes"] == 0
    assert r["text"]["min_font"] is None and r["text"]["histogram"] == {}


@pytest.mark.parametrize(
    "defect",
    [
        "disconnected",
        "cycle",
        "wrong_surface",
        "unknown_kind",
        "bad_root",
        "leaf_has_children",
    ],
)
def test_failed_reachability_preserves_only_the_separate_legacy_result(metric, defect):
    nodes = [leaf("Text", "t", 11), leaf("Button", "b", 14)]
    doc = card(nodes)
    graph = doc[1]["updateComponents"]
    if defect == "disconnected":
        graph["components"][0]["children"].remove("t")
    elif defect == "cycle":
        graph["components"][0]["children"].append("layout")
    elif defect == "wrong_surface":
        doc[2]["updateDataModel"]["surfaceId"] = "different"
    elif defect == "unknown_kind":
        nodes[0]["component"] = "UnknownText"
    elif defect == "bad_root":
        graph["root"] = "unknown"
    else:
        graph["components"][0]["children"].remove("b")
        nodes[0]["children"] = ["b"]
    r = metric.score(jsonl(doc))
    assert (
        r["status"] == "unresolved_tree" and r["text"] is None and r["button"] is None
    )
    assert r["legacy"] == {
        "min_font": 11,
        "below_12fp": 1,
        "below_10fp": 0,
        "numeric_nodes": 2,
    }


def test_typed_tree_can_be_read_from_array_and_legacy_expects_jsonl(metric):
    r = metric.score(json.dumps(card([leaf("Text", "t", 12)], root="layout")))
    assert r["status"] == "measured" and r["text"]["min_font"] == 12
    assert r["legacy"] is None
