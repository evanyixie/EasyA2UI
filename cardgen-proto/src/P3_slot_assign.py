"""P3 region 装配：把对象/条目/动作填进骨架 tree 的槽位。

管"放哪个 region、放几个"，不管"每条多少字"（文字容量是 P4/P5 的职责）。
fills 结构：{slot_id: {"info": [refs], "action": [refs]}}；zone 槽的动作
不作为子组件，而是由 P6 绑定为该背板容器的 onClick（S4/W8/W10 语义）。
"""


# 标题兜底：M1 常漏抽 title（q11/q47），而"右上角有图标"的卡片必须有标题（用户 2026-10-19 明示）。
# 名字优先取第一个业务对象名，其次按业务域给中性名。
TITLE_BY_DOMAIN = {"weather": "天气", "battery": "电量", "earphone": "耳机",
                   "calendar": "日程", "meeting": "会议", "countdown": "倒计时",
                   "healthSport": "健康", "notice": "提醒", "promotion": "优惠"}


def _ensure_title(plan: dict, fills: dict) -> None:
    """没有标题区就不用补；有标题区但 M1 没抽 title 时补一个（原地改 plan["entries"]）。

    注意：必须在**骨架路由之后**执行——补标题会改变"信息条数"，
    若在路由前补，2 条内容的卡会变 3 条而被改判成 S5（环卡因此丢掉环）。
    """
    if "header" not in fills:
        return
    entries = plan["entries"]
    if any(e["type"] == "title" for e in entries):
        return
    name = ""
    for o in plan.get("objects") or []:
        name = (o.get("name_hint") or "").strip()
        if name:
            break
    name = name or TITLE_BY_DOMAIN.get(plan.get("domain", ""), "卡片")
    entries.insert(0, {"ref": max((e["ref"] for e in entries), default=0) + 1,
                       "kind": "info", "type": "title", "hint": name[:8], "keep": "must"})


def _collect_slots(node, acc):
    slot = node.get("slot")
    if slot:
        acc.append(slot)
    for ch in node.get("children", []) or []:
        _collect_slots(ch, acc)
    return acc


def _is_action_slot(slot):
    return slot == "action" or slot.startswith("action_zone")


def _hero_ref(entries):
    for e in entries:
        if e["kind"] == "info" and e["type"] in ("discount", "price", "stat") and len(e["hint"]) <= 8:
            return e["ref"]
    return None


def assign_regions(plan: dict, skel: dict) -> dict:
    log = plan["fallback_log"]
    slots = _collect_slots(skel["tree"], [])
    fills = {s: {"info": [], "action": []} for s in slots}

    _ensure_title(plan, fills)          # 标题显示兜底（必须在路由之后）
    entries = plan["entries"]
    by_ref = {e["ref"]: e for e in entries}
    infos = [e["ref"] for e in entries if e["kind"] == "info"]
    actions = [e["ref"] for e in entries if e["kind"] == "action"]
    title_ref = next((r for r in infos if by_ref[r]["type"] == "title"), None)
    hero = _hero_ref(entries)
    objects = plan["objects"]

    used_info, used_act = set(), set()

    def take_info(slot, refs, cap):
        placed = 0
        for r in refs:
            if placed >= cap or r in used_info:
                continue
            fills[slot]["info"].append(r)
            used_info.add(r)
            placed += 1
        overflow = [r for r in refs if r not in used_info]
        return overflow

    zone_slots = sorted(s for s in slots if s.startswith("zone:"))
    aux_slots = sorted(s for s in slots if s.startswith("aux:"))
    az_slots = sorted(s for s in slots if s.startswith("action_zone:"))

    # --- 多对象骨架：对象 → zone ---
    if zone_slots:
        for i, slot in enumerate(zone_slots):
            if i < len(objects):
                fields = [r for r in objects[i]["fields"] if by_ref[r]["kind"] == "info"]
                if len(fields) > 3:
                    dropped = fields[3:]
                    log.append(f"{slot}: {len(dropped)} fields beyond 3 dropped")
                    fields = fields[:3]
                take_info(slot, fields, 3)
        # 动作 → 所属业务背板（绑定容器 onClick，非子组件；每板恰好 1 个 handler）
        # 匹配优先级：字段绑定 > 文案与业务名互相包含 > 文案与字段提示互相包含 > 顺序填空板
        def _score(a_ref, obj):
            a = by_ref[a_ref]
            ah = str(a.get("hint", "")).strip()
            if a.get("bind_to") in set(obj["fields"]):
                return 3
            name = str(obj.get("name_hint", "")).strip()
            if ah and name and (ah in name or name in ah):
                return 2
            for r in obj["fields"]:
                fh = str(by_ref[r].get("hint", "")).strip() if r in by_ref else ""
                if ah and fh and (ah in fh or fh in ah):
                    return 1
            return 0

        for a in actions:
            if a in used_act:
                continue
            best, best_slot = 0, None
            for i, slot in enumerate(zone_slots):
                if i >= len(objects) or fills[slot]["action"]:
                    continue
                sc = _score(a, objects[i])
                if sc > best:
                    best, best_slot = sc, slot
            if best_slot and best > 0:
                fills[best_slot]["action"].append(a)
                used_act.add(a)
        # 未匹配的动作：顺序填入仍为空的背板（保持旧的兜底语义，但不再集中到 zone:0）
        for a in actions:
            if a in used_act:
                continue
            empt = next((sl for sl in zone_slots if not fills[sl]["action"]), None)
            if empt:
                fills[empt]["action"].append(a)
                used_act.add(a)
    # --- 单对象骨架 ---
    else:
        # header：title 条目（可选槽位）
        if "header" in fills and title_ref is not None:
            fills["header"]["info"].append(title_ref)
            used_info.add(title_ref)
        # hero 槽（S1/W1/W3/W5 左焦点）
        # 规范：S1 不套 CardHeader，标题并入居中组（无 header 槽时标题先进 hero）
        if "hero" in fills and "header" not in fills and title_ref is not None:
            fills["hero"]["info"].append(title_ref)
            used_info.add(title_ref)
        if "hero" in fills:
            if hero is not None and hero not in used_info:
                fills["hero"]["info"].append(hero)
                used_info.add(hero)
            else:
                first = next((r for r in infos if r not in used_info), None)
                if first is not None:
                    fills["hero"]["info"].append(first)
                    used_info.add(first)
        # triple 槽（W4 三列 88/96/88 + 分隔线）：每列各 1 条
        triple_cols = sorted(sl for sl in slots if sl.startswith("triple:"))
        if triple_cols:
            cand = [r for r in infos if r not in used_info and r != title_ref]
            for ts in triple_cols:
                if cand:
                    take_info(ts, [cand.pop(0)], 1)
        elif "triple" in fills:  # 旧单槽兜底
            cand = [r for r in infos if r not in used_info and r != title_ref]
            take_info("triple", cand, 3)
        # aux 槽（W1/W5）
        for i, slot in enumerate(aux_slots):
            pool = infos if len(objects) <= 1 else objects[min(i + 1, len(objects) - 1)]["fields"]
            cand = [r for r in pool if r not in used_info and r != title_ref]
            take_info(slot, cand, 2)
        # S5/S6 主区（primary）：只放主值一条（数据 M1/M2 的主区均为单一主值）
        if "primary" in fills:
            pool = []
            if hero is not None and hero not in used_info:
                pool.append(hero)
            pool += [r for r in infos if r not in used_info and r != title_ref and r not in pool]
            take_info("primary", pool, 1)
        # S5 辅区（support）/ S6 底部辅信息（bottom_info）
        for slot, cap in (("support", 3), ("bottom_info", 2)):
            if slot in fills:
                cand = [r for r in infos if r not in used_info and r != title_ref]
                take_info(slot, cand, cap)
        # S6 圆形动作槽（每槽 1 个）
        if "bottom_action" in fills:
            a = next((x for x in actions if x not in used_act), None)
            if a is not None:
                fills["bottom_action"]["action"].append(a)
                used_act.add(a)
        # content / text_flow / list 槽
        for slot in ("content", "text_flow", "list"):
            if slot in fills:
                cap = 3 if slot != "content" else 3
                take_info(slot, [r for r in infos if r != title_ref], cap)
        # 独立 action 槽（S2 一个 / S3 两个）
        if "action" in fills:
            for a in actions:
                if len(fills["action"]["action"]) < 2 and a not in used_act:
                    fills["action"]["action"].append(a)
                    used_act.add(a)
        # W6 动作背板
        for slot in az_slots:
            if actions:
                a = next((x for x in actions if x not in used_act), None)
                if a is not None:
                    fills[slot]["action"].append(a)
                    used_act.add(a)

    # 覆盖率校验：未安置的条目记日志（信息按 keep 优先级丢弃）
    orphans = [r for r in infos if r not in used_info] + [a for a in actions if a not in used_act]
    for r in orphans:
        e = by_ref[r]
        if e.get("type") == "title" and "header" not in fills:
            # 该骨架没有标题区（S3 双动作、S4 上下双业务）：金标这几类卡本身就没有标题
            # （q44/q46/q48、q10/q34），标题"未显示"是骨架定义使然，不算丢字段
            continue
        if e.get("keep") == "must":
            # 必保条目超出槽位容量：金标同类卡也只保留前 N 条（如 q49 问 4 个值、金标同样
            # 只展示 3 行），故这是"降级"而非"缺陷"。措辞为降级日志，便于与真 bug 区分。
            log.append(f"ref {r} ({e['type']}) dropped: slot out of capacity (mustKeep)")
        else:
            log.append(f"ref {r} ({e['type']}) dropped (shouldKeep)")
    return {"fills": fills, "orphans": orphans}
