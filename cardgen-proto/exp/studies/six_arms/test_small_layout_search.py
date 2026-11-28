from copy import deepcopy
from math import ceil
from pathlib import Path
from types import SimpleNamespace

import pytest


def field(ref, entity, label="x", role="secondary"):
    return {"id": ref, "entity": entity, "role": role, "label": label, "text": "1"}


def refs(node):
    if "ref" in node:
        return [node["ref"]]
    return [ref for child in node["children"] for ref in refs(child)]


def direct_pair(tree, left, right):
    return any(
        band["kind"] == "row"
        and [refs(child) for child in band["children"]] == [[left], [right]]
        for band in tree["root"]["children"]
    )


@pytest.fixture
def layouts(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import small_layout_search
    from six_arms.harness_v2 import program_stages as program

    # Deterministic font metrics isolate structural rules from workstation fonts.
    def text(value, width, size, *, max_lines, bold, line_height):
        if width <= 0:
            raise ValueError("no width")
        lines = max(1, ceil(len(value) * size / (2 * width)))
        if lines > max_lines:
            raise ValueError("text does not fit")
        return SimpleNamespace(height=ceil(lines * size * line_height + 2), lines=lines)

    monkeypatch.setattr(program, "_measure", lambda: SimpleNamespace(text=text))
    monkeypatch.setattr(
        program, "_natural_width", lambda value, size, weight: len(value) * size / 2 + 4
    )

    def search(items, actions=(), size="2x2"):
        content = {"size": size, "title": "T", "items": items, "actions": list(actions)}
        base = program.program_route(content)
        original = deepcopy((content, base))
        trees = list(small_layout_search.iter_layouts(content, base, program))
        assert (content, base) == original
        for tree in trees:
            program._check_tree(tree, *program._index(content))
            assert refs(tree["root"]) == refs(base["root"])
            assert tree["root"]["children"][0] == {"kind": "text", "ref": "title"}
        return trees

    return search


def test_different_length_stacks_of_one_entity(layouts):
    trees = layouts([field(ref, "e") for ref in "abcde"])
    assert any(
        band["kind"] == "row" and [len(refs(c)) for c in band["children"]] == [2, 3]
        for tree in trees
        for band in tree["root"]["children"]
    )
    assert not layouts([field("a", "e")], size="2x4")
    assert not layouts([field(str(i), "e") for i in range(30)])


@pytest.mark.parametrize(
    ("label", "role", "extra", "expected"),
    [
        ("y", "secondary", [], True),
        ("", "secondary", [], False),
        ("y", "primary", [], False),
        ("y", "secondary", [field("other", "second")], False),
    ],
)
def test_card_field_may_share_a_single_entity_auxiliary_row(
    layouts, label, role, extra, expected
):
    trees = layouts([field("v", "first"), field("g", None, label, role), *extra])
    assert trees
    assert any(direct_pair(tree, "v", "g") for tree in trees) == expected


def test_neighbouring_records_require_labels_and_remain_complete(layouts):
    trees = layouts([field("a", "alpha"), field("b", "alpha"), field("c", "beta")])
    assert any(
        band["kind"] == "row"
        and [refs(c) for c in band["children"]] == [["a", "b"], ["c"]]
        for tree in trees
        for band in tree["root"]["children"]
    )
    assert not any(direct_pair(tree, "b", "c") for tree in trees)
    # An arbitrary first-frame value coinciding with an entity name is not a label.
    unlabelled = dict(field("c", "beta", None), text="beta")
    trees = layouts([field("a", "alpha"), unlabelled])
    assert trees and not any(direct_pair(tree, "a", "c") for tree in trees)


def test_actions_remain_with_their_owner_or_the_entire_card(layouts):
    actions = [
        {"id": "openA", "label": "go", "entity": "alpha"},
        {"id": "openCard", "label": "ok"},
    ]
    trees = layouts([field("a", "alpha"), field("b", "beta")], actions)
    assert trees
    for tree in trees:
        for band in tree["root"]["children"]:
            if band["kind"] != "row":
                continue
            cells = [refs(c) for c in band["children"]]
            if "openCard" in refs(band):
                assert cells == [["a", "openA", "b"], ["openCard"]]
            if "openA" in refs(band) and "b" in refs(band):
                assert any("a" in cell and "openA" in cell for cell in cells)
