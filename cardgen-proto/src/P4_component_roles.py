"""P4 组件角色选择：语义类型 + 特征 + **槽位形态** → 角色规格。

槽位感知（v3 §8）：board 类槽位（zone / aux 业务小背板）的条目不使用 hero 角色——
小背板空间只够"对象名+主值一行 + 次要信息一行"（M4），第一项统一 zone_value_line，
其余 zone_aux_line；hero 只出现在普通内容区。
其余条目沿用语义规则：hero 候选须为短提示（<=8 字）才落 hero_value，
否则落 status_lead；具体字号由 P5 容量引擎 / 宽度预算在梯级内最终确定。
"""
import json
from pathlib import Path

from .text_metrics import HERO_MAX_CHARS
from .sample_values import has_real_data

ROOT = Path(__file__).resolve().parent.parent
REG = json.loads((ROOT / "rules/components.json").read_text(encoding="utf-8"))
ROLES, RULES = REG["roles"], REG["select_rules"]


def _match(cond: dict, entry: dict) -> bool:
    if cond.get("actions") is True:
        if entry["kind"] != "action":
            return False
    if "types" in cond and entry["type"] not in cond["types"]:
        return False
    if "short" in cond:
        # hero 只承载"数值型短值"（68%/26°C/18天）：金标里文本型主值（多云/已连接）走
        # status_lead 18/700，只有数值才是 30/700 的大数字；超过 HERO_MAX_CHARS 也落 status_lead
        is_short = len(entry["hint"]) <= HERO_MAX_CHARS and has_real_data(entry["hint"])
        if is_short != cond["short"]:
            return False
    return True


BOARD_SLOT_PREFIXES = ("zone:", "aux:")
METRIC_SLOT_PREFIXES = ("triple:",)   # 三列指标：紧凑数值角色，不用 hero


def select_roles(entries: list, slot_of: dict = None) -> dict:
    """条目 → 角色。slot_of: {ref: slot_id}，用于槽位形态感知（可选）。"""
    picks, log = {}, []
    seen = {}
    for e in entries:
        slot = (slot_of or {}).get(e["ref"], "") or ""
        if slot.startswith(METRIC_SLOT_PREFIXES):
            picks[e["ref"]] = "compact_value"
            continue
        if slot == "bottom_action":
            picks[e["ref"]] = "icon_action"
            continue
        if slot == "primary":
            # 主区：首项主值（hero）/ 其余为同组单位或状态（hero_context）——数据 M1/M2 的"值 + 单位"
            idx = seen.get(slot, 0)
            seen[slot] = idx + 1
            if idx:
                picks[e["ref"]] = "hero_context"
            else:
                picks[e["ref"]] = ("hero_value"
                                   if len(e["hint"]) <= HERO_MAX_CHARS and has_real_data(e["hint"])
                                   else "status_lead")
            continue
        if slot in ("support", "bottom_info"):
            picks[e["ref"]] = "zone_aux_line"
            continue
        if slot.startswith(BOARD_SLOT_PREFIXES):
            idx = seen.get(slot, 0)
            seen[slot] = idx + 1
            picks[e["ref"]] = "zone_value_line" if idx == 0 else "zone_aux_line"
            continue
        hit = next((r["role"] for r in RULES if _match(r["if"], e)), None)
        if hit is None:
            hit = "support_line"
            log.append(f"ref {e['ref']}: no rule hit -> support_line")
        picks[e["ref"]] = hit
    return {"roles": picks, "fallback_log": log}
