"""Replay the released selector with three candidate-order keys on identical inputs."""

import argparse
import json
import multiprocessing
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations
from pathlib import Path

if __package__:
    from . import augmented_content_draws as replay
else:
    import augmented_content_draws as replay


TABLE = replay.TABLE.with_name("layout_order_sensitivity.json")
KEYS = ("original", "constant", "content_sha256")
CONSTANT = "fixed-layout-key-v1"
DECISIONS = ("pass", "no_policy_hit", "unknown")


def observe(draws, sealed, select):
    """Check every incoming draw against its receipt, once per unique input for scoring."""
    rows = {}
    n_draws = 0
    for draw in draws:
        if draw.status not in {"ready", "structure_unknown"}:
            replay.evidence.require(
                draw.status in {"content_rejected", "content_unknown"},
                "Unknown draw status",
            )
            continue
        n_draws += 1
        content_sha = replay.canonical_sha(draw.content)
        key = (
            draw.task,
            replay.canonical_sha(draw.source),
            content_sha,
            draw.entry["status"],
        )
        source_receipt = sealed[draw.task, draw.donor]
        replay.evidence.require(
            draw.content["size"] == draw.size
            and content_sha == source_receipt["content_sha256"],
            "Archived input differs",
        )
        if key not in rows:
            outcomes = {}
            for name, order_key in zip(
                KEYS, (draw.task, CONSTANT, content_sha), strict=True
            ):
                artifacts, decisions = select(
                    order_key, draw.content, draw.source, draw.entry
                )
                replay.evidence.require(
                    all(
                        decisions[p] in DECISIONS
                        and bool(artifacts[p]) == (decisions[p] == "pass")
                        for p in replay.POLICIES
                    ),
                    "Selector returned an inconsistent decision or artifact",
                )
                outcomes[name] = (artifacts, decisions)
            replay.evidence.require(
                replay.canonical_sha(draw.content) == content_sha,
                "Selector changed fixed content",
            )
            rows[key] = (draw.task, draw.size, outcomes)
        replay.evidence.require(
            rows[key][2]["original"]
            == (source_receipt["program"], source_receipt["program_decisions"]),
            "Original-key replay differs from sealed verdict or artifact",
        )
    return list(rows.values()), n_draws


def summarize(rows):
    result = {"unique_inputs": len(rows), "tasks": len({task for task, _, _ in rows})}
    for policy in replay.POLICIES:
        decisions = {}
        for name in KEYS:
            counts = Counter(outcomes[name][1][policy] for _, _, outcomes in rows)
            decisions[name] = {status: counts[status] for status in DECISIONS}
        pairwise = {}
        for left, right in combinations(KEYS, 2):
            counts = Counter()
            for _, _, outcomes in rows:
                lh, ld = outcomes[left]
                rh, rd = outcomes[right]
                if ld[policy] != rd[policy]:
                    counts["changed_decision"] += 1
                if lh[policy] and rh[policy]:
                    counts[
                        "same_sha" if lh[policy] == rh[policy] else "different_sha"
                    ] += 1
                elif lh[policy] or rh[policy]:
                    counts["one_artifact"] += 1
                else:
                    counts["neither_artifact"] += 1
            pairwise[f"{left}_vs_{right}"] = {
                name: counts[name]
                for name in (
                    "changed_decision",
                    "same_sha",
                    "different_sha",
                    "one_artifact",
                    "neither_artifact",
                )
            }
        changed_outputs = [
            task
            for task, _, outcomes in rows
            if len(
                {
                    outcomes[name][0][policy]
                    for name in KEYS
                    if outcomes[name][0][policy]
                }
            )
            > 1
        ]
        result[policy] = {
            "decisions": decisions,
            "pairs": pairwise,
            "any_different_positive_sha_inputs": len(changed_outputs),
            "any_different_positive_sha_tasks": len(set(changed_outputs)),
        }
    return result


def run(batch):
    sys.addaudithook(replay.evidence.no_network)
    receipts = batch / "augmented_content_draws_20261128/rows_verdicts.private.json"
    replay.evidence.check_file(receipts, replay.SEALED_ROWS)
    sealed = {(r["task"], r["donor"]): r for r in replay.evidence.load(receipts)}
    # The frozen parsing runtime and the public selection runtime use different
    # modules with the same import names, so isolate parsing in a fresh process.
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        plan_sha, draws = pool.submit(replay.verified_inputs, batch).result()
    select, _ = replay.public_selectors()
    rows, n_draws = observe(draws, sealed, select)
    return {
        "study": "Post-hoc offline sensitivity to the key ordering the frozen candidate menu. "
        "Each key sees identical content, source, entry and fonts. Decisions and positive A2UI byte "
        "hashes are separate measurements. A change in artifact bytes has no visual or preference judgment.",
        "constant_key": CONSTANT,
        "content_key": "SHA-256 of UTF-8 JSON, sorted keys, no extra spaces, unescaped Unicode.",
        "frozen_plan_sha256": plan_sha,
        "original_key_receipt_sha256": replay.SEALED_ROWS,
        "observed_content_draws": n_draws,
        "all": summarize(rows),
        "by_size": {
            s: summarize([r for r in rows if r[1] == s]) for s in ("2x2", "2x4")
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-root", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Write anonymous aggregates; defaults to checking the published table",
    )
    args = parser.parse_args()
    report = run(args.formal_root)
    if args.output:
        replay.evidence.save(args.output, report)
    else:
        replay.evidence.require(
            replay.evidence.load(TABLE) == report, "Published table differs"
        )
    print(json.dumps(report["all"], sort_keys=True))
