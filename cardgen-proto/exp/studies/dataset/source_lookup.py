"""供独立保管人核对报告题原始请求。输出仅含汇总，首帧、隔离与人工签认另核。"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from custodian_verify import (
    CheckError,
    canon,
    indexed,
    parse,
    require,
    sha,
)
from public_preflight import PROJECTION_SOURCES, legacy_view

OLD = "layout_comparison_20261124"
REVISION = "96390f907e4ffe72c04569d6b5571ef9424fd643"
P0_REVISION = "11ae00df70920245500dff7a867e02d4de72c26a"
CASE = re.compile(r"Q[0-9]{3,}")


@dataclass(frozen=True)
class Sources:
    package: Path
    identities: Path
    old_identities: Path
    rules: Path
    p0: Path
    originals: Path
    revision_repo: Path
    release_hash: str
    identity_manifest_hash: str
    old_identity_manifest_hash: str
    p0_hash: str


def load_inventory(config):
    """由保管人在独立渠道确认预期摘要，路径相对本配置位置解析。"""
    data = parse(config.read_bytes())
    path_names = (
        "package",
        "identities",
        "old_identities",
        "rules",
        "p0",
        "originals",
        "revision_repo",
    )
    digest_names = (
        "release_hash",
        "identity_manifest_hash",
        "old_identity_manifest_hash",
        "p0_hash",
    )
    require(set(data) == set(path_names + digest_names), "invalid_inventory_fields")
    for name in digest_names:
        require(
            isinstance(data[name], str) and re.fullmatch("[0-9a-f]{64}", data[name]),
            "invalid_inventory_hash",
        )
    for name in path_names:
        data[name] = (config.parent / data[name]).resolve()
    return Sources(**data)


@dataclass(frozen=True)
class ProjectionRules:
    sources: Sources

    @cached_property
    def whitelist(self):
        # 与 publish_pr798_fixed_inputs.release 一致，取旧发布全部身份行原投影字段的并集。
        data = released_file(
            self.sources.old_identities,
            self.sources.old_identity_manifest_hash,
            "identity_and_provenance.jsonl",
        )
        rows = indexed(data)
        require(bool(rows), "empty_whitelist_inventory")
        keys = set()
        for row in rows.values():
            original = row["source_task"]["original_request_for_review"]
            require(isinstance(original, dict), "invalid_whitelist_inventory")
            keys.update(original)
        require(bool(keys), "empty_revision_whitelist")
        return keys

    def confirm_versions(self):
        for name, digest in PROJECTION_SOURCES.items():
            verified_bytes(self.sources.rules / name, digest)


def verified_bytes(path, expected):
    raw = path.read_bytes()
    require(sha(raw) == expected, "file_hash_mismatch")
    return raw


def released_file(root, anchor, name):
    manifest = parse(verified_bytes(root / "manifest.json", anchor))
    return verified_bytes(root / name, manifest["outputs"][name])


def original_bytes(sources, p0_files, identity):
    case = identity.get("original_task_id")
    require(isinstance(case, str) and CASE.fullmatch(case), "invalid_source_locator")
    require(case in identity.get("source_case_ids", []), "representative_unlisted")
    origin = identity.get("source")
    name = f"{case}.json"
    if origin == OLD:
        require(name in p0_files, "baseline_source_not_in_inventory")
        path = sources.originals / name
        require(
            path.resolve().parent == sources.originals.resolve(),
            "invalid_source_locator",
        )
        return verified_bytes(path, p0_files[name]["sha256"])
    require(origin == REVISION, "unknown_source_version")
    # 用固定提交的本地 blob，忽略工作区版本与 replace refs，也禁止隐式拉取。
    result = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "-C",
            str(sources.revision_repo),
            "cat-file",
            "blob",
            f"{REVISION}:debug_tools/Datasets/online_updated/{name}",
        ],
        env={
            **os.environ,
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ALLOW_PROTOCOL": "",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=20,
    )
    require(result.returncode == 0, "revision_source_missing")
    return result.stdout


def compare_projection(raw, projection, origin, rules):
    card = parse(raw.decode("utf-8-sig"))
    require(
        isinstance(card, dict) and isinstance(projection, dict),
        "invalid_business_input",
    )
    if origin == OLD:
        expected, _ = legacy_view(card)
        business = expected
    else:
        require(origin == REVISION, "unknown_source_version")
        business = card["content"]
        if isinstance(business, str):
            business = parse(business)
        require(isinstance(business, dict), "invalid_business_input")
        expected = {
            key: value for key, value in business.items() if key in rules.whitelist
        }
    require(canon(expected) == canon(projection), "projection_mismatch")
    require(
        isinstance(projection.get("size"), str) and projection["size"], "missing_canvas"
    )
    require(
        any(projection.get(key) for key in ("originalQuery", "userQuery", "query")),
        "missing_query",
    )
    return business


def audit(sources, expected_count=219):
    projections = indexed(
        released_file(
            sources.package, sources.release_hash, "report/requests_for_review.jsonl"
        )
    )
    identity_rows = released_file(
        sources.identities,
        sources.identity_manifest_hash,
        "identity_and_provenance.jsonl",
    )
    identities = indexed(identity_rows)
    baseline = parse(verified_bytes(sources.p0, sources.p0_hash))
    require(baseline["data_commit"] == P0_REVISION, "baseline_revision_mismatch")
    require(len(projections) == expected_count, "report_denominator_mismatch")
    rules = ProjectionRules(sources)
    rules.confirm_versions()
    counts, origins, pair_hashes = Counter(), Counter(), []
    for tid, row in sorted(projections.items()):
        try:
            identity = identities.get(tid)
            require(identity is not None, "missing_identity")
            require(identity["collection"] == "report", "wrong_source_split")
            raw = original_bytes(sources, baseline["files"], identity)
            compare_projection(raw, row["original_request"], identity["source"], rules)
            pair_hashes.append(
                sha(canon([tid, sha(raw), sha(canon(row["original_request"]))]))
            )
            counts["verified"] += 1
            origins[identity["source"]] += 1
        except CheckError as exc:
            counts[str(exc)] += 1
        except (OSError, KeyError, ValueError, TypeError, subprocess.TimeoutExpired):
            counts["unreadable_or_malformed"] += 1
    return {
        "schema": "formal-raw-lookup-v2",
        "projection_source_sha256": PROJECTION_SOURCES,
        "lookup_code_sha256": sha(Path(__file__).read_bytes()),
        "legacy_view_code_sha256": sha(
            Path(sys.modules[legacy_view.__module__].__file__).read_bytes()
        ),
        "pr798_whitelist_manifest_sha256": sources.old_identity_manifest_hash
        if REVISION in origins
        else None,
        "expected": expected_count,
        "raw_request_projection_verified": counts["verified"],
        "errors": {k: v for k, v in sorted(counts.items()) if k != "verified"},
        "verified_by_source": dict(origins),
        "pair_hashes_folded_sha256": sha(canon(pair_hashes)),
        "public_manifest_sha256": sources.release_hash,
        "identity_manifest_sha256": sources.identity_manifest_hash,
        "baseline_manifest_sha256": sources.p0_hash,
        "first_frame_evidence_verified": None,
        "independent_human_attestation": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="新建聚合结果文件")
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    args = parser.parse_args()
    try:
        receipt = audit(load_inventory(args.inventory), args.expected_count)
        with args.out.open("x", encoding="utf-8") as output:
            json.dump(receipt, output, ensure_ascii=False, indent=2)
            output.write("\n")
    except (OSError, ValueError, KeyError, TypeError):
        print(
            "无法核验发布材料或写入新回执，请保管人在本地核对文件及摘要。",
            file=sys.stderr,
        )
        return 2
    print(
        f"逐题原请求核对 {receipt['raw_request_projection_verified']}/{receipt['expected']}。"
    )
    return int(bool(receipt["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
