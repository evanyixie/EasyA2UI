import json
from pathlib import Path

import pytest


@pytest.fixture
def analysis(monkeypatch):
    studies = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(studies.parents[1]))
    monkeypatch.syspath_prepend(str(studies))
    from six_arms import repair_content_yield

    return repair_content_yield


def card(*text):
    leaves = [
        {"id": f"t{i}", "component": "Text", "content": v} for i, v in enumerate(text)
    ]
    nodes = [
        {"id": "root", "component": "Column", "children": [n["id"] for n in leaves]},
        *leaves,
    ]
    return json.dumps(
        [
            {"createSurface": {"surfaceId": "s"}},
            {"updateComponents": {"surfaceId": "s", "components": nodes}},
            {"updateDataModel": {"surfaceId": "s", "path": "/", "value": {}}},
        ]
    ).encode()


def test_inclusive_coverage_threshold_and_numeric_sources(analysis):
    facts = {"10", "20", "30", "40", "50"}
    raw = card("a:10", "b:20", "c:30", "d:40", "e:88")
    s = analysis.content_scores(raw, facts, "88", {})
    assert (s["coverage"], s["fidelity"], s["numeric_total"]) == (
        "at_least_80",
        "all_sourced",
        5,
    )
    assert analysis.joint("pass", s["coverage"], s["fidelity"]) == "pass"
    bad = analysis.content_scores(raw, facts, "", {})
    assert analysis.joint("pass", bad["coverage"], bad["fidelity"]) == "fail"
    low = analysis.content_scores(card("a:10", "b:20", "c:30"), facts, "", {})
    assert low["coverage"] == "below_80"
    assert analysis.joint("missing", low["coverage"], low["fidelity"]) == "fail"


def test_empty_numeric_unknown_and_known_negative(analysis):
    no_numbers = analysis.content_scores(card("blue"), {"blue"}, "", {})
    assert no_numbers["numeric_total"] == 0 and no_numbers["fidelity"] == "empty_data"
    assert (
        analysis.joint("pass", no_numbers["coverage"], no_numbers["fidelity"])
        == "missing"
    )
    assert (
        analysis.joint("fail", no_numbers["coverage"], no_numbers["fidelity"]) == "fail"
    )
    for raw, facts in (
        (None, {"blue"}),
        (b"invalid", {"blue"}),
        (card("20"), None),
        (card("20"), set()),
    ):
        s = analysis.content_scores(raw, facts, "20", {})
        assert s["coverage"] == "unassessed"
        assert analysis.joint("missing", s["coverage"], s["fidelity"]) == "missing"


def test_no_missing_meter_imputation_and_failed_cost_in_numerator(analysis):
    records = [
        {"tokens": 60, "joint": "pass"},
        {"tokens": 40, "joint": "fail"},
        {"tokens": None, "joint": "pass"},
    ]
    out = analysis.costs(records)
    assert (
        out["assigned"],
        out["fully_metered_tasks"],
        out["certified_on_those_tasks"],
    ) == (3, 2, 1)
    assert out["tokens_per_certified_on_fully_metered_tasks"] == 100
    assert (
        analysis.costs([records[1]])["tokens_per_certified_on_fully_metered_tasks"]
        is None
    )


def test_same_task_3_by_3_and_common_metered_cohort(analysis):
    rows = []

    def seat(technical, tokens):
        return {
            "sha": "a",
            "technical": technical,
            "coverage": "at_least_80",
            "coverage_state": "measured",
            "covered": 1,
            "references": 1,
            "fidelity": "all_sourced",
            "supported": 1,
            "numeric_total": 1,
            "joint": technical,
            "tokens": tokens,
        }

    for i in range(3):
        r = {
            "task": str(i),
            "family": str(i // 2),
            **{k: seat("pass", 10) for k in analysis.STRATEGIES},
        }
        rows.append(r)
    rows[0]["L1-M"] = seat("missing", None)
    rows[1]["L5"] = seat("fail", 20)
    d = analysis.summarize(rows)
    mat = d["pairs"]["L5"]["states_l1m_rows_comparator_columns"]
    assert mat["pass"]["pass"] == mat["missing"]["pass"] == mat["pass"]["fail"] == 1
    group = d["token_cost"]["same_tasks_complete_usage_for_all_five"]
    assert group["L1-M"]["assigned"] == group["L5"]["assigned"] == 2
    assert group["L5"]["tokens_per_certified_on_fully_metered_tasks"] == 30
    extra = analysis.paired(rows, "L5", baseline="L6")
    assert extra["states_l6_rows_l5_columns"]["pass"]["fail"] == 1
    assert extra["certified_difference_rate_l5_minus_l6"] == -1 / 3
    assert extra["latent_difference_rate_bounds_l5_minus_l6"] == [-1 / 3, -1 / 3]
    assert (
        d["l1m_initial_to_terminal"]["different_coverage_or_numeric_counts_or_status"]
        == 0
    )
