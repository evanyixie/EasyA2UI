"""P2 骨架选择：尺寸决策 + 业务对象数路由（对齐 CreateMyCard 固定骨架四分法）。

路由顺序（UX-SPEC 第九节口 requiem）：先按 size 选分册（2x2 用 S1~S4，
2x4 用 W1~W10）→ 再按业务对象数 → 再按信息特征/动作数 → 兜底骨架。
对象数是第一判据：同对象的多个字段只算 1 个对象，字段数不增加对象数。

骨架不为文字量负责——文字容量由 P4/P5 的宽度预算处理。
"""
import json
from pathlib import Path

from .text_metrics import HERO_MAX_CHARS

ROOT = Path(__file__).resolve().parent.parent
REG = json.loads((ROOT / "rules/skeletons.json").read_text(encoding="utf-8"))
SKELS = REG["skeletons"]

# ⚠️ 故意不含 percent：percent 是"环形主值"信号，环画在 S2 的 content 槽里；
# 若把 percent 当 hero，单百分比卡会进 S1（居中单焦点）而丢掉环（实测 4 条卡会变）。
HERO_TYPES = {"discount", "price", "stat"}


def derive_features(plan: dict) -> dict:
    """从归一化计划派生路由特征（全部确定性规则，无模型参与）。"""
    infos = [e for e in plan["entries"] if e["kind"] == "info"]
    non_title = [e for e in infos if e["type"] != "title"]
    heroes = [e for e in non_title if e["type"] in HERO_TYPES and len(e["hint"]) <= HERO_MAX_CHARS]
    objects = plan["objects"]
    type_of = {e["ref"]: e["type"] for e in plan["entries"]}

    def _fields(o):  # 业务字段（标题归 header，不计入对象字段）
        return [f for f in o["fields"] if type_of.get(f) != "title"]

    return {
        "n_objects": len(objects) or 1,
        # ⚠️ 只数**非标题**条目：标题是显示字段（可缺、可兜底补），
        # 若把它计入内容条数，"有没有标题"就会改变骨架（实测 54 条里 9 条会变），
        # 这正是 2026-10-19 那次"补标题把环卡挤成 S5"的根因。
        "n_info": len(non_title),
        "n_act": sum(1 for e in plan["entries"] if e["kind"] == "action"),
        "hero": bool(heroes),
        "list": len(non_title) >= 3 and len(set(e["type"] for e in non_title)) <= 2,
        "triple_stats": len(non_title) == 3 and len(set(e["type"] for e in non_title)) == 1,
        "text": not heroes and all(e["type"] in ("title", "subtitle", "source", "member_tag") or len(e["hint"]) > 8 for e in non_title),
        "progress": False,  # 原型不产数值+total 语义，Progress 相关骨架保持休眠
        # 图标入口：数据 M2 的圆形图标钮（无文字标签）——它是 S2/S6 的唯一结构分界，
        # 由 M1 用 action_type=icon_button 显式声明（语义上二者等价，见 UX-SPEC §11.3）
        "icon_action": any(e["kind"] == "action" and e["type"] == "icon_button"
                           for e in plan["entries"]),
        # 「多对象 × 单值」= 设备/指标清单（金标 34/52 张用「标签值行」）：一行一个对象，
        # 左标签右数值 → 走单内容区 S2，不走 S5 的主辅二分（金标 q20 佐证，2026-10-16）
        "label_value_list": len(objects) >= 2 and all(len(_fields(o)) == 1 for o in objects),
        # 非标题数据条目数（S1 单焦点骨架的容量判据）
        "n_data": len([e for e in non_title]),
        # 恰好两个"同构多字段"对象（明天/后天、成都/上海）→ S4 上下双背板
        "dual_blocks": len(objects) == 2 and all(len(_fields(o)) >= 2 for o in objects),
    }


def decide_size(plan: dict, feats: dict) -> str:
    """尺寸决策：尊重 M1 的显式 size；auto 时默认 2×2。

    **2026-10-16 变更（对齐真实数据）**：取消"业务对象 ≥3 → 强制 2×4"的硬约束。
    金标 52 张全部 2×2，其中含跨 3 个数据来源的卡（日程 + 耳机 + 耳机仓）——
    对象数不决定画布尺寸。一屏信息塞不下时该走容量降级（P5 在**条目层面**处理），
    而不是把画布放大一倍；放大画布会让同一业务的卡凭空长出白背板与第二屏结构。
    """
    return plan["size"] if plan["size"] in ("2x2", "2x4") else "2x2"


def _match_range(rng, n):
    return rng[0] <= n <= rng[1]


def select_skeleton(plan: dict) -> dict:
    log = plan["fallback_log"]
    feats = derive_features(plan)
    size = decide_size(plan, feats)
    n_obj, n_act = min(feats["n_objects"], 4), feats["n_act"]

    if n_obj > 4:
        log.append(f"objects {feats['n_objects']} > 4 -> capped to 4")
        n_obj = 4

    # 路由决策表：条件按序命中即停（**形态优先**；对象数只用于 S4）
    route = []
    if size == "2x2":
        route = [  # 顺序即优先级（动作形态 → 无动作的区划 → 兜底）
                 # S4：恰好两个"同构多字段"对象且无动作（金标 q10 明天/后天、q34 成都/上海）。
                 # 注意：不按"2 对象 + 有动作 → S6"——S6 的入口是 40×40 圆钮，
                 # 若动作是胶囊会塞不进该槽（金标 q26/q29 走 S6 是因为它们本就是圆钮）。
                 (feats["dual_blocks"] and n_act == 0, "S4-stacked-zones"),
                 (n_act >= 2, "S3-info-dual-action"),
                 # S6：单个**图标入口**动作 → 主区 + 底部复合行（辅信息列 + 圆钮）
                 (n_act == 1 and feats["icon_action"], "S6-primary-bottom-action"),
                 # S5：无动作 + 信息 ≥3 且**非**"多对象×单值清单" → 主区 + 辅区纵向二分
                 (n_act == 0 and feats["n_info"] >= 3 and not feats["label_value_list"],
                  "S5-primary-support"),
                 # S1 只接"单焦点"（标题/数值/单位一组）：非标题数据条目 ≤1，
                 # 否则 hero 槽放不下第二个数据项 → 内容丢失（q11 实测）
                 (feats["hero"] and n_act == 0 and feats["n_data"] <= 1, "S1-single-info"),
                 (True, "S2-info-pair-action")]
    else:
        route = [(n_obj >= 4, "W8-quad-cells"),
                 (n_obj == 3, "W10-triple-backboards"),
                 (n_obj == 2, "W9-dual-backboards"),
                 (n_act >= 2, "W6-agenda-cta"),
                 (feats["triple_stats"], "W4-metric-triple"),
                 (feats["list"], "W7-list-rows"),
                 (feats["progress"], "W3-ring-detail"),
                 (feats["text"] and n_act == 0, "W2-text-flow"),
                 (True, "W1-focus-aux")]

    sid = next(s for cond, s in route if cond)
    skel_def = SKELS[sid]
    sel = skel_def["select"]
    if not _match_range(sel.get("actions", [0, 99]), n_act):
        log.append(f"{sid} expects actions {sel.get('actions')}, got {n_act} -> adapted")
    if sel["objects"][0] > n_obj or n_obj > sel["objects"][1]:
        log.append(f"{sid} expects objects {sel['objects']}, got {n_obj} -> adapted")

    skel = json.loads(json.dumps(skel_def, ensure_ascii=False))  # deep copy
    skel["sid"] = sid
    skel["resolved_size"] = size
    skel["features"] = feats
    return skel
