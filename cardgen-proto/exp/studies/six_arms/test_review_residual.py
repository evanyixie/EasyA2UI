import itertools
from pathlib import Path

import pytest


@pytest.fixture
def residual(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import review_residual

    return review_residual


def test_optimistic_counts_match_exhaustive_subsets(residual):
    intervals = [(-1, 1), (0, 1), (-1, 0), (0, 0)]
    for bounds in itertools.combinations_with_replacement(intervals, 4):
        for direction in (1, -1):
            possibilities = []
            for selected in itertools.chain.from_iterable(
                itertools.combinations(range(4), n) for n in range(5)
            ):
                total = sum(
                    (max if i in selected else min)(direction * lo, direction * hi)
                    for i, (lo, hi) in enumerate(bounds)
                )
                if total > 0:
                    possibilities.append(len(selected))
            assert residual.earliest_decisive_count(bounds, direction) == min(
                possibilities, default=None
            )


def test_units_keep_context_and_transport_separate(residual):
    def card(artifact, image, status="unknown"):
        return {"artifact": artifact, "image": image, "primary": status}

    def task(tid, left, right):
        return {
            "task": tid,
            "input": "same",
            "arms": {
                "L5": dict(zip(residual.POINTS, left)),
                "L4": dict(zip(residual.POINTS, right)),
            },
        }

    same = card("a", "x")
    records = [
        task("one", [same, same], [card("b", "y"), card("c", "y")]),
        task("two", [same, same], [card(None, None), card(None, None)]),
    ]
    result = residual.portfolio(records, ("L5", "L4"))
    assert result["distinct_absolute_visual_units_per_reader_within_arm"] == 4
    assert result["distinct_absolute_visual_units_if_cross_arm_reuse_signed"] == 4
    assert result["distinct_visual_units_if_whole_context_must_match"] == 5
    for cp in residual.POINTS:
        assert result["checkpoints"][cp]["seats"]["unknown_without_image"] == 1
        assert result["checkpoints"][cp]["net_bounds"] == [-2, 2]


def test_cross_arm_visual_identity_requires_same_task_artifact_and_image(residual):
    def card(artifact, image):
        return {"artifact": artifact, "image": image, "primary": "unknown"}

    def task(task_id):
        return {
            "task": task_id,
            "input": "frozen-input",
            "arms": {
                arm: dict.fromkeys(residual.POINTS, c)
                for arm, c in (
                    ("L4", card("different-source", "pixels")),
                    ("L5", card("same-source", "pixels")),
                    ("L6", card("same-source", "pixels")),
                )
            },
        }

    result = residual.portfolio([task("first"), task("second")], residual.ARMS)
    assert result["distinct_absolute_visual_units_if_cross_arm_reuse_signed"] == 4
    assert result["distinct_absolute_visual_units_per_reader_within_arm"] == 6
