from copy import deepcopy
from math import ceil
from pathlib import Path
from types import SimpleNamespace

import pytest


def item(ref, owner, label, value, role="secondary", unit=""):
    return {
        "id": ref,
        "entity": owner,
        "label": label,
        "text": value,
        "role": role,
        "unit": unit,
    }


def action(ref, label):
    return {"id": ref, "label": label, "handler": {"call": "original"}}


@pytest.fixture
def harness(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import small_layout_scoped as search
    from six_arms.harness_v2 import program_stages as program

    def font(size, bold):
        return SimpleNamespace(
            getlength=lambda s: 4 * sum(size if ord(c) > 127 else size / 2 for c in s)
        )

    def text(value, width, size, *, max_lines, bold, line_height):
        used = 0
        lines = 1
        for c in value:
            step = font(size, bold).getlength(c) / 4
            if step + 4 > width:
                raise ValueError("glyph")
            if c == "\n":
                lines += 1
                used = 0
                continue
            if used + step + 4 > width:
                lines += 1
                used = 0
            used += step
        if lines > max_lines:
            raise ValueError("lines")
        return SimpleNamespace(lines=lines, height=ceil(size * line_height * lines + 2))

    monkeypatch.setattr(
        program, "_measure", lambda: SimpleNamespace(_font=font, text=text)
    )
    return program, search


def solve(harness, items, actions=(), size="2x2"):
    p, s = harness
    content = {"size": size, "title": "标题", "items": items, "actions": list(actions)}
    base = p.program_route(content)
    before = deepcopy((content, base))
    result = s.try_geometry(content, base, p)
    assert (content, base) == before
    if result:
        p._check_tree(result["tree"], *p._index(content))
        original = [(n["kind"], n["ref"]) for n in s._leaves(base["root"])]
        assert original == [
            (n["kind"], n["ref"]) for n in s._leaves(result["geometry"]["root"])
        ]
    return result


def test_records_stay_separate_and_global_action_spans_body(harness):
    _, s = harness
    items = [
        item("x", "first", "用量", "0", "primary", "条"),
        item("y", "first", "余量", "0", unit="项"),
        item("z", "second", "", "文字"),
    ]
    result = solve(harness, items, [action("open", "继续操作")])
    geo = result["geometry"]["root"]
    sizes = {n["ref"]: n["style"] for n in s._leaves(geo)}
    assert (
        sizes["title"]["width"] == sizes["z"]["width"] == sizes["open"]["width"] == 130
    )
    assert sizes["x"]["width"] + sizes["y"]["width"] == 126
    assert sizes["x"]["fontSize"] == 20
    assert (
        sizes["y"]["fontSize"]
        == sizes["z"]["fontSize"]
        == sizes["open"]["fontSize"]
        == 14
    )


def test_number_boundaries_allow_surrounding_prose_to_wrap(harness):
    p, s = harness
    data = item("x", "e", "", "已完成3项今天继续整理")
    spans = s._value_spans(data["text"], data, p)
    assert not s._unreadable_wrap(
        data["text"], spans, p._measure()._font(14, False), 39
    )
    for value, unit in [("12", "件"), ("12.5%", ""), ("12℃~20℃", ""), ("3时5分", "")]:
        data = item("y", "e", "参考", value, unit=unit)
        rendered = p._leaf_text({"ref": "y", "kind": "text"}, {"y": data})
        [(start, end)] = s._value_spans(rendered, data, p)
        assert rendered[start:end] == value + unit


def test_rejects_glyph_rails_using_actual_line_breaks(harness):
    p, s = harness
    font = p._measure()._font(14, False)
    assert s._unreadable_wrap("甲乙丙丁", (), font, 16)
    assert not s._unreadable_wrap("甲乙", (), font, 16)
    assert not s._unreadable_wrap("甲乙丙丁", (), font, 28)
    assert not s._unreadable_wrap("甲\n乙\n丙", (), font, 16)
    assert s._unreadable_wrap("甲乙丙\nXY", (), font, 16)
    assert s._unreadable_wrap("29℃", [(0, 3)], font, 21)


def test_large_inputs_stop_before_breakpoint_enumeration(harness):
    assert solve(harness, [item("huge", "x", "", "甲" * 5000)]) is None
    assert solve(harness, [item(str(i), "x", "", "短") for i in range(60)]) is None
    assert solve(harness, [item("i", "x", "", "短")], size="2x4") is None


def test_global_actions_cannot_share_an_arbitrary_last_record(harness):
    # Long single-line actions leave insufficient room for a full-body rail.
    items = [
        item("x", "record", "", "条目甲乙", "primary"),
        item("y", "record", "余量", "80", unit="%"),
        item("z", "record", "", "已有结果"),
    ]
    assert (
        solve(
            harness,
            items,
            [action("one", "执行第一个操作"), action("two", "执行第二个操作")],
        )
        is None
    )
