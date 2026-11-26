"""在保管区执行各阶段工具。逐题输入、派生合同和处置清单均存储在调用者指定的位置。"""

import argparse
import hashlib
import json
from pathlib import Path

from audit_common import (
    digest,
    input_view,
    load,
    messages,
    private_destination,
    sha256,
    unique_object,
)
from fixed_content import extract
from freeze_candidates import select_candidates
from freeze_study import make_queue
from gold_evidence import prepare_case
from minimal_view import project
from p1_artifact import artifact_check
from prepare_dynamic_four_sets import (
    SEEDS,
    allocate,
    planned_counts,
    prepare_tasks,
    relation_families,
    validate_assignment,
)
from semantic_contract import contract, validate
from size_capability_dedup import deduplicate


def read_rows(path):
    return [
        json.loads(line, object_pairs_hook=unique_object)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def indexed(rows, key):
    result = {}
    for row in rows:
        identity = row[key]
        if not isinstance(identity, str) or not identity or identity in result:
            raise ValueError("编号为空或重复")
        result[identity] = row
    return result


def write_new(path, payload):
    data = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as file:
        file.write(data)


def inventory(root, names):
    resolved = root.resolve()
    files = {}
    for name in names:
        key = Path(name)
        path = (resolved / key).resolve()
        if (
            key.is_absolute()
            or ".." in key.parts
            or not path.is_relative_to(resolved)
            or key.as_posix() in files
        ):
            raise ValueError("清单含越界或重复路径")
        data = path.read_bytes()
        files[key.as_posix()] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    if not files:
        raise ValueError("冻结清单为空")
    return {"files": files, "tree_sha256": digest(files)}


def make_drafts(records, request_rows, targets):
    ids = indexed(records, "case_id")
    inputs = indexed(request_rows, "case_id")
    if not ids or ids.keys() != inputs.keys():
        raise ValueError("分集需要同一批案例的原请求和固定展示内容")
    if any(type(row.get("pre_exposed")) is not bool for row in inputs.values()):
        raise ValueError("缺少开发暴露登记")
    tasks = prepare_tasks(records, inputs)
    families = relation_families(tasks)
    counts = planned_counts(len(tasks), targets)
    trials = []
    for seed in SEEDS:
        try:
            allocation = allocate(tasks, families, seed, targets)
            checks = validate_assignment(tasks, families, allocation, counts)
            trials.append({"seed": seed, "allocation": allocation, "checks": checks})
        except ValueError as error:
            trials.append({"seed": seed, "allocation": None, "error": str(error)})
    return {
        "tasks": tasks,
        "families": families,
        "trials": trials,
        "formal_split_frozen": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="stage", required=True)
    arguments = {
        "freeze": ("root", "files", "out"),
        "inspect": ("request", "a2ui", "out"),
        "evidence": ("identity", "compact", "a2ui", "out"),
        "extract": ("evidence", "annotation", "a2ui", "out"),
        "semantics": ("packet", "review", "out"),
        "capabilities": ("records", "out"),
        "split": ("records", "requests", "targets", "out"),
        "select": ("records", "locks", "prior-dev", "out"),
        "queue": ("inputs", "family-map", "out"),
    }
    for name, args in arguments.items():
        cmd = commands.add_parser(name)
        for arg in args:
            cmd.add_argument("--" + arg, type=Path, required=True)
    a = parser.parse_args()
    a.out = private_destination(a.out)
    if a.stage == "freeze":
        result = inventory(a.root, load(a.files))
    elif a.stage == "inspect":
        view, query, envelope = input_view(load(a.request))
        checks, physical, _ = artifact_check(
            a.a2ui if a.a2ui.is_file() else None, view.get("size")
        )
        declared = view.get("size", view.get("suggestSize"))
        declared = (
            declared.lower().replace("×", "x") if isinstance(declared, str) else None
        )
        checks.extend(
            [
                {
                    "code": "P1_C4_SIZE",
                    "status": "pass" if declared in ("2x2", "2x4") else "unknown",
                    "declared_size": declared,
                },
                {
                    "code": "P1_C7_QUERY",
                    "status": "pass" if len(query.strip()) >= 4 else "fail",
                },
                {
                    "code": "P1_C8_LONG_QUERY",
                    "status": "pass",
                    "long_query": len(query.strip()) > 300,
                    "excluded_for_length": False,
                },
            ]
        )
        result = {
            "input_sha256": sha256(a.request),
            "checks": checks,
            "details": physical,
            "envelope": envelope,
            "minimal_input_audit": project(view),
        }
    elif a.stage == "evidence":
        result = prepare_case(load(a.identity), a.compact, a.a2ui)
    elif a.stage == "extract":
        evidence = load(a.evidence)
        if sha256(a.a2ui) != evidence["a2ui_sha256"]:
            raise ValueError("A2UI 与展示证据不匹配")
        result = extract(evidence, load(a.annotation), messages(a.a2ui))
    elif a.stage == "semantics":
        packet, review = load(a.packet), load(a.review)
        errors = validate(packet, review)
        if errors:
            raise ValueError("语义审核结构不满足：" + ", ".join(errors))
        result = contract(packet, review)
    elif a.stage == "capabilities":
        result = deduplicate(read_rows(a.records))
    elif a.stage == "split":
        targets = load(a.targets)
        if set(targets) != {"dev", "report", "extension", "reserve"} or any(
            type(v) is not int or v < 0 for v in targets.values()
        ):
            raise ValueError("需要四集非负整数名额")
        ordered = {k: targets[k] for k in ("dev", "report", "extension", "reserve")}
        result = make_drafts(read_rows(a.records), read_rows(a.requests), ordered)
    elif a.stage == "select":
        decisions, summary = select_candidates(
            read_rows(a.records), load(a.locks), read_rows(a.prior_dev)
        )
        result = {"dispositions": decisions, "summary": summary}
    else:
        rows = indexed(read_rows(a.family_map), "task_id")
        make_queue(a.inputs, {k: row["family_id"] for k, row in rows.items()}, a.out)
        return
    write_new(a.out, result)


if __name__ == "__main__":
    main()
