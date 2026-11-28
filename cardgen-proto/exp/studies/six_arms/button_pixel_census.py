"""Summarize two sealed readings of native button crops, without publishing case IDs.

Pass the seat JSONL, per-button JSONL, two blind vote JSONLs (blind_id, verdict)
followed by the technical checkpoint JSON array and execution-status JSONL.
Output is aggregate JSON.
"""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ARMS = tuple(f"L{n}" for n in range(1, 7))
CHECKPOINTS = ("raw_first", "after_common_repair")
VOTES = {"ellipsis", "no_ellipsis", "uncertain"}
ARTIFACT_AVAILABILITY = {
    (True, True): "both",
    (True, False): "left_only",
    (False, True): "right_only",
    (False, False): "neither",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def indexed(rows, fields):
    result = {}
    for row in rows:
        key = tuple(row[field] for field in fields)
        require(key not in result, "Duplicate key in supplied census")
        result[key] = row
    return result


def votes(rows):
    result = indexed(rows, ("blind_id",))
    require(all(r["verdict"] in VOTES for r in result.values()), "Invalid verdict")
    return {key[0]: row["verdict"] for key, row in result.items()}


def read_button(button, first, second):
    """Return the visible-caption verdict and its mutually exclusive evidence gap."""
    if button["state"] != "cropped":
        return "unknown", button["state"]
    label = button["source_label"]
    if not isinstance(label, str) or not label.strip():
        return "unknown", "source_label_unavailable"
    if button["source_label_ellipsis"]:
        return "unknown", "source_label_ellipsis"
    if label != button["native_text"]:
        return "unknown", "native_text_differs"
    alias = button["blind_id"]
    if first[alias] != second[alias]:
        return "unknown", "reader_disagreement"
    if first[alias] == "uncertain":
        return "unknown", "both_readers_uncertain"
    return ("ellipsis" if first[alias] == "ellipsis" else "clear"), None


def observed(button, first, second):
    return read_button(button, first, second)[0]


def classify_card(buttons, has_artifact):
    if not has_artifact:
        return "no_artifact"
    if not buttons:
        return "no_button"
    if "ellipsis" in buttons:
        return "ellipsis"
    return "unknown" if "unknown" in buttons else "clear"


def endpoint(tech, state):
    """Return attainable indicator bounds; None denotes missing technical evidence."""
    if tech is False or state == "ellipsis":
        return 0, 0
    if tech is None:
        return 0, 1
    require(state != "no_artifact", "Technical success without an artifact")
    return (0, 1) if state == "unknown" else (1, 1)


def summarize(seats, buttons, readings_a, readings_b, technical, executions):
    seat_fields = ("task", "arm", "checkpoint")
    source = indexed(seats, seat_fields)
    tech = indexed(technical, ("task_id", "arm", "checkpoint"))
    run = indexed(executions, ("task_id", "arm"))
    require(source.keys() == tech.keys(), "Technical rows do not cover the same seats")
    tasks = {task for task, _, _ in source}
    expected = {(task, arm, cp) for task in tasks for arm in ARMS for cp in CHECKPOINTS}
    require(source.keys() == expected and tasks, "Missing methods or checkpoints")
    require(
        run.keys() == {(task, arm) for task, arm, _ in source},
        "Missing execution status",
    )
    a, b = votes(readings_a), votes(readings_b)
    aliases = {r["blind_id"] for r in buttons if r["state"] == "cropped"}
    require(None not in aliases and "" not in aliases, "Missing blind ID")
    require(a.keys() == b.keys() == aliases, "Incomplete blinded readings")
    by_seat = defaultdict(list)
    captions = defaultdict(Counter)
    unknown = defaultdict(Counter)
    for key, button in indexed(buttons, (*seat_fields, "button_id")).items():
        seat = key[:3]
        require(seat in source, "Orphan button")
        require(
            source[seat]["artifact_sha256"] == button["artifact_sha256"],
            "Button belongs to a different artifact",
        )
        verdict, reason = read_button(button, a, b)
        by_seat[seat].append(verdict)
        if reason is not None:
            _, arm, cp = seat
            unknown[cp, arm][reason] += 1
            unknown[cp, "all"][reason] += 1
        captions[seat][json.dumps(button["source_label"], sort_keys=True)] += 1

    states, bounds = {}, {}
    groups = defaultdict(Counter)
    for key, row in source.items():
        _, arm, cp = key
        require(
            row["artifact_sha256"] == tech[key]["artifact_sha256"], "Artifact mismatch"
        )
        labels = by_seat[key]
        require(
            len(labels) == (row["source_button_count"] or 0), "Lost a source button"
        )
        require(not labels or row["artifact_sha256"], "Buttons without a source")
        state = classify_card(labels, bool(row["artifact_sha256"]))
        accepted = tech[key]["tech_pass"]
        require(isinstance(accepted, bool), "Unknown technical classification")
        missing = run[key[:2]]["status"] in {"callback_failed", "geometry_unknown"}
        require(not (accepted and missing), "Conflicting technical results")
        lo, hi = endpoint(None if missing else accepted, state)
        states[key], bounds[key] = state, (lo, hi)
        count = groups[cp, arm]
        count.update(
            {
                "seats": 1,
                "buttons": len(labels),
                f"card_{state}": 1,
                "technical_evidence_missing": int(missing),
                "lower": lo,
                "upper": hi,
            }
        )
        count.update(f"button_{label}" for label in labels)
        if accepted:
            count.update({"technical": 1, f"technical_{state}": 1})

    totals, pairs = {}, {}
    for cp in CHECKPOINTS:
        totals[cp] = {}
        for arm in ARMS:
            count = groups[cp, arm]
            for state in ("ellipsis", "clear", "unknown", "no_button", "no_artifact"):
                count.setdefault(f"card_{state}", 0)
                count.setdefault(f"technical_{state}", 0)
            for name in (
                "technical",
                "lower",
                "upper",
                "button_clear",
                "button_ellipsis",
                "button_unknown",
            ):
                count.setdefault(name, 0)
            totals[cp][arm] = dict(sorted(count.items()))
        pairs[cp] = {}
        for left, right in (("L4", "L5"), ("L5", "L6")):
            counts = Counter()
            # Retain zeros for cross-arm cells used in reported comparisons.
            for prefix in ("", "same_captions_", "both_technical_"):
                for l in ("clear", "ellipsis"):
                    for r in ("clear", "ellipsis"):
                        counts[f"{prefix}left_{l}_right_{r}"] = 0
            for name in (
                "both_emit_buttons",
                "both_emit_buttons_and_determinate",
                "determinate_same_captions_with_multiplicity",
                "both_technical_emit_buttons_and_determinate",
                "left_ellipsis_right_no_artifact",
                "left_no_artifact_right_ellipsis",
            ):
                counts[name] = 0
            coverage = Counter(dict.fromkeys(ARTIFACT_AVAILABILITY.values(), 0))
            for task in tasks:
                lk, rk = (task, left, cp), (task, right, cp)
                lmin, lmax = bounds[lk]
                rmin, rmax = bounds[rk]
                counts["left_minus_right_min"] += lmin - rmax
                counts["left_minus_right_max"] += lmax - rmin
                ls, rs = states[lk], states[rk]
                coverage[
                    ARTIFACT_AVAILABILITY[ls != "no_artifact", rs != "no_artifact"]
                ] += 1
                if ls == "ellipsis" and rs == "no_artifact":
                    counts["left_ellipsis_right_no_artifact"] += 1
                if rs == "ellipsis" and ls == "no_artifact":
                    counts["left_no_artifact_right_ellipsis"] += 1
                if ls in {"clear", "ellipsis", "unknown"} and rs in {
                    "clear",
                    "ellipsis",
                    "unknown",
                }:
                    counts["both_emit_buttons"] += 1
                if ls in {"clear", "ellipsis"} and rs in {"clear", "ellipsis"}:
                    counts["both_emit_buttons_and_determinate"] += 1
                    counts[f"left_{ls}_right_{rs}"] += 1
                    if captions[lk] == captions[rk]:
                        counts["determinate_same_captions_with_multiplicity"] += 1
                        counts[f"same_captions_left_{ls}_right_{rs}"] += 1
                    if tech[lk]["tech_pass"] and tech[rk]["tech_pass"]:
                        counts["both_technical_emit_buttons_and_determinate"] += 1
                        counts[f"both_technical_left_{ls}_right_{rs}"] += 1
                if lmin == lmax and rmin == rmax:
                    counts[f"endpoint_left_{lmin}_right_{rmin}"] += 1
            pairs[cp][f"{left}_{right}"] = {
                **dict(sorted(counts.items())),
                "artifact_availability": dict(coverage),
            }
    return {
        "requests": len(tasks),
        "distinct_button_crops_read": len(aliases),
        "distinct_crops_with_identical_votes": sum(a[i] == b[i] for i in aliases),
        "distinct_vote_pairs": dict(
            sorted(Counter(f"{a[i]}_{b[i]}" for i in aliases).items())
        ),
        "caption_evidence": "Two masked AI-assisted readings of original native button pixels. No additional human ratings.",
        "endpoint": "Observed technical acceptance and no confirmed renderer-added ellipsis on any emitted button. A button-free artifact satisfies the extra condition vacuously. Bounds retain missing pixel and technical evidence.",
        "by_checkpoint": totals,
        "button_unknown_by_reason": {
            cp: {arm: dict(sorted(unknown[cp, arm].items())) for arm in ("all", *ARMS)}
            for cp in CHECKPOINTS
        },
        "paired": pairs,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "seats",
        "buttons",
        "first_read",
        "second_read",
        "technical",
        "executions",
    ):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    inputs = {key: path.read_bytes() for key, path in vars(args).items()}
    rows = [
        [json.loads(line) for line in inputs[key].splitlines() if line.strip()]
        for key in ("seats", "buttons", "first_read", "second_read")
    ]
    executions = [
        json.loads(line) for line in inputs["executions"].splitlines() if line.strip()
    ]
    result = summarize(*rows, json.loads(inputs["technical"]), executions)
    result["source_sha256"] = {
        k: hashlib.sha256(v).hexdigest() for k, v in inputs.items()
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
