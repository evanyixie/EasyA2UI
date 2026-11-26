"""独立六档开发实验的模型输入输出合同；本模块不发送请求。"""

import json
import math
import re
from collections.abc import Mapping
from copy import deepcopy


class ProtocolError(ValueError):
    """模型响应违反当前阶段的合同。"""


STAGES = ("one_shot", "content", "structure", "geometry", "theme", "emit")
NATIVE = {"one_shot", "emit"}
DIMENSIONS = {"2x2": (150, 150), "2x4": (300, 150)}
KINDS = {"column", "row", "text", "button"}
GEOMETRY = {
    "width", "height", "fontSize", "fontWeight", "lineHeight", "maxLines", "textAlign",
    "alignItems", "justifyContent", "padding", "borderRadius", "clip", "itemMargin",
}
THEME = {"fontColor", "backgroundColor", "linearGradient"}
COLOR = re.compile(r"^#(?:[A-Fa-f0-9]{8}|[A-Fa-f0-9]{6})$")
PALETTES = {
    "blue": ["#FFCBDDFE", "#FFF1F6FE", "#FF1F4799", "#991F4799", "#331F4799"],
    "purple": ["#FFDBCCFF", "#FFF6F2FF", "#FF563D99", "#99563D99", "#33563D99"],
    "warm": ["#FFFFE0CC", "#FFFFF7F2", "#FF8C4B1C", "#998C4B1C", "#338C4B1C"],
    "dark": ["#FF191A1C", "#FF202224", "#E5FFFFFF", "#99FFFFFF", "#33FFFFFF"],
}
SHELL = {"width": 150, "height": 150, "borderRadius": 20, "clip": True, "padding": 12}
CATALOG = "ohos.a2ui.extended.catalog.form"
SURFACE = "surface_card"


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _require(ok, message):
    if not ok:
        raise ProtocolError(message)


def _object(value, required, optional, name):
    _require(isinstance(value, dict), f"{name} 应为对象")
    _require(not (required - value.keys()), f"{name} 缺字段 {sorted(required - value.keys())}")
    _require(not (value.keys() - required - optional),
             f"{name} 越权字段 {sorted(value.keys() - required - optional)}")


def _pairs(pairs):
    obj = {}
    for key, value in pairs:
        _require(key not in obj, f"重复 JSON 键 {key}")
        obj[key] = value
    return obj


def _load(raw):
    def invalid(value):
        raise ProtocolError(f"非法 JSON 数值 {value}")
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ProtocolError(f"JSON 不可解析 {exc}") from exc


def _string(value, name):
    _require(isinstance(value, str) and bool(value.strip()), f"{name} 应为非空字符串")


def _values(obj):
    if isinstance(obj, Mapping):
        for value in obj.values():
            yield from _values(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _values(value)
    elif isinstance(obj, (str, int, float)) and not isinstance(obj, bool):
        yield str(obj)


def _pointer(obj, path):
    if not isinstance(path, str) or not path.startswith("/"):
        return None
    for part in path[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        elif isinstance(obj, list) and part.isdecimal() and int(part) < len(obj):
            obj = obj[int(part)]
        else:
            return None
    return obj


_NUM_TOKEN = re.compile(r"(?<![0-9.])\d+(?:\.\d+)?(?![0-9.])")


def _check_numbers(text, evidence, name):
    allowed = {token for value in evidence for token in _NUM_TOKEN.findall(value)}
    unexplained = set(_NUM_TOKEN.findall(text)) - allowed
    _require(not unexplained, f"{name} 含无来源数字 {sorted(unexplained)}")


def _content(plan, source):
    _object(plan, {"size", "domain", "title", "items", "actions"}, set(), "content")
    _require(plan["size"] == source["size"] and plan["size"] in DIMENSIONS, "内容阶段改变尺寸")
    for key in ("title", "domain"):
        _string(plan[key], key)
    _require(isinstance(plan["items"], list) and isinstance(plan["actions"], list),
             "items/actions 应为数组")
    business_text = [str(source.get(key, "")) for key in ("query", "title", "description")]
    evidence = business_text + list(_values(source.get("sample_data", {})))
    _check_numbers(plan["title"], evidence, "title")
    ids = {"title"}
    candidates = {a["id"]: a for a in source.get("candidate_actions", [])}
    for action_flag, rows in ((False, plan["items"]), (True, plan["actions"])):
        for pos, row in enumerate(rows):
            where = ("actions" if action_flag else "items") + f"[{pos}]"
            if action_flag:
                _object(row, {"id", "label"}, {"handler"}, where)
            else:
                _object(row, {"id", "text"}, {"path", "unit", "label", "entity", "role"}, where)
            _string(row["id"], where + ".id")
            _require(row["id"] not in ids, f"{where} 重复引用 id {row['id']}")
            ids.add(row["id"])
            if action_flag:
                _string(row["label"], where + ".label")
                candidate = candidates.get(row["id"])
                _require(candidate is not None, f"{where} 未登记的动作")
                if "handler" in row:
                    _require(row["handler"] == candidate.get("handler"), f"{where} 动作载荷被改写")
                _check_numbers(row["label"], evidence + [str(candidate.get("label", ""))], where)
                continue
            for key in row.keys() - {"id"}:
                _string(row[key], where + "." + key)
            path = row.get("path")
            if path is not None:
                _require(path in source.get("candidate_paths", []), f"{where} 未登记的事实路径 {path}")
                value = _pointer(source.get("sample_data", {}), path)
                _require(value is not None, f"{where} 路径缺少初始数据 {path}")
                _require(isinstance(value, (str, int, float, bool)), f"{where} 只允许绑定标量")
                # text 是几何阶段的测量文字，必须对应渲染时同一路径的真实值。
                original = str(value)
                alternatives = {original.lower(), original} if isinstance(value, bool) else {original}
                _require(row["text"] in alternatives, f"{where} 动态 text 与本路径首帧值不一致")
            else:
                _require(any(row["text"] in value for value in business_text),
                         f"{where} 静态事实须逐字来自 query/title/description")
            for key in ("label", "unit", "entity"):
                if key in row:
                    _check_numbers(row[key], evidence, where + "." + key)
    return plan


def _geometry(style, kind, root, size):
    _require({"width", "height"} <= style.keys(), "每个节点需要 width 与 height")
    if kind in ("text", "button"):
        _require({"fontSize", "maxLines"} <= style.keys(), "Text/Button 需要 fontSize 与 maxLines")
    for key in ("width", "height", "fontSize", "lineHeight", "padding", "borderRadius", "itemMargin"):
        if key in style:
            value = style[key]
            _require(type(value) in (int, float) and math.isfinite(value) and
                     (value > 0 if key in {"width", "height", "fontSize", "lineHeight"} else value >= 0),
                     f"{key} 的值无效")
    if "maxLines" in style:
        _require(type(style["maxLines"]) is int and style["maxLines"] > 0, "maxLines 必须为正整数")
    if "fontWeight" in style:
        _require(type(style["fontWeight"]) is int and style["fontWeight"] in (400, 500, 700),
                 "fontWeight 必须取 400/500/700")
    if "clip" in style:
        _require(type(style["clip"]) is bool, "clip 必须为布尔值")
    for key in ("textAlign", "alignItems", "justifyContent"):
        if key in style:
            options = ("start", "center", "end", "spaceBetween") if key == "justifyContent" else ("start", "center", "end")
            _require(style[key] in options, f"{key} 枚举值无效")
    if root:
        _require((style["width"], style["height"]) == DIMENSIONS[size], "根尺寸必须等于调用方尺寸")
        _require(style.get("borderRadius") == 20 and style.get("clip") is True, "root 壳缺圆角或裁切")


def _color(value):
    return isinstance(value, str) and bool(COLOR.fullmatch(value))


def _theme(style):
    for key in ("fontColor", "backgroundColor"):
        if key in style:
            _require(_color(style[key]), f"{key} 色值无效")
    if "linearGradient" in style:
        gradient = style["linearGradient"]
        _object(gradient, {"direction", "colors"}, set(), "linearGradient")
        _require(gradient["direction"] == "RightBottom", "渐变方向无效")
        stops = gradient["colors"]
        _require(isinstance(stops, list) and len(stops) == 2, "渐变需要两个色阶")
        for position, pair in enumerate(stops):
            _require(isinstance(pair, list) and len(pair) == 2 and _color(pair[0])
                     and type(pair[1]) in (int, float) and pair[1] == position, "渐变色阶无效")


def _tree(stage, tree, source, content, previous):
    _object(tree, {"root"}, set(), stage)
    _require(isinstance(content, dict), "树阶段缺输入语义计划")
    texts = {row["id"] for row in content["items"]} | {"title"}
    buttons = {row["id"] for row in content["actions"]}
    refs = set()
    def visit(node, prior, depth):
        _require(depth <= 64, "树深度超过开发执行器上限")
        _require(isinstance(node, dict) and isinstance(node.get("kind"), str) and node["kind"] in KINDS,
                 "未知节点 kind")
        kind = node["kind"]
        container = kind in ("row", "column")
        _require(depth or container, "root 应为 column 或 row")
        required = {"kind", "children" if container else "ref"}
        if stage != "structure":
            required.add("style")
        _object(node, required, set(), kind)
        if prior is not None:
            _require(prior.get("kind") == kind and prior.get("ref") == node.get("ref"), "树形或引用发生变化")
        if stage != "structure":
            style = node["style"]
            _object(style, set(), GEOMETRY | (THEME if stage == "theme" else set()), "style")
            if stage == "geometry":
                _geometry(style, kind, depth == 0, source["size"])
            else:
                _require({k: v for k, v in style.items() if k in GEOMETRY} == prior["style"],
                         "主题阶段修改了几何")
                _theme(style)
                if depth == 0:
                    _require("linearGradient" in style or "backgroundColor" in style, "主题缺根背景")
                if not container:
                    _require("fontColor" in style, "主题缺文字颜色")
        if container:
            kids = node["children"]
            _require(isinstance(kids, list) and kids, "容器需要非空 children")
            prev_kids = prior["children"] if prior is not None else None
            _require(prev_kids is None or len(prev_kids) == len(kids), "节点数量发生变化")
            for i, child in enumerate(kids):
                visit(child, prev_kids[i] if prev_kids is not None else None, depth + 1)
        else:
            ref = node["ref"]
            _string(ref, "ref")
            _require(ref in (texts if kind == "text" else buttons), f"{kind} 引用无效 {ref}")
            _require(ref not in refs, f"树内重复引用 {ref}")
            refs.add(ref)
    if stage in ("geometry", "theme"):
        _require(isinstance(previous, dict) and "root" in previous, "缺上一步的树")
    visit(tree["root"], None if stage == "structure" else previous["root"], 0)
    _require(refs == texts | buttons, f"树缺少已接受语义引用 {sorted((texts | buttons) - refs)}")
    return tree


def parse_output(stage, raw, source, content=None, tree=None):
    """严格解析响应；返回原对象，任何格式或权限错误都保留为失败。"""
    _require(stage in STAGES and isinstance(raw, str), "未知阶段或响应类型")
    if stage in NATIVE:
        lines = raw.strip().splitlines()
        _require(len(lines) == 3, "原生产物必须恰好三行 JSONL")
        messages = [_load(line) for line in lines]
        for message, operation in zip(messages, ("createSurface", "updateComponents", "updateDataModel"), strict=True):
            _object(message, {"version", operation}, set(), operation)
            _require(message["version"] == "v0.9" and isinstance(message[operation], dict),
                     f"{operation} 的版本或外层对象无效")
        return messages
    result = _load(raw)
    if stage == "content":
        return _content(result, source)
    return _tree(stage, result, source, content, tree)


# 同一人工构造的示例用于所有条件，无开发样本及正式答案。
_EXAMPLE_SOURCE = {
    "size": "2x2", "query": "显示庭院温度，读数用℃，可打开记录", "title": "庭院温度", "description": "",
    "candidate_paths": ["/garden/value"],
    "candidate_actions": [{"id": "a1", "label": "打开记录", "handler": {"call": "openLog", "args": {}}}],
    "sample_data": {"garden": {"value": 18}},
}
_EXAMPLE_CONTENT = {
    "size": "2x2", "domain": "weather", "title": "庭院温度",
    "items": [{"id": "v", "text": "18", "path": "/garden/value", "label": "读数", "unit": "℃",
               "role": "primary", "entity": "庭院"}],
    "actions": [{"id": "a1", "label": "打开记录"}],
}
_EXAMPLE_STRUCTURE = {"root": {"kind": "column", "children": [
    {"kind": "text", "ref": "title"}, {"kind": "text", "ref": "v"}, {"kind": "button", "ref": "a1"},
]}}
_EXAMPLE_GEOMETRY = deepcopy(_EXAMPLE_STRUCTURE)
_EXAMPLE_GEOMETRY["root"]["style"] = {**SHELL, "itemMargin": 6, "alignItems": "start", "justifyContent": "start"}
for _node, _size, _weight, _height in zip(_EXAMPLE_GEOMETRY["root"]["children"], (16, 24, 14), (700, 700, 500), (23, 34, 36), strict=True):
    _node["style"] = {"width": 126, "height": _height, "fontSize": _size, "fontWeight": _weight,
                      "lineHeight": 1.35, "maxLines": 1, "textAlign": "start"}
_EXAMPLE_GEOMETRY["root"]["children"][2]["style"].update(borderRadius=16, textAlign="center")
_EXAMPLE_THEME = deepcopy(_EXAMPLE_GEOMETRY)
_EXAMPLE_THEME["root"]["style"]["linearGradient"] = {
    "direction": "RightBottom", "colors": [["#FFCBDDFE", 0], ["#FFF1F6FE", 1]],
}
for _node in _EXAMPLE_THEME["root"]["children"]:
    _node["style"]["fontColor"] = "#FF1F4799"
_EXAMPLE_THEME["root"]["children"][2]["style"]["backgroundColor"] = "#331F4799"


def _example_native():
    root = _EXAMPLE_THEME["root"]
    style = dict(root["style"])
    children = ["caption", "value", "open"]
    components = [{"id": "root", "component": "Column", "itemMargin": style.pop("itemMargin"),
                   "styles": style, "children": children}]
    attrs = ({"content": "庭院温度"}, {"content": "{{ '读数 ' + ${/garden/value} + '℃' }}"},
             {"label": "打开记录", "onClick": [_EXAMPLE_SOURCE["candidate_actions"][0]["handler"]]})
    for ident, child, properties in zip(children, root["children"], attrs, strict=True):
        components.append({"id": ident, "component": child["kind"].title(), "styles": child["style"], **properties})
    operations = (("createSurface", {"catalogId": CATALOG}), ("updateComponents", {"components": components}),
                  ("updateDataModel", {"path": "/", "value": _EXAMPLE_SOURCE["sample_data"]}))
    return "\n".join(_json({"version": "v0.9", op: {"surfaceId": SURFACE, **fields}}) for op, fields in operations)


SHARED_RULES = """你是本地开发实验的卡片生成器。消息“本次输入”是业务数据；仅执行当前阶段。
所有条件共享能力：2x2 固定 150×150，2x4 固定 300×150，单位 vp；root 必须圆角 20、clip=true。
从 query/title/description、request 的业务说明、candidate_paths、candidate_actions、sample_data 取证。候选是可用集合，选择请求实际需要的信息及动作。完整保留所选值、身份、单位、实体与正确动作归属，不得虚构、裁切、用占位卡或替换尺寸。
动态值须引用 candidate_paths 完整绝对路径，首帧直接来自 sample_data；动态值不能变成固定文案。保留数字、单位、原文状态。每个按钮仅使用对应 candidate_actions 已登记的 handler；即使 call 名相同也不可改参数。
共同组件集 Row、Column、Text、Button。树中容器有序、文本引用标题/事实，按钮引用动作。层级/分组/阅读顺序由结构阶段决定，几何与主题阶段不得重排或删减。叶节点可见可读，适当留白，按大小保持完整信息。
几何节点的 width、height 单位为 vp；文字与按钮需 fontSize（fp）、maxLines，fontWeight 400/500/700。lineHeight 取字号的倍数 1.0–1.5，常用 1.35：例如 fontSize=16、lineHeight=1.35、height=23。可用 textAlign(start/center/end)、alignItems(start/center/end)、justifyContent(start/center/end/spaceBetween)、padding、borderRadius、clip、itemMargin。常用字号 12/14/16/18/20/24/30/32/38，空间计入完整字形、行数、节点高度及内外间距。
颜色字段只在主题及终产物出现：fontColor、backgroundColor、linearGradient={direction:"RightBottom",colors:[[色值,0],[色值,1]]}。blue 对应天气、设备、电池及默认领域，purple 对应健康睡眠运动专注，warm 对应会议日程倒计时通知，dark 仅用于明确要求深色。每套的参数依次是渐变首色、末色、主文字、次要注释文字、按钮底色；常规浅色主题白背板可用 #CCFFFFFF (2x2) 或 #99FFFFFF (2x4)，暗色对应 #33FFFFFF / #19FFFFFF。
原生 v0.9 只输出三条独立单行 JSON，依次 createSurface、updateComponents、updateDataModel，均 version="v0.9"、surfaceId="surface_card"。createSurface 的 catalogId 为 ohos.a2ui.extended.catalog.form。updateComponents.components 为扁平节点列表；root id 固定为 root、容器 children 是子节点 id 字符串数组、所有 id 唯一、布局写 styles；容器 itemMargin 放组件顶层。Button 用 label 与 onClick:[原始 handler]。Text.content 可为静态字符串。纯动态值用 {"path":"/绝对路径"}；带 label 或 unit 的动态值在同一个 Text.content 中拼接，形如 "{{ '读数 ' + ${/garden/value} + '℃' }}"；JSON 字符串外层用双引号，表达式内的文字用单引号。样值已有的标签或单位只显示一次。updateDataModel 的 path="/"、value=输入的完整 sample_data。输出无需 Markdown 或说明。
"""
_TASKS = {
    "one_shot": "一次设计并直接输出完整原生三行 JSONL。自由决定语义、树、几何、主题、发射；直接给终产物。",
    "content": """只输出语义 JSON 对象 {size,domain,title,items:[{id,text,path?,unit?,label?,entity?,role?}],actions:[{id,label,handler?}]}。
每个字段用字符串；handler 若写必须是输入原对象。title 简洁、来自请求；item.id 自定唯一且避开 title 与动作 id。动态 item.path 是候选中的完整标量路径，text 是该路径实际首帧值的字符串（额外 label/unit 单独提供）；采用已知样值。静态事实 text 逐字从业务标题、需求或描述取。id=title 是保留引用。动作 id 必须照搬 candidate_actions[i].id；label 用明确业务动词。不得加布局或颜色。""",
    "structure": """在给定语义计划上自由写有序嵌套组件树，只输出 {"root":节点}。容器 {kind:"row"或"column",children:[...]}，根为容器。取本次输入 required_leaf_refs 中的每个 ref 恰好一次，按登记 kind 建 {kind,ref} 叶。label、unit 属于所属 item 的同一个 Text；不另造 ref。叶清单未指定布局，阅读顺序、容器及实体分组由你决定。此阶段无 style。""",
    "geometry": """复制传入整棵树，在每个节点添加 style。只能用上述几何字段，不能换任何节点、ref、树序或加颜色。root 明确宽高/圆角/clip，所有节点含数值 width/height，Text/Button 含 fontSize,maxLines；高度与行距需覆盖完整文本，所有列的高度/行的宽度须合计留得下。返回含 root 的完整树。""",
    "theme": """复制给定带几何的整棵树。保持每项原几何属性及值，只在节点 style 增加原生色值。root 需渐变或背景，每个 Text/Button 应有 fontColor，按钮可加 backgroundColor。按业务域及用户意图完成着色，返回含 root 的完整树。""",
    "emit": """按已给带色值树序列化三行 JSONL，逐叶按 ref 读取 content。若 item 同时含 path 和 label/unit，像共同示例一样将标签、绑定路径、单位保存在一个 Text.content；无标签和单位才用纯 {path}。保持标题、静态文案、动作和对应原始 handler，沿用树序、全部几何与颜色。""",
}


def build_messages(stage, source, content=None, tree=None):
    """所有条件共用业务例、约束和原生例；分段时再给本阶段格式。"""
    _require(stage in STAGES, "未知模型阶段")
    _require(source.get("size") in DIMENSIONS, "开发执行器只支持 2x2、2x4")
    if stage not in ("one_shot", "content"):
        _require(isinstance(content, dict), "缺少上一步语义计划")
    if stage in ("geometry", "theme", "emit"):
        _require(isinstance(tree, dict), "缺少上一步树")
    examples = {"content": _EXAMPLE_CONTENT, "structure": _EXAMPLE_STRUCTURE,
                "geometry": _EXAMPLE_GEOMETRY, "theme": _EXAMPLE_THEME}
    common = (SHARED_RULES + "\n色板：" + _json(PALETTES) + "\n同一虚构示例输入：" + _json(_EXAMPLE_SOURCE)
              + "\n对应完整终产物示例：\n" + _example_native())
    if stage in examples:
        common += "\n同一示例在本阶段的输出：" + _json(examples[stage])
    data = {"source": source}
    if content is not None:
        data["content"] = content
    if stage == "structure":
        data["required_leaf_refs"] = [
            {"kind": "text", "ref": "title"},
            *({"kind": "text", "ref": item["id"]} for item in content["items"]),
            *({"kind": "button", "ref": action["id"]} for action in content["actions"]),
        ]
    if tree is not None:
        data["tree"] = tree
    return [{"role": "system", "content": common + "\n本次阶段：" + _TASKS[stage]},
            {"role": "user", "content": "本次输入：" + _json(data)}]
