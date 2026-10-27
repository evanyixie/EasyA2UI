"""跑一个实验条件，产出一份 records.jsonl。

一个"条件"= 一次生成路径 + 一组运行选项。当前只支持已实现的路径：
    L4       原型现状（规则结构 + 程序装配），修正全开
    L4-NR    同上，但关掉入口/出口修正（RQ2 的“无补救”对照）

L1~L3 需要各自的 generate 路径（全包提示词 / 数值重算 / 模板库），
等论文侧实现后再挂到这里，不在这里造桩。

用法：
    python tools/run_condition.py L4 --out runs/L4
    python tools/run_condition.py L4-NR --out runs/L4-NR --mock
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.llm import MockLLM, build_llm                      # noqa: E402
from src.measure import build_record, write_records        # noqa: E402
from src.pipeline import generate                          # noqa: E402
from src.pipeline_options import PipelineOptions           # noqa: E402

CONDITIONS = {
    "L4": PipelineOptions(),
    "L4-NR": PipelineOptions(repair_plan=False, repair_card=False),
}


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args or args[0] not in CONDITIONS:
        print(f"用法：python tools/run_condition.py <{'|'.join(CONDITIONS)}> --out <dir> [--mock]")
        sys.exit(2)
    cond = args[0]
    options = CONDITIONS[cond]
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else ROOT / "runs" / cond
    out.mkdir(parents=True, exist_ok=True)

    llm = MockLLM() if "--mock" in sys.argv else build_llm()
    queries = json.loads((ROOT / "fixtures" / "batch_queries.json").read_text(encoding="utf-8"))

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
