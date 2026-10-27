"""运行选项与“可关修正”的行为守卫。

三类断言：
  1. 选项本身：默认全开、环境变量可关、看不懂的值不静默反转；
  2. 行为：关掉 repair_plan 后，四条“改内容集合”的修正确实不生效；
  3. 兜底：关掉 placeholder_card 后，失败不被占位卡掩盖。
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from src import normalize
from src.llm import MockLLM
from src.pipeline import generate
from src.pipeline_options import PipelineOptions, load_options


def _plan(**kw):
    base = {"domain": "battery", "size": "2x2", "theme": None,
            "info_items": [], "actions": [], "objects": [], "relations": [], "groups": []}
    base.update(kw)
    return base


def _norm(plan, **overrides):
    """跑一次归一化。overrides 为空 = 默认（全开）；显式构造，避免受环境变量影响。"""
    opts = PipelineOptions(**overrides) if overrides else None
    return normalize.normalize_plan(json.loads(json.dumps(plan)), opts)


def test_defaults_on():
    opts = PipelineOptions()
    assert opts.repair_plan and opts.repair_card and opts.placeholder_card
    assert set(opts.describe()) == {"repair_plan", "repair_card", "placeholder_card"}


def test_env_override_and_garbage_is_ignored():
    os.environ["CARDGEN_REPAIR_PLAN"] = "0"
    os.environ["CARDGEN_REPAIR_CARD"] = "nonsense"   # 看不懂 → 保持默认，不能反转
    try:
        opts = load_options()
        assert opts.repair_plan is False
        assert opts.repair_card is True
    finally:
        os.environ.pop("CARDGEN_REPAIR_PLAN", None)
        os.environ.pop("CARDGEN_REPAIR_CARD", None)


def test_without_repair_keeps_placeholder():
    opts = PipelineOptions().without_repair()
    assert opts.repair_plan is False and opts.repair_card is False
    assert opts.placeholder_card is True


def test_dedupe_switch():
    plan = _plan(info_items=[{"ref": 1, "type": "source", "content_hint": "查看详情"}],
                 actions=[{"ref": 2, "type": "primary_button", "label_hint": "查看详情"}],
                 objects=[{"name_hint": "", "fields": [1]}])
    assert [e["kind"] for e in _norm(plan)["entries"]] == ["action"]
    assert [e["kind"] for e in _norm(plan, repair_plan=False)["entries"]] == ["info", "action"]


def test_percent_switch():
    plan = _plan(info_items=[{"ref": 1, "type": "stat", "content_hint": "剩余电量"}],
                 objects=[{"name_hint": "手机", "fields": [1]}])
    assert _norm(plan)["entries"][0]["type"] == "percent"
    assert _norm(plan, repair_plan=False)["entries"][0]["type"] == "stat"


def test_dangling_relation_switch():
    plan = _plan(info_items=[{"ref": 1, "type": "title", "content_hint": "电量"}],
                 relations=[{"from": 1, "to": 99, "type": "binds"}],
                 objects=[{"name_hint": "", "fields": [1]}])
    assert _norm(plan)["relations"] == []
    assert _norm(plan, repair_plan=False)["relations"] == [
        {"from": 1, "to": 99, "type": "binds"}]


def test_object_merge_switch():
    plan = _plan(info_items=[{"ref": 1, "type": "title", "content_hint": "耳机"},
                             {"ref": 2, "type": "percent", "content_hint": "左耳机电量"},
                             {"ref": 3, "type": "percent", "content_hint": "右耳机电量"}],
                 objects=[{"name_hint": "耳机", "fields": [2]}])
    assert set(_norm(plan)["objects"][0]["fields"]) == {1, 2, 3}
    assert set(_norm(plan, repair_plan=False)["objects"][0]["fields"]) == {2}


class _FixedPlanLLM:
    """返回固定计划的桩模型，用来构造“空计划”等边界输入。"""

    model = "fixed-plan"

    def __init__(self, plan):
        self.plan = plan

    def complete(self, prompt):
        return json.dumps(self.plan, ensure_ascii=False)


def test_placeholder_switch():
    empty = _FixedPlanLLM({"domain": "unknown", "size": "auto", "theme": None,
                           "info_items": [], "actions": [], "objects": [],
                           "relations": [], "groups": []})
    on = generate("随便说点什么", empty)
    assert on["ir"] is not None and on["ir"]["entries"]
    assert on["meta"]["failed"] is False

    off = generate("随便说点什么", empty, options=PipelineOptions(placeholder_card=False))
    assert off["meta"]["failed"] is True
    assert off["ir"] is None and off["full-a2ui"] == ""
    assert any("placeholder_card disabled" in x for x in off["meta"]["fallback_log"])


def test_meta_carries_options_and_violations():
    r = generate("明天杭州天气怎么样", MockLLM())
    assert r["meta"]["failed"] is False
    assert r["meta"]["options"] == {"repair_plan": True, "repair_card": True,
                                    "placeholder_card": True}
    assert isinstance(r["meta"]["violations"], list)
    assert isinstance(r["meta"]["violation_codes"], dict)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"✅ {name}")
    print("✅ test_pipeline_options 全部通过")
