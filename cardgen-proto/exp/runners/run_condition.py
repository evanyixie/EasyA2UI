"""跑一个实验条件，产出一份 records.jsonl。

一个"条件"= 一次生成路径 + 一组运行选项。当前只支持已实现的路径：
    L6       原型现状（仅内容归模型，结构/几何/主题/发射由程序），修正全开
    L6-NR    同上，但关掉入口/出口修正（RQ2 的"无补救"对照）

L1~L5、L5b 需要各自的生成路径（一次全包 / 五段串联 / 数值重算 / 模板库），
等各阶段实现落地后再挂到这里，不在这里造桩。

用法：
    python exp/runners/run_condition.py L6 --out runs/L6
    python exp/runners/run_condition.py L6-NR --out runs/L6-NR --mock
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent   # cardgen-proto/
sys.path.insert(0, str(ROOT))

from src.M1_extract import MockLLM, build_llm                      # noqa: E402
from src.measure import build_record, write_records        # noqa: E402
from src.pipeline import generate                          # noqa: E402
from src.pipeline_options import PipelineOptions           # noqa: E402
from exp.conditions import CONDITIONS as CONDITION_TABLE, REPAIR_CONDITIONS  # noqa: E402

# 注意：这不是六档条件表。条件表在 exp/conditions.py（唯一事实源），
# 这里只是"每个条件对应的运行选项"——选项是另一个维度，不属于条件定义。
RUN_OPTIONS = {
    "L6": PipelineOptions(),
    "L6-NR": PipelineOptions(repair_plan=False, repair_card=False),
}


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    known = set(CONDITION_TABLE) | set(REPAIR_CONDITIONS)
    if not args or args[0] not in known:
        print(f"用法：python exp/runners/run_condition.py <条件> --out <dir> [--mock]")
        print(f"条件表里已声明：{'、'.join(sorted(known))}")
        sys.exit(2)
    cond = args[0]
    if cond not in RUN_OPTIONS:
        # 已声明但还没实现：不造桩，明确拒绝
        print(f"{cond} 已在条件表声明，但生成路径尚未实现（L1~L5、L5b 待落地）。")
        sys.exit(3)
    options = RUN_OPTIONS[cond]
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else ROOT / "runs" / cond
    out.mkdir(parents=True, exist_ok=True)

    llm = MockLLM() if "--mock" in sys.argv else build_llm()
    queries = json.loads((ROOT / "data" / "queries.json").read_text(encoding="utf-8"))

    records = []
    cards_dir = out / "cards"
    cards_dir.mkdir(exist_ok=True)
    started = time.time()
    for q in queries:
        r = generate(q["query"], llm, options=options)
        records.append(build_record(q["tag"], cond, q["query"], r))
        # 落一份原始产物：几何测量要拿它重新排版，记录里只存了指纹和文字
        (cards_dir / f"{q['tag']}.jsonl").write_text(r["full-a2ui"] or "", encoding="utf-8")
        print(f"{q['tag']} {'✅' if records[-1]['clean'] else '⚠️'} "
              f"{records[-1]['skeleton']} {records[-1]['timing'].get('total_ms')}ms")

    path = out / "records.jsonl"
    path.unlink(missing_ok=True)
    write_records(path, records)
    ok = sum(1 for r in records if r["clean"])
    print(f"\n== {cond}：{len(records)} 条，协议干净 {ok} 条 → {path}（{time.time() - started:.0f}s）==")


if __name__ == "__main__":
    main()
