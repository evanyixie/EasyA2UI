"""用参考测量逐节点检查容器边界、文字行盒及按钮内距。"""

import json
import math

import expressions as fidelity
from runtime import program

EPS = 0.05
SUPPORTED = {"Column", "Row", "Text", "Button"}

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
        json.loads(line, object_pairs_hook=unique) for line in raw.decode("utf8").splitlines()
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
                set(n) <= {"id", "component", "styles", prop, "onClick"} and prop in n, "复杂叶子"
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
                set(n) <= {"id", "component", "styles", "children", "itemMargin", "onClick"}
                and n["children"]
                and finite(n.get("itemMargin", 0))
                and n.get("itemMargin", 0) >= 0
                and s.get("alignItems", "start") in ("start", "center", "end")
                and s.get("justifyContent", "start") in ("start", "center", "end", "spaceBetween"),
                "未知容器/对齐参数",
            )
    demand(
        nodes[root]["component"] in ("Row", "Column") and nodes[root]["styles"].get("clip") is True,
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
        needed = sum(nodes[k]["styles"][main] for k in children) + gap * (len(children) - 1)
        spare = s[main] - 2 * p - needed
        if spare < -EPS:
            violation(i, "container_" + main, -spare)
        justify = s.get("justifyContent", "start")
        remain = max(0, spare)
        offset = remain / 2 if justify == "center" else remain if justify == "end" else 0
        if justify == "spaceBetween" and len(children) > 1:
            gap += remain / (len(children) - 1)
        for child in children:
            st = nodes[child]["styles"]
            free = s[cross] - 2 * p - st[cross]
            if free < -EPS:
                violation(child, "exceeds_parent_" + cross, -free)
            if offset + st[main] > s[main] - 2 * p + EPS:
                violation(child, "exceeds_parent_" + main, offset + st[main] - (s[main] - 2 * p))
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


def geometry_gates(messages, shared):
    # 只测卡本体的行盒与容器边界，同时核固定按钮的两边各 12vp 内距。
    raw = ("\n".join(json.dumps(m, ensure_ascii=False) for m in messages) + "\n").encode()
    parsed = parse(raw)
    issues, _, _ = inspect(parsed)
    found = issue_list(issues)
    unit = {u["id"]: u for u in shared["units"]}
    for c in parsed[1]["updateComponents"]["components"]:
        if c["component"] != "Button":
            continue
        u = unit[c["id"]]
        s = c["styles"]
        try:
            m = program._measure().text(
                u["sample_text"],
                s["width"] - 24,
                s["fontSize"],
                max_lines=1,
                bold=s["fontWeight"] >= 600,
                line_height=s["lineHeight"],
            )
            if m.height > s["height"]:
                found.append({"id": c["id"], "code": "button_label_height"})
        except ValueError:
            found.append({"id": c["id"], "code": "button_label_width_12vp_insets"})
    return found
