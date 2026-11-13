"""P1 归一化：枚举对齐 / 同义词映射 / ref 重排 / 入关截断 / 悬空边清洗 / fallback_log。

模型输出进入程序世界前的唯一"海关"：下游模块面对的都是 ref 连续、
枚举合法、引用闭合的干净数据，不需要任何防御性代码。

v2 扩展（2026-10-10 对齐 CreateMyCard）：domain / size / theme / objects / keep
五个新字段的归一化——domain 是主题映射与骨架路由的辅助键；objects 是
业务对象分组（骨架路由第一判据）；keep 是字段取舍标记（must/should）。
"""
import json
from pathlib import Path

from .pipeline_options import PipelineOptions

ROOT = Path(__file__).resolve().parent.parent
ENUMS = json.loads((ROOT / "rules/enums.json").read_text(encoding="utf-8"))
SYN = ENUMS["synonyms"]

# 「占满分比」类字段名：模型常把电量/完成度写成 stat，P1 按字段名确定性地纠正为 percent。
# （不依赖模型稳定性；命中后才可能走环形主值形态，见 compiler._ring_row）
PERCENT_KW = ("电量", "百分比", "完成度", "使用率", "占比", "进度", "充满", "剩余电")


def _norm_enum(value, valid, fallback, label, log):
    """枚举内 → 直接放行；同义词表 → 映射；否则回退并记录。"""
    if value in valid:
        return value, None
    if value in SYN and SYN[value] in valid:
        return SYN[value], f"synonym:{value}->{SYN[value]}"
    return fallback, f"{label} fallback: {value} -> {fallback}"


def _norm_type(value, valid):
    """枚举内 → 直接放行；同义词表 → 映射；否则丢弃。"""
    if value in valid:
        return value, None
    if value in SYN and SYN[value] in valid:
        return SYN[value], f"synonym:{value}->{SYN[value]}"
    return None, f"invalid:{value}"


def normalize_plan(plan: dict, options: PipelineOptions = None) -> dict:
    """归一化。

    options.repair_plan=False 时只做“解析性”处理（枚举对齐、ref 重排、去非法类型），
    不做任何“改内容集合”的修正——去重、stat→percent、悬空关系清洗、未归属字段并入。
    这四种修正是可关的（实验里的“无补救”组），因为它们会抹掉模型原始输出的缺陷。
    """
    options = options or PipelineOptions()
    log = []

    domain, why = _norm_enum(plan.get("domain", plan.get("intent")),
                             ENUMS["domain"], "unknown", "domain", log)
    if why:
        log.append(why)
    # intent：M1 显式给出优先；未给出时由 domain 派生（promotion/notice 等）
    intent = plan.get("intent")
    if intent not in ENUMS["intent"]:
        intent = domain if domain in ENUMS["intent"] else "info_card"
    size = plan.get("size", "auto")
    if size not in ENUMS["size"]:
        log.append(f"size fallback: {size} -> auto")
        size = "auto"
    theme = plan.get("theme")
    if theme is not None and theme not in ENUMS["theme"]:
        log.append(f"theme dropped (invalid: {theme})")
        theme = None

    entries, ref_map = [], {}
    for src, kind, valid, hint_key, cap in (
            (plan.get("info_items", []), "info", ENUMS["info_type"], "content_hint", 30),
            (plan.get("actions", []), "action", ENUMS["action_type"], "label_hint", 10)):
        for e in src:
            t, why = _norm_type(e.get("type"), valid)
            if not t:
                log.append(f"{kind} dropped ({why})")
                continue
            old = e.get("ref")
            new = len(entries) + 1
            if old is not None:
                ref_map[old] = new
            keep = e.get("keep", "must")
            entries.append({"ref": new, "kind": kind, "type": t,
                            "hint": str(e.get(hint_key, ""))[:cap],
                            "keep": keep if keep in ENUMS["keep"] else "must"})

    # 去重：同一入口既被声明为 info 又被声明为 action 时，保留动作（入口），丢弃重复 info。
    # 依据：动作是"入口"语义的更强表达；重复保留会让同一事实在卡面出现两次。
    # ⚠️ 这是"改内容集合"的修正，受 options.repair_plan 控制（关闭后重复条目原样留下，
    #    让模型的分组错误在产物里可见，而不是被程序抹平）。
    if options.repair_plan:
        def _key(t: str) -> str:
            return "".join(ch for ch in str(t) if ch.strip())

        act_keys = {_key(e["hint"]) for e in entries if e["kind"] == "action" and _key(e["hint"])}
        if act_keys:
            dropped_refs, kept = set(), []
            for e in entries:
                if e["kind"] == "info" and _key(e["hint"]) in act_keys:
                    dropped_refs.add(e["ref"])
                    log.append(f"info ref {e['ref']} duplicates action hint -> dropped (keep action)")
                    continue
                kept.append(e)
            if dropped_refs:
                entries = kept
                ref_map = {o: n for o, n in ref_map.items() if n not in dropped_refs}

    # 百分比语义纠正：hint/标签里出现"电量/百分比/完成度…"且模型给了 stat → percent
    # ⚠️ 改类型，属可关修正。
    if options.repair_plan:
        for e in entries:
            if e.get("kind") == "info" and e.get("type") == "stat":
                hint = str(e.get("hint") or "")
                if any(kw in hint for kw in PERCENT_KW):
                    e["type"] = "percent"

    # ⚠️ 悬空关系清洗同样"删数据"，可关。关闭时原样透传，交给下游/评测去看。
    if options.repair_plan:
        relations = [{"from": ref_map[r["from"]], "to": ref_map[r["to"]], "type": r["type"]}
                     for r in plan.get("relations", [])
                     if r.get("from") in ref_map and r.get("to") in ref_map
                     and r.get("type") in ENUMS["relation_type"]]
        dropped = len(plan.get("relations", [])) - len(relations)
        if dropped:
            log.append(f"{dropped} relation(s) dropped (dangling ref / bad type)")
    else:
        relations = list(plan.get("relations", []))

    # 业务对象分组：fields 引用重映射；空对象丢弃；未覆盖的 info ref 归入第一个对象
    objects = []
    for o in plan.get("objects", []):
        fields = sorted({ref_map[f] for f in o.get("fields", []) if f in ref_map})
        if not fields:
            continue
        objects.append({"name_hint": str(o.get("name_hint", ""))[:12], "fields": fields})
    info_refs = [e["ref"] for e in entries if e["kind"] == "info"]
    type_of = {e["ref"]: e["type"] for e in entries}
    covered = {f for o in objects for f in o["fields"]}
    missing = [r for r in info_refs if r not in covered]
    # 标题条目归属标题区（header），不是业务字段：无 header 槽的骨架（如 S4 上下双业务，
    # 金标 q10/q34 就没有标题）可以不显示它，因此不算丢字段、不进 fallback_log。
    titled = [r for r in missing if type_of[r] == "title"]
    missing = [r for r in missing if type_of[r] != "title"]
    # ⚠️ 这两处"并入首个对象"也是改内容集合（对象的分组会被补全），受 repair_plan 控制。
    if options.repair_plan:
        if objects and titled:
            objects[0]["fields"] = sorted(set(objects[0]["fields"]) | set(titled))
        if missing and objects:
            # 已有显式对象声明时，未覆盖字段并入第一个对象（记录）
            objects[0]["fields"] = sorted(set(objects[0]["fields"]) | set(missing))
            log.append(f"refs {missing} not in any object -> merged")
        elif missing:
            # 无显式对象声明：隐式单对象兜底（规范默认行为，不算 fallback）
            objects = [{"name_hint": "", "fields": sorted(missing)}]
    elif missing:
        log.append(f"refs {missing} not in any object (grouping repair disabled)")
    if not objects and not info_refs:
        objects = []

    # groups：P3 改用 objects/fills 装配后，groups 仅作语义参考保留，不再做覆盖兜底
    groups = [{"type": g["type"], "children": [ref_map[c] for c in g.get("children", []) if c in ref_map]}
              for g in plan.get("groups", []) if g.get("type") in ENUMS["group_type"]]

    return {"domain": domain, "intent": intent, "size": size, "theme": theme,
            "objects": objects, "entries": entries, "relations": relations,
            "groups": groups, "fallback_log": log}
