"""A6 supplement: repeated registered numeric-bearing bindings in separate native controls."""

import argparse
import itertools
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from six_arms import emit_fidelity
from six_arms import native_text_audit as native
from six_arms.harness_v2 import program_stages as program

PUBLIC = (
    Path(__file__).resolve().parents[4] / "paper/out/tables/native_repeated_facts.json"
)
PINS = {
    "observations": "620c51e4c95436dfa15b0cf2bd429ece8cd873b88716d481a3f7f3afc047fad2",
    "control_text": "06161a0ac6b0571d55ca1fd47b6f31202d30af30122c0e5c031fe4fb1902280d",
    "capture_index": "e4c9dd93fa2a2712897775e48fe47951c2ecbccb48dd2292a28b9cd02e8f4170",
}
PHASES = ("raw_first", "after_common_repair")
ARMS = tuple(f"L{i}" for i in range(1, 7))
STATES = (
    "repeated",
    "complete_without_repeat",
    "incomplete_without_confirmed_repeat",
    "no_capture",
)


def checked_rows(path, sha):
    return [json.loads(line) for line in native.checked(path, sha).splitlines()]


def numeric_paths(value, samples):
    """Only direct JSON pointers and supported literal/path concatenations contribute."""
    tokens = emit_fidelity.tokens(value)
    if tokens is emit_fidelity.UNKNOWN or (
        isinstance(value, str) and "${" in value and not value.strip().startswith("{{")
    ):
        return None
    found = set()
    for kind, token in tokens:
        if kind == "path":
            if token not in samples:
                return None
            try:
                scalar = program._sample({"value": samples[token]}, "/value")
            except program.StageError:
                return None
            if re.search(r"\d", scalar):
                found.add(token)
    return found


def positive_opacity(attributes):
    try:
        opacity = float(attributes.get("opacity"))
    except (ValueError, TypeError):
        return False
    return math.isfinite(opacity) and 0 < opacity <= 1


def identical_sample(data, path, sample):
    """native.classify already validated the pointer and its rendered value."""
    value = data
    for part in path[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return type(value) is type(sample) and value == sample


def inside(r, c):
    return c[0] <= r[0] < r[2] <= c[2] and c[1] <= r[1] < r[3] <= c[3]


def overlaps(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def inspect(components, index, crop, data, samples):
    """Return control evidence. Static text or two paths with the same rendered sample do not make a repeat."""
    seen = set()
    evidence = {}
    boxes = {}
    for node in components:
        kind, key = node["component"], node["id"]
        native.require(key not in seen, "Duplicate component ID")
        seen.add(key)
        if kind not in ("Text", "Button"):
            native.require(kind in ("Column", "Row"), "Unsupported component")
            continue
        attr = "label" if kind == "Button" else "content"
        paths = numeric_paths(node[attr], samples)
        controls = index.get(key, [])
        state, _ = native.classify(node, controls, crop, data, samples)
        status = state
        if len(controls) == 1 and controls[0].get("type") == kind:
            a = controls[0]
            b = native.box(a.get("bounds"))
            if b and a.get("visible") == "true" and b[0] < b[2] and b[1] < b[3]:
                boxes[key] = b
            if status == "match":
                if not positive_opacity(a):
                    status = "unverified_opacity"
                elif key not in boxes or not inside(boxes[key], crop):
                    status = "partially_outside"
        if status == "match" and paths is None:
            status = "unresolved_numeric_attribution"
        elif status == "match" and any(
            not identical_sample(data, p, samples[p]) for p in paths
        ):
            status = "registered_value_type_differs"
        evidence[key] = {
            "kind": kind,
            "paths": sorted(paths or ()),
            "native_state": state,
            "status": status,
        }
    for left, right in itertools.combinations(boxes, 2):
        if overlaps(boxes[left], boxes[right]):
            for key in (left, right):
                if evidence[key]["status"] == "match":
                    evidence[key]["status"] = "overlapping_controls"
    candidates, verified = defaultdict(list), defaultdict(list)
    for key, e in evidence.items():
        for path in e["paths"]:
            candidates[path].append(key)
            if e["status"] == "match":
                verified[path].append(key)
    positive = {p: ids for p, ids in verified.items() if len(ids) >= 2}
    complete = bool(evidence) and all(v["status"] == "match" for v in evidence.values())
    state = (
        "repeated"
        if positive
        else "complete_without_repeat"
        if complete
        else "incomplete_without_confirmed_repeat"
    )
    return {
        "state": state,
        "complete": complete,
        "matched_numeric_paths": len(verified),
        "matched_numeric_controls": len(set().union(*verified.values())),
        "structural_repeat_paths": {
            p: ids for p, ids in candidates.items() if len(ids) >= 2
        },
        "confirmed_repeat_paths": positive,
        "leaf_evidence": evidence,
    }


def check_capture(batch, obs, existing):
    prov = obs["provenance"]
    cap = prov["capture"]
    proof = batch / cap["proof_ref"]
    receipt = json.loads(native.checked(proof, cap["proof_sha256"]))
    task, arm, artifact = obs["task_id"], obs["arm"], obs["artifact_sha256"]
    native.require(
        (
            receipt["task"],
            receipt["arm"],
            receipt["input_sha256"],
            receipt["input_return_sha256"],
        )
        == (task, arm, artifact, artifact)
        and cap["artifact_sha256"] == artifact,
        "Wrong capture source",
    )
    native.require(
        receipt["status"] == "captured"
        and cap["host_state"] == receipt["terminal"]["state"]
        and receipt["run_id"] == cap["capture_run_id"]
        and receipt["screenshot_sha256"] == cap["screenshot_sha256"],
        "Incomplete capture proof",
    )
    native.checked(batch / cap["screenshot_ref"], cap["screenshot_sha256"])
    raw = native.checked(proof.parent / "received-input.jsonl", artifact)
    origin = batch / prov["artifact_ref"]
    native.checked(origin, artifact)
    entry = json.loads(
        native.checked(
            batch / "queue/package/registry" / (origin.parent.parent.name + ".json"),
            prov["registry_sha256"],
        )
    )
    native.require(
        entry["id"] == task
        and (existing["task"], existing["arm"], existing["sha256"])
        == (task, arm, artifact),
        "Wrong case",
    )
    tree = (
        json.loads(
            native.checked(
                proof.parent / "native-layout.json", existing["layout_sha256_at_audit"]
            )
        )
        if existing["layout_sha256_at_audit"]
        else {}
    )
    c = receipt["terminal"]["cropPx"]
    crop = (c["left"], c["top"], c["left"] + c["width"], c["top"] + c["height"])
    index = native.control_index(tree, crop) if tree else {}
    messages = [json.loads(line) for line in raw.splitlines()]
    graph = messages[1]["updateComponents"]
    emit_fidelity.graph(graph)
    data = messages[2]["updateDataModel"]
    native.require(data["path"] == "/", "Unsupported non-root data update")
    result = inspect(
        graph["components"], index, crop, data["value"], entry["binding_samples"]
    )
    old_states = {r["id"]: r["state"] for r in existing["leaves"]}
    native.require(
        old_states
        == {k: v["native_state"] for k, v in result["leaf_evidence"].items()},
        "Historical native controls differ",
    )
    return {
        **result,
        "artifact_sha256": artifact,
        "proof": cap["proof_ref"],
        "screenshot_sha256": cap["screenshot_sha256"],
        "registry_sha256": prov["registry_sha256"],
        "layout_sha256": existing["layout_sha256_at_audit"],
    }


def load_records(batch):
    observations = checked_rows(
        batch / "pre_score_evidence/endpoint/observations.private.jsonl",
        PINS["observations"],
    )
    audited = checked_rows(
        batch
        / "pre_score_evidence/native_control_text_20261128/control_text.private.jsonl",
        PINS["control_text"],
    )
    audits = {r["proof"]: r for r in audited}
    catalog = json.loads(
        native.checked(
            batch / "native_live/capture_index.private.json", PINS["capture_index"]
        )
    )
    catalog_proofs = {Path(c["proof"]).resolve() for c in catalog["captures"]}
    native.require(
        len(catalog_proofs) == len(audits) == len(audited) == 1159
        and catalog["state"] == "complete",
        "Wrong native catalog",
    )
    native.require(
        {(batch / p).resolve() for p in audits} == catalog_proofs,
        "Audit and catalog disagree",
    )
    cache, records = {}, []
    for obs in observations:
        task, arm, phase = (obs[k] for k in ("task_id", "arm", "checkpoint"))
        cap = obs["provenance"]["capture"]
        base = {
            "task": task,
            "arm": arm,
            "phase": phase,
            "execution": obs["execution"]["status"],
        }
        if not cap:
            records.append({**base, "state": "no_capture", "complete": False})
            continue
        proof = cap["proof_ref"]
        old = audits[proof]
        native.require(
            phase in old["phases"]
            and (task, arm, obs["artifact_sha256"])
            == (old["task"], old["arm"], old["sha256"]),
            "Stage/capture mismatch",
        )
        if proof not in cache:
            cache[proof] = check_capture(batch, obs, old)
        record = cache[proof]
        native.require(
            record["artifact_sha256"] == obs["artifact_sha256"]
            and record["screenshot_sha256"] == cap["screenshot_sha256"],
            "Invalid reused frame",
        )
        records.append({**base, **record})
    native.require(set(cache) == set(audits), "Unmatched captured frames")
    return records


def describe(rows):
    states = Counter(r["state"] for r in rows)
    return {
        "assigned": len(rows),
        "captured": len(rows) - states["no_capture"],
        "native_control_states": {k: states[k] for k in STATES},
        "complete_all_visible_controls": sum(r["complete"] for r in rows),
        "complete_with_numeric_binding": sum(
            r["complete"] and bool(r["matched_numeric_paths"]) for r in rows
        ),
        "complete_with_two_or_more_numeric_controls": sum(
            r["complete"] and r["matched_numeric_controls"] >= 2 for r in rows
        ),
        "complete_cards_with_confirmed_repeat": sum(
            r["complete"] and r["state"] == "repeated" for r in rows
        ),
        "confirmed_distinct_path_card_occurrences": sum(
            len(r.get("confirmed_repeat_paths", {})) for r in rows
        ),
        "captured_cards_with_potential_repeated_source_binding": sum(
            bool(r.get("structural_repeat_paths")) for r in rows
        ),
        "no_capture_reasons": dict(
            sorted(
                Counter(
                    r["execution"] for r in rows if r["state"] == "no_capture"
                ).items()
            )
        ),
    }


def paired(left, right):
    native.require(set(left) == set(right), "Unpaired assigned cases")
    joint = [(l, right[t]) for t, l in left.items()]
    complete = [(l, r) for l, r in joint if l["complete"] and r["complete"]]

    def four(rows):
        votes = Counter(
            (l["state"] == "repeated", r["state"] == "repeated") for l, r in rows
        )
        return {
            "paired": len(rows),
            "both": votes[True, True],
            "L4_only": votes[True, False],
            "L5_only": votes[False, True],
            "neither": votes[False, False],
        }

    return {
        "assigned": len(joint),
        "both_captured": sum(
            l["state"] != "no_capture" and r["state"] != "no_capture" for l, r in joint
        ),
        "joint_state_counts": [
            {"L4": l, "L5": r, "cases": n}
            for (l, r), n in sorted(
                Counter((l["state"], r["state"]) for l, r in joint).items()
            )
        ],
        "complete_both": four(complete),
        "complete_with_two_or_more_numeric_controls_both": four(
            [
                (l, r)
                for l, r in complete
                if min(l["matched_numeric_controls"], r["matched_numeric_controls"])
                >= 2
            ]
        ),
        "complete_with_numeric_binding_both": four(
            [
                (l, r)
                for l, r in complete
                if l["matched_numeric_paths"] and r["matched_numeric_paths"]
            ]
        ),
    }


def summarize(rows):
    index = {(r["task"], r["arm"], r["phase"]): r for r in rows}
    tasks = {r["task"] for r in rows}
    native.require(
        len(tasks) == 219
        and len(index) == len(rows) == 2628
        and set(index) == set(itertools.product(tasks, ARMS, PHASES)),
        "Incorrect formal grid",
    )
    phase_report = {}
    for phase in PHASES:
        groups = {a: {t: index[t, a, phase] for t in tasks} for a in ARMS}
        phase_report[phase] = {
            "by_arm": {
                a: describe(list(group.values())) for a, group in groups.items()
            },
            "all": describe([r for r in rows if r["phase"] == phase]),
            "L4_L5_same_task": paired(groups["L4"], groups["L5"]),
        }
    return {
        "scope": "Post-hoc RQ1/A6 lower-bound study. Count the same registered scalar binding with at least one decimal digit in two different native Text or Button IDs. Domains, dates and names containing a decimal digit remain eligible; the matched path establishes fact identity. Distinct paths with equal values, repetitions within one node, unbound literals and action parameters are outside the metric. Exact host control text is checked against decoded bindings and literals, the card bytes and registered sample. Positive controls must report visible, nonzero opacity, in-card and disjoint leaf boxes. Full painted glyphs and semantic redundancy are not inferred; repeated context may be intentional.",
        "original_A6_boundary": "The paper's A6 counts repeated numerical values on the rendered card even when the source is literal. This audit requires identical typed samples on a single registry path at separate controls. A captured card with incomplete controls and no proven repeat remains unknown. A card without a capture has no native observation. Matched numeric controls include distinct Text/Button IDs even if the underlying fact differs. Sources outside the candidate grammar and values encoded only in action parameters are unassessed.",
        "stages": phase_report,
        "frozen_source_sha256": PINS,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-batch", type=Path, required=True)
    parser.add_argument("--private-output", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rows = load_records(args.formal_batch)
    report = summarize(rows)
    if args.private_output:
        with args.private_output.open("x", encoding="utf-8", newline="\n") as f:
            for row in rows:
                f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    if args.check:
        native.require(
            report == json.loads(PUBLIC.read_bytes()), "A6 aggregate differs"
        )
        print("Native repeated-fact table matched.")
    else:
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )


if __name__ == "__main__":
    main()
