from pathlib import Path

import pytest


@pytest.fixture
def stats(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import adjacent_yield

    return adjacent_yield


def test_family_swaps_respect_opposing_and_repeated_members(stats):
    assert stats.family_pair_p([0, 0]) == 1
    assert stats.family_pair_p([3, -3]) == 1
    assert stats.family_pair_p([3, 3]) == 0.5
    assert stats.task_pair_p(0, 6) == 0.03125
    assert stats.holm({"a": 0.11, "b": 0.10, "c": 0.08}) == {"a": 0.24, "b": 0.24, "c": 0.24}


def test_missing_is_retained_and_primary_is_separate(stats):
    roster = [{"task_id": "one", "family": "g"}]
    seats = [{"task_id": "one", "arm": a, "status": "accepted"} for a in stats.ARMS]
    seats[-1]["status"] = "callback_failed"
    result = stats.adjacent(roster, seats)
    assert result["L6-L5"]["only_earlier_observed_pass"] == 1
    assert result["L6-L5"]["either_underlying_status_unknown"] == 1
    assert result["L5-L4"]["family_swap_exact_holm_four_secondary"] is None


def test_anonymous_histograms_reproduce_tests_and_reject_inconsistent_evidence(stats):
    roster = [
        {"task_id": name, "family": group}
        for name, group in zip("abcde", ("x", "x", "y", "y", "z"), strict=True)
    ]
    seats = []
    for arm in stats.ARMS:
        accepted = "ce" if arm == "L6" else "abde"
        for task in "abcde":
            status = "accepted" if task in accepted else "stage_rejected"
            seats.append({"task_id": task, "arm": arm, "status": status})
    rows = stats.adjacent(roster, seats)
    last = rows["L6-L5"]
    assert last["family_net_difference_histogram"] == {"-2": 1, "0": 2}
    assert (last["only_earlier_observed_pass"], last["only_later_observed_pass"]) == (3, 1)
    table = {"adjacent_observed_technical_yield": rows}
    verified = stats.verify_public(table)
    assert verified["L6-L5"]["family_swap_exact"] == 1
    assert verified["L6-L5"]["task_mcnemar_exact"] == 0.625

    last["family_net_difference_histogram"] = {"-1": 1, "0": 2}
    with pytest.raises(ValueError, match="histogram does not agree"):
        stats.verify_public(table)
    last["family_net_difference_histogram"] = {"-2": 1, "0": 2}
    last["task_mcnemar_exact_holm_four_secondary"] = 0.01
    with pytest.raises(ValueError, match="published"):
        stats.verify_public(table)
