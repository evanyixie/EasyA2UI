import copy
import hashlib
import itertools

import pytest
from cohort_analysis import ARMS, POINTS, collect, summarize
from endpoint import EVIDENCE_KINDS, INDEPENDENT, PRIMARY_ITEMS

VERSION = "1" * 64


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def sample():
    roster = [
        {"task_id": tid, "family": "f", "input_sha256": digest(tid)}
        for tid in ("a", "b", "c")
    ]
    records = []
    for r, arm, point in itertools.product(roster, ARMS, POINTS):
        tid = r["task_id"]
        original = digest(tid + arm + "first")
        current = original if point == POINTS[0] else digest(tid + arm + "repaired")
        subject = {
            "task_id": tid,
            "arm": arm,
            "checkpoint": point,
            "artifact_sha256": current,
        }
        evidence = {}
        for key in (
            *PRIMARY_ITEMS,
            *(["common_repair_lineage"] if point == POINTS[1] else []),
        ):
            source = next(iter(EVIDENCE_KINDS.get(key, {"contract_audit"})))
            evidence[key] = {
                "status": "pass",
                "evidence_ref": "synthetic",
                "subject": subject,
                "source_kind": "independent_review" if key in INDEPENDENT else source,
            }
        records.append(
            {
                **subject,
                "input_sha256": r["input_sha256"],
                "version_sha256": VERSION,
                "original_artifact_sha256": original,
                "execution": {"status": "native_captured", "evidence_ref": "synthetic"},
                "artifact": {"subject": subject, "evidence_ref": "synthetic"},
                "primary_evidence": evidence,
            }
        )
    return roster, records


def test_pairing_uses_full_assignment_and_keeps_composites_separate():
    roster, records = sample()
    for row in records:
        if row["task_id"] == "a" and row["arm"] == "L4":
            row["primary_evidence"]["independent_business"]["status"] = "fail"
    decisions = collect(roster, records, VERSION)
    group = summarize(roster, decisions, boot_reps=10, perm_reps=30)
    main = group["after_common_repair/primary"]
    assert main["predeclared_primary"] is True
    assert set(main["holm_secondary"]) == {"L2-L1", "L3-L2", "L4-L3", "L6-L5"}
    assert main["contrasts"]["L5-L4"]["effect"] == pytest.approx(1 / 3)
    for endpoint in ("c04", "60_percent", "100_percent"):
        assert group["raw_first/" + endpoint]["arms"]["L4"]["unknown"] == 3
    records[0]["primary_evidence"].pop("independent_business")
    decisions = collect(roster, records, VERSION)
    assert decisions["a", "L1", POINTS[0]]["primary"]["status"] == "unknown"


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "duplicate",
        "input",
        "version",
        "sha",
        "review",
        "lineage",
        "foreign_measurement",
    ],
)
def test_rejects_crossed_evidence_or_missing_assignments(change):
    roster, records = sample()
    if change == "missing":
        records.pop()
    elif change == "duplicate":
        records[-1] = copy.deepcopy(records[0])
    elif change == "input":
        records[-1]["input_sha256"] = digest("foreign")
    elif change == "version":
        records[-1]["version_sha256"] = digest("foreign")
    elif change == "sha":
        records[-1]["artifact_sha256"] = None
    elif change == "review":
        records[-1]["primary_evidence"]["independent_business"]["subject"] = dict(
            records[0]["artifact"]["subject"]
        )
    elif change == "lineage":
        records[-1]["original_artifact_sha256"] = digest("foreign")
    elif change == "foreign_measurement":
        records[-1]["artifact"]["subject"] = dict(records[0]["artifact"]["subject"])
    with pytest.raises(ValueError):
        collect(roster, records, VERSION)


def test_descriptive_development_without_registered_families():
    roster, records = sample()
    for row in roster:
        row["family"] = None
    decisions = collect(roster, records, VERSION)
    report = summarize(roster, decisions, descriptive=True)[
        "after_common_repair/primary"
    ]
    pair = report["contrasts"]["L5-L4"]
    assert pair["n_total"] == 3 and pair["n_families"] is None
    assert pair["effect"] == 0 and pair["family_permutation"] is None
    assert report["holm_secondary"] is None
    with pytest.raises(ValueError, match="family"):
        summarize(roster, decisions)
