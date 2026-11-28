"""Reconstruct the first terminal technical reason of each frozen experimental seat."""

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from six_arms.technical_yield import ARMS, read_lines

# The original validators raise on the first violation. Never infer later failures.
CONTENT_ERRORS = (
    (r"items\[\d+\] 动态 text 与本路径首帧值不一致", "first_frame_value"),
    (r"items\[\d+\]\.entity 含无来源数字 ", "entity_numeral"),
    (r"items\[\d+\]\.label 含无来源数字 ", "label_numeral"),
    (r"items\[\d+\] 静态事实须逐字来自 query/title/description", "literal_source"),
    (r"items\[\d+\]\.unit 应为非空字符串", "empty_unit"),
    (r"items\[\d+\] 只允许绑定标量", "non_scalar"),
)
TEXT_CODES = {"glyph_width", "lines", "text_height"}
CONTAINER_CODES = {
    "container_width",
    "container_height",
    "exceeds_parent_width",
    "exceeds_parent_height",
}
SOURCE_CODES = {
    "DUPLICATE_ID_OR_DISCONNECTED_TREE",
    "UNAUTHORIZED_HANDLER",
    "DUPLICATE_PARENT_OR_CYCLE",
}
NATIVE_CLASSES = (
    "complete_no_leaf_box_issue",
    "confirmed_leaf_box_issue",
    "incomplete_without_observed_issue",
)


def terminal_reason(execution):
    status, phase = execution["status"], execution["failed_stage"]
    if status == "accepted":
        return "accepted", "accepted"
    if status == "callback_failed":
        return "unknown", "callback_" + phase
    if status == "geometry_unknown":
        why = execution["exit"]["why"]
        if why.startswith("首帧无法解引用"):
            return "unknown", "first_frame_unresolved"
        if why.startswith("本解释器未覆盖的表达式"):
            return "unknown", "unsupported_expression"
    if status == "stage_rejected":
        stage = execution["stages"][-1]
        if stage["stage"] != phase or stage["status"] != status:
            raise ValueError("Terminal stage disagrees with outcome")
        message = stage["error"]["message"]
        if message.startswith("JSON 不可解析 "):
            return phase, "json_extra_data" if message.startswith(
                "JSON 不可解析 Extra data:"
            ) else "json_syntax"
        if phase == "content":
            for expression, reason in CONTENT_ERRORS:
                if re.match(expression, message):
                    return phase, reason
        if phase == "geometry" and message.startswith("reference_capacity:"):
            if re.search(r"完整内容需要 \d+vp，画布高度为 \d+vp", message):
                return phase, "card_height"
            if re.search(r"完整文字需要 \d+ 行，组件最多允许 \d+ 行", message):
                return phase, "component_lines"
    if status == "artifact_checks_rejected":
        codes = {
            entry.split()[0] for entry in execution["first_native"]["checks"]["errors"]
        }
        if codes and codes <= SOURCE_CODES:
            return "artifact", "+".join(sorted(codes))
    if status == "geometry_unresolved":
        exit_record = execution["exit"]
        codes = {issue["code"] for issue in exit_record["after"]}
        if codes and codes <= TEXT_CODES | CONTAINER_CODES:
            if not codes & CONTAINER_CODES:
                return "reference_geometry", "text_only"
            if not codes & TEXT_CODES:
                return "reference_geometry", "container_only"
            return "reference_geometry", "text_and_container"
    # A new validator or outcome requires an explicit mapping, never an invisible residual bin.
    raise ValueError(f"Unrecognized frozen outcome or diagnostic in {status}/{phase}")


def summarize(seats, records):
    projected = {(s["task_id"], s["arm"]): s for s in seats}
    tasks = {key[0] for key in projected}
    if (
        not tasks
        or len(projected) != len(seats)
        or set(projected) != {(t, a) for t in tasks for a in ARMS}
    ):
        raise ValueError("Expected one complete six-arm grid")
    classified = {}
    counts = defaultdict(Counter)
    reasons = defaultdict(Counter)
    for raw in records:
        key = raw["task"], raw["arm"]
        seat = projected.get(key)
        ex = raw["execution"]
        if (
            seat is None
            or key in classified
            or seat["state"] != "terminal"
            or (ex["arm"], ex["status"], ex["failed_stage"])
            != (key[1], seat["status"], seat["failed_stage"])
        ):
            raise ValueError("Unmatched or conflicting original outcome")
        category, reason = terminal_reason(ex)
        classified[key] = category
        counts[key[1]][category] += 1
        reasons[category, reason][key[1]] += 1
    if classified.keys() != projected.keys():
        raise ValueError("Missing original outcomes")
    paired = Counter((classified[t, "L5"], classified[t, "L6"]) for t in tasks)
    return {
        "assigned_tasks": len(tasks),
        "terminal_seats": len(classified),
        "counts_by_arm": dict(counts),
        "terminal_reasons": [
            {
                "stage": stage,
                "reason": reason,
                "arms": arms,
                "total": sum(arms.values()),
            }
            for (stage, reason), arms in sorted(reasons.items())
        ],
        "l5_l6_paired_stopping_points": [
            {"L5": a, "L6": b, "tasks": n} for (a, b), n in sorted(paired.items())
        ],
    }


def native_class(screen, observation, original):
    captured = observation["execution"]["status"] == "native_captured"
    execution = original["execution"]
    if screen["capture"] != captured:
        raise ValueError("Native capture status mismatch")
    if not captured:
        return None
    if not (
        screen["artifact_sha256"]
        == observation["artifact_sha256"]
        == execution["final_native"]["sha256"]
    ):
        raise ValueError("Mismatched captured artifact")
    classes = [c for c in NATIVE_CLASSES if screen[c]]
    if len(classes) != 1:
        raise ValueError("Ambiguous native classification")
    return classes[0]


def audit(batch):
    technical = batch / "tech_metrics/continuation_final"
    endpoint = batch / "pre_score_evidence/endpoint"
    seats_hash = json.loads((technical / "completion_receipt.json").read_bytes())[
        "private_seats_sha256"
    ]
    observations_hash = json.loads((endpoint / "receipt.json").read_bytes())[
        "observations_sha256"
    ]
    seats = read_lines(technical / "seats.private.jsonl", seats_hash)
    observed = read_lines(endpoint / "observations.private.jsonl", observations_hash)
    screen_data = (
        batch / "objective_quality_20261128/joined_checkpoints.private.json"
    ).read_bytes()
    screens = [
        r for r in json.loads(screen_data) if r["checkpoint"] == "after_common_repair"
    ]
    screen_index = {(r["task_id"], r["arm"]): r for r in screens}
    if len(screens) != len(screen_index) or screen_index.keys() != {
        (s["task_id"], s["arm"]) for s in seats
    }:
        raise ValueError("Incomplete or duplicate native assignment")
    cross = defaultdict(Counter)

    def originals():
        for obs in observed:
            if obs["checkpoint"] != "after_common_repair":
                continue
            link = obs["provenance"]
            data = (batch / link["outcome_ref"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != link["outcome_sha256"]:
                raise ValueError("Original outcome digest mismatch")
            raw = json.loads(data)
            key = (raw["task"], raw["arm"])
            if key != (obs["task_id"], obs["arm"]):
                raise ValueError("Observation references a different seat")
            category = native_class(screen_index[key], obs, raw)
            if category:
                artifact = (batch / obs["artifact"]["evidence_ref"]).read_bytes()
                if hashlib.sha256(artifact).hexdigest() != obs["artifact_sha256"]:
                    raise ValueError("Captured final artifact digest mismatch")
                cross[raw["execution"]["status"]][category] += 1
            yield raw

    report = summarize(seats, originals())
    report["native_screen_of_captured_finals"] = {
        status: {k: counts[k] for k in NATIVE_CLASSES}
        for status, counts in cross.items()
    }
    report["source_sha256"] = {
        "seats": seats_hash,
        "observations": observations_hash,
        "native_screen": hashlib.sha256(screen_data).hexdigest(),
    }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("new_output", type=Path)
    args = parser.parse_args()
    result = audit(args.batch)
    with args.new_output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
