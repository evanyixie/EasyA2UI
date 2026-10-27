"""容量适配引擎（v3 §8）：前向枚举 + 首个可行解。

作用范围：**固定几何槽位**（内高确定的单行区 / 业务小背板）。高度是硬约束，
需要在"结构候选 × 字号梯级"上枚举；弹性槽位（内高 auto）不由本引擎处理，
沿用 P5 的宽度预算。

候选序列（见 registry/layout_variants.json）：
  single_line —— stack → row → merged → drop_should → truncate
  board       —— stack（两行）→ merged（单行）→ drop_should → truncate

每个候选内部按字号梯级内插，做**宽度 + 高度双预算**验收：宽度逐条/合计不得超内宽，
高度按 1.4 × 字号累计不得超内高。首个通过者定稿；`truncate` 是链尾兜底（必有解）。
全程只有一层有序 for 循环，无状态撤销、无回溯。

返回布局决策（assemble 写入 ir["slot_layouts"]）：
  {"kind","candidate","structure","rows","fonts","truncated","dropped",
   "merged_copy","align","itemMargin","log"}
  structure: stack（每行一项）/ row（一项内多项同行）/ merged（合成单 Text）
"""
import json
from pathlib import Path

from .metrics import est_height, est_width, semantic_truncate

ROOT = Path(__file__).resolve().parent.parent
V = json.loads((ROOT / "registry/layout_variants.json").read_text(encoding="utf-8"))

LINE_LADDER = V["ladders"]["line"]
VALUE_LADDER = V["ladders"]["value"]
SINGLE_LINE_MAX_H = V["slot_kinds"]["single_line_max_h"]
BOARD_MAX_W = V["slot_kinds"]["board_max_w"]
ROW_GAP = V["spacing"]["row_gap"]
LINE_GAP = V["spacing"]["line_gap"]
MERGE_ALIGN = V["spacing"]["merge_align"]
MERGE_SEP = V["separators"]["merge"]
LINE_SEP = V["separators"]["line"]
GUARDS = V["guards"]


BOARD_PREFIXES = tuple(V["slot_kinds"].get("board_slot_prefixes") or ())


def slot_kind(box: dict) -> str:
    """槽位形态判定（§8.3 第 1 步）：board / single_line / flow。

    业务小背板（zone:*/aux:*）优先按槽位命名识别——其内高（39）与单行区上限重叠，
    几何无法区分；其余按几何派生。
    """
    ih, iw = box.get("inner_h"), box.get("inner_w")
    if box.get("kind") in ("board", "single_line", "flow"):
        return box["kind"]          # 骨架显式标注优先（几何无法区分时）
    if ih is None or iw is None:
        return "flow"
    if BOARD_PREFIXES and str(box.get("slot", "")).startswith(BOARD_PREFIXES):
        return "board"
    if ih <= SINGLE_LINE_MAX_H:
        return "single_line"
    if iw <= BOARD_MAX_W:
        return "board"
    return "flow"


def _options(base: float, floor: float = 12) -> list:
    """字号梯级：base 向下取批准档位，且不低于角色下限 floor（不新增档位）。

    floor 来自角色规格 min_size（如 hero_value 底线 20 = 主数字降档序列终点）——
    这是"纵排缩到底"与"换轴保字号"之间的分界线：缩到下限仍放不下，
    就应当换结构，而不是继续把主值缩成普通文字。
    """
    pool = sorted({s for s in LINE_LADDER + VALUE_LADDER if floor <= s <= base}, reverse=True)
    return pool or [floor]


def _total_height(sizes: dict, items: list, gap: float) -> float:
    return sum(est_height(1, sizes[it["ref"]]) for it in items) + gap * max(0, len(items) - 1)


def _floor(it: dict) -> float:
    return it.get("min_size") or 12


def _shrink(sizes: dict, items: list) -> bool:
    """把当前最大字号压一档；无可压则返回 False（确定性：同号取 order 靠后者）。"""
    worst, worst_next = None, None
    for it in items:
        nxt = next((s for s in _options(it["base_size"], _floor(it)) if s < sizes[it["ref"]]), None)
        if nxt is None:
            continue
        if worst is None or (sizes[it["ref"]], it["order"]) > (sizes[worst["ref"]], worst["order"]):
            worst, worst_next = it, nxt
    if worst is None:
        return False
    sizes[worst["ref"]] = worst_next
    return True


def _fit_stack(items: list, box: dict):
    """纵排：每条独立一行；逐条取最大可行字号，再按高度收敛。"""
    sizes = {}
    for it in items:
        pick = next((s for s in _options(it["base_size"], _floor(it))
                     if est_width(it["copy"], s) <= box["inner_w"]), None)
        if pick is None:
            return None                     # 交给后续候选（合并 / 截断）
        sizes[it["ref"]] = pick
    guard = 0
    while _total_height(sizes, items, LINE_GAP) > box["inner_h"] and guard < 60:
        guard += 1
        if not _shrink(sizes, items):
            return None
    if _total_height(sizes, items, LINE_GAP) > box["inner_h"]:
        return None
    return {"structure": "stack", "rows": [[it["ref"]] for it in items],
            "fonts": sizes, "align": "start"}


def _fit_row(items: list, box: dict):
    """横排：全部内容同行（底部对齐）；先按宽度收敛，再按行高收敛。"""
    g = GUARDS["row"]
    if not (g["min_items"] <= len(items) <= g["max_items"]):
        return None
    if any(it["type"] in g.get("forbid_types", []) for it in items):
        return None
    sizes = {it["ref"]: _options(it["base_size"], _floor(it))[0] for it in items}

    def width():
        return sum(est_width(it["copy"], sizes[it["ref"]]) for it in items) + ROW_GAP * (len(items) - 1)

    guard = 0
    while width() > box["inner_w"] and guard < 80:
        guard += 1
        if not _shrink(sizes, items):
            return None
    if width() > box["inner_w"]:
        return None
    guard = 0
    while est_height(1, max(sizes.values())) > box["inner_h"] and guard < 80:
        guard += 1
        if not _shrink(sizes, items):
            return None
    if est_height(1, max(sizes.values())) > box["inner_h"]:
        return None
    return {"structure": "row", "rows": [[it["ref"] for it in items]],
            "fonts": sizes, "align": MERGE_ALIGN, "itemMargin": ROW_GAP}


def _fit_merged(items: list, box: dict):
    """合并：多项合成一条 Text（规范分隔符）。"""
    g = GUARDS["merged"]
    if not (g["min_items"] <= len(items) <= g["max_items"]):
        return None
    text = MERGE_SEP.join(it["copy"] for it in items)
    base = max(it["base_size"] for it in items)
    floor = max(_floor(it) for it in items)
    for s in _options(base, floor):
        if est_width(text, s) <= box["inner_w"] and est_height(1, s) <= box["inner_h"]:
            return {"structure": "merged", "rows": [[it["ref"] for it in items]],
                    "fonts": {it["ref"]: s for it in items}, "merged_copy": text,
                    "align": "start"}
    return None


def _fit_board(items: list, box: dict):
    """业务小背板：第一行一项（对象名+主值），第二行其余 ≤2 项（` | ` 连接）。

    发射期会再拼接对象名前缀并做最终宽度兜底（见 P7 _zone_children）。"""
    g = GUARDS["board_rows"]
    first = items[0]
    rest = items[1:1 + g["max_items_line2"]]
    dropped = [it["ref"] for it in items[1 + g["max_items_line2"]:]]
    line2 = LINE_SEP.join(it["copy"] for it in rest) if rest else None
    for s0 in _options(first["base_size"], _floor(first)):
        if est_width(first["copy"], s0) > box["inner_w"]:
            continue
        if not rest:
            if est_height(1, s0) <= box["inner_h"]:
                return {"structure": "stack", "rows": [[first["ref"]]],
                        "fonts": {first["ref"]: s0}, "dropped": dropped, "align": "start"}
            continue
        # 第二行字号上限取第二行条目自身（金标：第一行 14/700、第二行 12/400）
        for s1 in _options(max(it["base_size"] for it in rest), max(_floor(it) for it in rest)):
            if est_width(line2, s1) > box["inner_w"]:
                continue
            if est_height(1, s0) + LINE_GAP + est_height(1, s1) <= box["inner_h"]:
                fonts = {first["ref"]: s0}
                for it in rest:
                    fonts[it["ref"]] = s1
                return {"structure": "stack",
                        "rows": [[first["ref"]], [it["ref"] for it in rest]],
                        "fonts": fonts, "dropped": dropped, "align": "start"}
    return None


def _fit_drop_should(items: list, box: dict):
    """省略：丢弃 keep=should 的条目后重新纵排（must 永不可丢）。"""
    kept = [it for it in items if it["keep"] != "should"]
    dropped = [it["ref"] for it in items if it["keep"] == "should"]
    if not dropped or not kept:
        return None
    res = _fit_stack(kept, box)
    if res is None:
        return None
    res["dropped"] = dropped
    res["dropped_reason"] = "keep=should"
    return res


def _fit_truncate(items: list, box: dict):
    """链尾兜底（T7）：按内高定行数上限，取最大可行字号并语义截断，必有解。"""
    max_rows = max(1, int(box["inner_h"] // est_height(1, min(LINE_LADDER))))
    kept, overflow = items[:max_rows], items[max_rows:]
    sizes, truncated = {}, {}
    for it in kept:
        opts = _options(it["base_size"], _floor(it))
        pick = next((s for s in opts if est_width(it["copy"], s) <= box["inner_w"]), opts[-1])
        sizes[it["ref"]] = pick
        if est_width(it["copy"], pick) > box["inner_w"]:
            truncated[it["ref"]] = semantic_truncate(it["copy"], box["inner_w"], pick)
    guard = 0
    while _total_height(sizes, kept, LINE_GAP) > box["inner_h"] and guard < 60:
        guard += 1
        if not _shrink(sizes, kept):
            break
    return {"structure": "stack", "rows": [[it["ref"]] for it in kept],
            "fonts": sizes, "truncated": truncated,
            "dropped": [it["ref"] for it in overflow], "align": "start"}


_DISPATCH = {"stack": None, "row": _fit_row, "merged": _fit_merged,
             "drop_should": _fit_drop_should, "truncate": _fit_truncate}


def adapt_slot(items: list, box: dict):
    """对固定几何槽位执行候选枚举与首个可行解；弹性槽位返回 None。

    items: [{"ref","role","type","copy","keep","base_size","order"}]
    box:   {"slot","inner_w","inner_h"}
    """
    if not items or box.get("inner_w") is None or box.get("inner_h") is None:
        return None
    kind = slot_kind(box)
    if kind == "flow":
        return None
    for name in V["candidates"][kind]:
        if name == "stack":
            res = _fit_board(items, box) if kind == "board" else _fit_stack(items, box)
        else:
            res = _DISPATCH[name](items, box)
        if res:
            res.setdefault("dropped", [])
            res.setdefault("truncated", {})
            res.update({"kind": kind, "candidate": name})
            note = f"capacity: {box['slot']} [{kind}] -> {name}"
            if res["dropped"]:
                note += f" (dropped {len(res['dropped'])})"
            if name == "truncate":
                note += " (链尾兜底)"
            res["log"] = [note]
            return res
    return None
