import copy
import hashlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def frames(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import selected_binding_frames

    return selected_binding_frames


SAMPLES = {
    "/data/n": 0,
    "/data/unit": "个",
    "/data/name": "日历",
    "/data/other": "日历",
}
RECT = (0, 0, 100, 100)


def wire(data=None):
    if data is None:
        data = {"data": {"n": 0, "unit": "个", "name": "日历", "other": "日历"}}
    graph = [
        {"id": "root", "component": "Row", "children": ["v", "b", "s"]},
        {"id": "v", "component": "Text", "content": "{{ ${/data/n} + ${/data/unit} }}"},
        {"id": "b", "component": "Button", "label": {"path": "/data/name"}},
        {"id": "s", "component": "Text", "content": "日历"},
    ]
    return json.dumps(
        [
            {"createSurface": {"surfaceId": "test"}},
            {"updateComponents": {"surfaceId": "test", "components": graph}},
            {"updateDataModel": {"surfaceId": "test", "path": "/", "value": data}},
        ]
    ).encode()


def tree():
    return {
        "attributes": {"id": "a2ui_capture_root", "bounds": "[0,0][100,100]"},
        "children": [
            {
                "attributes": {
                    "id": key,
                    "type": kind,
                    "visible": "true",
                    "opacity": "1",
                    "text": val,
                    "bounds": "[70,20][110,40]",
                }
            }
            for key, kind, val in [
                ("v", "Text", "0个"),
                ("b", "Button", "日历"),
                ("s", "Text", "日历"),
            ]
        ],
    }


def leaves(v="match", b="match"):
    return [
        {"id": "v", "kind": "Text", "dynamic": True, "state": v},
        {"id": "b", "kind": "Button", "dynamic": True, "state": b},
        {"id": "s", "kind": "Text", "dynamic": False, "state": "match"},
    ]


def test_paths_count_bindings_not_literal_lookalikes_and_allow_intersection(frames):
    assert frames._matched_paths(wire(), tree(), RECT, SAMPLES, leaves()) == {
        "/data/n",
        "/data/unit",
        "/data/name",
    }
    changed_type = {**SAMPLES, "/data/n": "0"}
    assert frames._matched_paths(wire(), tree(), RECT, changed_type, leaves()) == {
        "/data/name"
    }


@pytest.mark.parametrize(
    ("attrs", "state"),
    [
        ({"type": "Text"}, "no_unique_native_control"),
        ({"visible": "false"}, "no_visible_control_box"),
        ({"bounds": "[100,30][120,40]"}, "no_visible_control_box"),
        ({"text": "其他"}, "native_text_differs"),
        ({"opacity": "0"}, "match"),
    ],
)
def test_mismatched_or_invisible_control(frames, attrs, state):
    t = tree()
    t["children"][1]["attributes"].update(attrs)
    assert frames._matched_paths(wire(), t, RECT, SAMPLES, leaves(b=state)) == {
        "/data/n",
        "/data/unit",
    }


def test_ambiguous_id_and_unresolved_expression(frames):
    t = tree()
    t["children"].append(copy.deepcopy(t["children"][1]))
    raw = json.loads(wire())
    raw[1]["updateComponents"]["components"][1]["content"] = "{{ plus(${/data/n}) }}"
    audit = leaves("unresolved_expression", "no_unique_native_control")
    audit[0]["dynamic"] = None
    assert (
        frames._matched_paths(json.dumps(raw).encode(), t, RECT, SAMPLES, audit)
        == set()
    )
    with pytest.raises(ValueError, match="classification"):
        frames._matched_paths(json.dumps(raw).encode(), t, RECT, SAMPLES, leaves())


def test_index_links_receipt_registry_tree_and_checkpoint(
    frames, tmp_path, monkeypatch
):
    def save(rel, value):
        raw = value if isinstance(value, bytes) else json.dumps(value).encode()
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    raw = wire()
    artifact_ref = "outputs/example/L3/card.jsonl"
    sha = save(artifact_ref, raw)
    save("capture/received-input.jsonl", raw)
    shot = save("capture/card.png", b"test image")
    layout = save("capture/native-layout.json", tree())
    proof = "capture/receipt.json"
    receipt = {
        "task": "t",
        "arm": "L3",
        "input_sha256": sha,
        "input_return_sha256": sha,
        "status": "captured",
        "run_id": "r",
        "screenshot_sha256": shot,
        "terminal": {
            "state": "foreground",
            "cropPx": {"left": 0, "top": 0, "width": 100, "height": 100},
        },
    }
    cap = {
        "proof_ref": proof,
        "proof_sha256": save(proof, receipt),
        "capture_run_id": "r",
        "host_state": "foreground",
        "artifact_sha256": sha,
        "screenshot_sha256": shot,
        "screenshot_ref": "capture/card.png",
    }
    registry = save(
        "queue/package/registry/example.json", {"id": "t", "binding_samples": SAMPLES}
    )
    obs = {
        "task_id": "t",
        "arm": "L3",
        "checkpoint": "raw_first",
        "artifact_sha256": sha,
        "provenance": {
            "capture": cap,
            "registry_sha256": registry,
            "artifact_ref": artifact_ref,
        },
    }
    final = {**obs, "checkpoint": "after_common_repair"}
    audit = {
        "proof": proof,
        "layout_sha256_at_audit": layout,
        "task": "t",
        "arm": "L3",
        "sha256": sha,
        "phases": ["raw_first", "after_common_repair"],
        "leaves": leaves(),
    }
    a = save(
        "pre_score_evidence/native_control_text_20261128/control_text.private.jsonl",
        audit,
    )
    o = save(
        "pre_score_evidence/endpoint/observations.private.jsonl",
        "\n".join(json.dumps(seat) for seat in (obs, final)).encode(),
    )
    monkeypatch.setattr(
        frames.native_repeated_facts, "PINS", {"control_text": a, "observations": o}
    )
    index = frames.load_frame_index(tmp_path)
    expected = {"/data/n", "/data/unit", "/data/name"}
    assert frames.verified_paths(tmp_path, obs, raw, index) == expected
    assert frames.verified_paths(tmp_path, final, raw, index) == expected
    assert (
        frames.verified_paths(tmp_path, {"provenance": {"capture": None}}, None, index)
        == set()
    )
    for bad in (
        {**obs, "checkpoint": "unknown"},
        {**obs, "arm": "L4"},
        {**obs, "provenance": {**obs["provenance"], "registry_sha256": "other"}},
    ):
        with pytest.raises(ValueError):
            frames.verified_paths(tmp_path, bad, raw, index)
    with pytest.raises(ValueError):
        frames.verified_paths(tmp_path, final, raw + b" ", index)
    save("capture/native-layout.json", {})
    with pytest.raises(ValueError, match="Hash mismatch"):
        frames.verified_paths(tmp_path, obs, raw, frames.load_frame_index(tmp_path))
