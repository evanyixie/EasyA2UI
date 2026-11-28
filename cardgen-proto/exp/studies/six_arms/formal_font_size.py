"""Measure formal C-05 font declarations and compare them with content and geometry."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from six_arms import (
    composite_inputs,
    font_coverage_stats,
    font_declarations,
    native_font_observability,
    reference_content,
    reference_fact_sources,
    same_bound_font,
)
from six_arms.composite_cost_stats import ARMS, PHASES
from six_arms.fixed_content_repeats import check, digest
from six_arms.formal_numeric_fidelity import MATCHER_SHA, registered_reference
from six_arms.formal_reference_cost import encode, registries
from six_arms.paired_delivery_bounds import verified
from six_arms.web_geometry_inputs import load_inputs

ROOT = Path(__file__).resolve().parents[4]
TABLE = ROOT / "paper/out/tables/formal_font_size.json"


def minima(score):
    if score["status"] != "measured":
        return None, None
    panels = [score["text"], score["button"]]
    observed = [p["min_font"] for p in panels if p["min_font"] is not None]
    minimum = min(observed, default=None)
    complete = all(p["invalid"] == p["missing"] == 0 for p in panels)
    return minimum, minimum if complete else None


def histogram(values):
    counts = Counter(v for v in values if v is not None)
    return {str(k): v for k, v in sorted(counts.items())}


def reference_for_c05(raw):
    """Historical C-05 reads line two. Reference archives also store three messages as a JSON array."""
    if raw is None:
        return raw, False
    try:
        items = json.loads(raw)
    except (ValueError, UnicodeError):
        return raw, False
    if (
        isinstance(items, list)
        and len(items) == 3
        and all(isinstance(x, dict) for x in items)
    ):
        return "\n".join(
            json.dumps(x, ensure_ascii=False, allow_nan=False) for x in items
        ).encode(), True
    return raw, False


def summarize_fonts(scores):
    active = [s for s in scores if s["status"] == "measured"]
    old = [s["legacy"] for s in scores if s["legacy"] is not None]
    by_component = {}
    for kind in ("text", "button"):
        panels = [s[kind] for s in active]
        sizes = Counter()
        for p in panels:
            sizes.update(p["histogram"])
        by_component[kind] = {
            key: sum(p[key] for p in panels)
            for key in (
                "nodes",
                "declared",
                "missing",
                "invalid",
                "below_12fp",
                "below_10fp",
            )
        }
        by_component[kind]["font_histogram"] = dict(sizes)
    full_minima = [minima(s)[1] for s in active]
    return {
        "assigned": len(scores),
        "tree_status": dict(Counter(s["status"] for s in scores)),
        "legacy": {
            "scorable_records": len(old),
            "cards_with_numeric_declarations": sum(
                p["min_font"] is not None for p in old
            ),
            "numeric_nodes": sum(p["numeric_nodes"] for p in old),
            "card_minimum_histogram": histogram(p["min_font"] for p in old),
            **{
                f"below_{limit}fp": {
                    "nodes": sum(p[f"below_{limit}fp"] for p in old),
                    "cards": sum(p[f"below_{limit}fp"] > 0 for p in old),
                }
                for limit in (10, 12)
            },
        },
        "display_nodes": by_component,
        "fully_declared_display_card_minimum_histogram": histogram(full_minima),
        "fully_declared_display_card_count": sum(v is not None for v in full_minima),
    }


def run(root, vault):
    root, vault = root.resolve(), vault.resolve()
    check(
        root.is_relative_to(vault) and not vault.is_relative_to(ROOT),
        "Expected isolated custody inputs",
    )
    historical_metric = ROOT / "cardgen-proto/src/measure.py"
    check(
        digest(historical_metric.read_bytes().replace(b"\r\n", b"\n")) == MATCHER_SHA,
        "Historical C-05 source changed",
    )
    references = reference_fact_sources.load_references(root, vault)
    registered = registries(root)
    check(registered.keys() == references.keys(), "Reference and input roster mismatch")
    facts, reference_fonts, historical = {}, [], set()
    array_references = 0
    for task, reference in references.items():
        raw = (
            reference.a2ui_bytes()
            if isinstance(reference, reference_fact_sources.Reference)
            else None
        )
        facts[task] = registered_reference(raw)
        reference_bytes, converted = reference_for_c05(raw)
        reference_fonts.append(font_declarations.score(reference_bytes))
        array_references += int(converted)
        if raw and not reference.reconstructed_input:
            historical.add(task)

    edge, observations = composite_inputs.edge_evidence(root)
    rows, cache, coverage_receipt, primary_receipt = [], {}, [], []
    for seat in load_inputs(root):
        task, arm, phase = seat.task, seat.arm, seat.checkpoint
        geometry, _ = composite_inputs.geometry_result(
            seat, edge[task, arm, composite_inputs.WEB_PHASE[phase]], observations
        )
        key = (task, seat.artifact_sha256)
        if key not in cache:
            raw = verified(seat.path, seat.artifact_sha256) if seat.path else None
            cache[key] = (
                font_declarations.score(raw),
                reference_content.coverage(raw, facts[task]),
                same_bound_font.match_inputs(raw, registered[task]),
            )
        declaration, (hits, total, status), bound = cache[key]
        coverage_receipt.append((task, arm, phase, status, hits, total))
        primary_receipt.append(
            (task, arm, phase, seat.artifact_sha256, declaration["legacy"])
        )
        known, full = minima(declaration)
        rows.append(
            {
                "task": task,
                "family": seat.family,
                "arm": arm,
                "phase": phase,
                "has_artifact": seat.path is not None,
                "layout_size": seat.size,
                "known_min": known,
                "display_min": full,
                "font": declaration,
                "a4_hits": hits,
                "a4_total": total,
                "a4_status": status,
                "edge_ok": geometry,
                "bound": bound,
            }
        )
    a4_sha = digest(encode(sorted(coverage_receipt)))
    published = json.loads((TABLE.parent / "formal_reference_cost.json").read_bytes())
    check(
        a4_sha == published["coverage_count_receipt_sha256"],
        "Published A4a counts differ",
    )
    return {
        "historical_measure_sha256_lf": MATCHER_SHA,
        "legacy_count_receipt_sha256": digest(encode(sorted(primary_receipt))),
        "reference_control": summarize_fonts(reference_fonts),
        "reference_arrays_transcribed_as_three_lines": array_references,
        "reference_mapping_sha256": reference_fact_sources.summary(references)[
            "mapping_sha256"
        ],
        "coverage_count_receipt_sha256": a4_sha,
        "declarations": {
            p: {
                a: summarize_fonts(
                    [r["font"] for r in rows if r["phase"] == p and r["arm"] == a]
                )
                for a in ARMS
            }
            for p in PHASES
        },
        "content_geometry_and_font": font_coverage_stats.summarize(
            rows, expected_tasks=219
        ),
        "same_bound_value": same_bound_font.paired_report(
            {(r["task"], r["arm"], r["phase"]): r["bound"] for r in rows}
        ),
        "sensitivity_final_excluding_reconstructed": {
            "tasks": len(historical),
            "arms": {
                a: summarize_fonts(
                    [
                        r["font"]
                        for r in rows
                        if r["task"] in historical
                        and r["phase"] == PHASES[1]
                        and r["arm"] == a
                    ]
                )
                for a in ARMS
            },
        },
        "device_evidence": native_font_observability.audit(root),
        "scope": "C-05 counts explicit numeric fontSize on the stored component list. The display-only comparison requires a valid tree and complete positive declarations on Text and Button nodes. A2 uses sealed browser root-box measures. A4a is literal reference-value coverage. Analysis of the same bound value conditions on two artifacts and one unambiguous registered Text binding. These are observational comparisons.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_root", type=Path)
    parser.add_argument("--vault", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Write a new anonymous result; default verifies the published table",
    )
    args = parser.parse_args()
    result = run(args.formal_root, args.vault or args.formal_root.parent)
    if args.output:
        with args.output.open("xb") as out:
            out.write(encode(result))
    elif result != json.loads(TABLE.read_bytes()):
        raise ValueError("Published C-05 result differs")
    print("Verified formal C-05 on", result["reference_control"]["assigned"], "tasks")
