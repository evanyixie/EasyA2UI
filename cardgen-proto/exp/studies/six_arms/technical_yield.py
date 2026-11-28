"""Paired technical acceptance of the six frozen arms, including unavailable decisions."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from statistics import median

from fixed_layout.paired_analysis import analyze

ARMS = tuple(f"L{i}" for i in range(1, 7))
DECISION = {
    "accepted": "pass",
    "stage_rejected": "fail",
    "geometry_unresolved": "fail",
    "artifact_checks_rejected": "fail",
    "geometry_unknown": "missing",
    "callback_failed": "missing",
}


def read_lines(path, sha):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError(f"Input changed: {path}")
    return [json.loads(line) for line in raw.splitlines()]


def summarize(roster, rows):
    seats = defaultdict(dict)
    for row in rows:
        task, arm, status = row["task_id"], row["arm"], row["status"]
        if arm in seats[task] or arm not in ARMS or status not in DECISION:
            raise ValueError("Duplicate or unrecognized seat")
        seats[task][arm] = row
    ids = {entry["task_id"] for entry in roster}
    if (
        len(ids) != len(roster)
        or ids != set(seats)
        or any(set(s) != set(ARMS) for s in seats.values())
    ):
        raise ValueError("Incomplete or unmatched assignment")
    cohorts = {
        "all_assigned": roster,
        "source_217": [r for r in roster if r["included_in_217_sensitivity"]],
    }
    for size in sorted({r["size"] for r in roster}):
        cohorts[size] = [r for r in roster if r["size"] == size]
    results = {}
    for name, tasks in cohorts.items():
        groups = [{"task_id": r["task_id"], "family_id": r["family"]} for r in tasks]
        arms = {}
        for arm in ARMS:
            current = [seats[r["task_id"]][arm] for r in tasks]
            counts = Counter(DECISION[s["status"]] for s in current)
            passed = [s["elapsed_ms"] for s in current if s["status"] == "accepted"]
            arms[arm] = {
                "counts": dict(counts),
                "accepted_count_range": [
                    counts["pass"],
                    counts["pass"] + counts["missing"],
                ],
                "executor_median_all_ms": median(s["elapsed_ms"] for s in current),
                "executor_median_accepted_ms": median(passed) if passed else None,
                "failure_stage_terminal": dict(
                    Counter(
                        s["failed_stage"] for s in current if s["status"] != "accepted"
                    )
                ),
            }
        pairs = {}
        for a, b in combinations(ARMS, 2):
            decisions = []
            for r in groups:
                statuses = [seats[r["task_id"]][arm]["status"] for arm in (a, b)]
                decisions.append(
                    {
                        "task_id": r["task_id"],
                        "A": DECISION[statuses[0]],
                        "B": DECISION[statuses[1]],
                        "missing_reason": "/".join(
                            s for s in statuses if DECISION[s] == "missing"
                        ),
                    }
                )
            paired = analyze(groups, decisions)
            paired["only_" + a + "_pass"] = paired.pop("only_A_model_pass")
            paired["only_" + b + "_pass"] = paired.pop("only_B_program_pass")
            paired["A_arm"], paired["B_arm"] = a, b
            pairs[f"{b}_minus_{a}"] = paired
        results[name] = {
            "tasks": len(tasks),
            "arms": arms,
            "paired_technical_only": pairs,
        }
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=Path)
    parser.add_argument("new_summary", type=Path)
    args = parser.parse_args()
    analysis = args.batch / "analysis"
    technical = args.batch / "tech_metrics/continuation_final"
    seal = json.loads((analysis / "analysis_seal.json").read_bytes())["files_sha256"]
    receipt = json.loads((technical / "completion_receipt.json").read_bytes())
    roster = read_lines(analysis / "roster.jsonl", seal["roster.jsonl"])
    plan_bytes = (args.batch / "live/plan.json").read_bytes()
    if hashlib.sha256(plan_bytes).hexdigest() != receipt["plan_sha256"]:
        raise ValueError("Frozen assignment changed")
    cases = json.loads(plan_bytes)["assignment"]["cases"]
    sizes = {r["id"]: r["size"] for r in cases}
    if len(sizes) != len(cases) or sizes.keys() != {r["task_id"] for r in roster}:
        raise ValueError("Assignment and roster disagree")
    for r in roster:
        r["size"] = sizes[r["task_id"]]
    seats = read_lines(
        technical / "seats.private.jsonl", receipt["private_seats_sha256"]
    )
    result = summarize(roster, seats)
    result["inputs_sha256"] = {
        "roster": seal["roster.jsonl"],
        "seats": receipt["private_seats_sha256"],
        "assignment": receipt["plan_sha256"],
    }
    args.new_summary.parent.mkdir(parents=True, exist_ok=True)
    with args.new_summary.open("x", encoding="utf8") as out:
        json.dump(result, out, ensure_ascii=False, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
