from itertools import product
from pathlib import Path
from statistics import median

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import paired_resource_differences

    return paired_resource_differences


def test_exact_tied_rank_probability_matches_all_sign_flips(study):
    signed_rank = study.signed_rank
    sample = [-3, 0, 3, 1, 1, -7]
    # Magnitudes in the input order take ranks 3.5, 3.5, 1.5, 1.5, 5.
    ranks = [3.5, 3.5, 1.5, 1.5, 5]
    flips = [
        sum(s * r for s, r in zip(signs, ranks, strict=True))
        for signs in product((1, -1), repeat=5)
    ]
    distance = abs(3.5 + 1.5 + 1.5 - 3.5 - 5)
    result = signed_rank(sample)
    assert result["w_positive"] == 6.5 and result["w_negative"] == 8.5
    assert result["p_two_sided"] == sum(abs(d) >= distance for d in flips) / len(flips)
    assert result["zeros"] == 1
    assert signed_rank([0, 0])["p_two_sided"] is None
    assert signed_rank([median([1, 2]), -1.5])["p_two_sided"] == 1


def test_unmetered_and_no_model_call_are_distinct(study):
    metric_values = study.metric_values
    row = {"elapsed_ms": 0.123, "calls": []}
    assert metric_values(row) == {
        "executor_ms": 123,
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }
    row["calls"].append(
        {
            "tokens": dict.fromkeys(
                ("prompt_tokens", "completion_tokens", "total_tokens")
            )
        }
    )
    assert metric_values(row) == {
        "executor_ms": 123,
        "prompt_tokens": None,
        "completion_tokens": None,
    }
