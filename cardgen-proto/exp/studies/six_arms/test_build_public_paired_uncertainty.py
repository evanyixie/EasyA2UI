import random
from collections import Counter
from fractions import Fraction
from pathlib import Path

import pytest


@pytest.fixture
def contrast(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms.build_public_paired_uncertainty import contrast

    return contrast


def test_populations_stay_paired_and_unobserved_states_remain_unknown(contrast):
    pairs = [
        ("private-z", "fail", "missing"),
        ("private-a", "pass", "fail"),
        ("private-z", "pass", "pass"),
        ("private-b", "pass", "fail"),
        ("private-z", "missing", "pass"),
    ]
    result = contrast(pairs, seed=7, draws=121)
    assert result["pass_left"] == 3 and result["pass_right"] == 2
    assert result["latent_net_bounds"] == [0, 2]
    assert result["family_histogram"] == [[1, 1, 2], [3, -1, 1]]
    # Independently sample whole family IDs and count the original pairs in the draw.
    rng = random.Random(7)
    counts = Counter()
    ids = sorted({family for family, _, _ in pairs})
    for _ in range(121):
        tasks = [p for f in rng.choices(ids, k=len(ids)) for p in pairs if p[0] == f]
        counts[
            Fraction(
                sum((a == "pass") - (b == "pass") for _, a, b in tasks), len(tasks)
            )
        ] += 1
    assert result["bootstrap_histogram"] == [
        [r.numerator, r.denominator, counts[r]] for r in sorted(counts)
    ]
    assert result == contrast(reversed(pairs), seed=7, draws=121)
    assert "private" not in str(result)


def test_fully_unknown_still_has_zero_obtained_passes(contrast):
    result = contrast([("secret", "missing", "missing")], seed=8, draws=8)
    assert result["bootstrap_histogram"] == [[0, 1, 8]]
    assert result["latent_net_bounds"] == [-1, 1]


@pytest.mark.parametrize("pairs", [[], [("a", "unregistered", "fail")]])
def test_rejects_invalid_rows(contrast, pairs):
    with pytest.raises(ValueError):
        contrast(pairs, seed=1, draws=8)
