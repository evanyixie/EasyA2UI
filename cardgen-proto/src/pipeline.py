"""固定 workflow 编排：M1 → P1 → P2 → P3 → P4 → P5 → P6 主题装配 → P7 发射器。

在线链路唯一的模型调用是 M1；其余全部为程序环节。
未来改 Agent + skills 编排时，只需替换本文件，各步骤实现与 prompts 零改动。

debug=True 时返回 "trace"：逐环节的输入/输出记录，供调试器消费。
"""
import json
import time
from pathlib import Path

from . import normalize, skeletons, slot_assign, component_select, assemble, compiler, theme as theme_step
from .llm import LLMCallError, extract_json, stats_delta
from .pipeline_options import PipelineOptions, load_options
from .validate import validate_a2ui, count_by_code

ROOT = Path(__file__).resolve().parent.parent
ENUMS = json.loads((ROOT / "registry/enums.json").read_text(encoding="utf-8"))
LOG_PATH = ROOT / "logs" / "generate.jsonl"

EMPTY_PLAN = {"domain": "unknown", "intent": "info_card", "size": "auto", "theme": None,
              "info_items": [], "actions": [], "objects": [], "relations": [], "groups": []}


def _record(trace, step, kind, input_, output):
    if trace is not None:
        trace.append({"step": step, "kind": kind, "input": input_, "output": output})


def _write_request_log(record: dict) -> None:
    """追加一行请求级日志（logs/generate.jsonl），失败不影响主流程。"""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def generate(query: str, llm, debug: bool = False, size: str = None,
             options: PipelineOptions = None) -> dict:
    """生成一张卡。

    options 为空时按环境变量取默认（三个选项全开，与 v3.x 行为一致）。
    只有实验需要关掉修正/兜底时才显式传入——正常调用不需要关心它。
    """
    options = options or load_options()
    trace = [] if debug else None
    stats0 = llm.stats() if hasattr(llm, "stats") else None
    t0 = time.perf_counter()

    def _cost() -> dict:
        """一次生成消耗的模型资源。端点不给 token 时如实记 None，不估算。"""
        if stats0 is None or not hasattr(llm, "stats"):
            return {"calls": 1, "attempts": 1, "in_tokens": None,
                    "out_tokens": None, "usage_missing": 1}
        return stats_delta(stats0, llm.stats())

    # ---- M1 模型：结构规划（纯语义 + 对象分组 + 领域判断） ----
    tpl = (ROOT / "prompts/step1_structure_plan.md").read_text(encoding="utf-8")
    prompt = (tpl.replace("{{ENUMS}}", json.dumps(ENUMS, ensure_ascii=False))
                 .replace("{{QUERY}}", query))
    raw, parse_err = "", None
    started = time.time()
    try:
        raw = llm.complete(prompt)
        plan_raw = extract_json(raw)
    except LLMCallError as e:
        # 调用层失败：连接失败 / 读超时 / HTTP 错误（与输出解析失败区分）
        plan_raw = dict(EMPTY_PLAN)
        parse_err = f"M1 call fail: {e}"
    except Exception as e:
        plan_raw = dict(EMPTY_PLAN)
        parse_err = f"M1 parse fail: {e}"
    _record(trace, "M1", "模型",
            {"prompt": prompt, "query": query},
            {"raw": raw, "json": plan_raw, "parse_error": parse_err})
    t_m1 = time.perf_counter()

    # ---- P1~P7 程序 ----
    if size in ("2x2", "2x4"):
        plan_raw["size"] = size  # 用户/评测显式指定卡槽尺寸，优先于模型决策
    plan = normalize.normalize_plan(plan_raw, options)
    if parse_err:
        plan["fallback_log"].append(parse_err)
    if not plan["entries"]:
        if not options.placeholder_card:
            # 实验模式：不造占位卡，失败就是失败。调用方看 meta["failed"]。
            plan["fallback_log"].append("empty plan and placeholder_card disabled -> generation failed")
            t_fail = time.perf_counter()
            result = {"ir": None, "a2ui": None, "full-a2ui": "",
                      "meta": {"query": query, "fallback_log": plan["fallback_log"],
                               "failed": True, "violations": [], "violation_codes": {},
                               "timing": {"model_ms": round((t_m1 - t0) * 1000),
                                          "pipeline_ms": round((t_fail - t_m1) * 1000),
                                          "validate_ms": 0,
                                          "total_ms": round((t_fail - t0) * 1000)},
                               "cost": _cost(),
                               "options": options.describe()}}
            _record(trace, "P1", "程序", plan_raw, plan)
            _write_request_log({"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "query": query[:200],
                                "llm": type(llm).__name__,
                                "model": getattr(llm, "model", "mock"),
                                "m1_error": parse_err or "", "failed": True,
                                "fallback_log": plan["fallback_log"],
                                "timing": result["meta"]["timing"],
                                "cost": result["meta"]["cost"],
                                "options": options.describe(),
                                "duration_ms": int((time.time() - started) * 1000)})
            if trace is not None:
                result["trace"] = trace
            return result
        # 空计划兜底：任何输入都必须产出合法卡片（协议要求非空组件树）
        title_hint = (query or "").strip()[:12] or "未命名卡片"
        plan["entries"] = [
            {"ref": 1, "kind": "info", "type": "title", "hint": title_hint, "keep": "must"},
            {"ref": 2, "kind": "info", "type": "source", "hint": "暂无可展示的内容", "keep": "must"},
        ]
        plan["objects"] = [{"name_hint": "", "fields": [1, 2]}]
        plan["fallback_log"].append("M1 empty plan -> placeholder entries")
    _record(trace, "P1", "程序", plan_raw, plan)

    skel = skeletons.select_skeleton(plan)
    _record(trace, "P2", "程序", {k: plan[k] for k in ("domain", "size", "objects", "entries")}, skel)

    assign = slot_assign.assign_regions(plan, skel)
    _record(trace, "P3", "程序", {"plan": plan, "skeleton": skel["sid"]}, assign)

    slot_of = {}
    for slot, f in assign["fills"].items():
        for r in f["info"] + f["action"]:
            slot_of[r] = slot
    comp = component_select.select_roles(plan["entries"], slot_of=slot_of)
    _record(trace, "P4", "程序", plan["entries"], comp)

    ir = assemble.assemble_ir(plan, skel, assign, comp, plan_raw.get("intent"))
    _record(trace, "P5", "程序",
            {"plan": plan, "skeleton": skel["sid"], "assign": assign, "roles": comp,
             "m1_intent": plan_raw.get("intent")},
            ir)

    theme_step.apply_theme(ir, m1_theme=plan.get("theme"))
    _record(trace, "P6 主题装配", "程序",
            {"domain": ir["domain"], "m1_theme": plan.get("theme")},
            {"theme": ir["theme"], "palette": ir["palette"]})

    a2ui = compiler.compile_a2ui(ir)
    full_a2ui = compiler.compile_a2ui_full(ir)
    _record(trace, "P7 发射器", "程序",
            {"tree": ir["tree"], "entries": ir["entries"]},
            {"a2ui": a2ui, "full-a2ui": full_a2ui})
    t_pipe = time.perf_counter()

    # ---- 出口校验：只判不修，结果进 meta 与日志 ----
    # 校验是尺子，不是流水线阶段：出口修正（repair_card）要用它拿违规清单，
    # 评测与统计也直接调它量"没有修正时有多少违规"。所以它没有开关。
    violations = validate_a2ui(full_a2ui, ir["surface_id"], ir["size"])
    violation_dicts = [{"code": v.code, "where": v.where,
                        "detail": v.detail, "severity": v.severity} for v in violations]
    t_val = time.perf_counter()

    timing = {"model_ms": round((t_m1 - t0) * 1000),
              "pipeline_ms": round((t_pipe - t_m1) * 1000),
              "validate_ms": round((t_val - t_pipe) * 1000),
              "total_ms": round((t_val - t0) * 1000)}
    cost = _cost()

    result = {"ir": ir, "a2ui": a2ui, "full-a2ui": full_a2ui,
              "meta": {"query": query, "fallback_log": ir["fallback_log"],
                       "failed": False,
                       "violations": violation_dicts,
                       "violation_codes": count_by_code(violations),
                       "timing": timing, "cost": cost,
                       "options": options.describe()}}
    if trace is not None:
        result["trace"] = trace

    _write_request_log({"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": query[:200],
                        "llm": type(llm).__name__,
                        "model": getattr(llm, "model", "mock"),
                        "m1_error": parse_err or "",
                        "size": ir["size"], "skeleton": ir["skeleton_id"],
                        "domain": ir["domain"], "theme": ir["theme"],
                        "fallback_log": ir["fallback_log"],
                        "failed": False,
                        "violations": len(violations),
                        "violation_codes": count_by_code(violations),
                        "timing": timing, "cost": cost,
                        "options": options.describe(),
                        "duration_ms": int((time.time() - started) * 1000)})
    return result
