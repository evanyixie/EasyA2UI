"""Checks at the boundary between sealed artifacts, the browser and per-seat statistics."""

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest


def seat(path, digest, phase):
    return SimpleNamespace(
        task="one",
        family="family",
        arm="L5",
        checkpoint=phase,
        size="2x2",
        path=path,
        artifact_sha256=digest,
        cache_key=("2x2", digest) if path else None,
    )


def test_reuse_observation_preserve_seat_and_absence(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import formal_web_geometry as audit

    artifact = tmp_path / "card"
    raw = b"private fixture"
    artifact.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    assigned = [seat(artifact, digest, c) for c in audit.PHASES]
    assigned.append(seat(None, None, "raw_first"))
    batches = []

    def measure(cards):
        batches.append(len(cards))
        return [
            {
                "key": card["key"],
                "state": "measured",
                "expected_text_nodes": 2,
                "measured_text_nodes": 2,
                "overflow_sum_px": 6,
                "above4_nodes": 1,
            }
            for card in cards
        ]

    rows, observations = audit.measure_inputs(assigned, measure)
    assert batches == [1] and len(observations) == 1
    assert [r["phase"] for r in rows] == ["first", "final", "first"]
    assert [r.get("overflow_px") for r in rows] == [6, 6, None]
    assert rows[-1]["status"] == "missing"

    def incomplete(cards):
        result = measure(cards)
        result[0]["measured_text_nodes"] = 1
        return result

    with pytest.raises(ValueError, match="Partial"):
        audit.measure_inputs(assigned, incomplete)
    with pytest.raises(ValueError, match="Browser result"):
        audit.measure_inputs(assigned, lambda cards: [])
    artifact.write_bytes(b"changed")
    with pytest.raises(ValueError, match="Artifact changed"):
        audit.measure_inputs(assigned, measure)
