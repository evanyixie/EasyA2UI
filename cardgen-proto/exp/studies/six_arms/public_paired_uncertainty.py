"""Check the published final L5-L4 and L5-L6 obtained-pass intervals without custody files.

Each family bin contains (assigned tasks, L5 passes minus comparator passes, families).
Each archived draw bin contains (reduced difference numerator, denominator, draws).
The latter recovers the historical interval. Resampling the former in canonical bin
order independently repeats the method without disclosing the original family order.
"""

import argparse
import json
import random
from fractions import Fraction
from math import gcd, isclose
from pathlib import Path
from statistics import quantiles

CONTRASTS = {
    f"{endpoint}/L5-{arm}"
    for endpoint in ("technical", "joint")
    for arm in ("L4", "L6")
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _bins(rows):
    seen = set()
    for row in rows:
        require(
            isinstance(row, list)
            and len(row) == 3
            and all(type(x) is int for x in row),
            "Expected three integers per bin",
        )
        a, b, frequency = row
        require(
            frequency > 0 and (a, b) not in seen, "Empty or duplicate histogram bin"
        )
        seen.add((a, b))
        yield a, b, frequency


def interval(values):
    # Same inclusive type-7 cuts as fixed_layout.paired_analysis.analyze.
    cuts = quantiles(values, n=1000, method="inclusive")
    return [cuts[24], cuts[974]]


def summarize(row, *, tasks, families, replicates, seed):
    group_bins = sorted(_bins(row["family_histogram"]))
    require(
        all(s > 0 and abs(d) <= s for s, d, _ in group_bins),
        "Invalid family size or net",
    )
    require(
        sum(f for _, _, f in group_bins) == families
        and sum(s * f for s, _, f in group_bins) == tasks
        and 0 < families <= tasks,
        "Family counts do not reproduce the cohort",
    )
    left, right = row["pass_left"], row["pass_right"]
    require(
        all(type(v) is int and 0 <= v <= tasks for v in (left, right)),
        "Invalid arm counts",
    )
    net = sum(d * f for _, d, f in group_bins)
    require(
        net == left - right, "Family differences disagree with arm counts or direction"
    )
    # Opposite signs in distinct families require at least this many passes on either side.
    require(
        sum(max(d, 0) * f for _, d, f in group_bins) <= min(left, tasks - right)
        and sum(max(-d, 0) * f for _, d, f in group_bins) <= min(right, tasks - left),
        "Family signs incompatible with pass margins",
    )

    fractions = [Fraction(d, s) for s, d, _ in group_bins]
    lower, upper = min(fractions), max(fractions)
    max_denominator = families * max(s for s, _, _ in group_bins)
    draw_bins = list(_bins(row["bootstrap_histogram"]))
    require(
        sum(f for _, _, f in draw_bins) == replicates >= 2, "Wrong bootstrap draw count"
    )
    archived = []
    for numerator, denominator, frequency in draw_bins:
        require(
            0 < denominator <= max_denominator and gcd(numerator, denominator) == 1,
            "Invalid or unreduced draw ratio",
        )
        rate = Fraction(numerator, denominator)
        require(
            lower <= rate <= upper,
            "Draw outside the range of the observed family rates",
        )
        archived.extend([float(rate)] * frequency)

    # Anonymous canonical order may differ from the historical order even with the same seed.
    population = [(s, d) for s, d, f in group_bins for _ in range(f)]
    rng = random.Random(seed)
    independent = []
    for _ in range(replicates):
        sample = rng.choices(population, k=families)
        independent.append(sum(d for _, d in sample) / sum(s for s, _ in sample))
    return {
        "tasks": tasks,
        "families": families,
        "pass_left": left,
        "pass_right": right,
        "net": net,
        "obtained_difference_rate": net / tasks,
        "historical_ci95_rate": interval(archived),
        "anonymous_resample_ci95_rate": interval(independent),
    }


def verify_public(table, technical, all_arms, repair):
    """Check each contrast against its separately published endpoint, scale and precision."""
    require(
        table["schema"] == "public-paired-uncertainty-v1"
        and set(table["contrasts"]) == CONTRASTS,
        "Unexpected comparison set or schema",
    )
    technical = technical["formal_six_arm_technical_and_time"]
    cohort = all_arms["cohorts"]["all_assigned"]
    joint = cohort["phases"]["after_common_repair"]
    bootstrap = technical["paired_family_bootstrap"]
    tasks, families = cohort["tasks"], cohort["families"]
    require(
        tasks == technical["cohort"]["assigned_tasks"] == 219
        and families == technical["cohort"]["families"] == 200
        and table["seed"] == bootstrap["seed"] == 20261124
        and table["bootstrap_replicates"] == bootstrap["draws"] == 10000,
        "Unexpected formal cohort or bootstrap settings",
    )
    technical_arms = {
        r["arm"]: r
        for r in (
            dict(zip(technical["columns"], v, strict=True)) for v in technical["rows"]
        )
    }
    result = {}
    for name in sorted(CONTRASTS):
        endpoint, pair = name.split("/")
        left, right = pair.split("-")
        row = table["contrasts"][name]
        out = summarize(
            row,
            tasks=tasks,
            families=families,
            replicates=table["bootstrap_replicates"],
            seed=table["seed"],
        )
        if endpoint == "technical":
            a, b = technical_arms[left], technical_arms[right]
            require(
                a["assigned"] == b["assigned"] == tasks, "Technical denominator changed"
            )
            counts = (a["final_accept"], b["final_accept"])
            net = counts[0] - counts[1]
            bounds = [net - b["unknown_final_status"], net + a["unknown_final_status"]]
            expected = bootstrap["comparisons"][f"{left}_vs_{right}_all"][
                "accepted_difference_pp"
            ]
            observed = [out["obtained_difference_rate"], *out["historical_ci95_rate"]]
            # Original technical table reports percentage points rounded to four decimals.
            require(
                [round(x * 100, 4) for x in observed]
                == [expected["point"], *expected["percentile95"]],
                f"{name}: interval or difference disagrees with published technical result",
            )
        else:
            counts = tuple(joint["arms"][arm]["joint"]["pass"] for arm in (left, right))
            if right == "L4":
                source = joint["paired_l5_minus_l4"]
                point = source["certified_difference_rate"]
                latent = source["latent_difference_rate_bounds"]
            else:
                source = repair["additional_l5_minus_l6"]
                point = source["certified_difference_rate_l5_minus_l6"]
                latent = source["latent_difference_rate_bounds_l5_minus_l6"]
            bounds = [round(x * tasks) for x in latent]
            expected = [point, *source["certified_difference_family_percentile_ci95"]]
            observed = [out["obtained_difference_rate"], *out["historical_ci95_rate"]]
            require(
                all(
                    isclose(a, b, abs_tol=1e-15, rel_tol=0)
                    for a, b in zip(expected, observed, strict=True)
                ),
                f"{name}: interval or difference disagrees with published joint result",
            )
        require(
            (row["pass_left"], row["pass_right"]) == counts,
            f"{name}: published margins disagree",
        )
        require(
            row["latent_net_bounds"] == bounds,
            f"{name}: underlying unknown bounds disagree",
        )
        result[name] = {**out, "latent_net_bounds": bounds}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "table",
        type=Path,
        help="public_paired_uncertainty.json with the three earlier tables beside it",
    )
    path = parser.parse_args().table
    earlier = (
        "six_arm_evidence_20261128.json",
        "formal_arm_content_yield.json",
        "repair_content_yield.json",
    )
    result = verify_public(
        json.loads(path.read_bytes()),
        *(json.loads((path.parent / f).read_bytes()) for f in earlier),
    )
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
