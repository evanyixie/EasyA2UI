"""统一出口的保真修复。每次调用只读原始三消息，无请求、语义计划或答案输入。"""

import copy
import json
import math

import emit_fidelity as fidelity
from harness_v2 import program_stages as program


def dependency_files():
    """沿用六档参考测量、字体和与测量模块同目录的宽度分配实现。"""
    files = program.measurement_files()
    allocation = files["measure.py"].with_name("space_allocation.py")
    if not allocation.is_file():
        raise RuntimeError("共同几何修复需要 measure.py 同目录下的 space_allocation.py")
    return {**files, "space_allocation.py": allocation}


MAX_ROUNDS = 2
EPS = 0.05
SUPPORTED = {"Column", "Row", "Text", "Button"}
ADJUSTABLE = {"width", "height", "maxLines"}
STYLE = {
    "width",
    "height",
    "fontSize",
    "fontWeight",
    "lineHeight",
    "maxLines",
    "textAlign",
    "alignItems",
    "justifyContent",
    "padding",
    "borderRadius",
    "clip",
    "fontColor",
    "backgroundColor",
    "linearGradient",
}


class Unsupported(ValueError):
    pass


def demand(check, issue):
    if not check:
        raise Unsupported(issue)


def finite(v):
    return type(v) in (float, int) and math.isfinite(v)


def unique(pairs):
    result = {}
    for key, v in pairs:
        demand(key not in result, "存在重复 JSON 键")
        result[key] = v
    return result


def parse(raw):
    messages = [
        json.loads(line, object_pairs_hook=unique)
        for line in raw.decode("utf8").splitlines()
    ]
    names = ("createSurface", "updateComponents", "updateDataModel")
    demand(
        len(messages) == 3
        and all(
            isinstance(m, dict)
            and set(m) == {"version", k}
            and m["version"] == "v0.9"
            and isinstance(m[k], dict)
            for m, k in zip(messages, names, strict=True)
        ),
        "消息封装不支持",
    )
    a, b, c = [m[k] for m, k in zip(messages, names, strict=True)]
    demand(
        a["surfaceId"] == b["surfaceId"] == c["surfaceId"] and c["path"] == "/",
        "表面或数据路径不支持",
    )
    demand(a["catalogId"] == "ohos.a2ui.extended.catalog.form", "未证实的渲染器目录")
    fidelity.graph(b)
    root = b.get("root", "root")
    nodes = {n["id"]: n for n in b["components"]}
    for n in nodes.values():
        kind, s = n["component"], n["styles"]
        demand(
            kind in SUPPORTED
            and set(s) <= STYLE
            and all(finite(s[k]) and s[k] > 0 for k in ("width", "height")),
            "非四原语或未支持的几何",
        )
        demand(finite(s.get("padding", 0)) and s.get("padding", 0) >= 0, "非标量留白")
        if kind in ("Text", "Button"):
            prop = "content" if kind == "Text" else "label"
            demand(
                set(n) <= {"id", "component", "styles", prop, "onClick"} and prop in n,
                "复杂叶子",
            )
            demand(
                finite(s["fontSize"])
                and s["fontSize"] > 0
                and type(s["maxLines"]) is int
                and s["maxLines"] > 0
                and finite(s.get("lineHeight", 1.35))
                and 1 <= s.get("lineHeight", 1.35) <= 2
                and s.get("fontWeight", 400) in (400, 500, 700),
                "文字规格不可判定",
            )
        else:
            demand(
                set(n)
                <= {"id", "component", "styles", "children", "itemMargin", "onClick"}
                and n["children"]
                and finite(n.get("itemMargin", 0))
                and n.get("itemMargin", 0) >= 0
                and s.get("alignItems", "start") in ("start", "center", "end")
                and s.get("justifyContent", "start")
                in ("start", "center", "end", "spaceBetween"),
                "未知容器/对齐参数",
            )
    demand(
        nodes[root]["component"] in ("Row", "Column")
        and nodes[root]["styles"].get("clip") is True,
        "固定画布根不可判定",
    )
    return messages


def render_text(n, data):
    val = n["content"] if n["component"] == "Text" else n["label"]
    seq = fidelity.tokens(val)
    demand(seq is not fidelity.UNKNOWN, "本解释器未覆盖的表达式")
    parts = []
    for kind, token in seq:
        if kind == "text":
            parts.append(token)
        else:
            try:
                parts.append(program._sample(data, token))
            except program.StageError as exc:
                raise Unsupported("首帧无法解引用 " + token) from exc
    return "".join(parts)


def inspect(messages):
    update = messages[1]["updateComponents"]
    nodes = {n["id"]: n for n in update["components"]}
    root = update.get("root", "root")
    data = messages[2]["updateDataModel"]["value"]
    oracle = program._measure()
    issues, rects, metrics = {}, {}, {}

    def violation(i, code, amount):
        issues[(i, code)] = round(max(0, amount), 4)

    def walk(i, x, y):
        n = nodes[i]
        s = n["styles"]
        w, h, p = s["width"], s["height"], s.get("padding", 0)
        rects[i] = (x, y, w, h)
        if n["component"] in ("Text", "Button"):
            text = render_text(n, data)
            try:
                result = oracle.text(
                    text,
                    w - 2 * p,
                    s["fontSize"],
                    max_lines=max(1, len(text) + 1),
                    bold=s.get("fontWeight", 400) >= 600,
                    line_height=s.get("lineHeight", 1.35),
                )
                metrics[i] = (result.lines, result.height + 2 * p)
                if result.lines > s["maxLines"]:
                    violation(i, "lines", result.lines - s["maxLines"])
                if result.height + 2 * p > h + EPS:
                    violation(i, "text_height", result.height + 2 * p - h)
            except ValueError:
                metrics[i] = None
                violation(i, "glyph_width", 1)
            return
        children = n["children"]
        row = n["component"] == "Row"
        main, cross = ("width", "height") if row else ("height", "width")
        gap = n.get("itemMargin", 0)
        needed = sum(nodes[k]["styles"][main] for k in children) + gap * (
            len(children) - 1
        )
        spare = s[main] - 2 * p - needed
        if spare < -EPS:
            violation(i, "container_" + main, -spare)
        justify = s.get("justifyContent", "start")
        remain = max(0, spare)
        offset = (
            remain / 2 if justify == "center" else remain if justify == "end" else 0
        )
        if justify == "spaceBetween" and len(children) > 1:
            gap += remain / (len(children) - 1)
        for child in children:
            st = nodes[child]["styles"]
            free = s[cross] - 2 * p - st[cross]
            if free < -EPS:
                violation(child, "exceeds_parent_" + cross, -free)
            if offset + st[main] > s[main] - 2 * p + EPS:
                violation(
                    child,
                    "exceeds_parent_" + main,
                    offset + st[main] - (s[main] - 2 * p),
                )
            align = s.get("alignItems", "start")
            cross_off = free / 2 if align == "center" else free if align == "end" else 0
            cx, cy = (offset, cross_off) if row else (cross_off, offset)
            walk(child, x + p + cx, y + p + cy)
            offset += st[main] + gap

    walk(root, 0, 0)
    return issues, rects, metrics


def issue_list(violations):
    return [
        {"id": i, "code": code, "excess": amount}
        for (i, code), amount in sorted(violations.items())
    ]


def material(messages):
    """所有非几何内容逐字段比较；根节点的画布/壳以及字号等受保护。"""
    frozen = copy.deepcopy(messages)
    packet = frozen[1]["updateComponents"]
    for n in packet["components"]:
        if n["component"] in ("Row", "Column"):
            n.pop("itemMargin", None)
        if n["id"] != packet.get("root", "root"):
            for key in ADJUSTABLE:
                n["styles"].pop(key, None)
    return json.dumps(
        frozen,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def propose(original, initial, rounds):
    messages = copy.deepcopy(original)
    packet = messages[1]["updateComponents"]
    nodes = {n["id"]: n for n in packet["components"]}
    data = messages[2]["updateDataModel"]["value"]
    root = packet.get("root", "root")
    bad = {i for i, _ in initial}
    oracle = program._measure()
    actions = []

    def change(i, key, new):
        s = nodes[i]["styles"]
        if i == root or i not in bad or abs(s[key] - new) <= EPS:
            return
        actions.append(
            {
                "id": i,
                "key": key,
                "old": s[key],
                "new": new,
                "reason_codes": sorted(code for who, code in initial if who == i),
            }
        )
        s[key] = new

    def need(i, w):
        n, s = nodes[i], nodes[i]["styles"]
        text = render_text(n, data)
        try:
            m = oracle.text(
                text,
                w - 2 * s.get("padding", 0),
                s["fontSize"],
                max_lines=max(1, len(text) + 1),
                bold=s.get("fontWeight", 400) >= 600,
                line_height=s.get("lineHeight", 1.35),
            )
        except ValueError:
            return None
        return m.lines, m.height + 2 * s.get("padding", 0)

    def walk(i):
        n, s = nodes[i], nodes[i]["styles"]
        w, h, p = s["width"], s["height"], s.get("padding", 0)
        if n["component"] in ("Text", "Button"):
            m = need(i, w)
            if m:
                if m[0] > s["maxLines"] and n["component"] == "Text":
                    change(i, "maxLines", m[0])
                if m[1] > h + EPS:
                    change(i, "height", m[1])
            return
        children = n["children"]
        gap = n.get("itemMargin", 0)
        if rounds == 2:
            inner = w - 2 * p
            if n["component"] == "Column":
                for child in children:
                    if (
                        (child, "lines") in initial
                        or (child, "glyph_width") in initial
                        or (child, "exceeds_parent_width") in initial
                    ):
                        change(child, "width", inner)
            elif len(children) == 2 and all(
                nodes[c]["component"] in ("Text", "Button") for c in children
            ):
                first, second = children
                old = tuple(nodes[c]["styles"]["width"] for c in children)
                available = inner - gap
                if (
                    available > 10
                    and abs(available * 4 - round(available * 4)) < 0.000001
                ):
                    allocation = program._module(
                        "repair_alloc", dependency_files()["space_allocation.py"]
                    )
                    widths = [
                        old,
                        *allocation.pair_allocations(inner, gap),
                        (old[0], available - old[0]),
                        (available - old[1], old[1]),
                    ]
                    choices = []
                    for wa, wb in widths:
                        if min(wa, wb) <= 4 or wa + wb > available + EPS:
                            continue
                        if (first not in bad and wa != old[0]) or (
                            second not in bad and wb != old[1]
                        ):
                            continue
                        fit = [
                            need(c, amount)
                            for c, amount in zip(children, (wa, wb), strict=True)
                        ]
                        if all(v is not None for v in fit):
                            choices.append(
                                (
                                    max(v[1] for v in fit),
                                    sum(v[0] for v in fit),
                                    abs(wa - old[0]) + abs(wb - old[1]),
                                    wa,
                                    wb,
                                )
                            )
                    if choices:
                        *_, wa, wb = min(choices)
                        change(first, "width", wa)
                        change(second, "width", wb)
        for child in children:
            walk(child)
        heights = [nodes[c]["styles"]["height"] for c in children]
        minimum = (
            max(heights)
            if n["component"] == "Row"
            else sum(heights) + gap * (len(children) - 1)
        ) + 2 * p
        if minimum > h + EPS:
            change(i, "height", minimum)

    walk(root)
    return messages, actions


def balance_gaps(trial, original_rects, protected, actions):
    """只调已有同级间距。在每个试值上核对真实参考文本约束与完好矩形位置。"""
    packet = trial[1]["updateComponents"]
    nodes = {n["id"]: n for n in packet["components"]}
    containers = [
        n
        for n in nodes.values()
        if n["component"] in ("Row", "Column")
        and "itemMargin" in n
        and len(n["children"]) > 1
    ]

    def score():
        defects, rects, _ = inspect(trial)
        distances = [
            max(abs(a - b) for a, b in zip(original_rects[i], rects[i], strict=True))
            for i in protected
        ]
        return (
            len(defects) + sum(d > EPS for d in distances),
            round(sum(defects.values()) + sum(distances), 4),
        ), rects

    for node in containers:
        old = node["itemMargin"]
        minimum = min(old, 2)
        if minimum >= old - EPS:
            continue
        current, start = score()
        node["itemMargin"] = minimum
        _, end = score()
        values = {minimum, old, *[g for g in (2, 4, 6, 8, 12) if minimum <= g <= old]}
        axis = "width" if node["component"] == "Row" else "height"
        children = node["children"]
        budget = (
            node["styles"][axis]
            - 2 * node["styles"].get("padding", 0)
            - sum(nodes[c]["styles"][axis] for c in children)
        )
        values.add(budget / (len(children) - 1))
        # 保持原有效矩形的坐标，比只以减少溢出个数选择间距更严格。
        for i in protected:
            for k in (0, 1):
                slope = (end[i][k] - start[i][k]) / (minimum - old)
                if abs(slope) > 1e-8:
                    values.add(old + (original_rects[i][k] - start[i][k]) / slope)
        best = (current, 0, old)
        for value in sorted({round(g, 4) for g in values if minimum <= g <= old}):
            node["itemMargin"] = value
            trial_score, _ = score()
            best = min(best, (trial_score, abs(old - value), value))
        node["itemMargin"] = old
        if abs(best[2] - old) > EPS:
            node["itemMargin"] = best[2]
            actions.append(
                {
                    "id": node["id"],
                    "key": "itemMargin",
                    "old": old,
                    "new": best[2],
                    "reason_codes": ["retain_valid_rectangles_and_fit_full_content"],
                }
            )


def repair(raw):
    try:
        original = parse(raw)
        before, positions, _ = inspect(original)
        frozen = material(original)
    except (KeyError, ValueError, TypeError, RecursionError) as exc:
        return raw, {
            "status": "unsupported",
            "why": str(exc),
            "before": None,
            "after": None,
            "rounds": [],
        }
    bad = {i for i, _ in before}
    clean = set(positions) - bad
    log = {
        "status": "no_change" if not before else "unresolved",
        "before": issue_list(before),
        "after": issue_list(before),
        "protected_valid_boxes": sorted(clean),
        "maximum_rounds": MAX_ROUNDS,
        "rounds": [],
    }
    if not before:
        return raw, log
    for round_no in range(1, MAX_ROUNDS + 1):
        trial, actions = propose(original, before, round_no)
        if round_no == 2:
            balance_gaps(trial, positions, clean, actions)
        trial_issues, coords, _ = inspect(trial)
        introduced = {k: v for k, v in trial_issues.items() if k not in before}
        worsened = {
            k: v for k, v in trial_issues.items() if k in before and v > before[k] + EPS
        }
        shifted = [
            i
            for i in sorted(clean)
            if any(
                abs(a - b) > EPS for a, b in zip(positions[i], coords[i], strict=True)
            )
        ]
        intact = material(trial) == frozen
        permitted = bool(actions and not trial_issues and not shifted and intact)
        log["rounds"].append(
            {
                "round": round_no,
                "from": "original",
                "actions": actions,
                "candidate_violations": issue_list(trial_issues),
                "introduced_by_repair": issue_list(introduced),
                "worsened": issue_list(worsened),
                "moved_previously_valid_boxes": shifted,
                "protected_semantics_equal": intact,
                "accepted": permitted,
            }
        )
        if permitted:
            encoded = (
                "\n".join(
                    json.dumps(m, ensure_ascii=False, allow_nan=False) for m in trial
                )
                + "\n"
            ).encode("utf8")
            confirmed = parse(encoded)
            final, _, _ = inspect(confirmed)
            demand(not final and material(confirmed) == frozen, "序列化后核验失败")
            log.update(status="repaired", after=[], accepted_round=round_no)
            return encoded, log
    return raw, log
