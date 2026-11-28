"""Recompute the fixed-content, ten-draw layout study from the custodian's receipts."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

FORMAL_PLAN = "66a65da3c893fb2c0bd6ecd9feb8a09d669e95996e6692fffc635bdbe7c17d18"
REPEAT_PLAN = "89e5882deb5615a414671d69ae4f208aea5299333bff4af834cd09a9413ce041"
SELECTION = "819a5f79679ca24caa62137b8c5c9a647c94319e367e0ed7a25ed50405baf444"
ARMS = ("L5", "L6")
DRAWS = 10
WIRE = {
    "model": "deepseek-flash",
    "temperature": 1.0,
    "thinking": {"type": "disabled"},
    "stream": False,
    "max_tokens": 8192,
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode()


def read(path):
    return json.loads(path.read_bytes())


def check(condition, message):
    if not condition:
        raise ValueError(message)


def consistency(observations):
    """Count complete ten-draw agreements; absent outputs are never equal outputs."""
    check(len(observations) == DRAWS, "Incomplete set of scheduled repetitions")
    counts = Counter(x for x in observations if x is not None)
    observed = sum(counts.values())
    return {
        "observed_draws": observed,
        "all_ten_observed": int(observed == DRAWS),
        "all_ten_identical": int(observed == DRAWS and len(counts) == 1),
        "none_observed": int(observed == 0),
        "partially_observed": int(0 < observed < DRAWS),
        "two_or_more_observed_variants": int(len(counts) > 1),
    }


def summarize(groups):
    report = {"tasks": len(groups), "draws": sum(map(len, groups)), "agreement": {}}
    for name in ("structure", "first", "final"):
        total = Counter()
        for group in groups:
            total.update(consistency([r[name] for r in group]))
        report["agreement"][name] = dict(total)
    totals = [sum(r["accepted"] for r in group) for group in groups]
    report["technical"] = {
        "accepted_draws": sum(totals),
        "tasks_by_accepted_draws": dict(sorted(Counter(totals).items())),
        "terminal_statuses": dict(Counter(r["status"] for g in groups for r in g)),
        "failure_stages": dict(
            Counter(r["failed_stage"] for g in groups for r in g if r["failed_stage"])
        ),
    }
    report["median_task_median_structure_ms"] = round(
        median(median(r["ms"] for r in g) for g in groups), 3
    )
    report["median_draw_ms_excluding_content"] = round(
        median(r["layout_ms"] for group in groups for r in group), 3
    )
    return report


def artifact_hash(folder, execution, moment):
    card = execution[moment + "_native"]
    file = folder / (moment + "_native.a2ui.jsonl")
    if card is None:
        check(not file.exists(), "Unregistered native artifact")
        return None
    raw = file.read_bytes()
    check(
        raw == card["text"].encode() and digest(raw) == card["sha256"],
        "Native artifact mismatch",
    )
    return card["sha256"]


def add_provider_observation(
    path, original_message, structure, seen_ids, provider, fees
):
    calls = path / "calls/structure"
    c = read(calls / "call.json")
    msg = (calls / "messages.json").read_bytes()
    check(
        msg == original_message and json.loads(msg) == structure["messages"],
        "Structure messages differ",
    )
    check(
        c["actual_payload_sha256"]
        == digest(canonical({**WIRE, "messages": json.loads(msg)}))
        and c["physical_attempts"] == 1
        and c["stage"] == "structure"
        and c["endpoint"] == "https://api.deepseek.com/chat/completions"
        and c == structure["receipt"],
        "Structure request differs",
    )
    provider[str(c["http_status"])] += 1
    if c["http_status"] == 200:
        check(
            c["returned_model"] == WIRE["model"]
            and c["request_id"]
            and c["request_id"] not in seen_ids,
            "Reused or unverified model reply",
        )
        seen_ids.add(c["request_id"])
        check(
            digest((calls / "response.txt").read_bytes()) == structure["raw_sha256"],
            "Reply differs",
        )
        for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
            fees[k] += c["usage"][k]


def measure(batch, study):
    plan_path = batch / "live/plan.json"
    check(digest(plan_path.read_bytes()) == FORMAL_PLAN, "Formal allocation changed")
    cases = {c["id"]: c for c in read(plan_path)["assignment"]["cases"]}
    draws_sha = digest((study / "plan.json").read_bytes())
    check(draws_sha == REPEAT_PLAN, "Frozen repeat-study allocation changed")
    done = read(study / "complete.json")
    check(
        done["plan_sha256"] == draws_sha
        and done["terminal_seats"] == 240
        and not done["stop_flag"],
        "Study did not finish on the registered allocation",
    )
    selection_path = study / "selection.private.json"
    check(
        digest(selection_path.read_bytes()) == SELECTION,
        "Frozen twelve-task roster changed",
    )
    selection = read(selection_path)
    selected = selection["cases"]
    check(
        len(selected) == len({r["task"] for r in selected}) == 12,
        "Expected 12 distinct tasks",
    )
    seen_ids = set()
    ledger = defaultdict(dict)
    provider = Counter()
    fees = Counter()
    input_seal = hashlib.sha256()
    for sample in sorted(selected, key=lambda r: r["task"]):
        tid = sample["task"]
        case = cases[tid]
        check(
            all(
                case[k] == sample[k]
                for k in ("size", "input_sha256", "file_id", "registry_sha256")
            ),
            "Original assignment differs",
        )
        anchor = batch / "live" / case["file_id"] / "L5"
        orig = read(anchor / "outcome.json")
        check(
            orig["task"] == tid and orig["plan_sha256"] == FORMAL_PLAN,
            "Wrong original L5 seat",
        )
        frozen = orig["execution"]
        steps = {s["stage"]: s for s in frozen["stages"]}
        content = steps["content"]
        check(
            digest(canonical(content["product"])) == sample["content_sha256"],
            "Selected content differs from sampling lock",
        )
        check(
            len(content["product"]["items"]) + len(content["product"]["actions"])
            == sample["load"],
            "Selected load changed",
        )
        check(
            digest(canonical(frozen)) == orig["execution_sha256"],
            "Original formal outcome changed",
        )
        original_message = (anchor / "calls/structure/messages.json").read_bytes()
        check(
            json.loads(original_message) == steps["structure"]["messages"],
            "Mismatched original message",
        )
        original_raw = (anchor / "calls/content/response.txt").read_bytes()
        check(
            digest(original_raw) == content["raw_sha256"],
            "Original content reply mismatch",
        )
        slot_dir = study / "seats" / tid
        for arm in ARMS:
            group = []
            for rep in range(1, DRAWS + 1):
                path = slot_dir / arm / f"rep{rep:02}"
                receipt = read(path / "outcome.json")
                input_seal.update(
                    (digest((path / "outcome.json").read_bytes()) + "\n").encode()
                )
                job = receipt["job"]
                check(
                    (job["task"], job["arm"], job["rep"]) == (tid, arm, rep)
                    and receipt["plan_sha256"] == draws_sha,
                    "Seat allocation differs",
                )
                actual = receipt["execution"]
                check(
                    actual["arm"] == arm
                    and digest(canonical(actual)) == receipt["execution_sha256"],
                    "Execution changed",
                )
                phases = {s["stage"]: s for s in actual["stages"]}
                check(
                    actual["source_canonical_sha256"]
                    == frozen["source_canonical_sha256"]
                    and phases["content"]["raw_sha256"] == content["raw_sha256"]
                    and phases["content"]["product"] == content["product"],
                    "Selected content changed",
                )
                structure = phases["structure"]
                if arm == "L5":
                    check(
                        sorted(path.glob("calls/*/call.json"))
                        == [path / "calls/structure/call.json"],
                        "Unexpected provider phase",
                    )
                    add_provider_observation(
                        path, original_message, structure, seen_ids, provider, fees
                    )
                else:
                    check(
                        not list(path.glob("calls/*/call.json"))
                        and structure["owner"].startswith("program"),
                        "Unexpected L6 provider call",
                    )
                tree = (
                    digest(canonical(structure["product"]))
                    if structure["status"] == "completed"
                    else None
                )
                group.append(
                    {
                        "structure": tree,
                        "first": artifact_hash(path, actual, "first"),
                        "final": artifact_hash(path, actual, "final"),
                        "ms": structure["wall_ms"],
                        "layout_ms": actual["elapsed_ms"]
                        - phases["content"]["wall_ms"],
                        "accepted": actual["status"] == "accepted",
                        "status": actual["status"],
                        "failed_stage": actual["failed_stage"],
                    }
                )
            ledger[tid][arm] = group
    observed = set((study / "seats").glob("*/*/rep*/outcome.json"))
    check(len(observed) == 12 * 2 * DRAWS, "Unexpected or missing observations")
    pairs = {}
    hist = Counter(
        tuple(sum(r["accepted"] for r in x[a]) for a in ARMS) for x in ledger.values()
    )
    for mode in ("all", "any"):
        both = Counter()
        for arms in ledger.values():
            pair = tuple(
                (all if mode == "all" else any)(r["accepted"] for r in arms[a])
                for a in ARMS
            )
            both[
                {
                    (True, True): "both",
                    (True, False): "L5_only",
                    (False, True): "L6_only",
                    (False, False): "neither",
                }[pair]
            ] += 1
        pairs[mode + "_ten"] = dict(both)
    return {
        "design": "Exploratory, fixed accepted L5 content. Ten new structure draws or program executions per task and arm. Task-level summaries refer to these twelve tasks.",
        "formal_plan_sha256": FORMAL_PLAN,
        "selection_sha256": SELECTION,
        "sampling": {
            "population": selection["population"],
            "population_families": selection["population_families"],
            "seed": selection["seed"],
            "predraw_lock_sha256": selection["predraw_lock_sha256"],
            "strata": selection["strata"],
            "per_stratum": 2,
            "distinct_families": len({r["family"] for r in selected}),
        },
        "study_plan_sha256": draws_sha,
        "seat_receipts_digest": input_seal.hexdigest(),
        "provider_status": dict(provider),
        "independent_successful_request_ids": len(seen_ids),
        "structure_tokens": dict(fees),
        "results": {a: summarize([x[a] for x in ledger.values()]) for a in ARMS},
        "paired_technical_tasks": pairs,
        "paired_acceptance_histogram": [
            {"L5_passes_out_of_ten": a, "L6_passes_out_of_ten": b, "tasks": n}
            for (a, b), n in sorted(hist.items())
        ],
        "task_counts_by_size": dict(Counter(s["size"] for s in selected)),
        "size_breakdown": {
            size: {
                a: summarize(
                    [ledger[s["task"]][a] for s in selected if s["size"] == size]
                )
                for a in ARMS
            }
            for size in ("2x2", "2x4")
        },
    }


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("batch", type=Path)
    args.add_argument("study", type=Path)
    modes = args.add_mutually_exclusive_group()
    modes.add_argument("--check", type=Path)
    modes.add_argument("--output", type=Path)
    options = args.parse_args()
    result = measure(options.batch, options.study)
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if options.check:
        check(json.loads(encoded) == read(options.check), "Published aggregate differs")
        print("Fixed-content repeat aggregate matched.")
    elif options.output:
        options.output.write_text(encoded + "\n", encoding="utf-8", newline="\n")
    else:
        print(encoded)
