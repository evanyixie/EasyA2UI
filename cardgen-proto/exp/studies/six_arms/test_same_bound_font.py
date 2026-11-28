import itertools
import json
from pathlib import Path

import pytest


@pytest.fixture
def metric(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import same_bound_font

    return same_bound_font


def card(nodes, data, *, parent="/", detached=False):
    leaves = [
        {"id": str(i), "component": kind, key: value, "styles": {"fontSize": size}}
        for i, (kind, key, value, size) in enumerate(nodes)
    ]
    children = [n["id"] for n in leaves]
    root = {
        "id": "group",
        "component": "Column",
        "children": children[:-1] if detached else children,
    }
    return json.dumps(
        [
            {"createSurface": {"surfaceId": "s"}},
            {"updateComponents": {"surfaceId": "s", "components": [root, *leaves]}},
            {"updateDataModel": {"surfaceId": "s", "path": parent, "value": data}},
        ]
    ).encode()


def bound(path, fp):
    return ("Text", "content", {"path": path}, fp)


def test_match_uses_exact_display_path_and_only_reachable_text(metric):
    raw = card(
        [
            bound("/d/items/0/name", 14),
            ("Text", "content", " {{ ${/d/day} }} ", 16),
            ("Text", "content", "7", 32),
            ("Button", "label", {"path": "/d/day"}, 80),
            bound("/d/wrong", 18),
            bound("/d/empty", 14),
            bound("/d/unregistered", 14),
            bound("/d/custom~1key", 12),
        ],
        {
            "items": [{"name": "Alpha"}],
            "day": 7,
            "wrong": "different",
            "empty": " ",
            "unregistered": "Alpha",
            "custom/key": 0,
        },
        parent="/d",
    )
    result = metric.match_inputs(
        raw,
        {
            "/d/items/0/name": "Alpha",
            "/d/day": 7,
            "/d/wrong": "expected",
            "/d/empty": " ",
            "/d/custom~1key": 0,
        },
    )
    assert result["fields"] == {
        "/d/items/0/name": ("Alpha", 14),
        "/d/day": ("7", 16),
        "/d/custom~1key": ("0", 12),
    }
    assert result["referenced"] == {*result["fields"], "/d/wrong", "/d/empty"}
    assert metric.match_inputs(None, {})["status"] == "no_artifact"
    assert (
        metric.match_inputs(card([bound("/n", 14)], {"n": 7}, detached=True), {})[
            "status"
        ]
        == "unresolved_tree"
    )


@pytest.mark.parametrize(
    "other",
    [
        {"path": "/n"},
        "{{ ${/n} + ' h' }}",
        "{{ ${/n} * 2 }}",
        {"path": "/n", "fallback": 0},
    ],
)
def test_path_with_second_occurrence_is_excluded_even_when_unmeasurable(metric, other):
    nodes = [bound("/n", 16), ("Text", "content", other, None)]
    row = metric.match_inputs(card(nodes, {"n": 7}), {"/n": 7})
    assert row == {"status": "measured", "referenced": {"/n"}, "fields": {}}


@pytest.mark.parametrize("fp", [None, True, 0, -2, "12", float("inf")])
def test_font_must_be_declared_positive_finite_numeric(metric, fp):
    assert not metric.match_inputs(card([bound("/n", fp)], {"n": 7}), {"/n": 7})[
        "fields"
    ]


def test_compound_is_not_a_pure_path_even_if_it_renders_identical_text(metric):
    row = metric.match_inputs(
        card([("Text", "content", "{{ ${/n} + '' }}", 16)], {"n": 7}), {"/n": 7}
    )
    assert row["referenced"] == {"/n"} and not row["fields"]


def test_aggregate_denominators_directions_and_no_identifying_values(metric):
    def match(entries):
        vals = {p: p for p, _ in entries}
        return metric.match_inputs(
            card([bound("/" + p, v) for p, v in entries], vals),
            {"/" + p: p for p, _ in entries},
        )

    before = match([("secret_one", 12), ("secret_two", 16), ("three", 12)])
    after = match([("secret_one", 16), ("secret_two", 12), ("another", 12)])
    other = match([("another", 12)])
    missing = metric.match_inputs(None, {})
    keys = itertools.product(
        ("q_secret", "q_missing", "q_other"), metric.ARMS, metric.PHASES
    )
    seats = {key: before for key in keys}
    for p in metric.PHASES:
        seats["q_secret", "L5", p] = after
        seats["q_missing", "L5", p] = missing
        seats["q_other", "L5", p] = other
    seats["q_secret", "L4", metric.PHASES[1]] = after
    rep = metric.paired_report(seats)
    selected = rep["between"][metric.PHASES[0]]["L4_to_L5"]
    assert selected["assigned_task_pairs"] == 3 and selected["both_trees_assessed"] == 2
    assert selected["tasks_with_matched_fields"] == 1
    assert selected["matched_task_rate_assigned"] == 1 / 3
    assert selected["union_referenced_paths_on_assessed_pairs"] == 8
    assert (
        selected["shared_referenced_paths_on_assessed_pairs"]
        == selected["matched_field_pairs"]
        == 2
    )
    assert selected["matched_rate_shared_paths"] == 1
    assert selected["fields"] == {"larger": 1, "equal": 0, "smaller": 1}
    assert selected["tasks"] == {
        "mixed": 1,
        "all_equal": 0,
        "only_larger": 0,
        "only_smaller": 0,
    }
    assert rep["first_to_final"]["L4"]["tasks"]["mixed"] == 1
    for label in ("secret_one", "secret_two", "q_secret"):
        assert label not in json.dumps(rep)
    seats.pop(next(iter(seats)))
    with pytest.raises(ValueError, match="complete"):
        metric.paired_report(seats)


def test_same_value_different_field_or_same_field_changed_value_does_not_pair(metric):
    raw_a = card([bound("/a", 16), bound("/k", 20)], {"a": 5, "k": "first"})
    raw_b = card([bound("/b", 12), bound("/k", 10)], {"b": 5, "k": "next"})
    a = metric.match_inputs(raw_a, {"/a": 5, "/k": "first"})
    b = metric.match_inputs(raw_b, {"/b": 5, "/k": "next"})
    summary = metric._pairs([(a, b)])
    assert summary["shared_referenced_paths_on_assessed_pairs"] == 1
    assert summary["matched_field_pairs"] == 0
