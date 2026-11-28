"""RQ2/B5 offline replay of fixed-draft repair candidates. Only aggregate counts leave custody."""

import argparse
import json
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from six_arms.fixed_content_repeats import FORMAL_PLAN, canonical, check, digest
from six_arms.native_repeated_facts import PINS
from six_arms.paired_delivery_bounds import verified
from six_arms.portable_layout_engine import load_engine

PLAN = "f07f04cc41ff711fc590cc68e0f67ac821f94b75c9728b5065b8fdd34cab19ae"
PAIRED = "bf341baa5135848d0df1fdf86c69c670307f88608febf98b5b87d65bf0126f72"
EPS = 0.05  # Same tolerance and comparison as native_repair.repair.


def geometry_effect(before, after, *, identical=False):
    """Each measured item is a (node id, rule code) with the recorded excess, not a clinical or visual outcome."""
    if before is None or after is None:
        return {
            "not_numerically_comparable": 1,
            "unchanged_bytes_without_measurement": int(identical),
        }
    old, original_ids = before
    new, _ = after
    introduced = new.keys() - old.keys()
    worsened = [k for k in old.keys() & new.keys() if new[k] > old[k] + EPS]
    new_ids = sum(k[0] not in original_ids for k in introduced)
    return {
        "numerically_comparable": 1,
        "introduced_occurrences": len(introduced),
        "introduced_on_preexisting_ids": len(introduced) - new_ids,
        "introduced_on_new_ids": new_ids,
        "worsened_existing_occurrences": len(worsened),
        "with_introduction": int(bool(introduced)),
        "with_worsening": int(bool(worsened)),
        "with_either": int(bool(introduced or worsened)),
    }


def _observe(native, raw):
    try:
        parsed = native.parse(raw)
        issues, bounds, _ = native.inspect(parsed)
        return issues, set(bounds)
    except (ValueError, KeyError, TypeError, IndexError, RecursionError):
        return None


def _issue_map(items):
    return None if items is None else {(r["id"], r["code"]): r["excess"] for r in items}


def _agree(measured, recorded):
    if recorded is not None:
        check(
            measured is not None and measured[0] == _issue_map(recorded),
            "Replayed geometry differs from archived assessment",
        )


def verify_selection(original, candidates, terminal, common_pass):
    accepted = [raw for _, kept, raw in candidates if kept]
    check(len(accepted) <= 1, "More than one accepted repair")
    if terminal is None:
        check(
            common_pass is None and not accepted,
            "Unknown transport is not a terminal observation",
        )
    else:
        check(
            common_pass is not None
            and (accepted[0] if accepted else original) == terminal,
            "Terminal does not match accepted candidate or restored original",
        )
        if accepted:
            check(
                accepted[0] == candidates[-1][2] and candidates[-1][1],
                "Execution continued after acceptance",
            )


def audit(formal_root, *, engine=None):
    """The caller configures the original registered regular and bold fonts for portable_layout_engine."""
    base = Path(formal_root)
    rq = base / "rq2_followup_20261127"
    plan = json.loads(verified(rq / "plan.json", PLAN))["plan"]
    paired = json.loads(verified(rq / "verification/paired219.private.json", PAIRED))
    original_plan = json.loads(verified(base / "live/plan.json", FORMAL_PLAN))
    e = engine or load_engine()
    check(e.native.EPS == EPS, "Repair tolerance differs")
    for font in (e.program.REGULAR, e.program.BOLD):
        matching = [
            v
            for k, v in original_plan["dependencies"].items()
            if k.replace("\\", "/").split("/")[-1] == font.name
        ]
        check(len(matching) == 1, "Expected the registered reference font")
        verified(font, matching[0])
    obs = verified(
        base / "pre_score_evidence/endpoint/observations.private.jsonl",
        PINS["observations"],
    )
    proofs = {
        j["task_id"]: j["provenance"]
        for line in obs.splitlines()
        if (j := json.loads(line))["arm"] == "L1" and j["checkpoint"] == "raw_first"
    }
    subjects = {r["id"]: r for r in plan["subjects"]}
    check(
        len(subjects) == len(paired) == len({p["id"] for p in paired}) == 219,
        "Incomplete registered RQ2 cohort",
    )
    groups = defaultdict(Counter)
    calls = Counter()
    request_ids = set()
    task_counts = defaultdict(Counter)

    def record(arm, segment, category, effect):
        c = groups[arm, segment, category]
        c["count"] += 1
        c.update(effect)

    @lru_cache(maxsize=16)
    def measure(raw):
        return _observe(e.native, raw)

    for case in paired:
        t = case["id"]
        reg = subjects[t]
        check(reg["eligibility"] == case["model_eligibility"], "Eligibility differs")
        if reg["eligibility"] != "awaiting_first_repair":
            continue
        before_sha = case["initial_sha256"]
        proof = proofs[t]
        outcome_path = base / proof["outcome_ref"]
        run = json.loads(verified(outcome_path, proof["outcome_sha256"]))
        x = run["execution"]
        check(
            run["task"] == t
            and run["arm"] == "L1"
            and run["plan_sha256"] == FORMAL_PLAN
            and digest(canonical(x))
            == run["execution_sha256"]
            == proof["execution_sha256"],
            "Original execution provenance mismatch",
        )
        check(
            before_sha == x["first_native"]["sha256"] == reg["initial_sha256"]
            and case["program_sha256"]
            == x["final_native"]["sha256"]
            == reg["program_final_sha256"],
            "Fixed original or program output mismatch",
        )
        original = verified(
            outcome_path.with_name("first_native.a2ui.jsonl"), before_sha
        )
        initial = measure(original)
        for arm in ("program", "model"):
            observed_rounds = []
            terminal_sha = (
                case["program_sha256"] if arm == "program" else case["model_sha256"]
            )
            accepted = case[f"{arm}_common"]
            if arm == "program":
                exit_log = x["exit"]
                _agree(initial, exit_log.get("before"))
                for rr in exit_log["rounds"]:
                    proposal = rr["candidate"]
                    raw = proposal["text"].encode()
                    check(
                        digest(raw) == proposal["sha256"] and rr["from"] == "original",
                        "Different program candidate",
                    )
                    check(
                        measure(raw) is not None,
                        "Recorded program trial lacks reproducible geometry",
                    )
                    _agree(measure(raw), rr["candidate_violations"])
                    effect = geometry_effect(initial, measure(raw))
                    check(
                        effect["introduced_occurrences"]
                        == len(rr["introduced_by_repair"])
                        and effect["worsened_existing_occurrences"]
                        == len(rr["worsened"]),
                        "Program violation ledger mismatch",
                    )
                    observed_rounds.append((rr["round"], rr["accepted"], raw))
                terminal = verified(
                    outcome_path.with_name("final_native.a2ui.jsonl"), terminal_sha
                )
            else:
                folder = rq / "state" / t
                flag = folder / (
                    "transport_unknown.json" if accepted is None else "outcome.json"
                )
                result = json.loads(flag.read_bytes())
                check(
                    result["id"] == t
                    and result["plan_sha256"] == PLAN
                    and result["initial_sha256"] == before_sha
                    and result["common_pass"] is accepted
                    and result["terminal_sha256"] == terminal_sha,
                    "Model disposition mismatch",
                )
                terminal = (
                    None
                    if accepted is None
                    else verified(folder / "terminal.a2ui.jsonl", terminal_sha)
                )
                for rr in case["model_rounds"]:
                    idx = rr["round"]
                    stage = f"r{idx}"
                    slot = folder / "calls" / stage
                    seal = json.loads((slot / "seal.json").read_bytes())
                    intent = json.loads((slot / "intent.json").read_bytes())
                    check(
                        seal["stage"] == intent["stage"] == stage
                        and seal["messages_sha256"] == intent["messages_sha256"],
                        "Round request lineage mismatch",
                    )
                    verified(slot / "messages.json", seal["messages_sha256"])
                    call = json.loads(
                        verified(slot / "call.json", seal["receipt_sha256"])
                    )
                    check(call["stage"] == stage, "Round receipt misassigned")
                    calls["request_intents"] += 1
                    if rr["common_pass"] is None:
                        check(
                            accepted is None
                            and result["failed_round"] == stage
                            and result["failure_receipt_sha256"]
                            == seal["receipt_sha256"]
                            and call["http_status"] is None
                            and not call["request_id"]
                            and not (slot / "candidate.a2ui.jsonl").exists(),
                            "Invalid missing-response record",
                        )
                        calls["unconfirmed_provider_requests"] += 1
                        continue
                    source = result["rounds"][idx - 1]
                    check(
                        source["round"] == idx
                        and source["receipt_sha256"] == seal["receipt_sha256"]
                        and source["raw_sha256"] == seal["raw_sha256"]
                        and source["candidate_sha256"] == rr["candidate_sha256"],
                        "Reply and registered candidate differ",
                    )
                    verified(slot / "response.txt", seal["raw_sha256"])
                    raw = verified(
                        slot / "candidate.a2ui.jsonl", rr["candidate_sha256"]
                    )
                    assessment = json.loads(
                        verified(slot / "assessment.json", source["assessment_sha256"])
                    )
                    check(
                        assessment["accepted"] is rr["common_pass"]
                        and assessment["before"]["sha256"] == before_sha
                        and assessment["after"]["sha256"] == digest(raw),
                        "Candidate comparison is not against the original",
                    )
                    _agree(initial, assessment["before"]["geometry"]["issues"])
                    _agree(measure(raw), assessment["after"]["geometry"]["issues"])
                    check(
                        call["http_status"] == 200
                        and call["physical_attempts"] == 1
                        and call["request_id"]
                        and call["request_id"] not in request_ids
                        and call["usage"]["total_tokens"] == rr["added_tokens"],
                        "Duplicate or inconsistent provider response",
                    )
                    request_ids.add(call["request_id"])
                    calls["confirmed_responses"] += 1
                    calls["confirmed_tokens"] += rr["added_tokens"]
                    observed_rounds.append((idx, rr["common_pass"], raw))
            verify_selection(original, observed_rounds, terminal, accepted)
            task_counts[arm]["eligible"] += 1
            task_counts[arm][
                "common_unknown"
                if accepted is None
                else "common_pass"
                if accepted
                else "common_fail"
            ] += 1
            any_effect = False
            for idx, kept, raw in observed_rounds:
                effect = geometry_effect(
                    initial, measure(raw), identical=raw == original
                )
                any_effect |= bool(effect.get("with_either"))
                for segment in ("all_candidates", f"round_{idx}"):
                    record(
                        arm,
                        segment,
                        "accepted_candidate" if kept else "rejected_candidate",
                        effect,
                    )
            task_counts[arm][
                "tasks_with_at_least_one_observed_candidate_issue_introduced_or_worsened"
            ] += any_effect
            if terminal is None:
                record(arm, "terminal", "transport_unknown", {})
            else:
                key = "original_retained" if original == terminal else "changed"
                record(
                    arm,
                    "terminal",
                    key,
                    geometry_effect(
                        initial, measure(terminal), identical=original == terminal
                    ),
                )
    check(
        calls["request_intents"] == 335
        and len(request_ids) == 334
        and calls["unconfirmed_provider_requests"] == 1
        and task_counts["program"]["common_pass"] == 91
        and task_counts["model"]["common_pass"] == 101
        and all(v["eligible"] == 212 for v in task_counts.values()),
        "RQ2 registered totals differ",
    )
    report = {}
    for (arm, segment, key), counts in sorted(groups.items()):
        report.setdefault(arm, {}).setdefault(segment, {})[key] = dict(counts)
    return {
        "registered_cohort": len(paired),
        "eligible": 212,
        "method": "Fixed initial draft for every round and terminal; compare the reference geometry (node ID, rule) and a strictly >0.05 increase in recorded excess. A new ID after restructuring can create a newly keyed defect. This is a geometric diagnostic. Program field edits and model whole-card rewrites do not have a common atomic action count.",
        "counts": {a: dict(c) for a, c in task_counts.items()},
        "model_requests": dict(calls),
        "program_incremental_model_calls": 0,
        "effects": report,
        "rq2_plan_sha256": PLAN,
        "paired_ledger_sha256": PAIRED,
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("formal_root", type=Path)
    print(json.dumps(audit(cli.parse_args().formal_root), indent=2))
