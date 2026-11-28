from pathlib import Path

import pytest


def test_direction_and_shared_family_denominator(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms.layout_pair_summary import summarize

    cases = [
        {"task": "one", "family": "same", "l5": True, "l6": False},
        {"task": "two", "family": "same", "l5": True, "l6": True},
    ]
    summary = summarize(cases)
    assert (summary["requests"], summary["families"]) == (2, 1)
    assert (summary["both"], summary["only_l5"], summary["only_l6"]) == (1, 1, 0)
    assert summary["net_percentage_points"] == -50
    assert summary["family_bootstrap_ci95_pp"] is None
    with pytest.raises(ValueError):
        summarize([cases[0], cases[0]])
    with pytest.raises(ValueError, match="Missing"):
        summarize([{**cases[0], "l5": None}])


def test_fallback_charges_only_after_program_rejection(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms.layout_fallback_replay import aggregate

    timings = []
    calls = {}
    for task, model, program in [
        ("both", True, True), ("model", True, False),
        ("program", False, True), ("neither", False, False),
    ]:
        timings.append({"task": task, "strict": {
            "passes": {"model": model, "program": program},
            "program_ms": 2, "model_ms": 100,
        }})
        calls[task] = {"total_tokens": 10}
    result = aggregate(timings, calls, "strict")
    assert (result["fallback_calls"], result["rescued"], result["neither"]) == (2, 1, 1)
    assert result["program_or_fallback_pass"] == 3
    assert result["estimated_serial_mean_ms"] == result["estimated_serial_median_ms"] == 52
    assert result["fallback_structure_tokens"] == 20
