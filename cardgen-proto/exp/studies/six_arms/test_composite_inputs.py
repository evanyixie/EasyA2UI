from pathlib import Path

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import composite_inputs

    return composite_inputs


def test_current_validator_and_runtime_codes_only(study):
    m = study.protocol_mutations
    messages = m.make_card(m.BASES[0])
    for op in ("createSurface", "updateComponents", "updateDataModel"):
        next(msg for msg in messages if op in msg)[op]["surfaceId"] = "surface_card"
    blob = m.wire(messages).encode()
    validate = study.validator()
    other_errors = {"errors": ["An independent binding check failed"]}
    assert study.protocol_result(blob, "2x2", other_errors, validate) == (
        True,
        "empty_violations",
        {},
    )
    errors = validate(blob.decode(), "surface_card", "2x4")
    assert len(errors) == 1 and errors[0].code == "root.canvas"
    recorded = {"errors": [str(errors[0]), *other_errors["errors"]]}
    assert study.protocol_result(blob, "2x4", recorded, validate) == (
        False,
        "protocol_violations",
        {"root.canvas": 1},
    )
    with pytest.raises(ValueError, match="differ"):
        study.protocol_result(blob, "2x4", other_errors, validate)


def test_validator_exception_remains_unknown(study):
    def broken(*args):
        raise TypeError("synthetic unsupported handler")

    assert study.protocol_result(b"[]", "2x2", {"errors": []}, broken) == (
        None,
        "validator_exception_TypeError",
        {},
    )


def test_edge_rows_are_bound_to_original_artifact_canvas_and_checkpoint(study):
    from six_arms.web_geometry_inputs import GeometryInput

    s = GeometryInput(
        "t", "f", "L3", "raw_first", "2x2", "hash", Path("test"), "native_captured"
    )
    k = "2x2-hash"
    r = {
        "task": "t",
        "family": "f",
        "arm": "L3",
        "phase": "first",
        "artifact_sha256": "hash",
        "observation_key": k,
        "status": "measured",
        "text_nodes": 1,
        "above4_nodes": 0,
        "overflow_px": 8,
    }
    obs = {
        k: {
            "key": k,
            "state": "measured",
            "expected_text_nodes": 1,
            "measured_text_nodes": 1,
            "above4_nodes": 0,
            "overflow_sum_px": 8,
        }
    }
    assert study.geometry_result(s, r, obs) == (
        True,
        "measured",
    )  # Two edges of 4px do not fail.
    assert study.geometry_result(
        s, {**r, "above4_nodes": 1}, {k: {**obs[k], "above4_nodes": 1}}
    ) == (False, "measured")
    with pytest.raises(ValueError, match="different seat"):
        study.geometry_result(s, {**r, "phase": "final"}, obs)
    with pytest.raises(ValueError, match="canvas"):
        study.geometry_result(s, {**r, "observation_key": "2x4-hash"}, obs)
    with pytest.raises(ValueError, match="Inconsistent"):
        study.geometry_result(s, {**r, "text_nodes": 20}, obs)
    assert study.geometry_result(
        s, {**r, "status": "unsupported"}, {k: {"key": k, "state": "unassessed"}}
    ) == (None, "unsupported")


def test_budget_for_failed_call_and_missing_seat_are_counted_separately(
    study, tmp_path, monkeypatch
):
    from six_arms.web_geometry_inputs import GeometryInput

    seats = [
        GeometryInput("test", "group", "L2", p, "2x2", None, None, "transport_failed")
        for p in study.MOMENTS
    ]
    monkeypatch.setattr(study, "load_inputs", lambda root: seats)
    monkeypatch.setattr(
        study, "cost_indices", lambda root: {("test", "L2"): (None, 123)}
    )
    monkeypatch.setattr(study, "checked_rows", lambda *args: [])
    edge = {
        ("test", "L2", p): {
            "task": "test",
            "family": "group",
            "arm": "L2",
            "phase": p,
            "status": "missing",
            "artifact_sha256": None,
        }
        for p in study.WEB_PHASE.values()
    }
    monkeypatch.setattr(study, "edge_evidence", lambda root: (edge, {}))
    first, final = study.load_rows(tmp_path)
    assert first["total_tokens"] is first["known_tokens"] is None
    assert final["known_tokens"] == 123 and final["total_tokens"] is None
    assert all(
        r["protocol"] is False
        and r["geometry"] is None
        and r["absence_reason"] == "transport_failed"
        for r in (first, final)
    )
