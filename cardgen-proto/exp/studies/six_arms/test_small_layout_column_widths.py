from copy import deepcopy
from math import ceil
from pathlib import Path
from types import SimpleNamespace

import pytest


def sample():
    return {
        "size": "2x2",
        "title": "Heading",
        "items": [
            {
                "id": "v",
                "entity": "object",
                "role": "primary",
                "label": "P",
                "text": "P",
            },
            {
                "id": "l",
                "entity": "object",
                "role": "secondary",
                "label": "L",
                "text": "L" * 8,
            },
            {
                "id": "r",
                "entity": "object",
                "role": "secondary",
                "label": "S",
                "text": "S" * 8,
            },
        ],
        "actions": [{"id": "go", "label": "Open", "handler": {"name": "original"}}],
    }


@pytest.fixture
def layout(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms.harness_v2 import program_stages as stages
    from six_arms.small_layout_column_widths import try_geometry

    def advance(ch):
        return {"L": 14.9375, "S": 13.5}.get(ch, 8)

    def measure(text, width, size, *, max_lines, bold, line_height):
        occupied = 0
        lines = 1
        for char in text:
            step = advance(char)
            if step + 4 > width:
                raise ValueError("glyph cannot fit")
            if occupied + step + 4 > width:
                lines += 1
                occupied = 0
            occupied += step
        if lines > max_lines:
            raise ValueError("too many lines")
        return SimpleNamespace(height=ceil(lines * size * line_height + 2), lines=lines)

    font = SimpleNamespace(getlength=lambda text: 4 * sum(map(advance, text)))
    oracle = SimpleNamespace(text=measure, _font=lambda size, bold: font)
    monkeypatch.setattr(stages, "_measure", lambda: oracle)

    def run(content):
        base = stages.program_route(content)
        old = deepcopy((content, base))
        candidate = try_geometry(content, base, stages)
        assert old == (content, base)
        if candidate:
            stages._check_tree(candidate["tree"], *stages._index(content))
        return candidate

    return run


def test_complete_pair_fits_at_fractional_wrap_boundary(layout):
    result = layout(sample())
    assert result["row_widths"] == [63.75, 62.25]
    assert result["default_widths"] == [63, 63]
    title, primary, pair, action = result["geometry"]["root"]["children"]
    assert [title["ref"], primary["ref"], action["ref"]] == ["title", "v", "go"]
    assert [n["style"]["width"] for n in (title, primary, action)] == [130, 130, 130]
    assert [n["ref"] for n in pair["children"]] == ["l", "r"]
    assert [n["style"]["maxLines"] for n in pair["children"]] == [2, 2]
    assert [n["style"]["fontSize"] for n in pair["children"]] == [14, 14]
    assert primary["style"]["fontSize"] == 20


@pytest.mark.parametrize(
    ("key", "value"),
    [("role", "primary"), ("label", ""), ("entity", "another"), ("text", "S" * 50)],
)
def test_ineligible_or_oversized_pair_has_no_result(layout, key, value):
    content = sample()
    content["items"][-1][key] = value
    assert layout(content) is None


def test_uses_default_when_it_already_fits(layout):
    content = sample()
    for item in content["items"][1:]:
        item["text"] = item["label"]
    result = layout(content)
    assert result["row_widths"] == result["default_widths"]


def test_rejects_unsupported_canvas_and_ambiguous_pair(layout):
    content = sample()
    content["size"] = "2x4"
    assert layout(content) is None
    content["size"] = "2x2"
    for item in content["items"][1:]:
        item.pop("entity")
    assert layout(content) is None
