"""流水线输出快照 / 等价性比对（重构安全网）。

用 MockLLM 跑固定的一批 query，把 `full-a2ui` 三行 JSONL 原样存下来。
重构编译器之后重跑一次，两份快照**必须一字不差**——这是"行为没变"的硬证据。

用法：
    python tools/snapshot_pipeline.py save  /tmp/snap_before.json
    python tools/snapshot_pipeline.py diff  /tmp/snap_before.json /tmp/snap_after.json
    python tools/snapshot_pipeline.py save  /tmp/snap.json --cases   # 只跑 fixtures/cases.json

退出码：diff 有差异 → 1（可直接当 CI 断言）。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.llm import MockLLM          # noqa: E402
from src.pipeline import generate    # noqa: E402


# 编译器路径探针：专门覆盖"内容区排法"的几条（MockLLM 有对应场景）
PROBES = [
    ("probe_ring", "看手机电量"),
    ("probe_ring_status", "看手机电量、是不是在充电"),
    ("probe_label_rows", "出门前看手机剩余电量、耳机仓电量和耳机是否连接"),
]


def queries(only_cases: bool) -> list:
    out = list(PROBES)
    cases = json.loads((ROOT / "fixtures" / "cases.json").read_text(encoding="utf-8"))
    out += [("case%02d" % c["id"], c["query"]) for c in cases]
    if not only_cases:
        batch = json.loads((ROOT / "fixtures" / "batch_queries.json").read_text(encoding="utf-8"))
        out += [(q["tag"], q["query"]) for q in batch]
    return out


SURFACE = re.compile(r"sfc-[0-9a-f]{8}")


def _normalize(text: str) -> str:
    """surfaceId 每次随机生成，必须先抹平，否则等价性比对永远全红。"""
    return SURFACE.sub("sfc-FIXED", text)


def snap(only_cases: bool) -> dict:
    llm = MockLLM()          # 确定性桩模型：同样的 query 必须得到同样的计划
    data = {}
    for tag, q in queries(only_cases):
        r = generate(q, llm)
        data[tag] = {
            "skeleton": r["ir"]["skeleton_id"],
            "size": r["ir"]["size"],
            "theme": r["ir"]["theme"],
            "a2ui": _normalize(r["full-a2ui"]),
        }
    return data


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "save"
    only_cases = "--cases" in sys.argv

    if mode == "save":
        out = Path(sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--")
                   else "/tmp/snap.json")
        data = snap(only_cases)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"快照已写出：{out}（{len(data)} 条）")
        return

    if mode == "diff":
        a = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        b = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        bad = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                bad.append((k, "只在一侧存在"))
            elif a[k] != b[k]:
                fields = [f for f in a[k] if a[k][f] != b[k].get(f)]
                bad.append((k, "字段不同: " + ", ".join(fields)))
        print(f"比对 {len(a)} vs {len(b)} 条：{'✅ 完全一致' if not bad else f'❌ {len(bad)} 条不同'}")
        for k, why in bad[:10]:
            print(f"  - {k}: {why}")
        sys.exit(0 if not bad else 1)

    print("用法：save <out> | diff <a> <b> [--cases]")
    sys.exit(2)


if __name__ == "__main__":
    main()
