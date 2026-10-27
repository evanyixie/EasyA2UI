"""P5 拼装完整 IR（语义单点事实源）+ 容量预算。

容量分两路（v3 §8）：
  固定几何槽位（内高确定）→ 交容量引擎 capacity.adapt_slot 做
    "结构候选 × 字号梯级"的前向枚举与宽度+高度双预算验收，结果写
    ir["slot_layouts"]，并回写条目字号 / 截断文案；
  弹性槽位（内高 auto）→ 沿用宽度预算：hero 走降档序列 38/30/24/20，
    普通文字按槽位宽度语义截断。
数据类文字的运行时长度仍归渲染层兜底。
"""
import json
import uuid

from . import capacity
from .metrics import BUDGET, HERO_MAX_CHARS, est_height, est_width, semantic_truncate
from .sample_values import has_real_data
from .sample_values import infer_sample
from pathlib import Path

_semantic_truncate = semantic_truncate  # 兼容旧调用名

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = json.loads((ROOT / "registry/copy_templates.json").read_text(encoding="utf-8"))
LADDERS = json.loads((ROOT / "registry/ladders.json").read_text(encoding="utf-8"))
ROLES = json.loads((ROOT / "registry/components.json").read_text(encoding="utf-8"))["roles"]

SEMANTIC_ID = {"title": "title", "subtitle": "subtitle", "discount": "highlight", "price": "highlight",
               "deadline": "deadline", "member_tag": "tag", "source": "footnote", "stat": "stat",
               "primary_button": "cta-primary", "secondary_button": "cta-secondary",
               "toggle": "cta-toggle", "link": "cta-link"}

HERO_LADDER = LADDERS["hero_downgrade_ladder"]
BUDGET = LADDERS["text_width_budget"]


def fill_copy(intent: str, entry: dict) -> str:
    """文案模板库命中 → 模板填充；未命中 → hint 兜底。在线链路不做文案创作。"""
    tpl = TEMPLATES.get(intent, {}).get(entry["type"])
    return tpl.format(hint=entry["hint"]) if tpl else entry["hint"]


def _slot_geometry(tree: dict) -> dict:
    """从骨架 tree 提取每个槽位的可用文本宽度（容器宽 - 左右 padding）。"""
    return {slot: b["inner_w"] for slot, b in _slot_boxes(tree).items() if b["inner_w"] is not None}


def _slot_boxes(tree: dict) -> dict:
    """从骨架 tree 提取每个槽位的盒模型：宽/高/内宽/内高（非数值即 None）。"""
    boxes = {}

    def pad_axis(p, x_axis):
        if isinstance(p, dict):
            return (p.get("left", 0) + p.get("right", 0)) if x_axis else (p.get("top", 0) + p.get("bottom", 0))
        v = 2 * (p if isinstance(p, (int, float)) else 0)
        return v

    def walk(node):
        slot = node.get("slot")
        styles = node.get("styles", {})
        if slot:
            w, h = styles.get("width"), styles.get("height")
            w_num = w if isinstance(w, (int, float)) else None
            h_num = h if isinstance(h, (int, float)) else None
            padding = styles.get("padding", 0)
            boxes[slot] = {
                "slot": slot, "kind": node.get("kind"), "w": w_num, "h": h_num,
                "inner_w": (w_num - pad_axis(padding, True)) if w_num is not None else None,
                "inner_h": (h_num - pad_axis(padding, False)) if h_num is not None else None,
            }
        for ch in node.get("children", []) or []:
            walk(ch)
    walk(tree)
    return boxes


def _base_size(spec: dict) -> float:
    """角色的初始字号（候选梯级的起点）：hero_value 取降档序列首档。"""
    if "fontSize" in spec:
        return spec["fontSize"]
    if spec.get("ladder") == "hero_downgrade_ladder":
        return HERO_LADDER[0]["value"]
    return 14


def _audit_entry(e: dict, width: float, log: list) -> None:
    """宽度预算审计：hero 降档序列；普通文字按规格字号截断。"""
    spec = e["spec"]
    if e["role"] == "hero_value":
        for step in HERO_LADDER:
            size = step["value"]
            if est_width(e["copy"], size) * (1 + BUDGET["margin_ratio"]) <= width:
                spec["fontSize"] = size
                return
        size = HERO_LADDER[-1]["value"]
        new = _semantic_truncate(e["copy"], width / (1 + BUDGET["margin_ratio"]), size)
        log.append(f"capacity: hero ref {e['ref']} downgraded to {size}fp and truncated "
                   f"(len {len(e['copy'])} -> {len(new)})")
        e["copy"] = new
        spec["fontSize"] = size
        return
    size = spec.get("fontSize", 14)
    # 静态文案宽度已知，不再加压力余量；胶囊按钮文案仍按 1.2 倍预算
    margin = 1.0
    if e["role"] == "capsule_action":
        # 胶囊是 Row[图标 20, 间距 8, 文字]，文字拿不到整槽宽——
        # 曾按 126 全额预算，导致"设置手机使用时长"112px 塞进 98px 被硬裁（q38 实测）
        width = max(40.0, width - float(spec.get("icon", 20)) - float(spec.get("icon_gap", 8)))
    if est_width(e["copy"], size) * margin > width:
        new = _semantic_truncate(e["copy"], width / margin, size)
        if new != e["copy"]:
            log.append(f"capacity: semantic-truncated ref {e['ref']} "
                       f"(width over budget at {size}fp, len {len(e['copy'])} -> {len(new)})")
        e["copy"] = new


# 标签里的通用修饰词：拼"对象名 + 字段核心词"时去掉（剩余电量 -> 电量）
GENERIC_AFFIX = ("剩余", "当前", "状态", "情况", "信息", "数值", "百分比")


def _compose_label(obj_name: str, label: str) -> str:
    """同卡标签重复时，用「对象名 + 字段核心词」区分（金标 q20：手机电量 / 耳机仓电量）。

    拼出来超过 7 字就只留对象名（标签值行里对象名足够表意）。
    """
    obj_name = (obj_name or "").strip()
    label = (label or "").strip()
    if not obj_name or not label or obj_name in label:
        return obj_name or label
    core = label
    for a in GENERIC_AFFIX:
        core = core.replace(a, "")
    core = core.strip() or label
    cand = obj_name + core
    return cand if len(cand) <= 7 else obj_name


def assemble_ir(plan: dict, skel: dict, assign: dict, roles: dict, m1_intent) -> dict:
    log = list(plan["fallback_log"]) + list(roles["fallback_log"])
    geo = _slot_geometry(skel["tree"])

    # 槽位归属回填（供审计与发射使用）
    slot_of = {}
    for slot, f in assign["fills"].items():
        for r in f["info"] + f["action"]:
            slot_of[r] = slot

    # 数据类条目的样本值替换：泛化提示（"温度""天气"）-> 真实样值（"26°""晴"）
    DATA_TYPES = {"stat", "percent", "subtitle", "price", "discount", "deadline", "source"}

    # ── 同卡标签去重（q20 实测）────────────────────────────────────────
    # M1 常把两个不同对象的同类字段抽成同一个 hint（手机/耳机仓都叫"剩余电量"），
    # 于是标签重复、**样本值也跟着重复**（两个 68%），卡面出现"手机 68% / 耳机仓 68%"。
    # 金标做法是「对象名 + 字段核心词」（手机电量 / 耳机仓电量 / 耳机连接），
    # 这里用确定性规则复现：仅在标签重复时加对象名限定，单对象卡不受影响。
    ref_obj = {}
    for o in plan.get("objects") or []:
        for f in o.get("fields") or []:
            ref_obj.setdefault(f, o.get("name_hint") or "")
    _dup = {}
    for e in plan["entries"]:
        if e["kind"] == "info" and e["type"] in DATA_TYPES:
            _dup[e["hint"]] = _dup.get(e["hint"], 0) + 1

    ir_entries = []
    for e in plan["entries"]:
        role = roles["roles"][e["ref"]]
        spec = dict(ROLES[role]["spec"])
        hint = e["hint"]
        # 数据类条目：hint 若像"字段名/标签"（无数字）且能取到样本值，则
        # 把 hint 留作**标签**、样本值作**值** —— 这就是金标「标签值行」的形态
        # （q20「手机电量 … 68%」、S3「剩余电量 … 未充电」）。此前直接覆盖 hint，
        # 等于把标签丢了，卡面只剩孤零零的数值。
        label = None
        hint_name = e["hint"]          # 推断用的"字段名"（可能与原有 hint 不同）
        if e["type"] in DATA_TYPES and _dup.get(e["hint"], 0) > 1:
            # 标签重复：用「对象名 + 字段核心词」限定（"剩余电量"+手机 → "手机电量"）
            hint_name = _compose_label(ref_obj.get(e["ref"], ""), e["hint"])
        if e["type"] in DATA_TYPES:
            # 先用"去重后的标签"推断（能区分手机/耳机仓），失败再回退原字段名——
            # 去重标签在拼接超长时会退化成对象名（"产品立项会"），此时只有原字段名能推断出值
            sample = infer_sample(hint_name) or infer_sample(e["hint"])
            if sample:
                if not has_real_data(e["hint"]):
                    label = hint_name
                hint = sample
        entry = {
            "ref": e["ref"], "kind": e["kind"], "type": e["type"], "label": label,
            "copy": fill_copy(plan["intent"], {**e, "hint": hint}),
            "instance_id": f"{SEMANTIC_ID.get(e['type'], e['type'])}-r{e['ref']}",
            "role": role, "spec": spec,
            "binding": f"/data/items/{e['ref']}", "keep": e["keep"],
            "slot": slot_of.get(e["ref"]),
        }
        ir_entries.append(entry)

    # 主值定档按**最终文案**复核（样本值替换之后才看得到真值）：
    #   数值型短值 → hero_value（30/700，金标主数字档）
    #   文本型/超长 → status_lead（18/700，金标文本主值档）
    # hint 常是字段名（"降雨概率"→"20%"），用 hint 判 hero 会判错；且样本值会让文案变长
    # （"天气预警"→"大风蓝色预警"）。仅当全卡只有**一个**数值候选时才提升为 hero，
    # 避免"多个数值各占一行大字"。
    hero_cands = [e for e in ir_entries
                  if e["kind"] == "info" and e["type"] in DATA_TYPES
                  and len(e["copy"]) <= HERO_MAX_CHARS and has_real_data(e["copy"])]
    sole = len(hero_cands) == 1
    # 同一槽位有条目数上限：3 条以上必须整列成行（标签值行），
    # 此时把某一条提成 30fp 大字既放不下、也会挡掉行布局（q13 溢出的根因）
    per_slot = {}
    for e in ir_entries:
        if e["kind"] == "info" and e.get("slot"):
            per_slot[e["slot"]] = per_slot.get(e["slot"], 0) + 1
    for e in ir_entries:
        if e["kind"] != "info" or e["type"] not in DATA_TYPES:
            continue
        is_num_hero = (len(e["copy"]) <= HERO_MAX_CHARS and has_real_data(e["copy"])
                       and per_slot.get(e.get("slot"), 0) <= 2)
        was = e["role"]
        if was not in ("hero_value", "status_lead"):
            continue      # 只调"主值类"角色：zone/board/compact/capsule 等由槽位与形态决定
        want = "hero_value" if (is_num_hero and (sole or was == "hero_value")) else "status_lead"
        if was != want:
            e["role"] = want
            e["spec"] = dict(ROLES[want]["spec"])
        if want == "hero_value" and was != "hero_value":
            e["promoted_hero"] = True   # 由"唯一数值候选"提升来的主值，不再参与标签行

    # 意图贯穿校验（残差连接）：M1 未显式给 intent 时不校验
    if m1_intent and plan["intent"] != m1_intent:
        log.append(f"intent mismatch: {m1_intent} -> {plan['intent']}")

    # 容量适配（v3 §8）：固定几何槽位走"前向枚举 + 首个可行解"
    boxes = _slot_boxes(skel["tree"])
    by_ref = {e["ref"]: e for e in ir_entries}
    items_by_slot = {}
    for e in ir_entries:
        if e["kind"] == "info" and e["slot"]:
            items_by_slot.setdefault(e["slot"], []).append(e)

    slot_layouts = {}
    for slot, items in items_by_slot.items():
        box = boxes.get(slot) or {}
        payload = [{"ref": it["ref"], "role": it["role"], "type": it["type"],
                    "copy": it["copy"], "keep": it["keep"],
                    "base_size": _base_size(it["spec"]), "order": i,
                    "min_size": it["spec"].get("min_size")}
                   for i, it in enumerate(items)]
        res = capacity.adapt_slot(payload, box)
        if not res:
            continue
        for ref, size in (res.get("fonts") or {}).items():
            by_ref[ref]["spec"]["fontSize"] = size
        for ref, text in (res.get("truncated") or {}).items():
            by_ref[ref]["copy"] = text
        slot_layouts[slot] = res
        # 选择轨迹留在 slot_layouts；仅"降级选择"（链尾截断 / 丢弃条目）进 fallback_log
        if res.get("candidate") == "truncate" or res.get("dropped"):
            log.extend(res.get("log") or [])

    # 弹性槽位与未归属条目的宽度审计（固定槽位已由容量引擎处理）
    default_w = 126 if skel["resolved_size"] == "2x2" else 276
    for e in ir_entries:
        # 胶囊动作也要审计：它是 Row[图标 20, 间距 8, 文字]，文字拿不到整槽宽。
        # 此前循环只处理 kind=="info"，胶囊文案从未被审计 → "设置手机使用时长" 被硬裁（q38 实测）
        if e["kind"] == "action":
            if e["role"] == "capsule_action":
                _audit_entry(e, geo.get(e["slot"], default_w), log)
            continue
        if e["slot"] in slot_layouts:
            continue
        w = geo.get(e["slot"], default_w)
        _audit_entry(e, w, log)

    return {
        "surface_id": f"sfc-{uuid.uuid4().hex[:8]}",
        "size": skel["resolved_size"],
        "domain": plan["domain"],
        "intent": plan["intent"],
        "theme": None,  # P6 主题装配写入
        "entries": ir_entries,
        "objects": plan["objects"],
        "fills": assign["fills"],
        "slot_layouts": slot_layouts,
        "relations": plan["relations"],
        "groups": plan["groups"],
        "skeleton_id": skel["sid"],
        "fallback_log": log,
    }
