import json
from pathlib import Path

import pytest


@pytest.fixture
def metric(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import formal_font_size

    return formal_font_size


@pytest.mark.parametrize(
    ("fonts", "expected"),
    [
        ([], (None, None)),
        ([12, 15], (12, 12)),
        ([9, None], (9, None)),
        ([None], (None, None)),
    ],
)
def test_display_minimum_can_require_two_kinds_of_node(metric, fonts, expected):
    def panel(values):
        sizes = [value for value in values if value is not None]
        return {
            "min_font": min(sizes, default=None),
            "missing": values.count(None),
            "invalid": 0,
        }

    result = {
        "status": "measured",
        "text": panel(fonts[:1]),
        "button": panel(fonts[1:]),
    }
    assert metric.minima(result) == expected
    assert metric.minima({"status": "unresolved_tree"}) == (None, None)


def test_only_three_message_reference_array_is_transcribed(metric):
    messages = [
        {"createSurface": {}},
        {"updateComponents": {"components": []}},
        {"updateDataModel": {}},
    ]
    source = json.dumps(messages).encode()
    rewritten, changed = metric.reference_for_c05(source)
    assert changed and [json.loads(line) for line in rewritten.splitlines()] == messages
    for raw in [None, b"invalid", rewritten, b"[]", b'[{}, {}, "not a message"]']:
        assert metric.reference_for_c05(raw) == (raw, False)
