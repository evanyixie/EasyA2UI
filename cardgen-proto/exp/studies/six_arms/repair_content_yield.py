"""Post-hoc RQ2 joint technical and reference-content yield on the original five strategies."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fixed_layout.paired_analysis import analyze
from six_arms import formal_numeric_fidelity as historical
from six_arms import repair_strategy_comparison as comparison
from six_arms.cost_frontier import TECH_LEDGER, usage
from six_arms.fixed_content_repeats import check, digest
from six_arms.formal_reference_cost import ROOT, encode, registered_sources
from six_arms.paired_delivery_bounds import verified
from six_arms.repair_budget import load_comparisons
from six_arms.technical_yield import DECISION, read_lines
from six_arms.web_geometry_inputs import load_inputs

STRATEGIES = ("L1-NR", "L1", "L1-M", "L5", "L6")
TABLE = ROOT / "paper/out/tables/repair_content_yield.json"
PREVIOUS = "326de4787bd2af3405eb6fbd6491c65eebd6ed067a02ab64ce682fe997cfdadc"
STATES = ("pass", "fail", "missing")


def content_scores(raw, facts, query, registry):
    hits, denom, status = historical.content.coverage(raw, facts)
    numeric = historical.metric.score(raw, facts, query, registry)
    return {
        "coverage": historical.coverage_group(hits, denom, status),
        "coverage_state": status,
        "covered": hits,
        "references": denom,
        "fidelity": historical.fidelity_group(numeric),
        "supported": numeric["supported"],
        "numeric_total": numeric["total"],
    }


def joint(tech, coverage, fidelity):
    check(tech in STATES, "Invalid technical state")
    check(
        coverage in ("at_least_80", "below_80", "unassessed"), "Invalid coverage state"
    )
    check(
        fidelity
        in (
            "all_sourced",
            "some_unsourced",
            "empty_data",
            "unresolved_text",
            "no_artifact",
            "missing_reference",
        ),
        "Invalid numeric state",
    )
    if tech == "fail" or coverage == "below_80" or fidelity == "some_unsourced":
        return "fail"
    if (tech, coverage, fidelity) == ("pass", "at_least_80", "all_sourced"):
        return "pass"
    return "missing"


def arm_summary(records):
    counts = lambda field: dict(sorted(Counter(r[field] for r in records).items()))
    tech_pass = [r for r in records if r["technical"] == "pass"]
    return {
        "tasks": len(records),
        "technical": counts("technical"),
        "coverage": counts("coverage"),
        "coverage_state": counts("coverage_state"),
        "numeric_fidelity": counts("fidelity"),
        "joint": counts("joint"),
        "content_among_technical_passes": {
            group: dict(
                sorted(
                    Counter(
                        r["fidelity"] for r in tech_pass if r["coverage"] == group
                    ).items()
                )
            )
            for group in ("at_least_80", "below_80", "unassessed")
        },
    }


def paired(rows, other):
    roster = [{"task_id": r["task"], "family_id": r["family"]} for r in rows]
    votes = [
        {
            "task_id": r["task"],
            "A": r["L1-M"]["joint"],
            "B": r[other]["joint"],
            "missing_reason": "One or more required observations unavailable.",
        }
        for r in rows
    ]
    mat = Counter((r["A"], r["B"]) for r in votes)
    bounds = analyze(roster, votes)["all_assigned_difference_bounds_B_minus_A"]
    observed = analyze(
        roster,
        [
            {
                **v,
                "A": "pass" if v["A"] == "pass" else "fail",
                "B": "pass" if v["B"] == "pass" else "fail",
            }
            for v in votes
        ],
    )
    return {
        "states_l1m_rows_comparator_columns": {
            a: {b: mat[a, b] for b in STATES} for a in STATES
        },
        "certified_difference_rate_other_minus_l1m": observed[
            "all_assigned_point_difference"
        ],
        "certified_difference_family_percentile_ci95": observed[
            "paired_cluster_percentile_ci95"
        ],
        "latent_difference_rate_bounds_other_minus_l1m": bounds,
    }


def costs(records):
    valid = [r for r in records if r["tokens"] is not None]
    certified = sum(r["joint"] == "pass" for r in valid)
    total = sum(r["tokens"] for r in valid)
    return {
        "assigned": len(records),
        "fully_metered_tasks": len(valid),
        "missing_or_incomplete_meter": len(records) - len(valid),
        "tokens_all_fully_metered_tasks": total,
        "certified_on_those_tasks": certified,
        "tokens_per_certified_on_fully_metered_tasks": total / certified
        if certified
        else None,
    }


def summarize(rows):
    check(
        bool(rows) and len({r["task"] for r in rows}) == len(rows),
        "Invalid paired cohort",
    )
    common = [r for r in rows if all(r[a]["tokens"] is not None for a in STRATEGIES)]
    compared = [r for r in rows if r["L1-NR"]["sha"] and r["L1-M"]["sha"]]

    def content_changed(r):
        keys = (
            "coverage_state",
            "covered",
            "references",
            "fidelity",
            "supported",
            "numeric_total",
        )
        return any(r["L1-NR"][k] != r["L1-M"][k] for k in keys)

    return {
        "assigned_tasks": len(rows),
        "independent_families": len({r["family"] for r in rows}),
        "private_row_sha256": digest(encode(sorted(rows, key=lambda r: r["task"]))),
        "strategies": {a: arm_summary([r[a] for r in rows]) for a in STRATEGIES},
        "pairs": {a: paired(rows, a) for a in STRATEGIES if a != "L1-M"},
        "token_cost": {
            "per_strategy_complete_usage": {
                a: costs([r[a] for r in rows]) for a in STRATEGIES
            },
            "same_tasks_complete_usage_for_all_five": {
                a: costs([r[a] for r in common]) for a in STRATEGIES
            },
        },
        "l1m_initial_to_terminal": {
            "both_artifacts": len(compared),
            "different_wire_bytes": sum(
                r["L1-NR"]["sha"] != r["L1-M"]["sha"] for r in compared
            ),
            "different_coverage_or_numeric_counts_or_status": sum(
                content_changed(r) for r in compared
            ),
        },
        "scope": "Post-hoc joint of archived common technical pass, >=80% A4a reference value coverage "
        "and at least one numeric token with every token supported by a reference or request "
        "under the original A5 matcher. Empty numeric cards have no A5 rating. Any known "
        "failure is decisive. Other unassessed dimensions remain missing. Counts refer to "
        "each strategy's own card on the same request. Bootstrap resamples registered families "
        "10,000 times, seed 20261124, for the difference in obtained passes. The comparator "
        "and L1-M are not equal-budget. Token costs include failed work in the stated cohorts. "
        "No claim about complete business quality, actual invoicing, or the Web geometry B4 endpoint.",
    }


def load_usage(root, repairs):
    """The two pinned receipts contain the originally verified per-call usage."""
    previous = json.loads(
        verified(TABLE.with_name("model_repair_vs_layout_strategies.json"), PREVIOUS)
    )
    totals = previous["resource_costs"]["all_assigned"]
    ledger = read_lines(root / TECH_LEDGER, comparison.PINS[TECH_LEDGER])
    out = {a: {} for a in STRATEGIES}
    audit = {a: Counter() for a in STRATEGIES}

    def record(a, t, subtotal, missing):
        check(t not in out[a], "Duplicate seat meter")
        out[a][t] = None if missing else subtotal
        audit[a].update(total_tokens=subtotal, unknown_usage_calls=missing)

    for seat in ledger:
        arm = seat["arm"]
        if arm not in ("L1", "L5", "L6"):
            continue
        task = seat["task_id"]
        meter, missing = usage(seat["calls"])
        total = meter["total_tokens"]
        record(arm, task, total, missing)
        if arm == "L1":
            record("L1-NR", task, total, missing)
            added = [r["added_tokens"] for r in repairs[task]["model_rounds"]]
            check(
                all(v is None or type(v) is int and v >= 0 for v in added),
                "Invalid follow-up meter",
            )
            record(
                "L1-M",
                task,
                total + sum(v for v in added if v is not None),
                missing + sum(v is None for v in added),
            )
    mapping = {
        "L1-NR": "L1_initial",
        "L1": "L1_initial",
        "L1-M": "L1_M",
        "L5": "L5",
        "L6": "L6",
    }
    for arm, old in mapping.items():
        check(
            out[arm].keys() == repairs.keys()
            and all(v == totals[old][k] for k, v in audit[arm].items())
            and sum(v is not None for v in out[arm].values())
            == totals[old]["tasks_with_complete_usage"],
            "Per-task meter differs from original verified metering",
        )
    return out


def run(root, vault):
    root, vault = root.resolve(), vault.resolve()
    check(
        root.is_relative_to(vault) and not vault.is_relative_to(ROOT),
        "Expected isolated custody inputs",
    )
    check(
        digest(
            (ROOT / "cardgen-proto/src/measure.py").read_bytes().replace(b"\r\n", b"\n")
        )
        == historical.MATCHER_SHA,
        "Historical content matcher changed",
    )
    repairs = {r["id"]: r for r in load_comparisons(root)}
    usage_by_arm = load_usage(root, repairs)
    reference = historical.refs.load_references(root, vault)
    sources = {t: (query, reg) for t, _, query, reg in registered_sources(root)}
    originals = {(s.task, s.arm, s.checkpoint): s for s in load_inputs(root)}
    known = comparison.load_rows(root)
    check(
        set(repairs) == set(reference) == set(sources) == {r["task"] for r in known},
        "Different request rosters",
    )
    rows = []
    for case in known:
        task = case["task"]
        rr = repairs[task]
        row = {"task": task, "family": case["family"]}
        ref = reference[task]
        facts = historical.registered_reference(
            ref.a2ui_bytes() if isinstance(ref, historical.refs.Reference) else None
        )
        q, reg = sources[task]
        cache = {}
        for arm in STRATEGIES:
            src = "L1" if arm in ("L1-NR", "L1-M") else arm
            seat = originals[
                task,
                src,
                "raw_first" if arm in ("L1-NR", "L1-M") else "after_common_repair",
            ]
            check(seat.family == case["family"], "Mismatched task family")
            sha, path = seat.artifact_sha256, seat.path
            tech = DECISION[seat.execution_status]
            if arm == "L1-NR" and sha:
                tech = comparison.verdict(rr["first_common"])
            if arm == "L1-M":
                tech = case[arm]
                if rr["model_eligibility"] != "no_trigger":
                    sha = rr["model_sha256"]
                    path = (
                        root
                        / "rq2_followup_20261127/state"
                        / task
                        / "terminal.a2ui.jsonl"
                        if sha
                        else None
                    )
            if arm in ("L5", "L6"):
                check(tech == case[arm], "Original terminal state differs")
            check(
                bool(sha) == bool(path) and (tech != "pass" or sha),
                "Missing certified artifact",
            )
            if sha not in cache:
                raw = verified(path, sha) if path else None
                cache[sha] = content_scores(raw, facts, q, reg)
            score = cache[sha]
            row[arm] = {
                "sha": sha,
                "technical": tech,
                **score,
                "joint": joint(tech, score["coverage"], score["fidelity"]),
                "tokens": usage_by_arm[arm][task],
            }
        rows.append(row)
    return summarize(rows)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("batch", type=Path)
    cli.add_argument("vault", type=Path)
    cli.add_argument(
        "--output",
        type=Path,
        help="Write a new table; default verifies the published aggregate",
    )
    args = cli.parse_args()
    result = run(args.batch, args.vault)
    if args.output:
        with args.output.open("xb") as f:
            f.write(encode(result))
    else:
        check(
            result == json.loads(TABLE.read_bytes()),
            "RQ2 joint result differs from published table",
        )
    print("Verified", result["assigned_tasks"], "paired requests")
