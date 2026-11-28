"""Recompute the registered A5 literal numeric-source metric on sealed first and final cards."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from six_arms import numeric_fidelity as metric
from six_arms import numeric_fidelity_stats as stats
from six_arms import reference_content as content
from six_arms import reference_fact_sources as refs
from six_arms.composite_cost_stats import ARMS, PHASES
from six_arms.fixed_content_repeats import check, digest
from six_arms.formal_reference_cost import encode, registered_sources
from six_arms.paired_delivery_bounds import verified
from six_arms.web_geometry_inputs import load_inputs

ROOT = Path(__file__).resolve().parents[4]
TABLE = ROOT / "paper/out/tables/formal_numeric_fidelity.json"
MATCHER_SHA = "3bf0f319dc9fa266906d649aa4233398fa9da0c8cdefd0c4d08233776dca4376"


def coverage_group(hits, total, status):
    if status != "measured" or not total:
        return "unassessed"
    return "at_least_80" if hits * 100 >= total * 80 else "below_80"


def fidelity_group(metrics):
    if metrics["status"] != "measured":
        return metrics["status"]
    return (
        "all_sourced" if metrics["supported"] == metrics["total"] else "some_unsourced"
    )


def joint_counts(counts):
    """Keep an empty coverage stratum distinguishable from an unassessed card."""
    result = {label: {} for label in ("at_least_80", "below_80", "unassessed")}
    for (coverage, fidelity), n in sorted(counts.items()):
        result[coverage][fidelity] = n
    return result


def registered_reference(raw):
    if raw is None:
        return None
    try:
        return content.read_reference(raw)
    except (ValueError, TypeError, KeyError, IndexError, UnicodeError):
        return None


def run(root, vault):
    root, vault = root.resolve(), vault.resolve()
    check(
        root.is_relative_to(vault) and not vault.is_relative_to(ROOT),
        "Expected isolated custody inputs",
    )
    source_file = ROOT / "cardgen-proto/src/measure.py"
    check(
        digest(source_file.read_bytes().replace(b"\r\n", b"\n")) == MATCHER_SHA,
        "Historical A5 matcher changed",
    )
    sources = {
        task: (query, request.get("originalQuery"), registered)
        for task, request, query, registered in registered_sources(root)
    }
    references = refs.load_references(root, vault)
    check(sources.keys() == references.keys(), "Reference and input roster mismatch")
    facts, self_scores, historical = {}, [], set()
    for task, reference in references.items():
        raw = reference.a2ui_bytes() if isinstance(reference, refs.Reference) else None
        facts[task] = registered_reference(raw)
        query, _, registered = sources[task]
        check(
            isinstance(query, str) and bool(query.strip()), "Missing frozen model query"
        )
        self_scores.append(metric.score(raw, facts[task], query, registered))
        if isinstance(reference, refs.Reference) and not reference.reconstructed_input:
            historical.add(task)

    ledger, cache, paired_coverage = [], {}, []
    query_check = Counter()
    joint = {(a, p): Counter() for a in ARMS for p in PHASES}
    for seat in load_inputs(root):
        task, arm, phase = seat.task, seat.arm, seat.checkpoint
        query, original, registered = sources[task]
        key = task, seat.artifact_sha256
        if key not in cache:
            raw = verified(seat.path, seat.artifact_sha256) if seat.path else None
            score = metric.score(raw, facts[task], query, registered)
            alternative = (
                metric.score(raw, facts[task], original, registered)
                if original and original != query
                else score
            )
            cache[key] = score, content.coverage(raw, facts[task]), alternative
        score, coverage, alternative = cache[key]
        hits, total, status = coverage
        paired_coverage.append((task, arm, phase, status, hits, total))
        joint[arm, phase][coverage_group(*coverage), fidelity_group(score)] += 1
        if original and original != query:
            query_check["checkpoint_seats"] += 1
            query_check["changed_legacy_support_count"] += (
                alternative["supported"] != score["supported"]
            )
            query_check["changed_strict_support_count"] += (
                alternative["strict_supported"] != score["strict_supported"]
            )
        ledger.append(
            {
                "task": task,
                "family": seat.family,
                "arm": arm,
                "phase": phase,
                "metrics": score,
            }
        )

    a4_sha = digest(encode(sorted(paired_coverage)))
    published_a4 = json.loads(
        (TABLE.parent / "formal_reference_cost.json").read_bytes()
    )
    check(
        a4_sha == published_a4["coverage_count_receipt_sha256"],
        "Published A4a inputs or counts differ",
    )
    return {
        "reference_evidence": refs.summary(references),
        "historical_matcher_sha256_lf": MATCHER_SHA,
        "coverage_count_receipt_sha256": a4_sha,
        "numeric_count_receipt_sha256": digest(
            encode(
                sorted((r["task"], r["arm"], r["phase"], r["metrics"]) for r in ledger)
            )
        ),
        "reference_self_check": stats.arm_summary(self_scores),
        "formal": stats.summary(ledger, expected_tasks=219),
        "joint_a4a_a5": {
            p: {a: joint_counts(joint[a, p]) for a in ARMS} for p in PHASES
        },
        "sensitivity_excluding_reconstructed_final": {
            "tasks": len(historical),
            "arms": {
                a: stats.arm_summary(
                    [
                        r["metrics"]
                        for r in ledger
                        if r["task"] in historical
                        and r["arm"] == a
                        and r["phase"] == PHASES[1]
                    ]
                )
                for a in ARMS
            },
        },
        "query_source_check": {
            "tasks_with_nonempty_model_query": len(sources),
            "tasks_with_original_query_field": sum(
                bool(original) for _, original, _ in sources.values()
            ),
            "tasks_with_different_original_query": sum(
                bool(original) and original != q for q, original, _ in sources.values()
            ),
            "different_query_checkpoint_comparison": dict(query_check),
        },
        "interpretation": "Each card contributes distinct numeric fragments in first-frame Text content. Historical source support uses bidirectional text matching. A secondary diagnostic requires normalized equality of whole fragments, with conservative spelling and unit-boundary checks. Additional strict matches in registered input samples are reported among historically unsupported fragments. These checks cannot establish correct entity, denominator, units or runtime data. A4a uses the same originals. Cards with no numeric fragment and missing outputs are counted separately.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_root", type=Path)
    parser.add_argument("--vault", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Write a new anonymous aggregate; default verifies the published table",
    )
    args = parser.parse_args()
    report = run(args.formal_root, args.vault or args.formal_root.parent)
    if args.output:
        with args.output.open("xb") as f:
            f.write(encode(report))
    elif report != json.loads(TABLE.read_bytes()):
        raise ValueError("Published A5 result differs")
    print("Verified A5 on", report["formal"]["assigned_tasks"], "tasks")
