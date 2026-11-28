"""Compare final cards after changing only geometry on the same frozen L4 trees."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from six_arms import formal_arm_content_yield as six
from six_arms import formal_numeric_fidelity as historical
from six_arms import repair_content_yield as rq2
from six_arms.fixed_content_repeats import check, digest
from six_arms.formal_reference_cost import ROOT, encode, registered_sources

TABLE = ROOT / "paper/out/tables/fixed_geometry_content.json"
SIDES = ("model", "program")
POINTS = {"first": "raw_first", "final": "after_common_repair"}


def score_pair(pair, facts, query, values):
    """A repair can change feasibility even if the displayed values stay the same."""
    result = {k: pair[k] for k in ("task", "family", "reached", "in_217")}
    cache = {}
    for point in POINTS:
        sides = {}
        for side in SIDES:
            artifact = pair[side][point]
            tech = pair[side][point + "_technical"]
            check(
                artifact is not None or tech != "pass", "No artifact on technical pass"
            )
            if artifact not in cache:
                cache[artifact] = rq2.content_scores(artifact, facts, query, values)
            metrics = cache[artifact]
            sides[side] = {
                **metrics,
                "artifact_sha256": digest(artifact) if artifact is not None else None,
                "technical": tech,
                "joint": rq2.joint(tech, metrics["coverage"], metrics["fidelity"]),
            }
        if not pair["reached"]:
            check(sides["model"] == sides["program"], "Upstream outcomes diverged")
        result[point] = sides
    return result


def summarize(rows):
    check(len({r["task"] for r in rows}) == len(rows), "Duplicate task")
    groups = {
        "all_assigned": rows,
        "same_content_and_tree": [r for r in rows if r["reached"]],
        "same_tree_original_sources": [r for r in rows if r["reached"] and r["in_217"]],
    }
    result = {}
    for name, cohort in groups.items():
        check(bool(cohort), "Empty analysis group")
        phases = {}
        for point, checkpoint in POINTS.items():
            paired = [
                {"task": r["task"], "family": r["family"], **r[point]} for r in cohort
            ]
            with_both = [
                r for r in paired if all(r[s]["artifact_sha256"] for s in SIDES)
            ]
            fields = (
                "coverage_state",
                "covered",
                "references",
                "fidelity",
                "supported",
                "numeric_total",
            )
            comparison = {
                "arms": {s: rq2.arm_summary([r[s] for r in paired]) for s in SIDES},
                "both_have_artifacts": len(with_both),
                "both_artifacts_equal_reference_counts": sum(
                    all(r["model"][k] == r["program"][k] for k in fields)
                    for r in with_both
                ),
                "both_artifacts_identical_bytes": sum(
                    r["model"]["artifact_sha256"] == r["program"]["artifact_sha256"]
                    for r in with_both
                ),
            }
            if name != "all_assigned":
                comparison["joint_pair"] = six.compare(
                    paired, earlier="model", later="program"
                )
                counted = Counter(
                    (r["model"]["technical"], r["program"]["technical"]) for r in paired
                )
                comparison["technical_pair"] = {
                    m: {p: counted[m, p] for p in rq2.STATES} for m in rq2.STATES
                }
            phases[checkpoint] = comparison
        result[name] = {
            "tasks": len(cohort),
            "families": len({r["family"] for r in cohort}),
            "phases": phases,
        }
    return result


def run(batch, vault):
    from six_arms.fixed_geometry_resources import audit as original_geometry_resources
    from six_arms.formal_fixed_geometry_replay import iter_pairs

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
    sources = {t: (q, values) for t, _, q, values in registered_sources(batch)}
    references = historical.refs.load_references(batch, vault)
    check(sources.keys() == references.keys(), "Reference roster differs from requests")
    rows = []
    for pair in iter_pairs(batch):
        t = pair["task"]
        ref = references[t]
        facts = historical.registered_reference(
            ref.a2ui_bytes() if isinstance(ref, historical.refs.Reference) else None
        )
        rows.append(score_pair(pair, facts, *sources[t]))
    check({r["task"] for r in rows} == sources.keys(), "Incomplete replay")
    cohorts = summarize(rows)
    previous = json.loads(six.TABLE.read_bytes())["cohorts"]["all_assigned"]["phases"]
    for checkpoint in POINTS.values():
        model = cohorts["all_assigned"]["phases"][checkpoint]["arms"]["model"]
        check(
            model == previous[checkpoint]["arms"]["L4"], "Recorded L4 control differs"
        )
    return {
        "cohorts": cohorts,
        "geometry_stage_resources": original_geometry_resources(batch),
        "private_score_rows_sha256": digest(
            encode(sorted(rows, key=lambda r: r["task"]))
        ),
        "interpretation": "Post-hoc content check of a fixed-tree geometry intervention. "
        "Joint pass requires common technical acceptance, at least 80% reference coverage, "
        "and at least one numeric item with all numeric items sourced. "
        "Intervals resample registered task families using the same method as the six-arm content table. "
        "Displayed-value counts do not establish object attribution, visual quality or business delivery.",
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("batch", type=Path)
    cli.add_argument("vault", type=Path)
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    data = run(args.batch, args.vault)
    if args.output:
        with args.output.open("xb") as handle:
            handle.write(encode(data))
    else:
        check(
            data == json.loads(TABLE.read_bytes()), "Different same-tree content result"
        )
    print("Verified first and final cards in the fixed-tree geometry comparison.")
