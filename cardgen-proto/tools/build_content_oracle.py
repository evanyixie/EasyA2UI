"""从金标产物抽“应有事实集”，作为内容指标的独立基准。

为什么不从被测系统的 plan 里取 mustKeep？
  —— L1 根本没有 plan；而且拿 L4 自己的输出当基准等于自评。
金标（人工校验过的终端产物）是唯一独立且可用的 oracle。

抽取规则（宁少勿滥，宁可漏掉一条也不要引入噪声）：
  · 只取字符串 / 数字叶子；布尔与 None 跳过（卡面显示的是“已连接”，不是 true）
  · 跳过名字里带 code / id / url / icon / color / type 的键（都是机器值，不上卡面）
  · 跳过长度 > 20 的字符串（通常是描述而非展示值）

用法：
    python tools/build_content_oracle.py            # 重新生成 fixtures/content_oracle.json
    python tools/build_content_oracle.py --check    # 只打印统计，不写文件
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "gold"
DSL = DATA / "生成卡片的DSL结果"
OUT = ROOT / "fixtures" / "content_oracle.json"

SKIP_KEY = re.compile(r"code|id|url|icon|color|type|unit|timestamp|ts$", re.I)
MAX_LEN = 20
# 复合值拆分：金标常写成“25℃ / 32℃”“周一，晴”，按分隔符拆成独立事实，
# 否则“卡面只显示了其中一个”会被算成整体命中。
SEP = re.compile(r"\s*(?:/|~|～|—|→|至|，|,)\s*")


def _walk(node, key_path, acc):
    if isinstance(node, dict):
        for k, v in node.items():
            _walk(v, key_path + [str(k)], acc)
        return
    if isinstance(node, list):
        for i, v in enumerate(node):
            _walk(v, key_path + [str(i)], acc)
        return
    if isinstance(node, bool) or node is None:
        return
    if not isinstance(node, (str, int, float)):
        return
    key = key_path[-1] if key_path else ""
    if SKIP_KEY.search(key):
        return
    text = str(node).strip()
    if not text or len(text) > MAX_LEN:
        return
    parts = [p for p in (x.strip() for x in SEP.split(text)) if p]
    if len(parts) > 1:
        for p in parts:
            acc.append({"path": ".".join(key_path), "key": key, "value": p})
        return
    acc.append({"path": ".".join(key_path), "key": key, "value": text})


def extract_one(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data[2]["updateDataModel"].get("value") or {}
    acc = []
    _walk(value, [], acc)
    # 去重：同一个值只算一条事实
    seen, out = set(), []
    for f in acc:
        if f["value"] in seen:
            continue
        seen.add(f["value"])
        out.append(f)
    return out


def main() -> None:
    check_only = "--check" in sys.argv
    oracle, stats = {}, []
    for f in sorted(DSL.glob("q*.jsonl"), key=lambda p: int(re.sub(r"\D", "", p.stem))):
        facts = extract_one(f)
        oracle[f.stem] = facts
        stats.append((f.stem, len(facts)))

    total = sum(n for _, n in stats)
    print(f"抽取完成：{len(oracle)} 张卡，共 {total} 条事实，平均 {total / max(1, len(oracle)):.1f} 条/卡")
    empty = [t for t, n in stats if n == 0]
    if empty:
        print(f"⚠️ 以下卡片没抽到事实（需人工看一下）：{', '.join(empty)}")
    print("抽取最少的 5 张：", ", ".join(f"{t}({n})" for t, n in sorted(stats, key=lambda x: x[1])[:5]))

    if check_only:
        print(json.dumps(oracle["q1"], ensure_ascii=False, indent=1)[:600])
        return

    OUT.write_text(json.dumps(oracle, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写出：{OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
