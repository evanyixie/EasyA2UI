from copy import deepcopy
from pathlib import Path

import pytest


@pytest.fixture
def selector(monkeypatch):
    studies = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(studies.parents[1]))
    monkeypatch.syspath_prepend(str(studies))
    from six_arms import wide_menu_selection

    return wide_menu_selection


def content():
    return {
        "size": "2x4",
        "title": "Forecast",
        "items": [
            {
                "id": "a",
                "text": "18",
                "entity": "one",
                "role": "primary",
                "label": "Today",
            },
            {
                "id": "b",
                "text": "19",
                "entity": "one",
                "role": "secondary",
                "label": "Tomorrow",
            },
        ],
        "actions": [{"id": "go", "handler": "open", "label": "Open"}],
    }


def test_same_menu_is_blind_ordered_and_lossless(selector):
    data = content()
    old = deepcopy(data)
    wire, bid, reason = selector.packet(data, "task-1")
    assert reason is None and data == old
    assert wire == selector.packet(data, "task-1")[0]
    assert set(wire) == {"canvas", "content", "choices"}
    assert wire["canvas"] == {"width_vp": 300, "height_vp": 150}
    base = selector.program_stages.program_route(data)
    keys = set()
    for choice in wire["choices"]:
        assert set(choice) == {"id", "description", "tree", "features"}
        assert selector.menus.leaf_sequence(
            choice["tree"]["root"]
        ) == selector.menus.leaf_sequence(base["root"])
        keys.add(selector.canonical(choice["tree"]))
        if choice["id"] == bid:
            assert choice["tree"] == base
    expected = {selector.canonical(t) for t in selector.menus.wide_menu(data, base)}
    assert len(keys) == len(wire["choices"]) > 1 and keys == expected
    receipt = selector.saved_choice(wire, "a")
    assert selector.saved_choice(wire, "a", receipt) is receipt
    with pytest.raises(ValueError):
        selector.saved_choice(wire, "b", receipt)


def test_single_and_wrong_canvas(selector):
    single = content()
    single.update(items=[], actions=[])
    packet, base, error = selector.packet(single, "only")
    assert (
        error is None
        and base == selector.choose(packet) == "R1"
        and len(packet["choices"]) == 1
    )
    with pytest.raises(ValueError):
        selector.packet({**single, "size": "2x2"}, "other")


def test_only_available_width_changes_in_old_estimate(selector):
    data = content()
    data["actions"][0]["label"] = "长" * 13
    entries, _ = selector.program_stages._index(data)
    tree = {"root": {"kind": "column", "children": [{"kind": "button", "ref": "go"}]}}
    old = selector.menus._features(tree, entries)
    assert old == selector.menus._features(tree, entries, canvas_width=150)
    wide = selector.menus._features(tree, entries, canvas_width=300)
    assert old["action_width_excess_vp"] > 0 and wide["action_width_excess_vp"] == 0
    assert selector.menus.feature_rank(wide) < selector.menus.feature_rank(old)
    first = {"id": "R1", "features": wide}
    second = {"id": "R2", "features": wide.copy()}
    assert selector.choose({"choices": [first, second]}) == "R1"
    assert selector.choose({"choices": [second, first]}) == "R2"
