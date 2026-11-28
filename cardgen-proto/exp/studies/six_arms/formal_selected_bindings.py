"""Track accepted content-stage paths to emitted A2UI and native first-frame controls."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from six_arms.fixed_content_repeats import FORMAL_PLAN, check
from six_arms.formal_reference_cost import encode, registered_sources
from six_arms.matched_content_repeats import ARMS, VALID, verified_response
from six_arms.native_repeated_facts import PINS, checked_rows
from six_arms.paired_delivery_bounds import POINTS, verified
from six_arms.selected_binding_frames import load_frame_index, verified_paths
from six_arms.selected_bindings import inspect_selected
from six_arms.web_geometry_inputs import load_inputs

TABLE = (
    Path(__file__).resolve().parents[4]
    / "paper/out/tables/formal_selected_bindings.json"
)


def selection(folder, obs, registered):
    """Use the accepted product (including common entry repair), never a rejected proposal."""
    p = obs["provenance"]
    record = json.loads(verified(folder / "outcome.json", p["outcome_sha256"]))
    run = record["execution"]
    check(
        (
            record["task"],
            record["arm"],
            record["plan_sha256"],
            record["execution_sha256"],
        )
        == (obs["task_id"], obs["arm"], FORMAL_PLAN, p["execution_sha256"]),
        "Content stage belongs to another execution",
    )
    _, wire, _ = verified_response(folder, run)
    step = run["stages"][0]
    product = step.get("product")
    if product is None:
        expected = "callback_failed" if wire is None else "stage_rejected"
        check(step["status"] == expected, "Indeterminate content outcome")
        return expected, None
    entry = run["entry"]["status"]
    check(
        wire is not None and step["status"] == "completed" and entry in VALID,
        "Unaccepted selection",
    )
    paths = frozenset(item["path"] for item in product["items"] if "path" in item)
    check(paths <= registered, "Selected path absent from the frozen request")
    return entry, paths


def counts(rows):
    total = Counter()
    states = Counter()
    for r in rows:
        total["seats"] += 1
        states[r["entry"]] += 1
        total["artifacts"] += r["emitted"]
        total["captures"] += r["captured"]
        wanted = r["wanted"]
        if wanted is None:
            continue
        total["accepted_selections"] += 1
        total["selected_task_paths"] += len(wanted)
        if not wanted:
            total["accepted_without_dynamic_paths"] += 1
            continue
        total["accepted_with_dynamic_paths"] += 1
        if not r["emitted"]:
            total["selected_task_paths_without_artifact"] += len(wanted)
            continue
        total["emitted_with_dynamic_paths"] += 1
        total["selected_task_paths_with_artifact"] += len(wanted)
        total["referenced_task_paths"] += len(r["present"])
        total["absent_task_paths"] += len(r["absent"])
        total["unresolved_artifact_task_paths"] += len(r["unresolved"])
        total["native_confirmed_task_paths"] += len(r["confirmed"])
        total["all_selected_referenced"] += wanted == r["present"]
        total["all_selected_native_confirmed"] += wanted == r["confirmed"]
        if not r["captured"]:
            total["selected_task_paths_without_capture_on_emitted"] += len(wanted)
    check(
        total["selected_task_paths"]
        == total["selected_task_paths_with_artifact"]
        + total["selected_task_paths_without_artifact"],
        "Lost selected-path denominator",
    )
    check(
        total["selected_task_paths_with_artifact"]
        == total["referenced_task_paths"]
        + total["absent_task_paths"]
        + total["unresolved_artifact_task_paths"],
        "Incomplete artifact path accounting",
    )
    return {"counts": dict(total), "entry_outcomes": dict(states)}


def paired(rows, first, second):
    index = {(r["task"], r["arm"]): r for r in rows}
    check(len(index) == len(rows), "Duplicate task and arm in paired input")
    counts = Counter()
    output = Counter()
    one_sided_exits = {arm: Counter() for arm in (first, second)}
    for task in {r["task"] for r in rows}:
        a, b = (index[task, arm] for arm in (first, second))
        counts["assigned"] += 1
        if not (a["wanted"] and a["wanted"] == b["wanted"]):
            continue
        counts["same_nonempty_selected_path_set"] += 1
        output[
            {
                (True, True): "both",
                (True, False): "only_first",
                (False, True): "only_second",
                (False, False): "neither",
            }[a["emitted"], b["emitted"]]
        ] += 1
        if a["emitted"] != b["emitted"]:
            missing = b if a["emitted"] else a
            one_sided_exits[missing["arm"]][missing["exit_reason"]] += 1
        if not (a["emitted"] and b["emitted"]):
            continue
        counts["both_emitted_same_nonempty_set"] += 1
        a_verified, b_verified = (r["confirmed"] == r["wanted"] for r in (a, b))
        label = {
            (True, True): "both_confirmed",
            (False, True): "only_second_confirmed",
            (True, False): "only_first_confirmed",
            (False, False): "neither_confirmed",
        }[a_verified, b_verified]
        counts[label] += 1
    return {
        **counts,
        "artifact_availability_on_same_nonempty_set": dict(output),
        "missing_arm_at_one_sided_exits": one_sided_exits,
    }


def run(batch):
    plan = json.loads(verified(batch / "live/plan.json", FORMAL_PLAN))
    cases = {c["id"]: c for c in plan["assignment"]["cases"]}
    formal = checked_rows(
        batch / "pre_score_evidence/endpoint/observations.private.jsonl",
        PINS["observations"],
    )
    subjects = {(o["task_id"], o["arm"], o["checkpoint"]): o for o in formal}
    frames = load_frame_index(batch)
    # load_inputs independently verifies source data, lineage and every archived artifact.
    seats = load_inputs(batch)
    registered = {task: set(values) for task, _, _, values in registered_sources(batch)}
    check(registered.keys() == cases.keys(), "Different request and phase rosters")
    selections = {}
    rows = []
    for s in seats:
        if s.arm not in ARMS:  # L1 produces A2UI directly.
            continue
        key = s.task, s.arm
        obs = subjects[(*key, s.checkpoint)]
        if key not in selections:
            folder = batch / "live" / cases[s.task]["file_id"] / s.arm
            selections[key] = selection(folder, obs, registered[s.task])
        entry, wanted = selections[key]
        emitted = s.path is not None
        captured = obs["provenance"]["capture"] is not None
        check(
            (not emitted or wanted is not None) and (not captured or emitted),
            "Downstream evidence without upstream input",
        )
        raw = verified(s.path, s.artifact_sha256) if emitted else None
        traced = inspect_selected(wanted or set(), raw)
        confirmed = (
            verified_paths(batch, obs, raw, frames) & wanted
            if captured and wanted
            else frozenset()
        )
        check(confirmed <= traced["present"], "Unattributed native confirmation")
        rows.append(
            {
                "task": s.task,
                "arm": s.arm,
                "phase": s.checkpoint,
                "entry": entry,
                "wanted": wanted,
                "emitted": emitted,
                "captured": captured,
                "exit_reason": "/".join(
                    str(obs["provenance"].get(k) or "unspecified")
                    for k in ("runner_status", "failed_stage")
                ),
                "confirmed": confirmed,
                **traced,
            }
        )
    phases = {}
    for point in POINTS:
        part = [r for r in rows if r["phase"] == point]
        check(len(part) == 219 * len(ARMS), "Wrong formal denominator")
        phases[point] = {
            "overall": counts(part),
            "arms": {arm: counts(r for r in part if r["arm"] == arm) for arm in ARMS},
            "same_paths_on_emitted_pairs": {
                f"{a}_{b}": paired(part, a, b)
                for a, b in (("L2", "L3"), ("L4", "L5"), ("L5", "L6"))
            },
        }
    return {
        "formal_plan_sha256": FORMAL_PLAN,
        "observations_sha256": PINS["observations"],
        "native_text_audit_sha256": PINS["control_text"],
        "l1_unobservable_seats_per_checkpoint": len(cases),
        "phases": phases,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_root", type=Path)
    parser.add_argument("--output", type=Path, help="Write a new anonymous aggregate")
    args = parser.parse_args()
    result = run(args.formal_root)
    if args.output:
        with args.output.open("xb") as dest:
            dest.write(encode(result))
    else:
        check(result == json.loads(TABLE.read_bytes()), "Selected-path table differs")
    print("Verified both checkpoints of 1,095 staged formal seats.")
