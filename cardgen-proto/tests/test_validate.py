"""校验器单测：规则唯一事实源，既要能判对错，也要能定位与分组统计。

每个用例只破坏一处，断言“恰好报出那一类 code”，防止规则悄悄漏判或多判。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from src.validate import validate_a2ui, count_by_code
from src.pipeline import generate
from src.M1_extract import MockLLM

SID = "surface-test"
CATALOG = "ohos.a2ui.extended.catalog.form"


def _lines(components=None, canvas=(150, 150), catalog=CATALOG, version="v0.9",
           data_model=None):
    comps = components if components is not None else [
        {"id": "root", "component": "Column", "children": ["t1"],
         "styles": {"width": canvas[0], "height": canvas[1],
                    "borderRadius": 20, "clip": True}},
        {"id": "t1", "component": "Text", "styles": {}},
    ]
    return [
        {"version": version, "createSurface": {"surfaceId": SID, "catalogId": catalog}},
        {"version": version, "updateComponents": {"surfaceId": SID, "components": comps}},
        {"version": version, "updateDataModel": {"surfaceId": SID, "path": "/",
                                                 "value": data_model if data_model is not None else {}}},
    ]


def _text(lines):
    return "\n".join(json.dumps(l, ensure_ascii=False) for l in lines)


def _codes(text, size="2x2"):
    return [v.code for v in validate_a2ui(text, SID, size)]


def test_good_passes():
    assert _codes(_text(_lines())) == []


def test_line_count():
    assert _codes(_text(_lines()[:2])) == ["jsonl.line_count"]
    assert _codes("") == ["jsonl.line_count"]


def test_broken_json():
    assert _codes('{"a":1}\n{"b":2}\n{not json}') == ["jsonl.parse"]


def test_envelope_keys_and_version():
    lines = _lines(version="v0.8")
    codes = _codes(_text(lines))
    assert codes.count("envelope.version") == 3
    assert "envelope.line1" not in codes

    lines = _lines()
    lines[0]["extra"] = True
    assert "envelope.line1" in _codes(_text(lines))


def test_catalog_and_surface():
    assert "catalog.id" in _codes(_text(_lines(catalog="wrong.catalog")))

    lines = _lines()
    lines[1]["updateComponents"]["surfaceId"] = "other"
    assert "surface.update_components" in _codes(_text(lines))


def test_root_count_and_dangling():
    comps = [{"id": "a", "component": "Column", "children": ["missing"],
              "styles": {"width": 150, "height": 150, "borderRadius": 20, "clip": True}}]
    codes = _codes(_text(_lines(components=comps)))
    assert "tree.root_count" in codes
    assert "tree.dangling_child" in codes


def test_component_whitelist():
    comps = [{"id": "root", "component": "Column", "children": ["x"],
              "styles": {"width": 150, "height": 150, "borderRadius": 20, "clip": True}},
             {"id": "x", "component": "Table", "styles": {}}]
    assert "component.not_allowed" in _codes(_text(_lines(components=comps)))


def test_button_rules():
    good = [{"id": "root", "component": "Column", "children": ["b"],
             "styles": {"width": 150, "height": 150, "borderRadius": 20, "clip": True}},
            {"id": "b", "component": "Button",
             "onClick": [{"call": "submit", "args": {}}], "styles": {}}]
    assert _codes(_text(_lines(components=good))) == []

    bad = [{"id": "root", "component": "Column", "children": ["b"],
            "styles": {"width": 150, "height": 150, "borderRadius": 20, "clip": True}},
           {"id": "b", "component": "Button", "action": "x", "onClick": [], "styles": {}}]
    codes = _codes(_text(_lines(components=bad)))
    assert "button.action_field" in codes and "button.on_click" in codes


def test_canvas_and_shell():
    assert "root.canvas" in _codes(_text(_lines(canvas=(150, 150))), size="2x4")

    comps = [{"id": "root", "component": "Column", "children": [],
              "styles": {"width": 150, "height": 150}}]
    codes = _codes(_text(_lines(components=comps)))
    assert "root.shell" in codes


def test_data_model():
    lines = _lines()
    lines[2]["updateDataModel"] = {"surfaceId": SID, "path": "no-slash"}
    codes = _codes(_text(lines))
    assert "data_model.path" in codes and "data_model.value" in codes


def test_count_by_code():
    lines = _lines(version="v0.8")
    vs = validate_a2ui(_text(lines), SID)
    counts = count_by_code(vs)
    assert counts["envelope.version"] == 3
    assert sum(counts.values()) == len(vs)


def test_real_pipeline_is_clean():
    """真实流水线产物必须 0 违规——这条同时守住“校验器和发射器不脱节”。"""
    r = generate("明天杭州西湖区天气怎么样", MockLLM())
    assert r["meta"]["violations"] == [], r["meta"]["violations"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"✅ {name}")
    print("✅ test_validate 全部通过")
