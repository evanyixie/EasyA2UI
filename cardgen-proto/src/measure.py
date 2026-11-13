"""一次生成 = 一行记录：把度量字段拍平成可直接出表的形态。

设计约束（写在论文 §4.1）：
  1. 只记录**产物与计数**，不记录中间状态，四组才能用同一把尺子；
  2. 字段固定，缺什么就写 None / 空 dict，不臆造默认值；
  3. 几何（layout）与内容（content）由外部测量后回填，本模块只负责拼装。

用法：
    from src.measure import build_record, write_records
    rec = build_record("q01", "L6", query, result)
    rec["layout"] = {...}   # 由 exp/metrics/measure_geometry.py 回填
    rec["content"] = {...}  # 由 exp/metrics/measure_content.py 回填
"""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

SURFACE_RE = re.compile(r"sfc-[0-9a-f]{8}")
PLACEHOLDER_SURFACE = "sfc-FIXED"


def normalize_surface(text: str) -> str:
    """surfaceId 每次随机生成，比对前先抹平，否则一致性判断永远为假。"""
    return SURFACE_RE.sub(PLACEHOLDER_SURFACE, text or "")


def fingerprint(full_a2ui: str) -> str:
    """产物指纹：用于“同 query 重采样是否逐字相同”。不含随机 surfaceId。"""
    body = normalize_surface(full_a2ui)
    return "sha1:" + hashlib.sha1(body.encode("utf-8")).hexdigest()[:16]


def _components(full_a2ui: str) -> list:
    try:
        return json.loads(full_a2ui.splitlines()[1])["updateComponents"]["components"]
    except Exception:  # noqa: BLE001
        return []


def extract_text(full_a2ui: str) -> str:
    """卡面上所有文字，一行一个。内容类指标只吃这个，不看结构。"""
    return "\n".join(c.get("content") or "" for c in _components(full_a2ui)
                     if c.get("component") == "Text" and c.get("content"))


def static_metrics(full_a2ui: str) -> dict:
    """不需渲染就能量的静态指标（最小字号 / 组件数 / 文字条数）。

    字号报两条线（口径记录 C-05）：12fp 是 UX 规范线（判违规），
    10fp 是金标实测线（判"比金标还差"——金标自身存在 10fp 的卡）。
    """
    comps = _components(full_a2ui)
    fonts = [c["styles"]["fontSize"] for c in comps
             if isinstance(c.get("styles"), dict)
             and isinstance(c["styles"].get("fontSize"), (int, float))]
    texts = [c for c in comps if c.get("component") == "Text" and c.get("content")]
    return {"min_font": min(fonts) if fonts else None,
            "below_12fp": sum(1 for f in fonts if f < 12),
            "below_10fp": sum(1 for f in fonts if f < 10),
            "components": len(comps), "texts": len(texts)}


def build_record(tag: str, condition: str, query: str, result: dict,
                 layout: dict = None, content: dict = None) -> dict:
    """把一次 generate() 的结果拍成一行。字段顺序固定，方便 CSV 对齐。"""
    meta = result.get("meta") or {}
    ir = result.get("ir") or {}
    full = result.get("full-a2ui") or ""
    failed = bool(meta.get("failed"))
    # 口径记录 C-01：生成失败 = 不合格。记一条 generate.failed 违规，
    # 覆盖由 measure_content 按 0 计，保真不计入。不从分母剔除——
    # 剔除会让"经常失败的方案"因为分母小反而好看。
    codes = dict(meta.get("violation_codes") or {})
    if failed:
        codes["generate.failed"] = codes.get("generate.failed", 0) + 1
    return {
        "tag": tag,
        "condition": condition,
        "query": query,
        "failed": failed,
        "clean": (not failed) and not (meta.get("violations") or []),
        "violation_codes": codes,
        "violation_details": meta.get("violations") or [],
        "skeleton": ir.get("skeleton_id"),
        "size": ir.get("size"),
        "domain": ir.get("domain"),
        "theme": ir.get("theme"),
        "fallback_count": len(meta.get("fallback_log") or []),
        "timing": meta.get("timing") or {},
        "cost": meta.get("cost") or {},
        "options": meta.get("options") or {},
        "fingerprint": fingerprint(full),
        "static": static_metrics(full) if full else {},
        "card_text": extract_text(full),
        "layout": layout,
        "content": content,
    }


def write_records(path, records: list) -> None:
    """写 JSONL；一行一条记录，便于边跑边落盘（中途崩了也不丢已跑的部分）。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def flatten(rec: dict) -> dict:
    """把嵌套字段压成标量，供 CSV 导出（dict 转 k=v 串，列表转分号串）。"""
    out = {}
    for k, v in rec.items():
        if isinstance(v, dict):
            out[k] = ";".join(f"{kk}={vv}" for kk, vv in sorted(v.items()))
        elif isinstance(v, list):
            out[k] = ";".join(str(x) for x in v)
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# 内容指标（覆盖 / 保真 / 重复）
#
# 为什么放在产品区：它是"尺子"——谁都可以用它量一张卡，论文侧只是拿它跑批出表。
# 放在这里，删掉 exp/ 之后度量测试依然能跑通（架构检查会检查）。
# ---------------------------------------------------------------------------

_CONTENT_TOKEN_RE = re.compile(
    r"\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2}|\d{1,2}月\d{1,2}日|"
    r"\d{1,2}:\d{2}|"
    r"\d+(?:\.\d+)?\s*(?:%|℃|°C|°|天|小时|分钟|步|千卡|次|元|km|m|级)?")


def content_key(tag: str) -> str:
    """批次 tag 是 q01，基准键是 q1，统一到数字形态再查。"""
    m = re.search(r"(\d+)", str(tag))
    return f"q{int(m.group(1))}" if m else str(tag)


def _content_norm(s: str) -> str:
    """全角转半角、去空白、统一大小写——避免"68％"与"68%"被算成两个值。"""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s or ""))).lower()


def _content_contains(text_n: str, value: str) -> bool:
    """纯数字/带单位的值按边界匹配（68 不应命中 168）；其余按子串。"""
    v = _content_norm(value)
    if not v:
        return False
    if re.fullmatch(r"[\d.%℃°c天小时分钟步千卡次元]+", v):
        return re.search(r"(?<![\d.])" + re.escape(v) + r"(?![\d.])", text_n) is not None
    return v in text_n


def check_content(card_text: str, facts: list, query: str = "") -> dict:
    """返回一张卡的内容指标。facts 来自基准（[{key,value,path,must?}]）。

    口径（论文文档 §15）：C-02 覆盖拆两档（A4a 全部 / A4b 只对 must）；
    C-03 卡面没有任何数据型片段时保真记 None 并置 empty_data。
    """
    text_n = _content_norm(card_text)
    query_n = _content_norm(query)

    total = len(facts)
    missing = [f["value"] for f in facts if not _content_contains(text_n, f["value"])]
    covered = total - len(missing)

    must_facts = [f for f in facts if f.get("must")]
    if must_facts:
        must_total = len(must_facts)
        must_miss = [f["value"] for f in must_facts if not _content_contains(text_n, f["value"])]
        coverage_must = round((must_total - len(must_miss)) / must_total, 3)
    else:
        must_miss, coverage_must = [], None

    dup = 0
    for f in facts:
        v = _content_norm(f["value"])
        if v and text_n.count(v) >= 2:
            dup += 1

    tokens = {_content_norm(t) for t in _CONTENT_TOKEN_RE.findall(card_text or "")}
    tokens = {t for t in tokens if t}
    sources = [_content_norm(f["value"]) for f in facts] + ([query_n] if query_n else [])
    supported = [t for t in tokens
                 if any(_content_contains(s, t) or _content_contains(t, s) for s in sources)]
    unsupported = sorted(tokens - set(supported))

    return {
        "facts_total": total,
        "covered": covered,
        "coverage": round(covered / total, 3) if total else None,
        "coverage_must": coverage_must,
        "missing_must": must_miss,
        "missing": missing,
        "duplicated": dup,
        "tokens": len(tokens),
        "precision": round(len(supported) / len(tokens), 3) if tokens else None,
        "empty_data": not tokens,
        "unsupported": unsupported,
    }
