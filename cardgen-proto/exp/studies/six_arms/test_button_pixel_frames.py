import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def frames(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import button_pixel_frames

    return button_pixel_frames


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data), encoding="utf8")
    return sha(path)


@pytest.fixture
def row(tmp_path):
    p = tmp_path
    source = p / "received-input.jsonl"
    source_hash = write(
        source,
        {
            "updateComponents": {
                "components": [{"id": "b", "component": "Button", "label": "Action"}]
            }
        },
    )
    screen = Image.new("RGB", (9, 10), (17, 80, 50))
    screen.putpixel((3, 5), (255, 255, 255))
    screen.save(p / "screen.jpeg", quality=95)
    with Image.open(p / "screen.jpeg") as shot:
        shot.crop((1, 2, 6, 9)).convert("RGB").save(p / "card.png")
    ctrl = {
        "id": "b",
        "type": "Button",
        "text": "Action",
        "visible": "true",
        "bounds": "[2,4][5,7]",
        "origBounds": "[2,4][5,7]",
    }
    node = {"attributes": ctrl}
    tree_hash = write(
        p / "native-layout.json",
        {
            "attributes": {
                "id": "a2ui_capture_root",
                "visible": "true",
                "bounds": "[1,2][6,9]",
                "origBounds": "[1,2][6,9]",
            },
            "children": [node],
        },
    )
    rec = {
        "status": "captured",
        "task": "example",
        "arm": "A",
        "input_sha256": source_hash,
        "input_return_sha256": source_hash,
        "vp": [150, 150],
        "run_id": "r",
        "terminal": {
            "runId": "r",
            "widthVp": 150,
            "heightVp": 150,
            "cropPx": {"left": 1, "top": 2, "width": 5, "height": 7},
        },
        "full_sha256": sha(p / "screen.jpeg"),
        "screenshot_sha256": sha(p / "card.png"),
    }
    return {
        "task": "example",
        "arm": "A",
        "checkpoint": "first",
        "source": source.name,
        "artifact_sha256": source_hash,
        "receipt": "receipt.json",
        "tree_sha256": tree_hash,
        "receipt_sha256": write(p / "receipt.json", rec),
    }


def test_rgb_replay_and_duplicate_across_checkpoints(frames, row, tmp_path):
    manifest = tmp_path / "input.jsonl"
    absent = {"task": "other", "arm": "A", "checkpoint": "first"}
    manifest.write_text(
        "\n".join(map(json.dumps, [row, {**row, "checkpoint": "final"}, absent]))
    )
    dest = tmp_path / "result"
    frames.run(manifest, dest, bytes(range(32)))
    crops = list((dest / "blind/crops").glob("*.png"))
    assert len(crops) == 1
    buttons = [
        json.loads(l)
        for l in (dest / "private/buttons.private.jsonl").read_text().splitlines()
    ]
    assert [r["blind_id"] for r in buttons] == [crops[0].stem] * 2
    assert [r["state"] for r in buttons] == ["cropped"] * 2
    with Image.open(crops[0]) as tile, Image.open(tmp_path / "screen.jpeg") as screen:
        assert tile.size == (3, 3)
        assert tile.tobytes() == screen.crop((2, 4, 5, 7)).convert("RGB").tobytes()
    assert (
        json.loads((dest / "private/seats.private.jsonl").read_text().splitlines()[-1])[
            "seat_state"
        ]
        == "no_source"
    )


@pytest.mark.parametrize(
    "changed, state",
    [
        ({"bounds": "[3,4][5,7]"}, "outside_or_clipped"),
        ({"origBounds": "[0,4][5,7]", "bounds": "[0,4][5,7]"}, "outside_or_clipped"),
        ({"visible": "false"}, "hidden"),
        ({"type": "Text"}, "wrong_type"),
    ],
)
def test_ineligible_frames(frames, changed, state):
    attrs = {
        "type": "Button",
        "visible": "true",
        "bounds": "[2,4][5,7]",
        "origBounds": "[2,4][5,7]",
    }
    roi = (1, 2, 6, 9)
    assert frames.locate([{**attrs, **changed}], roi) == (state, None)
    assert frames.locate([], roi)[0] == "button_absent"
    assert frames.locate([attrs, attrs], roi)[0] == "ambiguous_id"


def test_untrusted_image_rejected_without_partial_output(frames, row, tmp_path):
    manifest = tmp_path / "input.jsonl"
    write(manifest, row)
    (tmp_path / "card.png").write_bytes(b"changed")
    dest = tmp_path / "result"
    with pytest.raises(ValueError, match="Hash mismatch"):
        frames.run(manifest, dest, bytes(range(32)))
    assert not dest.exists()
