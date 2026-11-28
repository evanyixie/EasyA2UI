"""Compare layout ownership on every archived content draw with a model structure arm.

Run the custodian CLI in a fresh interpreter. The two methods see the same
accepted content on each draw. No missing model replies are substituted.
"""

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

if __package__:
    from . import matched_structure_repeats as history
    from .fixed_content_repeats import FORMAL_PLAN
else:
    import matched_structure_repeats as history
    from fixed_content_repeats import FORMAL_PLAN


DONORS = ("L2", "L3", "L4", "L5")
load_batch = history.load_batch
verify = history.verify


@dataclass
class Draw:
    task: str
    donor: str
    size: str
    source: dict
    registry: dict
    original: dict
    folder: Path
    content: history.Reply | None
    structure: history.Reply | None
    status: str


def iter_draws(base, prep, plan_sha, package, cases):
    plan = base / "live/plan.json"
    verify(
        history.sha(plan.read_bytes()) == FORMAL_PLAN, "Wrong formal data or settings"
    )
    ids = set()
    for case in cases:
        task = case["id"]
        raw, registry = package(task)
        prep.queue.ensure_identity(case, raw, registry)
        source = prep.engine.trial.source_for(json.loads(raw), registry["data_model"])
        expected_content = prep.engine.model.build_messages("content", source)
        for donor in DONORS:
            folder = base / "live" / case["file_id"] / donor
            original = prep.queue.read_outcome(
                folder / "outcome.json", task, donor, plan_sha
            )
            stages = {stage["stage"]: stage for stage in original["stages"]}
            stage = stages["content"]
            verify(stage["messages"] == expected_content, "Unexpected content prompt")
            slot = folder / "calls/content"
            content = structure = None
            if stage["status"] == "callback_failed":
                history.missing_prompt(slot, stage)
                status = "content_unknown"
            else:
                content = history.received_reply(slot, stage)
                status = "content_rejected" if content.product is None else "ready"
            if status == "ready":
                step = stages["structure"]
                # The saved outcome sorts mapping keys. Rebuild their original wire
                # order before checking the serialized request sent to the selector.
                first = prep.engine.model.parse_output(
                    "content", content.wire.decode(), source
                )
                verify(
                    first == content.product,
                    "Content reply disagrees with the accepted record",
                )
                prompt = prep.engine.model.build_messages(
                    "structure", source, content=first
                )
                verify(
                    step["messages"] == prompt,
                    "Structure message does not use the chosen content",
                )
                slot = folder / "calls/structure"
                if step["status"] == "callback_failed":
                    history.missing_prompt(slot, step)
                    status = "structure_unknown"
                else:
                    structure = history.archived(slot, step)
            else:
                verify(
                    "structure" not in stages and original["failed_stage"] == "content",
                    "Invalid upstream stop",
                )
            for reply in (content, structure):
                if reply:
                    verify(reply.request_id not in ids, "Repeated provider request ID")
                    ids.add(reply.request_id)
            yield Draw(
                task,
                donor,
                case["size"],
                source,
                registry,
                original,
                folder,
                content,
                structure,
                status,
            )


def evaluate(draw, prep):
    if draw.status == "content_unknown":
        return None, None

    def recorded_content(phase, messages):
        verify(
            phase == "content" and messages == json.loads(draw.content.prompt),
            "L6 prompt differs",
        )
        return draw.content.wire

    program = prep.engine.execute_case(
        "L6", draw.source, recorded_content, registry_case=draw.registry
    )
    step = program["stages"][0]
    verify(
        step["raw_sha256"] == history.sha(draw.content.wire),
        "Program replay changed the content response",
    )
    if draw.status == "content_rejected":
        verify(
            step["status"] == "stage_rejected" and program["failed_stage"] == "content",
            "Content rejection differs",
        )
        return None, None
    verify(
        step["product"] == draw.content.product, "Program operated on different content"
    )
    program_pass = program["status"] == "accepted"
    if draw.status == "structure_unknown":
        return None, program_pass
    model = history.replay(
        prep, draw.source, draw.registry, draw.content, draw.structure
    )
    if draw.donor == "L5":
        history.anchor(draw.original, model, draw.folder)
    return model["status"] == "accepted", program_pass


def paired(rows):
    states = Counter(r["status"] for r in rows)
    known = [r for r in rows if r["status"] == "ready"]
    cells = Counter((r["model"], r["program"]) for r in known)
    unpaired = [r for r in rows if r["status"] == "structure_unknown"]
    return {
        "assigned_draws": len(rows),
        "statuses": dict(states),
        "compared": len(known),
        "model_accepted": sum(r["model"] for r in known),
        "program_accepted": sum(r["program"] for r in known),
        "both": cells[True, True],
        "model_only": cells[True, False],
        "program_only": cells[False, True],
        "neither": cells[False, False],
        "program_pass_when_model_structure_unknown": sum(
            r["program"] for r in unpaired
        ),
    }


def summarize(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[r["task"]].append(r)
    coverage = Counter()
    histogram = Counter()
    for group in groups.values():
        verify(
            len(group) == len(DONORS) and {r["donor"] for r in group} == set(DONORS),
            "Missing or duplicate donor",
        )
        result = paired(group)
        coverage[result["compared"]] += 1
        if result["compared"] == len(DONORS):
            histogram[result["model_accepted"], result["program_accepted"]] += 1
    return {
        "all": paired(rows),
        "by_archived_donor": {
            d: paired([r for r in rows if r["donor"] == d]) for d in DONORS
        },
        "tasks_by_complete_pairs": dict(sorted(coverage.items())),
        "tasks_with_four_complete_pairs": [
            {"model_passes": m, "program_passes": p, "tasks": n}
            for (m, p), n in sorted(histogram.items())
        ],
    }


def measure(base):
    def offline(event, _):
        if event in {"socket.connect", "socket.getaddrinfo"}:
            raise RuntimeError("Offline analysis")

    sys.addaudithook(offline)
    prep, plan_sha, package, cases = load_batch(base)
    rows = []
    source = hashlib.sha256()
    for draw in iter_draws(base, prep, plan_sha, package, cases):
        a, b = evaluate(draw, prep)
        source.update((draw.folder / "outcome.json").read_bytes())
        rows.append(
            {
                "task": draw.task,
                "donor": draw.donor,
                "status": draw.status,
                "model": a,
                "program": b,
            }
        )
    return {
        "design": "All four model-structure donor arms, original temperature-zero run. One paired replay per archived accepted content and received structure. Same source, content and common frozen downstream within each comparison. Post-hoc, technical acceptance only.",
        "formal_plan_sha256": FORMAL_PLAN,
        "donor_outcomes_sha256_in_order": source.hexdigest(),
        "new_model_calls": 0,
        "new_device_runs": 0,
        **summarize(rows),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("batch", type=Path)
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--output", type=Path)
    target.add_argument("--check", type=Path)
    args = p.parse_args()
    result = measure(args.batch.resolve())
    text = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2)
    if args.check:
        verify(
            json.loads(text) == json.loads(args.check.read_bytes()),
            "Published table differs",
        )
        print("Paired layouts across content draws matched.")
    else:
        args.output.write_text(text + "\n", encoding="utf-8", newline="\n")
