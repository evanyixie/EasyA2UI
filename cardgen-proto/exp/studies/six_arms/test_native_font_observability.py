import hashlib
import json
from itertools import product
from pathlib import Path

import pytest


@pytest.fixture
def audit(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import native_font_observability

    return native_font_observability


def fixture(audit, root):
    directory = root / "example"
    directory.mkdir()

    def write(name, data):
        raw = json.dumps(data).encode()
        (directory / name).write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    tree = {
        "attributes": {"type": "Row", "bounds": "intentionally private"},
        "children": [
            {
                "attributes": {
                    "type": "Text",
                    "originalText": "This must never appear",
                    "textStyle": {"fontSize": 15},
                },
                "children": [],
            },
            {"attributes": {"type": "Button", "lineHeight": 17}, "children": []},
        ],
    }
    tree_hash = write("native-layout.json", tree)
    receipt = write(
        "receipt.json",
        {
            "task": "secret-id",
            "arm": "L1",
            "input_sha256": "original",
            "input_return_sha256": "original",
            "status": "captured",
            "phases": list(audit.PHASE_LABELS.values()),
            "terminal": {"fontScale": 1.3},
        },
    )
    rows = [
        {
            "task": "secret-id",
            "arm": a,
            "checkpoint": p,
            **(
                {
                    "artifact_sha256": "original",
                    "receipt": "example/receipt.json",
                    "receipt_sha256": receipt,
                    "tree_sha256": tree_hash,
                }
                if a == "L1"
                else {}
            ),
        }
        for a, p in product(audit.ARMS, audit.PHASES)
    ]
    return rows, tree_hash


def test_field_only_scan_keeps_first_and_final_receipt_but_counts_tree_once(
    audit, tmp_path
):
    rows, digest = fixture(audit, tmp_path)
    result = audit._audit(rows, tmp_path, 1)
    assert result["unique_capture_receipts"] == result["unique_tree_contents"] == 1
    assert (
        result["tree_set_sha256_sorted_hex_with_lf"]
        == hashlib.sha256((digest + "\n").encode()).hexdigest()
    )
    for p in audit.PHASES:
        assert result["phases"][p]["L1"] == {
            "assigned": 1,
            "artifact": 1,
            "receipt": 1,
            "tree": 1,
        }
        assert result["phases"][p]["L2"]["tree"] == 0
    assert result["whole_window_nodes_in_unique_trees"] == {"Text": 1, "Button": 1}
    counts = result["field_occurrences"]
    assert counts["native_text_and_button_attributes"]["font_size"] == 1
    assert counts["all_native_node_attributes"]["line_height_or_baseline"] == 1
    assert counts["capture_receipt"]["font_scale"] == 1
    assert "This must never appear" not in json.dumps(
        result
    ) and "secret-id" not in json.dumps(result)


def test_reference_reuse_and_corrupt_tree_are_rejected(audit, tmp_path):
    rows, _ = fixture(audit, tmp_path)
    rows[1]["tree_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="reuse"):
        audit._audit(rows, tmp_path, 1)
    (tmp_path / "example" / "native-layout.json").write_text("{}", encoding="ascii")
    with pytest.raises(ValueError, match="digest"):
        audit._audit(rows, tmp_path, 1)


def test_archived_capture_paths_resolve_inside_the_relocated_batch(audit, tmp_path):
    path = "X:/original/site/formal/native_live/captures/opaque/receipt.json"
    assert (
        audit._receipt_path(tmp_path, path)
        == (tmp_path / "native_live/captures/opaque/receipt.json").resolve()
    )
    with pytest.raises(ValueError):
        audit._receipt_path(tmp_path, "X:/an-unrelated/archive/receipt.json")
