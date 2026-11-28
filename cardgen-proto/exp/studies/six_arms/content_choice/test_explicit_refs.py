from pathlib import Path

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    from six_arms.content_choice import explicit_refs

    return explicit_refs


def test_only_validated_dynamic_paths_count(study):
    stage = {
        "status": "completed",
        "product": {"items": [{"path": "/metric/target", "text": "12"}]},
    }
    assert study.product_state(stage, "/metric/target") == "kept"
    assert study.product_state(stage, "/other") == "valid_without_reference"
    stage["product"]["items"] = [{"text": "/metric/target"}]
    assert study.product_state(stage, "/metric/target") == "valid_without_reference"
    assert (
        study.product_state({"status": "stage_rejected"}, "/metric/target")
        == "stage_rejected"
    )
    assert (
        study.product_state({"status": "callback_failed"}, "/metric/target")
        == "callback_failed"
    )


def test_distinct_tasks_opportunities_and_duplicate_guard(study):
    table = dict.fromkeys(study.MODEL_ARMS, "kept")
    table["L3"] = "callback_failed"
    row = {
        "task": "private-example",
        "criterion": "metric",
        "program_kept": True,
        "model": table,
    }
    rows = [row, {**row, "criterion": "date"}]
    out = study.summarize(iter(rows))
    assert out["distinct_tasks"] == 1
    assert out["criteria"]["metric"][
        "tasks_by_number_of_model_opportunities_with_reference"
    ] == {4: 1}
    assert "private-example" not in str(out)
    with pytest.raises(ValueError, match="Duplicate"):
        study.summarize([row, row])
