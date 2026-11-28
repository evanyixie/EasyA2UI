"""Count repair attempts, proposals, rollbacks and final geometry defects from sealed evidence."""

import argparse
import json
import sys
from collections import Counter
from itertools import product
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from six_arms.composite_cost_stats import ARMS
from six_arms.fixed_content_repeats import FORMAL_PLAN, check, digest
from six_arms.formal_reference_cost import encode
from six_arms.paired_delivery_bounds import verified
from six_arms.repair_budget import load_comparisons, replay

TABLE = Path(__file__).resolve().parents[4] / "paper/out/tables/formal_repair_b5.json"


def indicators(rows):
    statuses = Counter(r["exit_status"] for r in rows)
    measured = [r for r in rows if r["before"] is not None and r["after"] is not None]
    triggered = [r for r in rows if r["rounds"]]
    attempts = [x for r in triggered for x in r["rounds"]]
    count = len(attempts)
    actions = sum(len(x["actions"]) for x in attempts)
    rounds = {}
    for number in (1, 2):
        subset = [x for x in attempts if x["round"] == number]
        rounds[str(number)] = {
            "proposed": len(subset),
            "committed": sum(x["committed"] for x in subset),
            "proposals_with_new_geometry_violations": sum(
                bool(x["introduced_by_repair"]) for x in subset
            ),
        }
    final_new = []
    for r in measured:
        before = {(i["id"], i["code"]) for i in r["before"]}
        after = {(i["id"], i["code"]) for i in r["after"]}
        final_new.append(after - before)
    return {
        "assigned": len(rows),
        "exit_status": dict(sorted(statuses.items())),
        "first_artifacts": sum(r["first_sha256"] is not None for r in rows),
        "original_and_final_geometry_assessed": len(measured),
        "assessed_originals_with_violations": sum(bool(r["before"]) for r in measured),
        "seats_with_attempts": len(triggered),
        "attempts": count,
        "actions_proposed": actions,
        "actions_per_proposal": actions / count if count else None,
        "actions_per_triggered_seat": actions / len(triggered) if triggered else None,
        "actions_in_committed_proposals": sum(
            len(x["actions"]) for x in attempts if x["committed"]
        ),
        "rounds": rounds,
        "committed": sum(r["committed"] for r in rows),
        "tried_and_returned_original": sum(
            not r["committed"] and r["first_sha256"] == r["final_sha256"]
            for r in triggered
        ),
        "seats_with_a_proposal_introducing_a_violation": sum(
            any(x["introduced_by_repair"] for x in r["rounds"]) for r in triggered
        ),
        "proposals_with_new_geometry_violations": sum(
            bool(x["introduced_by_repair"]) for x in attempts
        ),
        "new_node_code_pairs_summed_over_proposals": sum(
            len(x["introduced_by_repair"]) for x in attempts
        ),
        "nodes_with_new_violations_summed_over_proposals": sum(
            len({i["id"] for i in x["introduced_by_repair"]}) for x in attempts
        ),
        "proposals_worsening_existing_geometry_violations": sum(
            bool(x["worsened"]) for x in attempts
        ),
        "seats_with_new_violations_in_final_artifact": sum(
            bool(delta) for delta in final_new
        ),
        "new_node_code_pairs_in_final_artifacts": sum(
            len(delta) for delta in final_new
        ),
    }


def summarize(rows, expected=219):
    keys = {(r["task"], r["arm"]) for r in rows}
    tasks = {r["task"] for r in rows}
    check(
        len(tasks) == expected
        and len(rows) == len(keys)
        and keys == set(product(tasks, ARMS)),
        "Incomplete repair assignment",
    )
    return {
        "all": indicators(rows),
        "by_arm": {
            arm: indicators([r for r in rows if r["arm"] == arm]) for arm in ARMS
        },
    }


def run(batch):
    from six_arms.fixed_tree_density import locked_engine

    plan = json.loads(verified(batch / "live/plan.json", FORMAL_PLAN))
    engine, measurement_hashes = locked_engine(plan["dependencies"])
    allocation = engine.native.dependency_files()["space_allocation.py"]
    from six_arms.formal_repair_receipts import load_repair_rows
    from six_arms.rq2_repair_effects import audit

    rows = load_repair_rows(batch, replay_geometry=True)
    assignments = load_comparisons(batch)
    roster = {r["task"]: r for r in rows if r["arm"] == "L1"}
    check(set(roster) == {r["id"] for r in assignments}, "RQ2 and six-arm tasks differ")
    for r in assignments:
        original = roster[r["id"]]
        check(
            original["first_sha256"] == r["initial_sha256"],
            "RQ2 and L1 initial bytes differ",
        )
        if r["program_common"] is not None:
            check(
                original["final_sha256"] == r["program_sha256"],
                "Conflicting program return bytes",
            )
    counters = summarize(rows)
    paired = replay(assignments)
    check(
        paired["program_only"]["pass"] == 91
        and paired["model_budget_2"]["pass"] == 101
        and paired["program_first_budget_2"]["pass"] == 116,
        "Published repair outcomes differ",
    )
    per_seat = sorted(
        (r["task"], r["arm"], r["first_sha256"], r["final_sha256"], indicators([r]))
        for r in rows
    )
    return {
        "measurement_sha256": measurement_hashes,
        "replay_space_allocation_sha256": digest(allocation.read_bytes()),
        "formal_common_geometry_repair": counters,
        "formal_per_seat_metrics_sha256": digest(encode(per_seat)),
        "same_initial_repair_budget": paired,
        "same_initial_candidate_and_terminal_audit": audit(batch),
        "scope": "The six-arm B5 counts the common geometry repair after the initial artifact. All proposals are compared to that same initial artifact. An issue identity is a node id and geometry code. A changed property in one proposal counts as one action. Source or protocol rejection before the geometry exit provides no geometry estimate. The independent repair study reuses the L1 initial artifacts; counts in the two studies overlap.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_batch", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Write a new anonymous table. Default verifies the published table.",
    )
    args = parser.parse_args()
    public = run(args.formal_batch.resolve())
    if args.output:
        with args.output.open("xb") as f:
            f.write(encode(public))
    else:
        check(public == json.loads(TABLE.read_bytes()), "Published B5 result differs")
    print(
        "Verified",
        public["formal_common_geometry_repair"]["all"]["assigned"],
        "formal repair assignments",
    )
