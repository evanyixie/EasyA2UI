from pathlib import Path

import pytest


@pytest.fixture
def metric(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import repair_strategy_comparison

    return repair_strategy_comparison


def record(kind, first=None, final=None, seq=()):
    return {
        "model_eligibility": kind,
        "first_common": first,
        "model_common": final,
        "initial_sha256": None if kind == "no_first_artifact" else "original",
        "model_rounds": [{"round": i, "common_pass": v} for i, v in enumerate(seq, 1)],
    }


@pytest.mark.parametrize(
    ("row", "original_status", "state"),
    [
        (record("no_first_artifact"), "callback_failed", "missing"),
        (record("no_first_artifact"), "stage_rejected", "fail"),
        (record("trigger_unknown"), "geometry_unknown", "missing"),
        (record("no_trigger", True), "accepted", "pass"),
        (
            record("awaiting_first_repair", False, True, [True]),
            "geometry_unresolved",
            "pass",
        ),
        (
            record("awaiting_first_repair", False, False, [False, False]),
            "accepted",
            "fail",
        ),
        (record("awaiting_first_repair", False, None, [None]), "accepted", "missing"),
    ],
)
def test_registered_branch_preserved(metric, row, original_status, state):
    assert metric.model_result(row, original_status) == state


@pytest.mark.parametrize(
    "row",
    [
        record("awaiting_first_repair", True, True, [True]),
        record("awaiting_first_repair", False, False, [False]),
        record("awaiting_first_repair", False, False, [True, False]),
        record("no_trigger", False),
        record("trigger_unknown", None, None, [None]),
    ],
)
def test_inconsistent_attempt_order_and_triggers_rejected(metric, row):
    with pytest.raises(ValueError):
        metric.model_result(row, "accepted")


def test_paired_observations_keep_unknown_bounds_and_clusters(metric):
    rows = [
        {
            "task": "a",
            "family": "u",
            "L1-M": "pass",
            "L5": "fail",
            "L6": "pass",
            "first_common": False,
            "initial_status": "accepted",
            "eligibility": "awaiting_first_repair",
        },
        {
            "task": "b",
            "family": "u",
            "L1-M": "missing",
            "L5": "pass",
            "L6": "missing",
            "first_common": None,
            "initial_status": "callback_failed",
            "eligibility": "no_first_artifact",
        },
        {
            "task": "c",
            "family": "v",
            "L1-M": "fail",
            "L5": "pass",
            "L6": "fail",
            "first_common": False,
            "initial_status": "geometry_unresolved",
            "eligibility": "awaiting_first_repair",
        },
    ]
    data = metric.summarize(rows)
    assert data["assigned_tasks"] == 3 and data["independent_families"] == 2
    p = data["pairs"]["L5"]
    assert p["only_l1m_certified"] == 1 and p["only_other_certified"] == 2
    assert p["net_certified_other_minus_l1m"] == 1
    assert p["latent_net_other_minus_l1m_bounds"] == [0, 1]
    assert p["all_five_no_original_counted_as_failed_net_bounds"] == [1, 1]
    assert p["paired_states_l1m_rows_other_columns"]["missing"]["pass"] == 1
    assert p["certified_difference_cluster_ci95"] == [0, 1]
    assert data["pairs"]["L6"]["certified_difference_cluster_ci95"] is None
    assert metric.summarize(list(reversed(rows))) == data


def test_no_missing_result_silently_counted_as_fail(metric):
    row = {
        "task": "a",
        "family": "x",
        "L1-M": "pass",
        "L5": "false",
        "L6": "pass",
        "first_common": False,
        "initial_status": "accepted",
        "eligibility": "awaiting_first_repair",
    }
    with pytest.raises(ValueError):
        metric.summarize([row])
    row["L5"] = "fail"
    with pytest.raises(ValueError):
        metric.summarize([row, row])
