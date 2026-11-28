"""Registered paths supported by matching first-frame native control text."""

import hashlib
import json
from dataclasses import dataclass, field

from six_arms import emit_fidelity, native_repeated_facts, selected_bindings
from six_arms import native_text_audit as native
from six_arms.reference_content import surface_data


@dataclass
class _Frame:
    audit: dict
    phases: dict = field(default_factory=dict)
    paths: frozenset | None = None


def load_frame_index(batch):
    """Index verified original control audits and the frozen seats that may reuse them."""
    base = batch / "pre_score_evidence"
    audits = native_repeated_facts.checked_rows(
        base / "native_control_text_20261128/control_text.private.jsonl",
        native_repeated_facts.PINS["control_text"],
    )
    frames = {r["proof"]: _Frame(r) for r in audits}
    native.require(len(frames) == len(audits), "Duplicate audited proof")
    observations = native_repeated_facts.checked_rows(
        base / "endpoint/observations.private.jsonl",
        native_repeated_facts.PINS["observations"],
    )
    for obs in observations:
        prov, phase = obs["provenance"], obs["checkpoint"]
        cap = prov["capture"]
        if cap is None:
            continue
        frame = frames.get(cap["proof_ref"])
        native.require(frame is not None, "Unknown audited proof")
        r = frame.audit
        native.require(
            (r["task"], r["arm"], r["sha256"])
            == (obs["task_id"], obs["arm"], obs["artifact_sha256"])
            and cap["artifact_sha256"] == r["sha256"]
            and phase in r["phases"]
            and phase not in frame.phases,
            "Seat and audited proof disagree",
        )
        for previous in frame.phases.values():
            native.require(
                previous["capture"] == cap
                and previous["registry_sha256"] == prov["registry_sha256"],
                "Reused proof changed capture or registered samples",
            )
        frame.phases[phase] = prov
    native.require(
        all(set(f.phases) == set(f.audit["phases"]) for f in frames.values()),
        "Incomplete frozen capture mapping",
    )
    return frames


def _matched_paths(raw, tree, rect, samples, audited_leaves):
    graph, data, prefix = surface_data(raw)
    native.require(not prefix, "Unsupported non-root data update")
    emit_fidelity.graph(graph)
    index = native.control_index(tree, rect)
    paths = set()
    leaves = []
    for leaf in graph["components"]:
        kind, key = leaf["component"], leaf["id"]
        if kind not in selected_bindings.TEXT_FIELDS:
            continue
        controls = index.get(key, [])
        state, dynamic = native.classify(leaf, controls, rect, data, samples)
        leaves.append({"id": key, "kind": kind, "dynamic": dynamic, "state": state})
        if (
            state == "match"
            and dynamic
            and native_repeated_facts.positive_opacity(controls[0])
        ):
            refs = selected_bindings._dependencies(
                leaf[selected_bindings.TEXT_FIELDS[kind]]
            )
            if refs and all(
                native_repeated_facts.identical_sample(data, p, samples[p])
                for p in refs
            ):
                paths.update(refs)
    native.require(leaves == audited_leaves, "Frozen control classification differs")
    return frozenset(paths)


def verified_paths(batch, observation, raw, frame_index):
    """Return positive dependencies only. No capture gives an empty set.

    A matching control has a unique ID, positive opacity and a visible box with
    positive-area card intersection. This attests its reported text only;
    complete glyph visibility and later data updates require separate evidence.
    """
    prov = observation["provenance"]
    cap = prov["capture"]
    if cap is None:
        return set()
    key = observation["checkpoint"]
    frame = frame_index.get(cap["proof_ref"])
    native.require(
        frame is not None and frame.phases.get(key) == prov,
        "Unregistered frame or phase",
    )
    r = frame.audit
    digest = observation["artifact_sha256"]
    native.require(
        (observation["task_id"], observation["arm"], digest)
        == (r["task"], r["arm"], r["sha256"])
        and raw is not None
        and hashlib.sha256(raw).hexdigest() == digest,
        "Source or task differs from control audit",
    )
    origin = batch / prov["artifact_ref"]
    native.checked(origin, digest)
    if frame.paths is None:
        proof = batch / cap["proof_ref"]
        receipt = json.loads(native.checked(proof, cap["proof_sha256"]))
        native.require(
            (
                receipt["task"],
                receipt["arm"],
                receipt["input_sha256"],
                receipt["input_return_sha256"],
            )
            == (r["task"], r["arm"], digest, digest)
            and receipt["status"] == "captured"
            and receipt["run_id"] == cap["capture_run_id"]
            and receipt["screenshot_sha256"] == cap["screenshot_sha256"]
            and receipt["terminal"]["state"] == cap["host_state"],
            "Capture receipt differs from frozen seat",
        )
        native.checked(batch / cap["screenshot_ref"], cap["screenshot_sha256"])
        native.checked(proof.parent / "received-input.jsonl", digest)
        registry = (
            batch / "queue/package/registry" / (origin.parent.parent.name + ".json")
        )
        entry = json.loads(native.checked(registry, prov["registry_sha256"]))
        native.require(entry["id"] == r["task"], "Wrong source registry")
        tree_sha = r["layout_sha256_at_audit"]
        tree = (
            json.loads(native.checked(proof.parent / "native-layout.json", tree_sha))
            if tree_sha
            else {}
        )
        c = receipt["terminal"]["cropPx"]
        rect = (c["left"], c["top"], c["left"] + c["width"], c["top"] + c["height"])
        frame.paths = _matched_paths(
            raw, tree, rect, entry["binding_samples"], r["leaves"]
        )
    return set(frame.paths)
