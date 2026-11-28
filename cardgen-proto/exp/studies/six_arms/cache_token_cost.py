"""Reconcile formal six-arm token receipts and price the measured usage at supplied rates."""

import argparse
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from six_arms import cost_frontier
from six_arms.technical_yield import ARMS, read_lines

TABLES = Path(__file__).resolve().parents[4] / "paper/out/tables"
PARENT = TABLES / "six_arm_cost_frontier.json"
OUTPUT = TABLES / "six_arm_cache_token_cost.json"
CACHE = ("prompt_cache_hit_tokens", "prompt_cache_miss_tokens")
METER = (*CACHE, *cost_frontier.TOKEN_FIELDS)
COUNTS = (
    "assigned",
    "request_intents",
    "metered_requests",
    "unknown_usage_calls",
    *METER,
)
FROZEN_SEATS = "8a14e60a953e8b7e445df7985c7512ceefff94f0fcc404cc62bf6a6c51f83e72"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def parent_digest(parent):
    raw = json.dumps(parent, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def check_identities(row):
    require(
        all(type(row[k]) is int and row[k] >= 0 for k in METER), "Invalid token count"
    )
    require(
        sum(row[k] for k in CACHE) == row["prompt_tokens"],
        "Cache and prompt totals differ",
    )
    require(
        row["prompt_tokens"] + row["completion_tokens"] == row["total_tokens"],
        "Token totals differ",
    )


def measured(calls):
    standard, missing = cost_frontier.usage(calls)
    counts = Counter(standard)
    counts.update(
        request_intents=len(calls),
        metered_requests=len(calls) - missing,
        unknown_usage_calls=missing,
    )
    for call in calls:
        t = call["tokens"]
        if t["total_tokens"] is None:
            require(
                all(t[k] is None for k in CACHE),
                "Partial cache metering on an unmetered request",
            )
        else:
            check_identities(t)
            counts.update({k: t[k] for k in CACHE})
    return counts


def verify_receipts(batch, ledger):
    """Every local intent must join once to the original sealed provider receipt, including transport failures."""
    seen = set()
    provider_ids = set()
    for path in (batch / "live").glob("*/L*/calls/*/call.json"):
        seal = json.loads(path.with_name("seal.json").read_bytes())
        body = path.read_bytes()
        require(
            hashlib.sha256(body).hexdigest() == seal["receipt_sha256"],
            "Receipt hash mismatch",
        )
        # The frozen technical ledger stores SHA-256 digests of both request IDs.
        local = hashlib.sha256(seal["local_request_id"].encode()).hexdigest()
        require(
            local in ledger and local not in seen,
            "Unmatched or duplicated local intent",
        )
        seen.add(local)
        arm, call = ledger[local]
        receipt = json.loads(body)
        require(
            (
                arm,
                call["phase"],
                call["state"],
                call["attempts"],
                call["http_status"],
                call["provider"],
            )
            == (
                path.parents[2].name,
                receipt["stage"],
                seal["state"],
                receipt["physical_attempts"],
                receipt["http_status"],
                hashlib.sha256(receipt["request_id"].encode()).hexdigest()
                if receipt["request_id"]
                else None,
            ),
            "Provider/ledger linkage mismatch",
        )
        if receipt["request_id"] is not None:
            require(
                receipt["request_id"] not in provider_ids,
                "Repeated provider request ID",
            )
            provider_ids.add(receipt["request_id"])
        usage = receipt["usage"] or {}
        require(
            all(usage.get(k) == call["tokens"][k] for k in METER),
            "Receipt/ledger metering differs",
        )
        if usage:
            require(
                receipt["request_id"] is not None and receipt["http_status"] == 200,
                "Unidentified metered response",
            )
            require(
                usage["prompt_tokens_details"]["cached_tokens"] == usage[CACHE[0]],
                "Alias for cache hits differs",
            )
    require(seen == set(ledger), "Missing original receipt")
    return len(provider_ids)


def recount(batch, parent):
    require(
        parent["source_sha256"]["seats"] == FROZEN_SEATS, "Wrong source six-arm table"
    )
    rows = read_lines(batch / cost_frontier.TECH_LEDGER, FROZEN_SEATS)
    tasks = {arm: set() for arm in ARMS}
    counters = {arm: Counter() for arm in ARMS}
    ledger = {}
    for row in rows:
        a, t = row["arm"], row["task_id"]
        require(a in tasks and t not in tasks[a], "Duplicated seat or invalid arm")
        tasks[a].add(t)
        counters[a].update(measured(row["calls"]))
        counters[a]["assigned"] += 1
        for call in row["calls"]:
            require(call["local"] not in ledger, "Repeated local intent")
            ledger[call["local"]] = (a, call)
    require(
        all(len(ts) == 219 and ts == tasks[ARMS[0]] for ts in tasks.values()),
        "Incomplete formal grid",
    )
    unique_provider_ids = verify_receipts(batch, ledger)
    by_arm = {a: {k: c[k] for k in COUNTS} for a, c in counters.items()}
    result = {
        "scope": "Original formal 219 tasks x six arms; every request intent, including failed seats. Separate supplementary runs are outside this ledger.",
        "metering": "Each metered receipt satisfies cache-hit + cache-miss = input and input + output = total. The provider's cached_tokens field is a second representation of cache-hit input and is counted once. All receipt bytes and local request joins were checked; unmetered calls retain unknown usage.",
        "pricing": "No invoice or historical rates are asserted. A supplied-rate simulation prices only known cache-hit input, cache-miss input and output, per million tokens.",
        "source_sha256": {
            "formal_seats": FROZEN_SEATS,
            "cost_frontier_canonical_json": parent_digest(parent),
        },
        "arms": by_arm,
        "all": {k: sum(a[k] for a in by_arm.values()) for k in COUNTS},
        "unique_provider_request_ids": unique_provider_ids,
    }
    verify_public(result, parent)
    return result


def verify_public(report, parent):
    require(
        report["source_sha256"]
        == {
            "formal_seats": parent["source_sha256"]["seats"],
            "cost_frontier_canonical_json": parent_digest(parent),
        },
        "Wrong parent table",
    )
    require(set(report["arms"]) == set(ARMS), "Incomplete six-arm table")
    for arm, row in report["arms"].items():
        check_identities(row)
        original = parent["all_assigned"][arm]
        require(
            all(
                row[k] == original[k]
                for k in (
                    "assigned",
                    "request_intents",
                    "unknown_usage_calls",
                    *cost_frontier.TOKEN_FIELDS,
                )
            ),
            "Existing cost table totals differ",
        )
        require(
            row["request_intents"]
            == row["metered_requests"] + row["unknown_usage_calls"],
            "Unbalanced coverage",
        )
    totals = report["all"]
    require(
        all(totals[k] == sum(a[k] for a in report["arms"].values()) for k in COUNTS),
        "Invalid combined totals",
    )
    check_identities(totals)
    require(
        totals["metered_requests"] == report["unique_provider_request_ids"],
        "Request-ID coverage differs",
    )


def estimate(report, rates, unit):
    require(
        unit.strip()
        and all(r.is_finite() and r >= 0 for r in rates)
        and len(rates) == 3,
        "Supply a unit and three finite nonnegative rates",
    )
    fields = (*CACHE, "completion_tokens")

    def cost(row):
        amount = sum(row[k] * r for k, r in zip(fields, rates, strict=True)) / Decimal(
            1_000_000
        )
        return {
            "known_usage_estimate": format(amount, "f"),
            "unpriced_request_intents": row["unknown_usage_calls"],
        }

    return {
        "basis": "User-specified simulation for reported usage only; actual billing unavailable.",
        "currency_or_unit": unit,
        "rates_per_million": {f: str(r) for f, r in zip(fields, rates, strict=True)},
        "all": cost(report["all"]),
        "arms": {a: cost(r) for a, r in report["arms"].items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser(
        "check", help="Check the public aggregate against the original published totals"
    )
    rebuild = sub.add_parser(
        "replay", help="Verify the sealed seats and original service receipts"
    )
    rebuild.add_argument("formal_batch", type=Path)
    rebuild.add_argument(
        "--new-output",
        type=Path,
        help="Write a new file; default compares to the public table",
    )
    sim = sub.add_parser(
        "estimate",
        help="Price metered requests with explicit hypothetical rates per million tokens",
    )
    sim.add_argument(
        "--rates",
        type=Decimal,
        nargs=3,
        required=True,
        metavar=("CACHE_HIT", "CACHE_MISS", "OUTPUT"),
    )
    sim.add_argument("--unit", required=True, help="Currency or other scenario unit")
    args = parser.parse_args()
    parent = json.loads(PARENT.read_bytes())
    if args.mode == "replay":
        result = recount(args.formal_batch, parent)
        if args.new_output:
            with args.new_output.open("x", encoding="utf-8", newline="\n") as f:
                f.write(
                    json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
                    + "\n"
                )
            return
        require(
            result == json.loads(OUTPUT.read_bytes()),
            "Cache usage differs from published aggregate",
        )
    else:
        result = json.loads(OUTPUT.read_bytes())
        verify_public(result, parent)
        if args.mode == "estimate":
            print(
                json.dumps(
                    estimate(result, args.rates, args.unit),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
    print("Formal cache usage reconciled.")


if __name__ == "__main__":
    main()
