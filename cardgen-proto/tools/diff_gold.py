# -*- coding: utf-8 -*-
"""逐卡元素级比对：我们的产物 vs 金标（qN.jsonl）。

比骨架 id 细一层——把两侧都归一成"可比特征"，逐项对照：
  · 画布/padding/itemMargin（含金标节点级 itemMargin 的归一）
  · 容器构成（Column/Row/Stack 数量）、Text/Image/Progress 数量
  · 字号字重多重集（Text 的 (fontSize, fontWeight)）
  · 对齐多重集（容器的 (alignItems, justifyContent)、Text 的 textAlign）
  · 数值高度多重集（固定高度的容器/行）
  · 可点组件类型（onClick 挂在 Button/Row/Stack）、标签值行数
  · 文本侧：我们的文案 vs 金标绑定表达式（金标是 {{...}}，只比"是不是绑定/长度档"）

用法（在 cardgen-proto/ 目录）：
    python tools/diff_gold.py                     # 最新一次 runs
    python tools/diff_gold.py <run_dir>           # 指定运行
    python tools/diff_gold.py <run_dir> q20       # 单卡元素明细（逐组件打印）
    python tools/diff_gold.py <run_dir> --top     # 只打全局聚类
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "gold"
DSL_DIR = DATA / "生成卡片的DSL结果"
sys.path.insert(0, str(ROOT))
from tools.gold_dataset import latest_run                          # noqa: E402
from tools.extract_skeletons_from_cards import get_components, load_messages, norm_id  # noqa: E402

BIND = re.compile(r"\{\{")


def _im(node):
    """itemMargin 归一：金标在节点级，我们在 styles 内。"""
    return node.get("itemMargin", (node.get("styles") or {}).get("itemMargin"))


def canon(components: list) -> dict:
    """一组组件（同一 surface 的 components 数组）→ 可比特征。"""
    containers = ("Column", "Row", "Stack", "List")
    f = {"canvas": None, "pad": None, "im": None,
         "n_container": 0, "n_text": 0, "n_image": 0, "n_progress": 0, "n_button": 0,
         "fonts": Counter(), "align": Counter(), "textalign": Counter(),
         "heights": Counter(), "widths": Counter(), "clicks": Counter(),
         "n_label_rows": 0, "n_stack40": 0, "radius": Counter(), "gradient": False}
    for c in components:
        st = c.get("styles") or {}
        comp = c.get("component")
        if c.get("id") == "root":
            f["canvas"] = (st.get("width"), st.get("height"))
            f["pad"] = st.get("padding")
            f["im"] = _im(c)
            f["gradient"] = bool(st.get("linearGradient"))
            f["radius"][st.get("borderRadius")] += 1
        if comp in containers:
            # 只统计"有视觉意义的容器"（有数值尺寸/弹性/padding/背景），
            # 纯透传包装层（金标有 1~2 层无样式 wrapper）不计入，避免噪声
            styled = any(k in st for k in ("height", "width", "layoutWeight", "padding",
                                           "backgroundColor", "alignItems", "justifyContent"))
            if styled:
                f["n_container"] += 1
                f["align"][(st.get("alignItems") or "start",
                            st.get("justifyContent") or "start")] += 1   # 缺省即 start
        elif comp == "Text":
            f["n_text"] += 1
            f["fonts"][(st.get("fontSize"), st.get("fontWeight"))] += 1
            f["textalign"][st.get("textAlign") or "start"] += 1   # 缺省即左对齐
        elif comp == "Image":
            f["n_image"] += 1
        elif comp == "Progress":
            f["n_progress"] += 1
        elif comp == "Button":
            f["n_button"] += 1
        h = st.get("height")          # 只比容器行高（金标的 Text 行高属实现细节）
        if isinstance(h, (int, float)) and comp in containers + ("Button",):
            f["heights"][h] += 1
        if comp == "Stack" and st.get("width") == 40 and st.get("height") == 40:
            f["n_stack40"] += 1
        if "onClick" in c:
            f["clicks"][comp] += 1
    # 标签值行：Row 里恰好 2 个 Text 子节点（label+value；金标有"同行紧排"与"左右分列"两种变体）
    by_id = {c.get("id"): c for c in components}
    for c in components:
        if c.get("component") != "Row":
            continue
        kids = [by_id.get(k) for k in (c.get("children") or [])]
        if len(kids) == 2 and all(k and k.get("component") == "Text" for k in kids):
            f["n_label_rows"] += 1
    return f


def our_features(path: Path) -> tuple:
    msgs = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    comps = msgs[1]["updateComponents"]["components"]
    return canon(comps), comps


def gold_features(n: int) -> tuple:
    msgs = load_messages(DSL_DIR / f"q{n}.jsonl")
    comps, root_id = get_components(msgs)
    order = list(comps.values())
    return canon(order), order


def _fmt(counter: Counter, limit=6) -> str:
    return "{" + ", ".join(f"{k}×{v}" for k, v in sorted(
        counter.items(), key=lambda kv: (-kv[1], str(kv[0])))[:limit]) + "}"


def diff_one(n: int, ours_path: Path, verbose=False) -> list:
    of, ocomps = our_features(ours_path)
    gf, gcomps = gold_features(n)
    diffs = []

    def d(key, label, og, gg, fmt=str):
        if og != gg:
            diffs.append((key, f"{label}: 金标 {fmt(gg)} ← 我们 {fmt(og)}"))

    d("canvas", "画布", of["canvas"], gf["canvas"])
    d("pad", "root padding", of["pad"], gf["pad"])
    d("im", "root itemMargin", of["im"], gf["im"])
    d("grad", "渐变", of["gradient"], gf["gradient"])
    d("n_container", "容器数", of["n_container"], gf["n_container"])
    d("n_text", "文本数", of["n_text"], gf["n_text"])
    d("n_image", "图标数", of["n_image"], gf["n_image"])
    d("n_progress", "进度环", of["n_progress"], gf["n_progress"])
    d("fonts", "字号字重", of["fonts"], gf["fonts"], _fmt)
    d("n_stack40", "40×40 圆钮", of["n_stack40"], gf["n_stack40"])
    d("align", "容器对齐", of["align"], gf["align"], _fmt)
    d("textalign", "文本对齐", of["textalign"], gf["textalign"], _fmt)
    d("heights", "固定高度", of["heights"], gf["heights"], _fmt)
    d("clicks", "可点组件", of["clicks"], gf["clicks"], _fmt)
    d("lvr", "标签值行", of["n_label_rows"], gf["n_label_rows"])

    if verbose:
        print(f"----- q{n:02d} 我们的组件 -----")
        for c in ocomps:
            st = c.get("styles") or {}
            keep = {k: st[k] for k in ("width", "height", "layoutWeight", "fontSize",
                                       "fontWeight", "textAlign", "alignItems",
                                       "justifyContent", "padding", "borderRadius",
                                       "backgroundColor") if k in st}
            print(f"  {c['id']:<26}{c['component']:<8}"
                  f"{json.dumps(keep, ensure_ascii=False)[:150]}"
                  f"  {str(c.get('content') or c.get('label') or '')[:24]}")
        print(f"----- q{n:02d} 金标组件 -----")
        for c in gcomps:
            st = c.get("styles") or {}
            keep = {k: st[k] for k in ("width", "height", "layoutWeight", "fontSize",
                                       "fontWeight", "textAlign", "alignItems",
                                       "justifyContent", "padding", "borderRadius",
                                       "backgroundColor") if k in st}
            if _im(c) is not None:
                keep["itemMargin"] = _im(c)
            print(f"  {norm_id(c['id']):<26}{c['component']:<8}"
                  f"{json.dumps(keep, ensure_ascii=False)[:150]}"
                  f"  {str(c.get('content') or c.get('label') or '')[:24]}")
    return diffs


def main():
    args = [a for a in sys.argv[1:]]
    top_only = "--top" in args
    args = [a for a in args if a != "--top"]
    # 参数是路径还是"用最新一次"？看它存不存在，别靠字符串前缀
    run_dir = Path(args[0]) if args and Path(args[0]).exists() else latest_run()
    only = args[1] if len(args) > 1 else None
    # run_dir 可能是相对路径
    if not run_dir.is_absolute():
        run_dir = ROOT / run_dir

    idx = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
    per_card, cluster, skipped = [], Counter(), []
    for e in idx["files"]:
        n = int(re.search(r"q(\d+)", e["tag"]).group(1))
        if only and e["tag"] != only:
            continue
        # 旧批跑里可能含已下线的卡（q28/q36/q37），金标不在就跳过，不要抛异常
        if not (DSL_DIR / f"q{n}.jsonl").exists():
            skipped.append(e["tag"])
            continue
        diffs = diff_one(n, run_dir / e["file"], verbose=bool(only))
        per_card.append((e["tag"], e["skeleton"], diffs))
        for k, _ in diffs:
            cluster[k] += 1

    print(f"\n===== {run_dir.name} × 金标：逐卡元素级差异 =====")
    if skipped:
        print(f"（跳过 {len(skipped)} 张：金标已下线 {skipped}）")
    if not top_only:
        for tag, skel, diffs in per_card:
            if not diffs:
                print(f"\n[{tag}] {skel}  ✅ 元素级完全一致")
                continue
            print(f"\n[{tag}] {skel}  ({len(diffs)} 项差异)")
            for _, line in diffs:
                print("    ·", line)
    print("\n===== 差异聚类（按卡数）=====")
    for k, c in cluster.most_common():
        tags = [t for t, _, d in per_card if any(kk == k for kk, _ in d)]
        print(f"  {c:>3} 张  {k:<12} ({', '.join(tags[:14])}{' …' if len(tags) > 14 else ''})")


if __name__ == "__main__":
    main()
