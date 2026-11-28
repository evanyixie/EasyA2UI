"""独立核对实际阶段记录、产物和共同合同。"""

import json
from pathlib import Path

import common_native
import contract_checks as contract
import layout_decisions as layout
import program_layout
import runtime
import shared_adapter as adapter
from evidence import digest, read, require, sha
from geometry_checks import geometry_gates

DIAGNOSTIC_EXCEPTIONS = (
    ValueError,
    TypeError,
    IndexError,
    KeyError,
    AttributeError,
    ArithmeticError,
    RecursionError,
)
GROUPS = {
    "source_facts_and_bindings": {
        "source_leaf",
        "expression",
        "ordered_binding_occurrences",
        "symbolic_path_change",
        "emitted_sample",
        "localized_support",
        "unregistered_text",
        "extra_visible_leaf",
        "static_text",
        "standalone_support",
        "selected_sample",
        "frozen_source_bindings",
        "unit_once",
        "support_action_caption",
        "visible_declaration",
    },
    "actions": {
        "button_caption",
        "handler_and_hit_scope",
        "unrequested_handlers",
        "action_scope",
    },
    "entities_and_roles": {
        "entity_evidence",
        "semantic_relation",
        "ordered_entities",
        "declared_entity_hierarchy",
        "unit_typography",
        "button_visual_owner",
    },
}


def unknown(exc):
    return {
        "static_status": "unresolved",
        "error_type": type(exc).__name__,
        "detail": str(exc),
        "checks": [],
        "complete_product_success": None,
    }


def examine(function, *args):
    try:
        return function(*args)
    except DIAGNOSTIC_EXCEPTIONS as exc:
        return unknown(exc)


def group_status(checks, dimensions):
    hits = [c["status"] for c in checks if c["dimension"] in dimensions]
    if "mismatch" in hits:
        return "mismatch"
    if "unknown" in hits:
        return "unresolved"
    return "verified" if "verified" in hits else "not_applicable"


def combined(statuses):
    if "mismatch" in statuses:
        return "mismatch"
    return "verified" if all(x == "verified" for x in statuses) else "unresolved"


def strict_geometry(messages, shared):
    try:
        issues = geometry_gates(messages, shared)
        return {"status": "mismatch" if issues else "verified", "issues": issues}
    except DIAGNOSTIC_EXCEPTIONS as exc:
        return {
            "status": "unresolved",
            "detail": str(exc),
            "error_type": type(exc).__name__,
        }


def check_pair_input(row, line_sha, home, shared_path):
    rec_path = home / "input_receipt.json"
    rec = read(rec_path)
    require(rec["source_row_sha256"] == line_sha, "源行与准备回执不一致")
    result = {
        "status": rec["status"],
        "source_row_sha256": line_sha,
        "receipt_sha256": sha(rec_path),
        "error_type": rec.get("error_type"),
        "detail": rec.get("detail"),
    }
    if rec["status"] == "adapter_rejected":
        require(not shared_path.exists(), "投影拒绝却存在共用投影")
        try:
            adapter.document(row)
        except DIAGNOSTIC_EXCEPTIONS as exc:
            require(
                type(exc).__name__ == rec["error_type"] and str(exc) == rec["detail"],
                "首次投影拒绝无法重现",
            )
            result["first_rejection_reproduced"] = True
            return result, None
        raise ValueError("已经拒绝的原投影被重新接受")
    require(rec["status"] in {"accepted", "reference_rejected"}, "未知的共用准备状态")
    require(rec.get("shared_sha256") == sha(shared_path), "共同投影字节不符")
    shared = read(shared_path)
    require(shared["task_id"] == row["task_id"], "投影编号不一")
    result["projection"] = examine(contract.check_projection, row, shared)
    result["shared_sha256"] = sha(shared_path)
    fresh = adapter.document(row)

    # 可移植版将缺图像资产的管理说明改成通用文案，两版共有的事实、偏好与判定仍逐字段比较。
    def projection_payload(document):
        return {
            **document,
            "preference_issues": [
                {k: v for k, v in issue.items() if k != "cause"}
                for issue in document["preference_issues"]
            ],
        }

    require(
        contract.canonical(projection_payload(fresh))
        == contract.canonical(projection_payload(shared)),
        "冻结适配器与实际交付投影不符",
    )
    if rec["status"] == "accepted":
        require(
            rec.get("reference_sha256") == sha(home / "reference.json"),
            "参考表字节不符",
        )
        require(
            layout.measurements(shared) == read(home / "reference.json"),
            "实际参考表与冻结测量器不符",
        )
        result["reference_sha256"] = rec["reference_sha256"]
    else:
        try:
            layout.measurements(shared)
        except DIAGNOSTIC_EXCEPTIONS as exc:
            require(
                type(exc).__name__ == rec["error_type"] and str(exc) == rec["detail"],
                "首次参考准备拒绝无法重现",
            )
            result["first_rejection_reproduced"] = True
        else:
            raise ValueError("已经拒绝的参考准备被重新接受")
    return result, shared


def check_artifact(row, messages, shared, projection):
    native = examine(contract.check_native, row, messages)
    # 旧审查器的关系检查只处理登记类型，防止其他关系被静默计作已核。
    unhandled = set()
    owners = contract.original_scope(row)[1]
    for rel in row["relations"]:
        kind = rel["type"]
        if kind not in {
            "ordered",
            "contains",
            "peer",
            "primary_support",
            "supports",
        } or (kind == "ordered" and not (owners.get(rel["from"]) and owners.get(rel["to"]))):
            unhandled.add(kind)
    if unhandled:
        native["checks"].append(
            {
                "dimension": "semantic_relation",
                "status": "unknown",
                "reason": "关系类型或端点无法由登记规则验证",
                "types": sorted(unhandled),
            }
        )
        native["static_status"] = combined([native["static_status"], "unresolved"])
    checks = native["checks"]
    result = {
        "native": native,
        "reference_geometry": strict_geometry(messages, shared),
        "source_contract": combined([projection["static_status"], native["static_status"]]),
        "dimensions": {
            name: group_status(checks, values) if checks else "unresolved"
            for name, values in GROUPS.items()
        },
    }
    # Easy 声明校验重做；码流、独立合同和几何结果分别保留。
    wire = "\n".join(runtime.signature(m) for m in messages)
    try:
        complaints = list(runtime.validate(wire, "surface_card", row["size"]))
        result["easy"] = {
            "status": "mismatch" if complaints else "verified",
            "complaints": [str(c) for c in complaints],
        }
    except DIAGNOSTIC_EXCEPTIONS as exc:
        result["easy"] = {
            "status": "unresolved",
            "error_type": type(exc).__name__,
            "detail": str(exc),
        }
    result["joint_automatic"] = combined(
        [
            result["source_contract"],
            result["reference_geometry"]["status"],
            result["easy"]["status"],
        ]
    )
    return result


def check_slot(row, arm, home, common, shared, receipt_required, root):
    dest = home / arm
    art, rec_path = dest / "card.a2ui.jsonl", dest / "receipt.json"
    result = {
        "arm": arm,
        "artifact_sha256": None,
        "independent_business_pass": None,
        "independent_native_visual_pass": None,
        "complete_product_success": None,
    }
    if not rec_path.exists():
        require(not receipt_required and not art.exists(), "终局回执缺失")
        result["generation_status"] = "unexecuted_or_unsealed"
        return result
    rec = read(rec_path)
    require(
        rec["task_id"] == row["task_id"] and rec["cell"] == arm and rec["first_pass"] is True,
        "席位回执的题号、方法或首轮标志不符",
    )
    for key in ("source_row_sha256", "shared_sha256", "reference_sha256"):
        require(rec.get(key) == common.get(key), "两臂使用的输入或参考表摘要不符")
    status = rec["status"]
    if common["status"] != "accepted":
        require(status == "common_" + common["status"], "共用上游失败归类不一致")
    result.update(
        generation_status=status,
        receipt_sha256=sha(rec_path),
        started_utc=rec["started_utc"],
    )
    for phase in ("structure", "geometry"):
        stage = rec.get(phase)
        if stage is None:
            continue
        require(read(dest / (phase + "_receipt.json")) == stage, "独立阶段和总回执不一致")
        if stage["status"] == "accepted":
            require(
                sha(dest / (phase + ".json")) == stage["decision_sha256"],
                "阶段结构或几何摘要不符",
            )
        if stage.get("request_dir"):
            sealed = dest / "calls" / phase
            require(
                arm == "model_model"
                and Path(stage["request_dir"].replace("\\", "/")).parts[-2:] == ("calls", phase),
                "请求归属不符",
            )
            reference = read(home / "reference.json")
            tree = read(dest / "structure.json") if phase == "geometry" else None
            expected = layout.prompt(phase, shared, reference, tree)
            require(
                read(sealed / "messages.json") == expected,
                "发出提示与冻结输入和参考表不符",
            )
            prompt_hash = digest(runtime.signature(expected).encode())
            require(
                prompt_hash
                == stage["prompt_sha256"]
                == read(sealed / "call.json")["prompt_sha256"],
                "实际发出提示摘要不符",
            )
            call = read(sealed / "call.json")
            body = sealed / "response.body"
            if call.get("envelope_sha256"):
                require(sha(body) == call["envelope_sha256"], "服务响应信封发生变化")
            if call.get("response_sha256"):
                text = sealed / "response.txt"
                require(
                    sha(text) == call["response_sha256"]
                    and text.read_bytes().decode()
                    == read(body)["choices"][0]["message"]["content"],
                    "原始模型正文与信封不符",
                )
            if stage["status"] == "accepted":
                require(call.get("response_sha256"), "接受的模型阶段缺少原始正文")
                parsed = layout.parse((sealed / "response.txt").read_bytes().decode())
                replay = (
                    parsed
                    if phase == "structure"
                    else common_native.apply_decisions(tree, parsed, shared)
                )
                require(replay == read(dest / (phase + ".json")), "模型首次响应未还原为记录的决策")
        elif stage["status"] == "accepted":
            require(arm == "program_program", "模型阶段缺少实际请求证据")
            replay = (
                program_layout.program_route(shared)
                if phase == "structure"
                else program_layout.program_geometry(read(dest / "structure.json"), shared)
            )
            require(replay == read(dest / (phase + ".json")), "程序决策重放不符")
    require((status == "artifact_ready") == art.exists(), "产物存在性与回执不符")
    if not art.exists():
        return result
    require(common["status"] == "accepted" and shared is not None, "共同输入与产物不匹配")
    raw = art.read_bytes()
    require(digest(raw) == rec["artifact_sha256"], "产物摘要与回执不符")
    result["artifact_sha256"] = digest(raw)
    require(
        result["artifact_sha256"]
        == sha(root / "anonymous" / rec["anonymous_id"] / "card.a2ui.jsonl"),
        "匿名原件与生成原件不符",
    )
    messages = [json.loads(line) for line in raw.splitlines()]
    require(len(messages) == 3, "产物不是三条原始消息")
    result.update(check_artifact(row, messages, shared, common["projection"]))
    return result


def record_summary(result):
    measures = {
        "generation": result["generation_status"],
        "artifact": "present" if result["artifact_sha256"] else "absent",
    }
    for key in ("source_contract", "joint_automatic"):
        measures[key] = result.get(key, "no_artifact")
    measures["strict_reference_geometry"] = result.get("reference_geometry", {}).get(
        "status", "no_artifact"
    )
    measures["easy"] = result.get("easy", {}).get("status", "no_artifact")
    measures["native_contract"] = result.get("native", {}).get("static_status", "no_artifact")
    measures.update({d: result.get("dimensions", {}).get(d, "no_artifact") for d in GROUPS})
    return measures
