"""保管侧离线核对原请求、选择合同和可信首帧。只导出聚合数量与哈希。"""

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

SPLITS = ("dev", "report", "extension", "reserve")
MISSING = object()
EMPTY_INDEX = object()


class CheckError(ValueError):
    """错误码是公开的常量，不输出私域异常或字段值。"""


def require(ok, code):
    if not ok:
        raise CheckError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canon(data):
    return json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def signature(data):
    return sha(canon(data))


def pairs(items):
    record = {}
    for key, value in items:
        require(key not in record, "duplicate_json_key")
        record[key] = value
    return record


def parse(raw):
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: bad_json())


def bad_json():
    raise CheckError("nonfinite_json")


def indexed(raw):
    answer = {}
    for line in raw.splitlines():
        if line.strip():
            r = parse(line)
            tid = r["task_id"]
            require(
                isinstance(tid, str) and tid and tid not in answer,
                "duplicate_or_invalid_task_id",
            )
            answer[tid] = r
    return answer


def pointer(value, path, *, detect_empty_index=False):
    if path == "":
        return value
    require(
        isinstance(path, str)
        and path.startswith("/")
        and not re.search(r"~(?![01])", path),
        "invalid_json_pointer",
    )
    for tok in path[1:].split("/"):
        tok = tok.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and tok in value:
            value = value[tok]
        elif detect_empty_index and value == [] and re.fullmatch("0|[1-9][0-9]*", tok):
            return EMPTY_INDEX
        elif (
            isinstance(value, list)
            and re.fullmatch("0|[1-9][0-9]*", tok)
            and int(tok) < len(value)
        ):
            value = value[int(tok)]
        else:
            return MISSING
    return value


class Sources:
    def __init__(self, index_path, data):
        self.base = index_path.parent
        self.spec = data["sources"]
        self.cache = {}

    def value(self, locator, permitted):
        key = locator["source"]
        spec = self.spec[key]
        require(spec["kind"] in permitted, "source_role_mismatch")
        if key not in self.cache:
            path = (self.base / spec["file"]).resolve()
            require(
                path.is_relative_to(self.base.resolve()),
                "source_file_outside_inventory",
            )
            raw = path.read_bytes()
            require(sha(raw) == spec["sha256"], "source_hash_mismatch")
            self.cache[key] = raw
        raw = self.cache[key]
        line = locator.get("line")
        if line is not None:
            require(
                type(line) is int and 1 <= line <= len(raw.splitlines()),
                "invalid_source_line",
            )
            raw = raw.splitlines()[line - 1]
        value = pointer(parse(raw), locator.get("pointer", ""))
        require(value is not MISSING, "evidence_pointer_missing")
        return (
            value,
            spec["kind"],
            signature([spec["sha256"], line, locator.get("pointer", "")]),
        )


def paths_from(req):
    paths = defaultdict(set)
    bindings = req.get("candidateDataBindings") or []
    require(isinstance(bindings, list), "invalid_binding_list")
    for b in bindings:
        base = b["writeResultTo"].rstrip("/")
        require(not base or base.startswith("/"), "invalid_binding_root")
        fields = b.get("candidateOutputFields") or []
        require(isinstance(fields, list), "invalid_candidate_fields")
        for field in fields:
            require(isinstance(field, str) and bool(field), "invalid_binding_field")
            path = (
                field
                if field.startswith(base + "/")
                else base + "/" + field.lstrip("/")
            )
            paths[path].add(b.get("capabilityId"))
    return paths


def words(req):
    for field in ("originalQuery", "userQuery"):
        value = req.get(field)
        if isinstance(value, str) and value.strip():
            yield "".join(
                c
                for c in unicodedata.normalize("NFKC", value).casefold()
                if c.isalnum()
            )


def audit_case(tid, req, contract, evidence, sources, counts):
    # 哈希既区分源文件精确字节、JSONL行/指针，也区分选中 CardSpec 的规范 JSON。
    card, _, card_location = sources.value(evidence["cardspec"], {"original_cardspec"})
    business = card.get("content", card)
    require(
        isinstance(req, dict) and isinstance(business, dict), "invalid_source_request"
    )
    require(
        business.get("size") == contract.get("size") and bool(contract.get("size")),
        "caller_size_mismatch",
    )
    for k, v in req.items():
        require(
            k in business and canon(business[k]) == canon(v),
            "original_request_mismatch",
        )
    for k in (
        "size",
        "userQuery",
        "originalQuery",
        "candidateDataBindings",
        "candidateEventCandidates",
    ):
        if business.get(k):
            require(k in req, "source_projection_dropped_field")
    path_capabilities = paths_from(business)
    full_paths = set(path_capabilities)
    raw_events = business.get("candidateEventCandidates") or []
    require(isinstance(raw_events, list), "invalid_event_list")
    handlers = []
    for event in raw_events:
        handler = event.get("action")
        require(
            isinstance(handler, dict)
            and isinstance(handler.get("call"), str)
            and bool(handler["call"]),
            "invalid_event_handler",
        )
        handlers.append(signature(handler))
    frozen_actions = contract.get("actions", [])
    require(isinstance(frozen_actions, list), "invalid_fixed_action_list")
    for action in frozen_actions:
        accepted = action["handlers"]
        require(isinstance(accepted, list) and accepted, "fixed_action_missing_handler")
        require(
            all(signature(h) in handlers for h in accepted),
            "fixed_action_outside_candidates",
        )
    counts["no_action_candidates"] += not raw_events
    counts["no_selected_actions"] += not frozen_actions
    counts["no_binding_candidates"] += not full_paths
    frozen_samples = contract.get("binding_samples", {})
    require(isinstance(frozen_samples, dict), "invalid_fixed_samples")
    require(
        not (set(frozen_samples) - full_paths), "selected_binding_outside_candidates"
    )
    for group in contract.get("content_groups", []):
        for source in group.get("selected_value_sources", []):
            for binding in source.get("bindings", []):
                p = binding["path"]
                require(p in frozen_samples, "selected_source_missing_frozen_binding")
                if "sample_value" in binding:
                    require(
                        canon(binding["sample_value"]) == canon(frozen_samples[p]),
                        "selected_source_sample_conflict",
                    )
    for unit in contract.get("semantic_units", []):
        take = unit.get("take")
        if isinstance(take, dict) and "path" in take:
            require(
                take["path"] in frozen_samples, "selected_semantic_unit_missing_binding"
            )
    records = evidence.get("samples", {})
    require(isinstance(records, dict), "invalid_sample_map")
    observed, proven = {}, {}
    for path, loc in records.items():
        require(isinstance(path, str) and path.startswith("/"), "invalid_sample_path")
        require(
            path in full_paths
            or any(p.startswith(path.rstrip("/") + "/") for p in full_paths),
            "sample_outside_candidates",
        )
        val, role, locsha = sources.value(
            loc,
            {
                "runtime_snapshot",
                "capability_fixture",
                "original_cardspec",
                "derived_fixture",
            },
        )
        if role == "runtime_snapshot":
            owner, _, _ = sources.value(
                {**loc, "pointer": loc["owner_pointer"]}, {role}
            )
            require(owner in (tid, signature(card)), "snapshot_owner_mismatch")
        if role == "capability_fixture":
            capability, _, _ = sources.value(
                {**loc, "pointer": loc["capability_pointer"]}, {role}
            )
            allowed_caps = {
                c
                for p, ids in path_capabilities.items()
                for c in ids
                if p == path or p.startswith(path.rstrip("/") + "/")
            }
            require(
                isinstance(capability, str) and capability in allowed_caps,
                "fixture_capability_mismatch",
            )
        if role == "original_cardspec":
            original = evidence["cardspec"]
            origin_path = original.get("pointer", "")
            require(
                original["source"] == loc["source"]
                and original.get("line") == loc.get("line")
                and (
                    loc.get("pointer", "") == origin_path
                    or loc.get("pointer", "").startswith(origin_path + "/")
                ),
                "sample_from_another_cardspec",
            )
        if role == "derived_fixture":
            # 仅验派生记录、输入与算法文件摘要。此工具不会执行保管方提供的代码。
            linked, _, _ = sources.value(
                {**loc, "pointer": loc["input_hash_pointer"]}, {role}
            )
            algorithm, _, _ = sources.value(
                {**loc, "pointer": loc["algorithm_hash_pointer"]}, {role}
            )
            recipe = sources.spec[loc["algorithm_source"]]
            require(
                recipe["kind"] == "derivation_code"
                and linked == signature(card)
                and sha((sources.base / recipe["file"]).read_bytes())
                == recipe["sha256"]
                == algorithm,
                "derived_fixture_lineage_mismatch",
            )
            counts["derivations_linked_not_reexecuted"] += 1
        observed[path] = val
        proven[path] = [role, locsha, signature(val)]
        counts["sample_source_" + role] += 1
    for path in full_paths:
        value = observed.get(path, MISSING)
        if value is MISSING:
            parents = sorted(
                (p for p in observed if path.startswith(p.rstrip("/") + "/")),
                key=len,
                reverse=True,
            )
            for parent in parents:
                suffix = path[len(parent) :]
                value = pointer(observed[parent], suffix, detect_empty_index=True)
                # 空集合是有源首帧；若固定合同仍要求具体子值，应明确冲突。
                if value is EMPTY_INDEX:
                    require(
                        path not in frozen_samples,
                        "frozen_value_below_empty_collection",
                    )
                    counts["indexed_candidate_in_empty_collection"] += 1
                    break
                if value is not MISSING:
                    break
            else:
                raise CheckError("candidate_sample_source_missing")
        if path in frozen_samples:
            require(
                value is not MISSING and canon(value) == canon(frozen_samples[path]),
                "frozen_sample_mismatch",
            )
        if value is not MISSING and (
            value is None or value == "" or value == [] or value == {}
        ):
            counts["explicit_empty_sample"] += 1
    contract_sha = signature({k: v for k, v in contract.items() if k != "task_id"})
    evidence_digest = signature(
        [
            tid,
            signature(card),
            card_location,
            signature(req),
            sorted(full_paths),
            signature(business.get("candidateDataBindings") or []),
            sorted(handlers),
            signature(business.get("candidateEventCandidates") or []),
            proven,
            contract_sha,
        ]
    )
    return evidence_digest


def cross_split(groups):
    return sum(len({split for split, _ in vals}) > 1 for vals in groups.values())


def near_cross_split(rows):
    pairs_at_threshold, nearest = 0, set()
    for (split_a, id_a, texts_a), (split_b, id_b, texts_b) in combinations(rows, 2):
        if split_a == split_b:
            continue
        for a, b in ((a, b) for a in texts_a for b in texts_b):
            # 长度不足二字时保留原字，空字符串已在调用方排除。
            denom = len(a | b)
            if denom and len(a & b) / denom >= 0.70:
                pairs_at_threshold += 1
                nearest.update((id_a, id_b))
                break
    return pairs_at_threshold, len(nearest)


def verify(
    package,
    source_index,
    dispositions,
    manifest_sha,
    target_splits=("report",),
    source_index_sha=None,
    dispositions_sha=None,
):
    source_raw, exposure_raw = source_index.read_bytes(), dispositions.read_bytes()
    if source_index_sha:
        require(sha(source_raw) == source_index_sha, "source_index_hash_mismatch")
    if dispositions_sha:
        require(sha(exposure_raw) == dispositions_sha, "dispositions_hash_mismatch")
    source_doc = parse(source_raw)
    require(
        source_doc["schema"] == "card-pairing-source-index-v1", "wrong_index_schema"
    )
    require(
        bool(target_splits) and set(target_splits) <= set(SPLITS),
        "invalid_evidence_splits",
    )
    evidence = source_doc["cases"]
    sources = Sources(source_index, source_doc)
    labels = indexed(exposure_raw)
    manifest_raw = (package / "manifest.json").read_bytes()
    require(sha(manifest_raw) == manifest_sha, "release_manifest_hash_mismatch")
    files = parse(manifest_raw)["outputs"]

    def published(name):
        raw = (package / name).read_bytes()
        require(sha(raw) == files.get(name), "published_document_hash_mismatch")
        return raw

    status = parse(published("dataset_status.json"))
    groups = {
        k: defaultdict(list)
        for k in ("request", "fixed_contract", "registered_family", "wording")
    }
    issues, totals, by_split, row_hashes = Counter(), Counter(), {}, []
    layout_hashes, seen, lexical_rows = {}, set(), []
    for split in SPLITS:
        layout_raw = published(split + "/layout_inputs.jsonl")
        req_raw = published(split + "/requests_for_review.jsonl")
        require(
            sha(layout_raw) == status["layout_input_sha256"][split],
            "declared_layout_sha_mismatch",
        )
        layout_hashes[split] = sha(layout_raw)
        layouts, reqs = indexed(layout_raw), indexed(req_raw)
        require(layouts.keys() == reqs.keys(), "request_contract_rosters_differ")
        require(
            len(layouts) == status["counts_by_collection"][split],
            "split_count_mismatch",
        )
        require(not (seen & layouts.keys()), "anonymous_id_in_multiple_splits")
        seen.update(layouts)
        counts = Counter(rows=len(layouts))
        for tid, fixed in layouts.items():
            req = reqs[tid]["original_request"]
            fixed_sha = signature({k: v for k, v in fixed.items() if k != "task_id"})
            groups["fixed_contract"][fixed_sha].append((split, tid))
            groups["request"][signature(req)].append((split, tid))
            terms = set(words(req)) - {""}
            for text in terms:
                groups["wording"][signature([fixed.get("size"), text])].append(
                    (split, tid)
                )
            lexical_rows.append(
                (
                    split,
                    tid,
                    [{t[i : i + 2] for i in range(max(1, len(t) - 1))} for t in terms],
                )
            )
            label = labels.get(tid)
            if (
                not isinstance(label, dict)
                or not label.get("family_id")
                or not isinstance(label.get("family_exposure"), list)
            ):
                issues["exposure_or_family_unknown"] += 1
            else:
                require(
                    label.get("source_split") == split
                    and label.get("decision") == "retained",
                    "disposition_mismatch",
                )
                groups["registered_family"][str(label["family_id"])].append(
                    (split, tid)
                )
                if split != "dev" and label["family_exposure"]:
                    issues["known_closed_family_exposure"] += 1
            if split not in target_splits:
                counts["pair_outside_requested_scope"] += 1
                row_hashes.append(
                    [
                        split,
                        tid,
                        signature(["outside_scope", signature(req), fixed_sha]),
                    ]
                )
                continue
            try:
                require(tid in evidence, "original_pair_evidence_missing")
                digest = audit_case(tid, req, fixed, evidence[tid], sources, counts)
                counts["pair_verified"] += 1
            except (
                OSError,
                KeyError,
                TypeError,
                IndexError,
                AttributeError,
                RecursionError,
                ValueError,
            ) as err:
                code = (
                    str(err)
                    if isinstance(err, CheckError)
                    else "private_evidence_unreadable_or_malformed"
                )
                issues[code] += 1
                digest = signature(["unverified", signature(req), fixed_sha, code])
            row_hashes.append([split, tid, digest])
        by_split[split] = dict(counts)
        totals.update(counts)
    risk = {k + "_cross_split_groups": cross_split(v) for k, v in groups.items()}
    risk["within_or_across_split_duplicate_contract_groups"] = sum(
        len(v) > 1 for v in groups["fixed_contract"].values()
    )
    (
        risk["lexical_similarity_pairs_ge_0_70"],
        risk["lexical_similarity_participant_rows"],
    ) = near_cross_split(lexical_rows)
    if any(risk.values()):
        issues["cross_split_or_duplicate_requires_review"] += 1
    return {
        "schema": "card-pairing-aggregate-v1",
        "status": "review_needed" if issues else "verified_declared_checks",
        "release_manifest_sha256": manifest_sha,
        "release_layout_sha256": layout_hashes,
        "source_index_sha256": sha(source_raw),
        "dispositions_sha256": sha(exposure_raw),
        "private_receipt_hashes_independently_supplied": {
            "source_index": bool(source_index_sha),
            "dispositions": bool(dispositions_sha),
        },
        "verifier_sha256": sha(Path(__file__).read_bytes()),
        "paired_rows_sha256": signature(sorted(row_hashes)),
        "counts": dict(totals),
        "by_split": by_split,
        "issue_counts": dict(issues),
        "risk_counts": risk,
        "pairing_target_splits": sorted(set(target_splits)),
        "historical_blindness_proven": False,
        "semantic_near_duplicate_clearance": None,
        "independent_human_acceptance": None,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package", type=Path, required=True)
    ap.add_argument("--source-index", type=Path, required=True)
    ap.add_argument("--dispositions", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    ap.add_argument("--manifest-sha256", required=True)
    ap.add_argument("--source-index-sha256")
    ap.add_argument("--dispositions-sha256")
    ap.add_argument("--evidence-splits", nargs="+", choices=SPLITS, default=["report"])
    args = ap.parse_args()
    try:
        result = verify(
            args.package,
            args.source_index,
            args.dispositions,
            args.manifest_sha256,
            args.evidence_splits,
            args.source_index_sha256,
            args.dispositions_sha256,
        )
    except (
        OSError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
        AttributeError,
        RecursionError,
    ) as err:
        code = (
            str(err)
            if isinstance(err, CheckError)
            else "private_input_unreadable_or_malformed"
        )
        result = {
            "schema": "card-pairing-aggregate-v1",
            "status": "unverified",
            "issue_counts": {code: 1},
        }
    try:
        with args.receipt.open("x", encoding="utf8") as output:
            json.dump(result, output, ensure_ascii=False, indent=2, allow_nan=False)
    except OSError:
        print("无法创建新的回执文件")
        return 2
    print(result["status"])
    return 0 if result["status"] == "verified_declared_checks" else 1


if __name__ == "__main__":
    raise SystemExit(main())
