"""稳定性：同一句 query 重复采样 N 次，看每个字段是否稳定。

回答的是"确定性"这一主张，不是"质量"。统计口径用**全一致率**
（N 次取值完全相同才算稳定）——N=10 时个别低频变体会漏采样，
所以只报"全一致"这个二值量，报均值会被小样本骗。

用法：
    python tools/resample_stability.py --n 10 --temperature 1.0
    python tools/resample_stability.py --n 10 --mock         # 链路自检，无网络

产出：runs/stability/stability.json + 控制台摘要
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.llm import MockLLM, build_llm                    # noqa: E402
from src.measure import fingerprint                       # noqa: E402
from src.pipeline import generate                         # noqa: E402

FIELDS = ("domain", "size", "theme", "n_info", "types", "entries", "n_act", "action_types")


def canonical(plan: dict) -> dict:
    """把 M1 的计划压成可比较的字段值；ref 顺序抖动不算变化。"""
    items = plan.get("info_items") or []
    acts = plan.get("actions") or []
    return {
        "domain": plan.get("domain"),
        "size": plan.get("size"),
        "theme": plan.get("theme"),
        "n_info": len(items),
        "types": sorted(str(i.get("type")) for i in items),
        "entries": sorted(f"{i.get('type')}|{i.get('content_hint')}" for i in items),
        "n_act": len(acts),
        "action_types": sorted(str(a.get("type")) for a in acts),
    }


def main() -> None:
    def arg(name, default):
        return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

    n = int(arg("--n", 10))
    temperature = float(arg("--temperature", 1.0))
    llm = MockLLM() if "--mock" in sys.argv else build_llm()
    if hasattr(llm, "temperature") and "--mock" not in sys.argv:
        llm.temperature = temperature

    queries = json.loads((ROOT / "fixtures" / "batch_queries.json").read_text(encoding="utf-8"))
    stats0 = llm.stats() if hasattr(llm, "stats") else {}

    details = []
    for q in queries:
        plans, prints = [], []
        for _ in range(n):
            r = generate(q["query"], llm, debug=True)
            raw = next((t["output"]["json"] for t in r["trace"] if t["step"] == "M1"), {})
            plans.append(canonical(raw))
            prints.append(fingerprint(r["full-a2ui"] or ""))
        agree = {f: len({json.dumps(p[f], ensure_ascii=False) for p in plans}) == 1 for f in FIELDS}
        details.append({"tag": q["tag"], "agree": agree,
                        "artifact_all_agree": len(set(prints)) == 1})

    fields = {f: {"all_agree": round(sum(d["agree"][f] for d in details) / len(details), 3)}
              for f in FIELDS}
    artifact = round(sum(d["artifact_all_agree"] for d in details) / len(details), 3)

    cost = (llm.stats()["calls"] - stats0.get("calls", 0)) if stats0 else None
    out = {"n": n, "temperature": temperature, "queries": len(details),
           "fields": fields, "artifact_all_agree": artifact, "calls": cost,
           "details": details}
    path = ROOT / "runs" / "stability" / "stability.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"重采样 {n} 次 × {len(details)} 条（温度 {temperature}）：")
    for f, v in fields.items():
        print(f"  {f:<14} 全一致率 {v['all_agree']:.0%}")
    print(f"  产物逐字一致   {artifact:.0%}")
    print(f"→ {path}")


if __name__ == "__main__":
    main()
