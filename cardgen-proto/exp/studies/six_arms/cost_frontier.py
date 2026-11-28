"""Compare six-arm cost per assigned task and per observed pass on common tasks."""

import argparse
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path

from six_arms.technical_yield import ARMS, DECISION, read_lines

TOKEN_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens")
NATIVE_LEDGER = "objective_quality_20261128/joined_checkpoints.private.json"
TECH_LEDGER = "tech_metrics/continuation_final/seats.private.jsonl"
ENDPOINTS = ("technical_pass", "native_screen_pass")


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def usage(calls):
    """Keep the cost of failed seats; a missing meter reading is never a zero receipt."""
    known = Counter()
    missing = 0
    for call in calls:
        tokens = call["tokens"]
        values = tuple(tokens[k] for k in TOKEN_FIELDS)
        if any(v is None for v in values):
            if any(v is not None for v in values):
                raise ValueError("Partially reported usage needs explicit accounting")
            missing += 1
            continue
        if (
            any(type(v) is not int or v < 0 for v in values)
            or sum(values[:2]) != values[2]
        ):
            raise ValueError("Inconsistent provider token receipt")
        known.update(dict(zip(TOKEN_FIELDS, values)))
    return known, missing


def totals(rows):
    counts = Counter()
    for r in rows:
        costs, missing = usage(r["calls"])
        counts.update(costs)
        counts["assigned"] += 1
        counts["unknown_usage_calls"] += missing
        counts["request_intents"] += len(r["calls"])
        counts["known_physical_attempts"] += sum(
            c["attempts"] for c in r["calls"] if c["attempts"] is not None
        )
        counts["unknown_attempt_intents"] += sum(
            c["attempts"] is None for c in r["calls"]
        )
        counts["technical_pass"] += r["status"] == "accepted"
        counts["unknown_technical"] += DECISION[r["status"]] == "missing"
        counts["native_screen_pass"] += r["native_screen_pass"]
    data = dict(counts)
    for field in TOKEN_FIELDS:
        data[field] = counts[field]
    data["executor_seconds"] = round(sum(r["elapsed_ms"] for r in rows) / 1000, 6)
    if not counts["unknown_usage_calls"]:
        data["tokens_per_assigned"] = ratio(counts["total_tokens"], len(rows))
        for endpoint in ENDPOINTS:
            data["tokens_per_" + endpoint] = ratio(
                counts["total_tokens"], counts[endpoint]
            )
    return data


def frontier(arms, endpoint, cost):
    """Non-dominated points; equal points share membership and undefined costs are excluded."""
    points = {
        a: (r[cost], r[endpoint] / r["assigned"])
        for a, r in arms.items()
        if r[cost] is not None
    }
    return [
        a
        for a, (x, y) in points.items()
        if not any(
            other_x <= x and other_y >= y and (other_x < x or other_y > y)
            for other_x, other_y in points.values()
        )
    ]


def panels(grid, tasks, arms):
    def positive(task, arm, endpoint):
        row = grid[task, arm]
        return (
            row["status"] == "accepted"
            if endpoint == "technical_pass"
            else row[endpoint]
        )

    complete = [
        t for t in tasks if all(usage(grid[t, a]["calls"])[1] == 0 for a in arms)
    ]
    if not complete:
        raise ValueError("No shared usage-complete tasks")
    stats = {a: totals([grid[t, a] for t in complete]) for a in arms}
    pairs = {}
    for (a, b), flag in [
        (("L5", "L6"), "technical_pass"),
        (("L1", "L5"), "native_screen_pass"),
    ]:
        if a not in stats or b not in stats:
            continue

        decisions = Counter(
            (positive(t, a, flag), positive(t, b, flag)) for t in complete
        )
        pairs[a + "_" + b + "_" + flag] = {
            "both": decisions[True, True],
            "first_only": decisions[True, False],
            "second_only": decisions[False, True],
            "neither_observed": decisions[False, False],
        }
    l5, l6 = stats["L5"], stats["L6"]
    net = l5["technical_pass"] - l6["technical_pass"]
    return {
        "shared_tasks": len(complete),
        "excluded_missing_usage": len(tasks) - len(complete),
        "arms": stats,
        "observed_pairs": pairs,
        "frontiers": {
            e: {
                metric: frontier(stats, e, metric)
                for metric in ("tokens_per_assigned", "tokens_per_" + e)
            }
            for e in ENDPOINTS
        },
        "l5_over_l6": {
            "net_technical_passes": net,
            "incremental_tokens_per_net_technical_pass": ratio(
                l5["total_tokens"] - l6["total_tokens"], net
            )
            if net > 0
            else None,
            "incremental_seconds_per_net_technical_pass": ratio(
                l5["executor_seconds"] - l6["executor_seconds"], net
            )
            if net > 0
            else None,
        },
    }


def audit(batch, bounds_path, native_digest):
    tech_digest = json.loads(
        (batch / "tech_metrics/continuation_final/completion_receipt.json").read_bytes()
    )["private_seats_sha256"]
    seats = read_lines(batch / TECH_LEDGER, tech_digest)
    native_bytes = (batch / NATIVE_LEDGER).read_bytes()
    if hashlib.sha256(native_bytes).hexdigest() != native_digest:
        raise ValueError("Native ledger hash mismatch")
    screens = [
        r for r in json.loads(native_bytes) if r["checkpoint"] == "after_common_repair"
    ]
    native = {(r["task_id"], r["arm"]): r for r in screens}
    grid = {(s["task_id"], s["arm"]): s for s in seats}
    tasks = sorted({s["task_id"] for s in seats})
    if (
        not tasks
        or len(grid) != len(seats)
        or len(native) != len(screens)
        or grid.keys() != native.keys()
        or set(grid) != set(itertools.product(tasks, ARMS))
    ):
        raise ValueError("Source ledgers must cover the same complete six-arm grid")
    for key, row in grid.items():
        screen = native[key]
        if row["state"] != "terminal" or screen["tech_pass"] != (
            row["status"] == "accepted"
        ):
            raise ValueError("Outcome and native ledger disagree")
        if screen["complete_no_leaf_box_issue"] and not screen["capture"]:
            raise ValueError("Native pass without a captured frame")
        row["native_screen_pass"] = screen["complete_no_leaf_box_issue"]
    original = {a: totals([grid[t, a] for t in tasks]) for a in ARMS}
    bounds_bytes = bounds_path.read_bytes()
    bounds = json.loads(bounds_bytes)
    if bounds["sources"][TECH_LEDGER] != tech_digest:
        raise ValueError("Endpoint bounds refer to a different batch")
    arm_limits = bounds["cohorts"]["all_219"]["after_common_repair"]["arms"]
    optimistic = {}
    for arm, r in original.items():
        limits = arm_limits[arm]
        if (
            limits["total"] != len(tasks)
            or limits["technical_acceptance"] != r["technical_pass"]
        ):
            raise ValueError("Endpoint bounds do not match technical results")
        upper = limits["upper_success_count"]
        optimistic[arm] = {
            "upper_possible_deliveries": upper,
            "lower_possible_deliveries": limits["lower_success_count"],
            "known_tokens_divided_by_delivery_upper_count": ratio(
                r["total_tokens"], upper
            ),
            "executor_seconds_divided_by_delivery_upper_count": ratio(
                r["executor_seconds"], upper
            ),
        }
    return {
        "accounting": {
            "all_assigned_tokens": "Sum of provider-reported usage, including unsuccessful outputs. Missing usage is counted separately.",
            "shared_usage": "Include a task only when every request intent of every compared arm has a token receipt.",
            "observed_pass": "All selected tasks remain in the yield denominator, including missing decisions and uncaptured seats.",
            "native_screen": "Full sample text and button labels matched and all observed leaf boxes inside the card without overlap.",
            "timing": "Historical executor seconds, including failures and waits, excluding device rendering.",
            "cost_unit": "Reported tokens; no conversion into monetary charges.",
        },
        "source_sha256": {
            "seats": tech_digest,
            "native": native_digest,
            "frozen_delivery_bounds": hashlib.sha256(bounds_bytes).hexdigest(),
        },
        "all_assigned": original,
        "six_arm_complete_usage": panels(grid, tasks, ARMS),
        "l5_l6_complete_usage": panels(grid, tasks, ("L5", "L6")),
        "original_delivery_cost_lower_bounds_if_nonzero_deliveries": optimistic,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("frozen_bounds", type=Path)
    parser.add_argument(
        "native_sha256", help="Pinned native digest from the failure-mode audit"
    )
    parser.add_argument("new_output", type=Path)
    args = parser.parse_args()
    report = audit(args.batch, args.frozen_bounds, args.native_sha256)
    with args.new_output.open("x", encoding="utf-8", newline="\n") as out:
        out.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
