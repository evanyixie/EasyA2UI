"""检查审计器边界，防止自身制造‘全通过’。"""

import json

import pytest

from audit_common import graph_evidence, input_view, messages, pointer, write_rows
from p1_artifact import artifact_check


def artifact():
    return [
        {"version": "v0.9", "createSurface": {"surfaceId": "s", "catalogId": "form"}},
        {
            "version": "v0.9",
            "updateComponents": {
                "surfaceId": "s",
                "root": "root",
                "components": [
                    {
                        "id": "root",
                        "component": "Column",
                        "children": ["t", "v"],
                        "styles": {"width": "matchParent", "height": "matchParent"},
                    },
                    {"id": "t", "component": "Text", "content": "活动名称"},
                    {"id": "v", "component": "Text", "content": "{{ ${/data/value} }}"},
                ],
            },
        },
        {
            "version": "v0.9",
            "updateDataModel": {
                "surfaceId": "s",
                "path": "/",
                "value": {"data": {"value": "完整时间"}},
            },
        },
    ]


@pytest.mark.parametrize("mode", ["array", "jsonl", "concatenated"])
def test_normalization_preserves_all_original_objects(tmp_path, mode):
    original = artifact()
    path = tmp_path / "source.jsonl"
    separator = "\n" if mode == "jsonl" else ""
    text = (
        json.dumps(original)
        if mode == "array"
        else separator.join(map(json.dumps, original))
    )
    path.write_text(text, "utf8")
    assert messages(path) == original
    output = tmp_path / "normalized.jsonl"
    write_rows(output, messages(path))
    assert messages(output) == original
    assert path.read_text("utf8") == text


def test_duplicate_json_keys_are_not_silently_repaired(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text('{"version":"v0.9","version":"other"}', "utf8")
    with pytest.raises(ValueError, match="duplicate"):
        messages(path)


def test_pointer_preserves_zero_false_and_escaped_keys():
    model = {"a/b": {"~": [0, False]}}
    assert pointer(model, "/a~1b/~0/0") == 0
    assert pointer(model, "/a~1b/~0/1") is False
    with pytest.raises(ValueError):
        pointer(model, "/a~1b/~0/2")


@pytest.mark.parametrize("change", ["cycle", "unreachable", "missing", "duplicate"])
def test_bad_graph_is_rejected(change):
    update = artifact()[1]["updateComponents"]
    if change == "cycle":
        update["components"][1]["children"] = ["root"]
    elif change == "unreachable":
        update["components"][0]["children"] = ["t"]
    elif change == "missing":
        update["components"][0]["children"].append("absent")
    else:
        update["components"].append({"id": "v", "component": "Text"})
    with pytest.raises(ValueError):
        graph_evidence(update)


def test_input_view_preserves_business_preferences_and_nested_action_parameters():
    content = {
        "userQuery": "红色背景显示时间",
        "size": "2x2",
        "backgroundPreference": "红色",
        "bundleName": "outer.transport",
        "candidateEventCandidates": [
            {"action": {"args": {"bundleName": "real.action"}}}
        ],
    }
    raw = {
        "content": content,
        "deviceInfo": {"phone": "x"},
        "session": {"id": "private"},
    }
    view, query, evidence = input_view(raw)
    assert query == content["userQuery"]
    assert view["backgroundPreference"] == "红色"
    assert (
        view["candidateEventCandidates"][0]["action"]["args"]["bundleName"]
        == "real.action"
    )
    assert "bundleName" not in view and "deviceInfo" not in view
    assert evidence["semantic_filtering"] is False
    assert raw["content"] == content


def test_conflicting_duplicate_business_fields_require_review():
    view, _, evidence = input_view(
        {"content": {"userQuery": "原始"}, "userQuery": "被改写"}
    )
    assert view["userQuery"] == "原始"
    assert evidence["conflicting_business_fields"] == ["userQuery"]


def test_match_parent_keeps_geometry_unknown_not_zero(tmp_path):
    path = tmp_path / "a2ui.jsonl"
    write_rows(path, artifact())
    checks, details, _ = artifact_check(path, "2x2")
    assert all(check["status"] == "pass" for check in checks)
    assert details["host_size_vp"] is None
    assert details["physical_geometry_status"] == "not_measured"


def test_unresolved_binding_is_not_a_success(tmp_path):
    value = artifact()
    value[2]["updateDataModel"]["value"] = {}
    path = tmp_path / "a2ui.jsonl"
    write_rows(path, value)
    checks, _, _ = artifact_check(path, "2x2")
    result = next(check for check in checks if check["code"] == "P1_C3_BINDINGS")
    assert result["status"] == "fail"
    assert result["evidence"]["unresolved"][0]["path"] == "/data/value"


def test_non_root_data_update_stays_unknown(tmp_path):
    value = artifact()
    value[2]["updateDataModel"]["path"] = "/data"
    path = tmp_path / "a2ui.jsonl"
    write_rows(path, value)
    checks, _, _ = artifact_check(path, "2x2")
    result = next(check for check in checks if check["code"] == "P1_C3_BINDINGS")
    assert result["status"] == "unknown"
