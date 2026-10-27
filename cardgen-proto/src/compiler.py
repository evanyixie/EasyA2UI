"""P7 发射器：着色后 IR → A2UI surface（纯结构展开 + 协议合规，零色板知识）。

两个产物：
  compile_a2ui       简化调试视图（角色 + 文案 + 绑定汇总）
  compile_a2ui_full  A2UI v0.9 协议（鸿蒙扩展 form catalog 方言）
                     JSONL 三行：createSurface + updateComponents + updateDataModel

输入契约（由 P6 主题装配保证）：
  ir["tree"]         已着色的骨架树（语义背景 token 已替换为具体样式）；
  ir["palette"]      解析后的具体色板（roles 为具体 #AARRGGBB 色值）；
  ir["slot_layouts"] P5 容量引擎的槽位布局决策（v3 §8）：structure = stack /
                     row（同行包裹小 Row）/ merged（合成单 Text），rows 给出
                     行组与 ref，fonts 给出字号；本模块按 rows 发射；
  entries 的 spec 已无 color_role 等角色键，颜色全部为具体值。
本模块不读取 registry/themes.json，不做任何颜色决策。

发射规则（对齐 CreateMyCard UX-SPEC 与鸿蒙 Form 协议）：
  前序展平（root 第一位、父先子后）；小背板 zone 按布局决策合成行
  （第一行 700 对象名+主值，第二行 400，多项用 " | " 连接；merged 时合成单行）；zone 动作
  绑定为背板容器 onClick（EventHandler 恰好 1 个 handler）；开关条目发射
  Checkbox（Form 无 Toggle）；空槽位整体省略（协议禁止空 Row/Column）。
"""
import json
from pathlib import Path
from . import forms
from .paths import media_src
from .metrics import LINE_HEIGHT_RATIO, est_width, semantic_truncate

_semantic_truncate = semantic_truncate  # 兼容旧调用名

ROOT = Path(__file__).resolve().parent.parent
REG = json.loads((ROOT / "registry/components.json").read_text(encoding="utf-8"))
ROLES = REG["roles"]
# 图标策略（金标反哺）：标题区图标按业务域、动作内图标按动作语义关键词
ICON_POLICY = json.loads((ROOT / "registry/icons.json").read_text(encoding="utf-8"))


def header_icon_src(domain: str) -> str:
    name = ICON_POLICY["header_icon_by_domain"].get(domain, ICON_POLICY["default_header_icon"])
    return media_src(name)


def action_icon_src(label: str) -> str:
    for kw, name in ICON_POLICY["action_icon_by_keyword"]:
        if kw in (label or ""):
            return media_src(name)
    return media_src(ICON_POLICY["default_action_icon"])

CATALOG_ID = "ohos.a2ui.extended.catalog.form"

STYLE_KEYS = ("fontSize", "fontWeight", "fontColor", "backgroundColor", "height",
              "maxLines", "textAlign", "borderRadius", "borderWidth", "borderColor",
              "padding", "layoutWeight", "itemMargin", "alignItems", "justifyContent",
              "width", "clip", "linearGradient")


def _entry_component(e: dict) -> dict:
    """单条目 → 原生组件（语义字段扁平 + styles 嵌套；spec 颜色已由 P6 落定）。"""
    a2ui = ROLES[e["role"]]["a2ui"]
    spec = e["spec"]
    if e["role"] == "icon_action":
        # 圆形图标动作钮（数据 M2 的 bottom_action）：40x40 圆形容器，整块可点击。
        iid = e["instance_id"]
        # 金标该形态是 Stack(40)>Stack(40)>Image(20)：图标槽已启用，按动作语义取图标
        glyph = {"id": f"{iid}-icon", "component": "Image",
                 "src": action_icon_src(e["copy"]),
                 "styles": {"width": ICON_POLICY["spec"]["size"],
                            "height": ICON_POLICY["spec"]["size"],
                            "objectFit": ICON_POLICY["spec"]["objectFit"],
                            "fillColor": spec.get("fontColor")}}
        return {"id": iid, "component": "Stack",
                "styles": {"width": spec.get("width", 40), "height": spec.get("height", 40),
                           "borderRadius": spec.get("borderRadius", 20),
                           "backgroundColor": spec.get("backgroundColor"),
                           "justifyContent": "center", "alignContent": "center"},
                "onClick": [{"call": f"{iid}-click", "args": {"binding": e["binding"]}}],
                "children": [glyph["id"]], "_kids": [glyph]}
    if a2ui == "Row":
        # 图文胶囊（金标形态）：Row 承载图标 + 文字，整块可点
        iid = e["instance_id"]
        icon = {"id": f"{iid}-icon", "component": "Image",
                "src": action_icon_src(e.get("label") or e["copy"]),
                "styles": {"width": spec.get("icon", 20), "height": spec.get("icon", 20),
                           "objectFit": ICON_POLICY["spec"]["objectFit"],
                           "fillColor": spec.get("fontColor")}}
        text = {"id": f"{iid}-text", "component": "Text", "content": e["copy"],
                "styles": {"fontSize": spec.get("fontSize", 14),
                           "fontWeight": spec.get("fontWeight", 500), "maxLines": 1,
                           "fontColor": spec.get("fontColor"),
                           "textAlign": spec.get("textAlign", "center")}}
        styles = {k: spec[k] for k in ("height", "borderRadius", "backgroundColor", "width")
                  if k in spec}
        styles.update({"alignItems": "center", "justifyContent": "center",
                       "itemMargin": spec.get("icon_gap", 8)})
        return {"id": iid, "component": "Row", "styles": styles,
                "onClick": [{"call": f"{iid}-click", "args": {"binding": e["binding"]}}],
                "children": [icon["id"], text["id"]], "_kids": [icon, text]}
    if a2ui == "Button":
        comp = {"id": e["instance_id"], "component": "Button",
                "label": e["copy"],
                "onClick": [{"call": f"{e['instance_id']}-click",
                             "args": {"binding": e["binding"]}}]}
    elif a2ui == "Checkbox":
        comp = {"id": e["instance_id"], "component": "Checkbox",
                "label": e["copy"], "select": bool(spec.get("select", False))}
    else:
        comp = {"id": e["instance_id"], "component": a2ui, "content": e["copy"]}
    styles = {k: spec[k] for k in STYLE_KEYS if k in spec}
    if styles:
        comp["styles"] = styles
    return comp


def _zone_children(entries: list, object_hint: str, roles: dict, inner_width: float = 110.0, layout=None,
                   headline: str = None, headline_id: str = "entry"):
    """业务背板内容：按 P5 容量引擎的行组决策合成 Text。

    默认规则（无布局决策时）：第一行 700 对象名+主值，其余合并为 400 第二行；
    merged 决策时全部合成为单行（` · ` 连接）。
    合成后的整行文字按背板内宽做宽度预算（超出带 … 截断）——zone 行是
    发射时才合成的，必须在此兜底。"""
    infos = [e for e in entries if e["kind"] == "info"]
    if not infos:
        return []
    by_ref = {e["ref"]: e for e in infos}
    layout = layout or {}
    fonts = layout.get("fonts") or {}
    rows = layout.get("rows") or [[e["ref"]] for e in infos]
    children = []
    if headline:
        # 入口板（小背板 + 绑定动作）：第一行是入口名，其余信息进第二行（规范：整块点击）
        line = headline
        if object_hint and object_hint not in line:
            line = f"{object_hint} {line}".strip()
        if est_width(line, 14) > inner_width:
            line = semantic_truncate(line, inner_width, 14)
        children.append({"id": headline_id, "component": "Text", "content": line,
                         "styles": {"fontSize": 14, "fontWeight": 700,
                                    "fontColor": roles["primary_text"], "maxLines": 1}})
        rest = [by_ref[r]["copy"] for r in [x for row in rows for x in row] if r in by_ref][:2]
        if rest:
            line2 = " | ".join(rest)
            if est_width(line2, 12) > inner_width:
                line2 = semantic_truncate(line2, inner_width, 12)
            children.append({"id": f"{headline_id}-aux", "component": "Text", "content": line2,
                             "styles": {"fontSize": 12, "fontWeight": 400,
                                        "fontColor": roles["primary_text"], "maxLines": 1}})
        return children

    for ri, row in enumerate(rows[:2]):
        refs = [r for r in row if r in by_ref]
        if not refs:
            continue
        head = by_ref[refs[0]]
        line = " · ".join(by_ref[r]["copy"] for r in refs)
        # 对象名前缀：条目文案已包含业务名时不再重复（避免"每日歌单 每日歌单"）
        if object_hint and object_hint not in line:
            line = f"{object_hint} {line}".strip()
        size = fonts.get(refs[0]) or (14 if ri == 0 else 12)
        if ri > 0:
            line = " | ".join(by_ref[r]["copy"] for r in refs)
        if est_width(line, size) > inner_width:
            line = semantic_truncate(line, inner_width, size)
        children.append({"id": head["instance_id"], "component": "Text", "content": line,
                         "styles": {"fontSize": size, "fontWeight": 700 if ri == 0 else 400,
                                    "fontColor": roles["primary_text"], "maxLines": 1}})
    return children


class _Emitter:
    def __init__(self, ir: dict):
        self.ir = ir
        self.roles = ir["palette"]["roles"]
        self.by_ref = {e["ref"]: e for e in ir["entries"]}
        self.objects = {i: o.get("name_hint", "") for i, o in enumerate(ir["objects"])}
        self.layouts = ir.get("slot_layouts") or {}
        self._node_styles = {}
        self.components = []

    def _fill_children(self, slot: str, f: dict):
        """槽位 → 子组件列表（可能为空 = 省略该槽位）。"""
        kids = []
        if slot.startswith("zone:"):
            oi = int(slot.split(":")[1])
            hint = self.objects.get(oi, "")
            st = self._node_styles.get(slot) or {}
            pad = st.get("padding", 12)
            pad_x = (pad.get("left", 0) + pad.get("right", 0)) if isinstance(pad, dict) else 2 * float(pad or 0)
            inner = float(st.get("width", 134)) - pad_x
            # 小背板（≤63 高）且绑定了动作 → 整块点击入口板：第一行用入口名（动作文案）
            act0 = self.by_ref[f["action"][0]] if f["action"] else None
            is_entry_board = bool(act0) and float(st.get("height", 0) or 0) <= 63
            kids = _zone_children([self.by_ref[r] for r in f["info"] if r in self.by_ref],
                                  hint, self.roles, inner_width=inner,
                                  layout=self.layouts.get(slot),
                                  headline=(act0["copy"] if is_entry_board else None),
                                  headline_id=(act0["instance_id"] if is_entry_board else "entry"))
            if f["action"]:
                a = self.by_ref[f["action"][0]]
                self._pending_onclick = [{"call": f"{a['instance_id']}-click",
                                          "args": {"binding": a["binding"]}}]
                if not kids:
                    # 背板无信息条目但绑定了动作：整块点击入口板（规范：W8/W10 右小板整块点击），
                    # 文字用动作文案（业务名），避免背板空置被省略
                    label = a["copy"]
                    if hint and hint not in label:
                        label = f"{hint} {label}".strip()
                    if est_width(label, 14) > inner:
                        label = semantic_truncate(label, inner, 14)
                    kids = [{"id": a["instance_id"], "component": "Text", "content": label,
                             "styles": {"fontSize": 14, "fontWeight": 700,
                                        "fontColor": self.roles["primary_text"], "maxLines": 1}}]
        elif slot == "header":
            kids = []
            st = self._node_styles.get(slot) or {}
            w = st.get("width")
            pad = st.get("padding", 0)
            pad_x = (pad.get("left", 0) + pad.get("right", 0)) if isinstance(pad, dict) else 2 * pad
            # 标题可用宽度 = 槽宽 − 左右 padding − 图标 20 − 间距 8（否则长标题会在右边界被硬裁）
            avail = (float(w) - pad_x - ICON_POLICY["spec"]["size"]
                     - ICON_POLICY["spec"]["header_gap"]) if isinstance(w, (int, float)) else None
            for r in f["info"]:
                e = self.by_ref.get(r)
                if e is not None:
                    if avail and est_width(e["copy"], e["spec"].get("fontSize", 12)) > avail:
                        e = dict(e, copy=semantic_truncate(
                            e["copy"], avail, e["spec"].get("fontSize", 12)))
                    kids.append(self._item_comp(e))
            kids.append({"id": "header-icon", "component": "Image",
                         "src": header_icon_src(self.ir.get("domain")),
                         "styles": {"width": ICON_POLICY["spec"]["size"],
                                    "height": ICON_POLICY["spec"]["size"],
                                    "objectFit": ICON_POLICY["spec"]["objectFit"],
                                    "fillColor": self.roles[ICON_POLICY["spec"]["ink_role"]]}})
        elif slot.startswith("action_zone:"):
            if f["action"]:
                kids = [_entry_component(self.by_ref[f["action"][0]])]
        else:
            # 用哪种排法由 registry/content_forms.json 决定（表驱动）；
            # 这里不再判断"环 / 标签值行 / 一条一行"，新增排法请改表 + 在 src/forms.py 加函数。
            layout = self.layouts.get(slot) or {}
            kids.extend(forms.emit(slot, f, layout, self))
            for r in f["action"]:
                if r in self.by_ref:
                    kids.append(_entry_component(self.by_ref[r]))
        return kids

    def _item_comp(self, e: dict) -> dict:
        """单条目组件：header_title 走 CardHeader 形态，其余按角色规格。"""
        if e["role"] == "header_title":
            # CardHeader 形态：标题 12fp/400（图标槽原型阶段省略）
            return {"id": e["instance_id"], "component": "Text", "content": e["copy"],
                    "styles": {"fontSize": e["spec"].get("fontSize", 12), "fontWeight": 400,
                               "fontColor": self.roles["primary_text"], "maxLines": 1}}
        return _entry_component(e)

    def _merged_comp(self, e: dict, text: str) -> dict:
        """合并候选（T4）：多项内容合成为一个 Text，样式沿用首条目规格。"""
        styles = {k: e["spec"][k] for k in STYLE_KEYS if k in e["spec"]}
        styles.setdefault("fontSize", 14)
        styles["fontColor"] = self.roles["primary_text"]
        styles["maxLines"] = 1
        return {"id": e["instance_id"], "component": "Text", "content": text, "styles": styles}

    def _build(self, node: dict):
        """递归构建组件子树：返回 comp dict（挂 _kids），空子树返回 None。"""
        slot = node.get("slot")
        comp = {"id": node["id"], "component": node["component"]}
        styles = node.get("styles") or {}
        if styles:
            comp["styles"] = styles
        self._pending_onclick = None

        if slot:
            self._node_styles[slot] = node.get("styles") or {}
            kid_comps = self._fill_children(slot, self.ir["fills"].get(slot, {"info": [], "action": []}))
            if self._pending_onclick:
                comp["onClick"] = self._pending_onclick
        else:
            kid_comps = []
            for ch in node.get("children", []) or []:
                sub = self._build(ch)
                if sub:
                    kid_comps.append(sub)

        if not kid_comps:
            if not slot and not (node.get("children") or []) and node.get("component") not in ("Column", "Row", "Stack", "List"):
                comp["_kids"] = []
                return comp  # 叶子组件（如 Divider）：无子树但必须保留
            return None  # 空槽位整体省略（协议禁止空容器）
        # 标题区只有图标、没有标题时（M1 没抽出标题，如 q12）：图标靠右。
        # 否则 spaceBetween 会把唯一子节点排到最左，看起来"图标跑到左上角"。
        if slot == "header" and len(kid_comps) == 1:
            comp.setdefault("styles", {})["justifyContent"] = "end"
        comp["children"] = [k["id"] for k in kid_comps]
        comp["_kids"] = kid_comps
        return comp

    def _flatten(self, comp: dict, out: list):
        """前序展平：父在子前、root 第一位（对齐 CreateMyCard 正式产物的发射顺序，
        兼容顺序处理 children 引用的渲染器）。"""
        kids = comp.pop("_kids", [])
        out.append(comp)
        for k in kids:
            self._flatten(k, out)


def compile_a2ui(ir: dict) -> dict:
    """简化调试视图：角色 + 文案 + 绑定汇总。"""
    return {
        "surfaceId": ir["surface_id"],
        "updateType": "delta",
        "components": [{"id": e["instance_id"], "role": e["role"], "text": e["copy"]}
                       for e in ir["entries"]],
        "root": list(ir["fills"].keys()),
        "dataBindings": {e["instance_id"]: e["binding"] for e in ir["entries"]},
    }


def compile_a2ui_full(ir: dict) -> str:
    """A2UI v0.9 协议输出（鸿蒙扩展 form catalog 方言）：JSONL 三行。

    组件数组按前序（父先子后、root 第一位）发射，对齐 CreateMyCard 正式产物。
    骨架树由 P6 主题装配解析后经 ir["tree"] 传入。
    """
    surface_id = ir["surface_id"]
    tree = ir.get("tree")
    if tree is None:  # 兜底：未走 P6 时回读骨架原始树（不推荐路径）
        skels = json.loads((ROOT / "registry/skeletons.json").read_text(encoding="utf-8"))
        tree = skels["skeletons"][ir["skeleton_id"]]["tree"]

    emitter = _Emitter(ir)
    root = emitter._build(tree)
    if root:
        # 画布尺寸显式声明（150×150 / 300×150）：渲染端按此定画布。
        # 设备端 Form 若需 matchParent 铺满卡片槽位，由端侧按 size 字段改写（见 v3.4）。
        w, h = (300, 150) if ir["size"] == "2x4" else (150, 150)
        root["styles"]["width"] = w
        root["styles"]["height"] = h
        root["styles"].setdefault("borderRadius", 20)
        root["styles"]["clip"] = True
        emitter._flatten(root, emitter.components)

    first_frame = {"items": {str(e["ref"]): e["copy"] for e in ir["entries"]}}
    messages = [
        {"version": "v0.9",
         "createSurface": {"surfaceId": surface_id, "catalogId": CATALOG_ID}},
        {"version": "v0.9",
         "updateComponents": {"surfaceId": surface_id, "components": emitter.components}},
        {"version": "v0.9",
         "updateDataModel": {"surfaceId": surface_id, "path": "/data",
                             "value": first_frame}},
    ]
    return "\n".join(json.dumps(m, ensure_ascii=False) for m in messages)
