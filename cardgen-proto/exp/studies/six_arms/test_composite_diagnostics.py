from pathlib import Path

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import composite_diagnostics

    return composite_diagnostics


def sample(study, count=4):
    rows, edges, measures = {}, {}, {}
    for i in range(count):
        for a in study.stats.ARMS:
            t = str(i)
            sha = f"synthetic-{t}-{a}"
            key = "2x2-" + sha
            rows[t, a] = {
                "task": t,
                "family": "f" + t,
                "arm": a,
                "phase": study.FINAL,
                "protocol": True,
                "geometry": True,
                "a4a_hits": 4,
                "a4a_total": 5,
                "total_tokens": 0,
                "absence_reason": None,
                "artifact_sha256": sha,
            }
            edges[t, a, "final"] = {
                "task": t,
                "family": "f" + t,
                "arm": a,
                "phase": "final",
                "status": "measured",
                "text_nodes": 2,
                "above4_nodes": 0,
                "artifact_sha256": sha,
                "observation_key": key,
            }
            measures[key] = {
                "key": key,
                "state": "measured",
                "above4_nodes": 0,
                "clipped_text_nodes": 0,
                "expected_text_nodes": 2,
                "measured_text_nodes": 2,
            }
    return rows, edges, measures


def test_explains_opposite_arms_with_exclusive_reasons_and_conditional_pairs(study):
    rows, edges, measures = sample(study)

    def observation(t, a):
        return measures[edges[t, a, "final"]["observation_key"]]

    rows["0", "L4"]["a4a_hits"] = 3
    observation("0", "L5")["clipped_text_nodes"] = 1
    for t in ("0", "1"):
        rows[t, "L6"]["geometry"] = False
        edges[t, "L6", "final"]["above4_nodes"] = observation(t, "L6")[
            "above4_nodes"
        ] = 1
    rows["1", "L6"]["a4a_hits"] = 2
    rows["1", "L4"].update(
        absence_reason="transport_failed",
        protocol=False,
        a4a_hits=0,
        geometry=None,
        artifact_sha256=None,
    )
    e = edges["1", "L4", "final"]
    e.update(status="missing", artifact_sha256=None)
    del measures[e.pop("observation_key")]
    rows["2", "L5"]["a4a_hits"] = None
    rows["3", "L4"]["geometry"] = None
    edges["3", "L4", "final"]["status"] = "unsupported"
    observation("3", "L4")["state"] = "unassessed"
    rows["3", "L6"]["protocol"] = False

    report = study.diagnose(rows.values(), edges, measures)
    counts = report["arms"]["L5"]
    assert counts["qualified_by_horizontal_clip"]["pass"] == {
        "present": 1,
        "absent": 2,
        "unknown": 0,
    }
    assert counts["qualified_by_horizontal_clip"]["unknown"]["absent"] == 1
    assert counts["both_decisions_known"] == 3
    l45 = report["pairs"]["L4_L5"]
    l5 = l45["only_one_confirmed_qualified"]["L5"]
    assert (l5["opposite_failed"], l5["opposite_unknown"]) == (2, 1)
    assert {k: v for k, v in l5["opposite_reason"].items() if v} == {
        "coverage_below_80": 1,
        "no_artifact": 1,
        "indeterminate": 1,
    }
    assert l5["no_artifact_breakdown"] == {"transport_failed": 1}
    assert l45["both_artifacts"] == 3
    both = l45["both_artifacts_and_assessable_coverage_geometry"]
    assert (
        both["pairs"]
        == both["left_vs_right"]["fail"]["pass"]
        == both["right_pass"]
        == 1
    )
    assert both["left_pass"] == 0
    l56 = report["pairs"]["L5_L6"]
    reasons = l56["only_one_confirmed_qualified"]["L5"]["opposite_reason"]
    assert {k: v for k, v in reasons.items() if v} == {
        "protocol": 1,
        "frame_overflow": 1,
        "multiple_observed_failures": 1,
    }


def test_rejects_mismatched_artifact_and_impossible_clipping(study):
    rows, edges, measures = sample(study, 1)
    row = rows["0", "L2"]
    edge = edges["0", "L2", "final"]
    row["artifact_sha256"] = "unrelated"
    with pytest.raises(ValueError, match="artifact hashes differ"):
        study.diagnose(rows.values(), edges, measures)
    row["artifact_sha256"] = edge["artifact_sha256"]
    measures[edge["observation_key"]]["clipped_text_nodes"] = 3
    with pytest.raises(ValueError, match="inconsistent Edge"):
        study.diagnose(rows.values(), edges, measures)


def test_zero_text_is_unknown_and_all_assigned_required(study):
    rows, edges, measures = sample(study, 1)
    e = edges["0", "L1", "final"]
    obs = measures[e["observation_key"]]
    e["text_nodes"] = obs["expected_text_nodes"] = obs["measured_text_nodes"] = 0
    rows["0", "L1"]["geometry"] = None
    r = study.diagnose(rows.values(), edges, measures)
    assert r["arms"]["L1"]["qualified_by_horizontal_clip"]["unknown"]["unknown"] == 1
    rows.pop(("0", "L1"))
    with pytest.raises(ValueError, match="Incomplete final grid"):
        study.diagnose(rows.values(), edges, measures)
