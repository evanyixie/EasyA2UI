"""Replay a program-first layout policy using paired, sealed structure calls."""

import argparse
import hashlib
import json
import statistics
from pathlib import Path


def read_json(path, sha=None):
    data = path.read_bytes()
    if sha is not None and hashlib.sha256(data).hexdigest() != sha:
        raise ValueError(f"Receipt mismatch for {path.name}")
    return json.loads(data)


def aggregate(timings, calls, policy):
    records = [item[policy] for item in timings]
    misses = [i for i, row in enumerate(records) if not row["passes"]["program"]]
    rescued = sum(records[i]["passes"]["model"] for i in misses)
    totals_ms = [
        row["program_ms"] + (0 if row["passes"]["program"] else row["model_ms"])
        for row in records
    ]
    usage = [calls[item["task"]] for item in timings]
    return {
        "assigned": len(records),
        "program_pass": len(records) - len(misses),
        "model_pass": sum(row["passes"]["model"] for row in records),
        "fallback_calls": len(misses),
        "rescued": rescued,
        "neither": len(misses) - rescued,
        "program_or_fallback_pass": len(records) - len(misses) + rescued,
        "all_model_structure_tokens": sum(u["total_tokens"] for u in usage),
        "fallback_structure_tokens": sum(usage[i]["total_tokens"] for i in misses),
        "estimated_serial_mean_ms": round(statistics.mean(totals_ms), 2),
        "estimated_serial_median_ms": round(statistics.median(totals_ms), 2),
    }


def replay(batch, public_table):
    folder = batch / "same_content_l56_followup"
    timing = folder / "timing"
    sources = read_json(public_table)["sources_sha256"]
    timing_summary = read_json(timing / "summary.json", sources["timing_summary"])
    design = read_json(timing / "design.json", timing_summary["rules"])
    seals = read_json(timing / "source_receipts.private.json", design["sealed_replies"])
    timings = read_json(timing / "times.private.json", sources["paired_timings"])
    pairs = read_json(folder / "paired187.private.json", sources["joined_cases"])
    plan = read_json(batch / "live/plan.json")
    cases = {row["id"]: row for row in plan["assignment"]["cases"]}
    fixed = {row["task"]: row for row in pairs}
    ids = {row["task"] for row in timings}
    if len(ids) != len(timings) or len(fixed) != len(pairs) or ids != fixed.keys() or ids != seals.keys():
        raise ValueError("Pair, time or receipt roster mismatch")
    calls = {}
    for item in timings:
        task = item["task"]
        case, pair, seal = cases[task], fixed[task], seals[task]
        if not (case["input_sha256"] == seal["request"] and
                pair["content_sha256"] == seal["content"] == item["content_sha"]):
            raise ValueError("Input or selected content mismatch")
        for name, model, program in (("compatible", "l5", "l6"), ("strict", "strict_model", "strict_program")):
            if item[name]["passes"] != {"model": pair[model], "program": pair[program]}:
                raise ValueError("Frozen decisions disagree with timing records")
        call = read_json(batch / "live" / case["file_id"] / "L5/calls/structure/call.json", seal["call_receipt"])
        if (call["stage"], call["physical_attempts"], call["http_status"]) != ("structure", 1, 200):
            raise ValueError("Expected one observed structure response")
        u = call["usage"]
        if u["total_tokens"] != u["prompt_tokens"] + u["completion_tokens"]:
            raise ValueError("Unreconciled token usage")
        calls[task] = u
    return {policy: aggregate(timings, calls, policy) for policy in ("compatible", "strict")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_batch", type=Path)
    parser.add_argument("public_table", type=Path)
    args = parser.parse_args()
    print(json.dumps(replay(args.formal_batch, args.public_table), indent=2))
