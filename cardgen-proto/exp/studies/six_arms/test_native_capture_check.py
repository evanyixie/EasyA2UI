import hashlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def audit(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import native_capture_check

    return native_capture_check


def save(folder, name, value):
    raw = value if isinstance(value, bytes) else json.dumps(value).encode()
    (folder / name).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def example(tmp_path):
    surface = {"surfaceId": "card"}
    handler = {"call": "open", "args": {"id": 7}}
    leaves = [
        {"id": "value", "component": "Text", "content": {"path": "/n"}},
        {"id": "action", "component": "Button", "label": "Open", "onClick": [handler]},
    ]
    group = {"id": "root", "component": "Column", "children": ["value", "action"]}
    messages = [
        {"createSurface": surface},
        {
            "updateComponents": {
                **surface,
                "root": "root",
                "components": [group, *leaves],
            }
        },
        {"updateDataModel": {**surface, "path": "/", "value": {"n": 0}}},
    ]
    raw = b"\n".join(json.dumps(m).encode() for m in messages)
    sha = save(tmp_path, "source", raw)
    save(tmp_path, "received-input.jsonl", raw)
    rows = [
        {
            "attributes": {
                "id": leaf["id"],
                "type": leaf["component"],
                "text": label,
                "visible": "true",
                "bounds": box,
                "origBounds": box,
            }
        }
        for leaf, label, box in zip(
            leaves, ["0", "Open"], ["[0,0][20,10]", "[0,10][20,25]"], strict=True
        )
    ]
    tree = {
        "attributes": {"id": "a2ui_capture_root", "bounds": "[0,0][100,100]"},
        "children": rows,
    }
    tree_sha = save(tmp_path, "native-layout.json", tree)
    receipt = {
        "status": "captured",
        "task": "x",
        "arm": "A",
        "run_id": "run",
        "vp": [150, 150],
        "input_sha256": sha,
        "input_return_sha256": sha,
        "tree_sha256": tree_sha,
        "screenshot_sha256": save(tmp_path, "card.png", b"sealed-image"),
        "terminal": {
            "runId": "run",
            "widthVp": 150,
            "heightVp": 150,
            "cropPx": {"left": 0, "top": 0, "width": 100, "height": 100},
        },
    }
    content = {
        "title": "",
        "size": "2x2",
        "items": [{"id": "n", "path": "/n", "text": "0"}],
        "actions": [{"id": "open", "label": "Open", "handler": handler}],
    }
    row = {
        "task": "x",
        "arm": "A",
        "source": "source",
        "source_sha256": sha,
        "content": "content.json",
        "content_sha256": save(tmp_path, "content.json", content),
        "registry": "registry.json",
        "registry_sha256": save(
            tmp_path, "registry.json", {"id": "x", "binding_samples": {"/n": 0}}
        ),
        "receipt": "receipt.json",
        "receipt_sha256": save(tmp_path, "receipt.json", receipt),
    }
    return row, content, leaves, receipt, tree


def test_shared_edges_are_not_overlap(tmp_path, audit, example):
    result = audit.audit(example[0], tmp_path)
    assert result["state"] == "matched_control_evidence"
    assert len(result["leaves"]) == 2 and not result["overlaps"]


def test_duplicate_target_and_button_arguments_are_retained(audit, example):
    _, content, leaves, _, _ = example
    content["items"].append({"id": "n2", "path": "/n", "text": "0"})
    assert audit.targets(content, leaves) == "missing_selected_binding_or_button"
    del content["items"][1]
    leaves[1]["onClick"] = [{"call": "open", "args": {"id": 8}}]
    assert audit.targets(content, leaves) == "missing_selected_binding_or_button"


def test_visible_overlap_and_original_spill(tmp_path, audit, example):
    row, _, _, receipt, tree = example
    tree["children"][1]["attributes"].update(
        bounds="[0,9][20,25]", origBounds="[-1,9][20,25]"
    )
    receipt["tree_sha256"] = save(tmp_path, "native-layout.json", tree)
    row["receipt_sha256"] = save(tmp_path, "receipt.json", receipt)
    result = audit.audit(row, tmp_path)
    assert result["state"] == "observed_difference"
    assert result["overlaps"] == [["value", "action"]]
    assert result["leaves"][1]["geometry"] == "outside"


def test_missing_and_mismatched_evidence(tmp_path, audit, example):
    row, _, _, _, _ = example
    (tmp_path / "native-layout.json").unlink()
    assert audit.audit(row, tmp_path)["reason"] == "missing_sealed_tree"
    with pytest.raises(ValueError, match="Wrong capture assignment"):
        audit.audit({**row, "arm": "B"}, tmp_path)
    with pytest.raises(ValueError, match="Hash mismatch"):
        audit.audit({**row, "registry_sha256": "bad"}, tmp_path)


def test_unverified_text_regrouping_is_not_a_loss(audit, example):
    _, content, leaves, _, _ = example
    content["items"][0]["label"] = "Count"
    assert audit.targets(content, leaves) == "unresolved_leaf_contract"
