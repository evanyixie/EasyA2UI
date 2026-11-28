"""Compare a captured native accessibility tree against its immutable card and input samples.

The result concerns reported control text. A matching string is not proof that every
glyph was painted, that the right content was selected, or that an action worked.
"""

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from . import emit_fidelity as fidelity
from .harness_v2 import program_stages as program

BOUNDS = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked(path, expected_hash):
    content = path.read_bytes()
    require(
        hashlib.sha256(content).hexdigest() == expected_hash, f"Hash mismatch: {path}"
    )
    return content


def nodes(tree):
    yield tree
    for child in tree.get("children", []):
        yield from nodes(child)


def box(raw):
    match = BOUNDS.fullmatch(raw or "")
    return tuple(map(int, match.groups())) if match else None


def control_index(tree, crop):
    frames = [
        n
        for n in nodes(tree)
        if n.get("attributes", {}).get("id") == "a2ui_capture_root"
    ]
    index = defaultdict(list)
    if len(frames) != 1 or box(frames[0]["attributes"].get("bounds")) != crop:
        return index
    for n in nodes(frames[0]):
        attrs = n.get("attributes", {})
        if attrs.get("id"):
            index[attrs["id"]].append(attrs)
    return index


def classify(leaf, controls, crop, data, samples):
    kind = leaf["component"]
    value = leaf["content" if kind == "Text" else "label"]
    parts = fidelity.tokens(value)
    if parts is fidelity.UNKNOWN or (
        isinstance(value, str) and "${" in value and not value.strip().startswith("{{")
    ):
        return "unresolved_expression", None
    paths = [token for t, token in parts if t == "path"]
    if any(path not in samples for path in paths):
        return "unregistered_sample", bool(paths)
    expected = []
    for t, token in parts:
        if t == "text":
            expected.append(token)
            continue
        try:
            sample = program._sample({"value": samples[token]}, "/value")
            actual = program._sample(data, token)
        except program.StageError:
            return "unresolved_sample", True
        if sample != actual:
            return "emitted_sample_differs", True
        expected.append(sample)
    if len(controls) != 1 or controls[0].get("type") != kind:
        return "no_unique_native_control", bool(paths)
    control = controls[0]
    bounds = box(control.get("bounds"))
    if (
        control.get("visible") != "true"
        or not bounds
        or not (
            max(crop[0], bounds[0]) < min(crop[2], bounds[2])
            and max(crop[1], bounds[1]) < min(crop[3], bounds[3])
        )
    ):
        return "no_visible_control_box", bool(paths)
    if not isinstance(control.get("text"), str):
        return "native_text_unavailable", bool(paths)
    return (
        "match" if "".join(expected) == control["text"] else "native_text_differs"
    ), bool(paths)


def observe(capture_dir, receipt, artifact, samples):
    layout = capture_dir / "native-layout.json"
    digest = None
    index = {}
    crop = receipt["terminal"]["cropPx"]
    rect = (
        crop["left"],
        crop["top"],
        crop["left"] + crop["width"],
        crop["top"] + crop["height"],
    )
    if layout.is_file():
        raw = layout.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        index = control_index(json.loads(raw), rect)
    messages = [json.loads(line) for line in artifact.splitlines() if line.strip()]
    components = messages[1]["updateComponents"]
    fidelity.graph(components)
    data = messages[2]["updateDataModel"]["value"]
    leaves = []
    for leaf in components["components"]:
        kind = leaf["component"]
        if kind in ("Text", "Button"):
            state, dynamic = classify(
                leaf, index.get(leaf["id"], []), rect, data, samples
            )
            leaves.append(
                {"id": leaf["id"], "kind": kind, "dynamic": dynamic, "state": state}
            )
        else:
            require(kind in ("Column", "Row"), f"Unassessed component {kind}")
    states = {leaf["state"] for leaf in leaves}
    if states & {"native_text_differs", "emitted_sample_differs"}:
        state = "difference_observed"
    elif states == {"match"}:
        state = "all_control_text_matches"
    else:
        state = "incomplete"
    return {
        "layout_sha256_at_audit": digest,
        "state": state,
        "has_dynamic_text": any(leaf["dynamic"] is True for leaf in leaves),
        "leaves": leaves,
    }


def run(batch):
    endpoint = batch / "pre_score_evidence/endpoint"
    seal = json.loads((endpoint / "receipt.json").read_bytes())
    raw = checked(endpoint / "observations.private.jsonl", seal["observations_sha256"])
    observations = [json.loads(line) for line in raw.splitlines()]
    catalog = json.loads(
        checked(
            batch / "native_live/capture_index.private.json",
            seal["captured_index_sha256"],
        )
    )
    require(
        catalog["state"] == "complete"
        and catalog["queue_sha256"] == seal["version_sha256"],
        "Wrong capture run",
    )
    catalog_paths = {Path(row["proof"]).resolve() for row in catalog["captures"]}
    require(len(catalog_paths) == len(catalog["captures"]), "Duplicate capture")
    reports = {}
    counts = defaultdict(Counter)
    leaves = Counter()
    excluded = Counter()
    seen = set()
    for observation in observations:
        task, arm, phase = (observation[k] for k in ("task_id", "arm", "checkpoint"))
        seat = (task, arm, phase)
        require(seat not in seen, "Duplicate seat")
        seen.add(seat)
        prov = observation["provenance"]
        cap = prov["capture"]
        if not cap:
            excluded[observation["execution"]["status"]] += 1
            continue
        proof = (batch / cap["proof_ref"]).resolve()
        require(proof in catalog_paths, "Observation outside capture index")
        if proof not in reports:
            receipt = json.loads(checked(proof, cap["proof_sha256"]))
            h = observation["artifact_sha256"]
            require(
                (task, arm, h, cap["capture_run_id"], seal["version_sha256"])
                == tuple(
                    receipt[k]
                    for k in ("task", "arm", "input_sha256", "run_id", "queue_sha256")
                )
                and receipt["status"] == "captured"
                and receipt["input_return_sha256"] == h
                and receipt["screenshot_sha256"] == cap["screenshot_sha256"],
                "Capture lineage mismatch",
            )
            checked(batch / cap["screenshot_ref"], cap["screenshot_sha256"])
            artifact = checked(proof.parent / "received-input.jsonl", h)
            source = batch / prov["artifact_ref"]
            checked(source, h)
            registry = (
                batch / "queue/package/registry" / (source.parent.parent.name + ".json")
            )
            entry = json.loads(checked(registry, prov["registry_sha256"]))
            require(entry["id"] == task, "Wrong task registry")
            record = observe(proof.parent, receipt, artifact, entry["binding_samples"])
            record.update(
                task=task, arm=arm, sha256=h, proof=cap["proof_ref"], phases=[]
            )
            reports[proof] = record
            for leaf in record["leaves"]:
                mode = {True: "dynamic", False: "literal", None: "unclassified"}[
                    leaf["dynamic"]
                ]
                leaves[mode + "/" + leaf["state"]] += 1
        record = reports[proof]
        require(
            (task, arm, observation["artifact_sha256"])
            == (record["task"], record["arm"], record["sha256"]),
            "Reused unrelated proof",
        )
        record["phases"].append(phase)
        counts[phase + "/" + arm][record["state"]] += 1
    require(
        set(reports) == catalog_paths and len(seen) == seal["observations"],
        "Incomplete enumeration",
    )
    return list(reports.values()), {
        "captures": len(reports),
        "all_seat_checkpoints": len(seen),
        "distinct_capture_results": dict(Counter(r["state"] for r in reports.values())),
        "distinct_capture_leaf_results": dict(sorted(leaves.items())),
        "layout_files_present": sum(
            r["layout_sha256_at_audit"] is not None for r in reports.values()
        ),
        "by_checkpoint_arm": {k: dict(v) for k, v in sorted(counts.items())},
        "without_capture_by_execution_both_checkpoints": dict(excluded),
        "source_observations_sha256": seal["observations_sha256"],
        "new_model_calls": 0,
        "new_device_actions": 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=Path)
    parser.add_argument("new_output", type=Path)
    args = parser.parse_args()
    results, summary = run(args.batch)
    args.new_output.mkdir(parents=True, exist_ok=False)
    with (args.new_output / "control_text.private.jsonl").open(
        "x", encoding="utf8"
    ) as f:
        for record in results:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    (args.new_output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf8"
    )


if __name__ == "__main__":
    main()
