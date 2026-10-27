"""一次生成 = 一行记录：把度量字段拍平成可直接出表的形态。

设计约束（写在论文 §4.1）：
  1. 只记录**产物与计数**，不记录中间状态，四组才能用同一把尺子；
  2. 字段固定，缺什么就写 None / 空 dict，不臆造默认值；
  3. 几何（layout）与内容（content）由外部测量后回填，本模块只负责拼装。

用法：
    from src.measure import build_record, write_records
    rec = build_record("q01", "L4", query, result)
    rec["layout"] = {...}   # 由 tools/measure_geometry.py 回填
    rec["content"] = {...}  # 由 tools/measure_content.py 回填
"""
import hashlib
import json
import re
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
