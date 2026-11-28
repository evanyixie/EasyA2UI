"""Replay adjacent stage substitutions against a custodian's frozen formal batch.

Run in a fresh Python process. The batch supplies its original queue adapter,
registered business inputs, sealed source checksums and observed model replies.
The evaluator directory supplies the independent emit_fidelity checker.
No model service, phone, gold answers or ratings are needed.
"""

import argparse
import hashlib
import importlib
import json
import socket
import sys
from collections import Counter
from pathlib import Path

CONTRASTS = (("L2", "L3", "emit"), ("L3", "L4", "theme"), ("L5", "L6", "structure"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(ok, reason):
    if not ok:
        raise ValueError(reason)


def compare(
    folder, prior, program_arm, stage, source, registry, engine, fidelity, stable
):
    before = {s["stage"]: s for s in prior["stages"]}
    prefix = engine.trial.PHASES[: engine.trial.PHASES.index(stage)]
    if stage not in before:
        return {
            "reach": "upstream_not_reached",
            "first_error_stage": prior["failed_stage"],
        }
    used = []

    def recorded(phase, prompt):
        verify(phase in prefix and phase not in used, "unexpected model call")
        slot = folder / "calls" / phase
        wire = (slot / "response.txt").read_bytes()
        old = before[phase]
        verify(
            sha(wire) == old["raw_sha256"]
            and json.loads((slot / "messages.json").read_bytes())
            == prompt
            == old["messages"],
            "original model input or reply differs",
        )
        used.append(phase)
        return wire

    result = engine.execute_case(program_arm, source, recorded, registry_case=registry)
    after = {s["stage"]: s for s in result["stages"]}
    verify(used == list(prefix) and stage in after, "incomplete prefix")
    for phase in prefix:
        verify(
            stable(before[phase]["product"]) == stable(after[phase]["product"]),
            "prefix product differs",
        )
    verify(
        before[stage]["owner"].startswith("model_")
        and not after[stage]["owner"].startswith("model_"),
        "stage owner",
    )
    original_stage_call = folder / "calls" / stage
    content = after["content"]["product"]
    tree = None if stage == "structure" else after[prefix[-1]]["product"]
    target_prompt = engine.model.build_messages(
        stage, source, content=content, tree=tree
    )
    verify(
        json.loads((original_stage_call / "messages.json").read_bytes())
        == before[stage]["messages"]
        == target_prompt,
        "target prompt differs",
    )
    if before[stage]["raw_sha256"]:
        verify(
            sha((original_stage_call / "response.txt").read_bytes())
            == before[stage]["raw_sha256"],
            "target reply differs",
        )
    row = {
        "reach": "paired",
        "source_sha": prior["source_canonical_sha256"],
        "prefix_hashes": [stable(before[p]["product"]) for p in prefix],
    }
    verify(row["source_sha"] == result["source_canonical_sha256"], "source differs")
    for label, stages, branch in (("model", before, prior), ("program", after, result)):
        row[label + "_stage"] = stages[stage]["status"]
        row[label + "_terminal"] = branch["status"]
        row[label + "_failed_stage"] = branch["failed_stage"]
        for moment in ("first", "final"):
            card = branch[moment + "_native"]
            if card:
                raw = card["text"].encode()
                verify(sha(raw) == card["sha256"], "native checksum")
                if label == "model":
                    verify(
                        raw == (folder / (moment + "_native.a2ui.jsonl")).read_bytes(),
                        "sealed native differs",
                    )
            row[label + "_" + moment] = card["sha256"] if card else None
        if stage == "emit" and branch["first_native"]:
            rows = list(map(json.loads, branch["first_native"]["text"].splitlines()))
            audit = fidelity.audit(
                stages["content"]["product"], stages["theme"]["product"], rows, source
            )
            row[label + "_emit_fidelity"] = audit["status"]
            row[label + "_emit_dimensions"] = audit["dimensions"]
    return row


def count(rows):
    pairs = [r for r in rows if r["reach"] == "paired"]
    counts = {
        key: dict(Counter(r[key] for r in pairs))
        for key in (
            "model_stage",
            "program_stage",
            "model_terminal",
            "program_terminal",
        )
    }
    for moment in ("first", "final"):
        artifacts = [(r["model_" + moment], r["program_" + moment]) for r in pairs]
        counts[moment + "_artifacts"] = {
            "model": sum(bool(a) for a, b in artifacts),
            "program": sum(bool(b) for a, b in artifacts),
            "both": sum(bool(a and b) for a, b in artifacts),
            "both_same_bytes": sum(bool(a and a == b) for a, b in artifacts),
        }
    for label in ("model", "program"):
        key = label + "_emit_fidelity"
        if any(key in r for r in pairs):
            counts[key] = dict(Counter(r.get(key, "no_first_native") for r in pairs))
    return {
        "assigned": len(rows),
        "reached": len(pairs),
        "upstream_stopped": len(rows) - len(pairs),
        **counts,
    }


def main(args):
    def offline(*args, **kwargs):
        raise RuntimeError("offline")

    socket.socket.connect = offline
    socket.socket.connect_ex = offline
    sys.path.insert(0, str(args.base / "queue"))
    prep = importlib.import_module("prepare_queue")
    sys.path.insert(0, str(args.fidelity_dir))
    fidelity = importlib.import_module("emit_fidelity")
    run = args.base / "live"
    plan = prep.read(run / "plan.json")
    plan_sha = prep.queue.stable_hash(plan)
    receipt = prep.read(
        args.base / "tech_metrics/continuation_final/completion_receipt.json"
    )
    verify(receipt["complete"] and plan_sha == receipt["plan_sha256"], "wrong batch")
    named = {
        "input_adapter": Path(prep.__file__),
        "two_case_adapter": prep.TWO,
        "package_manifest": args.base / "queue/package/manifest.private.json",
    }
    for path, expected in plan["dependencies"].items():
        verify(
            sha(named.get(path, Path(path)).read_bytes()) == expected,
            "frozen dependency differs",
        )
    load = prep.FrozenPackage(args.base / "queue/package")
    roster = {
        r["task_id"]: r for r in prep.read_rows(args.base / "analysis/roster.jsonl")
    }
    records = {stage: [] for _, _, stage in CONTRASTS}
    for case in plan["assignment"]["cases"]:
        raw, reg = load(case["id"])
        prep.queue.ensure_identity(case, raw, reg)
        source = prep.engine.trial.source_for(json.loads(raw), reg["data_model"])
        for orig, other, stage in CONTRASTS:
            folder = run / case["file_id"] / orig
            prior = prep.queue.read_outcome(
                folder / "outcome.json", case["id"], orig, plan_sha
            )
            row = compare(
                folder,
                prior,
                other,
                stage,
                source,
                reg,
                prep.engine,
                fidelity,
                prep.queue.stable_hash,
            )
            row.update(
                task=case["id"],
                in_217=roster[case["id"]]["included_in_217_sensitivity"],
                outcome_sha=sha((folder / "outcome.json").read_bytes()),
            )
            records[stage].append(row)
    report = {
        "formal_plan_sha": plan_sha,
        "evaluator_sha": sha(Path(fidelity.__file__).read_bytes()),
        "script_sha": sha(Path(__file__).read_bytes()),
        "new_model_calls": 0,
        "new_device_calls": 0,
    }
    report["all_219"] = {stage: count(rows) for stage, rows in records.items()}
    report["source_217"] = {
        stage: count([r for r in rows if r["in_217"]])
        for stage, rows in records.items()
    }
    for stage, rows in records.items():
        verify(
            len({r["task"] for r in rows}) == len(rows) == 219,
            "duplicate or missing task",
        )
        prep.write(
            args.out / (stage + ".private.jsonl"),
            b"".join(prep.canonical(r) + b"\n" for r in rows),
        )
    prep.write(
        args.out / "summary.json",
        json.dumps(report, indent=2, ensure_ascii=False).encode("utf8"),
    )
    print(json.dumps(report["all_219"]))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("base", "fidelity_dir", "out"):
        p.add_argument(name, type=Path)
    main(p.parse_args())
