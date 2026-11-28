"""共同出口总表的合成回归，覆盖原件、缺席与缺证分母。"""

import pytest

import study

from . import native_repair, rq2, shared_exit


def test_missing_response_for_an_invalid_card_preserves_unknown_without_fonts():
    source = study.model_stages._EXAMPLE_SOURCE
    original = b"{}"
    outputs, report = rq2.compare(original, source, lambda _phase, _prompt: None)
    assert set(outputs.values()) == {original}
    assert report["arms"]["L1-M"]["joint_pass"] is None
    assert report["arms"]["L1-M"]["status"] == "missing_response"
    assert report["arms"]["L1-NR"]["assessment"]["reference_geometry_pass"] is None
    assert report["new_physical_requests"] == 0


def test_shared_batch_retains_missing_seats_and_rejects_deleted_artifacts(tmp_path):
    try:
        native_repair.dependency_files()
    except RuntimeError as exc:
        pytest.skip(str(exc))
    batch = tmp_path / "batch"
    study.freeze(study.FIXTURE, batch, ("L1",))
    todo = shared_exit.shared(batch, tmp_path / "unexecuted")
    assert todo["counts"]["all"]["status"] == {"unexecuted": 1}
    assert todo["counts"]["all"]["reference_assessed"] == 0
    study.execute(batch, "fixture")
    done = shared_exit.shared(batch, tmp_path / "complete")
    assert done["counts"]["all"]["reference_assessed"] == 1
    assert done["counts"]["all"]["final_pass"] == 1
    (batch / "garden-demo/L1/card.a2ui.jsonl").unlink()
    with pytest.raises(ValueError, match="摘要|缺失"):
        shared_exit.shared(batch, tmp_path / "broken")
