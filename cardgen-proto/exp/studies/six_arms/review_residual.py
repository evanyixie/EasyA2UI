"""Count remaining work for the two formal comparisons using sealed primary evidence.

Print anonymous counts. --private-ledger creates a custodian-only task index in
a new file. The index links existing observations; it is not a reviewer packet.
"""

import argparse
import json
from collections import Counter
from functools import cache
from pathlib import Path

if __package__:
    from . import paired_delivery_bounds as bounds
else:
    import paired_delivery_bounds as bounds

POINTS = bounds.POINTS

ARMS = ("L4", "L5", "L6")
COMPARISONS = (("L5", "L4"), ("L5", "L6"), ARMS)


def earliest_decisive_count(intervals, sign):
    """Optimistic minimum completely resolved tasks for a strict finite-cohort lead."""
    if sign not in (-1, 1):
        raise ValueError("Expected one of the two directions")
    bounds = [(lo, hi) if sign == 1 else (-hi, -lo) for lo, hi in intervals]
    lower = sum(lo for lo, _ in bounds)
    if lower > 0:
        return 0
    for n, gain in enumerate(sorted((hi - lo for lo, hi in bounds), reverse=True), 1):
        lower += gain
        if lower > 0:
            return n
    return None


def portfolio(rows, arms):
    totals = {}
    absolute_units, shared_absolute_units, pages, contextual_units = (
        set(),
        set(),
        set(),
        set(),
    )
    for cp in POINTS:
        counts = Counter()
        unknown_per_task = Counter()
        pair_intervals = []
        for task in rows:
            cards = [task["arms"][arm][cp] for arm in arms]
            # Both counts require identical task, input, original A2UI and screenshot.
            # Cross-arm reuse is optional and applies only to absolute visual items.
            images = tuple(
                (c["artifact"], c["image"]) if c["image"] else None for c in cards
            )
            page = (task["task"], task["input"], images)
            if any(images):
                pages.add(page)
                counts["tasks_with_images"] += 1
            for arm, card, image in zip(arms, cards, images):
                counts["seats"] += 1
                counts["status_" + card["primary"]] += 1
                if image:
                    unit = (task["task"], task["input"], arm, image)
                    absolute_units.add(unit)
                    shared_absolute_units.add((task["task"], task["input"], image))
                    contextual_units.add((unit, page))
                    counts["pictured"] += 1
                elif card["primary"] == "unknown":
                    counts["unknown_without_image"] += 1
            unknown_per_task[sum(c["primary"] == "unknown" for c in cards)] += 1
            if len(arms) == 2:
                pair_intervals.append(bounds.interval(*(c["primary"] for c in cards)))
        totals[cp] = {
            "seats": dict(sorted(counts.items())),
            "tasks_by_unknown_sides": dict(sorted(unknown_per_task.items())),
        }
        if pair_intervals:
            totals[cp]["net_bounds"] = [sum(v) for v in zip(*pair_intervals)]
            totals[cp]["best_case_fully_resolved_tasks_for_strict_left_lead"] = (
                earliest_decisive_count(pair_intervals, 1)
            )
            totals[cp]["best_case_fully_resolved_tasks_for_strict_right_lead"] = (
                earliest_decisive_count(pair_intervals, -1)
            )
    return {
        "checkpoints": totals,
        "distinct_absolute_visual_units_per_reader_within_arm": len(absolute_units),
        "distinct_absolute_visual_units_if_cross_arm_reuse_signed": len(
            shared_absolute_units
        ),
        "distinct_visual_units_if_whole_context_must_match": len(contextual_units),
        "distinct_nonempty_task_pages_if_whole_context_must_match": len(pages),
    }


def collect(batch, evaluator=None):
    assess = bounds.frozen_assess(evaluator)
    name, obs_hash = bounds.GRIDS["original"]
    observations = bounds.verified(
        batch / "followup_evidence_20261128" / name, obs_hash
    )
    roster = [
        json.loads(s)
        for s in bounds.verified(
            batch / "analysis/roster.jsonl", bounds.ROSTER
        ).splitlines()
    ]
    tasks = {r["task_id"]: r["raw_request_sha256"] for r in roster}
    if len(tasks) != len(roster):
        raise ValueError("Duplicate request in formal roster")
    ledger = {}

    @cache
    def check_file(path, sha):
        # Cache the successful check, not private artifact or screenshot bytes.
        bounds.verified(batch / path, sha)

    all_seats = set()
    for line in observations.splitlines():
        row = json.loads(line)
        task, arm, cp = row["task_id"], row["arm"], row["checkpoint"]
        key = (task, arm, cp)
        p = row["provenance"]
        if key in all_seats or tasks.get(task) != p["raw_request_sha256"]:
            raise ValueError("Duplicate seat or request mismatch")
        all_seats.add(key)
        if arm not in ARMS:
            continue
        item = ledger.setdefault(
            task,
            {
                "task": task,
                "input": row["input_sha256"],
                "packaged_request": p["packaged_request_sha256"],
                "arms": {},
            },
        )
        if (
            item["input"] != row["input_sha256"]
            or item["packaged_request"] != p["packaged_request_sha256"]
        ):
            raise ValueError("Input mismatch within a formal task")
        primary = assess(row)["primary"]
        cap = p["capture"]
        sha = row["artifact_sha256"]
        if sha:
            check_file(p["artifact_ref"], sha)
        if cap:
            receipt = json.loads(
                bounds.verified(batch / cap["proof_ref"], cap["proof_sha256"])
            )
            if (
                cap["artifact_sha256"] != sha
                or receipt["input_return_sha256"] != sha
                or receipt["screenshot_sha256"] != cap["screenshot_sha256"]
                or (receipt["task"], receipt["arm"]) != (task, arm)
            ):
                raise ValueError("Native receipt does not identify this card")
            check_file(cap["screenshot_ref"], cap["screenshot_sha256"])
        item["arms"].setdefault(arm, {})[cp] = {
            "execution": row["execution"]["status"],
            "primary": primary["status"],
            "known_failures": primary["failed"],
            "outstanding_if_undecided": primary["unknown"]
            if primary["status"] == "unknown"
            else [],
            "artifact": sha,
            "image": cap["screenshot_sha256"] if cap else None,
            "native_receipt": cap["proof_ref"] if cap else None,
            "source_receipt": row["execution"]["evidence_ref"],
        }
    expected = {(t, f"L{i}", c) for t in tasks for i in range(1, 7) for c in POINTS}
    if all_seats != expected:
        raise ValueError("Incomplete formal observation grid")
    return [ledger[r["task_id"]] for r in roster]


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("batch", type=Path)
    cli.add_argument("evaluator", type=Path, nargs="?")
    cli.add_argument("--private-ledger", type=Path)
    args = cli.parse_args()
    records = collect(args.batch, args.evaluator)
    if args.private_ledger:
        with args.private_ledger.open("x", encoding="utf-8", newline="\n") as f:
            for row in records:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {"/".join(a): portfolio(records, a) for a in COMPARISONS},
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
