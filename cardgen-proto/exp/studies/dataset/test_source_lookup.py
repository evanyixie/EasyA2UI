import json
from dataclasses import replace

import pytest

import source_lookup as app


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False).encode()
    path.write_bytes(raw)
    return app.sha(raw)


def release(root, name, row):
    file_hash = write(root / name, row)
    return write(root / "manifest.json", {"outputs": {name: file_hash}})


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    # 合成测试在临时目录验证规则版本哈希链。
    rules = tmp_path / "rules"
    digest = write(rules / "rules.py", "rule-fixture")
    monkeypatch.setattr(app, "PROJECTION_SOURCES", {"rules.py": digest})
    sources = app.Sources(
        package=tmp_path / "pub",
        identities=tmp_path / "ids",
        originals=tmp_path / "src",
        p0=tmp_path / "p0",
        rules=rules,
        old_identities=tmp_path / "old",
        revision_repo=tmp_path / "repo",
        release_hash="a" * 64,
        identity_manifest_hash="b" * 64,
        old_identity_manifest_hash="c" * 64,
        p0_hash="d" * 64,
    )
    projected = {
        "size": "2x2",
        "userQuery": "private-test-query",
        "candidateDataBindings": [],
        "originalQuery": "outer",
        "title": "A",
    }
    raw_hash = write(
        sources.originals / "Q900001.json",
        {
            "content": {
                "size": "2x2",
                "userQuery": "private-test-query",
                "candidateDataBindings": [],
            },
            "utterance": {"original": "outer"},
            "title": "A",
            "session": "internal",
        },
    )
    req_hash = release(
        sources.package,
        "report/requests_for_review.jsonl",
        {"task_id": "T-test", "original_request": projected},
    )
    idx_hash = release(
        sources.identities,
        "identity_and_provenance.jsonl",
        {
            "task_id": "T-test",
            "source": app.OLD,
            "original_task_id": "Q900001",
            "source_case_ids": ["Q900001"],
            "collection": "report",
        },
    )
    base_hash = write(
        sources.p0,
        {
            "data_commit": app.P0_REVISION,
            "files": {"Q900001.json": {"sha256": raw_hash}},
        },
    )
    return replace(
        sources,
        release_hash=req_hash,
        identity_manifest_hash=idx_hash,
        p0_hash=base_hash,
    )


def test_verified_is_aggregate_only(bundle):
    receipt = app.audit(bundle, 1)
    assert receipt["raw_request_projection_verified"] == 1
    assert not receipt["errors"]
    assert (
        receipt["independent_human_attestation"]
        is receipt["first_frame_evidence_verified"]
        is None
    )
    for private in ("T-test", "Q900001", "private-test-query", "private_extra"):
        assert private not in json.dumps(receipt)
    assert receipt == app.audit(bundle, 1)


def test_raw_file_modified(bundle):
    write(bundle.originals / "Q900001.json", {"size": "2x4"})
    assert app.audit(bundle, 1)["errors"] == {"file_hash_mismatch": 1}


def test_release_and_denominator_fail_closed(bundle):
    with pytest.raises(app.CheckError, match="report_denominator_mismatch"):
        app.audit(bundle, 2)
    write(bundle.package / "report/requests_for_review.jsonl", {})
    with pytest.raises(app.CheckError, match="file_hash_mismatch"):
        app.audit(bundle, 1)


def test_malformed_identity_never_traverses(bundle):
    for case in ("../Q900001", ["x"], "Q900001.json"):
        with pytest.raises(app.CheckError, match="invalid_source_locator"):
            app.original_bytes(bundle, {}, {"original_task_id": case})


def test_old_projection_is_exact_and_merges_envelope(bundle):
    rules = app.ProjectionRules(bundle)
    card = {"size": "2x2", "userQuery": "q", "originalQuery": "internal", "flag": False}
    raw = app.canon(
        {
            "content": card,
            "utterance": {"original": "outer"},
            "scope": "subject",
            "session": "transport",
        }
    )
    p = {**card, "originalQuery": "outer", "scope": "subject"}
    assert app.compare_projection(raw, p, app.OLD, rules) == p
    for wrong in ({k: v for k, v in p.items() if k != "scope"}, {**p, "flag": 0}, card):
        with pytest.raises(app.CheckError, match="projection_mismatch"):
            app.compare_projection(raw, wrong, app.OLD, rules)


def test_revision_uses_exact_frozen_old_universe(bundle):
    row = {
        "task_id": "R-old",
        "source_task": {
            "original_request_for_review": {
                "size": "2x2",
                "userQuery": "x",
                "candidateDataBindings": [],
                "brandNewOptional": None,
            }
        },
    }
    anchor = release(bundle.old_identities, "identity_and_provenance.jsonl", row)
    rules = app.ProjectionRules(replace(bundle, old_identity_manifest_hash=anchor))
    inner = {
        "size": "2x2",
        "userQuery": "q",
        "brandNewOptional": False,
        "unregistered": 1,
    }
    p = {k: v for k, v in inner.items() if k != "unregistered"}
    for obj in (inner, json.dumps(inner)):
        raw = app.canon({"utterance": {"original": "ignore outside"}, "content": obj})
        assert app.compare_projection(raw, p, app.REVISION, rules) == inner
        with pytest.raises(app.CheckError, match="projection_mismatch"):
            app.compare_projection(
                raw,
                {k: v for k, v in p.items() if k != "brandNewOptional"},
                app.REVISION,
                rules,
            )
    with pytest.raises(app.CheckError, match="file_hash_mismatch"):
        app.compare_projection(raw, p, app.REVISION, app.ProjectionRules(bundle))


def test_full_verifier_anchors_supplied_card_and_keeps_outer_query(tmp_path, bundle):
    import custodian_verify_v2 as v2
    from test_custodian_verify import fixture

    pkg, idx, disp, pkg_sha = fixture(tmp_path / "complete")
    index = json.loads(idx.read_bytes())
    (tid,) = index["cases"]
    request = json.loads((pkg / "report/requests_for_review.jsonl").read_bytes())[
        "original_request"
    ]
    card = {
        "content": {k: v for k, v in request.items() if k != "userQuery"},
        "userQuery": request["userQuery"],
    }
    raw_sha = write(bundle.originals / "Q900001.json", card)
    p0_hash = write(
        bundle.p0,
        {
            "data_commit": app.P0_REVISION,
            "files": {"Q900001.json": {"sha256": raw_sha}},
        },
    )
    identity_hash = release(
        bundle.identities,
        "identity_and_provenance.jsonl",
        {
            "task_id": tid,
            "source": app.OLD,
            "original_task_id": "Q900001",
            "source_case_ids": ["Q900001"],
            "collection": "report",
        },
    )
    inventory = replace(
        bundle,
        p0_hash=p0_hash,
        identity_manifest_hash=identity_hash,
        package=pkg,
        release_hash=pkg_sha,
    )

    def signed(card_value):
        index["sources"]["archive"]["sha256"] = write(
            idx.parent / "orig.json", {"card": card_value}
        )
        write(idx, index)
        return v2.verify(pkg, idx, disp, pkg_sha, inventory=inventory)

    assert signed(card)["status"] == "verified_declared_checks"
    assert signed({"content": request})["issue_counts"] == {
        "indexed_source_is_not_frozen_original": 1
    }
    assert signed(
        {"content": {"size": request["size"], "userQuery": request["userQuery"]}}
    )["issue_counts"] == {"indexed_source_is_not_frozen_original": 1}


def test_revision_only_reads_the_frozen_request(monkeypatch, bundle):
    import subprocess

    def catfile(args, **kwargs):
        assert (
            args[-1]
            == f"{app.REVISION}:debug_tools/Datasets/online_updated/Q900002.json"
        )
        assert kwargs["env"]["GIT_ALLOW_PROTOCOL"] == ""
        return subprocess.CompletedProcess(args, 0, b"{}")

    monkeypatch.setattr(app.subprocess, "run", catfile)
    assert (
        app.original_bytes(
            bundle,
            {},
            {
                "source": app.REVISION,
                "original_task_id": "Q900002",
                "source_case_ids": ["Q900002"],
            },
        )
        == b"{}"
    )


def test_private_inventory_resolves_external_rules_relative_to_config(tmp_path, bundle):
    from dataclasses import asdict
    from os.path import relpath

    config = tmp_path / "operator" / "inventory.json"
    values = {
        key: relpath(value, config.parent)
        if isinstance(value, type(tmp_path))
        else value
        for key, value in asdict(bundle).items()
    }
    write(config, values)
    inventory = app.load_inventory(config)
    assert inventory == bundle
    assert app.audit(inventory, 1)["raw_request_projection_verified"] == 1
    (inventory.rules / "rules.py").write_bytes(b"edited")
    with pytest.raises(app.CheckError, match="file_hash_mismatch"):
        app.audit(inventory, 1)
