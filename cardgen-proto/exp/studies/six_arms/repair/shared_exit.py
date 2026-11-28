"""重放六档共同出口的几何修复，逐个保留缺卡、不可判、未修复和已修复席位。"""

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from time import perf_counter_ns

import study
from harness_v2 import frozen_calls, trial

from . import evidence, native_repair as native
from .rq2 import provenance


def verify_rounds(raw, output, log):
    if log["status"] != "repaired" and output != raw:
        raise ValueError("未采纳修复时须逐字节保留原件")
    if log["before"] is None:
        return
    card = native.parse(raw)
    violations, positions, _ = native.inspect(card)
    if native.issue_list(violations) != log["before"]:
        raise ValueError("初稿几何诊断未复现")
    for attempt in log["rounds"]:
        replay = evidence.replay_changes(raw, attempt)
        if native.material(replay) != native.material(card):
            raise ValueError("几何修复改动受保护内容")
        defects, boxes, _ = native.inspect(replay)
        introduced = {key: v for key, v in defects.items() if key not in violations}
        if (
            native.issue_list(defects) != attempt["candidate_violations"]
            or native.issue_list(introduced) != attempt["introduced_by_repair"]
        ):
            raise ValueError("不同轮次的几何变化无法复核")
        if attempt["accepted"]:
            if defects or replay != native.parse(output):
                raise ValueError("返回了未获验收的候选")
            for node in log["protected_valid_boxes"]:
                if not all(
                    math.isclose(a, b, abs_tol=native.EPS, rel_tol=0)
                    for a, b in zip(positions[node], boxes[node], strict=True)
                ):
                    raise ValueError("原有效节点的位置或尺寸发生变化")


def summarize(rows):
    eligible = [
        r for r in rows if r["status"] in ("no_change", "repaired", "unresolved")
    ]
    return {
        "queue": len(rows),
        "status": dict(Counter(r["status"] for r in rows)),
        "reference_assessed": len(eligible),
        "original_pass": sum(not r["before"] for r in eligible),
        "final_pass": sum(not r["after"] for r in eligible),
        "rounds": sum(r.get("rounds", 0) for r in rows),
    }


def shared(batch, out):
    if out.resolve().is_relative_to(batch.resolve()):
        raise ValueError("共同出口输出目录须位于原冻结批次之外")
    manifest = batch / "freeze.json"
    lock = frozen_calls.read(manifest)
    current = (batch / "cases.json").is_file()
    if current:
        study.verified(batch)
    queue = lock["queue"]
    if (
        not queue
        or len({tuple(q) for q in queue}) != len(queue)
        or any(
            arm not in trial.ARMS
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", task)
            or Path(task).is_reserved()
            for task, arm in queue
        )
    ):
        raise ValueError("冻结题号或席位不合法")
    resources = provenance()
    out.mkdir(parents=True, exist_ok=False)
    study.write(
        out / "freeze.json",
        {
            **resources,
            "input_freeze_sha256": frozen_calls.sha(manifest),
            "queue": queue,
            "new_physical_requests": 0,
        },
    )
    rows = []
    for task, arm in queue:
        orig = batch / task / arm
        path = orig / "receipt.json"
        row = {"task": task, "arm": arm}
        rows.append(row)
        if not path.exists():
            if orig.is_dir() and any(orig.iterdir()):
                raise ValueError("已启动的席位缺少首件回执")
            row["status"] = "unexecuted"
            continue
        receipt = frozen_calls.read(path)
        source_file = batch / "sources" / (task + ".json")
        source = frozen_calls.read(source_file)
        if (
            frozen_calls.sha(source_file) != lock["source_hashes"][task]
            or lock["source_hashes"][task] != receipt["source_sha256"]
            or receipt["arm"] != arm
        ):
            raise ValueError("首件的业务源或所属条件与冻结清单不符")
        row["first_pass_status"] = receipt["status"]
        if current and frozen_calls.read(orig / "seal.json") != study.seat_hashes(orig):
            raise ValueError("公开首件归档未通过摘要复核")
        card_path = orig / "card.a2ui.jsonl"
        if not card_path.is_file():
            if receipt["status"] in {
                "artifact_checks_pass",
                "artifact_checks_rejected",
            }:
                raise ValueError("原回执已记录首件，实际卡片文件缺失")
            row.update(status="no_native_input", first_error=receipt.get("first_error"))
            continue
        raw = card_path.read_bytes()
        original_checks = trial.inspect_card(
            [json.loads(line) for line in raw.splitlines()], source
        )
        if original_checks != frozen_calls.read(orig / "checks.json"):
            raise ValueError("原首件出口检查未复现")
        start = perf_counter_ns()
        output, log = native.repair(raw)
        elapsed = (perf_counter_ns() - start) / 1e6
        verify_rounds(raw, output, log)
        final_checks = trial.inspect_card(
            [json.loads(line) for line in output.splitlines()], source
        )
        if final_checks != original_checks:
            raise ValueError("几何修复改变来源和协议判定")
        dest = out / task / arm
        dest.mkdir(parents=True)
        if raw != output:
            (dest / "card.a2ui.jsonl").write_bytes(output)
        study.write(dest / "repair.json", log)
        row.update(
            status=log["status"],
            original_sha256=evidence.digest(raw),
            terminal_sha256=evidence.digest(output),
            before=log["before"],
            after=log["after"],
            rounds=len(log["rounds"]),
            source_issues=final_checks["errors"],
            repair_function_ms=elapsed,
        )
    result = {
        "queue": queue,
        "counts": {
            "all": summarize(rows),
            **{
                arm: summarize([r for r in rows if r["arm"] == arm])
                for arm in trial.ARMS
            },
        },
        "rows": rows,
        "new_physical_requests": 0,
    }
    study.write(out / "shared.json", result)
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument(
        "batch", type=Path, help="已冻结的六档首件批次（含 sources、席位回执及原卡）"
    )
    cli.add_argument("out", type=Path)
    args = cli.parse_args()
    print(json.dumps(shared(args.batch, args.out)["counts"]["all"], ensure_ascii=False))
