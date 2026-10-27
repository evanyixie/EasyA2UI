"""度量层单测：记录结构、指纹归一化、内容指标的判定口径。

内容指标最容易写错的地方是"什么时候算命中"——数字边界、单位差异、编造值。
每个用例只改一处，断言恰好那一个数字变化。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.measure import build_record, extract_text, fingerprint, static_metrics  # noqa: E402
from tools.measure_content import check                                        # noqa: E402


def _card(texts, fonts=None):
    comps = [{"id": "root", "component": "Column", "children": [], "styles": {}}]
    for i, t in enumerate(texts):
        st = {"fontSize": (fonts[i] if fonts else 12)}
        comps.append({"id": f"t{i}", "component": "Text", "content": t, "styles": st})
    lines = [{"version": "v0.9", "createSurface": {"surfaceId": "sfc-abcdef12",
                                                  "catalogId": "ohos.a2ui.extended.catalog.form"}},
             {"version": "v0.9", "updateComponents": {"surfaceId": "sfc-abcdef12",
                                                     "components": comps}},
             {"version": "v0.9", "updateDataModel": {"surfaceId": "sfc-abcdef12",
                                                    "path": "/", "value": {}}}]
    return "\n".join(json.dumps(l, ensure_ascii=False) for l in lines)


FACTS = [{"key": "districtName", "value": "青浦区"},
         {"key": "batterySOC", "value": "68"},
         {"key": "condition", "value": "多云"}]


def _text(texts, fonts=None):
    """内容指标吃的是卡面文字，不是整段 JSONL——这里显式走一次抽取。"""
    return extract_text(_card(texts, fonts))


def test_fingerprint_ignores_surface_id():
    a = _card(["多云"])
    b = a.replace("sfc-abcdef12", "sfc-99999999")
    assert fingerprint(a) == fingerprint(b)


def test_extract_text_and_static():
    text = _card(["多云", "68%"], fonts=[12, 10])
    assert extract_text(text) == "多云\n68%"
    st = static_metrics(text)
    assert st["min_font"] == 10 and st["texts"] == 2


def test_build_record_fields():
    result = {"full-a2ui": _card(["多云"]),
              "ir": {"skeleton_id": "S2-info-pair-action", "size": "2x2",
                     "domain": "weather", "theme": "blue"},
              "meta": {"failed": False, "violations": [], "violation_codes": {},
                       "fallback_log": [], "timing": {"total_ms": 5},
                       "cost": {"calls": 1}, "options": {}}}
    rec = build_record("q01", "L4", "看天气", result)
    assert rec["clean"] is True and rec["skeleton"] == "S2-info-pair-action"
    assert rec["static"]["min_font"] == 12
    assert rec["layout"] is None and rec["content"] is None


def test_content_full_coverage():
    r = check(_text(["青浦区", "多云", "68%"]), FACTS)
    assert r["coverage"] == 1.0 and r["missing"] == []
    assert r["precision"] == 1.0 and r["unsupported"] == []


def test_content_missing_one():
    r = check(_text(["青浦区"]), FACTS)
    assert r["coverage"] == round(1 / 3, 3)
    assert set(r["missing"]) == {"68", "多云"}


def test_content_number_boundary():
    """168 里不该把 68 算成命中。"""
    r = check(_text(["青浦区", "多云", "168"]), FACTS)
    assert "68" in r["missing"]


def test_content_unit_added_by_card_is_not_fabrication():
    """基准是 68，卡面写 68% —— 单位是卡面加的，不算编造。"""
    r = check(_text(["68%"]), FACTS)
    assert r["precision"] == 1.0


def test_content_unsupported_number():
    r = check(_text(["青浦区", "多云", "68%", "降水 30%"]), FACTS)
    assert "30%" in r["unsupported"] and r["precision"] < 1.0


def test_content_duplicate():
    r = check(_text(["68%", "68%"]), FACTS)
    assert r["duplicated"] == 1


def test_static_two_font_lines():
    """口径 C-05：12fp 与 10fp 两条线分开数。"""
    st = static_metrics(_card(["a", "b", "c"], fonts=[12, 11, 9]))
    assert st["below_12fp"] == 2 and st["below_10fp"] == 1


def test_failed_record_counts_as_violation():
    """口径 C-01：失败卡记 generate.failed，clean=False。"""
    result = {"full-a2ui": "", "ir": {},
              "meta": {"failed": True, "violations": [], "violation_codes": {},
                       "fallback_log": ["M1 empty plan -> generation failed"],
                       "timing": {}, "cost": {}, "options": {}}}
    rec = build_record("q01", "L1", "x", result)
    assert rec["clean"] is False
    assert rec["violation_codes"] == {"generate.failed": 1}


def test_coverage_must_requires_annotation():
    """口径 C-02：未标 must 时 coverage_must 是 None（未量），不是 0。"""
    r = check(_text(["青浦区"]), FACTS)
    assert r["coverage_must"] is None
    facts = [dict(f, must=(f["key"] == "condition")) for f in FACTS]
    r2 = check(_text(["青浦区", "多云"]), facts)
    assert r2["coverage_must"] == 1.0 and r2["coverage"] < 1.0


def test_empty_data_card_flag():
    """口径 C-03：卡面没有数据型片段时 precision=None 且 empty_data=True。"""
    r = check(_text(["青浦区", "多云"]), FACTS)
    assert r["precision"] is None and r["empty_data"] is True


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"✅ {name}")
    print("✅ test_measure 全部通过")
