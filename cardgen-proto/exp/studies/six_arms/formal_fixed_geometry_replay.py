"""Reproduce the archived L4-tree geometry substitution, without a model or device.

iter_pairs yields the custodian's private artifacts and inputs. The CLI prints
only aggregate counts. On another machine set SIX_ARMS_FONT_REGULAR,
SIX_ARMS_FONT_BOLD and optionally SIX_ARMS_MEASURE_PY before starting Python.
"""

import argparse
import json
import os
from collections import Counter
from pathlib import Path, PureWindowsPath

from six_arms.fixed_content_repeats import FORMAL_PLAN, canonical, check, digest
from six_arms.formal_arm_content_yield import technical
from six_arms.formal_repair_receipts import read_exit
from six_arms.matched_structure_repeats import missing_prompt, received_reply
from six_arms.paired_delivery_bounds import ROSTER, verified
from six_arms.portable_layout_engine import HERE, load_engine
from six_arms.technical_yield import read_lines

ARCHIVE = "tech_metrics/continuation_final/same_tree_private"
PAIRS_SHA = "8beb265f91a2e9ca98d18ce1ad50acb40ad1ccd10736b701b3c26c028ac3df1c"
PORTABLE_MEASURE = "253ff21ca8747eff7edbba742d3e32f95a20f8ccd59761ba4efbcde6114ca056"


def frozen_engine(dependencies):
    """Accept relocated identical fonts, and the checked-in reference measurer."""
    pins = {PureWindowsPath(k).name: (Path(k), h) for k, h in dependencies.items()}
    inputs = (
        ("SIX_ARMS_FONT_REGULAR", "HarmonyOS_Sans_SC_Regular.ttf", "regular.ttf"),
        ("SIX_ARMS_FONT_BOLD", "HarmonyOS_Sans_SC_Bold.ttf", "bold.ttf"),
        ("SIX_ARMS_MEASURE_PY", "measure.py", "measure.py"),
    )
    for variable, name, _ in inputs:
        original = pins[name][0]
        if original.is_file():
            os.environ.setdefault(variable, str(original))
    engine = load_engine()
    files = engine.native.dependency_files()
    for _, name, alias in inputs:
        path = files[alias]
        if (
            alias == "measure.py"
            and path.resolve() == HERE / "reference_text_measure.py"
        ):
            verified(path, PORTABLE_MEASURE)
        else:
            verified(path, pins[name][1])
    return engine


def observed_stages(folder, run, source, engine):
    """Verify the original L4 calls. Keep upstream failures and missing answers distinct."""
    products = {}
    conditions = engine.trial.CONDITIONS.CONDITIONS
    check(
        [p for p in engine.trial.PHASES if conditions["L4"][p] != conditions["L5"][p]]
        == ["geometry"],
        "The two registered arms differ outside geometry",
    )
    steps = run["stages"]
    check(
        [s["stage"] for s in steps] == list(engine.trial.PHASES[: len(steps)])
        and all(s["owner"] == conditions["L4"][s["stage"]] for s in steps),
        "Unexpected formal L4 stage sequence or owner",
    )
    for step in steps:
        stage = step["stage"]
        if stage not in ("content", "structure", "geometry"):
            break
        slot = folder / "calls" / stage
        content = products.get("content")
        tree = products.get("structure")
        check(
            step["messages"]
            == engine.model.build_messages(stage, source, content, tree),
            "Archived stage did not see the same inputs",
        )
        if step["status"] == "callback_failed":
            missing_prompt(slot, step)
            break
        reply = received_reply(slot, step)
        wire = reply.wire.decode("utf-8")
        if stage == "content":
            entry = run["entry"]
            # All 219 original L4 entry receipts kept the content word for word.
            check(
                entry["original_text"] == entry["effective_text"] == wire
                and entry["original_sha256"]
                == entry["effective_sha256"]
                == digest(reply.wire),
                "Content entry evidence differs",
            )
        try:
            product = engine.model.parse_output(stage, wire, source, content, tree)
        except engine.STAGE_ERRORS:
            check(
                step["status"] == "stage_rejected",
                "Previously accepted stage now fails",
            )
            break
        check(
            step["status"] == "completed" and product == reply.product,
            "Reproduced stage differs from the sealed original",
        )
        products[stage] = product
    return products


def replay_tail(engine, source, content, tree, entry):
    """Retain the captured tree and run only the L5 program geometry, theme, emit and exit."""
    run = {
        "failed_stage": None,
        "entry": entry,
        "first_native": None,
        "final_native": None,
        "exit": {"status": "not_reached", "rounds": []},
    }
    for stage in ("geometry", "theme", "emit"):
        try:
            wire = engine._program_wire(stage, content, tree, source)
            tree = engine.model.parse_output(stage, wire, source, content, tree)
        except engine.STAGE_ERRORS:
            run.update(status="stage_rejected", failed_stage=stage)
            return run
    engine._finish(tree, source, run)
    return run


def branch(run, archived, files, evidence):
    receipt = read_exit(run, evidence)
    summary = {
        "status": run["status"],
        "failed_stage": run["failed_stage"],
        "exit": receipt["exit_status"],
        "first_sha": receipt["first_sha256"],
        "final_sha": receipt["final_sha256"],
    }
    check(summary == archived, "Historical disposition or artifact digest differs")
    scores = technical(receipt)
    out = {
        "status": run["status"],
        "failed_stage": run["failed_stage"],
        "first_technical": scores["raw_first"],
        "final_technical": scores["after_common_repair"],
    }
    for moment, path in files.items():
        sha = summary[moment + "_sha"]
        if sha is None:
            check(not path.exists(), "Unregistered native file")
            out[moment] = None
        else:
            raw = verified(path, sha)
            check(
                raw == run[moment + "_native"]["text"].encode(), "Artifact bytes differ"
            )
            out[moment] = raw
    return out


def iter_pairs(batch):
    """Yield all 219 formal tasks. A shared upstream stop applies to both policies."""
    batch = Path(batch).resolve()
    plan = json.loads(verified(batch / "live/plan.json", FORMAL_PLAN))
    archive = batch / ARCHIVE
    pairs = {
        r["case"]: r for r in read_lines(archive / "pairs.private.jsonl", PAIRS_SHA)
    }
    roster = {
        r["task_id"]: r for r in read_lines(batch / "analysis/roster.jsonl", ROSTER)
    }
    cases = plan["assignment"]["cases"]
    check(
        len(cases) == len(roster) == len(pairs) == 219
        and {c["id"] for c in cases} == roster.keys() == pairs.keys(),
        "Wrong formal assignments",
    )
    engine = frozen_engine(plan["dependencies"])
    pkg = batch / "queue/package"
    for case in cases:
        task, fid = case["id"], case["file_id"]
        check(digest(task.encode()) == fid, "Formal file key differs")
        historic = pairs[task]
        folder = batch / "live" / fid / "L4"
        original = json.loads(
            verified(folder / "outcome.json", historic["original_outcome_sha256"])
        )
        run = original["execution"]
        request = json.loads(
            verified(pkg / "requests" / (fid + ".json"), case["input_sha256"])
        )
        reg = json.loads(
            verified(pkg / "registry" / (fid + ".json"), case["registry_sha256"])
        )
        source = engine.trial.source_for(request, reg["data_model"])
        check(
            original["task"] == reg["id"] == task
            and original["arm"] == "L4"
            and original["plan_sha256"] == FORMAL_PLAN
            and reg["input_sha"] == case["input_sha256"]
            and digest(canonical(run)) == original["execution_sha256"]
            and digest(canonical(source)) == run["source_canonical_sha256"],
            "Original L4 execution linkage differs",
        )
        products = observed_stages(folder, run, source, engine)
        reached = "structure" in products
        check(
            historic["state"] == ("paired" if reached else "upstream_not_reached"),
            "Geometry opportunity differs",
        )
        moments = ("first", "final")
        model = branch(
            run,
            historic["l4"],
            {m: folder / f"{m}_native.a2ui.jsonl" for m in moments},
            engine.evidence,
        )
        comparison_files = {m: archive / f"{task}_{m}_native.jsonl" for m in moments}
        if reached:
            check(
                {p: digest(canonical(products[p])) for p in ("content", "structure")}
                == historic["upstream_sha256"],
                "Paired content or tree differs",
            )
            counterfactual = replay_tail(
                engine, source, products["content"], products["structure"], run["entry"]
            )
            program = branch(
                counterfactual,
                historic["program_geometry"],
                comparison_files,
                engine.evidence,
            )
        else:
            check(
                model["first"] is None
                and model["final"] is None
                and not any(p.exists() for p in comparison_files.values()),
                "Artifact after a shared upstream failure",
            )
            program = model.copy()
        yield {
            "task": task,
            "family": roster[task]["family"],
            "in_217": roster[task]["included_in_217_sensitivity"],
            "reached": reached,
            "source": source,
            "model": model,
            "program": program,
        }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("batch", type=Path)
    rows = list(iter_pairs(cli.parse_args().batch))
    paired = [r for r in rows if r["reached"]]
    print(
        json.dumps(
            {
                "assigned": len(rows),
                "reached": len(paired),
                "registry_sha256": PAIRS_SHA,
                "paired": {
                    moment: dict(
                        Counter(
                            "/".join(r[a][moment] for a in ("model", "program"))
                            for r in paired
                        )
                    )
                    for moment in ("first_technical", "final_technical")
                },
            },
            indent=2,
        )
    )
