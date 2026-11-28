"""Score ten independently generated endpoints per assigned task and arm, offline.

The private batch is the sealed plan.json and seats/<task>/<arm>/repNN archive.
Development uses two tasks; a formal run requires a twelve-task frozen plan.
The public output contains per-arm task counts and no task-level results.
"""

import argparse
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path

if __package__:
    from .fixed_content_repeats import (
        WIRE,
        artifact_hash,
        canonical,
        check,
        digest,
        read,
    )
else:
    from fixed_content_repeats import (
        WIRE,
        artifact_hash,
        canonical,
        check,
        digest,
        read,
    )

ARMS = tuple(f"L{n}" for n in range(1, 7))
REPS = range(1, 11)
DEV_PLAN = "ae76d40791882ff821418622ee2f50fd7a13ee4fb4d67388e75fed31003ed5f5"
ENDPOINT = "https://api.deepseek.com/chat/completions"
C1 = ("domain", "size", "theme", "item_count", "item_types", "typed_hints")
C2 = ("raw_bytes", "surface_masked_bytes")
METRICS = tuple(f"content.{name}" for name in C1) + tuple(
    f"{stage}.{name}" for stage in ("first", "final", "accepted_final") for name in C2
)
NO_ARTIFACT = object()  # A verified terminal outcome rules out a produced artifact.
OPS = ("createSurface", "updateComponents", "updateDataModel")
DECODER = json.JSONDecoder()
SPACE = re.compile(r"[ \r\n\t]*")


def content_fields(execution):
    """Use accepted semantic fields only; never infer type, hint or theme from pixels."""
    values = dict.fromkeys(C1)
    step = next((s for s in execution["stages"] if s["stage"] == "content"), None)
    if not step or step["status"] != "completed":
        return values
    content = step["product"]
    for key in ("domain", "size", "theme"):
        if isinstance(content.get(key), str) and content[key]:
            values[key] = content[key]
    items = content.get("items")
    if not isinstance(items, list):
        return values
    values["item_count"] = len(items)  # Action entries are a separate array.
    if not items or not all(
        isinstance(x, dict) and isinstance(x.get("type"), str) and x["type"]
        for x in items
    ):
        return values
    values["item_types"] = tuple(sorted(x["type"] for x in items))
    if all(isinstance(x.get("content_hint"), str) for x in items):
        values["typed_hints"] = tuple(
            sorted(
                (
                    x["type"],
                    "".join(
                        c
                        for c in x["content_hint"]
                        if not c.isspace()
                        and not unicodedata.category(c).startswith("P")
                    ),
                )
                for x in items
            )
        )
    return values


def member_spans(text, start):
    """Find immediate member value spans of a previously parsed JSON object."""
    check(text[start] == "{", "Expected an object")
    pos = SPACE.match(text, start + 1).end()
    members = {}
    while text[pos] != "}":
        key, end = DECODER.raw_decode(text, pos)
        check(key not in members, "Ambiguous duplicate JSON key")
        pos = SPACE.match(text, end).end()
        check(text[pos] == ":", "Invalid JSON member")
        value_start = SPACE.match(text, pos + 1).end()
        _, end = DECODER.raw_decode(text, value_start)
        members[key] = (value_start, end)
        pos = SPACE.match(text, end).end()
        if text[pos] == "}":
            break
        check(text[pos] == ",", "Invalid JSON separator")
        pos = SPACE.match(text, pos + 1).end()
    return members


def mask_surface(blob):
    """Replace only the three envelope surfaceId value tokens; preserve all other bytes."""
    try:
        text = blob.decode("utf-8")
        spans, ids = [], []
        pos = SPACE.match(text).end()
        for op in OPS:
            msg, end = DECODER.raw_decode(text, pos)
            check(
                isinstance(msg, dict)
                and op in msg
                and not (set(OPS) - {op}) & msg.keys(),
                "Unrecognized A2UI envelope",
            )
            start, _ = member_spans(text, pos)[op]
            left, right = member_spans(text, start)["surfaceId"]
            value = msg[op]["surfaceId"]
            check(isinstance(value, str) and value, "Missing surface identifier")
            spans.append((left, right))
            ids.append(value)
            pos = SPACE.match(text, end).end()
        check(pos == len(text) and len(set(ids)) == 1, "Surface mismatch")
        for left, right in reversed(spans):
            text = text[:left] + '"__surface__"' + text[right:]
        return text.encode("utf-8")
    except (KeyError, IndexError, TypeError, ValueError, RecursionError):
        return None


def observations(folder, execution):
    result = {f"content.{k}": v for k, v in content_fields(execution).items()}
    status = execution["status"]
    for phase in ("first", "final"):
        value = artifact_hash(folder, execution, phase)
        masked = None
        if value is not None:
            normalized = mask_surface(
                (folder / f"{phase}_native.a2ui.jsonl").read_bytes()
            )
            if normalized is not None:
                masked = digest(normalized)
        elif status == "stage_rejected":
            value = masked = NO_ARTIFACT
        result[f"{phase}.raw_bytes"] = value
        result[f"{phase}.surface_masked_bytes"] = masked
    for name in C2:
        accepted = None
        if status == "accepted":
            check(
                result["final.raw_bytes"] is not None, "Accepted without final artifact"
            )
            accepted = result[f"final.{name}"]
        elif status in {"geometry_unresolved", "stage_rejected"}:
            accepted = NO_ARTIFACT
        result[f"accepted_final.{name}"] = accepted
    return result


def task_score(values):
    """A differing observed pair disproves equality even if other draws are unknown."""
    check(len(values) == 10, "Expected ten scheduled repetitions")
    present = [v for v in values if v is not None and v is not NO_ARTIFACT]
    absent = values.count(NO_ARTIFACT)
    if absent or len(set(present)) > 1:
        outcome = "no"
    elif len(present) == 10:
        outcome = "yes"
    else:
        outcome = "unknown"
    return outcome, len(present), absent


def wilson(success, total):
    z = 1.959963984540054
    p = success / total
    scale = 1 + z * z / total
    center = (p + z * z / (2 * total)) / scale
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / scale
    return [round(max(0, center - half), 6), round(min(1, center + half), 6)]


def summarize(groups, formal):
    scores = [task_score(g) for g in groups]
    total = len(scores)
    counts = Counter(row[0] for row in scores)
    observed = sum(n for _, n, _ in scores)
    absent = sum(n for _, _, n in scores)
    lo, hi = counts["yes"], total - counts["no"]
    return {
        "tasks_yes_no_unknown": [lo, counts["no"], counts["unknown"]],
        "tasks_decidable": total - counts["unknown"],
        "tasks_all_ten_observable": sum(n == 10 for _, n, _ in scores),
        "draws_observed_absent_unknown": [
            observed,
            absent,
            total * 10 - observed - absent,
        ],
        "assigned_rate_bounds": [round(lo / total, 6), round(hi / total, 6)],
        "wilson95": wilson(lo, total) if formal and total == 12 and lo == hi else None,
    }


def key(job):
    return job["task"], job["arm"], job["rep"]


def verify_roster(spec, n):
    selected = {s["task"]: s for s in spec["selected"]}
    check(len(selected) == len(spec["selected"]) == n, "Wrong number of frozen tasks")
    check(
        all(re.fullmatch(r"[A-Za-z0-9_-]+", t) for t in selected),
        "Unsafe task identifier",
    )
    jobs = spec["order"]
    check(all(type(j["rep"]) is int for j in jobs), "Noninteger repetition")
    keys = {key(j) for j in jobs}
    check(
        len(keys) == len(jobs) == spec["total_seats"]
        and keys == set(product(selected, ARMS, REPS)),
        "Incomplete or duplicate frozen seats",
    )
    check(
        spec["payload_except_messages"]["temperature"] == 1.0, "Expected temperature 1"
    )
    return selected


def execution_inputs(batch, plan_sha, spec, selection, formal, freeze_sha):
    if not formal:
        return selection
    check(
        spec.get("evidence_mode") == "custodian_schedule_only",
        "A synthetic dry run is not formal evidence",
    )
    check(
        len({s["family"] for s in selection.values()}) == 12,
        "Formal tasks must be independent groups",
    )
    path = batch / "execution_freeze.json"
    check(
        freeze_sha and path.is_file() and digest(path.read_bytes()) == freeze_sha,
        "Formal scoring requires a pinned execution freeze",
    )
    locked = read(path)
    check(
        locked["plan_sha256"] == plan_sha
        and canonical(locked["payload_except_messages"])
        == canonical(spec["payload_except_messages"])
        == canonical(WIRE)
        and re.fullmatch("[a-f0-9]{64}", locked["runner_sha256"]),
        "Execution freeze does not bind this schedule and runner",
    )
    check(
        locked["official_endpoint"]
        == spec.get("official_endpoint", ENDPOINT)
        == ENDPOINT,
        "Endpoint changed after scheduling",
    )
    rows = {s["task"]: s for s in locked["selected"]}
    check(
        rows.keys() == selection.keys() and len(locked["selected"]) == len(rows),
        "Execution freeze does not cover selected cases",
    )
    for task, item in rows.items():
        hashes = [
            item[k]
            for k in ("source_sha256", "registry_sha256", "source_canonical_sha256")
        ]
        check(
            set(item["initial_prompt_sha256"]) == set(ARMS)
            and all(
                re.fullmatch("[a-f0-9]{64}", v)
                for v in [*hashes, *item["initial_prompt_sha256"].values()]
            ),
            "Missing frozen source, registry or initial prompt",
        )
        for name in ("source_sha256", "registry_sha256"):
            check(
                selection[task].get(name, item[name]) == item[name],
                "Selected source identity changed",
            )
    return rows


def verify_source_material(locked, sources, registry):
    """Bind both the original file bytes and the harness' normalized source bytes."""
    check(
        sources is not None and registry is not None,
        "Supply source files and registry together",
    )
    entries = read(registry)["cases"]
    source_hashes = {}
    for task, item in locked.items():
        raw = (sources / f"{task}.json").read_bytes()
        check(digest(raw) == item["source_sha256"], "Source file hash differs")
        source_hashes[task] = digest(canonical(json.loads(raw)))
        check(
            entries[task]["id"] == task
            and digest(canonical(entries[task])) == item["registry_sha256"],
            "Frozen registry identity or entry hash differs",
        )
        if "source_canonical_sha256" in item:
            check(
                source_hashes[task] == item["source_canonical_sha256"],
                "Canonical source hash differs",
            )
    return source_hashes


def receipts(folder, execution, first_prompt, spec, seen):
    wire = spec["payload_except_messages"]
    called = [s for s in execution["stages"] if s.get("receipt") is not None]
    paths = set((folder / "calls").glob("*/call.json"))
    check(
        called and len(called) == len(paths), "Incomplete or unregistered call receipts"
    )
    for index, stage in enumerate(called):
        phase = stage["stage"]
        path = folder / "calls" / phase / "call.json"
        check(path in paths, "Unexpected stage receipt")
        paths.remove(path)
        c = read(path)
        messages = (path.parent / "messages.json").read_bytes()
        seal = read(path.parent / "seal.json")
        check(
            c == stage["receipt"]
            and c["stage"] == phase == seal["stage"]
            and c["temperature"] == 1.0
            and c["requested_model"] == wire["model"]
            and c["endpoint"] == spec["official_endpoint"]
            and c["actual_payload_sha256"]
            == digest(canonical({**wire, "messages": stage["messages"]}))
            and json.loads(messages) == stage["messages"]
            and seal["messages_sha256"] == digest(messages)
            and seal["receipt_sha256"] == digest(path.read_bytes()),
            "Mismatched physical request",
        )
        if index == 0:
            check(digest(messages) == first_prompt, "Initial prompt changed")
        local_id = seal["local_request_id"]
        check(local_id and local_id not in seen["local"], "Reused local model request")
        seen["local"].add(local_id)
        if c["http_status"] == 200:
            request_id = c["request_id"]
            check(
                request_id
                and request_id not in seen["provider"]
                and c["returned_model"] == wire["model"]
                and c["physical_attempts"] == 1,
                "Reused or mismatched model response",
            )
            seen["provider"].add(request_id)
            raw = (path.parent / "response.txt").read_bytes()
            check(
                seal["state"] == "completed"
                and digest(raw) == stage["raw_sha256"] == seal["raw_sha256"],
                "Response hash differs",
            )
            if phase == "content" and stage["status"] == "completed":
                check(
                    canonical(json.loads(raw)) == canonical(stage["product"]),
                    "Accepted semantic fields differ from the physical model reply",
                )
        else:
            check(
                seal["state"] == "failed"
                and not (path.parent / "response.txt").exists(),
                "Unexpected response to failed call",
            )


def score_batch(
    batch,
    plan_sha,
    cohort,
    execution_freeze_sha=None,
    sources=None,
    registry=None,
    runner=None,
):
    formal = cohort == "formal"
    check(cohort in {"formal", "development"}, "Unknown cohort")
    plan = batch / "plan.json"
    check(digest(plan.read_bytes()) == plan_sha, "Frozen plan hash differs")
    spec = read(plan)["specification"]
    if not formal:
        check(plan_sha == DEV_PLAN, "Unexpected development plan")
    selection = verify_roster(spec, 12 if formal else 2)
    locked = execution_inputs(
        batch, plan_sha, spec, selection, formal, execution_freeze_sha
    )
    verified_sources = {}
    if formal or sources is not None or registry is not None:
        verified_sources = verify_source_material(locked, sources, registry)
    if formal:
        execution_freeze = read(batch / "execution_freeze.json")
        check(
            runner is not None
            and digest(runner.read_bytes()) == execution_freeze["runner_sha256"],
            "Missing or changed frozen runner file",
        )
        spec = {**spec, "official_endpoint": ENDPOINT}
    freeze = read(batch / "freeze_receipt.json")
    check(
        freeze["plan_sha256"] == plan_sha
        and freeze["jobs"] == spec["total_seats"]
        and freeze["new_model_requests_at_freeze"] == 0
        and (not formal or freeze["execution_freeze_sha256"] == execution_freeze_sha),
        "Unverified freeze receipt",
    )
    read_paths = set()
    counts, seen = Counter(), defaultdict(set)
    cells = defaultdict(list)
    source_hashes = defaultdict(set)
    for job in spec["order"]:
        task, arm, rep = key(job)
        folder = batch / "seats" / task / arm / f"rep{rep:02}"
        path = folder / "outcome.json"
        row = {}
        if path.exists():
            read_paths.add(path)
            record = read(path)
            run = record["execution"]
            check(
                record["job"] == job
                and record["plan_sha256"] == plan_sha
                and run["arm"] == arm
                and record["execution_sha256"] == digest(canonical(run)),
                "Mismatched seat or execution",
            )
            source_hashes[task].add(run["source_canonical_sha256"])
            counts[run["status"]] += 1
            if task in verified_sources:
                check(
                    run["source_canonical_sha256"] == verified_sources[task],
                    "Executed a different source",
                )
            if formal:
                check(
                    record["execution_freeze_sha256"] == execution_freeze_sha
                    and run["source_canonical_sha256"]
                    == locked[task]["source_canonical_sha256"],
                    "Formal seat not bound to frozen input",
                )
            prompt = locked[task]["initial_prompt_sha256"][arm]
            receipts(folder, run, prompt, spec, seen)
            row = observations(folder, run)
        else:
            counts["no_terminal_receipt"] += 1
        cells[task, arm].append(row)
    check(
        all(len(values) == 1 for values in source_hashes.values()),
        "Input changed between draws",
    )
    check(
        read_paths == set((batch / "seats").glob("*/*/*/outcome.json")),
        "Unregistered seat on disk",
    )
    check(read_paths, "No endpoint executions available for scoring")
    complete = batch / "complete.json"
    if complete.exists():
        done = read(complete)
        check(
            done["plan_sha256"] == plan_sha
            and done["terminal_seats"] == len(read_paths),
            "Batch completion receipt mismatch",
        )
    return {
        "schema": "endpoint-stability-scores-v1",
        "cohort": cohort,
        "plan_sha256": plan_sha,
        "tasks": len(selection),
        "assigned_seats": spec["total_seats"],
        "terminal_statuses": dict(sorted(counts.items())),
        "stage_receipts": len(seen["local"]),
        "distinct_http200_reply_ids": len(seen["provider"]),
        "verified_source_files_and_registry_entries": len(verified_sources),
        "verified_runner_entrypoint_file": formal,
        "interpretation": {
            "content": "Accepted content-stage product only. Item count excludes separately listed actions. "
            "All six semantic fields are structurally unobservable in L1. No inferred theme, type "
            "or hint. An empty item list supports count zero only.",
            "first_final": "Artifact bytes regardless of geometry. Raw bytes include surface IDs. "
            "Masked bytes replace only top-level operation surfaceId value tokens.",
            "accepted_final": "Ten technically accepted final artifacts required. Geometry unknown remains unknown.",
            "bounds": "Bounds over assigned tasks per arm. A known nonproduction or observed unequal pair "
            "disproves ten identical products; missing-only draws cannot establish equality.",
            "inference": "Wilson only for complete binary outcomes in twelve formal tasks; descriptive, "
            "without adjustment for stratification. Development counts describe two tasks only.",
        },
        "arms": {
            arm: {
                name: summarize(
                    [[r.get(name) for r in cells[task, arm]] for task in selection],
                    formal,
                )
                for name in METRICS
            }
            for arm in ARMS
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--cohort", required=True, choices=("development", "formal"))
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument(
        "--execution-freeze-sha256",
        help="Required for formal receipts; covers exact source, "
        "registry, runner and per-arm initial prompts before dispatch.",
    )
    parser.add_argument(
        "--sources", type=Path, help="Frozen source directory, one <task>.json per case"
    )
    parser.add_argument(
        "--registry", type=Path, help="Frozen JSON with a cases map keyed by task"
    )
    parser.add_argument(
        "--runner",
        type=Path,
        help="Frozen entry-point file. Required for formal evidence.",
    )
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--output", type=Path)
    output.add_argument("--check", type=Path)
    args = parser.parse_args()
    report = score_batch(
        args.batch,
        args.plan_sha256,
        args.cohort,
        args.execution_freeze_sha256,
        args.sources,
        args.registry,
        args.runner,
    )
    if args.check:
        check(report == read(args.check), "Published aggregate differs")
        print("Aggregate verified")
    else:
        data = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_bytes(data.encode())
        else:
            print(data, end="")


if __name__ == "__main__":
    main()
