"""公开请求的投影相容性预检。仅输出集合汇总，输入为已冻结的两个原始请求库存。"""

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from custodian_verify import (
    MISSING,
    canon,
    indexed,
    parse,
    paths_from,
    pointer,
    require,
    sha,
)

P0_REV = "11ae00df70920245500dff7a867e02d4de72c26a"
REV = "96390f907e4ffe72c04569d6b5571ef9424fd643"
DIRECTORY = "debug_tools/Datasets/online_updated"
REPORT = "report/requests_for_review.jsonl"
Q_NAME = re.compile(rb"Q[0-9]+\.json")
TRANSPORT = {"deviceInfo", "session", "userAuth", "pagination", "version", "bundleName"}
PROJECTION_SOURCES = {
    "audit_common.py": "cdd9a5d015e13a1a5ecad3b374e7d5ca58463a63b6f205cc218c2480aa9e868e",
    "publish_pr798_fixed_inputs.py": "510c27dae16b5b972e1042f1bceeb3e733e31508fcaab4a2f7ea0ebdeebd80ef",
}


def verified_file(path, digest):
    raw = path.read_bytes()
    require(sha(raw) == digest, "frozen_file_hash_mismatch")
    return raw


def card_object(raw):
    card = parse(raw.decode("utf-8-sig"))
    require(isinstance(card, dict), "invalid_card")
    return card


def legacy_view(card):
    """复现 audit_common.input_view 的公开业务投影，同时保留被内层覆盖的业务差异用于去重。"""
    nested = card.get("content")
    business = dict(nested) if isinstance(nested, dict) else dict(card)
    conflicts = {}
    if isinstance(nested, dict):
        for key, value in card.items():
            if key in TRANSPORT or key in {"content", "utterance"}:
                continue
            if key not in business:
                business[key] = value
            elif canon(business[key]) != canon(value):
                conflicts[key] = value
    for key in TRANSPORT:
        business.pop(key, None)
    overwritten = {}
    utterance = card.get("utterance")
    if isinstance(utterance, dict) and utterance.get("original") is not None:
        original = utterance["original"]
        if "originalQuery" in business and canon(business["originalQuery"]) != canon(
            original
        ):
            overwritten["originalQuery"] = business["originalQuery"]
        business["originalQuery"] = original
    return business, canon([business, conflicts, overwritten])


def baseline_inputs(manifest, directory):
    require(manifest["data_commit"] == P0_REV, "baseline_commit_mismatch")
    directory = directory.resolve()
    for name, info in sorted(manifest["files"].items()):
        if not Q_NAME.fullmatch(os.fsencode(name)):
            continue
        path = directory / name
        require(path.resolve().parent == directory, "source_outside_directory")
        raw = verified_file(path, info["sha256"])
        require(len(raw) == info["bytes"], "wrong_baseline_size")
        yield card_object(raw)


def local_git(repo, args, data=None):
    return subprocess.run(
        ["git", "--no-replace-objects", "-C", str(repo), *args],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=90,
        check=True,
        env={
            **os.environ,
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ALLOW_PROTOCOL": "",
        },
    ).stdout


def revision_inputs(repo, revision):
    tree = local_git(repo, ["ls-tree", "-z", f"{revision}:{DIRECTORY}"])
    oids = []
    for entry in tree.rstrip(b"\0").split(b"\0"):
        meta, name = entry.split(b"\t", 1)
        if not Q_NAME.fullmatch(name):
            continue
        mode, kind, oid = meta.split()
        require(mode in (b"100644", b"100755") and kind == b"blob", "invalid_q_blob")
        require(re.fullmatch(b"[0-9a-f]{40}", oid) is not None, "invalid_q_oid")
        oids.append(oid)
    require(oids, "empty_revision_inventory")
    stream = io.BytesIO(
        local_git(repo, ["cat-file", "--batch"], b"\n".join(oids) + b"\n")
    )
    for requested in oids:
        oid, kind, size = stream.readline().split()
        require(
            oid == requested and kind == b"blob" and size.isdigit(), "unexpected_blob"
        )
        raw = stream.read(int(size))
        require(len(raw) == int(size) and stream.read(1) == b"\n", "truncated_blob")
        header = b"blob " + size + b"\x00"
        require(
            hashlib.sha1(header + raw).hexdigest().encode() == oid, "blob_hash_mismatch"
        )
        yield card_object(raw)
    require(not stream.read(), "unexpected_git_output")


def aggregate(requests, baseline, revision):
    fields = set().union(*(row.keys() for row in requests))
    require(fields, "empty_projection_field_set")
    index = defaultdict(dict)
    targets = {canon(request) for request in requests}
    all_business = set()
    baseline_count = revision_count = 0
    for card in baseline:
        baseline_count += 1
        business, identity = legacy_view(card)
        all_business.add(identity)
        key = canon(business)
        if key in targets:
            index[key][identity] = business

    revision_matches = set()
    for card in revision:
        revision_count += 1
        inner = card["content"]
        if isinstance(inner, str):
            inner = parse(inner)
        require(isinstance(inner, dict), "invalid_incremental_content")
        business, identity = legacy_view({**card, "content": inner})
        all_business.add(identity)
        # 增量仅保留历史白名单内的 content 字段。所有已发布字段一定在白名单中，
        # 因而其完整字段并集可作必要条件；如果命中且另有未知白名单字段，不能确认。
        key = canon({k: v for k, v in inner.items() if k in fields})
        if key in targets:
            require(
                inner.keys() <= fields, "private_whitelist_required_for_possible_match"
            )
            revision_matches.add(key)
            index[key][identity] = business
    require(baseline_count and revision_count, "empty_inventory")

    unique = ambiguous = unmatched = 0
    paths_total = paths_matched = direct_agreed = direct_some = 0
    for request in requests:
        possible = index.get(canon(request), {})
        matches = len(possible)
        unique += matches == 1
        ambiguous += matches > 1
        unmatched += matches == 0
        # 分母按题内唯一候选路径，跨题分别计算；显式 null 与路径不存在分开。
        paths = paths_from(request)
        paths_total += len(paths)
        if not matches:
            continue
        paths_matched += len(paths)
        for path in paths:
            found = [pointer(record, path) for record in possible.values()]
            available = [canon(value) for value in found if value is not MISSING]
            direct_some += bool(available)
            direct_agreed += len(available) == matches and len(set(available)) == 1
    return {
        "schema": "public-report-request-preflight-v1",
        "report_requests": len(requests),
        "projection_field_union_count": len(fields),
        "baseline_q_records": baseline_count,
        "revision_q_records": revision_count,
        "distinct_business_contents_in_both_inventories": len(all_business),
        "requests_matching_incremental_projection": sum(
            canon(r) in revision_matches for r in requests
        ),
        "any_compatible_business_content": unique + ambiguous,
        "exactly_one_distinct_compatible_business_content": unique,
        "multiple_distinct_compatible_business_contents": ambiguous,
        "no_compatible_business_content": unmatched,
        "candidate_paths_declared_per_request_deduplicated": paths_total,
        "candidate_paths_in_requests_with_compatible_contents": paths_matched,
        "candidate_paths_with_direct_value_in_any_compatible_business_object": direct_some,
        "candidate_paths_with_same_direct_value_in_all_compatible_business_objects": direct_agreed,
        "frozen_selected_sample_value_agreement": None,
        "representative_source_identity_verified": None,
        "runtime_first_frame_verified": None,
        "independent_human_attestation": None,
    }


def run(inventory, expected_count):
    for filename, digest in PROJECTION_SOURCES.items():
        verified_file(inventory.rules / filename, digest)
    manifest = parse(
        verified_file(inventory.package / "manifest.json", inventory.release_hash)
    )
    request_hash = manifest["outputs"][REPORT]
    rows = indexed(verified_file(inventory.package / REPORT, request_hash))
    require(len(rows) == expected_count, "wrong_denominator")
    requests = [row["original_request"] for row in rows.values()]
    require(all(isinstance(r, dict) and r for r in requests), "invalid_request")
    baseline = parse(verified_file(inventory.p0, inventory.p0_hash))
    result = aggregate(
        requests,
        baseline_inputs(baseline, inventory.originals),
        revision_inputs(inventory.revision_repo, REV),
    )
    return {
        **result,
        "published_manifest_sha256": inventory.release_hash,
        "report_requests_file_sha256": request_hash,
        "baseline_manifest_sha256": inventory.p0_hash,
        "baseline_commit": P0_REV,
        "second_inventory_commit": REV,
        "baseline_projection_code_sha256": PROJECTION_SOURCES["audit_common.py"],
        "incremental_projection_code_sha256": PROJECTION_SOURCES[
            "publish_pr798_fixed_inputs.py"
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="仅新建聚合结果；默认打印到标准输出")
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    args = parser.parse_args()
    from source_lookup import load_inventory

    try:
        encoded = (
            json.dumps(
                run(load_inventory(args.inventory), args.expected_count),
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        ).encode()
        if args.out:
            with args.out.open("xb") as stream:
                stream.write(encoded)
        else:
            sys.stdout.buffer.write(encoded)
    except (KeyError, TypeError, ValueError, OSError, subprocess.SubprocessError):
        print("本次预检未完成，请在隔离环境核对冻结文件及格式。", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
