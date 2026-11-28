import json
from pathlib import Path

import pytest


@pytest.fixture
def evidence(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import alarm_tab_evidence

    return alarm_tab_evidence


def button_tree(bounds, *, visible=True, duplicates=1):
    button = {
        "id": "test-action",
        "type": "Button",
        "text": "Test",
        "bounds": bounds,
        "origBounds": bounds,
        "enabled": "true",
        "clickable": "true",
        "visible": "true" if visible else "false",
    }
    return json.dumps(
        {
            "attributes": {"id": "a2ui_capture_root", "bounds": "[0,0][100,100]"},
            "children": [{"attributes": button} for _ in range(duplicates)],
        }
    )


def test_hit_requires_one_visible_uncropped_button_with_matching_label(evidence):
    hit_center = evidence.hit_center
    target = {"id": "test-action", "label": "Test"}
    crop = (0, 0, 100, 100)
    assert hit_center(button_tree("[10,20][80,50]"), target, crop) == [45, 35]
    assert hit_center(button_tree("[10,20][120,50]"), target, crop) is None
    assert (
        hit_center(button_tree("[10,20][80,50]", visible=False), target, crop) is None
    )
    assert hit_center(button_tree("[10,20][80,50]", duplicates=2), target, crop) is None
    assert (
        hit_center(button_tree("[10,20][80,50]"), {**target, "label": "Other"}, crop)
        is None
    )


def test_dispatch_evidence_binds_host_time_target_and_event_order(evidence):
    dispatch_evidence = evidence.dispatch_evidence
    timing = {
        "host_pid": "123",
        "device_before_ms": 1234567890120,
        "sample_end_ms": 1234567890130,
    }
    head = "1234567890.125 123 123 JS: "
    clicked = head + "onClick triggered: componentId=t, handlers=1"
    rejected = head + "local function is not registered: clickToDeeplink"
    assert dispatch_evidence([clicked, rejected], timing, "t")
    assert not dispatch_evidence([rejected, clicked], timing, "t")
    assert not dispatch_evidence([clicked, rejected], timing, "other")
    assert not dispatch_evidence([clicked + "0", rejected], timing, "t")
    with pytest.raises(ValueError, match="Wrong host"):
        dispatch_evidence([clicked.replace(" 123 ", " 234 ", 1), rejected], timing, "t")
    with pytest.raises(ValueError, match="outside"):
        dispatch_evidence([clicked.replace(".125", ".150"), rejected], timing, "t")


def test_transport_and_loss_of_focus_do_not_become_observed_no_launch(evidence):
    classify_focus = evidence.classify_focus
    before = {"is_host": True, "is_clock": False, "focus_pid": "123", "window_id": "9"}
    samples = [{**before, "utc": f"2026-01-01T12:00:0{i}+00:00"} for i in range(4)]
    assert classify_focus(before, samples, "123") == "host_only"
    assert classify_focus(before, samples[:2], "123") == "unknown"
    other = {**samples[-1], "is_host": False, "focus_pid": "456"}
    assert classify_focus(before, [*samples[:3], other], "123") == "unknown"
    assert (
        classify_focus(before, [*samples[:3], {**other, "is_clock": True}], "123")
        == "clock_foreground"
    )
    with pytest.raises(ValueError, match="out of order"):
        classify_focus(before, list(reversed(samples)), "123")
