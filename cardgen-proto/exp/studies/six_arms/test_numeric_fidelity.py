import json
from pathlib import Path

import pytest


@pytest.fixture
def metric(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import numeric_fidelity

    return numeric_fidelity


def card(*texts, samples=None, button_label=None):
    nodes = [
        {"component": "Text", "id": f"t{i}", "content": text}
        for i, text in enumerate(texts)
    ]
    if button_label is not None:
        nodes.append({"component": "Button", "id": "btn", "label": button_label})
    root = {"component": "Row", "id": "root", "children": [n["id"] for n in nodes]}
    return json.dumps(
        [
            {"createSurface": {"surfaceId": "s"}},
            {"updateComponents": {"surfaceId": "s", "components": [root, *nodes]}},
            {"updateDataModel": {"surfaceId": "s", "value": samples or {}}},
        ]
    )


def test_original_support_and_mutually_exclusive_sources(metric):
    result = metric.score(
        card("68%", "7步", "3小时", "80%"),
        {"68%", "3小时"},
        "请显示7步、3小时",
        {"/sample": "80%"},
    )
    assert result == {
        "status": "measured",
        "total": 4,
        "supported": 3,
        "fact_only_supported": 1,
        "query_only_supported": 1,
        "both_supported": 1,
        "strict_supported": 3,
        "snapshot_supported_extra": 1,
    }


def test_reverse_query_match_is_attributed_to_query_only(metric):
    got = metric.score(card("5天"), set(), "5", {})
    assert (
        got["total"],
        got["supported"],
        got["query_only_supported"],
        got["strict_supported"],
    ) == (1, 1, 1, 0)


def test_unknown_artifact_versus_known_nonnumeric_card(metric):
    for raw, state in [
        (None, "no_artifact"),
        (b"incomplete", "unresolved_text"),
        (card({"path": "/missing"}), "unresolved_text"),
    ]:
        got = metric.score(raw, None, "", {})
        assert got["status"] == state
        assert all(got[k] is None for k in metric.COUNT_FIELDS)
    got = metric.score(card("健康", button_label="7次"), None, "", {})
    assert got["status"] == "empty_data"
    assert all(got[k] == 0 for k in metric.COUNT_FIELDS)


def test_known_empty_reference_can_use_query_unavailable_reference_cannot(metric):
    known = metric.score(card("0步"), {}, "0步", {})
    assert (known["total"], known["supported"], known["query_only_supported"]) == (
        1,
        1,
        1,
    )
    unknown = metric.score(card("0步"), None, "0步", {})
    assert unknown["status"] == "missing_reference" and unknown["total"] == 1
    assert all(unknown[k] is None for k in metric.COUNT_FIELDS if k != "total")


def test_resolve_first_frame_and_deduplicate_across_controls(metric):
    raw = card({"path": "/rate"}, "68 %", "68%", "0", samples={"rate": "68 %"})
    got = metric.score(raw, {"68%"}, "", {"/first": 0, "/second": 0, "/bool": False})
    assert (
        got["total"],
        got["supported"],
        got["strict_supported"],
        got["snapshot_supported_extra"],
    ) == (2, 1, 1, 1)


def test_entity_mismatch_still_counts_only_a_value_match(metric):
    wrong = card("乙的脉搏90", button_label="返回")
    got = metric.score(wrong, set(), "", {"/person/a/pulse": 90})
    assert (got["supported"], got["snapshot_supported_extra"]) == (0, 1)
    assert set(got) == {"status", *metric.COUNT_FIELDS}


@pytest.mark.parametrize("sample", ["25°C", "最高25°C / 30°C", "25 °C"])
def test_registration_uses_exact_unit_bearing_tokens(metric, sample):
    got = metric.score(card("25°C", "25", "5°C"), set(), "", {"/weather": sample})
    assert (got["total"], got["supported"], got["snapshot_supported_extra"]) == (
        3,
        0,
        1,
    )


@pytest.mark.parametrize("sample", ["168%", "8", "68", "68元", False, {"value": "68%"}])
def test_no_partial_digit_wrong_unit_or_path_name_match(metric, sample):
    got = metric.score(card("68%"), set(), "", {"/device/68%/value": sample})
    assert got["snapshot_supported_extra"] == 0


@pytest.mark.parametrize(
    ("shown", "original"),
    [
        ("234", "1,234"),
        ("100", "-100"),
        ("5", "−5"),
        ("5", "5%"),
        ("5", "5 kg"),
        ("5", "5公斤"),
        ("2.3", "1.2.3"),
        ("200", "6，200"),
        ("70", "P70"),
        ("60", "Mate60Pro"),
        ("0", "HOP-AL00"),
    ],
)
def test_unparsed_fragments_are_not_strict_matches(metric, shown, original):
    registered = metric.score(card(shown), set(), "", {"/sample": original})
    assert registered["snapshot_supported_extra"] == 0
    referenced = metric.score(card(shown), {original}, "", {})
    assert referenced["strict_supported"] == 0


def test_dates_and_clock_times_count_separately_without_partial_matches(metric):
    got = metric.score(
        card("2026-03-01", "14:20", "20"), set(), "", {"/sentence": "2026-03-01 14:20"}
    )
    assert (got["total"], got["snapshot_supported_extra"]) == (3, 2)


def test_exact_boundaries_do_not_continue_into_another_text(metric):
    got = metric.score(card("72", "其他说明"), {"72"}, "", {})
    assert (got["total"], got["strict_supported"]) == (1, 1)
    # The historical joined-text regex consumes a unit across the newline.
    # The standalone token must not be credited to that different denominator.
    across = metric.score(card("72", "天"), {"72"}, "", {})
    assert (across["total"], across["supported"], across["strict_supported"]) == (
        1,
        1,
        0,
    )
