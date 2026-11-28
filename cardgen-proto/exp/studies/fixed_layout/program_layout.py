"""共同黄金输入的固定树程序布局，支持无上游树的路由和任一合法冻结树的独立几何。"""

import math
from collections import Counter
from functools import lru_cache

from runtime import allocation
from runtime import program as stages

GAPS = (8, 6, 4, 2)
# 四原语开发实验借用数据展示文本主值、辅助正文及单行标题规格。
RECIPES = {
    "title": (12, 400, 1.0, 1),
    "primary": (21, 700, 1.25, 2),
    "identity": (14, 400, 1.35, None),
    "secondary": (14, 400, 1.35, None),
    "context": (14, 400, 1.35, None),
    "action": (14, 500, 1.35, 1),
}


def group(kind, children, force=False):
    if len(children) == 1 and not force:
        return children[0]
    return {"kind": kind, "children": children}


def leaf(u):
    return {"kind": u["kind"], "ref": u["id"]}


def program_route(shared):
    units = shared["units"]
    headers = [leaf(u) for u in units if u["role"] == "title"]
    buttons = [leaf(u) for u in units if u["kind"] == "button"]
    by_entity = {
        e["id"]: [u for u in units if u["entity"] == e["id"] and u["kind"] == "text"]
        for e in shared["entities"]
    }
    by_entity = {k: v for k, v in by_entity.items() if v}
    order = list(by_entity)
    ordered = [(r["from"], r["to"]) for r in shared["relations"] if r["type"] == "ordered"]
    # 稳定拓扑排序，仅使用实体顺序和冻结有向关系。
    while any(order.index(a) > order.index(b) for a, b in ordered):
        pending = order.copy()
        order = []
        while pending:
            next_key = next(
                (x for x in pending if not any(b == x and a in pending for a, b in ordered)), None
            )
            if next_key is None:
                raise ValueError("冻结实体顺序成环")
            pending.remove(next_key)
            order.append(next_key)
    records = {a["owners"][0] for a in shared["actions"] if a["interaction"] == "record_click"}
    paired = {frozenset((r["from"], r["to"])) for r in shared["relations"] if r["type"] == "peer"}
    blocks = {}
    width = shared["canvas"]["width"] - 24

    def one_line(u):
        size, weight, *_ = RECIPES[u["role"]]
        return stages._natural_width(u["sample_text"], size, weight)

    for entity, items in by_entity.items():
        if entity in records:
            blocks[entity] = group("row", [leaf(u) for u in items], force=True)
            continue
        rows = []
        i = 0
        while i < len(items):
            a = items[i]
            b = items[i + 1] if i + 1 < len(items) else None
            # 明确的数值标签与读数优先同行；其余同实体短主辅可在同一行完整阅读。
            pair = b is not None and (
                a.get("for_unit") == b["id"]
                or (
                    a["role"] in {"primary", "secondary"}
                    and b["role"] == "secondary"
                    and one_line(a) + one_line(b) + 8 <= width
                )
            )
            if pair:
                rows.append(group("row", [leaf(a), leaf(b)]))
                i += 2
            else:
                rows.append(leaf(a))
                i += 1
        blocks[entity] = group("column", rows)
    i = 0
    body = []
    while i < len(order):
        a = order[i]
        b = order[i + 1] if i + 1 < len(order) else None
        if b and shared["canvas"]["width"] >= 280 and frozenset((a, b)) in paired:
            body.append(group("row", [blocks[a], blocks[b]]))
            i += 2
        else:
            body.append(blocks[a])
            i += 1
    nodes = headers + body
    if buttons:
        nodes.append(group("row", buttons))
    tree = {"root": group("column", nodes, force=True)}
    validate_tree(tree, shared)
    return tree


def validate_tree(structure, shared):
    units = {u["id"]: u for u in shared["units"]}
    flat = []
    spans = []

    def walk(node):
        kind = node["kind"]
        if kind in {"text", "button"}:
            ref = node["ref"]
            if set(node) != {"kind", "ref"} or ref not in units or units[ref]["kind"] != kind:
                raise ValueError("可见叶格式或引用错误")
            flat.append(ref)
            return {ref}
        if (
            kind not in {"column", "row"}
            or set(node) != {"kind", "children"}
            or not node["children"]
        ):
            raise ValueError("未知容器或空组")
        members = set.union(*(walk(child) for child in node["children"]))
        spans.append(members)
        return members

    if set(structure) != {"root"} or structure["root"]["kind"] not in {"column", "row"}:
        raise ValueError("根必须是显式 Row 或 Column")
    walk(structure["root"])
    if Counter(flat) != Counter(units.keys()):
        raise ValueError("存在丢失或重复可见叶")
    for r in shared["relations"]:
        if r["type"] == "ordered":
            aa = [
                i
                for i, k in enumerate(flat)
                if units[k]["entity"] == r["from"] and units[k]["kind"] == "text"
            ]
            bb = [
                i
                for i, k in enumerate(flat)
                if units[k]["entity"] == r["to"] and units[k]["kind"] == "text"
            ]
            if not aa or not bb or max(aa) >= min(bb):
                raise ValueError("冻结实体顺序未满足")
    for a in shared["actions"]:
        if a["interaction"] == "record_click":
            owned = {
                k for k, u in units.items() if u["entity"] in a["owners"] and u["kind"] == "text"
            }
            if not owned or owned not in spans:
                raise ValueError("记录动作缺少独占实体子树")
    if any(
        u.get("for_unit") and flat.index(u["id"]) >= flat.index(u["for_unit"])
        for u in units.values()
    ):
        raise ValueError("显式读数标签必须在相应读数之前")


def program_geometry(structure, shared):
    validate_tree(structure, shared)
    units = {u["id"]: u for u in shared["units"]}
    canvas = shared["canvas"]
    width, height = stages._canvas(shared["size"])
    if (width, height) != (canvas["width"], canvas["height"]):
        raise ValueError("输入尺寸与冻结画布不一致")
    nodes = {}

    def index(node, key):
        nodes[key] = node
        for i, child in enumerate(node.get("children", [])):
            index(child, (*key, i))

    index(structure["root"], ())
    measure = stages._measure()

    def signature(node):
        if "ref" in node:
            return node["kind"], units[node["ref"]]["role"]
        return node["kind"], tuple(signature(c) for c in node["children"])

    @lru_cache
    def solve(key, w, gap):
        n = nodes[key]
        pad = 0 if key else 12
        available = w - 2 * pad
        base = {"width": w}
        if not key:
            base.update(padding=12, clip=True, borderRadius=20)
        if "ref" in n:
            unit = units[n["ref"]]
            button = n["kind"] == "button"
            size, weight, lh, maximum = RECIPES[unit["role"]]
            try:
                metric = measure.text(
                    unit["sample_text"],
                    available - (24 if button else 0),
                    size,
                    max_lines=maximum or max(1, len(unit["sample_text"]) + 1),
                    bold=weight >= 600,
                    line_height=lh,
                )
            except ValueError:
                return None
            if button and metric.height > 36:
                return None
            base.update(
                fontSize=size,
                fontWeight=weight,
                lineHeight=lh,
                maxLines=metric.lines,
                textAlign="center" if button else "start",
                height=36 if button else metric.height,
            )
            if button:
                base["borderRadius"] = 18
            return {**n, "style": base}
        row = n["kind"] == "row"
        kids = n["children"]
        total = available - gap * (len(kids) - 1)
        if row and total <= 0:
            return None
        options = [((total / len(kids) if row else available),) * len(kids)]
        if (
            row
            and len(kids) == 2
            and signature(kids[0]) != signature(kids[1])
            and math.isclose(total * 4, round(total * 4), abs_tol=0.000001)
        ):
            options.extend(allocation.pair_allocations(available, gap))
        best = None
        for split in options:
            children = [solve((*key, i), share, gap) for i, share in enumerate(split)]
            if any(c is None for c in children):
                continue
            heights = [c["style"]["height"] for c in children]
            natural = (max(heights) if row else sum(heights) + gap * (len(heights) - 1)) + 2 * pad
            if best is None or natural < best[0]:
                best = natural, children
        if best is None:
            return None
        base.update(height=best[0], itemMargin=gap, alignItems="start", justifyContent="start")
        return {"kind": n["kind"], "children": best[1], "style": base}

    attempts = {}
    for gap in GAPS:
        root = solve((), width, gap)
        natural = None if root is None else root["style"]["height"]
        attempts[gap] = natural
        if natural is not None and natural <= height:
            root["style"]["height"] = height
            return {"root": root}
    raise stages.StageError(
        "reference_capacity", f"固定树、角色字号和已登记份额下，需高vp {attempts}，画布{height}vp"
    )
