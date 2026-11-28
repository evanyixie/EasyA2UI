"""用合成日志检查首帧全分母、警告截断与同次终态对账。"""

import json

import pytest

import evidence as e
import summarize_host_warnings as w


def seat(task, arm, directory=None, state="READY", warnings=None):
    row = {
        "task_id": task,
        "arm": arm,
        "sample_selected": True,
        "capture_status": "no_first_artifact"
        if directory is None
        else "captured_first_frame",
        "generation_status": "absent" if directory is None else "artifact_ready",
    }
    if directory is not None:
        rid = f"private-run-{task}-{arm}"
        term = {"runId": rid, "state": state}
        if warnings is not None:
            term["warnings"] = warnings
        path = directory / task / arm / "capture_receipt.json"
        e.atomic(path, {"run_id": rid, "terminal": term})
        path.with_name("runner.log").write_text(
            "prefix A2UI_RUN " + json.dumps(term), encoding="utf8"
        )
        row["capture_receipt"] = str(path)
    return row


def test_ready_missing_complete_and_partial(tmp_path):
    msg = "Property content contains an invalid expression reference"
    item = {
        "code": "ERROR_CODE_INVALID_VALUE",
        "itemType": "component",
        "itemName": "Text",
        "message": msg,
    }
    other = {**item, "message": "private-value"}
    full = "2001: " + json.dumps(
        {"warnings": [item, other], "type": "schemaWarning", "warningCount": 2}
    )
    prefix = '2001: {"type":"schemaWarning","warningCount":3,"warnings":['
    cut = (
        prefix
        + json.dumps(other)
        + ","
        + json.dumps(item)
        + ',{"code":"ERROR_CODE_INVALID_VALUE","message":"Property content co'
    )
    a, b = e.ARMS
    res = w.summarize(
        [
            seat("one", a, tmp_path),
            seat("one", b),
            seat("two", a, tmp_path, "READY_WITH_WARNINGS", [full, cut]),
            seat("two", b),
        ]
    )
    assert res["assigned_seats"] == 4
    assert res["capture_status_by_arm"][b] == {"no_first_artifact": 2}
    assert res["verified_terminal_images"] == {"READY": 1, "READY_WITH_WARNINGS": 1}
    assert res["warning_message_forms"] == {"complete": 1, "truncated": 1}
    assert res["host_declared_entries_on_verified_images"] == 5
    assert res["declared_entries_without_complete_details"] == 1
    assert res["complete_details"] == {
        "Text.content_invalid_expression_reference": 2,
        "other": 2,
    }
    assert res["truncated_next_codes"] == {"ERROR_CODE_INVALID_VALUE": 1}
    assert res["truncated_next_properties"] == {"content": 1}
    assert "private" not in json.dumps(res)


def test_unknown_packet_and_missing_count(tmp_path):
    a, b = e.ARMS
    res = w.summarize(
        [
            seat(
                "t",
                a,
                tmp_path,
                "READY_WITH_WARNINGS",
                ["other private warning", '2001: {"type":'],
            ),
            seat("t", b, tmp_path, "READY_WITH_WARNINGS"),
        ]
    )
    assert res["warning_message_forms"] == {"unsupported": 1, "unreadable": 1}
    assert res["messages_or_lists_with_unknown_count"] == 3
    assert res["host_declared_entries_on_verified_images"] is None
    assert res["complete_details"] == {}
    assert "private" not in json.dumps(res)


@pytest.mark.parametrize(
    "replacement",
    [
        {"runId": "foreign", "state": "READY"},
        {"runId": "private-run-t-model_model", "state": "READY_WITH_WARNINGS"},
    ],
)
def test_log_must_match_run_and_terminal(tmp_path, replacement):
    a, b = e.ARMS
    captured = seat("t", a, tmp_path)
    (tmp_path / "t" / a / "runner.log").write_text(
        "A2UI_RUN " + json.dumps(replacement), encoding="utf8"
    )
    with pytest.raises(ValueError, match="唯一同次终态"):
        w.summarize([captured, seat("t", b)])
