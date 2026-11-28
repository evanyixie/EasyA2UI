"""Observed provider usage for the L1 first draft plus the registered model-repair follow-up."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import median

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from six_arms import cache_token_cost as metering
from six_arms.cost_frontier import TECH_LEDGER
from six_arms.fixed_content_repeats import check, digest
from six_arms.native_repeated_facts import PINS, checked_rows
from six_arms.paired_delivery_bounds import verified
from six_arms.rq2_repair_effects import PAIRED, PLAN
from six_arms.technical_yield import read_lines

FOLLOWUP_RECEIPT = "1352508f1fb9a3b3793bbbaa7b1b08349e8911876ec4df5909f142d3d1effc7a"
METRICS = (
    "request_intents",
    "confirmed_physical_attempts",
    "unknown_physical_attempt_intents",
    "provider_ids",
    "metered_requests",
    "unknown_usage_calls",
    *metering.METER,
)


def count(calls):
    row = metering.measured(calls)
    for call in calls:
        attempts = call["attempts"]
        check(
            attempts is None or type(attempts) is int and attempts >= 0,
            "Invalid provider-attempt count",
        )
        row["unknown_physical_attempt_intents"] += attempts is None
        row["confirmed_physical_attempts"] += attempts or 0
        row["provider_ids"] += call["provider"] is not None
    return row


def summarize(rows):
    totals = sum(rows, Counter())
    return {
        "assigned": len(rows),
        "tasks_with_any_intent": sum(r["request_intents"] > 0 for r in rows),
        "tasks_with_complete_usage": sum(not r["unknown_usage_calls"] for r in rows),
        **{k: totals[k] for k in METRICS},
    }


def pairs(left, right):
    check(left.keys() == right.keys(), "Pair roster differs")
    complete = [
        t
        for t in sorted(left)
        if not (left[t]["unknown_usage_calls"] or right[t]["unknown_usage_calls"])
    ]
    return {
        "assigned": len(left),
        "complete_usage_pairs": len(complete),
        "left_only_missing": sum(
            bool(left[t]["unknown_usage_calls"]) and not right[t]["unknown_usage_calls"]
            for t in left
        ),
        "right_only_missing": sum(
            not left[t]["unknown_usage_calls"] and bool(right[t]["unknown_usage_calls"])
            for t in left
        ),
        "both_missing": sum(
            bool(left[t]["unknown_usage_calls"] and right[t]["unknown_usage_calls"])
            for t in left
        ),
        "L1_M": summarize([left[t] for t in complete]),
        "comparator": summarize([right[t] for t in complete]),
        "median_L1_M_minus_comparator": {
            k: median(left[t][k] - right[t][k] for t in complete) if complete else None
            for k in ("request_intents", *metering.METER)
        },
        "all_assigned_intent_median_L1_M_minus_comparator": median(
            left[t]["request_intents"] - right[t]["request_intents"] for t in left
        )
        if left
        else None,
    }


def followup_call(slot, rr, local, provider):
    seal = json.loads((slot / "seal.json").read_bytes())
    intent = json.loads((slot / "intent.json").read_bytes())
    call = json.loads(verified(slot / "call.json", seal["receipt_sha256"]))
    check(
        call["stage"]
        == slot.name
        == seal["stage"]
        == intent["stage"]
        == f"r{rr['round']}"
        and all(
            seal[k] == intent[k]
            for k in ("messages_sha256", "local_request_id", "started_utc")
        ),
        "Follow-up request lineage differs",
    )
    verified(slot / "messages.json", seal["messages_sha256"])
    key = digest(intent["local_request_id"].encode())
    check(key not in local, "Repeated local request across generation or follow-up")
    local.add(key)
    usage = call["usage"] or {}
    request_id = call["request_id"]
    if rr["common_pass"] is None:
        check(
            seal["state"] == "failed"
            and call["http_status"] is None
            and not request_id
            and not usage
            and call["physical_attempts"] is None
            and seal["raw_sha256"] is None
            and rr["added_tokens"] is None,
            "Transport unknown contains unsupported billing or response evidence",
        )
    else:
        check(
            seal["state"] == "completed"
            and call["http_status"] == 200
            and bool(request_id)
            and call["physical_attempts"] == 1
            and usage["total_tokens"] == rr["added_tokens"]
            and usage["prompt_tokens_details"]["cached_tokens"]
            == usage[metering.CACHE[0]],
            "Metering differs from frozen round",
        )
        verified(slot / "response.txt", seal["raw_sha256"])
        key = digest(request_id.encode())
        check(key not in provider, "Repeated provider ID across studies")
        provider.add(key)
    return {
        "attempts": call["physical_attempts"],
        "provider": request_id,
        "tokens": {k: usage.get(k) for k in metering.METER},
    }


def report(batch):
    base = Path(batch)
    rq = base / "rq2_followup_20261127"
    formal = read_lines(base / TECH_LEDGER, metering.FROZEN_SEATS)
    ledger = {c["local"]: (r["arm"], c) for r in formal for c in r["calls"]}
    check(
        len(ledger) == sum(len(r["calls"]) for r in formal), "Duplicate original intent"
    )
    metering.verify_receipts(base, ledger)
    local, provider = (
        set(ledger),
        {c["provider"] for _, c in ledger.values() if c["provider"] is not None},
    )
    original = {
        arm: {r["task_id"]: count(r["calls"]) for r in formal if r["arm"] == arm}
        for arm in ("L1", "L5", "L6")
    }
    receipt = json.loads(verified(rq / "verification/receipt.json", FOLLOWUP_RECEIPT))
    check(
        receipt["formal_plan_sha256"] == PLAN and receipt["paired_sha256"] == PAIRED,
        "Wrong registered follow-up",
    )
    subjects = json.loads(verified(rq / "plan.json", PLAN))["plan"]["subjects"]
    registry = {r["id"]: r for r in subjects}
    registered_results = json.loads(
        verified(rq / "verification/paired219.private.json", PAIRED)
    )
    first = {
        r["task_id"]: r["artifact_sha256"]
        for r in checked_rows(
            base / "pre_score_evidence/endpoint/observations.private.jsonl",
            PINS["observations"],
        )
        if r["arm"] == "L1" and r["checkpoint"] == "raw_first"
    }
    check(
        len(registered_results) == len(registry) == len(subjects) == 219
        and all(g.keys() == registry.keys() for g in [*original.values(), first])
        and {r["id"] for r in registered_results} == registry.keys(),
        "Incomplete registered cohorts",
    )
    added, expected_slots = {}, set()
    for result in registered_results:
        t = result["id"]
        reg = registry[t]
        rounds = result["model_rounds"]
        check(
            first[t] == result["initial_sha256"] == reg["initial_sha256"]
            and reg["eligibility"] == result["model_eligibility"]
            and bool(rounds) == (reg["eligibility"] == "awaiting_first_repair")
            and [r["round"] for r in rounds] == list(range(1, len(rounds) + 1))
            and len(rounds) <= 2,
            "Unregistered original or attempts",
        )
        calls = []
        for rr in rounds:
            slot = rq / "state" / t / "calls" / f"r{rr['round']}"
            expected_slots.add(slot / "call.json")
            calls.append(followup_call(slot, rr, local, provider))
        added[t] = count(calls)
    check(
        expected_slots == set((rq / "state").glob("*/calls/*/call.json"))
        and len(expected_slots) == receipt["official_logged_intents"],
        "Unaccounted follow-up call",
    )
    combined = {t: original["L1"][t] + added[t] for t in registry}
    all_assigned = {
        name: summarize(list(grid.values()))
        for name, grid in {
            "L1_initial": original["L1"],
            "model_repair_added": added,
            "L1_M": combined,
            "L5": original["L5"],
            "L6": original["L6"],
        }.items()
    }
    official = json.loads(
        verified(rq / "verification/aggregate.json", receipt["aggregate_sha256"])
    )["extra_model_cost"]
    subtotal = all_assigned["model_repair_added"]
    check(
        (
            subtotal["request_intents"],
            subtotal["confirmed_physical_attempts"],
            subtotal["unknown_physical_attempt_intents"],
            subtotal["provider_ids"],
        )
        == (
            official["calls"],
            official["physical"],
            official["unknown_physical"],
            receipt["official_responses_replayed"],
        )
        and all(
            subtotal[k] == official["tokens"][k]["known_subtotal"]
            and subtotal["unknown_usage_calls"]
            == official["tokens"][k]["unknown_calls"]
            for k in metering.METER
        ),
        "Added cost differs from original follow-up verification",
    )
    return {
        "scope": "L1 one-shot generation once plus its actual, separately executed model repair on the same frozen first draft. L5 and L6 are the original generation runs. Metered token totals are observed subtotals including failed seats; missing usage is unknown.",
        "timing": "Generation and model repair were executed in different batches. Their sum is not a measured end-to-end latency; no full-chain latency or actual invoiced charge is available.",
        "sources": {
            "formal_seats": metering.FROZEN_SEATS,
            "followup_plan": PLAN,
            "paired": PAIRED,
            "followup_verification": FOLLOWUP_RECEIPT,
            "original_endpoints": PINS["observations"],
        },
        "all_assigned": all_assigned,
        "paired_complete": {
            f"L1_M_vs_{a}": pairs(combined, original[a]) for a in ("L5", "L6")
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    print(json.dumps(report(parser.parse_args().batch), indent=2, allow_nan=False))
