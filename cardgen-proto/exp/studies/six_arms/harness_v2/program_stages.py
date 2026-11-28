"""外部开发预实验的程序阶段。文字测量来自冻结的 7.1 参考字体引擎。"""

from __future__ import annotations

import copy
import importlib.util
import math
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

# 研究包与 cardgen-proto/exp 下的条件表共用同一个原型。
EASY = Path(os.environ.get("EASY_CARDGEN_ROOT") or Path(__file__).resolve().parents[4])
genui_root = os.environ.get("GENUI_ROOT")
engine = os.environ.get("SIX_ARMS_MEASURE_PY")
MEASURE_FILE = (
    Path(engine) if engine else Path(genui_root) / "src/genui_device/measure.py"
    if genui_root else None
)
REGULAR = Path(os.environ["SIX_ARMS_FONT_REGULAR"]) if os.environ.get("SIX_ARMS_FONT_REGULAR") else None
BOLD = Path(os.environ["SIX_ARMS_FONT_BOLD"]) if os.environ.get("SIX_ARMS_FONT_BOLD") else None


def measurement_files():
    files = {"measure.py": MEASURE_FILE, "regular.ttf": REGULAR, "bold.ttf": BOLD}
    if any(p is None or not p.is_file() for p in files.values()):
        raise RuntimeError("程序几何需要 GENUI_ROOT 或 SIX_ARMS_MEASURE_PY，以及 SIX_ARMS_FONT_REGULAR、SIX_ARMS_FONT_BOLD")
    return files


CANVASES = {"2x2": (150, 150), "2x4": (300, 150)}
CONTAINERS = {"column", "row"}
LEAVES = {"text", "button"}
PRIMARY_ROLES = {"primary", "headline", "metric", "focus", "value", "main"}


class StageError(ValueError):
    """可随运行回执保存的明确拒绝。"""

    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@lru_cache
def _module(name, path):
    spec = importlib.util.spec_from_file_location("six_arms_frozen_" + name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@lru_cache
def _measure():
    measurement_files()
    return _module("measure", MEASURE_FILE).TextMeasure(REGULAR, BOLD)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _canvas(size):
    if isinstance(size, dict):
        dims = (size.get("width_vp", size.get("width")), size.get("height_vp", size.get("height")))
        if all(_number(value) and value > 0 for value in dims):
            return dims
    elif isinstance(size, str) and size in CANVASES:
        return CANVASES[size]
    raise StageError("unsupported_canvas", repr(size))


def _index(content):
    title = content.get("title")
    if not isinstance(title, str):
        raise StageError("invalid_content", "title 应为字符串")
    entries = {"title": {"text": title, "role": "title"}} if title else {}
    actions = set()
    for key, label in (("items", "text"), ("actions", "label")):
        rows = content.get(key, [])
        if not isinstance(rows, list):
            raise StageError("invalid_content", f"{key} 应为列表")
        for row in rows:
            if not isinstance(row, dict):
                raise StageError("invalid_content", f"{key} 条目须为对象")
            ref = row.get("id")
            if not isinstance(ref, str) or not ref or ref == "title" or ref in entries:
                raise StageError("invalid_reference", repr(ref))
            if not isinstance(row.get(label), str) or not row[label].strip():
                raise StageError("invalid_content", f"{ref} 缺少 {label}")
            entries[ref] = row
            if key == "actions":
                actions.add(ref)
    return entries, actions


def _check_tree(tree, entries, actions):
    used = set()

    def visit(node):
        if not isinstance(node, dict):
            raise StageError("invalid_structure", "节点须为对象")
        kind = node.get("kind")
        if kind in CONTAINERS:
            if node.get("ref") is not None or not isinstance(node.get("children"), list) or not node["children"]:
                raise StageError("invalid_structure", "容器须声明非空子节点")
            for child in node["children"]:
                visit(child)
        elif kind in LEAVES:
            ref = node.get("ref")
            if not isinstance(ref, str) or ref not in entries or ref in used:
                raise StageError("invalid_reference", repr(ref))
            if (kind == "button") != (ref in actions) or node.get("children"):
                raise StageError("invalid_structure", f"{kind}/{ref} 的节点角色错误")
            used.add(ref)
        else:
            raise StageError("unsupported_component", str(kind))

    if not isinstance(tree, dict) or not isinstance(tree.get("root"), dict):
        raise StageError("invalid_structure", "缺少 root")
    visit(tree["root"])
    missing = set(entries) - used
    if missing:
        raise StageError("omitted_references", ", ".join(sorted(missing)))


def program_route(content):
    """按实体保留相邻记录，宽卡允许同层两个记录并排。"""
    entries, actions = _index(content)
    width, _ = _canvas(content.get("size"))
    nodes = [{"kind": "text", "ref": "title"}] if "title" in entries else []
    groups = []
    for row in content.get("items", []):
        entity = row.get("entity")
        if groups and entity and entity == groups[-1][0]:
            groups[-1][1].append({"kind": "text", "ref": row["id"]})
        else:
            groups.append((entity, [{"kind": "text", "ref": row["id"]}]))
    grouped_actions = set()
    for index, (entity, children) in enumerate(groups):
        if entity and all(other != entity for other, _ in groups[index + 1:]):
            for action in content.get("actions", []):
                if action.get("entity") == entity:
                    children.append({"kind": "button", "ref": action["id"]})
                    grouped_actions.add(action["id"])
    i = 0
    while i < len(groups):
        entity, children = groups[i]
        block = children[0] if len(children) == 1 else {"kind": "column", "children": children}
        if width >= 280 and entity and i + 1 < len(groups) and groups[i + 1][0]:
            following = groups[i + 1][1]
            sibling = following[0] if len(following) == 1 else {"kind": "column", "children": following}
            block = {"kind": "row", "children": [block, sibling]}
            i += 1
        nodes.append(block)
        i += 1
    for ref in entries:
        if ref in actions - grouped_actions:
            nodes.append({"kind": "button", "ref": ref})
    tree = {"root": {"kind": "column", "children": nodes}}
    _check_tree(tree, entries, actions)
    return tree


def _parts(entry, value):
    label = entry.get("label") or ""
    unit = entry.get("unit") or ""
    if not isinstance(label, str) or not isinstance(unit, str):
        raise StageError("invalid_content", "label/unit 应为字符串")
    prefix = label + " " if label and not value.startswith(label) else ""
    suffix = unit if unit and not value.endswith(unit) else ""
    return prefix, value, suffix


def _leaf_text(node, entries):
    item = entries[node["ref"]]
    if node["kind"] == "button":
        return item["label"]
    return "".join(_parts(item, item["text"]))


def _font_style(node, entries, compact):
    if node["kind"] == "button":
        return (12 if compact else 14), 500
    role = entries[node["ref"]].get("role")
    if role in PRIMARY_ROLES:
        return (16 if compact else 20), 700
    if node["ref"] == "title":
        return 12, 500
    return (12 if compact else 14), 400


def _natural_width(value, font_size, weight):
    font = _measure()._font(font_size, weight >= 600)
    return math.ceil(max((font.getlength(line) for line in value.split("\n")), default=0) / 4 + 4)


def _row_widths(preferred, total):
    """在同一行中先满足短节点，再把剩余宽度平分给尚未满足的节点。"""
    if total <= 0:
        raise StageError("reference_capacity", "行间距超过可用宽度")
    widths = [0] * len(preferred)
    remaining = total
    for index, child in enumerate(sorted(range(len(preferred)), key=preferred.__getitem__)):
        share = remaining / (len(preferred) - index)
        widths[child] = share if index == len(preferred) - 1 else min(preferred[child], share)
        remaining -= widths[child]
    return widths


def program_geometry(structure, content):
    """保留自由树并试排两组固定的间距和字号，所有文字均须完整容纳。"""
    entries, actions = _index(content)
    _check_tree(structure, entries, actions)
    width, height = _canvas(content.get("size"))
    oracle = _measure()
    capacity = _module("measure", MEASURE_FILE).CapacityError

    def solve(compact):
        gap, pad = (2, 8) if compact else (4, 10)
        tree = copy.deepcopy(structure)

        def preferred(node):
            if node["kind"] in LEAVES:
                size, weight = _font_style(node, entries, compact)
                return _natural_width(_leaf_text(node, entries), size, weight) + (12 if node["kind"] == "button" else 0)
            parts = [preferred(child) for child in node["children"]]
            return sum(parts) + gap * (len(parts) - 1) if node["kind"] == "row" else max(parts)

        def assign(node, available, root=False):
            kind = node["kind"]
            padding = pad if root else 0
            style = {"width": available}
            node["style"] = style
            if root:
                style.update(padding=padding, borderRadius=20, clip=True)
            inside = available - 2 * padding
            if kind in LEAVES:
                size, weight = _font_style(node, entries, compact)
                button = kind == "button"
                horizontal_inset = 6 if button else 0
                line_height = 1.3
                metric = oracle.text(_leaf_text(node, entries), inside - 2 * horizontal_inset, size,
                                     max_lines=1 if button else max(1, int(height / size)),
                                     bold=weight >= 600, line_height=line_height)
                style.update(fontSize=size, fontWeight=weight, maxLines=metric.lines,
                             lineHeight=line_height, textAlign="center" if button else "start")
                if button:
                    style["borderRadius"] = 16 if not root else 20
                used = (max(30, metric.height + 6) if button else metric.height) + 2 * padding
            else:
                children = node["children"]
                spaces = gap * (len(children) - 1)
                widths = (_row_widths([preferred(child) for child in children], inside - spaces)
                          if kind == "row" else [inside] * len(children))
                heights = [assign(child, child_width) for child, child_width in zip(children, widths, strict=True)]
                used = (max(heights) if kind == "row" else sum(heights) + spaces) + 2 * padding
                style.update(itemMargin=gap, alignItems="start", justifyContent="start")
            style["height"] = height if root else used
            return used

        required = assign(tree["root"], width, root=True)
        if required > height:
            raise StageError("reference_capacity", f"完整内容需要 {required:g}vp，画布高度为 {height:g}vp")
        return tree

    for compact in (False, True):
        try:
            return solve(compact)
        except (capacity, StageError) as exc:
            if isinstance(exc, StageError) and exc.code != "reference_capacity":
                raise
            if compact:
                raise StageError("reference_capacity", str(exc)) from exc


def program_theme(geometry, content):
    """按 Easy 冻结主题目录选色；只着色，不改变几何或选型。"""
    entries, actions = _index(content)
    _check_tree(geometry, entries, actions)
    source = _module("easy_theme", EASY / "src/P6_theme.py")
    selected = source.select_theme(content.get("domain"), content.get("theme"), [])
    palette = source.CATALOG["themes"][selected]["palette"]
    themed = copy.deepcopy(geometry)

    def visit(node):
        style = node.setdefault("style", {})
        if node["kind"] in LEAVES:
            role = entries[node["ref"]].get("role")
            color = "primary_text" if role in PRIMARY_ROLES or node["ref"] == "title" else "secondary_text"
            style["fontColor"] = palette["roles"][color]
            if node["kind"] == "button":
                style["backgroundColor"] = palette["roles"]["action_bg"]
        for child in node.get("children", []):
            visit(child)

    visit(themed["root"])
    themed["root"]["style"]["linearGradient"] = copy.deepcopy(palette["gradient"])
    return themed


def _sample(data, path):
    if not isinstance(path, str) or not path.startswith("/") or re.search(r"~(?![01])", path):
        raise StageError("invalid_binding_path", repr(path))
    value = data
    for token in path[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and token in value:
            value = value[token]
        elif isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", token) and int(token) < len(value):
            value = value[int(token)]
        else:
            raise StageError("missing_binding_sample", path)
    if type(value) is bool:
        return "true" if value else "false"
    if not isinstance(value, str) and not _number(value):
        raise StageError("unsupported_binding_value", path)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _handler(context, ref):
    handler = context.get("action_handlers", {}).get(ref)
    if handler is None:
        for action in context.get("actions", []):
            if isinstance(action, dict) and action.get("id") == ref:
                handler = action.get("handler", action.get("event"))
                break
    if not isinstance(handler, dict) or not isinstance(handler.get("call"), str) or not handler["call"].strip():
        raise StageError("missing_action_handler", ref)
    return copy.deepcopy(handler)


def _native_literal(text):
    """设备已验证的单引号字面量；未证实可逆的转义不能直接输出。"""
    if any(char in text for char in ("'", '"', "\\", "${", "{{", "}}")) or any(
        ord(char) < 32 or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF
        or char in "\u2028\u2029" for char in text
    ):
        raise StageError("unrepresentable_binding_literal", "文本含设备未验证的表达式分隔符或控制符")
    return "'" + text + "'"


def program_emit(themed, content, context):
    """发射冻结宿主的三条 v0.9 消息；只接受调用者的首帧样值和事件载荷。"""
    entries, actions = _index(content)
    _check_tree(themed, entries, actions)
    width, height = _canvas(content.get("size"))
    if ("size" in context and _canvas(context["size"]) != (width, height)) or (
        ("width_vp" in context or "height_vp" in context)
        and (context.get("width_vp"), context.get("height_vp")) != (width, height)
    ):
        raise StageError("caller_canvas_mismatch", "调用者画布与内容合同冲突")
    data = context.get("sample_data", {})
    if not isinstance(data, dict):
        raise StageError("invalid_sample_data", "调用者首帧数据应为对象")
    components = []

    def emit(node, identity):
        kind = node["kind"]
        style = copy.deepcopy(node.get("style", {}))
        if not all(_number(style.get(key)) and style[key] > 0 for key in ("width", "height")):
            raise StageError("missing_geometry", identity)
        if identity == "root" and ((style["width"], style["height"]) != (width, height)
                                   or style.get("clip") is not True or style.get("borderRadius") != 20):
            raise StageError("root_shell_mismatch", f"{width}×{height}、圆角20和clip为必需")
        part = {"id": identity, "component": kind.title(), "styles": style}
        components.append(part)
        if kind in CONTAINERS:
            part["itemMargin"] = style.pop("itemMargin", 0)
            part["children"] = []
            for index, child in enumerate(node["children"]):
                child_id = f"{identity}_{index}"
                part["children"].append(child_id)
                emit(child, child_id)
            return
        if not (_number(style.get("fontSize")) and style["fontSize"] > 0
                and type(style.get("maxLines")) is int and style["maxLines"] > 0):
            raise StageError("missing_geometry", f"{identity} 缺少字号或完整行数")
        ref = node["ref"]
        entry = entries[ref]
        if kind == "button":
            part.update(label=entry["label"], onClick=[_handler(context, ref)])
            return
        path = entry.get("path")
        if path is None:
            part["content"] = _leaf_text(node, entries)
            return
        value = _sample(data, path)
        prefix, _, suffix = _parts(entry, value)
        if not prefix and not suffix:
            part["content"] = {"path": path}
            return
        # 同一个 Text 上保留动态路径，使用宿主支持的字符串拼接表达式。
        if "}" in path or path != path.strip():
            raise StageError("unrepresentable_binding_expression", path)
        operands = [_native_literal(prefix)] if prefix else []
        operands.append("${" + path + "}")
        if suffix:
            operands.append(_native_literal(suffix))
        part["content"] = "{{ " + " + ".join(operands) + " }}"

    emit(themed["root"], "root")
    surface = {"surfaceId": "surface_card"}
    return [
        {"version": "v0.9", "createSurface": {**surface, "catalogId": "ohos.a2ui.extended.catalog.form"}},
        {"version": "v0.9", "updateComponents": {**surface, "root": "root", "components": components}},
        {"version": "v0.9", "updateDataModel": {**surface, "path": "/", "value": copy.deepcopy(data)}},
    ]
