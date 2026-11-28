"""Replay archived free and rule-selected trees on the original fixed-content program backend."""

import argparse
import hashlib
import importlib
import json
import sys
from collections import Counter
from functools import partial
from pathlib import Path
from types import SimpleNamespace

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fixed_layout.paired_analysis import analyze

FREEZE = "5e26a7fafe099bb816d644efd6e34d1221b88f3325bc4e260ea363028bc41d62"
SEAL = "130b6be7c098770a4eb300312b783f44db7e22ed945c06c01823295dc45113bc"
TABLE = (
    Path(__file__).resolve().parents[4]
    / "paper/out/tables/formal_content_only_structure_bridge.json"
)
ARMS = ("model_model", "program_program")
REJECT = (ValueError, TypeError, KeyError, RecursionError)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verified(path, sha):
    data = path.read_bytes()
    require(digest(data) == sha, "Archived file hash differs")
    return data


def encoded(value):
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        + "\n"
    ).encode()


def dependencies(freeze):
    paths = {}
    for ref, sha in freeze["dependencies"].items():
        path = Path(ref)
        require(path.name not in paths, "Ambiguous frozen dependency")
        verified(path, sha)
        paths[path.name] = path
    for name in ("gold_trial.py", "verify_method.py", "verify_golden.py"):
        sys.path.insert(0, str(paths[name].parent))
    method = importlib.import_module("verify_method")
    base = method.run
    contract = importlib.import_module("verify_golden")
    for module in (
        base,
        base.common,
        base.layout,
        base.trial,
        base.layout.stages,
        method,
        contract,
    ):
        path = Path(module.__file__).resolve()
        require(
            path == paths[path.name].resolve(),
            "Historical module name collision; launch in a fresh process",
        )
    return SimpleNamespace(base=base, contract=contract, method=method, paths=paths)


def route_projection(view):
    """Use only fields in the exact structure prompt, before any common downstream binding."""
    require(
        set(view)
        == {
            "visible",
            "entities",
            "relations",
            "actions",
            "canvas",
            "user_preferences",
            "reference",
        },
        "Changed structure input",
    )
    return {
        "units": view["visible"],
        **{k: view[k] for k in ("entities", "relations", "actions", "canvas")},
    }


def replay_tree(base, shared, obtain, receipt):
    try:
        tree = obtain()
        base.common.roles_and_clicks(tree, shared)
        base.layout.validate_tree(tree, shared)
    except REJECT as exc:
        require(
            receipt["status"] == "rejected"
            and (receipt["error_type"], receipt["detail"])
            == (type(exc).__name__, str(exc)),
            "Stored structure rejection differs",
        )
        return None
    require(receipt["status"] == "accepted", "Stored accepted structure differs")
    return tree


def acquired_model_tree(engine, folder, entry, messages, shared):
    base = engine.base
    slot = folder / "calls/structure"
    call = json.loads((slot / "call.json").read_bytes())
    actual = json.loads((slot / "messages.json").read_bytes())
    require(
        actual == messages
        and digest(base.trial.signature(actual).encode())
        == call["prompt_sha256"]
        == entry["prompt_sha256"],
        "Actual model structure input differs",
    )
    require(
        call["stage"] == "structure" and call["http_status"] == entry["http_status"],
        "Unknown request provenance",
    )
    if entry["status"] == "transport_unknown":
        require(
            not (slot / "response.txt").is_file() and call["http_status"] != 200,
            "Unexpected response for unavailable tree",
        )
        return None
    envelope = json.loads(verified(slot / "response.body", call["envelope_sha256"]))
    raw = verified(slot / "response.txt", call["response_sha256"]).decode("utf8")
    require(
        call["http_status"] == 200
        and raw == envelope["choices"][0]["message"]["content"],
        "Model structure reply mismatch",
    )
    return replay_tree(base, shared, lambda: base.parse(raw), entry)


def compile_tree(engine, tree, shared, source):
    """Use identical geometry, emission, protocol, reference geometry and source/ownership audit."""
    base = engine.base
    try:
        geometry = base.layout.program_geometry(tree, shared)
    except base.layout.stages.StageError as exc:
        require(exc.code == "reference_capacity", "Unexpected geometry failure")
        return {"state": "geometry_rejected"}
    try:
        messages = base.common.emit(geometry, shared, tree)
        wire = "\n".join(base.trial.signature(m) for m in messages)
        if list(base.trial.VALIDATE(wire, "surface_card", shared["size"])):
            return {"state": "emit_rejected", "geometry": geometry}
    except (ValueError, TypeError, KeyError):
        return {"state": "emit_rejected", "geometry": geometry}
    try:
        status = engine.contract.check_native(source, messages)["static_status"]
    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        ArithmeticError,
        RecursionError,
    ):
        status = "unresolved"
    require(
        status in ("verified", "mismatch", "unresolved"),
        "Invalid native contract decision",
    )
    try:
        geometry_ok = not engine.method.geometry_gates(messages, shared)
    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        ArithmeticError,
        RecursionError,
    ):
        geometry_ok = None
    state = (
        "pass"
        if geometry_ok is True and status == "verified"
        else (
            "failed_check"
            if geometry_ok is False or status == "mismatch"
            else "static_unknown"
        )
    )
    return {
        "state": state,
        "reference_geometry_pass": geometry_ok,
        "static_contract": status,
        "geometry": geometry,
        "artifact_sha256": digest((wire + "\n").encode()),
    }


def stored_tree(folder, receipt, tree):
    p = folder / "structure.json"
    if tree is None:
        require(
            not p.exists() and not receipt.get("decision_sha256"),
            "Rejected structure with output",
        )
    else:
        require(
            tree == json.loads(verified(p, receipt["decision_sha256"])),
            "Replayed tree differs from submitted tree",
        )


def program_diagonal(folder, receipt, result):
    """Verify the original program-arm decisions/bytes, including rejections."""
    if result["state"] in ("structure_rejected", "geometry_rejected"):
        stage = "structure" if result["state"] == "structure_rejected" else "geometry"
        require(
            receipt[stage]["status"] == "rejected"
            and receipt.get("artifact_sha256") is None,
            "Program rejection changed",
        )
    else:
        geo = receipt["geometry"]
        require(
            geo["status"] == "accepted"
            and json.loads(verified(folder / "geometry.json", geo["decision_sha256"]))
            == result["geometry"],
            "Program geometry differs from recorded decision",
        )
        if result["state"] == "emit_rejected":
            require(
                receipt["status"] == "emit_rejected"
                and not receipt.get("artifact_sha256"),
                "Historical program emitter differed",
            )
            return
        require(
            result["artifact_sha256"] == receipt["artifact_sha256"],
            "Program wire differs",
        )
        verified(folder / "card.a2ui.jsonl", receipt["artifact_sha256"])


def outcome(state):
    if state == "pass":
        return "pass"
    if state in ("transport_unknown", "static_unknown"):
        return "missing"
    require(
        state
        in (
            "shared_rejected",
            "structure_rejected",
            "geometry_rejected",
            "emit_rejected",
            "failed_check",
        ),
        "Unregistered state",
    )
    return "fail"


def summarize(rows):
    require(
        len({r["task"] for r in rows}) == len(rows) and bool(rows), "Duplicate tasks"
    )
    result = {}
    cohorts = {
        "assigned": rows,
        "shared_content_ready": [r for r in rows if r["shared"]],
        "both_original_trees_accepted": [r for r in rows if r["both"]],
    }
    for name, cases in cohorts.items():
        if not cases:
            result[name] = {"tasks": 0}
            continue
        model, program = ARMS
        roster = [{"task_id": r["task"], "family_id": r["family"]} for r in cases]
        votes = [
            {
                "task_id": r["task"],
                "A": outcome(r[model]["state"]),
                "B": outcome(r[program]["state"]),
                "missing_reason": "Unassessable or missing recorded input",
            }
            for r in cases
        ]
        tri = analyze(roster, votes)
        delivery = analyze(
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
        result[name] = {
            "tasks": len(cases),
            "families": len({r["family"] for r in cases}),
            "model_tree": arm_summary(cases, model),
            "program_tree": arm_summary(cases, program),
            "both_conclusive_pass": tri["both_pass"],
            "only_model_pass_other_fail": tri["only_A_model_pass"],
            "only_program_pass_other_fail": tri["only_B_program_pass"],
            "both_conclusive_fail": tri["both_fail"],
            "one_or_more_unknown": tri["pairs_with_missing"],
            "program_minus_model_rate_bounds": tri[
                "all_assigned_difference_bounds_B_minus_A"
            ],
            "obtained_pass_difference_rate": delivery["all_assigned_point_difference"],
            "obtained_pass_difference_family_ci95": delivery[
                "paired_cluster_percentile_ci95"
            ],
        }
    return result


def arm_summary(cases, arm):
    cells = [r[arm] for r in cases]
    return {
        "states": dict(sorted(Counter(v["state"] for v in cells).items())),
        "wire_emitted": sum(bool(v.get("artifact_sha256")) for v in cells),
        "strict_reference_geometry_pass": sum(
            v.get("reference_geometry_pass") is True for v in cells
        ),
        "frozen_semantic_and_action_contract": dict(
            sorted(
                Counter(
                    v["static_contract"] for v in cells if "static_contract" in v
                ).items()
            )
        ),
    }


def run(batch):
    freeze = json.loads(verified(batch / "freeze.json", FREEZE))
    seal = json.loads(verified(batch / "seal.json", SEAL))
    require(
        seal["freeze_sha256"] == FREEZE and seal["receipts_count"] == 438,
        "Unmatched historical seal",
    )
    engine = dependencies(freeze)
    inputs = {
        json.loads(s)["task_id"]: (digest(s), json.loads(s))
        for s in engine.paths["layout_inputs.jsonl"].read_bytes().splitlines()
        if s.strip()
    }
    groups = {
        d["task_id"]: d["family_id"]
        for s in engine.paths["roster.jsonl"].read_bytes().splitlines()
        if (d := json.loads(s))
    }
    require(
        len(inputs) == len(freeze["queue"]) == 219 and set(inputs) == set(groups),
        "Wrong fixed-content cohort",
    )
    rows = []
    for assignment in freeze["queue"]:
        tid = assignment["task_id"]
        sig, source = inputs[tid]
        require(
            sig == assignment["input_line_sha256"], "Source content contract changed"
        )
        home = batch / "results" / tid
        prep = json.loads((home / "input_receipt.json").read_bytes())
        rec = {}
        for arm in ARMS:
            relative = f"results/{tid}/{arm}/receipt.json"
            rec[arm] = json.loads(
                verified(batch / relative, seal["arm_receipt_sha256"][relative])
            )
            require(
                rec[arm]["first_pass"]
                and rec[arm]["task_id"] == tid
                and rec[arm]["cell"] == arm
                and rec[arm]["source_row_sha256"] == prep["source_row_sha256"] == sig
                and rec[arm]["shared_sha256"] == prep.get("shared_sha256")
                and rec[arm]["reference_sha256"] == prep.get("reference_sha256"),
                "Fixed input or original arm differs",
            )
        admitted = prep["status"] == "accepted"
        row = {"task": tid, "family": groups[tid], "shared": admitted, "both": False}
        rows.append(row)
        if not admitted:
            require(
                prep["status"] in ("adapter_rejected", "reference_rejected")
                and all(not r["structure"] for r in rec.values()),
                "Skipped common input has structure",
            )
            for arm in ARMS:
                row[arm] = {"state": "shared_rejected"}
            continue
        shared = json.loads(
            verified(batch / "shared_inputs" / (tid + ".json"), prep["shared_sha256"])
        )
        reference = json.loads(
            verified(home / "reference.json", prep["reference_sha256"])
        )
        msgs = engine.base.prompt("structure", shared, reference)
        view = json.loads(msgs[-1]["content"])
        projection = route_projection(view)
        trees = []
        for arm in ARMS:
            folder = home / arm
            entry = rec[arm]["structure"]
            require(
                entry == json.loads((folder / "structure_receipt.json").read_bytes()),
                "Structure receipt differs",
            )
            if arm == "model_model":
                tree = acquired_model_tree(engine, folder, entry, msgs, shared)
            else:
                tree = replay_tree(
                    engine.base,
                    shared,
                    partial(engine.base.layout.program_route, projection),
                    entry,
                )
            stored_tree(folder, entry, tree)
            trees.append(tree)
            if tree is None:
                result = {
                    "state": "transport_unknown"
                    if entry["status"] == "transport_unknown"
                    else "structure_rejected"
                }
            else:
                result = compile_tree(engine, tree, shared, source)
            if arm == "program_program":
                program_diagonal(folder, rec[arm], result)
            row[arm] = {k: v for k, v in result.items() if k != "geometry"}
        row["both"] = all(t is not None for t in trees)
        row["same_tree"] = row["both"] and trees[0] == trees[1]
        old_model = rec[ARMS[0]].get("artifact_sha256")
        if old_model:
            verified(home / ARMS[0] / "card.a2ui.jsonl", old_model)
        new = row[ARMS[0]].get("artifact_sha256")
        old_program = rec[ARMS[1]].get("artifact_sha256")
        row["both_artifacts"] = bool(new and old_program)
        row["same_artifact"] = bool(new and new == old_program)
        row["matches_any_historical_artifact"] = bool(
            new and new in (old_program, old_model)
        )
    return {
        "freeze_sha256": FREEZE,
        "original_seal_sha256": SEAL,
        "per_case_receipt_sha256": digest(
            encoded(sorted(rows, key=lambda r: r["task"]))
        ),
        "identical_trees_among_paired": sum(bool(r.get("same_tree")) for r in rows),
        "both_program_backend_artifacts": sum(
            bool(r.get("both_artifacts")) for r in rows
        ),
        "both_program_backend_artifacts_identical": sum(
            bool(r.get("same_artifact")) for r in rows
        ),
        "model_tree_artifact_identical_to_either_historical_artifact_on_same_task": sum(
            bool(r.get("matches_any_historical_artifact")) for r in rows
        ),
        "results": summarize(rows),
        "scope": (
            "Post-hoc common-backend replay of the November 25 fixed-content study. "
            "The model received visible units, roles, entities, relations, action owners, "
            "preferences, a canvas and a reference width table. The rules read only fields "
            "from that projection and computed needed widths with the frozen font metrics. "
            "The model could submit any accepted Row/Column tree; the fixed rules produced "
            "a tree of that grammar without enumerating a common finite menu. Both original "
            "trees kept their submitted topology and leaf IDs through the same frozen geometry, "
            "emitter, protocol, reference geometry and static source/action checks. "
            "Identical wire bytes identify candidates for same-task screenshot reuse. "
            "This replay adds no device or independent human observations. "
            "The separate 187-case experiment used different content contracts."
        ),
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("fixed_layout_custody_batch", type=Path)
    cli.add_argument(
        "--output",
        type=Path,
        help="Write a new anonymous aggregate; default verifies the published table",
    )
    args = cli.parse_args()
    result = run(args.fixed_layout_custody_batch.resolve())
    if args.output:
        with args.output.open("xb") as f:
            f.write(encoded(result))
    else:
        require(result == json.loads(TABLE.read_bytes()), "Public aggregate differs")
    print(
        "Verified",
        result["results"]["assigned"]["tasks"],
        "assigned fixed-content pairs",
    )
