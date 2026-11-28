"""Search sealed native accessibility trees for font evidence. Outputs field counts, never values."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path, PureWindowsPath

from six_arms.composite_cost_stats import ARMS, PHASES

MANIFEST = "formal_button_pixel_census_20261128/inventory/admin/public_reproduction_manifest.private.jsonl"
MANIFEST_SHA256 = "6176cc600f9232e5b33ddc24efaa79de778748300e410bd1705e5cb932a77f88"
PHASE_LABELS = {"raw_first": "first_native", "after_common_repair": "final_native"}
CATEGORIES = (
    "font_size",
    "font_scale",
    "line_height_or_baseline",
    "density_or_zoom",
    "other_font_style",
)


def _category(name):
    k = "".join(c for c in name.lower() if c.isalnum())
    if "fontscale" in k or "fontscale" in k.replace("size", "") or "textscale" in k:
        return "font_scale"
    if "fontsize" in k or "textsize" in k or k in {"pointsize", "pixelsize"}:
        return "font_size"
    if "lineheight" in k or "baseline" in k:
        return "line_height_or_baseline"
    if (
        "density" in k
        or "zoom" in k
        or k in {"scale", "dpi", "devicepixelratio", "pixelspervp"}
    ):
        return "density_or_zoom"
    if "font" in k or "typograph" in k or "textstyle" in k:
        return "other_font_style"
    return None


def _field_counts(obj):
    counts = Counter()
    pending = [obj]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            for k, v in value.items():
                category = _category(k)
                if category:
                    counts[category] += 1
                if isinstance(v, (dict, list)):
                    pending.append(v)
        elif isinstance(value, list):
            pending.extend(value)
    return counts


def _checked(path, expected):
    if not path.is_file():
        raise ValueError("Sealed native evidence missing")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Sealed native evidence digest mismatch")
    return data


def _panel(counts):
    return {k: counts[k] for k in CATEGORIES}


def _receipt_path(root, registered):
    path = Path(registered)
    if path.is_absolute() and path.is_relative_to(root.resolve()):
        path = path.relative_to(root.resolve())
    elif path.is_absolute() or PureWindowsPath(registered).is_absolute():
        # Sealed manifests retain capture-machine paths. Rebase only the registered capture subtree.
        parts = PureWindowsPath(registered).parts
        starts = [
            i
            for i in range(len(parts) - 1)
            if parts[i : i + 2] == ("native_live", "captures")
        ]
        if len(starts) != 1:
            raise ValueError("No unique formal capture subtree")
        path = Path(*parts[starts[0] :])
    result = (root / path).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("Native receipt outside the frozen batch")
    return result


def _audit(rows, root, expected_tasks):
    unique = set()
    tasks = set()
    per = defaultdict(Counter)
    receipt_links, tree_digests = {}, set()
    tree_counts, receipted = Counter(), Counter()
    native_nodes, text_button_counts = Counter(), Counter()
    for row in rows:
        t, a, p = row["task"], row["arm"], row["checkpoint"]
        if (t, a, p) in unique or a not in ARMS or p not in PHASES:
            raise ValueError("Invalid native measurement seat")
        unique.add((t, a, p))
        tasks.add(t)
        counts = per[p, a]
        counts["assigned"] += 1
        if row.get("artifact_sha256"):
            counts["artifact"] += 1
        if not row.get("receipt"):
            continue
        path = _receipt_path(root, row["receipt"])
        counts["receipt"] += 1
        link = (
            t,
            a,
            row["artifact_sha256"],
            row["receipt_sha256"],
            row.get("tree_sha256"),
        )
        if path in receipt_links:
            previous, phases = receipt_links[path]
            if previous != link or PHASE_LABELS[p] not in phases:
                raise ValueError("Conflicting reuse of a physical capture")
            counts["tree"] += bool(link[-1])
            continue
        record = json.loads(_checked(path, link[3]))
        phases = record["phases"]
        if (
            PHASE_LABELS[p] not in phases
            or record.get("status") != "captured"
            or (record["task"], record["arm"], record["input_sha256"]) != link[:3]
            or record["input_return_sha256"] != link[2]
        ):
            raise ValueError("Native capture assignment or original source mismatch")
        receipt_links[path] = link, phases
        receipted.update(_field_counts(record))
        tree_sha = link[-1]
        if record.get("tree_sha256") and record["tree_sha256"] != tree_sha:
            raise ValueError("Conflicting sealed tree digest")
        if not tree_sha:
            continue
        tree = _checked(path.with_name("native-layout.json"), tree_sha)
        counts["tree"] += 1
        if tree_sha in tree_digests:
            continue
        tree_digests.add(tree_sha)
        pending = [json.loads(tree)]
        while pending:
            node = pending.pop()
            attrs = node["attributes"]
            found = _field_counts(attrs)
            tree_counts.update(found)
            if attrs.get("type") in ("Text", "Button"):
                native_nodes[attrs["type"]] += 1
                text_button_counts.update(found)
            pending.extend(node["children"])
    if (
        not tasks
        or len(tasks) != expected_tasks
        or unique != set(product(tasks, ARMS, PHASES))
    ):
        raise ValueError("Expected a complete native measurement assignment")
    tree_set = ("\n".join(sorted(tree_digests)) + "\n").encode("ascii")
    return {
        "assigned_tasks": len(tasks),
        "unique_capture_receipts": len(receipt_links),
        "unique_tree_contents": len(tree_digests),
        "tree_set_sha256_sorted_hex_with_lf": hashlib.sha256(tree_set).hexdigest(),
        "phases": {
            p: {
                a: {
                    k: per[p, a][k] for k in ("assigned", "artifact", "receipt", "tree")
                }
                for a in ARMS
            }
            for p in PHASES
        },
        "whole_window_nodes_in_unique_trees": {
            k: native_nodes[k] for k in ("Text", "Button")
        },
        "field_occurrences": {
            "all_native_node_attributes": _panel(tree_counts),
            "native_text_and_button_attributes": _panel(text_button_counts),
            "capture_receipt": _panel(receipted),
        },
        "scope": "Recorded field names only. Count all accessibility nodes in each unique captured window. A matching name alone cannot establish a resolved font size or its unit.",
    }


def audit(root):
    """Supply the formal batch directory on the custody machine. No device access."""
    root = Path(root)
    raw = _checked(root / MANIFEST, MANIFEST_SHA256)
    result = _audit([json.loads(line) for line in raw.splitlines()], root, 219)
    return {"manifest_sha256": MANIFEST_SHA256, **result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_root", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.formal_root), ensure_ascii=False, indent=2))
