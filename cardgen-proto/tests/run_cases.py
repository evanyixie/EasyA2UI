"""批量跑 data/cases.json，输出原型验证报告。

指标（对应方案 §10）：
  主用例：意图正确 N/N、骨架路由正确 N/N、零 fallback N/N、A2UI 协议合规 N/N
  （case 8/9 分别覆盖新增骨架 S6 图标入口、S5 主辅二分）
  容量用例 7：标题组件非 C-102、copy 长度 <= C-101 容量(12)、无硬截断日志
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")  # Windows GBK 控制台也能正常显示中文

from src.pipeline import generate
from src.M1_extract import MockLLM
from src.P5_assemble import est_width
from src.validate import validate_a2ui

HEADER_SPEC = 12     # header_title 规格 fontSize
HEADER_WIDTH = 126   # 2x2 CardHeader 标题槽位宽（vp）
CAPSULE_MAX_CHARS = 6  # 2x2 胶囊按钮文案上限（UX-SPEC）


def check_full_a2ui(text: str, surface_id: str, size: str = "2x2") -> list:
    """协议合规检查。规则唯一事实源在 src/validate.py，这里只做“转成字符串”的适配。

    以前这 55 行规则住在本文件里，统计脚本量不到；迁到 src 后流水线与评测共用同一份。
    """
    return [f"{v.code}: {v.detail}" for v in validate_a2ui(text, surface_id, size)]


def count_label_rows(full_a2ui: str) -> int:
    """数「标签值行」：Row 里带 textAlign=end 的右对齐值 Text（金标 q20 类清单形态）。"""
    try:
        comps = json.loads(full_a2ui.splitlines()[1])["updateComponents"]["components"]
    except Exception:  # noqa: BLE001
        return -1
    return sum(1 for c in comps
               if c.get("component") == "Text" and c.get("styles", {}).get("textAlign") == "end")


def main():
    llm = MockLLM()
    cases = json.loads((ROOT / "data" / "cases.json").read_text(encoding="utf-8"))
    main_cases = [c for c in cases if not c.get("capacity_check")]
    cap_cases = [c for c in cases if c.get("capacity_check")]

    report, ok_intent, zero_fb, a2ui_ok, ok_skel = [], 0, 0, 0, 0
    for c in main_cases:
        r = generate(c["query"], llm)
        log = r["meta"]["fallback_log"]
        intent_ok = c["expect_intent"] is None or r["ir"]["intent"] == c["expect_intent"]
        ok_intent += intent_ok
        zero_fb += (not log)
        skel_ok = c.get("expect_skeleton") is None or r["ir"]["skeleton_id"] == c["expect_skeleton"]
        ok_skel += skel_ok
        full_errs = check_full_a2ui(r["full-a2ui"], r["ir"]["surface_id"])
        a2ui_ok += (not full_errs)
        rows = count_label_rows(r["full-a2ui"])
        rows_ok = c.get("expect_label_rows") is None or rows == c["expect_label_rows"]
        report.append({"id": c["id"], "query": c["query"], "intent": r["ir"]["intent"],
                       "domain": r["ir"]["domain"], "size": r["ir"]["size"],
                       "theme": r["ir"]["theme"],
                       "intent_ok": intent_ok, "skeleton": r["ir"]["skeleton_id"],
                       "skeleton_ok": skel_ok,
                       "label_rows": rows, "label_rows_ok": rows_ok,
                       "entries": len(r["ir"]["entries"]),
                       "a2ui_components": len(r["a2ui"]["components"]), "fallbacks": log,
                       "full_a2ui_errs": full_errs})
        if c.get("expect_label_rows") is not None and not rows_ok:
            print(f"❌ 用例 {c['id']} 标签值行 {rows} != 期望 {c['expect_label_rows']}")

    cap_report = []
    for c in cap_cases:
        r = generate(c["query"], llm)
        log = r["meta"]["fallback_log"]
        title = next(e for e in r["ir"]["entries"] if e["type"] == "title")
        checks = {
            "role_header_title": title["role"] == "header_title",
            "copy_within_width": est_width(title["copy"], HEADER_SPEC) * 1.2 <= HEADER_WIDTH,
            "no_hard_truncated": not any(x.startswith("capacity: hero") or
                                         x.startswith("capacity: truncated") for x in log),
        }
        cap_report.append({"id": c["id"], "query": c["query"],
                           "title_role": title["role"],
                           "title_copy": title["copy"], "checks": checks, "fallbacks": log})

    print(json.dumps({"main_cases": report, "capacity_cases": cap_report}, ensure_ascii=False, indent=2))
    n = len(report)
    lv = [r for r, c in zip(report, main_cases) if c.get("expect_label_rows") is not None]
    print("\n== 主用例 %d | 意图正确 %d/%d | 骨架正确 %d/%d | 零 fallback %d/%d | A2UI协议合规 %d/%d ==" % (
        n, ok_intent, n, ok_skel, n, zero_fb, n, a2ui_ok, n))
    if lv:
        print("== 形态断言 | 标签值行正确 %d/%d ==" % (
            sum(1 for r in lv if r["label_rows_ok"]), len(lv)))
    for cr in cap_report:
        passed = all(cr["checks"].values())
        print("== 容量用例 %d | 通过 %s | %s ==" % (
            cr["id"], "YES" if passed else "NO", json.dumps(cr["checks"], ensure_ascii=False)))


if __name__ == "__main__":
    main()
