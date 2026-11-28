"""Custody-side A4a/C-04/B4. Outputs anonymous aggregates; no model or device calls."""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from six_arms import composite_cost_stats as stats
from six_arms import (
    composite_inputs,
)
from six_arms import (
    reference_content as content,
)
from six_arms import (
    reference_fact_sources as refs,
)
from six_arms.fixed_content_repeats import FORMAL_PLAN
from six_arms.harness_v2 import trial
from six_arms.paired_delivery_bounds import verified
from six_arms.web_geometry_inputs import load_inputs

ROOT = Path(__file__).resolve().parents[4]
TABLE = ROOT / "paper/out/tables/formal_reference_cost.json"
DIAGNOSTICS = ROOT / "paper/out/tables/formal_reference_cost_diagnostics.json"


def encode(x):
    return (
        json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode()


def registries(root):
    plan = json.loads(verified(root / "live/plan.json", FORMAL_PLAN))
    sources = {}
    for case in plan["assignment"]["cases"]:
        name = case["file_id"] + ".json"
        package = root / "queue/package"
        req = json.loads(verified(package / "requests" / name, case["input_sha256"]))
        reg = json.loads(verified(package / "registry" / name, case["registry_sha256"]))
        source = trial.source_for(req, reg["data_model"])
        sources[case["id"]] = {
            p: trial.lookup(source["sample_data"], p) for p in source["candidate_paths"]
        }
    return sources


def case_evidence(reference, registry):
    if not isinstance(reference, refs.Reference):
        return None, {"status": "missing_reference"}
    raw = reference.a2ui_bytes()
    try:
        facts = content.read_reference(raw)
    except (ValueError, TypeError, KeyError, IndexError, UnicodeError):
        return None, {"status": "unsupported_reference"}
    hits, total, status = content.coverage(raw, facts)
    return facts, {
        "status": "facts_extracted" if facts else "empty_reference",
        **content.registered_value_support(facts, registry),
        "self_hits": hits,
        "self_total": total,
        "self_status": status,
    }


def control(control_rows):
    rows = list(control_rows)
    active = [r for r in rows if r["status"] == "facts_extracted"]
    known = [r for r in active if r["self_status"] == "measured"]
    return {
        "cases": len(rows),
        "reference_states": dict(Counter(r["status"] for r in rows)),
        "positive_reference_fact_counts": {
            str(n): count
            for n, count in sorted(Counter(r["total"] for r in active).items())
        },
        "fact_instances_across_tasks": sum(r["total"] for r in active),
        "same_value_any_candidate": sum(r["same_value_any_candidate"] for r in active),
        "same_value_same_path": sum(r["same_value_same_path"] for r in active),
        "tasks_all_values_at_same_paths": sum(
            r["same_value_same_path"] == r["total"] for r in active
        ),
        "tasks_no_value_at_same_path": sum(
            r["same_value_same_path"] == 0 for r in active
        ),
        "reference_against_own_text": {
            "measured": len(known),
            "unassessed": len(rows) - len(known),
            "passing": {
                str(p): sum(r["self_hits"] * 100 >= p * r["self_total"] for r in known)
                for p in stats.THRESHOLDS
            },
            "states": dict(Counter(r.get("self_status", r["status"]) for r in rows)),
        },
    }


def profile(rows):
    selected = {}
    for arm in stats.ARMS:
        finals = [
            r for r in rows if r["arm"] == arm and r["phase"] == "after_common_repair"
        ]
        if finals:
            selected[arm] = stats.arm_summary(finals, True)["thresholds"]
    return selected


def run(root, vault, *, diagnostics=False):
    if not root.resolve().is_relative_to(
        vault.resolve()
    ) or vault.resolve().is_relative_to(ROOT):
        raise ValueError("Run the evaluator on the isolated custody inputs")
    references = refs.load_references(root, vault)
    registered = registries(root)
    facts, controls = {}, {}
    for task, reference in references.items():
        facts[task], controls[task] = case_evidence(reference, registered[task])
    inputs = load_inputs(root)
    seats = {(s.task, s.arm, s.checkpoint): s for s in inputs}
    rows = composite_inputs.load_rows(root)
    cache = {}
    for row in rows:
        task = row["task"]
        seat = seats[task, row["arm"], row["phase"]]
        row["artifact_sha256"] = seat.artifact_sha256
        key = (task, seat.artifact_sha256)
        if key not in cache:
            raw = verified(seat.path, seat.artifact_sha256) if seat.path else None
            cache[key] = content.coverage(raw, facts[task])
        row["a4a_hits"], row["a4a_total"], row["a4a_status"] = cache[key]
    if diagnostics:
        from six_arms.composite_diagnostics import diagnostic_report
        from six_arms.reference_coverage_stats import a4a_report

        return {
            "assigned_tasks": len(controls),
            "literal_reference_coverage": a4a_report(rows),
            "joint_outcomes": diagnostic_report(rows, root),
        }
    historical = {
        t
        for t, r in references.items()
        if isinstance(r, refs.Reference) and not r.reconstructed_input
    }
    matched = {
        t
        for t, r in controls.items()
        if r["status"] == "facts_extracted" and r["total"] == r["same_value_same_path"]
    }
    alternate = [
        {**r, "protocol": None, "geometry": None, "a4a_hits": None}
        if r.get("absence_reason") == "transport_failed"
        else r
        for r in rows
    ]
    return {
        "evidence": refs.summary(references),
        "reference_control": control(controls.values()),
        "inputs": composite_inputs.diagnostic_counts(rows),
        "coverage_states_by_phase": {
            p: dict(Counter(r["a4a_status"] for r in rows if r["phase"] == p))
            for p in stats.PHASES
        },
        "formal": stats.summarize(rows, expected_tasks=219),
        "sensitivity_final": {
            "excluding_reconstructed_inputs": {
                "tasks": len(historical),
                "arms": profile([r for r in rows if r["task"] in historical]),
            },
            "all_reference_values_in_registered_samples_at_same_paths": {
                "tasks": len(matched),
                "arms": profile([r for r in rows if r["task"] in matched]),
            },
            "transport_failure_treated_as_unobserved": {
                "tasks": 219,
                "arms": profile(alternate),
            },
        },
        "coverage_count_receipt_sha256": hashlib.sha256(
            encode(
                sorted(
                    (
                        r["task"],
                        r["arm"],
                        r["phase"],
                        r["a4a_status"],
                        r["a4a_hits"],
                        r["a4a_total"],
                    )
                    for r in rows
                )
            )
        ).hexdigest(),
        "method": "Historical A4a unique reference-data values, matched against resolved Text content in component order with the original value matcher. Button labels are outside this metric. Composition requires protocol pass, reference value coverage at threshold, and no Text node over four CSS px. Main coverage threshold 80%, sensitivity 60% and 100%. Independent must-show A4b and business delivery are not scored.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_root", type=Path)
    parser.add_argument("--vault", type=Path)
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Verify the secondary literal-coverage and clipping breakdown",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write a new aggregate; default verifies the published table",
    )
    args = parser.parse_args()
    report = run(
        args.formal_root,
        args.vault or args.formal_root.parent,
        diagnostics=args.diagnostics,
    )
    published = DIAGNOSTICS if args.diagnostics else TABLE
    if args.output:
        with args.output.open("xb") as f:
            f.write(encode(report))
    elif report != json.loads(published.read_bytes()):
        raise ValueError("Reference-cost aggregate differs from the frozen evidence")
    print(
        "Verified reference-cost aggregate for",
        report["assigned_tasks"]
        if args.diagnostics
        else report["reference_control"]["cases"],
        "tasks",
    )
