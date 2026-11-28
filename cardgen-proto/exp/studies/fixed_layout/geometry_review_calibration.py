"""Compare a frozen reference-geometry verdict with two existing overall ratings.

Input is one JSON list of de-identified pictured seats. Each row has task, arm,
image_sha256, geometry, and original/final pairs of overall votes. Missing
votes remain unresolved. Distinct requests may legitimately share an image.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ARMS = ("model_model", "program_program")
GEOMETRY = {"verified", "mismatch"}
VOTES = {"pass", "fail"}


def agreement(votes):
    if any(v not in VOTES for v in votes):
        return "unresolved"
    if votes[0] != votes[1]:
        return "disagree"
    return "both_" + votes[0]


def tabulate(rows, version, equal_image_weight=False):
    frequency = Counter(r["image_sha256"] for r in rows)
    groups = {key: Counter() for key in sorted(GEOMETRY)}
    for row in rows:
        weight = 1 / frequency[row["image_sha256"]] if equal_image_weight else 1
        groups[row["geometry"]][agreement(row[version])] += weight
    return {g: {k: round(v, 4) for k, v in sorted(n.items())} for g, n in groups.items()}


def paired(rows, version):
    by_task = defaultdict(dict)
    for row in rows:
        by_task[row["task"]][row["arm"]] = row
    counts = Counter()
    for pair in by_task.values():
        if len(pair) != 2:
            continue
        model, prog = (pair[arm] for arm in ARMS)
        machine = (model["geometry"], prog["geometry"])
        if machine[0] == machine[1]:
            direction = "same_verdict"
        else:
            direction = ARMS[machine.index("verified")]
        human = (agreement(model[version]), agreement(prog[version]))
        if any(v not in {"both_pass", "both_fail"} for v in human):
            decided = "no_joint_pair_verdict"
        elif human[0] == human[1]:
            decided = "same_verdict"
        else:
            decided = ARMS[human.index("both_pass")]
        counts[direction, decided] += 1
    return {f"{g}/{h}": n for (g, h), n in sorted(counts.items())}


def summarize(rows):
    seats = set()
    for row in rows:
        key = (row["task"], row["arm"])
        if key in seats or key[1] not in ARMS or row["geometry"] not in GEOMETRY:
            raise ValueError("Duplicate seat or unknown method/verdict")
        if len(row["image_sha256"]) != 64:
            raise ValueError("Missing image fingerprint")
        for version in ("original", "final"):
            votes = row[version]
            if len(votes) != 2 or any(v not in {*VOTES, None, "unknown"} for v in votes):
                raise ValueError("Expected two explicit or unresolved votes")
        seats.add(key)
    report = {"pictured_seats": len(seats), "unique_images": len({r["image_sha256"] for r in rows})}
    for version in ("original", "final"):
        report[version] = {
            "seats": tabulate(rows, version),
            "by_method": {
                arm: tabulate([r for r in rows if r["arm"] == arm], version) for arm in ARMS
            },
            "equal_weight_per_image": tabulate(rows, version, True),
            "paired_technical_vs_human": paired(rows, version),
        }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(json.loads(args.rows.read_bytes())), ensure_ascii=False, indent=2))
