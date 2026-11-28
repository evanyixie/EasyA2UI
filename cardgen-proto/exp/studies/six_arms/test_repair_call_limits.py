from pathlib import Path

import pytest


@pytest.fixture
def limits(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import repair_call_limits

    return repair_call_limits


def test_replay_stops_after_program_or_first_rewrite(limits):
    case = {
        "model_eligibility": "awaiting_first_repair",
        "model_rounds": [
            {"round": 1, "common_pass": False, "added_tokens": 24},
            {"round": 2, "common_pass": True, "added_tokens": 30},
        ],
    }
    accepted = {"initial_status": "accepted"}
    rejected = {"initial_status": "geometry_unresolved"}
    assert limits.repair_choice(accepted, case, True) == ("pass", [])
    assert limits.repair_choice(rejected, case, False) == ("fail", [])
    assert limits.repair_choice(rejected, case, True) == ("fail", [24])
    case["model_rounds"][0].update(common_pass=None, added_tokens=None)
    assert limits.repair_choice(rejected, case, True) == ("missing", [None])


def test_cap_and_unknown_preserved(limits):
    rows = [
        {
            "task": "1",
            "family": "a",
            "whole_card": ("missing", [None]),
            "staged": ("pass", [9]),
        },
        {
            "task": "2",
            "family": "b",
            "whole_card": ("pass", [4, 3]),
            "staged": ("fail", [8]),
        },
    ]
    result = limits.score(rows, 2)
    assert result["difference_bounds_with_unknown_outcomes"] == [-0.5, 0]
    assert result["obtained_difference_staged_minus_whole_card"] == 0
    assert result["strategies"]["whole_card"]["unmetered_requests"] == 1
    assert result["strategies"]["whole_card"]["metered_tokens"] == 7
    with pytest.raises(ValueError):
        limits.score(rows, 1)
