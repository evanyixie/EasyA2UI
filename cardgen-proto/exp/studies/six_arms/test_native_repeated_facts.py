from pathlib import Path

import pytest


@pytest.fixture
def audit(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import native_repeated_facts

    return native_repeated_facts


BASE = {"/data/x": "68%", "/data/y": "68%"}
DATA = {"data": {"x": "68%", "y": "68%"}}
X = {"path": "/data/x"}
Y = {"path": "/data/y"}


def observations(audit, leaves, *, samples=None, data=None):
    nodes, index = [], {}
    for i, (kind, value, rendered, overrides) in enumerate(leaves):
        key = f"control-{i}"
        prop = "content" if kind == "Text" else "label"
        nodes.append({"id": key, "component": kind, prop: value})
        index[key] = [
            {
                "type": kind,
                "visible": "true",
                "opacity": "1.0",
                "text": rendered,
                "bounds": f"[0,{i * 20}][30,{20 + i * 20}]",
                **overrides,
            }
        ]
    return audit.inspect(
        nodes,
        index,
        (0, 0, 100, 100),
        DATA if data is None else data,
        BASE if samples is None else samples,
    )


def test_same_fact_across_two_disjoint_controls(audit):
    r = observations(
        audit,
        [
            ("Text", X, "68%", {}),
            ("Button", "{{ '电量' + ${/data/x} }}", "电量68%", {}),
        ],
    )
    assert r["state"] == "repeated"
    assert r["confirmed_repeat_paths"] == {"/data/x": ["control-0", "control-1"]}
    assert r["matched_numeric_controls"] == 2


@pytest.mark.parametrize(
    "leaves",
    [
        [("Text", X, "68%", {}), ("Button", Y, "68%", {})],
        [("Text", X, "68%", {}), ("Button", "68%", "68%", {})],
        [("Text", "{{ ${/data/x} + ' ' + ${/data/x} }}", "68% 68%", {})],
    ],
)
def test_equal_strings_or_within_control_are_not_same_fact_across_controls(
    audit, leaves
):
    r = observations(audit, leaves)
    assert r["state"] == "complete_without_repeat" and not r["structural_repeat_paths"]


@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({"visible": "false"}, "no_visible_control_box"),
        ({"opacity": "0"}, "unverified_opacity"),
        ({"bounds": "[0,20][120,45]"}, "partially_outside"),
        ({"bounds": "[0,10][30,30]"}, "overlapping_controls"),
        ({"text": "6…"}, "native_text_differs"),
    ],
)
def test_candidate_needs_two_verified_controls(audit, overrides, expected):
    r = observations(audit, [("Text", X, "68%", {}), ("Button", X, "68%", overrides)])
    assert r["leaf_evidence"]["control-1"]["status"] == expected
    assert r["structural_repeat_paths"] and not r["confirmed_repeat_paths"]
    assert r["state"] == "incomplete_without_confirmed_repeat"


def test_incomplete_card_can_contain_confirmed_repeat(audit):
    r = observations(
        audit,
        [
            ("Text", X, "68%", {}),
            ("Text", X, "68%", {}),
            ("Text", "{{ calc(${/data/x}) }}", "unknown", {}),
        ],
    )
    assert r["state"] == "repeated" and not r["complete"]


def test_numbers_require_identical_typed_registry_values(audit):
    r = observations(
        audit,
        [("Text", X, "0", {}), ("Text", X, "0", {})],
        samples={"/data/x": 0},
        data={"data": {"x": "0"}},
    )
    assert r["state"] == "incomplete_without_confirmed_repeat"
    assert r["leaf_evidence"]["control-0"]["status"] == "registered_value_type_differs"
    assert audit.numeric_paths(X, {"/data/x": "星期三"}) == set()
    assert audit.numeric_paths(X, {"/data/x": "周３"}) == {"/data/x"}
    assert audit.numeric_paths(X, {}) is None


def test_missing_frames_do_not_enter_negative_or_numeric_denominators(audit):
    numeric = observations(audit, [("Text", X, "68%", {}), ("Button", Y, "68%", {})])
    no = {"state": "no_capture", "complete": False, "execution": "stage_rejected"}
    rows = {"first": numeric, "second": no}
    p = audit.paired(rows, {k: numeric for k in rows})
    assert p["assigned"] == 2 and p["both_captured"] == 1
    assert p["complete_with_two_or_more_numeric_controls_both"]["neither"] == 1
    assert audit.describe(list(rows.values()))["no_capture_reasons"] == {
        "stage_rejected": 1
    }
