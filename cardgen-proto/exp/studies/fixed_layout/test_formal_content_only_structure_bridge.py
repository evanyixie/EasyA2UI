from types import SimpleNamespace

import formal_content_only_structure_bridge as bridge
import pytest


def test_input_projection_uses_only_model_visible_fields_and_preserves_ownership():
    visible = [{"id": "alarm", "kind": "button", "role": "action"}]
    actions = [{"action_id": "open", "interaction": "record_click", "owners": ["x"]}]
    view = {
        "visible": visible,
        "entities": [{"id": "x"}],
        "actions": actions,
        "relations": [],
        "canvas": {"width": 150},
        "user_preferences": [],
        "reference": {},
    }
    assert bridge.route_projection(view) == {
        "units": visible,
        "entities": [{"id": "x"}],
        "actions": actions,
        "relations": [],
        "canvas": {"width": 150},
    }
    with pytest.raises(ValueError):
        bridge.route_projection(dict(view, query="original request"))


def test_original_validation_decision_and_structure_are_unchanged(tmp_path):
    tree = {"root": {"kind": "column", "children": [{"kind": "text", "ref": "one"}]}}
    calls = []
    check = lambda t, s: calls.append((t, s))
    base = SimpleNamespace(
        common=SimpleNamespace(roles_and_clicks=check),
        layout=SimpleNamespace(validate_tree=check),
    )
    assert bridge.replay_tree(base, {}, lambda: tree, {"status": "accepted"}) is tree
    assert calls == [(tree, {}), (tree, {})]
    raw = bridge.encoded(tree)
    (tmp_path / "structure.json").write_bytes(raw)
    receipt = {"decision_sha256": bridge.digest(raw)}
    bridge.stored_tree(tmp_path, receipt, tree)
    with pytest.raises(ValueError, match="differs"):
        bridge.stored_tree(tmp_path, receipt, {})

    def reject():
        raise ValueError("invalid leaf")

    refusal = {
        "status": "rejected",
        "error_type": "ValueError",
        "detail": "invalid leaf",
    }
    assert bridge.replay_tree(base, {}, reject, refusal) is None
    with pytest.raises(ValueError, match="rejection differs"):
        bridge.replay_tree(base, {}, reject, dict(refusal, detail="another reason"))


def test_geometry_semantics_and_emission_are_separate_endpoints(tmp_path):
    shared = {"size": "2x4"}
    tree = {"root": {"kind": "row"}}
    geometry = {"root": {"kind": "row", "style": {"width": 300}}}
    messages = [{"a": 1}, {"b": 2}]

    def geometry_solver(t, s):
        assert (t, s) == (tree, shared)
        return geometry

    def emit(g, s, t):
        assert (g, s, t) == (geometry, shared, tree)
        return messages

    engine = SimpleNamespace(
        base=SimpleNamespace(
            layout=SimpleNamespace(program_geometry=geometry_solver),
            common=SimpleNamespace(emit=emit),
            trial=SimpleNamespace(signature=lambda m: min(m), VALIDATE=lambda *_: []),
        ),
        method=SimpleNamespace(geometry_gates=lambda m, s: []),
        contract=SimpleNamespace(
            check_native=lambda s, m: {"static_status": "verified"}
        ),
    )
    full = bridge.compile_tree(engine, tree, shared, {})
    assert full["state"] == "pass"
    wire = b"a\nb\n"
    assert full["artifact_sha256"] == bridge.digest(wire)
    (tmp_path / "card.a2ui.jsonl").write_bytes(wire)
    original = bridge.encoded(geometry)
    (tmp_path / "geometry.json").write_bytes(original)
    receipt = {
        "geometry": {"status": "accepted", "decision_sha256": bridge.digest(original)},
        "artifact_sha256": bridge.digest(wire),
    }
    bridge.program_diagonal(tmp_path, receipt, full)
    (tmp_path / "card.a2ui.jsonl").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash differs"):
        bridge.program_diagonal(tmp_path, receipt, full)
    engine.contract.check_native = lambda *_: {"static_status": "unresolved"}
    uncertain = bridge.compile_tree(engine, tree, shared, {})
    assert uncertain["state"] == "static_unknown"
    assert uncertain["reference_geometry_pass"] is True
    assert uncertain["artifact_sha256"] == full["artifact_sha256"]
    engine.method.geometry_gates = lambda *_: ["button width"]
    assert bridge.compile_tree(engine, tree, shared, {})["state"] == "failed_check"
    engine.base.trial.VALIDATE = lambda *_: ["invalid protocol"]
    assert bridge.compile_tree(engine, tree, shared, {})["state"] == "emit_rejected"


def test_cohorts_keep_missing_transport_and_shared_failures():
    cases = [
        ("0", "a", True, True, "pass", "pass"),
        ("1", "a", True, True, "geometry_rejected", "pass"),
        ("2", "b", True, False, "transport_unknown", "pass"),
        ("3", "c", False, False, "shared_rejected", "shared_rejected"),
    ]
    rows = [
        {
            "task": t,
            "family": f,
            "shared": s,
            "both": b,
            "model_model": {"state": m},
            "program_program": {"state": p},
        }
        for t, f, s, b, m, p in cases
    ]
    result = bridge.summarize(rows)
    assert result["assigned"]["tasks"] == 4
    assert result["assigned"]["families"] == 3
    assert result["shared_content_ready"]["tasks"] == 3
    assert result["both_original_trees_accepted"]["tasks"] == 2
    assert result["assigned"]["one_or_more_unknown"] == 1
    assert result["assigned"]["both_conclusive_fail"] == 1
    assert result["assigned"]["program_minus_model_rate_bounds"] == [0.25, 0.5]
