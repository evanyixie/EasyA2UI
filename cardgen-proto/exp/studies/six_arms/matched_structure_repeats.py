"""Replay natural repeats of an L5 structure message under its frozen L5 tail.

CLI: python -B matched_structure_repeats.py PRIVATE_FORMAL_ROOT PUBLIC_TABLE.json
Run in a fresh interpreter with the original queue adapter and pinned dependencies.
Only the formal execution package, receipts and emitted artifacts are used.
"""

import argparse
import importlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

if __package__:
    from .formal_stage_replay import sha, verify
else:
    from formal_stage_replay import sha, verify


DONORS = ("L2", "L3", "L4")


@dataclass(frozen=True)
class Reply:
    prompt: bytes
    wire: bytes
    request_id: str
    product: dict | None


def archived(stage_dir, stage):
    """Return the sealed reply of a stage that passed its contract."""
    verify(stage["status"] == "completed", "original stage did not pass")
    return received_reply(stage_dir, stage)


def received_reply(stage_dir, stage):
    """Bind the physical reply to its records independently of the contract verdict."""
    seal = json.loads((stage_dir / "seal.json").read_bytes())
    prompt = (stage_dir / "messages.json").read_bytes()
    wire = (stage_dir / "response.txt").read_bytes()
    receipt = (stage_dir / "call.json").read_bytes()
    call = json.loads(receipt)
    verify(
        sha(prompt) == seal["messages_sha256"]
        and sha(wire) == seal["raw_sha256"] == stage["raw_sha256"]
        and sha(receipt) == seal["receipt_sha256"]
        and json.loads(prompt) == stage["messages"]
        and call == stage["receipt"]
        and seal["stage"] == stage["stage"] == call["stage"],
        "stage archive disagrees with frozen outcome",
    )
    verify(
        seal["state"] == "completed"
        and stage["status"] in {"completed", "stage_rejected"}
        and call["http_status"] == 200
        and call["physical_attempts"] == 1
        and call["requested_model"] == call["returned_model"] == "deepseek-flash"
        and call["request_id"],
        "missing independent successful formal model call",
    )
    product = stage["product"] if stage["status"] == "completed" else None
    return Reply(prompt, wire, call["request_id"], product)


def missing_prompt(stage_dir, stage):
    seal = json.loads((stage_dir / "seal.json").read_bytes())
    prompt = (stage_dir / "messages.json").read_bytes()
    receipt = (stage_dir / "call.json").read_bytes()
    verify(
        seal["state"] == "failed"
        and sha(prompt) == seal["messages_sha256"]
        and json.loads(prompt) == stage["messages"]
        and sha(receipt) == seal["receipt_sha256"]
        and json.loads(receipt) == stage["receipt"]
        and seal["raw_sha256"] is None
        and not (stage_dir / "response.txt").exists(),
        "unverified missing structure reply",
    )
    return prompt


def missing_response(stage_dir, stage, target):
    prompt = missing_prompt(stage_dir, stage)
    return (
        "same_message_missing_reply"
        if prompt == target.prompt
        else "different_message_missing_reply"
    )


def read_first(result):
    card = result["first_native"]
    if card is not None:
        verify(sha(card["text"].encode()) == card["sha256"], "invalid first artifact")
    direct = result["exit"]["status"] == "no_change"
    verify(not direct or (card and not card["checks"]["errors"]), "invalid direct pass")
    return card["sha256"] if card else None, direct


def replay(prep, source, registry, content, structure):
    replies = {"content": content, "structure": structure}
    used = []

    def recorded(phase, prompt):
        reply = replies[phase]
        verify(prompt == json.loads(reply.prompt), "replay request changed")
        used.append(phase)
        return reply.wire

    result = prep.engine.execute_case("L5", source, recorded, registry_case=registry)
    steps = {s["stage"]: s for s in result["stages"]}
    verify(used == list(replies), "model-owned stages incomplete")
    for name, reply in replies.items():
        verify(
            steps[name]["status"] == "completed"
            and steps[name]["raw_sha256"] == sha(reply.wire)
            and steps[name]["product"] == reply.product,
            "frozen stage failed to reproduce",
        )
    return result


def anchor(original, replayed, folder):
    for key in (
        "source_canonical_sha256",
        "status",
        "failed_stage",
        "stages_completed",
        "first_native",
        "final_native",
        "first_native_after_entry_repair",
    ):
        verify(replayed[key] == original[key], f"L5 anchor changed: {key}")
    verify(read_first(replayed) == read_first(original), "first direct pass differs")
    for moment in ("first_native", "final_native"):
        path = folder / (moment + ".a2ui.jsonl")
        card = original[moment]
        verify(
            (
                not path.exists()
                if card is None
                else path.read_bytes() == card["text"].encode()
            ),
            "L5 anchor differs from on-disk artifact",
        )


@dataclass(frozen=True)
class Observation:
    tree: str
    first: str | None
    direct: bool


def summary(groups):
    """Each group starts with L5. Missing artifacts never count as equal bytes."""
    draws = [s for group in groups for s in group]
    pairs = [p for group in groups for p in combinations(group, 2)]
    anchor_pairs = [(group[0], s) for group in groups for s in group[1:]]

    def paired(rows):
        present = [(a, b) for a, b in rows if a.first and b.first]
        return {
            "pairs": len(rows),
            "same_tree": sum(a.tree == b.tree for a, b in rows),
            "different_tree": sum(a.tree != b.tree for a, b in rows),
            "both_first_present": len(present),
            "both_first_absent": sum(
                a.first is None and b.first is None for a, b in rows
            ),
            "first_presence_disagrees": sum(
                bool(a.first) != bool(b.first) for a, b in rows
            ),
            "same_first_bytes_when_both_present": sum(
                a.first == b.first for a, b in present
            ),
            "different_first_bytes_when_both_present": sum(
                a.first != b.first for a, b in present
            ),
            "both_direct_pass": sum(a.direct and b.direct for a, b in rows),
            "neither_direct_pass": sum(not a.direct and not b.direct for a, b in rows),
            "direct_pass_disagrees": sum(a.direct != b.direct for a, b in rows),
        }

    def pattern(flags):
        if all(flags):
            return "all"
        return "some" if any(flags) else "none"

    by_anchor = paired(anchor_pairs)
    by_anchor["only_anchor_direct_pass"] = sum(
        a.direct and not b.direct for a, b in anchor_pairs
    )
    by_anchor["only_alternative_direct_pass"] = sum(
        b.direct and not a.direct for a, b in anchor_pairs
    )
    return {
        "tasks": len(groups),
        "anchor_first_artifacts": sum(bool(g[0].first) for g in groups),
        "anchor_first_direct_passes": sum(g[0].direct for g in groups),
        "structure_calls": len(draws),
        "first_artifacts": sum(bool(s.first) for s in draws),
        "first_direct_passes": sum(s.direct for s in draws),
        "tasks_with_structure_variation": sum(
            len({s.tree for s in g}) > 1 for g in groups
        ),
        "tasks_with_different_available_first_bytes": sum(
            len({s.first for s in g if s.first is not None}) > 1 for g in groups
        ),
        "first_availability_by_task": dict(
            Counter(pattern([bool(s.first) for s in g]) for g in groups)
        ),
        "direct_pass_by_task": dict(
            Counter(pattern([s.direct for s in g]) for g in groups)
        ),
        "all_within_task_pairs": paired(pairs),
        "l5_anchor_vs_alternative": by_anchor,
    }


def load_batch(base):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(base / "queue"))
    prep = importlib.import_module("prepare_queue")
    plan = prep.read(base / "live/plan.json")
    plan_sha = prep.queue.stable_hash(plan)
    completion = prep.read(
        base / "tech_metrics/continuation_final/completion_receipt.json"
    )
    verify(
        completion["complete"] and completion["plan_sha256"] == plan_sha, "wrong batch"
    )
    named = {
        "input_adapter": Path(prep.__file__),
        "two_case_adapter": prep.TWO,
        "package_manifest": base / "queue/package/manifest.private.json",
    }
    for key, expected in plan["dependencies"].items():
        verify(
            sha(named.get(key, Path(key)).read_bytes()) == expected,
            "frozen dependency differs",
        )
    load = prep.FrozenPackage(base / "queue/package")
    cases = plan["assignment"]["cases"]
    verify(len({c["id"] for c in cases}) == len(cases) == 219, "invalid roster")
    return prep, plan_sha, load, cases


def run(base):
    prep, plan_sha, load, cases = load_batch(base)
    groups, decisions, donor_calls, request_ids = [], Counter(), Counter(), set()

    def outcome(case, arm):
        path = base / "live" / case["file_id"] / arm / "outcome.json"
        return prep.queue.read_outcome(path, case["id"], arm, plan_sha)

    for case in cases:
        folder = base / "live" / case["file_id"]
        original = outcome(case, "L5")
        steps = {s["stage"]: s for s in original["stages"]}
        if "structure" not in steps:
            verify(original["failed_stage"] == "content", "unaccounted L5 absence")
            decisions["l5_stopped_at_content"] += 1
            continue
        content = archived(folder / "L5/calls/content", steps["content"])
        target = archived(folder / "L5/calls/structure", steps["structure"])
        raw, registry = load(case["id"])
        prep.queue.ensure_identity(case, raw, registry)
        source = prep.engine.trial.source_for(json.loads(raw), registry["data_model"])
        alternatives = [target]
        for arm in DONORS:
            donor = outcome(case, arm)
            archived_dir = folder / arm / "calls/structure"
            stage = next(
                (s for s in donor["stages"] if s["stage"] == "structure"), None
            )
            if stage is None:
                decisions["alternative_structure_not_reached"] += 1
                continue
            if stage["status"] == "callback_failed":
                decisions[missing_response(archived_dir, stage, target)] += 1
                continue
            reply = archived(archived_dir, stage)
            if reply.prompt != target.prompt:
                decisions["alternative_different_message"] += 1
                continue
            alternatives.append(reply)
            donor_calls[arm] += 1
        group = []
        for index, reply in enumerate(alternatives):
            verify(
                reply.request_id not in request_ids,
                "duplicate physical structure request",
            )
            request_ids.add(reply.request_id)
            result = replay(prep, source, registry, content, reply)
            if index == 0:
                anchor(original, result, folder / "L5")
            group.append(
                Observation(prep.queue.stable_hash(reply.product), *read_first(result))
            )
        groups.append(group)
    repeated = [g for g in groups if len(g) >= 2]
    return {
        "schema": "matched-structure-repeats-v1",
        "formal_plan_sha256": plan_sha,
        "scope": "Natural repeats matching L5's complete structure message bytes within the same task; reuse successful recorded physical replies with independent request IDs.",
        "outcome": "All replies use L5's frozen content stage (including its registered entry repair) and program tail. Direct technical pass is exit.status=no_change before any exit repair. Visual and business quality were not assessed.",
        "sampling": "Donor arms are L2/L3/L4. Group counts condition on naturally matched messages; pair counts share replies within tasks.",
        "assigned_tasks": len(cases),
        "reproduced_l5_anchors": len(groups),
        "eligible_matched_replies_from_other_arms": dict(donor_calls),
        "missing_or_unmatched": dict(decisions),
        "new_model_calls": 0,
        "new_device_calls": 0,
        "by_replies_per_task": {
            str(n): summary([g for g in groups if len(g) == n]) for n in range(1, 5)
        },
        "tasks_with_repeated_messages": summary(repeated),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("formal_root", type=Path)
    p.add_argument("table", type=Path)
    args = p.parse_args()
    args.table.write_text(
        json.dumps(run(args.formal_root.resolve()), indent=2) + "\n", encoding="utf-8"
    )
