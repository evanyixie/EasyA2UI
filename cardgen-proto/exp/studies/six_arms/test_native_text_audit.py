import json
from pathlib import Path

import pytest

RECT = (4, 6, 104, 106)
CONTENT = "{{ '剩余 ' + ${/data/count} + ' 项' }}"
LEAF = {"id": "v", "component": "Text", "content": CONTENT}
CONTROL = {
    "id": "v",
    "type": "Text",
    "text": "剩余 0 项",
    "visible": "true",
    "bounds": "[6,8][50,32]",
}
DATA = {"data": {"count": 0}}
SAMPLES = {"/data/count": 0}


@pytest.fixture
def audit(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import native_text_audit

    return native_text_audit


def test_reads_registered_first_frame_and_native_text(audit):
    classify = audit.classify
    assert classify(LEAF, [CONTROL], RECT, DATA, SAMPLES) == ("match", True)
    assert classify(LEAF, [{**CONTROL, "text": ""}], RECT, DATA, SAMPLES) == (
        "native_text_differs",
        True,
    )
    assert classify(LEAF, [CONTROL], RECT, {"data": {"count": 1}}, SAMPLES) == (
        "emitted_sample_differs",
        True,
    )
    assert classify(LEAF, [CONTROL], RECT, DATA, {}) == ("unregistered_sample", True)
    assert classify(LEAF, [CONTROL], RECT, {}, SAMPLES) == ("unresolved_sample", True)


@pytest.mark.parametrize(
    "controls", [[], [CONTROL, CONTROL], [{**CONTROL, "type": "Button"}]]
)
def test_missing_or_ambiguous_match_is_unknown(audit, controls):
    classify = audit.classify
    assert (
        classify(LEAF, controls, RECT, DATA, SAMPLES)[0] == "no_unique_native_control"
    )


def test_offscreen_and_unhandled_expression_are_unknown(audit):
    classify = audit.classify
    assert (
        classify(LEAF, [{**CONTROL, "bounds": "[105,0][206,40]"}], RECT, DATA, SAMPLES)[
            0
        ]
        == "no_visible_control_box"
    )
    assert (
        classify(
            {**LEAF, "content": "{{ upper(${/data/count}) }}"},
            [CONTROL],
            RECT,
            DATA,
            SAMPLES,
        )[0]
        == "unresolved_expression"
    )
    assert (
        classify({**LEAF, "content": "${/data/count}"}, [CONTROL], RECT, DATA, SAMPLES)[
            0
        ]
        == "unresolved_expression"
    )


def test_control_belongs_to_same_card_and_crop(audit):
    node = {"attributes": CONTROL}
    tree = {
        "children": [
            node,
            {
                "attributes": {"id": "a2ui_capture_root", "bounds": "[4,6][104,106]"},
                "children": [node],
            },
        ]
    }
    assert audit.control_index(tree, RECT)["v"] == [CONTROL]
    assert not audit.control_index(tree, (0, 0, 100, 100))


def test_missing_dump_leaves_unjudged(tmp_path, audit):
    src = [
        {"createSurface": {}},
        {"updateComponents": {"root": "v", "components": [LEAF]}},
        {"updateDataModel": {"value": DATA}},
    ]
    record = audit.observe(
        tmp_path,
        {"terminal": {"cropPx": {"left": 0, "top": 0, "width": 100, "height": 100}}},
        b"\n".join(json.dumps(m).encode() for m in src),
        SAMPLES,
    )
    assert record["state"] == "incomplete" and record["layout_sha256_at_audit"] is None
