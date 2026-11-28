from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def layout(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import portable_enhanced_layout

    return portable_enhanced_layout


def example(size):
    return {
        "size": size,
        "title": "Synthetic",
        "items": [
            {
                "id": "a",
                "text": "14",
                "label": "North",
                "entity": "A",
                "role": "secondary",
            },
            {
                "id": "b",
                "text": "16",
                "label": "East",
                "entity": "A",
                "role": "secondary",
            },
            {
                "id": "c",
                "text": "20",
                "label": "South",
                "entity": "A",
                "role": "secondary",
            },
        ],
        "actions": [{"id": "next", "label": "Next"}, {"id": "open", "label": "Open"}],
    }


@pytest.mark.parametrize("size", ["2x2", "2x4"])
def test_menus_preserve_every_field_and_action_and_are_repeatable(layout, size):
    menus = layout.menus
    content = example(size)
    base = menus.stage.program_route(content)
    original = deepcopy((base, content))

    def menu():
        return list(
            menus.small_menu(content, base, "synthetic")
            if size == "2x2"
            else menus.wide_menu(content, base)
        )

    candidates = menu()
    assert len(candidates) == len({menus.canonical(t) for t in candidates}) > 1
    assert menu() == candidates
    assert all(
        menus.leaf_sequence(t["root"]) == menus.leaf_sequence(base["root"])
        for t in candidates
    )
    assert (base, content) == original
    if size == "2x4":
        assert candidates[0] == base


def test_no_shared_action_rail_when_action_belongs_to_one_record(layout):
    content = example("2x4")
    content["actions"][1]["entity"] = "A"
    # Use an explicit ordered tree with adjacent trailing buttons of different scope.
    root = {
        "kind": "column",
        "children": [{"kind": "text", "ref": k} for k in ("title", "a", "b", "c")]
        + [{"kind": "button", "ref": k} for k in ("next", "open")],
    }
    for tree in layout.menus.wide_menu(content, {"root": root}):
        assert tree["root"]["kind"] == "column"
        for n in layout.menus.nodes(tree["root"]):
            if n["kind"] == "row":
                assert not {"next", "open"}.issubset(layout.refs(n))


def test_compatibility_preserves_legacy_success_and_standard_uses_only_strict_artifact(
    layout, monkeypatch
):
    first, second = {"root": "legacy"}, {"root": "wide-fallback"}
    program = SimpleNamespace(program_route=lambda _: first)
    monkeypatch.setattr(layout.menus, "wide_menu", lambda *_: iter((first, second)))
    results = {
        "legacy": layout.TreeResult("accepted", "fail", "original-native"),
        "wide-fallback": layout.TreeResult(
            "accepted", "pass", "standard-native", "standard-native", "standard-native"
        ),
    }
    monkeypatch.setattr(
        layout,
        "score_tree",
        lambda engine, content, source, entry, tree: results[tree["root"]],
    )
    hashes, verdicts = layout.select(
        "key", {"size": "2x4"}, {}, {}, SimpleNamespace(program=program)
    )
    assert hashes == {"compatible": "original-native", "standard": "standard-native"}
    assert verdicts == {"compatible": "pass", "standard": "pass"}


def test_unknown_and_exhausted_are_separate(layout, monkeypatch):
    eng = SimpleNamespace(
        program=SimpleNamespace(program_route=lambda _: {"root": "x"})
    )
    monkeypatch.setattr(layout.menus, "wide_menu", lambda _content, tree: iter((tree,)))
    monkeypatch.setattr(
        layout,
        "score_tree",
        lambda *args: layout.TreeResult("geometry_unknown", "unknown"),
    )
    hashes, verdicts = layout.select("key", {"size": "2x4"}, {}, {}, eng)
    assert hashes == {"compatible": None, "standard": None}
    assert verdicts == {"compatible": "unknown", "standard": "unknown"}
    monkeypatch.setattr(
        layout, "score_tree", lambda *args: layout.TreeResult("stage_rejected", "fail")
    )
    assert set(layout.select("key", {"size": "2x4"}, {}, {}, eng)[1].values()) == {
        "no_policy_hit"
    }


def test_narrow_numeric_unit_and_parent_overflow_are_rejected(layout):
    with pytest.raises(ValueError, match="Split numeric"):
        layout.check_line_breaks(["speed 1", "3%"], "speed 13%", [(6, 9)])
    layout.check_line_breaks(["speed ", "13%"], "speed 13%", [(6, 9)])
    root = {
        "kind": "column",
        "style": {"width": 25, "height": 50, "padding": 3},
        "children": [
            {"kind": "text", "ref": "one", "style": {"width": 20, "height": 14}}
        ],
    }
    assert layout.frame_issue(root) == "width_overflow"
