"""Fixed-tree 2x2 factorial replay of 12 cases with ten frozen L5 structure draws each.

The first letter denotes role fonts, the second gap and root padding (S=standard,
C=compact). A positive cell means the full tree fits reference geometry. Native
and end-to-end acceptance are separate historical anchors.
"""

import argparse
import itertools
import os
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path, PureWindowsPath
from types import FunctionType

from PIL import __version__ as pillow_version
from PIL import features

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from six_arms import enhanced_repeat_bridge as bridge
from six_arms import fixed_content_repeats as receipts
from six_arms.formal_reference_cost import encode
from six_arms.matched_structure_repeats import archived
from six_arms.portable_enhanced_layout import frame_issue
from six_arms.portable_layout_engine import load_engine
from six_arms.standard_repeat_bridge import canonical_sha

CELLS = ("SS", "CS", "SC", "CC")
PRIOR = "50b317c69376142d09ff4426749931ac5644365dce22a1d6669e3a8d7284c228"
SOURCE_FNS = {
    "SIX_ARMS_FONT_REGULAR": "HarmonyOS_Sans_SC_Regular.ttf",
    "SIX_ARMS_FONT_BOLD": "HarmonyOS_Sans_SC_Bold.ttf",
    "SIX_ARMS_MEASURE_PY": "measure.py",
}


def one_recipe(program, cell):
    """Run the original solver bytecode with a private font hook; leave the module intact.

    The solver visits standard spacing first, then compact only on capacity failure.
    Refuse the other spacing at its first leaf. For the selected spacing, call
    the original role-font helper with the independently assigned font setting.
    """
    if cell not in CELLS:
        raise ValueError("Unknown recipe")
    compact_fonts, compact_spacing = (x == "C" for x in cell)
    original = program.program_geometry

    def font_style(node, entries, spacing):
        if spacing != compact_spacing:
            raise program.StageError("reference_capacity", "Nonassigned spacing")
        return program._font_style(node, entries, compact_fonts)

    isolated = FunctionType(
        original.__code__,
        {**original.__globals__, "_font_style": font_style},
        original.__name__,
        original.__defaults__,
        original.__closure__,
    )

    def fit(tree, content):
        try:
            geometry = isolated(tree, content)
        except program.StageError as exc:
            if exc.code == "reference_capacity":
                return None
            raise
        bridge.require(
            geometry["root"]["style"]["padding"] == (8 if compact_spacing else 10),
            "Assigned spacing was bypassed",
        )
        return geometry

    return fit


def aggregate(rows):
    """Anonymous task-level response patterns, both conditional effects and interaction."""
    grouped = defaultdict(list)
    patterns = Counter()
    contrasts = {
        "compact_font_at_standard_spacing": ("CS", "SS"),
        "compact_font_at_compact_spacing": ("CC", "SC"),
        "compact_spacing_at_standard_font": ("SC", "SS"),
        "compact_spacing_at_compact_font": ("CC", "CS"),
    }
    for r in rows:
        grouped[r["task"]].append(r)
        patterns["".join(str(int(r["fits"][cell])) for cell in CELLS)] += 1
    if not rows:
        raise ValueError("No independent structure draws")

    def mean(numbers):
        return float(sum(numbers, Fraction(0)) / len(numbers))

    rates = {
        t: {c: Fraction(sum(r["fits"][c] for r in rr), len(rr)) for c in CELLS}
        for t, rr in grouped.items()
    }
    result = {}
    for name, (b, a) in contrasts.items():
        diffs = [int(r["fits"][b]) - int(r["fits"][a]) for r in rows]
        by_task = [p[b] - p[a] for p in rates.values()]
        result[name] = {
            "gained_draws": diffs.count(1),
            "lost_draws": diffs.count(-1),
            "tied_draws": diffs.count(0),
            "equal_task_weight_difference": mean(by_task),
            "higher_tasks": sum(d > 0 for d in by_task),
            "lower_tasks": sum(d < 0 for d in by_task),
            "tied_tasks": sum(d == 0 for d in by_task),
        }
    return {
        "tasks": len(grouped),
        "draws": len(rows),
        "bit_order": list(CELLS),
        "draw_fit_pattern_counts": dict(sorted(patterns.items())),
        "cells": {
            c: {
                "fit": sum(r["fits"][c] for r in rows),
                "equal_task_weight_rate": mean([p[c] for p in rates.values()]),
            }
            for c in CELLS
        },
        "conditional_differences": result,
        "interaction_equal_task_weight": mean(
            [p["CC"] - p["SC"] - p["CS"] + p["SS"] for p in rates.values()]
        ),
        "cases_by_fit_count_in_cell_order": [
            {"counts": list(counts), "tasks": n}
            for counts, n in sorted(
                Counter(
                    tuple(sum(r["fits"][c] for r in rr) for c in CELLS)
                    for rr in grouped.values()
                ).items()
            )
        ],
    }


def locked_engine(dependencies):
    hashes = {}
    for var, filename in SOURCE_FNS.items():
        (source,) = [
            (p, h)
            for p, h in dependencies.items()
            if PureWindowsPath(p).name == filename
        ]
        recorded, expected = source
        location = Path(os.environ.get(var) or recorded).resolve()
        bridge.check_file(location, expected)
        os.environ[var] = str(location)
        hashes[filename] = expected
    return load_engine(), hashes


def run(batch):
    sys.addaudithook(bridge.no_network)
    study = batch / "fixed_content_repeat12_20261128"
    bridge.check_file(study / "plan.json", receipts.REPEAT_PLAN)
    bridge.check_file(batch / "live/plan.json", receipts.FORMAL_PLAN)
    bridge.check_file(study / "complete.json", bridge.PINS["matched_complete"])
    bridge.check_file(study / "selection.private.json", receipts.SELECTION)
    prior_file = study / "enhanced_program_followup/paired_strict_repeats.private.json"
    bridge.check_file(prior_file, PRIOR)
    prior = bridge.load(prior_file)["rows"]
    spec = bridge.load(study / "plan.json")["specification"]
    tasks = bridge.indexed(spec["tasks"])
    expected = set(itertools.product(tasks, range(1, 11)))
    bridge.require(
        len(tasks) == 12
        and len(prior) == 120
        and {(r["task"], r["rep"]) for r in prior} == expected,
        "Missing or duplicate registered repeat",
    )
    formal = {
        r["id"]: r for r in bridge.load(batch / "live/plan.json")["assignment"]["cases"]
    }
    engine, hashes = locked_engine(spec["frozen_dependencies"])
    fits = {cell: one_recipe(engine.program, cell) for cell in CELLS}
    original_input = {}
    for t in tasks:
        case = formal[t]
        folder = batch / "queue/package"
        name = case["file_id"] + ".json"
        req, reg = folder / "requests" / name, folder / "registry" / name
        bridge.check_file(req, case["input_sha256"])
        bridge.check_file(reg, case["registry_sha256"])
        original_input[t] = engine.trial.source_for(
            bridge.load(req), bridge.load(reg)["data_model"]
        )
    rows, ids = [], set()
    calibration = Counter()
    for old in prior:
        t, rep = old["task"], old["rep"]
        path = study / "seats" / t / "L5" / f"rep{rep:02d}"
        bridge.check_file(path / "outcome.json", old["original_outcome_sha256"])
        outcome = bridge.load(path / "outcome.json")
        ex = outcome["execution"]
        bridge.require(
            outcome["job"] == {"task": t, "rep": rep, "arm": "L5"}
            and outcome["plan_sha256"] == receipts.REPEAT_PLAN
            and canonical_sha(ex) == outcome["execution_sha256"],
            "Unmatched original execution",
        )
        stages = {x["stage"]: x for x in ex["stages"]}
        content, source = stages["content"]["product"], original_input[t]
        reply = archived(path / "calls/structure", stages["structure"])
        tree = engine.model.parse_output(
            "structure", reply.wire.decode(), source, content=content
        )
        bridge.require(
            canonical_sha(tree) == old["structure_product_sha256"]
            and tree == reply.product
            and canonical_sha(content)
            == old["content_sha256"]
            == tasks[t]["content_sha256"]
            and canonical_sha(source) == ex["source_canonical_sha256"]
            and old["original_model_accepted"] == (ex["status"] == "accepted")
            and bridge.digest(reply.wire) == old["structure_reply_sha256"]
            and bridge.digest(reply.prompt) == tasks[t]["structure_messages_sha256"]
            and reply.request_id not in ids,
            "Structure, source or independent request differs",
        )
        ids.add(reply.request_id)
        geometries = {c: solver(tree, content) for c, solver in fits.items()}
        # The original falls back on capacity failure before contract/exit checks.
        selected = (
            geometries["SS"] if geometries["SS"] is not None else geometries["CC"]
        )
        historical = stages["geometry"]
        if selected is None:
            bridge.require(
                historical.get("product") is None
                and ex.get("failed_stage") == "geometry"
                and historical["error"]["type"] == "StageError"
                and historical["error"]["message"].startswith("reference_capacity:"),
                "Archived geometry unexpectedly exists",
            )
        else:
            bridge.require(
                historical["status"] == "completed"
                and canonical_sha(selected) == canonical_sha(historical["product"]),
                "Standard-first fallback differs from the frozen geometry",
            )
        measured = {}
        for c, geom in geometries.items():
            if geom is None:
                measured[c] = False
                continue
            try:
                checked = engine.model.parse_output(
                    "geometry",
                    engine.trial.signature(geom),
                    source,
                    content=content,
                    tree=tree,
                )
            except engine.model.ProtocolError:
                measured[c] = False
                continue
            bridge.require(checked == geom, "Geometry changed during contract check")
            measured[c] = frame_issue(geom["root"]) is None
        bridge.require(
            canonical_sha(tree) == old["structure_product_sha256"]
            and canonical_sha(content) == old["content_sha256"],
            "A recipe mutated frozen input",
        )
        calibration["archived_geometry_or_capacity_rejection_reproduced"] += 1
        calibration["archived_completed_geometry"] += (
            historical["status"] == "completed"
        )
        calibration["archived_accepted_exit"] += ex["status"] == "accepted"
        calibration["archived_strict_policy_pass"] += (
            old["strict_judgement"]["verdict"] == "pass"
        )
        rows.append(
            {
                "task": t,
                "rep": rep,
                "fits": measured,
                "solver_fits": {c: g is not None for c, g in geometries.items()},
                "old": old["original_model_accepted"],
                "strict": old["strict_judgement"]["verdict"] == "pass",
            }
        )
    bridge.require(
        len(ids) == 120
        and calibration["archived_accepted_exit"] == 101
        and calibration["archived_strict_policy_pass"] == 50,
        "Historical tail anchors differ",
    )
    return {
        "scope": "Fixed model trees and selected content from the original 12 cases and ten independent replies each. First letter: role fonts; second: gap and root padding. The geometric outcome requires that the complete frozen solver fits the tree and its children fit their frames. It does not re-score native output quality or end-to-end delivery.",
        "assignment": "SS/CS/SC/CC are actually tried on each draw. Standard roles use the frozen 20/14/12fp rules, compact 16/12/12fp; root padding and child gap are respectively 10/4vp or 8/2vp. All four cells retain text, actions, tree, order, reference fonts, measurement and width allocation.",
        "inputs": {
            "repeat_plan": receipts.REPEAT_PLAN,
            "prior_replay": PRIOR,
            "fonts_and_measurer": hashes,
            "pillow": pillow_version,
            "freetype": features.version_module("freetype2"),
        },
        "calibration": dict(calibration),
        "paired_draw_digests": {
            kind: bridge.digest(
                encode(
                    sorted(
                        (r["task"], r["rep"], [r[kind][c] for c in CELLS]) for r in rows
                    )
                )
            )
            for kind in ("solver_fits", "fits")
        },
        "solver_passes_rejected_by_geometry_checks": {
            c: sum(r["solver_fits"][c] and not r["fits"][c] for r in rows)
            for c in CELLS
        },
        "geometric_feasibility": aggregate(rows),
        "geometry_vs_historical_policy": [
            {
                "standard_geometry_fit": s,
                "compact_geometry_fit": c,
                "historical_exit_accepted": a,
                "historical_strict_pass": v,
                "draws": n,
            }
            for (s, c, a, v), n in sorted(
                Counter(
                    (r["fits"]["SS"], r["fits"]["CC"], r["old"], r["strict"])
                    for r in rows
                ).items()
            )
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_batch", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Write a new table; default verifies the published result.",
    )
    args = parser.parse_args()
    report = run(args.formal_batch)
    if args.output:
        with args.output.open("xb") as file:
            file.write(encode(report))
    else:
        public = (
            Path(__file__).resolve().parents[4]
            / "paper/out/tables/fixed_tree_density.json"
        )
        bridge.require(report == bridge.load(public), "Fixed-tree replay differs")
    print(
        "Verified fixed-tree geometry on",
        report["geometric_feasibility"]["draws"],
        "draws",
    )
