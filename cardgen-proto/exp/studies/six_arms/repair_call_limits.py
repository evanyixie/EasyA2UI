"""Same-assignment, same maximum model requests per task, with early stopping."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fixed_layout.paired_analysis import analyze
from six_arms import repair_strategy_comparison as strategy
from six_arms.cache_token_cost import FROZEN_SEATS
from six_arms.cost_frontier import TECH_LEDGER
from six_arms.fixed_content_repeats import check
from six_arms.formal_reference_cost import ROOT, encode
from six_arms.repair_budget import load_comparisons
from six_arms.technical_yield import DECISION, read_lines

TABLE = ROOT / "paper/out/tables/repair_call_limits.json"


def repair_choice(record, case, allow_model):
    """Prefer the actual accepted program terminal. Any later model call uses the original."""
    program = DECISION[record["initial_status"]]  # Formal terminal after common repair.
    eligible = case["model_eligibility"] == "awaiting_first_repair"
    if not allow_model or not eligible or program == "pass":
        return program, []
    check(program == "fail", "Program repair trigger not determined")
    first = case["model_rounds"][0]
    check(first["round"] == 1, "Expected the first archived rewrite")
    return strategy.verdict(first["common_pass"]), [first["added_tokens"]]


def score(rows, limit):
    roster = [{"task_id": r["task"], "family_id": r["family"]} for r in rows]
    arms = ("whole_card", "staged")
    pairs = [
        {
            "task_id": r["task"],
            "A": r["whole_card"][0],
            "B": r["staged"][0],
            "missing_reason": "transport or technical assessment unavailable in the original ledger",
        }
        for r in rows
    ]
    evidence = analyze(roster, pairs)
    obtained = analyze(
        roster,
        [
            {
                "task_id": p["task_id"],
                "A": "pass" if p["A"] == "pass" else "fail",
                "B": "pass" if p["B"] == "pass" else "fail",
            }
            for p in pairs
        ],
    )
    costs = {}
    for arm in arms:
        states = Counter(r[arm][0] for r in rows)
        counts = Counter(len(r[arm][1]) for r in rows)
        values = [n for r in rows for n in r[arm][1]]
        check(all(1 <= count <= limit for count in counts), "Exceeded the task cap")
        check(
            all(n is None or type(n) is int and n >= 0 for n in values), "Invalid usage"
        )
        costs[arm] = {
            "states": {state: states[state] for state in strategy.STATES},
            "tasks_by_request_count": {str(k): counts[k] for k in sorted(counts)},
            "request_intents": len(values),
            "metered_tokens": sum(n for n in values if n is not None),
            "unmetered_requests": values.count(None),
        }
    return {
        "assigned": len(roster),
        "families": len({r["family_id"] for r in roster}),
        "maximum_request_intents_per_task": limit,
        "strategies": costs,
        "both_obtained": obtained["both_pass"],
        "only_whole_card_obtained": obtained["only_A_model_pass"],
        "only_staged_obtained": obtained["only_B_program_pass"],
        "neither_obtained": obtained["both_fail"],
        "obtained_difference_staged_minus_whole_card": obtained[
            "all_assigned_point_difference"
        ],
        "family_bootstrap_ci95_for_obtained_difference": obtained[
            "paired_cluster_percentile_ci95"
        ],
        "difference_bounds_with_unknown_outcomes": evidence[
            "all_assigned_difference_bounds_B_minus_A"
        ],
    }


def run(root):
    records = strategy.load_rows(root)
    cases = {row["id"]: row for row in load_comparisons(root)}
    calls = {
        (row["task_id"], row["arm"]): [
            c["tokens"]["total_tokens"] for c in row["calls"]
        ]
        for row in read_lines(root / TECH_LEDGER, FROZEN_SEATS)
    }
    result = {}
    for limit, staged in ((1, "L6"), (2, "L5")):
        rows = []
        for record in records:
            t = record["task"]
            status, extra = repair_choice(record, cases[t], limit == 2)
            check(len(calls[t, "L1"]) == 1, "Expected one original model intention")
            rows.append(
                {
                    "task": t,
                    "family": record["family"],
                    "whole_card": (status, calls[t, "L1"] + extra),
                    "staged": (record[staged], calls[t, staged]),
                }
            )
        result[staged] = score(rows, limit)
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("formal_root", type=Path)
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    results = run(args.formal_root)
    if args.output:
        with args.output.open("xb") as stream:
            stream.write(encode(results))
    else:
        check(
            json.loads(TABLE.read_bytes()) == results,
            "Published call-cap comparison differs",
        )
    print("Verified two request caps on", results["L6"]["assigned"], "paired requests")
