"""内容指标：漏了多少（覆盖）、编了多少（保真）、重复了几处。

输入是 `src.measure` 落下的记录（含 card_text），所以不用重跑模型；
基准来自 `data/content_oracle.json`（金标抽出的应有事实集）。

用法：
    python exp/metrics/measure_content.py runs/L6/records.jsonl
    python exp/metrics/measure_content.py runs/L6/records.jsonl --out runs/L6/records.content.jsonl
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent   # cardgen-proto/
sys.path.insert(0, str(ROOT))

ORACLE = ROOT / "data" / "content_oracle.json"

from src.measure import check_content as check, content_key as _key  # noqa: E402

def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    src = Path(args[0])
    # 默认原地回填：内容与几何两把尺子都往同一份记录里写，避免多份副本走散
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else src

    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]

    for r in rows:
        facts = oracle.get(_key(r.get("tag")), [])
        if r.get("failed"):
            # 口径 C-01：失败卡 = 覆盖 0、保真不计入、缺全部事实
            r["content"] = {"facts_total": len(facts), "covered": 0, "coverage": 0.0,
                            "coverage_must": 0.0 if any(f.get("must") for f in facts) else None,
                            "missing": [f["value"] for f in facts], "missing_must": [],
                            "duplicated": 0, "tokens": 0, "precision": None,
                            "empty_data": True, "unsupported": []}
        else:
            r["content"] = check(r.get("card_text", ""), facts, r.get("query", ""))

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ok = [r for r in rows if r["content"]["coverage"] is not None]
    empty = sum(1 for r in rows if r["content"].get("empty_data"))
    if ok:
        cov = sum(r["content"]["coverage"] for r in ok) / len(ok)
        must = [r["content"]["coverage_must"] for r in ok
                if r["content"].get("coverage_must") is not None]
        prec = [r["content"]["precision"] for r in ok if r["content"]["precision"] is not None]
        tot_missing = sum(len(r["content"]["missing"]) for r in ok)
        print(f"内容指标：{len(ok)} 张卡，平均覆盖 {cov:.1%}，"
              f"漏掉事实 {tot_missing} 条，平均保真 {sum(prec) / len(prec):.1%}" if prec else "")
        if must:
            print(f"  必显覆盖（A4b）：{sum(must) / len(must):.1%}（已标注 must 的卡 {len(must)} 张）")
        if empty:
            print(f"  空数据卡：{empty} 张（保真不计入，单独计数）")
        worst = sorted(ok, key=lambda r: r["content"]["coverage"])[:5]
        for r in worst:
            print(f"  - {r['tag']}: 覆盖 {r['content']['coverage']:.0%}，缺 {r['content']['missing']}")
    print(f"已写出：{out}")


if __name__ == "__main__":
    main()
