import itertools
import json
from pathlib import Path

import pytest


@pytest.fixture
def metric(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import formal_repeated_values

    return formal_repeated_values


def card(*texts, button=""):
    leaves = [
        {"id": f"t{i}", "component": "Text", "content": text}
        for i, text in enumerate(texts)
    ]
    leaves.append({"id": "b", "component": "Button", "label": button})
    root = {"id": "root", "component": "Column", "children": [n["id"] for n in leaves]}
    return json.dumps(
        [
            {"createSurface": {"surfaceId": "s"}},
            {
                "updateComponents": {
                    "surfaceId": "s",
                    "root": "root",
                    "components": [root, *leaves],
                }
            },
            {"updateDataModel": {"surfaceId": "s", "value": {"v": "68%"}}},
        ]
    )


def test_reference_values_per_card_once_and_location_partition(metric):
    r = metric.score(
        card("68% 68%", {"path": "/v"}, "晴 晴", "气", "温", "气温", button="晴 晴"),
        {"68%", "晴", "气温"},
    )
    assert r["all_values"] == {
        "reference_values": 3,
        "duplicated": 3,
        "within_only": 1,
        "across_only": 0,
        "both": 1,
        "joined_only": 1,
    }
    assert r["strict_numeric"] == r["digit_values"]
    assert r["strict_numeric"]["both"] == 1
    assert (
        metric.score(card("晴", button="晴"), {"晴"})["all_values"]["duplicated"] == 0
    )


def test_distinct_original_spellings_and_semantically_separate_paths(metric):
    facts = metric.content.reference_facts(
        {"left": "68%", "right": "68%", "other": "６８％"}
    )
    assert len(facts) == 2
    result = metric.score(card("68%", "６８％"), facts)
    for grp in metric.GROUPS:
        assert result[grp]["across_only"] == result[grp]["duplicated"] == 2


@pytest.mark.parametrize(
    "text,bad",
    [
        ("15 15", "5"),
        ("5% 5%", "5"),
        ("1,234 和 1,234", "234"),
        ("−5 −5", "5"),
        ("− 5 − 5", "5"),
        ("A5 A5", "5"),
        ("5GHz 5GHz", "5"),
        ("55汉字 55汉字", "55"),
        ("Q5 和 Q5", "Q5"),
        ("243元 243元", "43元"),
        ("1.5 1.5", "5"),
    ],
)
def test_substrings_and_non_numeric_labels_only_in_legacy(metric, text, bad):
    result = metric.score(card(text), {bad})
    assert result["digit_values"]["duplicated"] == 1
    assert result["strict_numeric"]["duplicated"] == 0


def test_strict_recognizes_equal_tokens_without_cross_node_numeric_fusion(metric):
    r = metric.score(
        card("电量６８％，电量68%", "剩余68%", "7", "2", "72"), {"68%", "72"}
    )
    assert r["strict_numeric"]["both"] == r["strict_numeric"]["duplicated"] == 1
    assert r["all_values"]["joined_only"] == 1
    r = metric.score(card("72", "下一条", "72"), {"72"})
    assert r["strict_numeric"]["across_only"] == 1


def test_unknown_empty_no_output_and_button_only_are_distinguishable(metric):
    labels = [
        metric.score(None, {"75"}),
        metric.score(card("项目"), None),
        metric.score(card(), {}),
        metric.score(card({"path": "/missing"}), {"75"}),
        metric.score(card(button="75 75"), {"75"}),
        metric.score(card("项目"), {"项目"}),
    ]
    assert [x["status"] for x in labels] == [
        "no_artifact",
        "missing_reference",
        "empty_reference",
        "unresolved_text",
        "measured",
        "measured",
    ]
    panel = metric.summarize(labels)
    assert panel["assigned"] == 6 and panel["states"]["measured"] == 2
    assert (
        panel["all_values"]["reference_values"] == 2
        and panel["all_values"]["duplicated"] == 0
    )
    assert panel["strict_numeric"]["cards_with_reference_values"] == 1


def test_normalized_occurrence_localization_matches_frozen_checker(metric):
    facts = {"1", "11", "１２", "A", "1A", "12%"}
    pieces = ("", "1", "11", "２", "A", "1 A", "12％")
    for nodes in itertools.product(pieces, repeat=3):
        row = metric.score(card(*nodes), facts)
        expected = metric.measure.check_content(
            "\n".join(nodes), [{"value": s} for s in facts]
        )
        assert row["all_values"]["duplicated"] == expected["duplicated"]
        for grp in metric.GROUPS:
            assert (
                sum(row[grp][key] for key in metric.LOCATIONS) == row[grp]["duplicated"]
            )
