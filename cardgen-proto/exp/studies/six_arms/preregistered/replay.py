"""Recompute the primary delivery endpoint from the original sealed observations."""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(DIRECTORY.parents[1]))
from six_arms.fixed_content_repeats import FORMAL_PLAN, check
from six_arms.paired_delivery_bounds import EVALUATOR, GRIDS, ROSTER, verified

TABLE = DIRECTORY.parents[4] / "paper/out/tables/formal_delivery_replay.json"
INPUT_INDEX = "96e5bddfd402f9d5c2d67f78d92400a67718b1d9054797eeb0a1d33f14256b2a"
CODE = {
    "endpoint.py": EVALUATOR,
    "cohort_analysis.py": "e4e1357bd83bfde927dfdca588da63406894bf52f3854c3b158c119bf7f25209",
    "paired_stats.py": "701f083ae61ea3b6533661d7663abc13feeed5a25ff4ae2c03c0b47b3ca798c5",
}


def load_rows(path, digest):
    return [json.loads(line) for line in verified(path, digest).splitlines()]


def run(root):
    for filename, digest in CODE.items():
        verified(DIRECTORY / filename, digest)
    # The archived modules use sibling imports. Verify them before loading them.
    from cohort_analysis import ARMS, POINTS, collect, summarize

    roster = load_rows(root / "analysis/roster.jsonl", ROSTER)
    index = load_rows(root / "analysis/execution_index.jsonl", INPUT_INDEX)
    roster_by_task = {r["task_id"]: r for r in roster}
    check(len(roster_by_task) == len(roster) == 219, "Invalid formal roster")
    check(
        len(index) == len(roster)
        and {r["task_id"] for r in index} == roster_by_task.keys(),
        "Wrong execution index",
    )
    filename, digest = GRIDS["original"]
    rows = load_rows(root / "followup_evidence_20261128" / filename, digest)
    by_task = defaultdict(list)
    for row in rows:
        by_task[row["task_id"]].append(row)
    check(by_task.keys() == roster_by_task.keys(), "Wrong observation subjects")
    decisions = {}
    for entry in index:
        task = entry["task_id"]
        check(
            all(entry[k] == v for k, v in roster_by_task[task].items()),
            "Roster mismatch",
        )
        # Some different requests legitimately share model-visible input. Pair by task.
        decisions.update(collect([entry], by_task[task], FORMAL_PLAN))

    cohorts = {}
    for label in ("219", "217"):
        members = [
            {**r, "input_sha256": r["raw_request_sha256"]}
            for r in roster
            if label == "219" or r["included_in_217_sensitivity"]
        ]
        check(len(members) == int(label), "Wrong sensitivity cohort")
        estimates = summarize(members, decisions)
        phases = {}
        for point in POINTS:
            primary = estimates[f"{point}/primary"]
            missing = Counter(
                condition
                for member in members
                for arm in ARMS
                for verdict in [decisions[member["task_id"], arm, point]["primary"]]
                if verdict["status"] == "unknown"
                for condition in verdict["unknown"]
            )
            phases[point] = {
                "arms": primary["arms"],
                "unknown_criteria_among_unresolved_seats": dict(missing),
                "paired_contrasts": {
                    name: {
                        k: comparison[k]
                        for k in (
                            "n_total",
                            "n_known",
                            "n_unknown",
                            "paired_table",
                            "effect_bounds",
                            "effect",
                            "inference_status",
                        )
                    }
                    for name, comparison in primary["contrasts"].items()
                },
            }
        cohorts[label] = {
            "families": len({r["family"] for r in members}),
            "phases": phases,
        }
    return {
        "code_sha256": CODE,
        "observations_sha256": digest,
        "observations": len(rows),
        "cohorts": cohorts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_root", type=Path)
    parser.add_argument("--output", type=Path, help="Write a new anonymous aggregate")
    args = parser.parse_args()
    output = run(args.formal_root)
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(
                json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            )
    else:
        check(
            output == json.loads(TABLE.read_bytes()), "Published endpoint table differs"
        )
    print(
        f"Verified {output['observations']} checkpoint observations from the sealed batch."
    )


if __name__ == "__main__":
    main()
