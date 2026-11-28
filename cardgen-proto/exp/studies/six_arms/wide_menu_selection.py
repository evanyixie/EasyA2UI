"""Freeze the content-only common menu and one program choice for every original wide request."""

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter_ns

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from six_arms import portable_layout_menus as menus
from six_arms.fixed_content_repeats import FORMAL_PLAN, canonical, check, digest
from six_arms.harness_v2 import model_stages, program_stages, trial
from six_arms.matched_structure_repeats import missing_prompt, received_reply
from six_arms.native_repeated_facts import PINS, checked_rows
from six_arms.paired_delivery_bounds import ROSTER, verified

SEED = "wide-common-menu-20261128-v1"
ROOT = Path(__file__).resolve().parents[4]


def frozen(path, value):
    raw = canonical(value) + b"\n"
    if path.exists():
        check(path.read_bytes() == raw, "Existing private packet differs")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as f:
            f.write(raw)
    return digest(raw)


def describe(node):
    if "ref" in node:
        return node["ref"]
    direction = {"row": "横排", "column": "竖排"}[node["kind"]]
    return direction + "(" + "、".join(describe(c) for c in node["children"]) + ")"


def packet(content, task):
    """No model tree, compiled geometry, original query or private source is consumed."""
    check(content["size"] == "2x4", "Only wide content is eligible")
    try:
        base = program_stages.program_route(content)
    except program_stages.StageError as exc:
        return None, None, exc.code
    entries, actions = program_stages._index(content)
    expected = menus.leaf_sequence(base["root"])
    choices = []
    ordered = sorted(
        menus.wide_menu(content, base), key=lambda t: digest(canonical([SEED, task, t]))
    )
    base_id = None
    for n, tree in enumerate(ordered, 1):
        program_stages._check_tree(tree, entries, actions)
        check(
            menus.leaf_sequence(tree["root"]) == expected,
            "Candidate changed the original leaf order",
        )
        option = f"R{n}"
        if tree == base:
            check(base_id is None, "Baseline is duplicated")
            base_id = option
        choices.append(
            {
                "id": option,
                "description": describe(tree["root"]),
                "tree": tree,
                "features": menus._features(tree, entries, canvas_width=300),
            }
        )
    check(
        len({canonical(c["tree"]) for c in choices}) == len(choices) and base_id,
        "Invalid menu deduplication or missing original tree",
    )
    return (
        {
            "canvas": {"width_vp": 300, "height_vp": 150},
            "content": content,
            "choices": choices,
        },
        base_id,
        None,
    )


def choose(wire):
    return min(wire["choices"], key=lambda c: menus.feature_rank(c["features"]))["id"]


def saved_choice(wire, wire_sha, previous=None):
    start = perf_counter_ns()
    chosen = choose(wire)
    elapsed = (perf_counter_ns() - start) / 1e6
    if previous is not None:
        check(
            previous["wire_sha256"] == wire_sha
            and previous["choice"] == chosen
            and math.isfinite(previous["elapsed_ms"])
            and previous["elapsed_ms"] >= 0,
            "Existing program choice is inconsistent",
        )
        return previous
    return {"choice": chosen, "wire_sha256": wire_sha, "elapsed_ms": elapsed}


def content_receipt(batch, case, raw_sha, sealed_outcome):
    t, fid = case["id"], case["file_id"]
    check(
        re.fullmatch(r"[a-zA-Z0-9_-]+", t) and digest(t.encode()) == fid,
        "Unsafe or mismatched task ID",
    )
    pkg = batch / "queue/package"
    req = json.loads(verified(pkg / "requests" / (fid + ".json"), case["input_sha256"]))
    reg = json.loads(
        verified(pkg / "registry" / (fid + ".json"), case["registry_sha256"])
    )
    check(
        req["size"] == case["size"] == "2x4"
        and req["_custody_original_envelope_sha256"] == raw_sha
        and reg["id"] == t
        and reg["input_sha"] == case["input_sha256"],
        "Invalid original inputs",
    )
    source = trial.source_for(req, reg["data_model"])
    folder = batch / "live" / fid / "L5"
    rec = json.loads(verified(folder / "outcome.json", sealed_outcome))
    ex = rec["execution"]
    check(
        rec["task"] == t
        and rec["arm"] == "L5"
        and rec["plan_sha256"] == FORMAL_PLAN
        and digest(canonical(ex)) == rec["execution_sha256"]
        and digest(canonical(source)) == ex["source_canonical_sha256"],
        "Wrong frozen L5 upstream receipt",
    )
    stage = ex["stages"][0]
    check(
        stage["stage"] == "content"
        and stage["messages"] == model_stages.build_messages("content", source),
        "Different model-visible input for original content",
    )
    slot = folder / "calls/content"
    if stage["status"] == "callback_failed":
        missing_prompt(slot, stage)
        return "content_transport_unknown", None, None, None
    reply = received_reply(slot, stage)
    try:
        selected = model_stages.parse_output("content", reply.wire.decode(), source)
    except (ValueError, KeyError, TypeError):
        check(
            reply.product is None and stage["status"] == "stage_rejected",
            "Unreproduced content rejection",
        )
        return "content_rejected", None, None, digest(reply.wire)
    check(
        stage["status"] == "completed"
        and selected == reply.product
        and selected["size"] == case["size"],
        "Replayed content differs from accepted frozen decision",
    )
    return (
        "ready",
        selected,
        {"source": source, "entry": ex["entry"]},
        digest(reply.wire),
    )


def freeze(batch, out):
    batch, out = batch.resolve(), out.resolve()
    check(
        not out.is_relative_to(ROOT) and out.is_relative_to(batch) and out != batch,
        "Use a dedicated child folder of the private formal batch",
    )
    plan = json.loads(verified(batch / "live/plan.json", FORMAL_PLAN))
    roster_rows = checked_rows(batch / "analysis/roster.jsonl", ROSTER)
    roster = {r["task_id"]: r for r in roster_rows}
    # Only the initial outcome hash is used from the independently sealed endpoint index.
    endpoints = {
        r["task_id"]: r["provenance"]["outcome_sha256"]
        for r in checked_rows(
            batch / "pre_score_evidence/endpoint/observations.private.jsonl",
            PINS["observations"],
        )
        if r["arm"] == "L5" and r["checkpoint"] == "raw_first"
    }
    cases = plan["assignment"]["cases"]
    check(
        len(cases) == len(roster_rows) == len(roster) == 219
        and {c["id"] for c in cases} == roster.keys() == endpoints.keys(),
        "Wrong formal roster",
    )
    wide = [c for c in cases if c["size"] == "2x4"]
    check(len(wide) == 50, "Unexpected size stratum")
    program_file = out / "program_choices.json"
    prior = json.loads(program_file.read_bytes()) if program_file.exists() else {}
    program = {}
    cohort = []
    queue = []
    for case in wide:
        tid = case["id"]
        state, content, private, raw_hash = content_receipt(
            batch, case, roster[tid]["raw_request_sha256"], endpoints[tid]
        )
        row = {
            "task_id": tid,
            "file_id": case["file_id"],
            "family": roster[tid]["family"],
            "status": state,
            "content_response_sha256": raw_hash,
            "content_sha256": None,
            "private_input_sha256": None,
            "wire_sha256": None,
            "options": [],
            "baseline_id": None,
        }
        cohort.append(row)
        if state != "ready":
            continue
        wire, baseline, error = packet(content, tid)
        row["content_sha256"] = digest(canonical(content))
        row["private_input_sha256"] = frozen(
            out / "private_inputs" / (tid + ".json"), private
        )
        if wire is None:
            row.update(status="empty", reason=error)
            continue
        path = out / "shared" / (tid + ".json")
        wire_sha = frozen(path, wire)
        options = [c["id"] for c in wire["choices"]]
        row.update(
            status="multiple" if len(options) > 1 else "forced",
            wire_sha256=wire_sha,
            options=options,
            baseline_id=baseline,
        )
        # Load the exact same sorted bytes the model runner will use. Time selection only.
        program[tid] = saved_choice(
            json.loads(verified(path, wire_sha)), wire_sha, prior.get(tid)
        )
        if len(options) > 1:
            queue.append(
                {
                    "task_id": tid,
                    "wire_path": str(path),
                    "wire_sha256": wire_sha,
                    "options": options,
                }
            )
    counts = dict(sorted(Counter(row["status"] for row in cohort).items()))
    cohort_hash = frozen(
        out / "cohort.private.json",
        {"formal_plan_sha256": FORMAL_PLAN, "seed": SEED, "cases": cohort},
    )
    program_hash = frozen(program_file, program)
    index_hash = frozen(out / "index.json", {"rows": queue})
    result = {
        "formal_plan_sha256": FORMAL_PLAN,
        "cohort_sha256": cohort_hash,
        "program_sha256": program_hash,
        "index_sha256": index_hash,
        "method_sha256": {
            Path(mod.__file__).stem: digest(
                Path(mod.__file__).read_bytes().replace(b"\r\n", b"\n")
            )
            for mod in (
                sys.modules[__name__],
                menus,
                program_stages,
                model_stages,
                trial,
            )
        },
        "counts": counts,
    }
    frozen(out / "selection_freeze.json", result)
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("batch", type=Path)
    cli.add_argument("out", type=Path)
    args = cli.parse_args()
    print(json.dumps(freeze(args.batch, args.out), indent=2))
