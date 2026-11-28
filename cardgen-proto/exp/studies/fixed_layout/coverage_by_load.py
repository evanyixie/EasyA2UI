"""Summarize the fixed-content cohort from assigned input to a pair of first artifacts."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from evidence import ARMS, SIZES, digest, read, require, safe_name, verified


def summarize(batch, inputs):
    seal = read(batch / "seal.json")
    lock = json.loads(verified(batch / "freeze.json", seal["freeze_sha256"]))
    queue = {safe_name(r["task_id"]): r["input_line_sha256"] for r in lock["queue"]}
    require(
        len(queue) == len(lock["queue"]) == lock["denominator"], "duplicate assignment"
    )
    require(
        lock["arms"] == dict(zip(("A", "B"), ARMS, strict=True)),
        "unexpected experimental arms",
    )
    receipt_hashes = seal["arm_receipt_sha256"]
    counts = defaultdict(Counter)
    seen = set()
    for raw in verified(inputs, lock["input_sha256"]).splitlines():
        row = json.loads(raw)
        task = row["task_id"]
        require(task not in seen and queue.get(task) == digest(raw), "unexpected input")
        seen.add(task)
        size, facts, actions = row["size"], row["D"], row["A"]
        require(
            size in SIZES and all(type(n) is int and n >= 0 for n in (facts, actions)),
            "invalid frozen load",
        )
        statuses = []
        for arm in ARMS:
            rel = f"results/{task}/{arm}/receipt.json"
            seat = json.loads(verified(batch / rel, receipt_hashes[rel]))
            require(
                seat["cell"] == arm
                and seat["task_id"] == task
                and seat["first_pass"] is True
                and seat["source_row_sha256"] == queue[task],
                "seat mismatch",
            )
            statuses.append(seat["status"])
        common_reject = [s.startswith("common_") for s in statuses]
        require(
            not any(common_reject) or statuses[0] == statuses[1],
            "unpaired common rejection",
        )
        model, program = [s == "artifact_ready" for s in statuses]
        outcome = {
            "assigned": 1,
            "common_admitted": int(not any(common_reject)),
            "model_first": int(model),
            "program_first": int(program),
            "paired_first": int(model and program),
            "model_transport_unknown": int("transport_unknown" in statuses[0]),
        }
        for label in (
            "all",
            size,
            f"{size}/D+A={facts + actions}",
            "with_action" if actions else "without_action",
        ):
            counts[label].update(outcome)
    require(
        seen == queue.keys() and len(receipt_hashes) == 2 * len(seen),
        "incomplete assignment or receipt index",
    )
    return {
        "input_sha256": lock["input_sha256"],
        "strata": dict(sorted(counts.items())),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("inputs", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.batch, args.inputs), indent=2))
