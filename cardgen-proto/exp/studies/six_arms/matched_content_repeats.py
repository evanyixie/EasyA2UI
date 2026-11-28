"""Formal within-task content-stage repeats with a common frozen L6 program tail.

Run in a fresh interpreter: python -B matched_content_repeats.py FORMAL_ROOT TABLE.json
"""

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from statistics import mean

if __package__:
    from .matched_structure_repeats import anchor, load_batch, read_first, sha, verify
else:
    from matched_structure_repeats import anchor, load_batch, read_first, sha, verify


ARMS = ("L2", "L3", "L4", "L5", "L6")
PARAMETERS = {
    "model": "deepseek-flash",
    "temperature": 0,
    "thinking": False,
    "max_tokens_per_response": 8192,
    "initial_http_attempts_per_stage": 1,
}
VALID = {"valid_unchanged", "repaired_and_valid"}


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def bag(rows):
    return tuple(sorted(rows))


def dimensions(plan, source):
    """Summarize only dimensions explicitly encoded in the accepted contract."""
    rows = plan["items"]
    facts = tuple(
        ("path", r["path"]) if "path" in r else ("literal", r["text"]) for r in rows
    )
    candidates = {a["id"]: a for a in source["candidate_actions"]}
    actions = tuple(a["id"] for a in plan["actions"])
    registered = [candidates[a] for a in actions]

    def item_map(keys):
        return bag(
            (fact, *(r.get(k, "") for k in keys))
            for r, fact in zip(rows, facts, strict=True)
        )

    return {
        "facts": bag(facts),
        "actions": bag(actions),
        "candidate_actions": bool(candidates),
        "facts_order": facts,
        "actions_order": actions,
        "roles": item_map(["role"])
        if rows and all(r.get("role") for r in rows)
        else None,
        "entities": item_map(["entity"])
        if rows and all(r.get("entity") for r in rows)
        else None,
        "fact_wording": item_map(["label", "text", "unit"]),
        "title": plan["title"],
        "action_wording": bag((a["id"], a["label"]) for a in plan["actions"]),
        "registered_targets": bag(
            (a["id"], canonical(a["handler"])) for a in registered
        ),
        "registered_owners": bag(a["capabilityId"] for a in registered)
        if all(a.get("capabilityId") for a in registered)
        else None,
        "plan": canonical(plan),
    }


def comparisons(a, b):
    """None marks pairs ineligible for a dimension; absence cannot inflate agreement."""
    same_facts, same_actions = a["facts"] == b["facts"], a["actions"] == b["actions"]
    both_have_facts = same_facts and bool(a["facts"])
    both_have_actions = same_actions and bool(a["actions"])
    any_action = bool(a["actions"] or b["actions"])

    return {
        "selected_fact_multiset": same_facts,
        "selected_fact_multiset_when_either_selected": same_facts
        if a["facts"] or b["facts"]
        else None,
        "selected_action_ids": same_actions,
        "selected_action_ids_when_candidates_available": same_actions
        if a["candidate_actions"]
        else None,
        "selected_action_ids_when_either_selected": same_actions
        if any_action
        else None,
        "selected_facts_and_actions": same_facts and same_actions,
        "registered_action_targets_when_either_selected": a["registered_targets"]
        == b["registered_targets"]
        if any_action
        else None,
        "registered_action_capabilities_when_either_selected": a["registered_owners"]
        == b["registered_owners"]
        if any_action
        and a["registered_owners"] is not None
        and b["registered_owners"] is not None
        else None,
        "literal_item_roles_given_same_facts_and_complete_role_tags": a["roles"]
        == b["roles"]
        if both_have_facts and a["roles"] is not None and b["roles"] is not None
        else None,
        "literal_item_entities_given_same_facts_and_complete_entity_tags": a["entities"]
        == b["entities"]
        if both_have_facts and a["entities"] is not None and b["entities"] is not None
        else None,
        "item_wording_given_same_nonempty_facts": a["fact_wording"] == b["fact_wording"]
        if both_have_facts
        else None,
        "title_wording": a["title"] == b["title"],
        "action_wording_given_same_nonempty_actions": a["action_wording"]
        == b["action_wording"]
        if both_have_actions
        else None,
        "fact_order_given_same_facts_two_or_more_distinct": a["facts_order"]
        == b["facts_order"]
        if same_facts and len(set(a["facts"])) >= 2
        else None,
        "action_order_given_same_actions_two_or_more_distinct": a["actions_order"]
        == b["actions_order"]
        if same_actions and len(set(a["actions"])) >= 2
        else None,
        "entire_effective_contract_with_ids": a["plan"] == b["plan"],
    }


@dataclass
class Draw:
    arm: str
    raw_sha: str
    entry_status: str
    semantic: dict | None
    first: str | None
    direct: bool


def report_agreement(groups):
    totals = defaultdict(Counter)
    task_rates = defaultdict(list)
    for group in groups:
        qualified = [d.semantic for d in group if d.semantic is not None]
        local = defaultdict(list)
        for a, b in combinations(qualified, 2):
            for key, agree in comparisons(a, b).items():
                totals[key]["available_contract_pairs"] += 1
                if agree is not None:
                    local[key].append(agree)
        for key, flags in local.items():
            task_rates[key].append(mean(flags))
            totals[key]["eligible_pairs"] += len(flags)
            totals[key]["equal_pairs"] += sum(flags)
    return {
        key: {
            "eligible_pairs": counts["eligible_pairs"],
            "equal_pairs": counts["equal_pairs"],
            "inapplicable_pairs": counts["available_contract_pairs"]
            - counts["eligible_pairs"],
            "tasks_with_comparable_pairs": len(task_rates[key]),
            "mean_within_task_pair_agreement": mean(task_rates[key])
            if task_rates[key]
            else None,
        }
        for key, counts in totals.items()
    }


def technical(groups):
    result = Counter()
    counts = Counter()
    first_patterns, pass_patterns, flips = Counter(), Counter(), Counter()
    for group in groups:
        result["eligible_tasks"] += bool(group)
        result["tasks_with_two_or_more_draws"] += len(group) >= 2
        counts[len(group)] += 1
        result["draws"] += len(group)
        result["first_artifacts"] += sum(d.first is not None for d in group)
        result["direct_passes"] += sum(d.direct for d in group)
        if len(group) < 2:
            continue
        for flags, patterns in (
            ([d.first is not None for d in group], first_patterns),
            ([d.direct for d in group], pass_patterns),
        ):
            patterns["all" if all(flags) else "some" if any(flags) else "none"] += 1
        for a, b in combinations(group, 2):
            result["pairs"] += 1
            result["pairs_with_equal_raw_bytes"] += a.raw_sha == b.raw_sha
            result["pairs_both_direct_pass"] += a.direct and b.direct
            result["pairs_neither_direct_pass"] += not a.direct and not b.direct
            result["pairs_both_first_present"] += bool(a.first and b.first)
            result["pairs_same_first_bytes_when_both_present"] += bool(
                a.first and a.first == b.first
            )
            if (
                a.semantic is not None
                and b.semantic is not None
                and a.semantic["plan"] == b.semantic["plan"]
            ):
                result["pairs_same_effective_contract_and_identical_first_outcome"] += 1
                verify(
                    (a.first, a.direct) == (b.first, b.direct),
                    "identical effective contract did not replay identically",
                )
            if a.direct != b.direct:
                result["pairs_direct_pass_disagrees"] += 1
                if a.semantic is None or b.semantic is None:
                    flips["one_content_rejected"] += 1
                elif (
                    a.semantic["facts"] != b.semantic["facts"]
                    or a.semantic["actions"] != b.semantic["actions"]
                ):
                    flips["both_valid_different_fact_or_action_set"] += 1
                else:
                    flips["both_valid_same_fact_and_action_sets"] += 1
    return {
        **result,
        "tasks_by_observed_draw_count": dict(sorted(counts.items())),
        "first_availability_in_repeated_tasks": dict(first_patterns),
        "direct_pass_in_repeated_tasks": dict(pass_patterns),
        "discordant_pairs_by_content": dict(flips),
    }


def verified_response(folder, original):
    step = original["stages"][0]
    verify(step["stage"] == "content", "wrong stage")
    d = folder / "calls/content"
    seal = json.loads((d / "seal.json").read_bytes())
    prompt = (d / "messages.json").read_bytes()
    call_bytes = (d / "call.json").read_bytes()
    call = json.loads(call_bytes)
    verify(
        sha(prompt) == seal["messages_sha256"]
        and json.loads(prompt) == step["messages"]
        and sha(call_bytes) == seal["receipt_sha256"]
        and call == step["receipt"]
        and call["stage"] == seal["stage"] == "content",
        "content seal differs",
    )
    if step["status"] == "callback_failed":
        verify(
            seal["state"] == "failed"
            and step["raw_sha256"] is None
            and seal["raw_sha256"] is None
            and not (d / "response.txt").exists(),
            "unverified missing reply",
        )
        return prompt, None, None
    wire = (d / "response.txt").read_bytes()
    verify(
        call["http_status"] == 200
        and call["physical_attempts"] == 1
        and call["request_id"]
        and call["requested_model"] == call["returned_model"] == PARAMETERS["model"]
        and seal["state"] == "completed"
        and sha(wire) == seal["raw_sha256"] == step["raw_sha256"],
        "physical reply disagrees with frozen evidence",
    )
    return prompt, wire, call["request_id"]


def replay(prep, source, registry, prompt, wire, original):
    seen = []

    def recorded(phase, messages):
        verify(
            phase == "content" and messages == json.loads(prompt), "L6 request differs"
        )
        seen.append(phase)
        return wire

    run = prep.engine.execute_case("L6", source, recorded, registry_case=registry)
    verify(seen == ["content"], "unexpected number of model-owned stages")
    c = run["stages"][0]
    prior = original["stages"][0]
    verify(
        run["source_canonical_sha256"] == original["source_canonical_sha256"]
        and run["entry"] == original["entry"]
        and c["status"] == prior["status"]
        and c["raw_sha256"] == prior["raw_sha256"]
        and c.get("product") == prior.get("product"),
        "frozen content contract failed to reproduce",
    )
    return run


def run(base):
    prep, plan_sha, load, cases = load_batch(base)
    plan = prep.read(base / "live/plan.json")
    verify(
        all(plan["parameters"][k] == v for k, v in PARAMETERS.items()),
        "unverified sampling settings",
    )
    grouped = []
    ids = set()
    status = defaultdict(Counter)
    anchors = 0
    for case in cases:
        raw, registry = load(case["id"])
        prep.queue.ensure_identity(case, raw, registry)
        source = prep.engine.trial.source_for(json.loads(raw), registry["data_model"])
        equivalent = set()
        group = []
        for arm in ARMS:
            folder = base / "live" / case["file_id"] / arm
            original = prep.queue.read_outcome(
                folder / "outcome.json", case["id"], arm, plan_sha
            )
            prompt, wire, rid = verified_response(folder, original)
            equivalent.add(prompt)
            if wire is None:
                status[arm]["missing_transport"] += 1
                continue
            verify(rid not in ids, "shared request ID is not an independent draw")
            ids.add(rid)
            result = replay(prep, source, registry, prompt, wire, original)
            entry = result["entry"]["status"]
            product = result["stages"][0].get("product")
            verify(
                entry in VALID | {"rejected_unchanged"}
                and (entry == "valid_unchanged") == result["entry"]["before"]["valid"]
                and (product is not None) == (entry in VALID)
                and (product is not None or result["failed_stage"] == "content"),
                "unsupported entry outcome",
            )
            if arm == "L6":
                anchor(original, result, folder)
                anchors += 1
            group.append(
                Draw(
                    arm,
                    sha(wire),
                    entry,
                    dimensions(product, source) if product is not None else None,
                    *read_first(result),
                )
            )
            status[arm][entry] += 1
        verify(len(equivalent) == 1, "content messages differ within this task")
        grouped.append(group)
    valid = [[d for d in group if d.semantic is not None] for group in grouped]
    metrics = report_agreement(valid)
    report = {
        "schema": "matched-content-repeats-v1",
        "formal_plan_sha256": plan_sha,
        "arms": list(ARMS),
        "sampling": PARAMETERS,
        "assigned_tasks": len(cases),
        "assigned_content_slots": len(cases) * len(ARMS),
        "independent_returned_replies": len(ids),
        "same_message_verified_tasks": len(grouped),
        "l6_anchors_reproduced": anchors,
        "new_model_calls": 0,
        "new_device_calls": 0,
        "observed_entry_status_by_arm": dict(status),
        "observed_entry_totals": dict(sum(status.values(), Counter())),
        "contract_agreement": metrics,
        "comparison_rules": {
            "sampling": "Identical within-task message bytes and common registered transport settings, with distinct provider request IDs for returned replies. These are natural repeats across arms, with no random restarts or server-side seed guarantee.",
            "facts": "Multiset of dynamic binding paths or source-validated literal static text; duplicate occurrences retained. Titles and generated item IDs are separate.",
            "actions": "Registered action IDs, handler payloads and registered capability IDs. Omitted handler uses the original registered target.",
            "priority_entity": "Exact explicit role or entity strings, conditional on equal nonempty fact multisets and complete annotations on both sides. Missing tags are ineligible; lexical disagreement need not be semantic disagreement.",
            "action_entity_owner": "Unobservable. The action row has no link to a displayed entity. Registered capability/handler identity measures business target only.",
            "wording": "Exact title; within identical selected facts compare per-fact label, text and unit; within identical selected actions compare button labels.",
            "order": "Compare order within items or within actions only when both select the same multiset with at least two distinct identities. The contract does not define interleaving of the two arrays.",
            "agreements": "Pairs within tasks share draws. Report equal/eligible pairs and mean within-task rate over tasks with eligible pairs. Agreement is not correctness.",
            "technical": "For each returned raw reply rerun the frozen L6 entry and program tail. Direct pass means exit.status=no_change. Missing transport has no observable reply; rejected content is retained as a failed input to the downstream comparison.",
        },
        "l6_on_all_returned_replies": technical(grouped),
        "l6_on_valid_content_only": technical(valid),
    }
    if any(d.entry_status == "repaired_and_valid" for g in valid for d in g):
        report["agreement_directly_valid_originals_only"] = report_agreement(
            [[d for d in g if d.entry_status == "valid_unchanged"] for g in valid]
        )
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("formal_root", type=Path)
    p.add_argument("table", type=Path)
    args = p.parse_args()
    args.table.write_text(
        json.dumps(run(args.formal_root.resolve()), indent=2) + "\n", encoding="utf-8"
    )
