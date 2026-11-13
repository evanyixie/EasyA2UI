# -*- coding: utf-8 -*-
"""真实数据集冒烟（防止"换了测试用例就裸奔"）。

`data/queries.json` 由 `tools/gold_dataset.py` 从 CreateMyCard
人工校验数据生成（49 条真实 userQuery）。这些 query 是**面向真实模型**的：
离线 MockLLM 是封闭域桩模型，语义必然对不上，因此本测试**不断言 fallback 数**，
只断言"管线不崩、协议不破、数据集完整"——这是换数据集后最低限度的安全网。
语义质量用真实模型跑 `tools/batch_generate.py`；结构质量用
`python tools/gold_dataset.py check`（金标结构核验）。

运行：python tests/test_gold_queries.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from src.M1_extract import MockLLM                      # noqa: E402
from src.pipeline import generate                # noqa: E402
from tests.run_cases import check_full_a2ui      # noqa: E402

QUERIES = ROOT / "data" / "queries.json"
GOLD = ROOT / "data" / "gold_pairs.json"
REPORT = []


def case(name, ok, detail=""):
    REPORT.append((name, ok, detail))
    print(f"{'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail else ""))


def main():
    queries = json.loads(QUERIES.read_text(encoding="utf-8"))
    gold = json.loads(GOLD.read_text(encoding="utf-8"))

    case("数据集：批次清单 49 条", len(queries) == 49, f"实际 {len(queries)}")
    case("数据集：query 全部唯一",
         len({q["query"] for q in queries}) == len(queries))
    case("数据集：每条都带金标尺寸",
         all(q.get("size") in ("2x2", "2x4") for q in queries))
    case("数据集：gold_pairs 与清单一一对应",
         gold["count"] == len(queries) == len(gold["pairs"]),
         f"gold={gold['count']} 清单={len(queries)}")
    unclassified = [p["id"] for p in gold["pairs"] if p["gold"]["skeleton"] == "?"]
    case("数据集：金标骨架全部归属本项目骨架集合", not unclassified,
         f"未归类 {unclassified}" if unclassified else f"{len(gold['pairs'])} 张全部归类")

    # 样本值关键词：必须**最长匹配**（顺序无关），否则 "剩余电量" 会被 "剩余" 抢走 → 30天
    from src.sample_values import infer_sample
    samples = {"剩余电量": "68%", "耳机仓电量": "80%", "耳机是否连接": "已连接",
               "电池温度": "29.0 ℃", "睡眠得分": "82分", "剩余天数": "30天",
               "空气质量": "良", "当前温度": "29°", "充电状态": "未充电"}
    wrong = {k: (v, infer_sample(k)) for k, v in samples.items() if infer_sample(k) != v}
    case("样本值：关键词最长匹配（顺序无关）", not wrong,
         f"错误 {wrong}" if wrong else f"{len(samples)} 条真实字段名全部命中预期值")

    llm = MockLLM()
    errs, fallbacks, skels = [], 0, {}
    for q in queries:
        try:
            r = generate(q["query"], llm, size=q.get("size"))
        except Exception as e:  # noqa: BLE001
            errs.append(f"{q['tag']}: {type(e).__name__}: {e}")
            continue
        ir = r["ir"]
        skels[ir["skeleton_id"]] = skels.get(ir["skeleton_id"], 0) + 1
        fallbacks += bool(r["meta"]["fallback_log"])
        bad = check_full_a2ui(r["full-a2ui"], ir["surface_id"], ir["size"])
        if bad:
            errs.append(f"{q['tag']}: {bad}")
    case("真实 query × MockLLM：零异常零协议违规", not errs,
         f"{len(errs)} 处，例：{errs[:2]}" if errs else f"{len(queries)} 条全通过；fallback {fallbacks} 条（MockLLM 语义不匹配，属预期）")
    print("   骨架分布:", json.dumps(skels, ensure_ascii=False))

    bad = [r for r in REPORT if not r[1]]
    print(f"\n== 真实数据集冒烟：{len(REPORT) - len(bad)}/{len(REPORT)} 通过 ==")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
