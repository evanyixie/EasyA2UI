import random
from collections import Counter
from fractions import Fraction
from pathlib import Path
from statistics import quantiles

import pytest


@pytest.fixture
def stats(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import public_paired_uncertainty

    return public_paired_uncertainty


def historic_draws(groups, seed, n):
    rng = random.Random(seed)
    rates = []
    for _ in range(n):
        indices = rng.choices(range(len(groups)), k=len(groups))
        rates.append(
            Fraction(
                sum(groups[i][1] for i in indices), sum(groups[i][0] for i in indices)
            )
        )
    return rates


def synthetic():
    groups = [(3, -1), (1, 1), (2, 0), (1, 1)]
    draws = historic_draws(groups, 8, 80)
    row = {
        "pass_left": 4,
        "pass_right": 3,
        "family_histogram": [[1, 1, 2], [3, -1, 1], [2, 0, 1]],
        "bootstrap_histogram": [
            [r.numerator, r.denominator, count] for r, count in Counter(draws).items()
        ],
    }
    return groups, draws, row


def test_different_family_sizes_and_original_vs_anonymous_order(stats):
    groups, draws, row = synthetic()
    out = stats.summarize(row, tasks=7, families=4, replicates=80, seed=8)
    old_quantiles = quantiles([float(x) for x in draws], n=40, method="inclusive")
    canonical = historic_draws(sorted(groups), 8, 80)
    new_quantiles = quantiles([float(x) for x in canonical], n=40, method="inclusive")
    assert out["obtained_difference_rate"] == 1 / 7
    assert out["historical_ci95_rate"] == pytest.approx(
        [old_quantiles[0], old_quantiles[-1]]
    )
    assert out["anonymous_resample_ci95_rate"] == pytest.approx(
        [new_quantiles[0], new_quantiles[-1]]
    )
    assert out["historical_ci95_rate"] != out["anonymous_resample_ci95_rate"]


@pytest.mark.parametrize(
    "override,reason",
    [
        ({"pass_left": 2}, "direction"),
        ({"pass_left": 1, "pass_right": 0}, "signs incompatible"),
        ({"family_histogram": [[1, 1, 3], [3, -1, 1]]}, "cohort"),
        ({"family_histogram": [[1, 1, 2], [1, 1, 2]]}, "duplicate"),
        ({"family_histogram": [[1, True, 4]]}, "three integers"),
        ({"family_histogram": [[1, -2, 4]]}, "size or net"),
        ({"bootstrap_histogram": [[1, 3, 79]]}, "draw count"),
        ({"bootstrap_histogram": [[0, 2, 80]]}, "unreduced"),
        ({"bootstrap_histogram": [[1, 0, 80]]}, "unreduced"),
        ({"bootstrap_histogram": [[1, 13, 80]]}, "unreduced"),
        ({"bootstrap_histogram": [[-1, 1, 80]]}, "range"),
    ],
)
def test_rejects_inconsistent_or_invalid_histograms(stats, override, reason):
    _, _, row = synthetic()
    with pytest.raises(ValueError, match=reason):
        stats.summarize({**row, **override}, tasks=7, families=4, replicates=80, seed=8)


def test_frozen_direction_and_cohort_are_required(stats):
    with pytest.raises(ValueError, match="schema"):
        stats.verify_public(
            {
                "schema": "public-paired-uncertainty-v1",
                "contrasts": {"joint/L6-L5": {}},
            },
            {},
            {},
            {},
        )


def test_reader_checks_earlier_tables_and_distinguishes_unknowns(stats):
    # A synthetic cohort of the registered size with 19 gains, plus two
    # unobserved L5 endpoints and one unobserved comparator endpoint.
    groups = [(1, 0)] * 181 + [(2, 1)] * 19
    draws = historic_draws(groups, 20261124, 10000)
    cuts = quantiles([float(x) for x in draws], n=40, method="inclusive")
    ci, point = [cuts[0], cuts[-1]], 19 / 219
    row = {
        "pass_left": 29,
        "pass_right": 10,
        "latent_net_bounds": [18, 21],
        "family_histogram": [[1, 0, 181], [2, 1, 19]],
        "bootstrap_histogram": [
            [x.numerator, x.denominator, n] for x, n in Counter(draws).items()
        ],
    }
    table = {
        "schema": "public-paired-uncertainty-v1",
        "seed": 20261124,
        "bootstrap_replicates": 10000,
        "contrasts": {name: row.copy() for name in stats.CONTRASTS},
    }
    technical = {
        "formal_six_arm_technical_and_time": {
            "columns": ["arm", "assigned", "final_accept", "unknown_final_status"],
            "rows": [["L5", 219, 29, 2], ["L4", 219, 10, 1], ["L6", 219, 10, 1]],
            "cohort": {"assigned_tasks": 219, "families": 200},
            "paired_family_bootstrap": {
                "draws": 10000,
                "seed": 20261124,
                "comparisons": {
                    key: {
                        "accepted_difference_pp": {
                            "point": round(point * 100, 4),
                            "percentile95": [round(x * 100, 4) for x in ci],
                        }
                    }
                    for key in ("L5_vs_L4_all", "L5_vs_L6_all")
                },
            },
        }
    }
    bounds = [18 / 219, 21 / 219]
    joint_final = {
        "arms": {
            arm: {"joint": {"pass": n}}
            for arm, n in (("L5", 29), ("L4", 10), ("L6", 10))
        },
        "paired_l5_minus_l4": {
            "certified_difference_rate": point,
            "latent_difference_rate_bounds": bounds,
            "certified_difference_family_percentile_ci95": ci,
        },
    }
    joint_all = {
        "cohorts": {
            "all_assigned": {
                "tasks": 219,
                "families": 200,
                "phases": {"after_common_repair": joint_final},
            }
        }
    }
    repair = {
        "additional_l5_minus_l6": {
            "certified_difference_rate_l5_minus_l6": point,
            "latent_difference_rate_bounds_l5_minus_l6": bounds,
            "certified_difference_family_percentile_ci95": ci,
        }
    }
    result = stats.verify_public(table, technical, joint_all, repair)
    assert set(result) == stats.CONTRASTS
    assert all(v["obtained_difference_rate"] == point for v in result.values())
    table["contrasts"]["joint/L5-L4"]["latent_net_bounds"] = [19, 19]
    with pytest.raises(ValueError, match="underlying unknown"):
        stats.verify_public(table, technical, joint_all, repair)
