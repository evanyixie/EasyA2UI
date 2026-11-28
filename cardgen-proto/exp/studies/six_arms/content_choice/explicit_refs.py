"""Trace an input-registered fact from the common candidate set to frozen selections."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from six_arms.technical_yield import read_lines

MODEL_ARMS = ("L2", "L3", "L4", "L5", "L6")


def product_state(stage, path):
    status = stage["status"]
    if status in {"stage_rejected", "callback_failed"} and not stage.get("product"):
        return status
    if status != "completed" or not isinstance(stage.get("product"), dict):
        raise ValueError("Inconsistent frozen content stage")
    items = stage["product"]["items"]
    return (
        "kept"
        if any(i.get("path") == path for i in items)
        else "valid_without_reference"
    )


def summarize(records):
    groups = defaultdict(list)
    seen = set()
    for r in records:
        signature = r["task"], r["criterion"]
        if signature in seen or set(r["model"]) != set(MODEL_ARMS):
            raise ValueError("Duplicate requirement or incomplete opportunities")
        seen.add(signature)
        groups[r["criterion"]].append(r)
    out = {}
    for criterion, subset in sorted(groups.items()):
        by_arm = {a: Counter(r["model"][a] for r in subset) for a in MODEL_ARMS}
        distribution = Counter(
            sum(s == "kept" for s in r["model"].values()) for r in subset
        )
        out[criterion] = {
            "assigned_tasks": len(subset),
            "program_kept_reference": sum(r["program_kept"] for r in subset),
            "model_valid_product_by_arm": by_arm,
            "tasks_by_number_of_model_opportunities_with_reference": dict(
                sorted(distribution.items())
            ),
        }
    return {"distinct_tasks": len({task for task, _ in seen}), "criteria": out}


def audit(batch, manifest):
    technical = batch / "pre_score_evidence/content_selection"
    receipt_bytes = (technical / "receipt.json").read_bytes()
    lock = json.loads(receipt_bytes)["sealed_files"]
    prog_name, model_name = (
        "program_choices.private.jsonl",
        "model_attempt_index.private.jsonl",
    )
    programs = read_lines(technical / prog_name, lock[prog_name])
    attempts = read_lines(technical / model_name, lock[model_name])
    program = {r["task_id"]: r for r in programs}
    model = {(r["task_id"], r["arm"]): r for r in attempts}
    if len(program) != len(programs) or len(model) != len(attempts):
        raise ValueError("Duplicate selection receipt")
    plan_bytes = (batch / "live/plan.json").read_bytes()
    if hashlib.sha256(plan_bytes).hexdigest() != manifest["plan_sha256"]:
        raise ValueError("Input register and run refer to different assignments")
    cases = {r["id"]: r for r in json.loads(plan_bytes)["assignment"]["cases"]}
    if set(cases) != set(program) or set(model) != {
        (t, a) for t in cases for a in MODEL_ARMS
    }:
        raise ValueError("Selection grid differs from frozen assignment")
    results = []
    for record in manifest["requirements"]:
        task, path = record["task"], record["path"]
        case = cases[task]
        if case["input_sha256"] != record["packaged_request_sha256"]:
            raise ValueError("Mismatched registered input")
        registry = (
            batch / "queue/package/registry" / (case["file_id"] + ".json")
        ).read_bytes()
        if (
            hashlib.sha256(registry).hexdigest() != case["registry_sha256"]
            or path not in json.loads(registry)["binding_samples"]
        ):
            raise ValueError("Registered field missing from the frozen sample registry")
        picked = program[task]
        stage_decisions = {}
        for arm in MODEL_ARMS:
            index = model[task, arm]
            raw = (batch / index["outcome_file"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != index["outcome_file_sha256"]:
                raise ValueError("Frozen outcome digest mismatch")
            outcome = json.loads(raw)
            execution = outcome["execution"]
            stage = execution["stages"][0]
            if (
                (outcome["task"], outcome["arm"], stage["stage"])
                != (task, arm, "content")
                or stage["status"] != index["content_stage_status"]
                or execution["source_canonical_sha256"] != index["source_sha256"]
                or index["source_sha256"] != picked["source_sha256"]
            ):
                raise ValueError("Different source, opportunity or stage")
            stage_decisions[arm] = product_state(stage, path)
        results.append(
            {
                "task": task,
                "criterion": record["criterion"],
                "program_kept": path in picked["choice"]["fact_ids"],
                "model": stage_decisions,
            }
        )
    summary = summarize(results)
    summary["selection_receipt_sha256"] = hashlib.sha256(receipt_bytes).hexdigest()
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("registered_inputs", type=Path)
    parser.add_argument("register_sha256")
    parser.add_argument("new_output", type=Path)
    args = parser.parse_args()
    raw_inputs = args.registered_inputs.read_bytes()
    if hashlib.sha256(raw_inputs).hexdigest() != args.register_sha256:
        raise ValueError("Input-only register changed")
    report = audit(args.batch, json.loads(raw_inputs))
    report["input_register_sha256"] = args.register_sha256
    with args.new_output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, sort_keys=True, indent=2) + "\n")
