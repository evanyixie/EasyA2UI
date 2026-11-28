import json
from copy import deepcopy
from pathlib import Path

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import protocol_mutations

    return protocol_mutations


def changed_fields(before, after):
    """A replacement or a single list insertion/deletion counts as one edited field."""
    if type(before) != type(after):
        return 1
    if isinstance(before, dict):
        return len(before.keys() ^ after.keys()) + sum(
            changed_fields(before[k], after[k]) for k in before.keys() & after.keys()
        )
    if isinstance(before, list):
        if len(before) != len(after):
            return abs(len(before) - len(after))
        return sum(changed_fields(a, b) for a, b in zip(before, after, strict=True))
    return int(before != after)


def test_five_different_healthy_contexts_and_isolated_edits(study):
    all_wires, shapes = [], set()
    for index, case in enumerate(study.BASES):
        base = study.make_card(case)
        untouched = deepcopy(base)
        by_node = base[1]["updateComponents"]["components"]
        shape = tuple((n["component"], len(n.get("children", []))) for n in by_node)
        shapes.add(shape)
        display = study.read_only_variant(base)
        display_nodes = display[1]["updateComponents"]["components"]
        assert not any(
            n["component"] == "Button" or "open" in n.get("children", [])
            for n in display_nodes
        )
        all_wires.extend([study.wire(base), study.wire(display)])
        for code in study.EDITS:
            text = study.mutate(base, code, index)
            all_wires.append(text)
            lines = text.splitlines()
            if code == "jsonl.line_count":
                assert len(lines) in {2, 4}
                assert all(json.loads(line) for line in lines)
            elif code == "jsonl.parse":
                assert len(lines) == 3
                with pytest.raises(json.JSONDecodeError):
                    [json.loads(line) for line in lines]
            else:
                assert changed_fields(base, [json.loads(s) for s in lines]) == 1
        assert base == untouched
    assert len(shapes) == 5
    assert len(set(all_wires)) == len(all_wires) == 100


def test_record_secondary_codes_and_exceptions_separately(study):
    report = study.build_report()
    assert len(report["legal_observations"]) == 10
    assert report["legal_with_codes"] == report["legal_exceptions"] == 0
    by_code = {r["target"]: r for r in report["per_target"]}
    assert len(by_code) == 18
    assert sum(len(r["observations"]) for r in by_code.values()) == 90
    by_case = {
        (r["target"], item["context"]): item
        for r in by_code.values()
        for item in r["observations"]
    }
    for name in ("timer", "journey", "checklist"):
        assert by_case["tree.root_count", name]["codes"] == {
            "tree.root_count": 1,
            "root.canvas": 1,
            "root.shell": 1,
        }
    assert by_case["envelope.version", "checklist"]["codes"] == {
        "envelope.version": 1,
        "envelope.line2": 1,
    }
    assert by_case["button.on_click", "checklist"] == {
        "context": "checklist",
        "outcome": "exception",
        "codes": {},
        "exception_type": "TypeError",
    }
    assert report["outcome_counts"] == {
        "target_only": 85,
        "target_and_other": 4,
        "exception": 1,
    }
    assert report["target_code_hits"] == 89
    assert report == json.loads(study.DEFAULT_TABLE.read_bytes())


def test_stray_code_is_not_a_hit_and_silence_is_not_rejection(study):
    assert (
        study.classification(
            "target", {"exception_type": None, "codes": {"elsewhere": 1}}
        )
        == "other_only"
    )
    assert (
        study.classification("target", {"exception_type": None, "codes": {}})
        == "silent"
    )
