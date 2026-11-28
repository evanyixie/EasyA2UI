"""Pair a repaired one-shot strategy with the original L5 and L6 per assigned request."""

import argparse
import json
import sys
from collections import Counter
from itertools import product
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fixed_layout.paired_analysis import N_BOOT, SEED, analyze
from six_arms.cost_frontier import TECH_LEDGER
from six_arms.fixed_content_repeats import FORMAL_PLAN, canonical, check, digest
from six_arms.formal_reference_cost import ROOT, encode
from six_arms.paired_delivery_bounds import verified
from six_arms.paired_resource_differences import PINS
from six_arms.repair_budget import load_comparisons
from six_arms.repair_strategy_costs import report as observed_cost
from six_arms.rq2_repair_effects import PLAN as REPAIR_PLAN
from six_arms.technical_yield import DECISION, read_lines
from six_arms.web_geometry_inputs import load_inputs

STATES = ("pass", "fail", "missing")
STRATEGIES = ("L1-M", "L5", "L6")


def verdict(value):
    check(value is None or type(value) is bool, "Invalid technical decision")
    return "missing" if value is None else "pass" if value else "fail"


def model_result(case, initial_status):
    eligibility = case["model_eligibility"]
    rounds = case["model_rounds"]
    first, final = case["first_common"], case["model_common"]
    if eligibility == "awaiting_first_repair":
        check(
            first is False and case["initial_sha256"],
            "Unexpected original repair trigger",
        )
        check([r["round"] for r in rounds] in ([1], [1, 2]), "Invalid repair sequence")
        check(
            all(r["common_pass"] is False for r in rounds[:-1]),
            "Repair continued after stopping",
        )
        check(
            rounds[-1]["common_pass"] is final,
            "Repair decision differs from final attempt",
        )
        check(
            len(rounds) == 2 or final is not False, "Missing second permitted attempt"
        )
        return verdict(final)
    check(not rounds, "Untriggered or unavailable repair has attempts")
    if eligibility == "no_first_artifact":
        check(
            case["initial_sha256"] is None and first is None and final is None,
            "Expected unavailable original",
        )
        check(
            initial_status in ("callback_failed", "stage_rejected"),
            "Unsupported missing-original reason",
        )
        return DECISION[initial_status]
    if eligibility == "trigger_unknown":
        check(
            case["initial_sha256"] and first is None and final is None,
            "Expected unknown original trigger",
        )
        return "missing"
    check(
        eligibility == "no_trigger" and case["initial_sha256"] and first is True,
        "Invalid no-trigger original",
    )
    check(
        final is None or final is True,
        "No-trigger strategy changed a known passing original",
    )
    return "pass"


def load_rows(root):
    """Private custody join. Never publish task identifiers, family IDs, inputs or images."""
    repair_records = load_comparisons(root)
    rq = root / "rq2_followup_20261127"
    repair_plan = json.loads(verified(rq / "plan.json", REPAIR_PLAN))["plan"]
    registered = {r["id"]: r for r in repair_plan["subjects"]}
    check(
        repair_plan["source_plan"] == FORMAL_PLAN
        and len(registered) == len(repair_plan["subjects"]) == 219,
        "Registered repair cohort differs from original formal assignment",
    )
    seats = read_lines(root / TECH_LEDGER, PINS[TECH_LEDGER])
    statuses = {(s["task_id"], s["arm"]): s["status"] for s in seats}
    check(len(statuses) == len(seats) == 219 * 6, "Invalid frozen terminal seat roster")
    # load_inputs verifies the assignment, each family's input, all native artifact hashes,
    # and each initial/final link against the separately sealed endpoint observation.
    evidence = {(s.task, s.arm, s.checkpoint): s for s in load_inputs(root)}
    result = []
    for row in repair_records:
        task = row["id"]
        enrollment = registered[task]
        original = evidence[task, "L1", "raw_first"]
        program_terminal = evidence[task, "L1", "after_common_repair"]
        check(
            original.artifact_sha256
            == row["initial_sha256"]
            == enrollment["initial_sha256"]
            and program_terminal.artifact_sha256
            == row["program_sha256"]
            == enrollment["program_final_sha256"]
            and row["model_eligibility"] == enrollment["eligibility"],
            "Repair record does not refer to the frozen original or eligibility",
        )
        initial_status = statuses[task, "L1"]
        fid = digest(task.encode())
        rec = json.loads((root / "live" / fid / "L1/outcome.json").read_bytes())
        execution = rec["execution"]
        check(
            rec["task"] == task
            and rec["arm"] == "L1"
            and rec["plan_sha256"] == FORMAL_PLAN
            and digest(canonical(execution)) == rec["execution_sha256"]
            and row["source_sha256"] == execution["source_canonical_sha256"]
            and execution["status"] == initial_status,
            "RQ2 source or original formal status differs",
        )
        model = model_result(row, initial_status)
        if row["model_eligibility"] == "awaiting_first_repair":
            check(
                verdict(row["program_common"]) == DECISION[initial_status],
                "Common L1 terminal checks differ",
            )
            if model != "missing":
                terminal = row["model_sha256"]
                check(
                    terminal
                    == (
                        row["model_rounds"][-1]["candidate_sha256"]
                        if model == "pass"
                        else row["initial_sha256"]
                    ),
                    "Terminal is neither the accepted repair nor the retained original",
                )
                verified(rq / "state" / task / "terminal.a2ui.jsonl", terminal)
            else:
                check(
                    row["model_sha256"] is None,
                    "Unknown model reply reported a terminal",
                )
        item = {
            "task": task,
            "family": original.family,
            "eligibility": row["model_eligibility"],
            "initial_status": initial_status,
            "first_common": row["first_common"],
            "L1-M": model,
        }
        for arm in STRATEGIES[1:]:
            terminal = evidence[task, arm, "after_common_repair"]
            state = DECISION[statuses[task, arm]]
            check(
                terminal.family == original.family
                and (state != "pass" or terminal.artifact_sha256),
                "Accepted comparator missing verified artifact or mismatched family",
            )
            item[arm] = state
        result.append(item)
    check(len({r["family"] for r in result}) == 200, "Formal family count differs")
    return result


def compare(rows, arm):
    """Distinguish success observed on all assigned tasks from latent unknown outcomes."""
    roster = [{"task_id": r["task"], "family_id": r["family"]} for r in rows]
    pairs = Counter((r["L1-M"], r[arm]) for r in rows)

    def observed(value):
        return "pass" if value == "pass" else "fail"

    decisions = [
        {"task_id": r["task"], "A": observed(r["L1-M"]), "B": observed(r[arm])}
        for r in rows
    ]
    certified = analyze(roster, decisions)

    def net_range(all_absent_are_fail):
        lower = upper = 0
        for r in rows:
            a = (
                "fail"
                if all_absent_are_fail and r["eligibility"] == "no_first_artifact"
                else r["L1-M"]
            )
            b = r[arm]
            lower += int(b == "pass") - int(a != "fail")
            upper += int(b != "fail") - int(a == "pass")
        return [lower, upper]

    return {
        "assigned": len(rows),
        "paired_states_l1m_rows_other_columns": {
            l: {r: pairs[l, r] for r in STATES} for l in STATES
        },
        "both_certified": certified["both_pass"],
        "only_l1m_certified": certified["only_A_model_pass"],
        "only_other_certified": certified["only_B_program_pass"],
        "neither_certified": certified["both_fail"],
        "net_certified_other_minus_l1m": certified["only_B_program_pass"]
        - certified["only_A_model_pass"],
        "certified_difference_rate_other_minus_l1m": certified[
            "all_assigned_point_difference"
        ],
        "certified_difference_cluster_ci95": certified[
            "paired_cluster_percentile_ci95"
        ],
        "latent_net_other_minus_l1m_bounds": net_range(False),
        "all_five_no_original_counted_as_failed_net_bounds": net_range(True),
    }


def summarize(rows):
    tasks = {r["task"] for r in rows}
    check(
        len(tasks) == len(rows) and bool(rows) and all(r["family"] for r in rows),
        "Missing family or duplicate task",
    )
    check(
        all(r[arm] in STATES for r, arm in product(rows, STRATEGIES)), "Invalid result"
    )
    origins = Counter(r["eligibility"] for r in rows)
    return {
        "assigned_tasks": len(rows),
        "independent_families": len({r["family"] for r in rows}),
        "initial_model_repair_eligibility": dict(sorted(origins.items())),
        "original_common_passes": sum(r["first_common"] is True for r in rows),
        "no_original_reasons": dict(
            sorted(
                Counter(
                    r["initial_status"]
                    for r in rows
                    if r["eligibility"] == "no_first_artifact"
                ).items()
            )
        ),
        "terminal_counts": {
            arm: {s: sum(r[arm] == s for r in rows) for s in STATES}
            for arm in STRATEGIES
        },
        "pairs": {arm: compare(rows, arm) for arm in STRATEGIES[1:]},
        "bootstrap": {
            "method": "Resample entire registered families with replacement, preserving same-request pairing; each assigned task has equal weight within a draw. Percentile 95% for obtained technical success only.",
            "seed": SEED,
            "replicates": N_BOOT,
        },
        "scope": "Same original requests. L1-M retries a retained L1 original up to twice, whereas L5 and L6 start from the original request. The comparison of strategies was proposed in section 8; its exact paired analysis and missing-data sensitivities were specified after the original runs. Missing transport or an unassessable trigger stays unknown in the three-state comparison. Every assigned task counts toward obtained success. The RQ2 sensitivity treats all missing L1 originals as observed process failures. This is not an equal-budget, visual-quality or complete-delivery comparison.",
    }


def run(root):
    return summarize(load_rows(root))


def audit(root):
    quality = run(root)
    cost = observed_cost(root)
    check(
        all(
            r["assigned"] == quality["assigned_tasks"]
            for r in cost["all_assigned"].values()
        ),
        "Cost and technical result cohort sizes differ",
    )
    return {"technical_results": quality, "resource_costs": cost}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("formal_root", type=Path)
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    result = audit(args.formal_root.resolve())
    if args.output:
        with args.output.open("xb") as stream:
            stream.write(encode(result))
    else:
        published = ROOT / "paper/out/tables/model_repair_vs_layout_strategies.json"
        check(
            result == json.loads(published.read_bytes()), "Published comparison differs"
        )
    print("Verified", result["technical_results"]["assigned_tasks"], "paired tasks")
