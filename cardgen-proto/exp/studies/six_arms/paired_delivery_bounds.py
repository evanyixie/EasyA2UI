"""Compare frozen delivery bounds with a sensitivity assumption for identical cards."""

import argparse
import hashlib
import itertools
import json
import runpy
from collections import Counter
from pathlib import Path

# Custodian receipts for the original experiment, with and without a separate clock probe.
GRIDS = {
    "original": (
        "observations.native.private.jsonl",
        "28e95fa792d7b1f4612b2f69930adce719449ea306d7f690d552b5b0fd535600",
    ),
    "clock": (
        "observations.clock_sensitivity.private.jsonl",
        "71c05c198d330218151ef857abb1c7587dfe4d191a2d072f71c44722896b5414",
    ),
}
ROSTER = "ffcecb4ce1cf0f0fb0ea9e3a43140c1b119420f619d335ad621bd2063e9a39c2"
EVALUATOR = "f113cd7b10b14a3dabeaaa18f9e8e092a32f6cec875b57a2d909caeff8c86058"
CLOCK_INTENTS = "2ad8a88d7db78306377d18caa92e11a0ca46299b55a343021ec42be3dd1f7146"
POINTS = ("raw_first", "after_common_repair")


def verified(path, digest):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"Evidence hash mismatch for {path.name}")
    return data


def interval(left, right, tied=False):
    possible = {"pass": (1,), "fail": (0,), "unknown": (0, 1)}
    values = [
        a - b
        for a, b in itertools.product(possible[left], possible[right])
        if not tied or a == b
    ]
    if not values:
        raise ValueError("Equal-outcome assumption contradicts observed statuses")
    return min(values), max(values)


def identical_card(batch, left, right):
    """Require the same input, bytes and native evidence on both sides; exclude handlers."""
    a, b = left["provenance"], right["provenance"]
    if left["task_id"] != right["task_id"] or left["checkpoint"] != right["checkpoint"]:
        raise ValueError("Comparison across tasks or checkpoints")
    if left["input_sha256"] != right["input_sha256"] or any(
        a[key] != b[key]
        for key in ("raw_request_sha256", "packaged_request_sha256", "registry_sha256")
    ):
        raise ValueError("Comparison across inputs")
    if not a["capture"] or not b["capture"] or not left["artifact_sha256"]:
        return False
    if (
        left["execution"]["status"] != "native_captured"
        or right["execution"]["status"] != "native_captured"
    ):
        return False
    if left["artifact_sha256"] != right["artifact_sha256"]:
        return False
    if a["capture"]["screenshot_sha256"] != b["capture"]["screenshot_sha256"]:
        return False
    known = [
        {k: v["status"] for k, v in row["primary_evidence"].items()}
        for row in (left, right)
    ]
    required = {
        "protocol",
        "first_response_lineage",
        "trusted_native_frame",
        "lossless_caller_canvas",
    }
    if left["checkpoint"] == "after_common_repair":
        required.add("common_repair_lineage")
    if known[0] != known[1] or any(known[0].get(key) != "pass" for key in required):
        return False
    for row in (left, right):
        cap = row["provenance"]["capture"]
        verified(batch / cap["screenshot_ref"], cap["screenshot_sha256"])
        data = verified(
            batch / row["provenance"]["artifact_ref"], row["artifact_sha256"]
        )
        if any(
            node.get("onClick")
            for line in data.splitlines()
            for node in json.loads(line)
            .get("updateComponents", {})
            .get("components", [])
        ):
            return False
    return True


def replay(batch, evaluator):
    verified(evaluator, EVALUATOR)
    assess = runpy.run_path(str(evaluator))["assess"]
    roster = [
        json.loads(line)
        for line in verified(batch / "analysis/roster.jsonl", ROSTER).splitlines()
    ]
    seats = set(
        itertools.product(
            (r["task_id"] for r in roster), (f"L{i}" for i in range(1, 7)), POINTS
        )
    )
    intent = json.loads(
        verified(
            batch / "objective_quality_20261128/clock_query_link.private.json",
            CLOCK_INTENTS,
        )
    )
    explicit = {
        (r["task"], r["arm"], r["phase"]): r
        for r in intent
        if r["scope"] == "explicit_open"
    }
    grids, statuses = {}, {}
    for label, (name, sha) in GRIDS.items():
        lines = verified(batch / "followup_evidence_20261128" / name, sha).splitlines()
        rows = [json.loads(line) for line in lines]
        grid = {(r["task_id"], r["arm"], r["checkpoint"]): r for r in rows}
        if len(rows) != len(seats) or grid.keys() != seats:
            raise ValueError("Incomplete or duplicated experimental seats")
        grids[label] = grid
        statuses[label] = {
            k: assess(row)["primary"]["status"] for k, row in grid.items()
        }
    statuses["explicit_clock"] = dict(statuses["original"])
    for k, scope in explicit.items():
        row = grids["clock"][k]
        if (
            scope["artifact"] != row["artifact_sha256"]
            or scope["request_sha256"] != row["provenance"]["packaged_request_sha256"]
            or row["primary_evidence"]["actual_action_destinations"]["status"] != "fail"
        ):
            raise ValueError("Probe does not match the input and artifact")
        statuses["explicit_clock"][k] = statuses["clock"][k]

    report = {}
    for point, other in itertools.product(POINTS, ("L4", "L6")):
        pairs = []
        for r in roster:
            a, b = ((r["task_id"], arm, point) for arm in ("L5", other))
            left, right = (grids["original"][k] for k in (a, b))
            equal = identical_card(batch, left, right)
            captures = [row["provenance"]["capture"] for row in (left, right)]
            both = all(captures)
            same_png = (
                both
                and captures[0]["screenshot_sha256"] == captures[1]["screenshot_sha256"]
            )
            pairs.append(
                (a, b, equal, r["included_in_217_sensitivity"], both, same_png)
            )
        for scope, subset in (("219", pairs), ("217", [p for p in pairs if p[3]])):
            for label, states in statuses.items():
                cases = [(states[a], states[b], eq) for a, b, eq, *_ in subset]
                observed = [interval(a, b) for a, b, _ in cases]
                tied = [interval(a, b, eq) for a, b, eq in cases]
                report[f"{scope}/{point}/L5-{other}/{label}"] = {
                    "n": len(cases),
                    "matching_cards": sum(eq for _, _, eq in cases),
                    "both_captured": sum(p[4] for p in subset),
                    "matching_screenshot_digest": sum(p[5] for p in subset),
                    "observed_pairs": dict(Counter(f"{a}/{b}" for a, b, _ in cases)),
                    "unresolved_differences": sum(lo != hi for lo, hi in observed),
                    "unresolved_differences_if_equal_cards_tie": sum(
                        lo != hi for lo, hi in tied
                    ),
                    "unrestricted_net_bounds": [sum(c) for c in zip(*observed)],
                    "equal_card_net_bounds": [sum(c) for c in zip(*tied)],
                }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_batch", type=Path)
    parser.add_argument("frozen_evaluator", type=Path)
    args = parser.parse_args()
    print(json.dumps(replay(args.formal_batch, args.frozen_evaluator), indent=2))
