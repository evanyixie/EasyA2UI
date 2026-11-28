import pytest
from preference_calibration import coefficient, summarize_reader, verify


def test_ranks_include_ties_and_repeated_deltas():
    bins = [[0, 29, 1, 18], [1, 1, 0, 9]]
    assert coefficient(bins) == {"n": 58, "spearman": 0.392256}
    assert coefficient([[0, 1, 2, 3]]) == {"n": 6, "spearman": None}
    assert coefficient([]) == {"n": 0, "spearman": None}
    assert coefficient([[-2, 0, 0, 1], [3, 0, 0, 2]])["spearman"] is None
    with pytest.raises(ValueError):
        coefficient([[1, -1, 0, 1]])


def test_missing_votes_cannot_be_counted_as_ties():
    table = {
        "bins": [[0, 0, 1, 0]],
        "missing_metric": 0,
        "result": {"n": 1, "spearman": None},
    }
    sheet = {
        "eligible": 3,
        "directional_or_tie": 0,
        "eligible_without_rank": {"blank": 3},
        "metrics": {"geometry": table},
    }
    report = {
        "columns": [
            "program_advantage",
            "prefer_model",
            "explicit_tie",
            "prefer_program",
        ],
        "cohorts": {"paired": {"pictured_pairs": 4, "readers": {"a": sheet}}},
    }
    with pytest.raises(ValueError, match="totals"):
        verify(report)


def test_summary_preserves_abstentions_and_metric_missingness():
    rows = [
        {"task": i, "eligible": True, "preference": v, "size": size}
        for i, (v, size) in enumerate(
            [("tie", None), ("model", -1), ("both_bad", 10), (None, 0)]
        )
    ]
    summary = summarize_reader(rows, ["size"])
    assert summary["eligible_without_rank"] == {"blank": 1, "both_bad": 1}
    assert summary["metrics"]["size"] == {
        "bins": [[-1, 1, 0, 0]],
        "result": {"n": 1, "spearman": None},
        "missing_metric": 1,
    }
    with pytest.raises(ValueError, match="eligibility"):
        summarize_reader([{**rows[0], "eligible": False}], ["size"])
