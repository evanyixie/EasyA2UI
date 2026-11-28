import json
import subprocess
import sys

import pytest

import custodian_verify as cv


def put(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(cv.canon(content))
    return cv.sha(path.read_bytes())


def lines(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(cv.canon(r) + b"\n" for r in records))
    return cv.sha(path.read_bytes())


def fixture(
    base, *, empty=False, risk=False, missing=False, wrong=False, conflict=False
):
    package = base / "release"
    snapshots = base / "private"
    manifests, hashes, labels, cases, source_files = {}, {}, [], {}, {}
    queries = ["花园记录", "秘密气温甲", "办公安排乙", "运动睡眠丙"]
    for i, split in enumerate(cv.SPLITS):
        tid = "PRIVATE-" + str(i)
        q = queries[0] if risk and split == "report" else queries[i]
        req = {
            "size": "2x2",
            "userQuery": q,
            "candidateDataBindings": [],
            "candidateEventCandidates": [],
        }
        selected, events = {}, []
        if split == "report" and not risk:
            req["candidateDataBindings"] = [
                {
                    "capabilityId": "sensor",
                    "writeResultTo": "/live",
                    "candidateOutputFields": ["/items/0/value"]
                    if empty
                    else ["/value"],
                }
            ]
            if not empty:
                h = {"call": "openPrivateSession", "args": {"key": "private-key-value"}}
                req["candidateEventCandidates"] = [
                    {"action": h, "capabilityId": "sensorClick"}
                ]
                events = [{"handlers": [{**h, "args": {}} if wrong else h]}]
                selected["/live/value"] = 4 if conflict else 0
        fixed = {
            "task_id": tid,
            "size": "2x2",
            "display_title": q,
            "actions": events,
            "binding_samples": selected,
        }
        prefix = split + "/"
        hashes[split] = manifests[prefix + "layout_inputs.jsonl"] = lines(
            package / prefix / "layout_inputs.jsonl", [fixed]
        )
        manifests[prefix + "requests_for_review.jsonl"] = lines(
            package / prefix / "requests_for_review.jsonl",
            [{"task_id": tid, "original_request": req}],
        )
        if split == "report":
            archive = {
                "card": {"content": req, "unexposed_metadata": "private-source-field"}
            }
            source_files["archive"] = {
                "kind": "original_cardspec",
                "file": "orig.json",
                "sha256": put(snapshots / "orig.json", archive),
            }
            record = {"owner": tid, "value": {"items": []} if empty else 0}
            source_files["snap"] = {
                "kind": "runtime_snapshot",
                "file": "snap.json",
                "sha256": put(snapshots / "snap.json", record),
            }
            samples = (
                {}
                if risk or missing
                else {
                    "/live" if empty else "/live/value": {
                        "source": "snap",
                        "pointer": "/value",
                        "owner_pointer": "/owner",
                    }
                }
            )
            cases[tid] = {
                "cardspec": {"source": "archive", "pointer": "/card"},
                "samples": samples,
            }
        labels.append(
            {
                "task_id": tid,
                "source_split": split,
                "decision": "retained",
                "family_id": "0" if risk and split == "report" else str(i),
                "family_exposure": ["historical"] if risk and split == "report" else [],
            }
        )
    manifests["dataset_status.json"] = put(
        package / "dataset_status.json",
        {
            "counts_by_collection": dict.fromkeys(cv.SPLITS, 1),
            "layout_input_sha256": hashes,
        },
    )
    pubsha = put(package / "manifest.json", {"outputs": manifests})
    index, disp = snapshots / "sources.json", snapshots / "dispositions.jsonl"
    put(
        index,
        {
            "schema": "card-pairing-source-index-v1",
            "cases": cases,
            "sources": source_files,
        },
    )
    lines(disp, labels)
    return package, index, disp, pubsha


def test_private_aggregate_and_deterministic_hash(tmp_path):
    args = fixture(tmp_path)
    result = cv.verify(*args)
    assert result["status"] == "verified_declared_checks"
    assert result["by_split"]["report"]["pair_verified"] == 1
    assert result["counts"]["pair_outside_requested_scope"] == 3
    assert cv.verify(*args)["paired_rows_sha256"] == result["paired_rows_sha256"]
    payload = json.dumps(result, ensure_ascii=False)
    for private in (
        "PRIVATE-",
        "气温甲",
        "private-key-value",
        "openPrivate",
        "/live/",
        "orig.json",
    ):
        assert private not in payload


def test_verified_empty_collection_and_no_actions(tmp_path):
    result = cv.verify(*fixture(tmp_path, empty=True))
    assert result["status"] == "verified_declared_checks"
    assert result["counts"]["no_action_candidates"] == 1
    assert result["counts"]["indexed_candidate_in_empty_collection"] == 1


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"missing": True}, "candidate_sample_source_missing"),
        ({"wrong": True}, "fixed_action_outside_candidates"),
        ({"conflict": True}, "frozen_sample_mismatch"),
    ],
)
def test_source_mismatch(tmp_path, kwargs, code):
    result = cv.verify(*fixture(tmp_path, **kwargs))
    assert result["status"] == "review_needed" and result["issue_counts"][code] == 1


def test_no_candidates_and_exposure_separate(tmp_path):
    result = cv.verify(*fixture(tmp_path, risk=True))
    assert result["by_split"]["report"]["pair_verified"] == 1
    assert result["counts"]["no_binding_candidates"] == 1
    assert result["issue_counts"]["known_closed_family_exposure"] == 1
    for key in (
        "request_cross_split_groups",
        "fixed_contract_cross_split_groups",
        "registered_family_cross_split_groups",
        "wording_cross_split_groups",
        "lexical_similarity_pairs_ge_0_70",
    ):
        assert result["risk_counts"][key] == 1


def test_source_changed_after_freeze(tmp_path):
    args = fixture(tmp_path)
    (tmp_path / "private" / "orig.json").write_bytes(b"{}")
    assert cv.verify(*args)["issue_counts"] == {"source_hash_mismatch": 1}


def test_unreceived_private_index_failed_closed(tmp_path):
    args = fixture(tmp_path)
    index = args[1]
    obj = json.loads(index.read_bytes())
    obj["cases"] = {}
    put(index, obj)
    assert cv.verify(*args)["issue_counts"] == {"original_pair_evidence_missing": 1}


def test_missing_selected_binding_and_false_empty_are_separate(tmp_path):
    args = fixture(tmp_path)
    idx = json.loads(args[1].read_bytes())
    sources = cv.Sources(args[1], idx)
    rr = json.loads((args[0] / "report/requests_for_review.jsonl").read_bytes())
    fixed = json.loads((args[0] / "report/layout_inputs.jsonl").read_bytes())
    fixed["content_groups"] = [
        {"selected_value_sources": [{"bindings": [{"path": "/undeclared"}]}]}
    ]
    with pytest.raises(cv.CheckError, match="selected_source_missing_frozen_binding"):
        cv.audit_case(
            rr["task_id"],
            rr["original_request"],
            fixed,
            idx["cases"][rr["task_id"]],
            sources,
            cv.Counter(),
        )


def test_private_source_digest_attestation(tmp_path):
    args = fixture(tmp_path)
    with pytest.raises(cv.CheckError, match="source_index_hash_mismatch"):
        cv.verify(*args, source_index_sha="0" * 64)


def test_cli_only_exports_aggregate(tmp_path):
    package, index, disp, manifest_hash = fixture(tmp_path)
    out = tmp_path / "receipt.json"
    run = subprocess.run(
        [
            sys.executable,
            cv.__file__,
            "--package",
            str(package),
            "--source-index",
            str(index),
            "--dispositions",
            str(disp),
            "--receipt",
            str(out),
            "--manifest-sha256",
            manifest_hash,
        ],
        capture_output=True,
        check=False,
    )
    assert run.returncode == 0 and run.stdout.strip() == b"verified_declared_checks"
    assert json.loads(out.read_bytes())["by_split"]["report"]["pair_verified"] == 1
    assert b"PRIVATE-" not in out.read_bytes()
