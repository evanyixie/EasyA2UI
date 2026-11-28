"""Recount B1/B2 from the original formal executor clocks and sealed provider receipts."""

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from six_arms.cache_token_cost import FROZEN_SEATS, verify_receipts
from six_arms.cost_frontier import TECH_LEDGER
from six_arms.fixed_content_repeats import FORMAL_PLAN, canonical, check, digest
from six_arms.native_repeated_facts import PINS
from six_arms.paired_delivery_bounds import verified
from six_arms.technical_yield import ARMS, read_lines

PHASES = ("content", "structure", "geometry", "theme", "emit")
INDEX = "pre_score_evidence/endpoint/observations.private.jsonl"
SUMMARY_SHA = "262c265cc7d42b1cdfe786cb569f57f70e5aed235d57fa5a7b88af756e5555c1"
TABLE = (
    Path(__file__).resolve().parents[4] / "paper/out/tables/formal_stage_timing.json"
)


def distribution(values, *, signed=False):
    """Linear interpolation and millisecond precision of the original timing ledger."""
    values = list(values)
    known = sorted(v for v in values if v is not None)
    check(
        all(
            type(v) in (int, float) and math.isfinite(v) and (signed or v >= 0)
            for v in known
        ),
        "Invalid clock value",
    )

    def percentile(p):
        if not known:
            return None
        index = (len(known) - 1) * p
        lo = int(index)
        return round(
            known[lo] + (known[math.ceil(index)] - known[lo]) * (index - lo), 3
        )

    return {
        "eligible": len(values),
        "observed": len(known),
        "unknown": len(values) - len(known),
        "p50_ms": percentile(0.5),
        "p95_ms": percentile(0.95),
        "max_ms": max(known, default=None),
        "sum_ms": round(sum(known), 3) if known else None,
    }


def residual(row):
    """Use only disjoint spans. An unreached exit contributes no elapsed interval."""
    values = [s["wall_ms"] for s in row["stages"].values()]
    if row["exit_reached"]:
        values.append(row["exit_ms"])
    if row["elapsed_ms"] is None or None in values:
        return None
    return round(row["elapsed_ms"] - sum(values), 3)


def project(record, seat, folder):
    run = record["execution"]
    arm = seat["arm"]
    steps = run["stages"]
    order = ("one_shot",) if arm == "L1" else PHASES
    check(
        [s["stage"] for s in steps] == list(order[: len(steps)])
        and len(steps) == len(seat["steps"]),
        "Stage sequence differs",
    )
    clocks = (
        run["status"],
        run["elapsed_ms"],
        run.get("output_check_and_repair_wall_ms"),
    )
    check(
        clocks == (seat["status"], seat["elapsed_ms"], seat["output_check_ms"])
        and (run["first_native"] is not None) == seat["first_emitted"],
        "Seat clock linkage differs",
    )
    calls = {c["phase"]: c for c in seat["calls"]}
    check(len(calls) == len(seat["calls"]), "Repeated call for one stage")
    stages = {}
    for s, registered in zip(steps, seat["steps"], strict=True):
        phase = s["stage"]
        owner = s["owner"]
        receipt = s.get("receipt")
        check(
            (phase, s["wall_ms"], s["status"])
            == (registered["phase"], registered["wall_ms"], registered["status"]),
            "Stage timing/status differs",
        )
        is_model = owner == "one_shot" or owner.startswith("model_")
        check(
            (owner.startswith("program_") or is_model)
            and (phase in calls) == is_model == (receipt is not None),
            "Stage owner/receipt differs",
        )
        if is_model:
            original = json.loads((folder / "calls" / phase / "call.json").read_bytes())
            check(
                original == receipt and calls[phase]["http_ms"] == receipt["http_ms"],
                "HTTP measurement differs from the provider receipt or cost ledger",
            )
        stages[phase] = {
            "owner": owner,
            "status": s["status"],
            "wall_ms": s["wall_ms"],
            "callback_ms": s.get("callback_wall_ms"),
            "call": calls.pop(phase, None),
        }
    check(not calls, "Unreached stage has an extra call")
    return {
        "stages": stages,
        "exit_ms": clocks[2],
        "exit_reached": seat["first_emitted"],
        "elapsed_ms": clocks[1],
        "status": run["status"],
    }


def aggregate(arm, rows):
    output = {}
    for phase in ("one_shot",) if arm == "L1" else PHASES:
        reached = [r["stages"][phase] for r in rows if phase in r["stages"]]
        callbacks = [s for s in reached if s["call"] is not None]
        calls = [s["call"] for s in callbacks]
        physical = [c["attempts"] for c in calls if c["attempts"] is not None]
        output[phase] = {
            "attempted": len(reached),
            "not_reached": len(rows) - len(reached),
            "owners": dict(Counter(s["owner"] for s in reached)),
            "stage_status": dict(Counter(s["status"] for s in reached)),
            "wall_ms": distribution(s["wall_ms"] for s in reached),
            "callback_wall_ms": distribution(s["callback_ms"] for s in callbacks),
            "receipt_http_ms": distribution(c["http_ms"] for c in calls),
            "logged_model_intents": len(calls),
            "known_physical_attempts": sum(physical),
            "unknown_physical_attempt_intents": len(calls) - len(physical),
            "provider_identified_responses": sum(
                c["provider"] is not None for c in calls
            ),
        }
    return {
        "assigned": len(rows),
        "statuses": dict(Counter(r["status"] for r in rows)),
        "stages": output,
        "elapsed_ms": distribution(r["elapsed_ms"] for r in rows),
        "output_check_and_repair_wall_ms": distribution(
            r["exit_ms"] for r in rows if r["exit_reached"]
        ),
        "exit_not_reached": sum(not r["exit_reached"] for r in rows),
        "unattributed_elapsed_ms": distribution(
            (residual(r) for r in rows), signed=True
        ),
    }


def clock(row, span):
    if span == "exit":
        return row["exit_reached"], row["exit_ms"]
    if span == "unattributed":
        return True, residual(row)
    if span == "elapsed":
        return True, row["elapsed_ms"]
    if span in row["stages"]:
        return True, row["stages"][span]["wall_ms"]
    return False, None


def adjacent(left, right):
    """Separate the full cohort's elapsed-time difference from stage-conditional contrasts."""
    check(left.keys() == right.keys(), "Unpaired tasks")
    result = {}
    for span in (*PHASES, "exit", "unattributed", "elapsed"):
        changes, common, completed = [], [], []
        for task in left:
            lr, lv = clock(left[task], span)
            rr, rv = clock(right[task], span)
            # Early stop contributes no executed span. Missing clocks on reached spans stay unknown.
            measurable = (not lr or lv is not None) and (not rr or rv is not None)
            delta = (
                round((rv if rr else 0) - (lv if lr else 0), 3) if measurable else None
            )
            changes.append(delta)
            if lr and rr:
                common.append(delta)
                if span in PHASES and all(
                    row["stages"][span]["status"] == "completed"
                    for row in (left[task], right[task])
                ):
                    completed.append(delta)
        measured = distribution(changes, signed=True)
        result[span] = {
            "assigned_pairs": len(changes),
            "missing_pair_clocks": measured["unknown"],
            "all_assigned_difference_sum_ms": measured["sum_ms"]
            if not measured["unknown"]
            else None,
            "both_reached_right_minus_left_ms": distribution(common, signed=True),
        }
        if span in PHASES:
            result[span]["both_completed_right_minus_left_ms"] = distribution(
                completed, signed=True
            )
    return result


def audit(formal_root):
    root = Path(formal_root)
    verified(root / "live/plan.json", FORMAL_PLAN)
    seats = read_lines(root / TECH_LEDGER, FROZEN_SEATS)
    cost = {(r["task_id"], r["arm"]): r for r in seats}
    check(len(cost) == len(seats) == 219 * 6, "Formal seat roster differs")
    verify_receipts(
        root, {c["local"]: (r["arm"], c) for r in seats for c in r["calls"]}
    )
    data = {arm: {} for arm in ARMS}
    for obs in read_lines(root / INDEX, PINS["observations"]):
        if obs["checkpoint"] != "raw_first":
            continue
        task, arm, proof = obs["task_id"], obs["arm"], obs["provenance"]
        path = root / proof["outcome_ref"]
        record = json.loads(verified(path, proof["outcome_sha256"]))
        check(
            task not in data[arm]
            and (record["task"], record["arm"]) == (task, arm)
            and record["plan_sha256"] == FORMAL_PLAN
            and record["execution"]["arm"] == arm
            and digest(canonical(record["execution"]))
            == record["execution_sha256"]
            == proof["execution_sha256"],
            "Outcome identity or digest differs",
        )
        data[arm][task] = project(record, cost[task, arm], path.parent)
    check(
        all(
            len(arm) == 219 and arm.keys() == data["L1"].keys() for arm in data.values()
        ),
        "Incomplete paired roster",
    )
    original = json.loads(
        verified((root / TECH_LEDGER).with_name("technical_summary.json"), SUMMARY_SHA)
    )
    by_arm = {arm: aggregate(arm, list(rows.values())) for arm, rows in data.items()}
    for arm, result in by_arm.items():
        old = original["by_arm"][arm]
        check(
            result["elapsed_ms"] == old["executor_elapsed_all_scheduled_ms"]
            and result["output_check_and_repair_wall_ms"]
            == old["output_check_and_repair_ms_on_reaching"]
            and result["statuses"] == old["terminal_by_status"],
            "Custody seat/exit aggregate differs",
        )
        for phase, stats in result["stages"].items():
            reference = old["stages"][phase]
            check(
                stats["wall_ms"] == reference["reached_stage_wall_ms"]
                and stats["receipt_http_ms"] == reference["http_ms_by_logged_intent"]
                and stats["known_physical_attempts"]
                == reference["physical_attempts"]["known_subtotal"]
                and stats["unknown_physical_attempt_intents"]
                == reference["physical_attempts"]["unknown_rows"],
                "Custody stage aggregate differs",
            )
    return {
        "schema": "formal_stage_timing.v1",
        "tasks": 219,
        "assigned_seats": len(cost),
        "source_sha256": {
            "formal_plan": FORMAL_PLAN,
            "outcome_index": PINS["observations"],
            "cost_seats": FROZEN_SEATS,
            "cost_summary": SUMMARY_SHA,
        },
        "units": "Milliseconds. P50/P95 use linear interpolation on observed clocks.",
        "timing_scope": "Executor only. HTTP is inside model callback, callback inside stage. "
        "Elapsed includes reached stage walls, joint output check/repair and residual.",
        "contrast": "Full cohort sums include zero duration for an unreached span; "
        "the paired distributions condition on reaching that span in both arms.",
        "by_arm": by_arm,
        "right_minus_left": {
            f"{b}_minus_{a}": adjacent(data[a], data[b])
            for a, b in (("L4", "L5"), ("L5", "L6"))
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_root", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Write a new aggregate; default checks the published table",
    )
    args = parser.parse_args()
    report = audit(args.formal_root)
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(
                json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            )
    else:
        check(report == json.loads(TABLE.read_bytes()), "Published table differs")
    print(f"Verified {report['assigned_seats']} signed seats")


if __name__ == "__main__":
    main()
