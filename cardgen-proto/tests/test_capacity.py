"""容量适配专项测试（v3 §8）：前向枚举 + 首个可行解。

覆盖：
  T1  保原形（弹性槽位仍走宽度预算）
  T3  换轴（S3 单行区：纵排放不下 → 横排单行，用户案例 68% + 充电中）
  T4  合并（小背板 / 单行区）
  T6  省略（keep=should 丢弃）
  T7  截断（链尾兜底，必有解且记 fallback_log）
  + 协议合规（check_full_a2ui）与"合并条目不出现在组件树"的完整性断言

运行：python tests/test_capacity.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import assemble, capacity, compiler, component_select, normalize, slot_assign  # noqa: E402
from src import theme as theme_step  # noqa: E402
from tests.run_cases import check_full_a2ui  # noqa: E402

REG = json.loads((ROOT / "registry/skeletons.json").read_text(encoding="utf-8"))["skeletons"]


def build(plan_raw: dict, sid: str):
    """强制指定骨架，跑 P1~P7，返回 (ir, components, full_a2ui)。"""
    plan = normalize.normalize_plan(plan_raw)
    skel = dict(REG[sid])
    skel["sid"], skel["resolved_size"] = sid, skel["size"]
    assign = slot_assign.assign_regions(plan, skel)
    slot_of = {}
    for slot, f in assign["fills"].items():
        for r in f["info"] + f["action"]:
            slot_of[r] = slot
    roles = component_select.select_roles(plan["entries"], slot_of=slot_of)
    ir = assemble.assemble_ir(plan, skel, assign, roles, plan.get("intent"))
    theme_step.apply_theme(ir, m1_theme=None)
    full = compiler.compile_a2ui_full(ir)
    comps = json.loads(full.splitlines()[1])["updateComponents"]["components"]
    return ir, comps, full


def plan(size, domain, objects, infos, actions=None):
    return {"domain": domain, "intent": "info_card", "size": size, "theme": None,
            "objects": objects, "info_items": infos, "actions": actions or [],
            "relations": [], "groups": [], "fallback_log": []}


def comp(comps, cid):
    return next((c for c in comps if c["id"] == cid), None)


REPORT = []


def case(name, ok, detail=""):
    REPORT.append((name, ok, detail))
    print(f"{'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail else ""))


# ---------------- 用例 1：S3 单行区换轴（用户案例 68% + 充电中） ----------------
p1 = plan("2x2", "earphone",
          [{"name_hint": "耳机盒", "fields": [2, 3]}],
          [{"ref": 2, "type": "stat", "content_hint": "68%", "keep": "must"},
           {"ref": 3, "type": "subtitle", "content_hint": "充电中", "keep": "must"}],
          [{"ref": 4, "type": "link", "content_hint": "每日歌单", "keep": "must"},
           {"ref": 5, "type": "link", "content_hint": "收藏歌单", "keep": "must"}])
ir1, comps1, full1 = build(p1, "S3-info-dual-action")
lay = ir1["slot_layouts"].get("content", {})
case("T3 换轴：S3 单行区选中 row 候选",
     lay.get("structure") == "row" and lay.get("candidate") == "row",
     f"structure={lay.get('structure')} candidate={lay.get('candidate')}")
wrapper = comp(comps1, "content-row0")
case("T3 换轴：同行内容包裹在小 Row 内（底部对齐）",
     wrapper is not None and wrapper["component"] == "Row"
     and wrapper["styles"].get("alignItems") == "bottom"
     and len(wrapper.get("children", [])) == 2,
     json.dumps(wrapper, ensure_ascii=False)[:120] if wrapper else "未找到 content-row0")
sizes = {e["ref"]: e["spec"].get("fontSize") for e in ir1["entries"]}
case("T3 换轴：字号按高度预算收敛（hero 38 → 24）",
     sizes.get(1) == 24 and sizes.get(2) == 14, f"fonts={sizes}")
case("T3 换轴：协议合规", not check_full_a2ui(full1, ir1["surface_id"], "2x2"))

# ---------------- 用例 2：S4 小背板两行（T1 保原形） ----------------
p2 = plan("2x2", "battery",
          [{"name_hint": "手机", "fields": [1, 2]},
           {"name_hint": "耳机盒", "fields": [3, 4]}],
          [{"ref": 1, "type": "stat", "content_hint": "68%", "keep": "must"},
           {"ref": 2, "type": "subtitle", "content_hint": "充电中", "keep": "must"},
           {"ref": 3, "type": "stat", "content_hint": "47%", "keep": "must"},
           {"ref": 4, "type": "subtitle", "content_hint": "未充电", "keep": "must"}])
ir2, comps2, full2 = build(p2, "S4-stacked-zones")
z0 = ir2["slot_layouts"].get("zone:0", {})
case("T1 保原形：小背板两行纵排",
     z0.get("structure") == "stack" and len(z0.get("rows", [])) == 2,
     f"rows={z0.get('rows')}")
case("T1 保原形：背板两行字号 16/12",
     comp(comps2, "stat-r1")["styles"]["fontSize"] == 16
     and comp(comps2, "subtitle-r2")["styles"]["fontSize"] == 12,
     f"line1={comp(comps2, 'stat-r1')['styles'].get('fontSize')} "
     f"line2={comp(comps2, 'subtitle-r2')['styles'].get('fontSize')}")
case("T1 保原形：协议合规", not check_full_a2ui(full2, ir2["surface_id"], "2x2"))

# ---------------- 用例 3：合并候选（机制级单测 + 背板 ` | ` 行合并集成） ----------------
_pick = capacity._fit_merged(
    [{"ref": 1, "role": "zone_value_line", "type": "stat", "copy": "68%",
      "keep": "must", "base_size": 14, "order": 0, "min_size": 12},
     {"ref": 2, "role": "zone_aux_line", "type": "subtitle", "copy": "充电中",
      "keep": "must", "base_size": 12, "order": 1, "min_size": 12}],
    {"slot": "zone:0", "inner_w": 110, "inner_h": 39})
case("T4 合并：_fit_merged 产出 ` · ` 连接的单条文本",
     _pick is not None and _pick["structure"] == "merged"
     and _pick["merged_copy"] == "68% · 充电中" and _pick["rows"] == [[1, 2]],
     f"{(_pick or {}).get('merged_copy')}")

p3 = plan("2x2", "battery",
          [{"name_hint": "手机", "fields": [1, 2, 3]}],
          [{"ref": 1, "type": "stat", "content_hint": "68%", "keep": "must"},
           {"ref": 2, "type": "subtitle", "content_hint": "快充", "keep": "must"},
           {"ref": 3, "type": "subtitle", "content_hint": "低温", "keep": "must"}])
ir3, comps3, full3 = build(p3, "S4-stacked-zones")
z0b = ir3["slot_layouts"].get("zone:0", {})
texts3 = [c.get("content") for c in comps3 if c["component"] == "Text"]
case("T4 行合并：小背板三项 → 第一行主值 + 第二行 ` | ` 合并",
     z0b.get("kind") == "board" and z0b.get("structure") == "stack"
     and len(z0b.get("rows", [])) == 2 and len(z0b["rows"][1]) == 2
     and any("|" in (t or "") for t in texts3),
     f"kind={z0b.get('kind')} rows={z0b.get('rows')} texts={texts3}")
case("T4 行合并：协议合规", not check_full_a2ui(full3, ir3["surface_id"], "2x2"))

# ---------------- 用例 4：省略候选（keep=should 丢弃） ----------------
# 注意：这里的超长文案必须**不命中** src/sample_values.py 的关键词表，
# 否则会被样本值替换成短文本（如"空气"→"良"），就不超宽了。
p4 = plan("2x2", "weather",
          [{"name_hint": "深圳", "fields": [1, 2]}],
          [{"ref": 1, "type": "stat", "content_hint": "26°", "keep": "must"},
           {"ref": 2, "type": "subtitle", "content_hint": "这是一条很长的可选支撑说明文字用于触发超宽丢弃", "keep": "should"}])
ir4, comps4, full4 = build(p4, "S4-stacked-zones")
z0c = ir4["slot_layouts"].get("zone:0", {})
case("T6 省略：超宽的可选行被丢弃并记 fallback",
     any(e["ref"] == 2 for e in ir4["entries"])
     and not any(c["id"] == "subtitle-r2" for c in comps4)
     and any("dropped" in x for x in ir4["fallback_log"]),
     f"fallback={ir4['fallback_log']}")

# ---------------- 用例 5：截断兜底（单条超长，链尾必解） ----------------
p5 = plan("2x2", "unknown",
          [{"name_hint": "未知", "fields": [2]}],
          [{"ref": 2, "type": "subtitle",
            "content_hint": "这是一条极其冗长的说明文字用于触发链尾截断兜底分支的验证", "keep": "must"}],
          [{"ref": 4, "type": "link", "content_hint": "去看看", "keep": "must"},
           {"ref": 5, "type": "link", "content_hint": "再逛逛", "keep": "must"}])
ir5, comps5, full5 = build(p5, "S3-info-dual-action")
lay5 = ir5["slot_layouts"].get("content", {})
case("T7 截断：链尾兜底被选中且文案带省略号",
     lay5.get("candidate") == "truncate"
     and any((c.get("content") or "").endswith("…") for c in comps5),
     f"candidate={lay5.get('candidate')} truncated={lay5.get('truncated')}")
case("T7 截断：fallback_log 记录兜底（供候选表收敛）",
     any("链尾兜底" in x for x in ir5["fallback_log"]), f"{ir5['fallback_log']}")
case("T7 截断：协议合规", not check_full_a2ui(full5, ir5["surface_id"], "2x2"))

# ---------------- 用例 6：弹性槽位不介入（T1 宽度预算照旧） ----------------
p6 = plan("2x2", "promotion",
          [{"name_hint": "会员", "fields": [1, 2, 3]}],
          [{"ref": 1, "type": "title", "content_hint": "双11会员促销", "keep": "must"},
           {"ref": 2, "type": "discount", "content_hint": "5折", "keep": "must"},
           {"ref": 3, "type": "price", "content_hint": "¥199", "keep": "must"}],
          [{"ref": 4, "type": "primary_button", "content_hint": "立即购买", "keep": "must"}])
ir6, comps6, full6 = build(p6, "S2-info-pair-action")
case("弹性槽位：content 不产生固定槽位布局（走宽度预算）",
     "content" not in ir6["slot_layouts"] or ir6["slot_layouts"]["content"]["kind"] == "flow",
     f"layouts={list(ir6['slot_layouts'].keys())}")
case("弹性槽位：协议合规", not check_full_a2ui(full6, ir6["surface_id"], "2x2"))

# ---------------- 汇总 ----------------
bad = [r for r in REPORT if not r[1]]
print(f"\n== 容量适配专项：{len(REPORT) - len(bad)}/{len(REPORT)} 通过 ==")
sys.exit(1 if bad else 0)
