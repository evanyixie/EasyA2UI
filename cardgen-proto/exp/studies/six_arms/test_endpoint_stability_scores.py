import json
from itertools import product
from pathlib import Path

import pytest


@pytest.fixture
def score(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import endpoint_stability_scores

    return endpoint_stability_scores


def native(identifier, nested="same"):
    ops = ("createSurface", "updateComponents", "updateDataModel")
    return (
        "\r\n".join(
            json.dumps({op: {"surfaceId": identifier, "data": {"surfaceId": nested}}})
            for op in ops
        )
        + "\n"
    ).encode()


def test_mask_changes_only_direct_id_tokens_preserving_original_bytes(score):
    source = native("old", "inside")
    assert score.mask_surface(source) == score.mask_surface(native("NEW", "inside"))
    assert score.mask_surface(source) != score.mask_surface(native("old", "different"))
    assert score.mask_surface(source).endswith(b"\n")
    assert score.mask_surface(source) != score.mask_surface(
        source.replace(b"\r\n", b"\n")
    )
    assert score.mask_surface(source) != score.mask_surface(source.replace(b": ", b":"))
    assert score.mask_surface(source.replace(b'"old"', b'"other"', 1)) is None
    assert (
        score.mask_surface(
            source.replace(b'"surfaceId": "old"', b'"surfaceId":"a", "surfaceId":"old"')
        )
        is None
    )
    assert score.mask_surface(b"not a card") is None


def test_semantic_multisets_follow_explicit_schema_only(score):
    def fields(items, **extra):
        return score.content_fields(
            {
                "stages": [
                    {
                        "stage": "content",
                        "status": "completed",
                        "product": {
                            "domain": "sport",
                            "size": "2x2",
                            "items": items,
                            "actions": [{"id": "action"}],
                            **extra,
                        },
                    }
                ]
            }
        )

    items = [
        {"type": "reading", "content_hint": "甲， 乙"},
        {"type": "unit", "content_hint": "℃"},
    ]
    a, b = (
        fields(items + items[:1], theme="blue"),
        fields([*items[::-1], items[0]], theme="blue"),
    )
    assert a == b and a["item_count"] == 3 and a["theme"] == "blue"
    assert a["typed_hints"] == (("reading", "甲乙"), ("reading", "甲乙"), ("unit", "℃"))
    assert (
        fields([{"type": "reading", "content_hint": "甲丙"}])["typed_hints"]
        != a["typed_hints"]
    )
    absent = fields([{"id": "a", "role": "reading", "text": "something"}])
    assert absent["item_types"] is absent["typed_hints"] is absent["theme"] is None
    assert (
        fields([])["item_count"] == 0
        and fields([])["item_types"] is fields([])["typed_hints"] is None
    )
    assert score.content_fields({"stages": []}) == dict.fromkeys(score.C1)


def test_ten_failures_or_partial_observations_do_not_become_stable(score):
    no = score.NO_ARTIFACT
    groups = [["X"] * 10, [no] * 10, ["X"] * 9 + [None], [None] * 8 + ["X", "Y"]]
    m = score.summarize(groups, formal=False)
    assert m["tasks_yes_no_unknown"] == [1, 2, 1]
    assert m["tasks_all_ten_observable"] == 1 and m["tasks_decidable"] == 3
    assert m["assigned_rate_bounds"] == [0.25, 0.5]
    assert m["draws_observed_absent_unknown"] == [21, 10, 9]
    assert m["wilson95"] is None
    assert score.summarize([["X"] * 10] * 12, formal=True)["wilson95"] == [
        0.757506,
        1.0,
    ]
    assert (
        score.summarize([["X"] * 10] * 11 + [[None] * 10], formal=True)["wilson95"]
        is None
    )


def test_checkpoint_hashes_and_technical_failure_are_distinct(score, tmp_path):
    blob = native("initial")
    entry = {"sha256": score.digest(blob), "text": blob.decode()}
    run = {
        "stages": [],
        "status": "geometry_unresolved",
        "first_native": entry,
        "final_native": entry,
    }
    for phase in ("first", "final"):
        (tmp_path / f"{phase}_native.a2ui.jsonl").write_bytes(blob)
    o = score.observations(tmp_path, run)
    assert o["first.raw_bytes"] == o["final.raw_bytes"] == score.digest(blob)
    assert o["accepted_final.raw_bytes"] is score.NO_ARTIFACT
    assert (
        score.observations(tmp_path, {**run, "status": "geometry_unknown"})[
            "accepted_final.raw_bytes"
        ]
        is None
    )
    (tmp_path / "final_native.a2ui.jsonl").write_bytes(blob + b" ")
    with pytest.raises(ValueError, match="Native artifact mismatch"):
        score.observations(tmp_path, run)


def test_roster_requires_complete_unique_repetitions(score):
    cases = ["t1", "t2"]
    spec = {
        "selected": [{"task": t} for t in cases],
        "total_seats": 120,
        "payload_except_messages": {"temperature": 1},
        "order": [
            {"task": t, "arm": a, "rep": n}
            for t, a, n in product(cases, score.ARMS, score.REPS)
        ],
    }
    assert set(score.verify_roster(spec, 2)) == set(cases)
    spec["order"][-1] = spec["order"][0]
    with pytest.raises(ValueError, match="duplicate"):
        score.verify_roster(spec, 2)


def test_formal_schedule_alone_cannot_be_scored(score, tmp_path):
    rows = {f"t{i}": {"task": f"t{i}", "family": f"g{i}"} for i in range(12)}
    with pytest.raises(ValueError, match="synthetic"):
        score.execution_inputs(
            tmp_path, "plan", {"evidence_mode": "synthetic_dry_run"}, rows, True, None
        )
    spec = {
        "evidence_mode": "custodian_schedule_only",
        "payload_except_messages": score.WIRE,
    }
    with pytest.raises(ValueError, match="pinned"):
        score.execution_inputs(tmp_path, "plan", spec, rows, True, None)
    h = "1" * 64
    selected = [
        {
            **r,
            "source_sha256": h,
            "registry_sha256": h,
            "source_canonical_sha256": h,
            "initial_prompt_sha256": dict.fromkeys(score.ARMS, h),
        }
        for r in rows.values()
    ]
    freeze = {
        "plan_sha256": "plan",
        "official_endpoint": score.ENDPOINT,
        "runner_sha256": h,
        "payload_except_messages": spec["payload_except_messages"],
        "selected": selected,
    }
    p = tmp_path / "execution_freeze.json"
    p.write_bytes(score.canonical(freeze))
    assert (
        score.execution_inputs(
            tmp_path, "plan", spec, rows, True, score.digest(p.read_bytes())
        ).keys()
        == rows.keys()
    )
    p.write_bytes(
        score.canonical({**freeze, "official_endpoint": "https://different.invalid"})
    )
    with pytest.raises(ValueError, match="Endpoint"):
        score.execution_inputs(
            tmp_path, "plan", spec, rows, True, score.digest(p.read_bytes())
        )
    selected[0]["initial_prompt_sha256"].pop("L6")
    p.write_bytes(score.canonical(freeze))
    with pytest.raises(ValueError, match="initial prompt"):
        score.execution_inputs(
            tmp_path, "plan", spec, rows, True, score.digest(p.read_bytes())
        )


def test_source_identity_binds_exact_file_and_private_registry(score, tmp_path):
    source = tmp_path / "task.json"
    source.write_text('{"title": "synthetic"}\n', encoding="utf-8")
    registry = tmp_path / "registry.json"
    entry = {"id": "task", "values": []}
    registry.write_bytes(score.canonical({"cases": {"task": entry}}))
    canonical_hash = score.digest(score.canonical(score.read(source)))
    locked = {
        "task": {
            "source_sha256": score.digest(source.read_bytes()),
            "source_canonical_sha256": canonical_hash,
            "registry_sha256": score.digest(score.canonical(entry)),
        }
    }
    assert score.verify_source_material(locked, tmp_path, registry) == {
        "task": canonical_hash
    }
    registry.write_bytes(
        score.canonical({"cases": {"task": {**entry, "id": "different"}}})
    )
    with pytest.raises(ValueError, match="registry"):
        score.verify_source_material(locked, tmp_path, registry)
    source.write_bytes(source.read_bytes() + b" ")
    with pytest.raises(ValueError, match="Source file hash"):
        score.verify_source_material(locked, tmp_path, registry)


def test_request_reuse_and_wrong_first_prompt_raise(score, tmp_path):
    from collections import defaultdict

    spec = {
        "official_endpoint": "test",
        "payload_except_messages": {"model": "m", "temperature": 1},
    }
    stage = "content"
    f = tmp_path / "calls" / stage
    f.mkdir(parents=True)
    messages = [{"role": "user", "content": "synthetic"}]
    msg = score.canonical(messages)
    raw = b"[]"
    c = {
        "stage": stage,
        "temperature": 1.0,
        "requested_model": "m",
        "returned_model": "m",
        "physical_attempts": 1,
        "request_id": "reply",
        "http_status": 200,
        "endpoint": "test",
        "actual_payload_sha256": score.digest(
            score.canonical({**spec["payload_except_messages"], "messages": messages})
        ),
    }
    (f / "messages.json").write_bytes(msg)
    (f / "call.json").write_bytes(score.canonical(c))
    (f / "response.txt").write_bytes(raw)
    (f / "seal.json").write_bytes(
        score.canonical(
            {
                "stage": stage,
                "local_request_id": "once",
                "messages_sha256": score.digest(msg),
                "receipt_sha256": score.digest(score.canonical(c)),
                "state": "completed",
                "raw_sha256": score.digest(raw),
            }
        )
    )
    execution = {
        "stages": [
            {
                "stage": stage,
                "status": "completed",
                "product": [],
                "receipt": c,
                "messages": messages,
                "raw_sha256": score.digest(raw),
            }
        ]
    }
    seen = defaultdict(set)
    score.receipts(tmp_path, execution, score.digest(msg), spec, seen)
    with pytest.raises(ValueError, match="Reused"):
        score.receipts(tmp_path, execution, score.digest(msg), spec, seen)
    with pytest.raises(ValueError, match="Initial prompt"):
        score.receipts(tmp_path, execution, "mismatch", spec, defaultdict(set))
    execution["stages"][0]["product"] = {"size": "different"}
    with pytest.raises(ValueError, match="semantic fields"):
        score.receipts(tmp_path, execution, score.digest(msg), spec, defaultdict(set))
