"""Offline follow-up on archived content draws from the four model-structure arms.

Supply the frozen formal batch directory and original paired_times.py benchmark.
Both enhanced program policies are rerun for each distinct task, source, content
and entry status. Every observed model structure response is scored separately.
"""

import argparse
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from unittest.mock import patch

if __package__:
    from . import enhanced_repeat_bridge as evidence
    from . import layout_content_draws as primary
    from .standard_repeat_bridge import accepted_sha, canonical_sha
else:
    import enhanced_repeat_bridge as evidence
    import layout_content_draws as primary
    from standard_repeat_bridge import accepted_sha, canonical_sha


TABLE = evidence.PUBLIC.with_name("augmented_content_draws.json")
POLICIES = ("compatible", "standard")
DONORS = ("L2", "L3", "L4", "L5")


def program_layout(bench, dev, mods, task, content, source, entry):
    """Use the original policies; task only breaks candidate ordering ties on small cards."""
    base = bench.run.eng.program.program_route(content)
    small = content["size"] == "2x2"
    evidence.require(small or content["size"] == "2x4", "Unknown canvas")
    standard = compatible = None
    unknown = dict.fromkeys(POLICIES, False)
    if small:
        # family/transfer only label rows returned by loop_one; never entered into search.
        metadata = {"task": task, "family": None, "in_transfer": None}
        judge = bench.run.ex.judge_one

        def observe_candidate(*args):
            decision = judge(*args)
            if decision["verdict"] == "unknown":
                unknown["standard"] = True
            return decision

        # loop_one retains only part of its per-candidate verdict trace. Observe the
        # same unmodified results so an unresolved candidate cannot become a failure.
        with patch.object(bench.run.ex, "judge_one", observe_candidate):
            record, _ = bench.run.loop_one((metadata, content, source), mods)
        standard = record["stages"][-1]
        if record["extra_checks"]:
            unknown["standard"] = True
        evidence.require(
            record["content_sha"] == bench.run.ex.sha(bench.run.ex.packed(content)),
            "Small input identity",
        )
    for name, tree in dev.recorded_menu(base, content):
        if not small and standard is None:
            decision = bench.run.ex.judge_one(content, source, tree, base)
            standard = accepted_sha(decision)
            unknown["standard"] |= decision["verdict"] == "unknown"
        if compatible is None:
            trial = dev.run_tail(tree, content, source, entry)
            accepted = (
                trial["status"] == "accepted"
                if name == "native_L6"
                else trial["strict"]
            )
            if accepted:
                compatible = trial["final_sha"]
            elif trial["status"] in {"geometry_unknown", "execution_error"}:
                unknown["compatible"] = True
        if small:
            evidence.require(
                name == "native_L6",
                "Small compatibility baseline must precede fallback",
            )
            compatible = compatible or standard
            unknown["compatible"] |= unknown["standard"]
            break
        if compatible is not None and standard is not None:
            break
    outputs = {"compatible": compatible, "standard": standard}
    decisions = {
        name: "pass" if sha else "unknown" if unknown[name] else "no_policy_hit"
        for name, sha in outputs.items()
    }
    return outputs, decisions


def model_layout(bench, dev, draw, entry):
    tree, content = draw.structure.product, draw.content.product
    model = dev.run_tail(tree, content, draw.source, entry)
    strict = bench.run.ex.judge_one(content, draw.source, tree, tree)
    compatible_sha = model.get("final_sha") if model["status"] == "accepted" else None
    standard_sha = accepted_sha(strict)
    evidence.require(
        standard_sha is None or standard_sha == compatible_sha,
        "Strict model pass altered the original artifact",
    )
    return {"compatible": compatible_sha, "standard": standard_sha}, {
        "compatible": model["status"],
        "standard": strict["verdict"],
    }


def unresolved(row, who, policy):
    return row[who + "_decisions"][policy] in {
        "unknown",
        "geometry_unknown",
        "execution_error",
    }


def aggregate(rows):
    paired = [r for r in rows if r["status"] == "ready"]
    out = {
        "scheduled": len(rows),
        "content_and_structure_status": dict(
            sorted(Counter(r["status"] for r in rows).items())
        ),
        "ready_content_and_structure": len(paired),
        "distinct_tasks_with_both_inputs": len({r["task"] for r in paired}),
    }
    for policy in POLICIES:
        counts = Counter(
            (bool(r["model"][policy]), bool(r["program"][policy])) for r in paired
        )
        unknown_program_hits = sum(
            bool(r["program"][policy])
            for r in rows
            if r["status"] == "structure_unknown"
        )

        m_unknown = sum(unresolved(r, "model", policy) for r in paired)
        p_unknown = sum(unresolved(r, "program", policy) for r in paired)
        difference = counts[False, True] - counts[True, False]
        missing = [r for r in rows if r["status"] == "structure_unknown"]
        missing_p_unknown = sum(unresolved(r, "program", policy) for r in missing)
        out[policy] = {
            "on_ready_pairs": {
                "both_confirmed": counts[True, True],
                "model_only_confirmed": counts[True, False],
                "program_only_confirmed": counts[False, True],
                "neither_confirmed": counts[False, False],
            },
            "ready_model_decisions": dict(
                sorted(Counter(r["model_decisions"][policy] for r in paired).items())
            ),
            "ready_program_decisions": dict(
                sorted(Counter(r["program_decisions"][policy] for r in paired).items())
            ),
            "ready_model_unknown_program_confirmed": sum(
                unresolved(r, "model", policy) and bool(r["program"][policy])
                for r in paired
            ),
            "ready_program_unknown_model_confirmed": sum(
                unresolved(r, "program", policy) and bool(r["model"][policy])
                for r in paired
            ),
            "ready_program_minus_model_extreme_counts": [
                difference - m_unknown,
                difference + p_unknown,
            ],
            "accepted_content_program_minus_model_extreme_counts": [
                difference - m_unknown + unknown_program_hits - len(missing),
                difference + p_unknown + unknown_program_hits + missing_p_unknown,
            ],
            "accepted_content_draws_for_extreme_counts": len(paired) + len(missing),
            "on_ready_model_confirmed": counts[True, True] + counts[True, False],
            "on_ready_program_confirmed": counts[True, True] + counts[False, True],
            "on_missing_structure_program_confirmed": unknown_program_hits,
        }
        # Both layout policies stop at the same rejected content. An unobserved
        # content draw could give either policy one more pass than its counterpart.
        unknown_content = out["content_and_structure_status"].get("content_unknown", 0)
        lower, upper = out[policy][
            "accepted_content_program_minus_model_extreme_counts"
        ]
        out[policy]["all_scheduled_program_minus_model_extreme_counts"] = [
            lower - unknown_content,
            upper + unknown_content,
        ]
    return out


def four_content_tasks(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["task"]].append(row)
    evidence.require(
        all(len(rs) == len({r["donor"] for r in rs}) == 4 for rs in groups.values()),
        "Incomplete donor grid",
    )
    ready = [rs for rs in groups.values() if all(r["status"] == "ready" for r in rs)]
    result = {"all_tasks": len(groups), "all_four_ready": len(ready)}
    for policy in POLICIES:
        outcomes = Counter()
        model_total = program_total = 0
        for rs in ready:
            if any(
                unresolved(r, side, policy) for r in rs for side in ("model", "program")
            ):
                continue
            m, p = (
                sum(bool(r[side][policy]) for r in rs) for side in ("model", "program")
            )
            model_total += m
            program_total += p
            outcomes[
                "program_more" if p > m else "model_more" if m > p else "equal"
            ] += 1
        n = outcomes.total()
        result[policy] = {
            "all_four_known_tasks": n,
            "excluded_ready_tasks_with_unknown": len(ready) - n,
            "program_more": outcomes["program_more"],
            "model_more": outcomes["model_more"],
            "equal": outcomes["equal"],
            "model_passes": model_total,
            "program_passes": program_total,
            "paired_draws": n * 4,
            "mean_within_task_program_minus_model_pp": round(
                100 * (program_total - model_total) / (4 * n), 4
            )
            if n
            else None,
        }
    return result


def run(batch, benchmark):
    sys.addaudithook(evidence.no_network)
    evidence.check_file(benchmark, evidence.PINS["benchmark"])
    spec = importlib.util.spec_from_file_location(
        "original_187_program_policies", benchmark
    )
    bench = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bench)
    _, dev, mods, _ = bench.load()
    bench.warm_fonts()
    compare_file = batch / "same_content_l56_followup/timing/times.private.json"
    evidence.check_file(compare_file, evidence.PINS["timed187"])
    historical = evidence.indexed(evidence.load(compare_file))
    prep, plan_sha, package, cases = primary.load_batch(batch)
    evidence.require(
        bench.BASE.resolve() == batch.resolve() and prep.engine is bench.run.eng,
        "Mixed frozen batches/engines",
    )
    results, calibrations, request_ids, cache = [], set(), set(), {}
    for draw in primary.iter_draws(batch, prep, plan_sha, package, cases):
        row = {
            "task": draw.task,
            "donor": draw.donor,
            "size": draw.size,
            "status": draw.status,
        }
        results.append(row)
        if draw.status in {"content_unknown", "content_rejected"}:
            continue
        evidence.require(
            draw.status in {"ready", "structure_unknown"} and draw.content is not None,
            "Unknown content status",
        )
        entry = draw.original["entry"]
        content = draw.content.product
        content_hash = canonical_sha(content)
        key = draw.task, canonical_sha(draw.source), content_hash, entry["status"]
        if key not in cache:
            cache[key] = program_layout(
                bench, dev, mods, draw.task, content, draw.source, entry
            )
            evidence.require(
                canonical_sha(content) == content_hash, "Program changed fixed content"
            )
        prog, decisions = cache[key]
        row.update(
            content_sha256=content_hash, program=prog, program_decisions=decisions
        )
        if draw.status == "structure_unknown":
            continue
        evidence.require(
            draw.structure.request_id not in request_ids,
            "Duplicate physical model response",
        )
        request_ids.add(draw.structure.request_id)
        checked_tree = prep.engine.model.parse_output(
            "structure",
            draw.structure.wire.decode(),
            draw.source,
            content=content,
            tree=None,
        )
        evidence.require(
            checked_tree == draw.structure.product,
            "Structure did not parse for this specific content",
        )
        row["model"], row["model_decisions"] = model_layout(bench, dev, draw, entry)
        if draw.donor == "L5":
            old = historical[draw.task]
            evidence.require(
                content_hash == old["content_sha"], "Historical content identity"
            )
            for policy, old_name in (
                ("compatible", "compatible"),
                ("standard", "strict"),
            ):
                for side in ("model", "program"):
                    evidence.require(
                        row[side][policy] == old[old_name][side + "_sha"],
                        "Historical 187 case-level SHA or gap changed",
                    )
            calibrations.add(draw.task)
    evidence.require(
        len(results) == len({(r["task"], r["donor"]) for r in results}) == 219 * 4,
        "Incomplete draw grid",
    )
    evidence.require(
        calibrations == historical.keys() and len(calibrations) == 187,
        "Incomplete 187-case calibration",
    )
    return {
        "study": "Post-hoc counterfactual replays on actual L2-L5 content/structure calls, with a common L5 downstream. "
        "Each policy is applied to exactly the same accepted content and source on both sides. "
        "Standard follows the historical reference size, geometry, fidelity and unchanged exit checks, with the model tree's own order. "
        "Compatible keeps a successful legacy program layout, then applies the locked enhanced fallback. "
        "A confirmed-pass table counts positive evidence; nonconfirmation may include an unknown verdict. "
        "A missing physical model structure is displayed separately and never credited as a program victory. "
        "Multiple draws share tasks, sometimes exact content. These are paired technical projections, without visual or business assessments.",
        "frozen_formal_plan_sha256": plan_sha,
        "frozen_benchmark_sha256": evidence.PINS["benchmark"],
        "case_level_anchor_sha256": evidence.PINS["timed187"],
        "case_level_anchor_cases": len(calibrations),
        "case_level_anchor_comparisons": len(calibrations) * 4,
        "different_program_inputs_scored": len(cache),
        "unique_original_model_structure_responses": len(request_ids),
        "new_network_requests": 0,
        "device_runs": 0,
        "all": aggregate(results),
        "complete_four_draw_tasks": four_content_tasks(results),
        "by_content_donor": {
            arm: aggregate([r for r in results if r["donor"] == arm]) for arm in DONORS
        },
        "by_canvas": {
            size: aggregate([r for r in results if r["size"] == size])
            for size in ("2x2", "2x4")
        },
    }, results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument(
        "--private-output",
        type=Path,
        help="Optional custodian-only per-draw evidence file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write anonymous aggregates; default checks the published table",
    )
    args = parser.parse_args()
    report, records = run(args.formal_root, args.benchmark)
    if args.private_output:
        args.private_output.parent.mkdir(parents=True, exist_ok=True)
        if args.private_output.exists():
            evidence.require(
                evidence.load(args.private_output) == records,
                "Existing private output differs",
            )
        else:
            evidence.save(args.private_output, records)
    if args.output:
        evidence.save(args.output, report)
    else:
        evidence.require(evidence.load(TABLE) == report, "Published table differs")
    print(json.dumps(report["all"], sort_keys=True))
