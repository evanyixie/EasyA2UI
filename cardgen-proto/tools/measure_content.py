"""内容指标：漏了多少（覆盖）、编了多少（保真）、重复了几处。

输入是 `src.measure` 落下的记录（含 card_text），所以不用重跑模型；
基准来自 `fixtures/content_oracle.json`（金标抽出的应有事实集）。

用法：
    python tools/measure_content.py runs/L4/records.jsonl
    python tools/measure_content.py runs/L4/records.jsonl --out runs/L4/records.content.jsonl
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ORACLE = ROOT / "fixtures" / "content_oracle.json"

# 卡面上的“数据型片段”：带单位/百分号的数字、日期、时间
TOKEN_RE = re.compile(
    r"\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2}|\d{1,2}月\d{1,2}日|"
    r"\d{1,2}:\d{2}|"
    r"\d+(?:\.\d+)?\s*(?:%|℃|°C|°|天|小时|分钟|步|千卡|次|元|km|m|级)?")


def _key(tag: str) -> str:
    """批次 tag 是 q01，基准键是 q1，统一到数字形态再查。"""
    m = re.search(r"(\d+)", str(tag))
    return f"q{int(m.group(1))}" if m else str(tag)


def _norm(s: str) -> str:
    """全角转半角、去空白、统一大小写——避免“68％”与“68%”被算成两个值。"""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s or ""))).lower()


def _contains(text_n: str, value: str) -> bool:
    """纯数字/带单位的值按边界匹配（68 不应命中 168）；其余按子串。"""
    v = _norm(value)
    if not v:
        return False
    if re.fullmatch(r"[\d.%℃°c天小时分钟步千卡次元]+", v):
        return re.search(r"(?<![\d.])" + re.escape(v) + r"(?![\d.])", text_n) is not None
    return v in text_n


def check(card_text: str, facts: list, query: str = "") -> dict:
    """返回一张卡的内容指标。facts 来自 oracle（[{key,value,path,must?}]）。

    口径（论文文档 §15 口径记录）：
      C-02 覆盖拆两档——coverage 对全部事实（A4a），coverage_must 只对
           标了 must 的事实（A4b）。oracle 未标注 must 时 coverage_must 为
           None（不是 0），表示"这一档还没量"，不算分母。
      C-03 卡面没有任何数据型片段时 precision 记 None 并置 empty_data，
           单独报"空数据卡"数——记 100% 会让空卡刷满分，记 0 会冤枉合法形态。
    """
    text_n = _norm(card_text)
    query_n = _norm(query)

    total = len(facts)
    missing = [f["value"] for f in facts if not _contains(text_n, f["value"])]
    covered = total - len(missing)

    # A4b：只对人工标注 must 的事实算（T09 完成标注后生效）
    must_facts = [f for f in facts if f.get("must")]
    if must_facts:
        must_total = len(must_facts)
        must_miss = [f["value"] for f in must_facts if not _contains(text_n, f["value"])]
        coverage_must = round((must_total - len(must_miss)) / must_total, 3)
    else:
        must_miss, coverage_must = [], None

    # 重复：同一事实值在卡面出现 ≥2 次
    dup = 0
    for f in facts:
        v = _norm(f["value"])
        if v and text_n.count(v) >= 2:
            dup += 1

    # 保真：卡面上的数据型片段，能不能在基准或 query 里找到出处
    tokens = {_norm(t) for t in TOKEN_RE.findall(card_text or "")}
    tokens = {t for t in tokens if t}
    sources = [_norm(f["value"]) for f in facts] + ([query_n] if query_n else [])
    # 双向包含：卡面写 "68%"，基准是 68 → 也算有出处（单位是卡面加的，不是编的）
    supported = [t for t in tokens
                 if any(_contains(s, t) or _contains(t, s) for s in sources)]
    unsupported = sorted(tokens - set(supported))

    return {
        "facts_total": total,
        "covered": covered,
        "coverage": round(covered / total, 3) if total else None,
        "coverage_must": coverage_must,           # A4b，未标注时 None
        "missing_must": must_miss,
        "missing": missing,
        "duplicated": dup,
        "tokens": len(tokens),
        "precision": round(len(supported) / len(tokens), 3) if tokens else None,
        "empty_data": not tokens,                 # C-03：空数据卡单独计数
        "unsupported": unsupported,
    }


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
