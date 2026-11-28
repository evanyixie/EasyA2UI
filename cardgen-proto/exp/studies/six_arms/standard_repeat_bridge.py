"""Apply the historical strict reference checks to the 120 sealed L5 structure replies."""

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter

if __package__:
    from . import enhanced_repeat_bridge as bridge
    from .matched_structure_repeats import archived
else:
    import enhanced_repeat_bridge as bridge
    from matched_structure_repeats import archived


TABLE = bridge.PUBLIC.with_name("standard_repeat_bridge.json")
PROGRAM_ROUNDS = "5476c41c3a27ada4094c7635815e31fad29876114adb8e8461c07a4de5750812"


def canonical_sha(value):
    return bridge.digest(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    )


def accepted_sha(observation):
    if observation["verdict"] == "pass":
        artifact = observation["first_artifact_sha256"]
        bridge.require(
            observation["standard_fonts"]
            and observation["unchanged"]
            and observation["source_fidelity"] != "different"
            and observation["stage_exit"] == "accepted"
            and isinstance(artifact, str)
            and re.fullmatch(r"[0-9a-f]{64}", artifact),
            "Incomplete strict pass",
        )
        return artifact
    bridge.require(
        observation["verdict"] in {"fail", "unknown"}, "Unexpected strict verdict"
    )
    return None


def compare(rows):
    grouped = {}
    pairs, reasons, statuses, change = Counter(), Counter(), Counter(), Counter()
    transitions = Counter()
    for r in rows:
        t, rep = r["task"], r["rep"]
        rounds = grouped.setdefault(t, {})
        bridge.require(rep not in rounds, "Duplicate repeat")
        m = r["strict_judgement"]["verdict"]
        p = bool(r["program_standard_sha"])
        rounds[rep] = m, p
        statuses[m] += 1
        pairs[m == "pass", p] += 1
        transitions[r["original_model_accepted"], m == "pass"] += 1
        if m != "pass":
            reasons.update(set(r["strict_judgement"]["reason"].split("|")))
    bridge.require(
        len(grouped) == 12
        and all(set(v) == set(range(1, 11)) for v in grouped.values()),
        "Missing paired repeats",
    )
    hist = Counter()
    for rr in grouped.values():
        model = sum(m == "pass" for m, _ in rr.values())
        program = sum(p for _, p in rr.values())
        change[
            "model_more"
            if model > program
            else "program_more"
            if program > model
            else "equal"
        ] += 1
        hist[model, program] += 1
    return {
        "scope": "Post-hoc supplementary fixed-content assay using only the frozen replies and program runs; no new calls, images or ratings. "
        "Both sides use the benchmark's original standard-font role sizes. The strict reference also enforces frame capacity, source fidelity and an unchanged common exit. "
        "The model side retains each emitted tree and its leaf order. The enhanced program uses its locked candidate enumeration. The 120 pairs are ten repetitions on each of twelve cases.",
        "cases": 12,
        "paired_repetitions": len(rows),
        "historical_model_checks": 12,
        "new_provider_calls": 0,
        "device_runs": 0,
        "original_model_accepted": sum(a for (old, _), a in transitions.items() if old),
        "strict_model_verdicts": dict(sorted(statuses.items())),
        "strict_program_accepted": sum(n for (_, p), n in pairs.items() if p),
        "paired_confirmed_pass": {
            "both": pairs[True, True],
            "model_only": pairs[True, False],
            "program_only": pairs[False, True],
            "neither": pairs[False, False],
        },
        "cases_by_number_of_passes": {
            "model_more": change["model_more"],
            "program_more": change["program_more"],
            "equal": change["equal"],
        },
        "anonymous_grouped_pass_counts": [
            {"model_passes_in_ten": m, "program_passes_in_ten": p, "cases": n}
            for (m, p), n in sorted(hist.items())
        ],
        "model_nonpass_reason_mentions": dict(sorted(reasons.items())),
        "model_compatible_to_strict": {
            "both": transitions[True, True],
            "compatible_only": transitions[True, False],
            "strict_only": transitions[False, True],
            "neither": transitions[False, False],
        },
        "source_sha256": {**bridge.PINS, "followup_program_rounds": PROGRAM_ROUNDS},
    }


def replay(batch, benchmark, private):
    sys.addaudithook(bridge.no_network)
    matched, refs = bridge.sealed_inputs(batch, benchmark)
    strict_archive = matched / "enhanced_program_followup/repetitions.private.json"
    bridge.check_file(strict_archive, PROGRAM_ROUNDS)
    recorded = [
        r for r in bridge.load(strict_archive)["rows"] if r["policy"] == "standard"
    ]
    programs = {(r["task"], r["rep"]): r for r in recorded}
    bridge.require(len(programs) == len(recorded) == 120, "Program repetition identity")
    plan = bridge.indexed(bridge.load(matched / "plan.json")["specification"]["tasks"])
    historical = bridge.indexed(
        bridge.load(batch / "same_content_l56_followup/timing/times.private.json")
    )
    spec = importlib.util.spec_from_file_location(
        "reference_benchmark_standard_tail", benchmark
    )
    bench = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bench)
    data, dev, mods, _ = bench.load()
    bench.warm_fonts()
    rows, checks, ids = [], [], set()
    started = perf_counter()
    for task, ref in sorted(refs.items()):
        item = data[task]
        content, source = item["content"], item["source"]
        bridge.require(
            canonical_sha(content) == ref["content"] == plan[task]["content_sha256"],
            "Unmatched content",
        )
        baseline = item["tree"]
        old_judgement = bench.run.ex.judge_one(content, source, baseline, baseline)
        expected, _ = bench.measure(item, "strict_model_tail", dev, mods)
        bridge.require(
            accepted_sha(old_judgement)
            == expected
            == historical[task]["strict"]["model_sha"],
            "Historical model tail did not match",
        )
        checks.append(
            {
                "task": task,
                "content_sha256": ref["content"],
                "historical_structure_sha256": canonical_sha(baseline),
                "historical_accepted_sha256": expected,
                "judgement": old_judgement,
            }
        )
        for rep in range(1, 11):
            seat = matched / "seats" / task / "L5" / f"rep{rep:02d}"
            row = bridge.load(seat / "outcome.json")
            ex = row["execution"]
            bridge.require(
                row["job"] == {"task": task, "arm": "L5", "rep": rep}
                and row["plan_sha256"] == bridge.PINS["matched_plan"]
                and canonical_sha(ex) == row["execution_sha256"],
                "Unmatched L5 repeat",
            )
            stages = {s["stage"]: s for s in ex["stages"]}
            stage = stages["structure"]
            bridge.require(
                canonical_sha(stages["content"]["product"]) == ref["content"],
                "L5 repeat used different content",
            )
            reply = archived(seat / "calls/structure", stage)
            bridge.require(
                reply.request_id not in ids
                and bridge.digest(reply.prompt)
                == plan[task]["structure_messages_sha256"]
                and stage["receipt"]["actual_payload_sha256"]
                == plan[task]["payload_sha256"],
                "Repeated request or wrong messages",
            )
            ids.add(reply.request_id)
            tree = bench.run.eng.model.parse_output(
                "structure", reply.wire.decode(), source, content=content, tree=None
            )
            bridge.require(
                tree == reply.product,
                "Original reply did not reconstruct the archived structure",
            )
            verdict = bench.run.ex.judge_one(content, source, tree, tree)
            sha = accepted_sha(verdict)
            if sha:
                bridge.require(
                    sha
                    == (ex["first_native"] or {})["sha256"]
                    == (ex["final_native"] or {})["sha256"],
                    "Strict pass changed the original output",
                )
                bridge.check_file(seat / "first_native.a2ui.jsonl", sha)
                bridge.check_file(seat / "final_native.a2ui.jsonl", sha)
            prog = programs[task, rep]
            bridge.require(
                prog["content_sha256"] == ref["content"]
                and prog["result_sha256"] == ref["standard"],
                "Unmatched program comparison",
            )
            rows.append(
                {
                    "task": task,
                    "rep": rep,
                    "content_sha256": ref["content"],
                    "original_outcome_sha256": bridge.digest(
                        (seat / "outcome.json").read_bytes()
                    ),
                    "structure_reply_sha256": bridge.digest(reply.wire),
                    "structure_product_sha256": canonical_sha(tree),
                    "original_model_accepted": ex["status"] == "accepted",
                    "original_model_status": ex["status"],
                    "strict_judgement": verdict,
                    "strict_model_accepted_sha": sha,
                    "program_standard_sha": prog["result_sha256"],
                }
            )
    bridge.require(len(ids) == len(rows) == 120, "Wrong independent reply count")
    if private:
        private.mkdir(parents=True, exist_ok=True)
        out = private / "paired_strict_repeats.private.json"
        bridge.require(not out.exists(), "Existing strict-repeat record")
        bridge.save(
            out,
            {
                "references": checks,
                "rows": rows,
                "source_sha256": {**bridge.PINS, "program": PROGRAM_ROUNDS},
                "replay_wall_seconds": perf_counter() - started,
            },
        )
    return compare(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-batch", type=Path, required=True)
    parser.add_argument("--historical-benchmark", type=Path, required=True)
    parser.add_argument("--private-output", type=Path)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--check", action="store_true")
    target.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = replay(args.formal_batch, args.historical_benchmark, args.private_output)
    if args.check:
        bridge.require(
            report == bridge.load(TABLE), "Standard-font repeat aggregate differs"
        )
        print("Standard-font repeat table matched.")
    else:
        bridge.save(args.output, report)


if __name__ == "__main__":
    main()
