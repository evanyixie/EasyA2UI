from copy import deepcopy
from pathlib import Path

import pytest


@pytest.fixture
def example(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import structure_input_audit as audit

    data = {
        "query": "显示读数",
        "candidate_paths": ["/n", "/m"],
        "candidate_actions": [{"id": "a"}],
    }
    content = {
        "title": "读数",
        "size": "2x2",
        "items": [{"id": "v", "text": "18", "path": "/n"}],
        "actions": [{"id": "a", "label": "查看"}],
    }
    refs = [
        {"kind": "text", "ref": "title"},
        {"kind": "text", "ref": "v"},
        {"kind": "button", "ref": "a"},
    ]
    body = {
        "source": deepcopy(data),
        "content": deepcopy(content),
        "required_leaf_refs": deepcopy(refs),
    }
    tree = {
        "root": {
            "kind": "column",
            "children": [refs[0], {"kind": "row", "children": refs[1:]}],
        }
    }
    return audit, body, data, content, tree


def test_measures_available_context_without_counting_extra_reference_as_shown(example):
    audit, *args = example
    counts = audit.compare(*args)
    assert counts["model_prompt_has_unselected_path"] == 1
    assert counts["model_prompt_has_unselected_action"] == 0
    assert counts["selected_action_cards"] == counts["model_has_nested_button"] == 1
    assert counts["original_program_has_nested_button"] == 0


def test_changed_context_or_missing_leaf_does_not_enter_comparison(example):
    audit, body, source, content, tree = example
    body["source"]["query"] = ""
    with pytest.raises(ValueError, match="Input mismatch"):
        audit.compare(body, source, content, tree)
    body["source"] = source
    tree["root"]["children"].pop()
    with pytest.raises(ValueError, match="树缺少"):
        audit.compare(body, source, content, tree)
