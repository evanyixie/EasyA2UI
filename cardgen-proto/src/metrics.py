"""文字度量：压力宽度估算 / 行高估算 / 语义截断。

P5 容量预算与 P7 发射期合成的公共基础（v3 §7.5 / §8），单独成模块以避免
assemble 与 capacity 之间的循环依赖。

口径：
  宽度 —— 中文约 1em、字母数字约 0.65em、其他约 0.85em（压力预算，非真机排版）；
  行高 —— 1.4 × 字号（UX-SPEC「文本高度至少字号的 1.4 倍」同源）。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUDGET = json.loads((ROOT / "registry/ladders.json").read_text(encoding="utf-8"))["text_width_budget"]

LINE_HEIGHT_RATIO = 1.4


def est_width(text: str, font_size: float) -> float:
    """压力宽度估算。"""
    w = 0.0
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff" or "\u3000" <= ch <= "\u303f" or ch in "，。、；：！？…—·（）《》":
            w += font_size * BUDGET["cjk_em"]
        elif ch.isascii() and ch.isalnum():
            w += font_size * BUDGET["alnum_em"]
        else:
            w += font_size * BUDGET["other_em"]
    return w


def est_height(rows: int, font_size: float) -> float:
    """rows 行该字号文本的高度估算。"""
    return rows * font_size * LINE_HEIGHT_RATIO


def semantic_truncate(text: str, max_width: float, font_size: float) -> str:
    """按宽度预算截断：在标点/CJK 边界收刀并补省略号。"""
    if est_width(text, font_size) <= max_width:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if est_width(text[:mid] + "…", font_size) <= max_width:
            lo = mid
        else:
            hi = mid - 1
    cut = text[:lo].rstrip()
    for s in "，。、；：！？,.;:!?…—· ":
        pos = cut.rfind(s)
        if pos >= 2:
            cut = cut[:pos + 1]
            break
    return cut + "…"


_semantic_truncate = semantic_truncate  # 兼容旧调用名


# 主值（hero）可承载的最大字符数：hero 起点 38fp、2×2 安全区 126vp，
# 38fp 下最多容纳 ~3 个中文字（38×3=114≤126），4 字已需降档到 30。
# 超过 4 字的值不该当 hero——降到 20fp 仍超宽、只能截断（实测 7 张卡踩到），
# 应改落 status_lead（18/700，高 24，与金标 primary_main 的 16~18fp/h24 一致）。
HERO_MAX_CHARS = 4
