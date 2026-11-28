"""Paired tests for observed technical yield across adjacent experimental arms."""

import argparse
import json
from collections import Counter, defaultdict
from itertools import pairwise
from math import comb
from pathlib import Path

from six_arms.technical_yield import ARMS, DECISION, read_lines

PRIMARY = "L5-L4"
PAIRS = tuple(f"{b}-{a}" for a, b in pairwise(ARMS))


def task_pair_p(left_only, right_only):
    n = left_only + right_only
    tail = sum(comb(n, k) for k in range(min(left_only, right_only) + 1))
    return min(1.0, (2 * tail) / 2**n)


def family_pair_p(differences):
    """Swap method labels together within each family under exchangeability."""
    sums = Counter({0: 1})
    weights = [abs(d) for d in differences if d]
    for weight in weights:
        updated = Counter()
        for total, count in sums.items():
            updated[total - weight] += count
            updated[total + weight] += count
        sums = updated
    observed = abs(sum(differences))
    return sum(count for value, count in sums.items() if abs(value) >= observed) / 2**len(weights)


def holm(probabilities):
    adjusted = {}
    previous = 0.0
    for i, (key, p) in enumerate(sorted(probabilities.items(), key=lambda item: item[1])):
        previous = max(previous, min(1.0, (len(probabilities) - i) * p))
        adjusted[key] = previous
    return adjusted


def tests_from_counts(rows):
    """Compute paired tests from counts for each contrast independently."""
    if set(rows) != set(PAIRS):
        raise ValueError("Expected all five adjacent arm contrasts")
    out = {}
    for name in PAIRS:
        row = rows[name]
        earlier = row["only_earlier_observed_pass"]
        later = row["only_later_observed_pass"]
        tasks, families = row["tasks"], row["families"]
        if (
            any(type(v) is not int for v in (earlier, later, tasks, families))
            or min(earlier, later) < 0 or earlier + later > tasks or not 0 < families <= tasks
        ):
            raise ValueError(f"{name}: invalid assignment or discordant counts")
        differences = []
        for key, frequency in row["family_net_difference_histogram"].items():
            delta = int(key)
            if str(delta) != key or type(frequency) is not int or not 0 < frequency <= families:
                raise ValueError(f"{name}: invalid histogram bin")
            differences.extend([delta] * frequency)
        if (
            len(differences) != families or sum(differences) != later - earlier
            or row["later_minus_earlier_observed_pass"] != later - earlier
            or sum(abs(d) for d in differences) > earlier + later
        ):
            raise ValueError(f"{name}: histogram does not agree with paired counts")
        out[name] = {
            "task_mcnemar_exact": task_pair_p(earlier, later),
            "family_swap_exact": family_pair_p(differences),
        }
    for metric in ("task_mcnemar_exact", "family_swap_exact"):
        corrected = holm({k: v[metric] for k, v in out.items() if k != PRIMARY})
        for name, row in out.items():
            row[metric + "_holm_four_secondary"] = corrected.get(name)
    return out


def adjacent(roster, seats):
    families = {r["task_id"]: r["family"] for r in roster}
    values = {(r["task_id"], r["arm"]): DECISION[r["status"]] for r in seats}
    required = {(task, arm) for task in families for arm in ARMS}
    if not families or not all(families.values()) or len(families) != len(roster):
        raise ValueError("Invalid assignment roster")
    if values.keys() != required or len(values) != len(seats):
        raise ValueError("A seat is missing, duplicated or outside the assignment")
    out = {}
    for a, b in pairwise(ARMS):
        deltas = defaultdict(int)
        a_only = b_only = missing = 0
        for task, family in families.items():
            left, right = values[task, a], values[task, b]
            missing += "missing" in (left, right)
            delta = int(right == "pass") - int(left == "pass")
            deltas[family] += delta
            a_only += delta == -1
            b_only += delta == 1
        out[f"{b}-{a}"] = {
            "tasks": len(families),
            "families": len(deltas),
            "either_underlying_status_unknown": missing,
            "only_earlier_observed_pass": a_only,
            "only_later_observed_pass": b_only,
            "later_minus_earlier_observed_pass": b_only - a_only,
            "family_net_difference_histogram": {
                str(delta): count for delta, count in sorted(Counter(deltas.values()).items())
            },
        }
    for name, result in tests_from_counts(out).items():
        out[name].update(result)
    return out


def verify_public(table):
    rows = table["adjacent_observed_technical_yield"]
    results = tests_from_counts(rows)
    for name, result in results.items():
        for metric, calculated in result.items():
            if rows[name][metric] != calculated:
                raise ValueError(f"{name}: published {metric} does not match the paired counts")
    return results


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    source = cli.add_mutually_exclusive_group(required=True)
    source.add_argument("batch", nargs="?", type=Path, help="sealed batch directory")
    source.add_argument("--public", type=Path, help="recompute and check the published aggregate JSON")
    args = cli.parse_args()
    if args.public is not None:
        result = verify_public(json.loads(args.public.read_bytes()))
    else:
        analysis = args.batch / "analysis"
        tech = args.batch / "tech_metrics/continuation_final"
        seals = json.loads((analysis / "analysis_seal.json").read_bytes())["files_sha256"]
        roster = read_lines(analysis / "roster.jsonl", seals["roster.jsonl"])
        seat_sha = json.loads((tech / "completion_receipt.json").read_bytes())["private_seats_sha256"]
        seats = read_lines(tech / "seats.private.jsonl", seat_sha)
        result = adjacent(roster, seats)
    print(json.dumps(result, indent=2, allow_nan=False))
