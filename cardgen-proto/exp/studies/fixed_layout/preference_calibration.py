"""Recompute T04 preference correlations from anonymous paired counts.

Each bin contains one program advantage and three counts (model preferred,
explicit tie, program preferred). Unknown, missing and both-bad responses
have no rank. Keep independent studies, readers and metrics separate.
"""

import argparse
import json
from collections import Counter
from math import isfinite
from pathlib import Path
from statistics import correlation

COLUMNS = ["program_advantage", "prefer_model", "explicit_tie", "prefer_program"]
PREFERENCE = {"model": -1, "tie": 0, "program": 1}


def midranks(values):
    counts = Counter(values)
    ranks = {}
    offset = 0
    for value, count in sorted(counts.items()):
        ranks[value] = offset + (count + 1) / 2
        offset += count
    return [ranks[value] for value in values]


def coefficient(bins):
    predictors, votes = [], []
    seen = set()
    for delta, model, tie, program in bins:
        if type(delta) not in (int, float) or not isfinite(delta) or delta in seen:
            raise ValueError("Expected a distinct finite program advantage per row")
        seen.add(delta)
        for preference, count in zip((-1, 0, 1), (model, tie, program)):
            if type(count) is not int or count < 0:
                raise ValueError("Expected nonnegative integer pair counts")
            predictors.extend([delta] * count)
            votes.extend([preference] * count)
    rho = None
    if len(set(predictors)) > 1 and len(set(votes)) > 1:
        rho = round(correlation(midranks(predictors), midranks(votes)), 6)
    return {"n": len(votes), "spearman": rho}


def summarize_reader(rows, metrics):
    """One row per pictured pair; omit unpublished task keys from the result."""
    if len({row["task"] for row in rows}) != len(rows):
        raise ValueError("Duplicate task in reader sheet")
    for row in rows:
        pref = row["preference"]
        if pref not in {*PREFERENCE, "unknown", "both_bad", None}:
            raise ValueError("Unexpected preference")
        if type(row["eligible"]) is not bool or (
            not row["eligible"] and pref is not None
        ):
            raise ValueError("Preference without eligibility")
    ranked = [row for row in rows if row["preference"] in PREFERENCE]
    result = {}
    for metric in metrics:
        freq = Counter(
            (r[metric], r["preference"]) for r in ranked if r[metric] is not None
        )
        deltas = sorted({delta for delta, _ in freq})
        bins = [[d, *(freq[d, k] for k in ("model", "tie", "program"))] for d in deltas]
        calc = coefficient(bins)
        result[metric] = {
            "bins": bins,
            "result": calc,
            "missing_metric": len(ranked) - calc["n"],
        }
    eligible = [r for r in rows if r["eligible"]]
    return {
        "eligible": len(eligible),
        "directional_or_tie": len(ranked),
        "eligible_without_rank": dict(
            sorted(
                Counter(
                    r["preference"] or "blank"
                    for r in eligible
                    if r["preference"] not in PREFERENCE
                ).items()
            )
        ),
        "metrics": result,
    }


def verify(report):
    if report["columns"] != COLUMNS:
        raise ValueError("Unexpected table schema")
    results = {}
    for cohort, study in report["cohorts"].items():
        for reader, sheet in study["readers"].items():
            if (
                not 0
                <= sheet["directional_or_tie"]
                <= sheet["eligible"]
                <= study["pictured_pairs"]
            ):
                raise ValueError("Inconsistent reader coverage")
            without_rank = sheet["eligible_without_rank"]
            if (
                not without_rank.keys() <= {"blank", "unknown", "both_bad"}
                or any(type(n) is not int or n < 0 for n in without_rank.values())
                or sum(without_rank.values())
                != sheet["eligible"] - sheet["directional_or_tie"]
            ):
                raise ValueError("Missing or inapplicable ranks do not match coverage")
            for metric, table in sheet["metrics"].items():
                calc = coefficient(table["bins"])
                if calc["n"] + table["missing_metric"] != sheet["directional_or_tie"]:
                    raise ValueError(
                        "Pair totals do not match eligible, observed preferences"
                    )
                if table["missing_metric"] < 0 or calc != table["result"]:
                    raise ValueError("Published result disagrees with paired counts")
                results[f"{cohort}/{reader}/{metric}"] = calc
    return results


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("table", type=Path)
    args = cli.parse_args()
    print(json.dumps(verify(json.loads(args.table.read_bytes())), indent=2))
