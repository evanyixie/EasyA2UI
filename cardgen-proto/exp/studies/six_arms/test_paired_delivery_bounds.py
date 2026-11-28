import copy
import hashlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def bounds(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import paired_delivery_bounds

    return paired_delivery_bounds


def test_bounds_keep_unresolved_pairs_unknown(bounds):
    interval = bounds.interval
    assert interval("unknown", "unknown") == (-1, 1)
    assert interval("unknown", "unknown", tied=True) == (0, 0)
    assert interval("fail", "unknown") == (-1, 0)
    with pytest.raises(ValueError):
        interval("fail", "pass", tied=True)


def test_same_image_alone_and_same_handler_are_insufficient(tmp_path, bounds):
    identical_card = bounds.identical_card
    image = b"same screenshot evidence"
    (tmp_path / "image").write_bytes(image)
    proof = {"status": "pass"}
    base = {
        "task_id": "test",
        "checkpoint": "raw_first",
        "input_sha256": "input",
        "execution": {"status": "native_captured"},
        "primary_evidence": dict.fromkeys(
            (
                "first_response_lineage",
                "protocol",
                "trusted_native_frame",
                "lossless_caller_canvas",
            ),
            proof,
        ),
        "provenance": {
            "raw_request_sha256": "raw",
            "packaged_request_sha256": "package",
            "registry_sha256": "registry",
            "artifact_ref": "artifact",
            "capture": {
                "screenshot_sha256": hashlib.sha256(image).hexdigest(),
                "screenshot_ref": "image",
            },
        },
    }

    def write_card(handlers):
        native = json.dumps(
            {"updateComponents": {"components": [{"onClick": handlers}]}}
        ).encode()
        (tmp_path / "artifact").write_bytes(native)
        base["artifact_sha256"] = hashlib.sha256(native).hexdigest()

    write_card([])
    assert identical_card(tmp_path, base, base)
    other = copy.deepcopy(base)
    other["artifact_sha256"] = "different"
    assert not identical_card(tmp_path, base, other)
    other = copy.deepcopy(base)
    other["primary_evidence"]["trusted_native_frame"] = {"status": "unknown"}
    assert not identical_card(tmp_path, base, other)
    write_card([{"call": "action"}])
    assert not identical_card(tmp_path, base, base)
