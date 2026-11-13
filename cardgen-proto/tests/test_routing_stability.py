"""路由稳定性检查：显示字段不得改变骨架选择。

背景（2026-10-19）：标题兜底曾放在 P1，补出来的标题让 `n_info` 从 2 变 3，
2 条内容的卡被改判成 S5，**环卡因此丢掉环**。根因不是那次放错位置，
而是路由特征把"标题"当成了内容条目。本测试把这条不变量钉死：

  1. 同一计划，去掉/加回标题（含清理悬挂引用）→ 骨架必须一致
  2. percent 不计入 hero（否则单百分比卡会进 S1、丢掉环）
  3. 单百分比卡永远不会被路由到 S1

任何一条挂了，说明又有人让"显示字段"参与了布局决策。
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import P2_skeleton_route  # noqa: E402
from src.M1_extract import MockLLM               # noqa: E402
from src.pipeline import generate         # noqa: E402

ok = True


def case(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print(f"{'✅' if cond else '❌'} {name}" + (f"  {detail}" if detail and not cond else ""))


def plans() -> list:
    queries = [q["query"] for q in
               json.loads((ROOT / "data" / "queries.json").read_text(encoding="utf-8"))]
    queries += ["看手机电量", "看手机电量、是不是在充电", "出门前看手机剩余电量、耳机仓电量和耳机是否连接"]
    llm = MockLLM()
    out = []
    for q in queries:
        r = generate(q, llm, debug=True)
        out.append(copy.deepcopy(next(t["output"] for t in r["trace"] if t["step"] == "P1")))
    return out


P = plans()

# 1) 标题有无不影响骨架（去标题时同步清掉 objects 里的悬挂引用）
bad = []
for p in P:
    titles = {e["ref"] for e in p["entries"] if e["type"] == "title"}
    if not titles:
        continue
    stripped = copy.deepcopy(p)
    stripped["entries"] = [e for e in stripped["entries"] if e["type"] != "title"]
    for o in stripped["objects"]:
        o["fields"] = [f for f in o["fields"] if f not in titles]
    if P2_skeleton_route.select_skeleton(stripped)["sid"] != P2_skeleton_route.select_skeleton(copy.deepcopy(p))["sid"]:
        bad.append("?")
case("标题存在与否不改变骨架", not bad, f"{len(bad)}/{len(P)} 条会变")

# 2) percent 不属于 hero 类型；"纯百分比计划"（没有 stat/price/discount）不得被判 hero
pct_plans = [p for p in P if any(e["type"] == "percent" for e in p["entries"])]
case("percent 不属于 HERO_TYPES", "percent" not in P2_skeleton_route.HERO_TYPES)
synthetic = {"entries": [{"ref": 1, "kind": "info", "type": "title", "hint": "电量", "keep": "must"},
                         {"ref": 2, "kind": "info", "type": "percent", "hint": "剩余电量", "keep": "must"}],
             "objects": [{"name_hint": "电池", "fields": [2]}]}
case("纯百分比计划不算 hero", not P2_skeleton_route.derive_features(copy.deepcopy(synthetic))["hero"])

# 3) 单百分比卡不进 S1（S1 是居中单焦点，没有 content 槽，会丢环）
bad3 = [p for p in pct_plans
        if P2_skeleton_route.select_skeleton(copy.deepcopy(p))["sid"] == "S1-single-info"]
case("单百分比卡不会被路由到 S1", not bad3, f"{len(bad3)} 条")

print("\n== 路由稳定性 %s ==" % ("通过" if ok else "失败"))
print(f"（覆盖 {len(P)} 条计划，其中 {len(pct_plans)} 条含 percent）")
sys.exit(0 if ok else 1)
