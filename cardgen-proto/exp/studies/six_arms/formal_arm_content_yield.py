"""Six frozen arms on the same registered tasks, using the post-hoc RQ2 joint endpoint."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fixed_layout.paired_analysis import analyze
from six_arms import formal_numeric_fidelity as historical
from six_arms import repair_content_yield as rq2
from six_arms.composite_cost_stats import ARMS, PHASES
from six_arms.fixed_content_repeats import check, digest
from six_arms.formal_reference_cost import ROOT, encode, registered_sources
from six_arms.formal_repair_receipts import load_repair_rows
from six_arms.paired_delivery_bounds import ROSTER, verified
from six_arms.technical_yield import DECISION, read_lines
from six_arms.web_geometry_inputs import load_inputs

TABLE = ROOT / "paper/out/tables/formal_arm_content_yield.json"


def technical(row):
    """Read the actual first source/geometry check and the committed terminal disposition."""
    exit_status = row["exit_status"]
    terminal = DECISION[row["execution_status"]]
    if exit_status == "not_reached":
        check(
            row["execution_status"] in {"stage_rejected", "callback_failed"},
            "Unexpected no-artifact status",
        )
        check(
            row["first_sha256"] is None and row["final_sha256"] is None,
            "Artifact at unreached exit",
        )
        return dict.fromkeys(PHASES, terminal)
    check(
        bool(row["first_sha256"]) and bool(row["final_sha256"]),
        "Missing common-exit artifact",
    )
    if exit_status == "skipped_source_check":
        first = "fail"
    elif exit_status == "unsupported":
        first = "missing"
    else:
        check(
            exit_status in {"no_change", "repaired", "unresolved"}
            and isinstance(row["before"], list),
            "Invalid initial geometry",
        )
        first = "fail" if row["before"] else "pass"
    return {"raw_first": first, "after_common_repair": terminal}


def compare(rows, *, earlier="L4", later="L5"):
    """Separate finite-cohort unknown-state bounds from sampling uncertainty of obtained passes."""
    roster = [{"task_id": r["task"], "family_id": r["family"]} for r in rows]
    votes = [
        {
            "task_id": r["task"],
            "A": r[earlier]["joint"],
            "B": r[later]["joint"],
            "missing_reason": "One or more required components are unobserved.",
        }
        for r in rows
    ]
    matrix = Counter((v["A"], v["B"]) for v in votes)
    obtained = [
        {
            **v,
            "A": "pass" if v["A"] == "pass" else "fail",
            "B": "pass" if v["B"] == "pass" else "fail",
        }
        for v in votes
    ]
    latent = analyze(roster, votes)
    certified = analyze(roster, obtained)
    return {
        "rows": earlier,
        "columns": later,
        "difference": f"{later}_minus_{earlier}",
        "states": {a: {b: matrix[a, b] for b in rq2.STATES} for a in rq2.STATES},
        "pairs_with_both_states_known": latent["complete_pairs"],
        "certified_difference_rate": certified["all_assigned_point_difference"],
        "certified_difference_family_percentile_ci95": certified[
            "paired_cluster_percentile_ci95"
        ],
        "latent_difference_rate_bounds": latent[
            "all_assigned_difference_bounds_B_minus_A"
        ],
    }


def summarize(rows, roster):
    """Require every assigned task/arm/checkpoint; exclude only the two registered reconstructed inputs."""
    grid = {}
    for row in rows:
        task, arm, phase = row["task"], row["arm"], row["phase"]
        key = (task, arm, phase)
        check(
            task in roster and arm in ARMS and phase in PHASES and key not in grid,
            "Duplicate or unexpected seat",
        )
        check(row["family"] == roster[task]["family"], "Wrong family")
        grid[key] = row
    check(
        len(grid) == len(roster) * len(ARMS) * len(PHASES), "Incomplete checkpoint grid"
    )
    check(
        all(type(r["included_in_217_sensitivity"]) is bool for r in roster.values()),
        "Missing cohort flag",
    )
    result = {}
    for group, tasks in (
        ("all_assigned", list(roster)),
        (
            "original_sources",
            [t for t, r in roster.items() if r["included_in_217_sensitivity"]],
        ),
    ):
        check(bool(tasks), "Empty cohort")
        phases = {}
        for phase in PHASES:
            paired = [
                {
                    "task": t,
                    "family": roster[t]["family"],
                    **{a: grid[t, a, phase] for a in ARMS},
                }
                for t in tasks
            ]
            phases[phase] = {
                "arms": {a: rq2.arm_summary([r[a] for r in paired]) for a in ARMS},
                "paired_l5_minus_l4": compare(paired),
            }
        result[group] = {
            "tasks": len(tasks),
            "families": len({roster[t]["family"] for t in tasks}),
            "phases": phases,
        }
    return result


def run(batch, vault):
    batch, vault = Path(batch).resolve(), Path(vault).resolve()
    check(
        batch.is_relative_to(vault) and not vault.is_relative_to(ROOT),
        "Expected isolated custody inputs",
    )
    matcher = ROOT / "cardgen-proto/src/measure.py"
    check(
        digest(matcher.read_bytes().replace(b"\r\n", b"\n")) == historical.MATCHER_SHA,
        "Historical metric changed",
    )
    roster = {
        r["task_id"]: r for r in read_lines(batch / "analysis/roster.jsonl", ROSTER)
    }
    check(
        len(roster) == 219
        and sum(r["included_in_217_sensitivity"] for r in roster.values()) == 217,
        "Unexpected roster",
    )
    receipts = {(r["task"], r["arm"]): r for r in load_repair_rows(batch)}
    refs = historical.refs.load_references(batch, vault)
    sources = {
        t: (query, registry) for t, _, query, registry in registered_sources(batch)
    }
    check(roster.keys() == refs.keys() == sources.keys(), "Different source rosters")
    facts = {
        t: historical.registered_reference(
            ref.a2ui_bytes() if isinstance(ref, historical.refs.Reference) else None
        )
        for t, ref in refs.items()
    }
    rows, scores = [], {}
    for s in load_inputs(batch):
        receipt = receipts[s.task, s.arm]
        sha_field = "first_sha256" if s.checkpoint == "raw_first" else "final_sha256"
        check(
            receipt[sha_field] == s.artifact_sha256 and receipt["family"] == s.family,
            "Mismatched checkpoint artifact",
        )
        tech = technical(receipt)[s.checkpoint]
        key = (s.task, s.artifact_sha256)
        if key not in scores:
            raw = verified(s.path, s.artifact_sha256) if s.path else None
            scores[key] = rq2.content_scores(raw, facts[s.task], *sources[s.task])
        score = scores[key]
        check(
            tech != "pass" or s.path is not None,
            "Technical pass without original artifact",
        )
        rows.append(
            {
                "task": s.task,
                "family": s.family,
                "arm": s.arm,
                "phase": s.checkpoint,
                "technical": tech,
                "joint": rq2.joint(tech, score["coverage"], score["fidelity"]),
                **score,
            }
        )
    result = summarize(rows, roster)
    previous = json.loads(rq2.TABLE.read_bytes())
    # Compare the full set of stage and content marginals, not only the positive totals.
    for phase, arm, old_arm in (
        ("raw_first", "L1", "L1-NR"),
        ("after_common_repair", "L1", "L1"),
        ("after_common_repair", "L5", "L5"),
        ("after_common_repair", "L6", "L6"),
    ):
        for cohort, expected in (
            ("all_assigned", previous["strategies"][old_arm]),
            (
                "original_sources",
                {
                    "joint": previous["registered_original_input_subset"][
                        "joint_states"
                    ][old_arm]
                },
            ),
        ):
            current = result[cohort]["phases"][phase]["arms"][arm]
            check(
                all(current[k] == v for k, v in expected.items()),
                "RQ2 common-arm control mismatch",
            )
    return {
        "cohorts": result,
        "private_score_rows_sha256": digest(
            encode(sorted(rows, key=lambda r: (r["task"], r["arm"], r["phase"])))
        ),
        "score": "Post-hoc common technical pass, A4a coverage >=80%, and nonempty A5 with every numeric token sourced. "
        "Any known failure is decisive; other incomplete combinations are unknown. This is not the preregistered complete-delivery endpoint.",
        "inference": "L5 minus L4, paired by task. Percentile interval resamples registered families 10,000 times, seed 20261124, "
        "for the difference in obtained passes. Latent bounds allow every unknown component outcome. "
        "The six-arm composite was added after earlier five-strategy marginals were known.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("vault", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Create a new anonymous aggregate; default checks the published table",
    )
    args = parser.parse_args()
    result = run(args.batch, args.vault)
    if args.output:
        with args.output.open("xb") as out:
            out.write(encode(result))
    else:
        check(
            result == json.loads(TABLE.read_bytes()),
            "Different six-arm joint aggregate",
        )
    print("Verified joint endpoint for all six arms and both checkpoints.")
