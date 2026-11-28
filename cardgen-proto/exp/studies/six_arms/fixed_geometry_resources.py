"""Original resource receipts for the two geometry implementations on each identical L4 tree."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from six_arms import cache_token_cost as cost
from six_arms.cost_frontier import TECH_LEDGER
from six_arms.fixed_content_repeats import FORMAL_PLAN, canonical, check, digest
from six_arms.formal_stage_timing import INDEX, PINS, distribution
from six_arms.harness_v2 import model_stages
from six_arms.paired_delivery_bounds import verified
from six_arms.technical_yield import read_lines

PAIRS = "8beb265f91a2e9ca98d18ce1ad50acb40ad1ccd10736b701b3c26c028ac3df1c"
BRANCH = "41a6c515948bb59fe8d2d02a84e948e300b7aae1d804bd2a72675a3a7ba2ea5c"
PARAMETERS = {
    "concurrency": 1,
    "initial_http_attempts_per_stage": 1,
    "max_tokens_per_response": 8192,
    "model": "deepseek-flash",
    "temperature": 0,
    "thinking": False,
}


def clock_summary(rows):
    return {
        "model_geometry_wall_ms": distribution(r["model_ms"] for r in rows),
        "program_geometry_wall_ms": distribution(r["program_ms"] for r in rows),
        "model_minus_program_same_tree_ms": distribution(
            (r["model_ms"] - r["program_ms"] for r in rows), signed=True
        ),
        "model_callback_wall_ms": distribution(r["callback_ms"] for r in rows),
        "original_official_post_wall_ms": distribution(r["http_ms"] for r in rows),
    }


def summarize(rows, assigned):
    check(
        len(rows) <= assigned and len({r["task"] for r in rows}) == len(rows),
        "Duplicate or unexpected paired geometry seat",
    )
    calls = [r["call"] for r in rows]
    local = [c["local"] for c in calls]
    provider = [c["provider"] for c in calls if c["provider"] is not None]
    check(
        len(set(local)) == len(local) and len(set(provider)) == len(provider),
        "A request receipt was reused",
    )
    usage = cost.measured(calls)
    received = [r for r in rows if r["call"]["http_status"] == 200]
    message_counts = Counter(r["messages_sha256"] for r in rows)
    answered_counts = Counter(r["messages_sha256"] for r in received)
    return {
        "assigned": assigned,
        "same_tree_reached": len(rows),
        "upstream_unreached": assigned - len(rows),
        "model_stage_status": dict(
            sorted(Counter(r["model_status"] for r in rows).items())
        ),
        "all_attempted_geometry": clock_summary(rows),
        "same_trees_with_received_model_response": clock_summary(received),
        "requests": {
            "l4_model_local_intents": len(local),
            "distinct_provider_response_ids": len(provider),
            "known_physical_attempts": sum(
                c["attempts"] for c in calls if c["attempts"] is not None
            ),
            "unconfirmed_physical_attempt_counts": sum(
                c["attempts"] is None for c in calls
            ),
            "distinct_request_message_sha256": len(message_counts),
            "identical_message_groups_with_multiple_local_intents": sum(
                n > 1 for n in message_counts.values()
            ),
            "identical_message_groups_with_multiple_confirmed_responses": sum(
                n > 1 for n in answered_counts.values()
            ),
            "program_geometry_model_calls": 0,
            "extra_model_calls_in_same_tree_replay": 0,
        },
        "known_geometry_usage": {
            **{
                k: usage[k]
                for k in ("metered_requests", "unknown_usage_calls", *cost.METER)
            },
            "metered_requests_with_any_cached_input_tokens": sum(
                c["tokens"].get("prompt_cache_hit_tokens", 0) > 0
                for c in calls
                if c["tokens"]["total_tokens"] is not None
            ),
        },
    }


def read_stage(folder, outcome, pair, seat):
    run = outcome["execution"]
    stages = {s["stage"]: s for s in run["stages"]}
    check(len(stages) == len(run["stages"]), "Repeated stage")
    if pair["state"] == "upstream_not_reached":
        check(
            "geometry" not in stages
            and not {"content", "structure"} <= set(run["stages_completed"]),
            "Unreached branch has a geometry stage",
        )
        return None
    check(
        pair["state"] == "paired"
        and pair["new_model_calls"] == 0
        and {"content", "structure", "geometry"} <= stages.keys(),
        "Missing identical-tree entry",
    )
    originals = {k: stages[k]["product"] for k in ("content", "structure")}
    check(
        {k: digest(canonical(v)) for k, v in originals.items()}
        == pair["upstream_sha256"],
        "Program used a different content or tree",
    )
    stage = stages["geometry"]
    check(stage["owner"] == "model_solve", "Wrong geometry owner")
    sub = folder / "calls/geometry"
    seal = json.loads((sub / "seal.json").read_bytes())
    intent = json.loads((sub / "intent.json").read_bytes())
    check(
        seal["stage"] == intent["stage"] == "geometry"
        and seal["local_request_id"] == intent["local_request_id"]
        and seal["messages_sha256"] == intent["messages_sha256"],
        "Geometry intent/receipt mismatch",
    )
    messages = json.loads(verified(sub / "messages.json", seal["messages_sha256"]))
    enclosed = json.loads(messages[-1]["content"].removeprefix("本次输入："))
    check(
        digest(canonical(enclosed["source"])) == run["source_canonical_sha256"]
        and digest(canonical(enclosed["content"])) == pair["upstream_sha256"]["content"]
        and digest(canonical(enclosed["tree"])) == pair["upstream_sha256"]["structure"]
        and messages
        == stage["messages"]
        == model_stages.build_messages(
            "geometry",
            enclosed["source"],
            content=enclosed["content"],
            tree=enclosed["tree"],
        ),
        "Geometry request did not contain the identical upstream input",
    )
    call = json.loads(verified(sub / "call.json", seal["receipt_sha256"]))
    (meter,) = [c for c in seat["calls"] if c["phase"] == "geometry"]
    (ledger_stage,) = [s for s in seat["steps"] if s["phase"] == "geometry"]
    check(
        (stage["wall_ms"], stage["status"])
        == (ledger_stage["wall_ms"], ledger_stage["status"])
        and call == stage["receipt"]
        and call["http_ms"] == meter["http_ms"]
        and call["physical_attempts"] == meter["attempts"]
        and call["http_status"] == meter["http_status"]
        and call["requested_model"] == PARAMETERS["model"]
        and digest(intent["local_request_id"].encode()) == meter["local"],
        "Different geometry timing, model, request, or cost row",
    )
    request_id = call["request_id"]
    check(
        (digest(request_id.encode()) if request_id else None) == meter["provider"],
        "Different provider request",
    )
    check(
        all((call["usage"] or {}).get(k) == meter["tokens"][k] for k in cost.METER),
        "Different geometry token receipt",
    )
    if call["http_status"] == 200:
        check(
            call["returned_model"] == PARAMETERS["model"]
            and seal["state"] == "completed"
            and request_id
            and meter["attempts"] == 1
            and call["usage"]["prompt_tokens_details"]["cached_tokens"]
            == meter["tokens"]["prompt_cache_hit_tokens"],
            "Invalid official geometry response",
        )
        raw = verified(sub / "response.txt", seal["raw_sha256"])
        check(
            raw == stage["raw_text"].encode() and digest(raw) == stage["raw_sha256"],
            "Geometry response bytes changed",
        )
    else:
        check(
            stage["status"] == "callback_failed"
            and seal["state"] == "failed"
            and call["usage"] is None
            and seal["raw_sha256"] is None
            and stage["raw_text"] is None
            and not (sub / "response.txt").exists(),
            "Unconfirmed dispatch unexpectedly has a response or usage",
        )
    return {
        "task": pair["case"],
        "model_ms": stage["wall_ms"],
        "program_ms": pair["program_geometry_ms"],
        "callback_ms": stage["callback_wall_ms"],
        "http_ms": call["http_ms"],
        "call": meter,
        "model_status": stage["status"],
        "messages_sha256": seal["messages_sha256"],
    }


def audit(batch):
    batch = Path(batch)
    plan = json.loads(verified(batch / "live/plan.json", FORMAL_PLAN))
    check(plan["parameters"] == PARAMETERS, "Unexpected model parameters")
    verified(batch / "mechanism/same_tree.py", BRANCH)
    pairs = read_lines(
        batch / "tech_metrics/continuation_final/same_tree_private/pairs.private.jsonl",
        PAIRS,
    )
    cases = {r["case"] for r in pairs}
    check(
        len(pairs) == len(cases) == 219
        and cases == {r["id"] for r in plan["assignment"]["cases"]},
        "Different mechanism roster",
    )
    origins = {
        r["task_id"]: r["provenance"]
        for r in read_lines(batch / INDEX, PINS["observations"])
        if r["arm"] == "L4" and r["checkpoint"] == "raw_first"
    }
    seats = {
        r["task_id"]: r
        for r in read_lines(batch / TECH_LEDGER, cost.FROZEN_SEATS)
        if r["arm"] == "L4"
    }
    check(origins.keys() == seats.keys() == cases, "Missing original geometry seat")
    records = []
    for pair in pairs:
        task = pair["case"]
        proof = origins[task]
        check(
            proof["outcome_sha256"] == pair["original_outcome_sha256"],
            "Different original L4 seat",
        )
        path = batch / proof["outcome_ref"]
        outcome = json.loads(verified(path, proof["outcome_sha256"]))
        check(
            (outcome["task"], outcome["arm"], outcome["plan_sha256"])
            == (task, "L4", FORMAL_PLAN)
            and outcome["execution_sha256"]
            == proof["execution_sha256"]
            == digest(canonical(outcome["execution"])),
            "Original geometry outcome differs",
        )
        row = read_stage(path.parent, outcome, pair, seats[task])
        if row is not None:
            records.append(row)
    report = summarize(records, len(pairs))
    return {
        **report,
        "source_sha256": {
            "same_tree_rows": PAIRS,
            "branch_executor": BRANCH,
            "formal_plan": FORMAL_PLAN,
            "formal_costs": cost.FROZEN_SEATS,
            "outcome_index": PINS["observations"],
        },
        "timing": "Original model and archived local program geometry-stage wall times on identical accepted content and tree. "
        "The model clock includes its callback and network. Timings are from separate runs and exclude downstream rendering. "
        "All reached inputs include recorded wait for transport failures; the received-response subset also retains any model output rejected by the stage.",
        "reuse": "The model side uses its actual original L4 response or transport receipt. The program replays the upstream content and structure, then computes geometry locally. "
        "Prefix-cache hits are counted as input tokens and do not constitute full response reuse.",
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("batch", type=Path)
    args = cli.parse_args()
    print(json.dumps(audit(args.batch), sort_keys=True, indent=2))
