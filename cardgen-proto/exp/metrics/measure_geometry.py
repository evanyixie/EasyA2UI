"""几何指标：把卡片真排版一遍，量越界与裁切，回填到 records.jsonl。

为什么不在流水线里跑：每张卡要起一次渲染器（几百毫秒），会拖慢生成；
而且四组产物一起量才公平，属于评测不属于生成。

用法：
    python exp/metrics/measure_geometry.py runs/L6
    python exp/metrics/measure_geometry.py runs/L6 --keep      # 保留中间 HTML（排查用）

依赖本机 Edge/Chrome 无头模式（与 tools/check_layout.py 同源，不引入 playwright）。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent   # cardgen-proto/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from gen_card_compare import card_html          # noqa: E402
from tools.check_layout import measure          # noqa: E402

NUM = re.compile(r"\d+")


def _empty_layout() -> dict:
    return {"overflow": 0, "overflow_px": 0, "overflow_max": 0, "clipped": 0, "edge_clip": 0,
            "min_font": None, "below_min_font": 0, "below_10fp": 0}


def _min_font(path: Path):
    """静态读字号：最小值 + 低于 12fp / 10fp 的节点数（口径 C-05 两条线）。"""
    fonts = []
    try:
        lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        comps = json.loads(lines[1])["updateComponents"]["components"]
    except Exception:  # noqa: BLE001
        return None, 0, 0
    for c in comps:
        st = c.get("styles") or {}
        if isinstance(st.get("fontSize"), (int, float)):
            fonts.append(st["fontSize"])
    if not fonts:
        return None, 0, 0
    return min(fonts), sum(1 for f in fonts if f < 12), sum(1 for f in fonts if f < 10)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    run = Path(args[0])
    records_path = run / "records.jsonl"
    cards_dir = run / "cards"
    if not records_path.exists() or not cards_dir.exists():
        print(f"缺少 {records_path} 或 {cards_dir}（先用 exp/runners/run_condition.py 跑一遍）")
        sys.exit(2)

    cards, layout_of = [], {}
    for f in sorted(cards_dir.glob("*.jsonl")):
        tag = f.stem
        body, (w, h) = card_html(f)
        cards.append((tag, body, w, h))
        layout_of[tag] = _empty_layout()
        mf, b12, b10 = _min_font(f)
        layout_of[tag]["min_font"] = mf
        layout_of[tag]["below_min_font"] = b12
        layout_of[tag]["below_10fp"] = b10

    issues = measure(cards)
    for i in issues:
        lay = layout_of.setdefault(i["tag"], _empty_layout())
        if i["kind"] == "overflow":
            pxs = [int(n) for n in NUM.findall(i["detail"])]
            lay["overflow"] += 1
            lay["overflow_px"] += sum(pxs)
            # 单节点最大越界像素（口径 C-04：≤4px 与金标同级，不计缺陷）
            lay["overflow_max"] = max(lay.get("overflow_max", 0), max(pxs) if pxs else 0)
        elif i["kind"] == "clipped-text":
            lay["clipped"] += 1
        elif i["kind"] == "edge-clip":
            lay["edge_clip"] += 1

    rows = [json.loads(l) for l in records_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        r["layout"] = layout_of.get(r["tag"], _empty_layout())
    with records_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_over = sum(1 for r in rows if r["layout"]["overflow"])
    n_clip = sum(1 for r in rows if r["layout"]["clipped"])
    print(f"几何：{len(rows)} 张卡，越界 {n_over} 张，明显裁切 {n_clip} 张"
          f"（已在 -- 检查器口径下测量）→ {records_path}")


if __name__ == "__main__":
    main()
