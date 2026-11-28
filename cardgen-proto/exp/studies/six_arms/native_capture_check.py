"""Offline, role-independent checks for paired first-frame captures.

One JSONL manifest row per task and arm. Required keys: task, arm, source,
registry, content and their companion *_sha256 fields. A captured seat adds
receipt, receipt_sha256 and (for older receipts) tree_sha256. Relative paths
are resolved against the manifest. The caller supplies frozen content before
looking at either arm. Results contain control evidence, not a visual rating.
"""

import argparse
import hashlib
import json
from collections import Counter
from itertools import combinations
from pathlib import Path

from . import emit_fidelity as fidelity
from . import native_text_audit as native
from .harness_v2 import program_stages as program


def signature(parts):
    return None if parts is fidelity.UNKNOWN else tuple(parts)


def targets(content, components):
    """Exact per-leaf contract with multiplicity; regrouped text stays unresolved."""
    expected, actions = program._index(content)
    texts = Counter()
    buttons = Counter()
    paths = Counter()
    undecoded = False
    for component in components:
        if component["component"] == "Text":
            parts = signature(fidelity.tokens(component["content"]))
            if parts is None:
                undecoded = True
                continue
            texts[parts] += 1
            paths.update(value for kind, value in parts if kind == "path")
        elif component["component"] == "Button":
            buttons[
                fidelity.json_key([component.get("label"), component.get("onClick")])
            ] += 1
    expected_texts = Counter()
    expected_buttons = Counter()
    expected_paths = Counter()
    unknown_handler = False
    for ref, item in expected.items():
        if ref in actions:
            handler = item.get("handler")
            if handler is None:
                unknown_handler = True
            else:
                expected_buttons[fidelity.json_key([item["label"], [handler]])] += 1
        else:
            expected_texts[signature(fidelity.expected_text(item))] += 1
            if "path" in item:
                expected_paths[item["path"]] += 1
    if expected_buttons - buttons or (not undecoded and expected_paths - paths):
        return "missing_selected_binding_or_button"
    if (
        unknown_handler
        or undecoded
        or texts != expected_texts
        or buttons != expected_buttons
    ):
        return "unresolved_leaf_contract"
    return "match"


def intersection(a, b):
    return max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])


def area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def inspect_tree(tree, crop, components, data, samples):
    index = native.control_index(tree, crop)
    findings, visible = [], {}
    for leaf in components:
        kind = leaf["component"]
        if kind not in ("Text", "Button"):
            native.require(kind in ("Row", "Column"), f"Unsupported control {kind}")
            continue
        key = leaf["id"]
        controls = index.get(key, [])
        state, _ = native.classify(leaf, controls, crop, data, samples)
        geometry = "unknown"
        if len(controls) == 1 and controls[0].get("type") == kind:
            control = controls[0]
            current = native.box(control.get("bounds"))
            original = native.box(control.get("origBounds"))
            if control.get("visible") == "true" and current:
                clipped = intersection(current, crop)
                if area(clipped):
                    visible[key] = clipped
                if original and area(original):
                    if intersection(original, crop) != original:
                        geometry = "outside"
                    elif area(clipped):
                        geometry = "inside"
        findings.append({"id": key, "kind": kind, "text": state, "geometry": geometry})
    overlaps = [
        [a, b]
        for a, b in combinations(visible, 2)
        if area(intersection(visible[a], visible[b])) > 0
    ]
    return findings, overlaps


def audit(row, base):
    def path(key):
        return base / row[key]

    def frozen(key):
        return native.checked(path(key), row[key + "_sha256"])

    result = {
        k: row[k]
        for k in ("task", "arm", "source_sha256", "registry_sha256", "content_sha256")
    }
    result.update(state="incomplete", leaves=[], overlaps=[])
    for key in ("source", "registry", "content"):
        if not row.get(key) or not path(key).is_file():
            return {**result, "reason": "missing_" + key}
    raw = frozen("source")
    registry = json.loads(frozen("registry"))
    content = json.loads(frozen("content"))
    native.require(registry["id"] == row["task"], "Wrong task registry")
    messages = [json.loads(line) for line in raw.splitlines() if line.strip()]
    native.require(
        len(messages) == 3, "Expected a single create, component and data update"
    )
    surface = messages[0]["createSurface"]["surfaceId"]
    updates = messages[1]["updateComponents"]
    native.require(
        surface == updates["surfaceId"] == messages[2]["updateDataModel"]["surfaceId"],
        "Mixed surfaces",
    )
    fidelity.graph(updates)
    components = updates["components"]
    data = messages[2]["updateDataModel"]["value"]
    result["target_state"] = targets(content, components)
    if not row.get("receipt") or not path("receipt").is_file():
        return {**result, "reason": "missing_receipt"}

    receipt = json.loads(frozen("receipt"))
    result["receipt_sha256"] = row["receipt_sha256"]
    if receipt.get("status") != "captured":
        return {**result, "reason": "no_completed_capture"}
    if not receipt.get("task") or not receipt.get("arm"):
        return {**result, "reason": "missing_capture_assignment"}
    native.require(
        (receipt["task"], receipt["arm"]) == (row["task"], row["arm"]),
        "Wrong capture assignment",
    )
    if "content_sha256" in receipt:
        native.require(
            receipt["content_sha256"] == row["content_sha256"],
            "Different frozen content",
        )
    native.require(
        receipt["input_sha256"]
        == receipt["input_return_sha256"]
        == row["source_sha256"],
        "Different capture source",
    )
    terminal = receipt["terminal"]
    native.require(terminal["runId"] == receipt["run_id"], "Different terminal run")
    canvas = program._canvas(content["size"])
    native.require(
        tuple(receipt["vp"]) == (terminal["widthVp"], terminal["heightVp"]) == canvas,
        "Different caller canvas",
    )
    directory = path("receipt").parent
    for name, digest in (
        ("card.png", receipt["screenshot_sha256"]),
        ("received-input.jsonl", receipt["input_return_sha256"]),
    ):
        file = directory / name
        if not file.is_file():
            return {**result, "reason": "missing_" + name}
        native.checked(file, digest)
    layout = directory / "native-layout.json"
    tree_hash = receipt.get("tree_sha256") or row.get("tree_sha256")
    if row.get("tree_sha256") and receipt.get("tree_sha256"):
        native.require(
            row["tree_sha256"] == receipt["tree_sha256"], "Conflicting tree hashes"
        )
    if not tree_hash or not layout.is_file():
        return {**result, "reason": "missing_sealed_tree"}
    tree = json.loads(native.checked(layout, tree_hash))
    roi = terminal["cropPx"]
    crop = (
        roi["left"],
        roi["top"],
        roi["left"] + roi["width"],
        roi["top"] + roi["height"],
    )
    native.require(area(crop) > 0, "Invalid capture rectangle")
    findings, overlaps = inspect_tree(
        tree, crop, components, data, registry["binding_samples"]
    )
    result.update(
        leaves=findings,
        overlaps=overlaps,
        tree_sha256=tree_hash,
        screenshot_sha256=receipt["screenshot_sha256"],
    )
    if (
        overlaps
        or result["target_state"] == "missing_selected_binding_or_button"
        or any(
            f["geometry"] == "outside"
            or f["text"] in ("native_text_differs", "emitted_sample_differs")
            for f in findings
        )
    ):
        result["state"] = "observed_difference"
    elif (
        result["target_state"] == "match"
        and findings
        and all(f["geometry"] == "inside" and f["text"] == "match" for f in findings)
    ):
        result["state"] = "matched_control_evidence"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("new_output", type=Path)
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    results, seen, shared = [], set(), {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        task, arm = row["task"], row["arm"]
        pair_input = row["content_sha256"], row["registry_sha256"]
        native.require((task, arm) not in seen, "Duplicate seat")
        native.require(
            shared.setdefault(task, pair_input) == pair_input, "Different paired input"
        )
        seen.add((task, arm))
        results.append(audit(row, args.manifest.parent))
    out = {"manifest_sha256": hashlib.sha256(raw).hexdigest(), "results": results}
    with args.new_output.open("x", encoding="utf-8") as stream:
        json.dump(out, stream, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
