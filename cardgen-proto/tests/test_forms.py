"""排法表检查：`rules/content_forms.json` 与 `src/content_forms.py` 的对应关系。

把"新增排法要改哪两处"这条约定变成可执行断言：
  1. 表里的每个 id 都必须有实现，实现也必须都在表里（防止加了函数忘了登记，或反之）
  2. 最后一条必须是无条件兜底（否则某类槽位会选中空）
  3. when 里的键必须是已知的（拼错一个字母会静默变成"永远命中"）
  4. order 唯一且递增
  5. 需要几何的排法必须有 spec；环的几何确实来自 spec（改 JSON 就该变）
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import content_forms as forms      # noqa: E402
from src.M1_extract import MockLLM               # noqa: E402
from src.pipeline import generate         # noqa: E402

KNOWN_WHEN = {"slots", "has_layout_rows", "all_present", "exact_types",
              "min_items", "max_items", "all_have_label", "no_promoted_hero"}
ok = True


def case(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print(f"{'✅' if cond else '❌'} {name}" + (f"  {detail}" if detail and not cond else ""))


table_ids = [f["id"] for f in forms.TABLE]
case("表里每个排法都有实现", all(i in forms.EMITTERS for i in table_ids),
     str([i for i in table_ids if i not in forms.EMITTERS]))
case("每个实现都在表里（没有孤儿函数）",
     all(k in table_ids for k in forms.EMITTERS),
     str([k for k in forms.EMITTERS if k not in table_ids]))
case("最后一条是无条件兜底", not (forms.TABLE[-1].get("when") or {}), table_ids[-1])

unknown = sorted({k for f in forms.TABLE for k in (f.get("when") or {})} - KNOWN_WHEN)
case("when 里的键都是已知的", not unknown, str(unknown))

orders = [f["order"] for f in forms.TABLE]
case("order 唯一且递增", orders == sorted(set(orders)), str(orders))

case("需要几何的排法都有 spec",
     all(forms.SPECS.get(i) for i in ("ring_stat", "label_rows")),
     str({i: bool(forms.SPECS.get(i)) for i in ("ring_stat", "label_rows")}))

# 功能断言：环的几何真的来自 spec（改 JSON 就该变，否则说明又写死在代码里了）
saved = copy.deepcopy(forms.SPECS["ring_stat"])
try:
    forms.SPECS["ring_stat"]["ring"] = 60
    r = generate("看手机电量", MockLLM())
    comps = json.loads(r["full-a2ui"].splitlines()[1])["updateComponents"]["components"]
    arc = next(c for c in comps if c["component"] == "Progress")
    case("环的直径来自 spec（改成 60 立即生效）", arc["styles"]["width"] == 60,
         str(arc["styles"].get("width")))
    case("环的描边也来自 spec", arc["styles"]["strokeWidth"] == 6,
         str(arc["styles"].get("strokeWidth")))
finally:
    forms.SPECS["ring_stat"] = saved

print("\n== 排法表检查 %s ==" % ("通过" if ok else "失败"))
sys.exit(0 if ok else 1)
