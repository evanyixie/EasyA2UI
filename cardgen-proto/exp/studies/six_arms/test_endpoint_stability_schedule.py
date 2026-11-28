from collections import Counter
from pathlib import Path

import pytest


@pytest.fixture
def scheduler(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import endpoint_stability_schedule

    return endpoint_stability_schedule


def row(i, family=None, size=None, layout=None):
    return {
        "task": f"SYN-{i:04}",
        "family": family or f"family-{i}",
        "size": size or ("2x2" if i % 2 else "2x4"),
        "layout": layout or f"layout-{i % 6}",
    }


def test_synthetic_full_grid_and_permutation_invariance(scheduler):
    rows = [row(i, family=f"family-{i % 140}") for i in range(219)]
    a = scheduler.make_plan(rows, "synthetic_dry_run", {})
    b = scheduler.make_plan(rows[::-1], "synthetic_dry_run", {})
    assert a == b
    spec = a["specification"]
    assert all(x["selected"] == 2 for x in spec["strata"])
    cases = spec["selected"]
    assert len({r["family"] for r in cases}) == 12
    assert Counter(r["size"] for r in cases) == {"2x2": 6, "2x4": 6}
    assert len({(j["task"], j["arm"], j["rep"]) for j in spec["order"]}) == 720
    assert {j["rep"] for j in spec["order"]} == set(range(1, 11))
    run = scheduler.dry_run()
    assert run["scheduled_seats"] == run["bound_envelopes"] == 720
    assert run["model_calls"] == run["device_calls"] == run["missing_envelopes"] == 0
    assert run["evidence_mode"] == "synthetic_dry_run" and not run["scoring_performed"]


def test_joint_matching_keeps_feasible_size_quota_with_cross_layout_families(scheduler):
    # The six narrow cards can only use groups shared with one of the two wide layouts.
    rows = [row(i, f"shared-{i}", "2x2", "narrow") for i in range(6)]
    rows += [row(i + 6, f"shared-{i}", "2x4", "collision") for i in range(6)]
    rows += [row(i + 12, f"wide-{i}", "2x4", "alternative") for i in range(6)]
    chosen, cells = scheduler.select(rows)
    assert len({r["family"] for r in chosen}) == 12
    assert Counter(r["size"] for r in chosen) == {"2x2": 6, "2x4": 6}
    assert next(c["selected"] for c in cells if c["layout"] == "collision") == 0


def test_unbalanced_size_is_explicit_and_family_shortage_blocks(scheduler):
    rows = [row(0, size="2x2")] + [row(i, size="2x4") for i in range(1, 20)]
    chosen, _ = scheduler.select(rows)
    assert Counter(r["size"] for r in chosen) == {"2x2": 1, "2x4": 11}
    with pytest.raises(ValueError, match="across sizes: 3"):
        scheduler.select([row(i, f"family-{i % 3}") for i in range(219)])


@pytest.mark.parametrize(
    "bad",
    [
        {"output": "not input metadata"},
        {"layout": ""},
        {"task": "../OUT"},
        {"size": "3x4"},
        {"family": ""},
    ],
)
def test_metadata_excludes_outcomes_unresolved_layout_and_invalid_ids(scheduler, bad):
    rows = [row(i) for i in range(12)]
    rows[0].update(bad)
    with pytest.raises(ValueError):
        scheduler.select(rows)


def test_signed_undetermined_is_a_distinct_stratum_without_known_layout_claims(
    scheduler,
):
    rows = [row(i, layout=("未判定" if i % 2 else "UNDETERMINED")) for i in range(219)]
    spec = scheduler.make_plan(rows, "synthetic_dry_run", {})["specification"]
    summary = spec["layout_coverage"]
    assert (
        summary["undetermined_candidate_rows"] == 219
        and summary["undetermined_selected_rows"] == 12
    )
    assert (
        summary["known_layouts_in_roster"] == summary["known_layouts_in_selection"] == 0
    )
    assert (
        summary["interpretation"]
        == "conditional_schedule_only_no_known_layout_coverage"
    )
    assert all(r["layout"] == "undetermined" for r in spec["selected"])
    rows[0]["layout"] = "known"
    mixed = scheduler.make_plan(rows, "synthetic_dry_run", {})["specification"][
        "layout_coverage"
    ]
    assert (
        mixed["undetermined_candidate_rows"],
        mixed["undetermined_selected_rows"],
    ) == (218, 11)
    assert mixed["known_layouts_in_selection"] == 1


def test_private_draft_requires_matching_preexisting_references(scheduler):
    # A fixture fingerprint exercises linking only; the function does not authenticate P8.
    fixture = b"synthetic fingerprint fixture"
    h = scheduler.sha(fixture)
    m = {
        "split": "report",
        "layout_source": "independent_labels",
        "p8_receipt_sha256": h,
        "cases": [row(i) for i in range(219)],
    }
    raw = scheduler.canonical(m)
    result = scheduler.private_plan(raw, scheduler.sha(raw), fixture, h)
    assert result["specification"]["evidence_mode"] == "custodian_schedule_only"
    with pytest.raises(ValueError, match="fingerprints"):
        scheduler.private_plan(raw, scheduler.sha(raw), fixture + b"changed", h)
    for key, val in [
        ("split", "dev"),
        ("layout_source", "generated_card"),
        ("p8_receipt_sha256", "0" * 64),
    ]:
        changed = scheduler.canonical({**m, key: val})
        with pytest.raises(ValueError, match="report-only"):
            scheduler.private_plan(changed, scheduler.sha(changed), fixture, h)


def test_manifest_and_receipt_are_bound_to_exact_bytes_plan_seat_and_payload(scheduler):
    plan = scheduler.make_plan([row(i) for i in range(219)], "synthetic_dry_run", {})
    raw = scheduler.canonical(plan)
    h = scheduler.sha(raw)
    job = plan["specification"]["order"][0]
    rel = f"{job['task']}/{job['arm']}/rep{job['rep']:02}"
    payload = {"synthetic_preflight": True}
    r = {
        "job": job,
        "plan_sha256": h,
        "execution": payload,
        "execution_sha256": scheduler.sha(scheduler.canonical(payload)),
    }

    def check(pairs):
        return scheduler.verify_receipts(raw, h, pairs)

    assert check([(rel, r)])["missing_envelopes"] == 719
    with pytest.raises(ValueError, match="repeated"):
        check([(rel, r), (rel, r)])
    with pytest.raises(ValueError, match="misfiled"):
        check([("other-folder", r)])
    with pytest.raises(ValueError, match="another plan"):
        check([(rel, {**r, "plan_sha256": "wrong"})])
    with pytest.raises(ValueError, match="Unbound"):
        check([(rel, {**r, "execution": {"different": True}})])
    with pytest.raises(ValueError, match="Unregistered"):
        scheduler.verify_receipts(raw + b"\n", h, [])
    real = scheduler.canonical(
        {
            **plan,
            "specification": {
                **plan["specification"],
                "evidence_mode": "custodian_schedule_only",
            },
        }
    )
    with pytest.raises(ValueError, match="Synthetic outcome"):
        scheduler.verify_receipts(
            real,
            scheduler.sha(real),
            [(rel, {**r, "plan_sha256": scheduler.sha(real)})],
        )
