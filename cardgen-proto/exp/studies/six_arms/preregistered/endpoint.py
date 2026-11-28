"""固定画布试验逐题终点。仅判定调用者明确提供的当前检查点证据，不扫描文件或读取金标。

assess(record) 接受 JSON 兼容对象，返回逐项状态、依据、缺项和两个终点。
task_id、arm、checkpoint 标识唯一席位及原始首轮/共同修复后谱系。execution 为当前
检查点的 {status, evidence_ref}。primary_evidence 的项为 {status, evidence_ref}；
独立评审项还需 source_kind=independent_review / independent_adjudication。
not_applicable 仅限条件项，另需 applicability 对应项 {applies:false,reason,evidence_ref}。
c04 提供 protocol、coverage、overflow。artifact.subject 和每项测量的 subject 均填
{task_id,arm,checkpoint,artifact_sha256}，artifact.evidence_ref 指向原件登记凭据。
没有同检查点原件、未执行或测量对象不匹配时不使用相应数值。数值样例见 test_endpoint.py。
引用须由调用方绑定到同一题、检查点和产物并保存原件。此纯函数不会代签或核验外部签名。
"""

import math
import re

PRIMARY_ITEMS = (
    "first_response_lineage",
    "protocol",
    "trusted_native_frame",
    "lossless_caller_canvas",
    "must_show_facts",
    "entity_roles_priority",
    "binding_fidelity",
    "registered_action_payloads",
    "actual_action_destinations",
    "independent_business",
    "title_anchor",
    "body_alignment",
    "readable_text",
    "specialized_presentation",
    "schedule_timeline",
)
CONDITIONAL = {
    "binding_fidelity": "bindings",
    "registered_action_payloads": "actions",
    "actual_action_destinations": "actions",
    "title_anchor": "title_anchor",
    "body_alignment": "body_alignment",
    "readable_text": "text",
    "specialized_presentation": "specialized_presentation",
    "schedule_timeline": "schedule_timeline",
}
INDEPENDENT = {
    "independent_business",
    "title_anchor",
    "body_alignment",
    "readable_text",
    "specialized_presentation",
    "schedule_timeline",
}
EVIDENCE_KINDS = {
    "first_response_lineage": {"first_attempt_receipt"},
    "common_repair_lineage": {"common_repair_receipt"},
    "trusted_native_frame": {"native_frame_with_trusted_values"},
    "registered_action_payloads": {"registry_payload_audit"},
    "actual_action_destinations": {"native_action_trace"},
}
HARD_FAILURES = {
    "stage_rejected",
    "artifact_checks_rejected",
    "algorithm_rejected",
    "unsupported_contract",
    "partial_delivery",
    "native_rejected",
}
INCOMPLETE = {
    "transport_failed",
    "infra_interrupted",
    "not_run",
    "no_artifact",
    "device_unavailable",
    "unknown",
}
OBSERVED = {"artifact_checks_pass", "artifact_emitted", "native_captured"}
STATUSES = {"pass", "fail", "unknown", "not_applicable"}


def _ref(value):
    return isinstance(value, str) and bool(value.strip())


def _decision(status, reason, **details):
    return {"status": status, "reason": reason, **details}


def _proof(raw, key, applicability=None, *, independent=False):
    if raw is None:
        return _decision("unknown", "缺少本项证据")
    if not isinstance(raw, dict) or raw.get("status") not in STATUSES:
        raise ValueError(f"{key} 的证据状态无效")
    status, ref = raw["status"], raw.get("evidence_ref")
    reason = raw.get("reason")
    if status == "unknown":
        return _decision("unknown", reason or "证据尚未确定", evidence_ref=ref)
    if status == "not_applicable":
        scope = (applicability or {}).get(CONDITIONAL.get(key)) or {}
        if key not in CONDITIONAL or scope.get("applies") is not False:
            return _decision("unknown", "缺少已冻结的不适用判定或此项不可豁免")
        if not _ref(scope.get("evidence_ref")) or not _ref(scope.get("reason")):
            return _decision("unknown", "不适用的冻结依据或理由缺失")
        return _decision(status, scope["reason"], evidence_ref=scope["evidence_ref"])
    if not _ref(ref):
        return _decision("unknown", "判定缺少可回查的证据引用")
    kind = raw.get("source_kind")
    if independent and kind not in {"independent_review", "independent_adjudication"}:
        return _decision("unknown", "此项需要独立评审或独立仲裁", evidence_ref=ref)
    if key in EVIDENCE_KINDS and kind not in EVIDENCE_KINDS[key]:
        return _decision("unknown", "提供的证据类型无法判定此项", evidence_ref=ref)
    return _decision(
        status, reason or "据提供的证据判定", evidence_ref=ref, source_kind=kind
    )


def _execution(raw):
    if raw is None:
        return _decision("unknown", "缺当前检查点执行回执")
    status = raw.get("status")
    if status not in HARD_FAILURES | INCOMPLETE | OBSERVED:
        raise ValueError("无法识别执行状态，请先按冻结分类映射")
    if not _ref(raw.get("evidence_ref")):
        return _decision("unknown", "执行状态缺回执引用", execution_status=status)
    result = (
        "fail"
        if status in HARD_FAILURES
        else "pass"
        if status in OBSERVED
        else "unknown"
    )
    return _decision(
        result,
        raw.get("reason") or status,
        execution_status=status,
        evidence_ref=raw["evidence_ref"],
    )


def _combine(checks):
    failed = [k for k, x in checks.items() if x["status"] == "fail"]
    missing = [k for k, x in checks.items() if x["status"] == "unknown"]
    status = "fail" if failed else "unknown" if missing else "pass"
    return {"status": status, "failed": failed, "unknown": missing, "checks": checks}


def _inventory(block):
    ids = block.get("expected_ids")
    if ids is None:
        return None
    if (
        not isinstance(ids, list)
        or any(not _ref(k) for k in ids)
        or len(set(ids)) != len(ids)
    ):
        raise ValueError("冻结清单需为不重复且非空字符串组成的列表")
    if not ids or not _ref(block.get("inventory_ref")):
        return None
    return ids


def _observations(block, ids):
    values = block.get("observations", {})
    if not isinstance(values, dict) or set(values) - set(ids):
        raise ValueError("观测含有未登记清单项或格式错误")
    return [values.get(k) for k in ids]


def _coverage_counts(block):
    ids = _inventory(block)
    if not ids or not _ref(block.get("evidence_ref")):
        return _decision(
            "unknown", "缺已预标的必显清单、观测依据或有定义的分母", fraction=None
        )
    values = _observations(block, ids)
    if any(v is not None and not isinstance(v, bool) for v in values):
        raise ValueError("必显覆盖须为 true、false 或 null")
    n, yes, missing = len(ids), values.count(True), values.count(None)
    return {
        "covered": yes,
        "unknown_count": missing,
        "total": n,
        "fraction": None if missing else yes / n,
        "inventory_ref": block["inventory_ref"],
        "evidence_ref": block["evidence_ref"],
    }


def _coverage_at(counts, percent):
    if "total" not in counts:
        return {**counts, "threshold_percent": percent}
    yes, missing, n = counts["covered"], counts["unknown_count"], counts["total"]
    if 100 * (yes + missing) < percent * n:
        status = "fail"
    elif missing:
        status = "unknown"
    else:
        status = "pass" if 100 * yes >= percent * n else "fail"
    return _decision(
        status,
        f"预标必显覆盖至少 {percent}%，缺测项不作未覆盖",
        threshold_percent=percent,
        **counts,
    )


def _overflow(block):
    ids = _inventory(block)
    if (
        not ids
        or not _ref(block.get("evidence_ref"))
        or block.get("method") != "native_glyph_px"
    ):
        return _decision(
            "unknown", "缺全节点清单或原生字形像素观测", max_overflow_px=None
        )
    values = _observations(block, ids)
    known = [v for v in values if v is not None]
    if any(type(v) not in (float, int) or not math.isfinite(v) or v < 0 for v in known):
        raise ValueError("节点越界必须为非负、有限的原生像素数")
    maximum = max(known, default=None)
    missing = len(ids) - len(known)
    if maximum is not None and maximum > 4:
        status = "fail"
    elif missing:
        status = "unknown"
    else:
        status = "pass"
    return _decision(
        status,
        "逐节点原生字形最大越界不超过 4px",
        unknown_count=missing,
        total=len(ids),
        observed_max_px=maximum,
        max_overflow_px=None if missing else maximum,
        inventory_ref=block["inventory_ref"],
        evidence_ref=block["evidence_ref"],
    )


def _artifact(record):
    execution = record.get("execution") or {}
    if execution.get("status") in {"not_run", "no_artifact"}:
        return _decision("unknown", "当前检查点未执行或登记为无原件")
    if execution.get("status") not in HARD_FAILURES | OBSERVED or not _ref(
        execution.get("evidence_ref")
    ):
        return _decision("unknown", "当前检查点缺少已执行的可核回执")
    item = record.get("artifact") or {}
    subject = item.get("subject")
    if not isinstance(subject, dict) or not _ref(item.get("evidence_ref")):
        return _decision("unknown", "当前检查点缺少可回查的原件及摘要登记")
    sha = subject.get("artifact_sha256")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        return _decision("unknown", "原件登记缺有效的 SHA-256")
    if any(subject.get(k) != record[k] for k in ("task_id", "arm", "checkpoint")):
        return _decision("unknown", "原件属于其他题目、条件或检查点")
    return _decision(
        "pass",
        "有同题、同档、同检查点的发射原件",
        subject=subject,
        evidence_ref=item["evidence_ref"],
    )


def _c04(record):
    artifact = _artifact(record)
    blocks = record.get("c04") or {}
    paired = {}
    for key in ("protocol", "coverage", "overflow"):
        block = blocks.get(key) or {}
        if artifact["status"] == "pass" and block.get("subject") == artifact["subject"]:
            paired[key] = block
    calibrated = _proof(paired.get("protocol"), "c04_calibrated_protocol")
    if (
        calibrated["status"] in {"pass", "fail"}
        and calibrated["source_kind"] != "calibrated_protocol"
    ):
        calibrated = _decision(
            "unknown", "缺校准协议依据", evidence_ref=calibrated["evidence_ref"]
        )
    counts = _coverage_counts(paired.get("coverage", {}))
    overflow = _overflow(paired.get("overflow", {}))

    def at(percent):
        return _combine(
            {
                "same_checkpoint_artifact": artifact,
                "calibrated_protocol": calibrated,
                f"must_show_{percent}_percent": _coverage_at(counts, percent),
                "max_node_overflow_4px": overflow,
            }
        )

    result = at(80)
    result["unpaired_or_missing_evidence"] = [
        k for k in ("protocol", "coverage", "overflow") if k not in paired
    ]
    result["sensitivity"] = {f"{pct}_percent": at(pct) for pct in (60, 100)}
    return result


def assess(record):
    """对一个席位的一个检查点独立计算首次完整交付和论文 C04。返回值可序列化为 JSON。"""
    if not _ref(record.get("task_id")) or not _ref(record.get("arm")):
        raise ValueError("需要题目及条件标识")
    point = record.get("checkpoint")
    if point not in {"raw_first", "after_common_repair"}:
        raise ValueError("需要指定首轮原件或共同修复后的检查点")
    primary = record.get("primary_evidence") or {}
    applicable = record.get("applicability") or {}
    items = (
        (*PRIMARY_ITEMS, "common_repair_lineage")
        if point == "after_common_repair"
        else PRIMARY_ITEMS
    )
    if set(primary) - set(items) or set(applicable) - set(CONDITIONAL.values()):
        raise ValueError("当前检查点含未登记的评分或适用性字段")
    checks = {"execution": _execution(record.get("execution"))}
    for key in items:
        checks[key] = _proof(
            primary.get(key), key, applicable, independent=key in INDEPENDENT
        )
    return {
        "task_id": record["task_id"],
        "arm": record["arm"],
        "checkpoint": point,
        "primary": _combine(checks),
        "c04": _c04(record),
    }
