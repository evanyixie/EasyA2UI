from pathlib import Path

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import fixed_geometry_content

    def score(raw, facts, query, values):
        if raw is None:
            return {
                "coverage": "unassessed",
                "coverage_state": "no_artifact",
                "covered": None,
                "references": 2,
                "fidelity": "no_artifact",
                "supported": None,
                "numeric_total": None,
            }
        covered = 1 if raw == b"partial" else 2
        return {
            "coverage": "at_least_80" if covered == 2 else "below_80",
            "coverage_state": "measured",
            "covered": covered,
            "references": 2,
            "fidelity": "all_sourced",
            "supported": 1,
            "numeric_total": 1,
        }

    monkeypatch.setattr(fixed_geometry_content.rq2, "content_scores", score)
    return fixed_geometry_content


def test_same_tree_does_not_waive_content_or_score_a_repair_as_first_pass(study):
    def case(task, model, program, *, reached=True, original=True):
        def side(arg):
            raw, pre, post = arg
            return {
                "first": raw,
                "final": raw,
                "first_technical": pre,
                "final_technical": post,
            }

        return study.score_pair(
            {
                "task": task,
                "family": task,
                "in_217": original,
                "reached": reached,
                "model": side(model),
                "program": side(program),
            },
            [],
            "query",
            {},
        )

    rows = [
        case("a", (b"one", "fail", "pass"), (b"two", "pass", "pass")),
        case(
            "b",
            (b"partial", "fail", "pass"),
            (b"partial", "pass", "pass"),
            original=False,
        ),
        case(
            "c",
            (None, "missing", "missing"),
            (None, "missing", "missing"),
            reached=False,
        ),
    ]
    result = study.summarize(rows)
    full = result["all_assigned"]["phases"]["after_common_repair"]
    assert full["arms"]["program"]["joint"] == {"pass": 1, "fail": 1, "missing": 1}
    scores = result["same_content_and_tree"]["phases"]
    final = scores["after_common_repair"]
    assert (
        final["both_have_artifacts"]
        == final["both_artifacts_equal_reference_counts"]
        == 2
    )
    assert final["both_artifacts_identical_bytes"] == 1
    assert final["joint_pair"]["states"]["pass"]["pass"] == 1
    assert scores["raw_first"]["joint_pair"]["states"]["fail"]["pass"] == 1
    assert result["same_tree_original_sources"]["tasks"] == 1
    with pytest.raises(ValueError, match="Duplicate"):
        study.summarize([*rows, rows[0]])
