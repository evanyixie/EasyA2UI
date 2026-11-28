"""核对冻结商用登记表与发布选中路径的类型样例。只输出聚合，运行时真实值另核。"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from custodian_verify import bad_json, pairs, require, sha

REGISTRY_PREFIX = "widget_service/cloud/data/capabilities/"
SCOPES = ("app-11.7.7.300_rom-7.0", "app-11.7.9.300_rom-7.0")
SOURCE_REVISIONS = (
    "11ae00df70920245500dff7a867e02d4de72c26a",
    "96390f907e4ffe72c04569d6b5571ef9424fd643",
)
MISSING = object()


def parse(raw):
    return json.loads(
        raw,
        object_pairs_hook=pairs,
        parse_constant=lambda _: bad_json(),
        parse_float=Decimal,
    )


def verified_file(path, expected):
    raw = path.read_bytes()
    require(sha(raw) == expected, "frozen_file_hash_mismatch")
    return raw


def rows(raw):
    result = {}
    for line in raw.splitlines():
        if line.strip():
            row = parse(line)
            tid = row["task_id"]
            require(
                isinstance(tid, str) and tid and tid not in result,
                "invalid_task_inventory",
            )
            result[tid] = row
    return result


def registry_files(archive_path, archive_sha, registry_repo):
    # 仅打开预登记的三个商用登记表 blob。归档还含开发题与配置，两者均不参加逐题对照。
    archive = parse(verified_file(archive_path, archive_sha))
    names = ("registry_ranges.json", *(v + "/data_capabilities.json" for v in SCOPES))
    files, hashes = {}, {}
    env = {
        **os.environ,
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ALLOW_PROTOCOL": "",
    }
    for name in names:
        meta = archive["sources"][name]
        require(
            meta["path"] == REGISTRY_PREFIX + name
            and (meta["historical_revision"], meta["simulated_base_revision"])
            == SOURCE_REVISIONS
            and meta["content_identical"] is True
            and meta["simulated_base_sha256"] == meta["historical_sha256"],
            "registry_anchor_mismatch",
        )
        git = ["git", "--no-replace-objects", "-C", str(registry_repo)]
        oid = meta["git_blob"]
        require(re.fullmatch(r"[0-9a-f]{40}", oid), "invalid_registry_blob")
        for revision in SOURCE_REVISIONS:
            resolved = (
                subprocess.check_output(
                    [*git, "rev-parse", "--verify", revision + ":" + meta["path"]],
                    stderr=subprocess.DEVNULL,
                    env=env,
                    timeout=20,
                )
                .strip()
                .decode("ascii")
            )
            require(resolved == oid, "registry_revision_mismatch")
        raw = subprocess.check_output(
            [*git, "cat-file", "blob", oid],
            stderr=subprocess.DEVNULL,
            env=env,
            timeout=20,
        )
        git_header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
        require(
            hashlib.sha1(git_header + raw).hexdigest() == oid, "registry_blob_mismatch"
        )
        hashes[name] = sha(raw)
        require(hashes[name] == meta["historical_sha256"], "registry_bytes_mismatch")
        files[name] = parse(raw)
    ranges = files["registry_ranges.json"]["ranges"]
    require(
        sorted(r["registryVersion"] for r in ranges) == sorted(SCOPES),
        "wrong_registry_ranges",
    )
    caps = {}
    for version in SCOPES:
        entries = files[version + "/data_capabilities.json"]
        caps[version] = {c["id"]: c["outputSchema"] for c in entries}
        require(len(caps[version]) == len(entries), "duplicate_capability_id")
    return ranges, caps, hashes


def version_key(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", value):
        return None
    result = [int(part) for part in value.split(".")]
    while result and result[-1] == 0:
        result.pop()
    return tuple(result)


def runtime_version(key, raw):
    # 两个冻结源提交的 CapabilityRegistry 同法提取数字，ROM 取首个点版本的前两段。
    # 无版本凭据保留未知，不使用服务当前默认值。
    if not isinstance(raw, str):
        return None
    if key == "romVersion":
        match = re.search(r"[0-9]+(?:\.[0-9]+)+", raw)
        if match:
            return version_key(".".join(match[0].split(".")[:2]))
    match = re.search(r"[0-9]+(?:\.[0-9]+)*", raw)
    return version_key(match[0]) if match else None


def possible_scopes(request, ranges):
    known = {}
    for key in ("appVersion", "romVersion"):
        aliases = ("appVersion", "prdVer") if key == "appVersion" else (key,)
        for alias in aliases:
            if alias not in request:
                continue
            parsed = runtime_version(key, request[alias])
            if parsed is None or (key in known and parsed != known[key]):
                return "invalid_version_metadata", []
            known[key] = parsed
    versions = [
        r["registryVersion"]
        for r in ranges
        if all(
            version_key(r[k]["minInclusive"]) <= v < version_key(r[k]["maxExclusive"])
            for k, v in known.items()
        )
    ]
    if not versions:
        return "outside_approved_ranges", []
    if len(known) == 2 and len(versions) == 1:
        return "identified", versions
    if len(known) == 2:
        return "overlapping_ranges", versions
    return (
        "partial_version_metadata" if known else "absent_version_metadata"
    ), versions


def tokens(path):
    require(
        isinstance(path, str)
        and (not path or path.startswith("/"))
        and not re.search(r"~(?![01])", path),
        "invalid_pointer",
    )
    return (
        tuple(s.replace("~1", "/").replace("~0", "~") for s in path[1:].split("/"))
        if path
        else ()
    )


def declarations(request):
    result = defaultdict(list)
    for binding in request.get("candidateDataBindings", []):
        root = tokens(binding["writeResultTo"])
        # candidateOutputFields 均是相对输出根的 JSON 指针。能力不可从根名/字段尾名推断。
        fields = binding.get("candidateOutputFields", [])
        require(isinstance(fields, list), "invalid_candidate_fields")
        for field in set(fields):
            relative = tokens(field)
            require(relative, "invalid_relative_path")
            result[root + relative].append((binding["capabilityId"], relative))
    return result


def kind(value):
    if type(value) in (int, Decimal):
        return "number"
    return type(value).__name__


def equal(a, b):
    if kind(a) != kind(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(equal(i, j) for i, j in zip(a, b, strict=True))
    return a == b


def concrete(value, rest):
    for segment in rest:
        if isinstance(value, dict) and segment in value:
            value = value[segment]
        elif isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", segment) or int(segment) >= len(
                value
            ):
                return "concrete_index_absent", MISSING
            value = value[int(segment)]
        else:
            return "field_missing_from_concrete_sample", MISSING
    return "available", value


def example(schema, path):
    for pos, segment in enumerate(path):
        if "sampleValue" in schema:
            return concrete(schema["sampleValue"], path[pos:])
        if schema.get("type") == "array":
            # items 是元素类型，不是有归属的第 0 或第 n 项。只有具体数组才赋予索引。
            return "array_index_without_concrete_sample", MISSING
        if segment not in schema.get("properties", {}):
            return "registry_field_absent", MISSING
        schema = schema["properties"][segment]
    return (
        ("available", schema["sampleValue"])
        if "sampleValue" in schema
        else ("sample_value_absent", MISSING)
    )


def compare_path(frozen, declarations_for_path, versions, caps):
    if not declarations_for_path:
        return "no_exact_candidate_declaration"
    if len(declarations_for_path) != 1:
        return "ambiguous_candidate_declaration"
    if not versions:
        return "no_supported_registry_scope"
    capability, relative = declarations_for_path[0]
    views = [
        example(caps[version][capability], relative)
        if capability in caps[version]
        else ("registry_capability_absent", MISSING)
        for version in versions
    ]
    status, value = views[0]
    if any(
        s != status or (s == "available" and not equal(value, v)) for s, v in views[1:]
    ):
        return "registry_versions_disagree"
    if status != "available":
        return status
    return "same_example" if equal(value, frozen) else "different_example"


def states():
    return {"paths": Counter(), "cases": Counter(), "frozen_empty_values": Counter()}


def record(result, outcomes, frozen):
    counts = Counter(outcomes.values())
    result["paths"].update(counts)
    matched = counts["same_example"]
    different = counts["different_example"]
    total = len(outcomes)
    cases = result["cases"]
    if not total:
        category = "no_paths"
    elif matched == total:
        category = "all_same_example"
    elif matched:
        category = "some_same_example"
    else:
        category = "no_same_example"
    cases[category] += 1
    cases["with_different_example"] += bool(different)
    cases["with_missing_or_unresolved"] += total > matched + different
    for p in outcomes:
        if p in frozen:
            val = frozen[p]
            if val is None or (isinstance(val, (str, dict, list)) and not val):
                result["frozen_empty_values"][kind(val)] += 1
    result["cases"]["total"] += 1


def selected_refs(contract):
    mentioned, conflicts = set(), set()
    frozen = contract["binding_samples"]
    for group in contract["content_groups"]:
        for source in group.get("selected_value_sources", []):
            for binding in source.get("bindings", []):
                path = binding["path"]
                mentioned.add(path)
                if (
                    path in frozen
                    and "sample_value" in binding
                    and not equal(binding["sample_value"], frozen[path])
                ):
                    conflicts.add(path)
    for unit in contract["semantic_units"]:
        take = unit.get("take")
        if isinstance(take, dict) and "path" in take:
            mentioned.add(take["path"])
    return mentioned, conflicts


def aggregate(requests, contracts, ranges, caps, expected):
    require(
        requests.keys() == contracts.keys() and len(requests) == expected,
        "wrong_report_inventory",
    )
    scope_status, version_counts = Counter(), Counter()
    all_frozen, directly_selected = states(), states()
    for tid, row in requests.items():
        request, contract = row["original_request"], contracts[tid]
        require(request.get("size") == contract["size"], "canvas_mismatch")
        status, versions = possible_scopes(request, ranges)
        scope_status[status] += 1
        version_counts[len(versions)] += 1
        declared = declarations(request)
        frozen = contract["binding_samples"]
        require(isinstance(frozen, dict), "invalid_frozen_sample_map")
        selected, conflicts = selected_refs(contract)
        outcomes = {}
        for path, sample in frozen.items():
            outcomes[path] = (
                "selected_value_conflict_in_release"
                if path in conflicts
                else compare_path(sample, declared[tokens(path)], versions, caps)
            )
        record(all_frozen, outcomes, frozen)
        record(
            directly_selected,
            {p: outcomes.get(p, "no_frozen_sample") for p in selected},
            frozen,
        )
    return {
        "schema": "frozen-registry-selected-path-diagnostics-v1",
        "report_cases": expected,
        "registry_version_metadata_cases": scope_status,
        "compatible_registry_scope_count_by_case": version_counts,
        "frozen_binding_samples": all_frozen,
        "distinct_paths_explicitly_referenced_in_groups_or_semantic_units": directly_selected,
        "scope_note": "缺版本时仅对照已批准且与已知维度相容的全部版本的一致样例；这不肯定该设备位于登记范围。",
        "source_note": "商用 outputSchema.sampleValue 是类型样例。相同/不同描述冻结值与登记样例的逐字段 JSON 比较。",
        "array_note": "数组下标须落在具体 sampleValue 数组内。通用 items 样例不赋予任何实际元素索引。",
        "case_note": "每题按路径去重。全同/部分同/无同/无路径互斥；含不同、含缺证两项可重叠。",
        "cases_with_same_task_first_frame_proven_by_this_source": 0,
        "actual_same_task_first_frame_agreement": None,
        "human_attestation": None,
    }


def run(args):
    manifest = parse(
        verified_file(args.package / "manifest.json", args.manifest_sha256)
    )
    names = ("report/requests_for_review.jsonl", "report/layout_inputs.jsonl")
    hashes = {name: manifest["outputs"][name] for name in names}
    requests, contracts = (
        rows(verified_file(args.package / name, hashes[name])) for name in names
    )
    ranges, caps, registry_hashes = registry_files(
        args.archive, args.archive_sha256, args.repo
    )
    return {
        **aggregate(requests, contracts, ranges, caps, expected=args.expected_count),
        "published_manifest_sha256": args.manifest_sha256,
        "report_file_sha256": hashes,
        "registry_archive_sha256": args.archive_sha256,
        "registry_file_sha256": registry_hashes,
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--out", type=Path, help="只新建匿名汇总，默认打印汇总")
    for name in ("package", "archive", "repo"):
        cli.add_argument("--" + name, type=Path, required=True)
    for name in ("manifest-sha256", "archive-sha256"):
        cli.add_argument("--" + name, required=True)
    cli.add_argument("--expected-count", type=int, required=True)
    args = cli.parse_args()
    try:
        payload = (
            json.dumps(run(args), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode()
        if args.out:
            with args.out.open("xb") as output:
                output.write(payload)
        else:
            sys.stdout.buffer.write(payload)
    except (KeyError, OSError, ValueError, TypeError, subprocess.SubprocessError):
        print(
            "登记样例汇总未完成，请核对冻结文件、批准版本与目标文件。", file=sys.stderr
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
