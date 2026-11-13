"""把各条件的 records.jsonl 汇总成一张表（论文表 1 / 表 3 的原料）。

每个条件一行，指标按论文 §4 的 A/B 组组织。缺失的测量写 "—"，不用 0 冒充。

"合格@x%"（口径记录 C-04）：协议合规 ∧ 覆盖 ≥ x ∧ 单节点越界 ≤ 4px。
覆盖优先用 A4b（必显）；oracle 未标注 must 时降级用 A4a，此时表里的
"合格"含义偏严（漏一条即掉档），跑 T09 标注后会自动切换。

用法：
    python exp/metrics/build_metrics_report.py runs/L6 runs/L6-NR
    python exp/metrics/build_metrics_report.py runs/*  --out runs/report.md
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent   # cardgen-proto/
sys.path.insert(0, str(ROOT))


def _pct(x) -> str:
    return "—" if x is None else f"{x * 100:.0f}%"


def _num(x) -> str:
    return "—" if x is None else str(x)


def _pctile(values, q):
    if not values:
        return None
    values = sorted(values)
    idx = min(len(values) - 1, max(0, int(round((len(values) - 1) * q))))
    return values[idx]


def _qualified(r: dict, threshold: float) -> bool:
    """口径记录 C-04：合格卡 = 协议合规 ∧ 必显覆盖 ≥ 阈值 ∧ 单节点越界 ≤ 4px。

    覆盖取 A4b（必显）；oracle 尚未标注 must 时降级用 A4a，
    降级会在表头标注。生成失败的卡恒为不合格（C-01）。
    """
    if r.get("failed") or not r.get("clean"):
        return False
    con = r.get("content") or {}
    cov = con.get("coverage_must")
    if cov is None:
        cov = con.get("coverage")
    if cov is None or cov < threshold:
        return False
    lay = r.get("layout") or {}
    if (lay.get("overflow_max") or 0) > 4:
        return False
    return True


def summarize(cond: str, rows: list) -> dict:
    n = len(rows)
    clean = sum(1 for r in rows if r.get("clean"))
    failed = sum(1 for r in rows if r.get("failed"))

    lay = [r["layout"] for r in rows if r.get("layout")]
    over = sum(1 for l in lay if l.get("overflow"))
    clip = sum(1 for l in lay if l.get("clipped"))
    fonts = [l["min_font"] for l in lay if l.get("min_font") is not None]
    below = sum(l.get("below_min_font", 0) for l in lay)
    below10 = sum(l.get("below_10fp", 0) for l in lay)

    con = [r["content"] for r in rows if r.get("content") and r["content"].get("coverage") is not None]
    cov = round(sum(c["coverage"] for c in con) / len(con), 3) if con else None
    cov_must = [c["coverage_must"] for c in con if c.get("coverage_must") is not None]
    cov_m = round(sum(cov_must) / len(cov_must), 3) if cov_must else None
    prec = [c["precision"] for c in con if c.get("precision") is not None]
    missing = sum(len(c.get("missing") or []) for c in con)
    dup = sum(c.get("duplicated") or 0 for c in con)
    empty = sum(1 for r in rows if (r.get("content") or {}).get("empty_data"))

    totals = [r["timing"]["total_ms"] for r in rows if r.get("timing", {}).get("total_ms")]
    models = [r["timing"]["model_ms"] for r in rows if r.get("timing", {}).get("model_ms")]
    calls = sum((r.get("cost") or {}).get("calls") or 0 for r in rows)
    tokens_in = [r["cost"]["in_tokens"] for r in rows if (r.get("cost") or {}).get("in_tokens")]
    tokens_out = [r["cost"]["out_tokens"] for r in rows if (r.get("cost") or {}).get("out_tokens")]

    def q(k):
        return _pct(round(sum(1 for r in rows if _qualified(r, k)) / n, 3) if n else None)

    return {
        "条件": cond,
        "条数": n,
        "失败": failed,
        "A1 协议干净": _pct(clean / n if n else None),
        "A2 越界卡": f"{over}" if lay else "—",
        "A2 裁切卡": f"{clip}" if lay else "—",
        "A3 最小字号": _num(min(fonts) if fonts else None),
        "A3 低于12fp节点": below if lay else "—",
        "A3 低于10fp节点": below10 if lay else "—",
        "A4 覆盖": _pct(cov),
        "A4b 必显覆盖": _pct(cov_m),
        "A5 保真": _pct(round(sum(prec) / len(prec), 3) if prec else None),
        "A5 空数据卡": empty if con else "—",
        "A4 漏条数": missing if con else "—",
        "A6 重复值": dup if con else "—",
        "合格@60%": q(0.6),
        "合格@80%": q(0.8),
        "合格@100%": q(1.0),
        "B1 时延P50": _num(_pctile(totals, 0.5)),
        "B1 时延P95": _num(_pctile(totals, 0.95)),
        "B1 模型耗时P50": _num(_pctile(models, 0.5)),
        "B2 调用次数": calls,
        "B3 输入token": sum(tokens_in) if tokens_in else "—",
        "B3 输出token": sum(tokens_out) if tokens_out else "—",
    }


def to_markdown(rows: list) -> str:
    if not rows:
        return "（没有数据）"
    cols = list(rows[0])
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def main() -> None:
    dirs = [Path(a) for a in sys.argv[1:] if not a.startswith("--")]
    if not dirs:
        print(__doc__)
        sys.exit(2)
    rows = []
    for d in dirs:
        p = d / "records.jsonl" if d.is_dir() else d
        if not p.exists():
            print(f"跳过（没有 records.jsonl）：{d}")
            continue
        recs = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        rows.append(summarize(d.name if d.is_dir() else p.stem, recs))

    md = to_markdown(rows)
    print(md)
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md + "\n", encoding="utf-8")
        print(f"\n→ {out}")


if __name__ == "__main__":
    main()
