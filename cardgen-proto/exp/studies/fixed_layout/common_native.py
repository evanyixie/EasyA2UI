"""黄金内容实验的共同树合同、点击归属及原生发射。"""

from __future__ import annotations

import copy
import math
from collections import Counter

from runtime import data_model

GAPS = (2, 4, 6, 8)
LEAVES = {"text", "button"}


class ContractError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise ContractError(reason)


def font(unit):
    if unit["kind"] == "button":
        return 14, 500, 1.35, 1
    if unit["role"] == "title":
        return 12, 400, 1.0, 1
    if unit["role"] == "primary":
        return 21, 700, 1.25, 2
    return 14, 400, 1.35, 32


def walk(node, path="0"):
    yield path, node
    for i, child in enumerate(node.get("children", [])):
        yield from walk(child, path + "." + str(i))


def roles_and_clicks(tree, shared, styled=False):
    require(isinstance(tree, dict) and set(tree) == {"root"}, "树根合同不符")
    units = {u["id"]: u for u in shared["units"]}
    indexed = {}
    refs = []
    leaves_of = {}
    style_keys = {"style"} if styled else set()

    def visit(node, loc, depth):
        require(depth < 30 and isinstance(node, dict), "无效树节点或嵌套过深")
        kind = node.get("kind")
        indexed[loc] = node
        if kind in LEAVES:
            require(set(node) == {"kind", "ref"} | style_keys, "叶节点字段不正确")
            ref = node["ref"]
            require(
                isinstance(ref, str) and ref in units and units[ref]["kind"] == kind,
                "未知叶或叶类型错误",
            )
            refs.append(ref)
            leaves = {ref}
        else:
            require(
                kind in ("row", "column") and set(node) == {"kind", "children"} | style_keys,
                "容器字段不正确",
            )
            require(
                isinstance(node["children"], list) and bool(node["children"]),
                "容器为空",
            )
            leaves = set()
            for i, child in enumerate(node["children"]):
                leaves.update(visit(child, f"{loc}.{i}", depth + 1))
        leaves_of[loc] = leaves
        return leaves

    visit(tree["root"], "0", 0)
    require(tree["root"]["kind"] in ("row", "column"), "根必须是容器")
    require(Counter(refs) == Counter(list(units)), "有叶遗漏或重复")
    positions = {ref: i for i, ref in enumerate(refs)}
    for relation in shared["relations"]:
        if relation["type"] == "ordered":
            first, second = (
                [positions[k] for k, u in units.items() if u["entity"] == entity]
                for entity in (relation["from"], relation["to"])
            )
            require(first and second and max(first) < min(second), "记录阅读顺序颠倒或交错")
    clicks = {}
    for action in shared["actions"]:
        shape = action["interaction"]
        if shape == "whole_card":
            loc = "0"
        elif shape == "independent_entry":
            matches = [
                p
                for p, n in indexed.items()
                if n["kind"] == "button"
                and units[n["ref"]].get("action_ref") == action["action_id"]
            ]
            require(len(matches) == 1, "独立动作缺少唯一按钮")
            loc = matches[0]
        elif shape == "record_click":
            owned = {k for k, u in units.items() if u["entity"] in action["owners"]}
            matches = [p for p, leaves in leaves_of.items() if owned and leaves == owned]
            require(bool(matches), "record_click 无专属于该记录的完整子树")
            loc = min(matches, key=lambda p: len(p.split(".")))
        else:
            raise ContractError("未知点击范围")
        require(loc not in clicks, "多个动作争用同一点击区")
        clicks[loc] = copy.deepcopy(action["handlers"])
    return units, clicks


def finite(number):
    return (
        isinstance(number, (float, int)) and not isinstance(number, bool) and math.isfinite(number)
    )


def geometry_style(kind, root, unit, w, h, option):
    require(all(finite(i) and i > 0 for i in (w, h)), "宽高应为有限正数")
    base = {"width": w, "height": h}
    if root:
        base.update(padding=12, borderRadius=20, clip=True)
    if kind in LEAVES:
        size, weight, line_height, maximum = font(unit)
        require(type(option) is int and 1 <= option <= maximum, "文字行数不符")
        base.update(
            fontSize=size,
            fontWeight=weight,
            lineHeight=line_height,
            maxLines=option,
            textAlign="center" if kind == "button" else "start",
        )
        if kind == "button":
            require(h == 36, "按钮高度必须为36vp")
            base["borderRadius"] = 18
    else:
        require(option in GAPS and type(option) is int, "容器间距超出约定")
        base.update(itemMargin=option, alignItems="start", justifyContent="start")
    return base


def apply_decisions(tree, raw, shared):
    units, _ = roles_and_clicks(tree, shared)
    require(
        isinstance(raw, dict) and set(raw) == {"boxes"} and isinstance(raw["boxes"], list),
        "缺 boxes 数组",
    )
    result = copy.deepcopy(tree)
    nodes = dict(walk(result["root"]))
    seen = set()
    for box in raw["boxes"]:
        require(isinstance(box, dict), "行框记录类型有误")
        loc = box.get("at")
        require(isinstance(loc, str) and loc in nodes and loc not in seen, "位置未知或重复")
        seen.add(loc)
        node = nodes[loc]
        field = "lines" if node["kind"] in LEAVES else "gap"
        require(set(box) == {"at", "w", "h", field}, "几何输出包含越权或缺失字段")
        node["style"] = geometry_style(
            node["kind"],
            loc == "0",
            units.get(node.get("ref")),
            box["w"],
            box["h"],
            box[field],
        )
    require(seen == set(nodes), "部分节点缺少几何结果")
    return result


def emit(geometry, shared, tree):
    units, clicks = roles_and_clicks(geometry, shared, styled=True)
    source_tree = {p: (n["kind"], n.get("ref")) for p, n in walk(tree["root"])}
    require(
        source_tree == {p: (n["kind"], n.get("ref")) for p, n in walk(geometry["root"])},
        "几何阶段改变结构",
    )
    root_style = geometry["root"]["style"]
    require(
        tuple(root_style.get(k) for k in ("width", "height"))
        == tuple(shared["canvas"][k] for k in ("width", "height")),
        "画布被改变",
    )
    components = []
    ids = {
        p: n.get("ref", "root" if p == "0" else "layout_" + p.replace(".", "_"))
        for p, n in walk(geometry["root"])
    }
    require(len(ids) == len(set(ids.values())), "组件ID冲突")
    for loc, node in walk(geometry["root"]):
        kind, style = node["kind"], node["style"]
        require(isinstance(style, dict), "缺少样式对象")
        u = units.get(node.get("ref"))
        expected = geometry_style(
            kind,
            loc == "0",
            u,
            style.get("width"),
            style.get("height"),
            style.get("maxLines") if u else style.get("itemMargin"),
        )
        # 内层显式零 padding 与缺省一致；其他几何字段均参与两侧同一核对。
        pared = dict(style)
        if loc != "0" and pared.get("padding") == 0:
            del pared["padding"]
        require(pared == expected, "几何样式偏离共同配方 " + loc)
        style = dict(expected)
        comp = {"id": ids[loc], "component": kind.capitalize(), "styles": style}
        if u:
            comp["label" if kind == "button" else "content"] = u["expression"]
            style["fontColor"] = "#FF1F4799" if u["role"] in ("primary", "action") else "#CC1F4799"
            if kind == "button":
                style["backgroundColor"] = "#331F4799"
        else:
            comp["children"] = [ids[f"{loc}.{i}"] for i in range(len(node["children"]))]
            comp["itemMargin"] = style.pop("itemMargin")
        if loc == "0":
            style["linearGradient"] = {
                "direction": "RightBottom",
                "colors": [["#FFCBDDFE", 0], ["#FFF1F6FE", 1]],
            }
        if loc in clicks:
            comp["onClick"] = clicks[loc]
        components.append(comp)
    data = {}
    for path, value in shared["binding_samples"].items():
        data_model.write(data, path, copy.deepcopy(value))
    require(
        all(data_model.read(data, p) == value for p, value in shared["binding_samples"].items()),
        "数据未还原",
    )
    messages = []
    for op, payload in (
        ("createSurface", {"catalogId": "ohos.a2ui.extended.catalog.form"}),
        ("updateComponents", {"root": "root", "components": components}),
        ("updateDataModel", {"path": "/", "value": data}),
    ):
        messages.append({"version": "v0.9", op: {"surfaceId": "surface_card", **payload}})
    return messages
