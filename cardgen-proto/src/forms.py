"""内容类槽位的排法（方案2：表驱动）。

规则全部在 `registry/content_forms.json`：按 `order` 从小到大，取**第一个**满足
`when` 的排法。本模块只负责"怎么拼组件"，"用哪个"由表决定。

**扩展规则（写代码前先读）**
1. 新增一种排法 = 在表里加一条 `order` + `when`（+ 可选 `spec`），并在下面写一个同名函数；
   然后往 `EMITTERS` 里登记一行。**不要再往 `compiler._fill_children` 里加 if**。
2. 只有"多个排法会抢同一个槽"的槽位才值得进表：
   `content` / `primary` / `support` / `bottom_info`。
   `header`/`action` 是"条目类型 → 组件"的一对一映射，走 `component_select` 的规则表即可；
   `zone:`/`aux:` 背板的"放不下怎么缩"是试算，走 `layout_variants.json`，不要塞进本表。
3. 每种排法必须写明它最多吃几条（`max_items`）、是否要求条目都带标签等条件；
   "放不下怎么缩"仍交给容量引擎，排法本身不做降级。
"""
import json
import re
from pathlib import Path

from .metrics import est_width, semantic_truncate

ROOT = Path(__file__).resolve().parent.parent
TABLE = json.loads((ROOT / "registry/content_forms.json").read_text(encoding="utf-8"))["forms"]
SPECS = {f["id"]: f.get("spec", {}) for f in TABLE}


def _inner_w(em, slot, default=126):
    """槽位可用内宽（节点宽 - 左右 padding）。用于把过长的值截到放得下。"""
    st = (em._node_styles.get(slot) or {})
    w = st.get("width")
    if not isinstance(w, (int, float)):
        return default
    pad = st.get("padding", 0)
    pad_x = (pad.get("left", 0) + pad.get("right", 0)) if isinstance(pad, dict) else 2 * pad
    return max(20, w - pad_x)


def _fit_text(text, width, size, tol=4.0):
    """放不下就按语义边界截断；差值 ≤ tol 像素时保留原样（为了 2px 加个省略号更难看）。"""
    w = est_width(text, size)
    if width <= 0 or w <= width + tol:
        return text
    return semantic_truncate(text, width, size)


def _has_all_labels(items):
    return all(e is not None and e.get("label") for e in items)


def _match(rule: dict, ctx: dict) -> bool:
    w = rule.get("when") or {}
    if "slots" in w and ctx["slot"] not in w["slots"]:
        return False
    if w.get("has_layout_rows") and not ctx["rows"]:
        return False
    if w.get("all_present") and any(e is None for e in ctx["items"]):
        return False
    if "exact_types" in w:
        for t, n in w["exact_types"].items():
            if sum(1 for e in ctx["items"] if e is not None and e.get("type") == t) != n:
                return False
    if w.get("min_items") is not None and len(ctx["items"]) < w["min_items"]:
        return False
    if w.get("max_items") is not None and len(ctx["items"]) > w["max_items"]:
        return False
    if w.get("all_have_label") and not _has_all_labels(ctx["items"]):
        return False
    if w.get("no_promoted_hero") and any(e is not None and e.get("promoted_hero")
                                         for e in ctx["items"]):
        return False
    return True


def pick_form(slot: str, items: list, rows) -> str:
    """按表里的 order 取第一个可行的排法；表里最后一条必须无条件命中。"""
    ctx = {"slot": slot, "items": items, "rows": rows}
    for rule in TABLE:
        if _match(rule, ctx):
            return rule["id"]
    raise RuntimeError(f"content_forms.json 没有命中任何排法（slot={slot}），"
                       f"最后一条应当是无条件的兜底排法")


def emit(slot: str, fills: dict, layout: dict, em) -> list:
    """给内容类槽位生成子组件。em = 编译器实例（提供 roles / by_ref / 单条目发射）。"""
    items = [em.by_ref.get(r) for r in fills["info"]]
    form_id = pick_form(slot, items, layout.get("rows"))
    return EMITTERS[form_id](em, slot, fills, layout)


# --------------------------------------------------------------------------- 排法实现
def _capacity_rows(em, slot, f, layout):
    """容量引擎已经给出逐行决策：换轴 / 合并 / 单条照发。"""
    kids = []
    structure = layout.get("structure")
    for ri, row in enumerate(layout.get("rows") or []):
        refs = [r for r in row if r in em.by_ref]
        if not refs:
            continue
        if structure == "merged" and len(refs) > 1:
            text = " · ".join(em.by_ref[r]["copy"] for r in refs)
            kids.append(em._merged_comp(em.by_ref[refs[0]], text))
        elif structure == "row" and len(refs) > 1:
            inner = [em._item_comp(em.by_ref[r]) for r in refs]
            kids.append({"id": f"{slot}-row{ri}", "component": "Row",
                         "styles": {"alignItems": layout.get("align", "bottom"),
                                    "itemMargin": layout.get("itemMargin", 4)},
                         "children": [c["id"] for c in inner], "_kids": inner})
        else:
            for r in refs:
                kids.append(em._item_comp(em.by_ref[r]))
    return kids


def _ring_stat(em, slot, f, layout):
    """环形主值：`Row(h52){ Stack{Progress 环, 图标}, Column{标签, 值, 状态} }`。

    几何全部来自 content_forms.json 的 `spec`（改外观只改 JSON）。
    """
    from .compiler import header_icon_src      # 延迟导入，避免循环依赖

    items = [em.by_ref.get(r) for r in f["info"]]
    main = next(e for e in items if e.get("type") == "percent")
    rest = [e for e in items if e is not main]
    nums = re.findall(r"\d+(?:\.\d+)?", main["copy"])
    value = float(nums[0]) if nums else 0
    value = int(value) if value.is_integer() else value
    label = (main.get("label") or "").strip()

    rid = f"{slot}-ring"
    sp = SPECS["ring_stat"]
    ring = {"id": f"{rid}-arc", "component": "Progress",
            "value": value, "total": 100,
            "styles": {"width": sp["ring"], "height": sp["ring"],
                       "strokeWidth": sp["strokeWidth"], "type": "ring",
                       "color": em.roles[sp["colorRole"]],
                       "backgroundColor": em.roles[sp["trackRole"]]}}
    icon = {"id": f"{rid}-icon", "component": "Image",
            "src": header_icon_src(em.ir.get("domain")),
            "styles": {"width": sp["icon"], "height": sp["icon"], "objectFit": "contain",
                       "fillColor": em.roles[sp["iconRole"]]}}
    stack = {"id": f"{rid}-stack", "component": "Stack",
             "styles": {"width": sp["ring"], "height": sp["ring"], "alignContent": "center"},
             "children": [ring["id"], icon["id"]], "_kids": [ring, icon]}

    lines, line_ids = [], []
    if label:
        label = _fit_text(label, _inner_w(em, slot) - sp["ring"] - sp["iconGap"],
                          sp["label"]["fontSize"])
        lid = f"{rid}-label"
        line_ids.append(lid)
        lines.append({"id": lid, "component": "Text", "content": label,
                      "styles": {"width": "matchParent", "height": sp["label"]["height"],
                                 "fontSize": sp["label"]["fontSize"],
                                 "fontWeight": sp["label"]["fontWeight"], "maxLines": 1,
                                 "fontColor": em.roles[sp["label"]["colorRole"]]}})
    for i, e in enumerate([main] + rest):
        tid = f"{rid}-text{i}"
        line_ids.append(tid)
        lines.append({"id": tid, "component": "Text",
                      "content": e["copy"] if e is not main else str(value),
                      "styles": {"width": "matchParent", "height": sp["value"]["height"],
                                 "fontSize": sp["value"]["fontSize"],
                                 "fontWeight": sp["value"]["fontWeight"], "maxLines": 1,
                                 "fontColor": em.roles[sp["value"]["colorRole"]]}})
    column = {"id": f"{rid}-labels", "component": "Column",
              "styles": {"height": sp["rowHeight"], "layoutWeight": 1,
                         "itemMargin": sp["lineGap"],
                         "justifyContent": "center", "alignItems": "start"},
              "children": line_ids, "_kids": lines}
    return [{"id": rid, "component": "Row",
             "styles": {"width": "matchParent", "height": sp["rowHeight"],
                        "itemMargin": sp["iconGap"],
                        "justifyContent": "center", "alignItems": "center"},
             "children": [stack["id"], column["id"]], "_kids": [stack, column]}]


def _value_room(e, avail, sp):
    """标签优先保完整：值可用宽度 = 内宽 − 间距 − 标签实际宽度。"""
    label_w = est_width(e["label"], sp["label"]["fontSize"])
    return max(30.0, avail - sp["rowGap"] - label_w)


def _label_rows(em, slot, f, layout):
    """标签在左、数值在右；内容区整列沉底（金标 q20）。"""
    items = [em.by_ref.get(r) for r in f["info"]]
    sp = SPECS["label_rows"]
    avail = _inner_w(em, slot)
    rows = []
    for i, e in enumerate(items):
        lid, vid = f"{slot}-lv{i}-label", f"{slot}-lv{i}-value"
        rows.append({
            "id": f"{slot}-lv{i}", "component": "Row",
            "styles": {"width": "matchParent", "height": sp["rowHeight"],
                       "itemMargin": sp["rowGap"],
                       "alignItems": "center", "justifyContent": "spaceBetween"},
            "children": [lid, vid],
            "_kids": [
                {"id": lid, "component": "Text",
                 "content": _fit_text(e["label"], avail - sp["rowGap"] - 40,
                                      sp["label"]["fontSize"]),
                 "styles": {"fontSize": sp["label"]["fontSize"],
                            "fontWeight": sp["label"]["fontWeight"], "maxLines": 1,
                            "fontColor": em.roles[sp["label"]["colorRole"]]}},
                {"id": vid, "component": "Text",
                 "content": _fit_text(e["copy"], _value_room(e, avail, sp),
                                      sp["value"]["fontSize"]),
                 "styles": {"fontSize": sp["value"]["fontSize"],
                            "fontWeight": sp["value"]["fontWeight"], "maxLines": 1,
                            "layoutWeight": 1, "textAlign": "end",
                            "fontColor": em.roles[sp["value"]["colorRole"]]}}]})
    if slot != "content":
        return rows
    return [{"id": f"{slot}-lv-list", "component": "Column",
             "styles": {"width": "matchParent", "layoutWeight": 1,
                        "justifyContent": "end", "alignItems": "start",
                        "itemMargin": sp["listGap"]},
             "children": [r["id"] for r in rows], "_kids": rows}]


def _plain_items(em, slot, f, layout):
    """兜底：一条一段，按条目自身的角色规格发射。"""
    return [em._item_comp(em.by_ref[r]) for r in f["info"] if r in em.by_ref]


EMITTERS = {
    "capacity_rows": _capacity_rows,
    "ring_stat": _ring_stat,
    "label_rows": _label_rows,
    "plain_items": _plain_items,
}
