"""独立保管端的完整核验 v2。沿用 v1 证据与风险口径，以固定来源及发布版本精确核对原请求。"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import custodian_verify as v1
import public_preflight as preflight
import source_lookup as lookup
from custodian_verify import (
    EMPTY_INDEX,
    MISSING,
    SPLITS,
    CheckError,
    Sources,
    canon,
    cross_split,
    indexed,
    near_cross_split,
    parse,
    paths_from,
    pointer,
    require,
    sha,
    signature,
    words,
)


class BoundSources:
    """v2 将保管方选择的 CardSpec 锚定到已冻结的身份表和原始文件。"""

    def __init__(self, inventory):
        self.inventory = inventory
        self.rules = lookup.ProjectionRules(inventory)
        self.rules.confirm_versions()
        self.identities = indexed(
            lookup.released_file(
                inventory.identities,
                inventory.identity_manifest_hash,
                "identity_and_provenance.jsonl",
            )
        )
        baseline = parse(lookup.verified_bytes(inventory.p0, inventory.p0_hash))
        require(
            baseline["data_commit"] == lookup.P0_REVISION, "baseline_revision_mismatch"
        )
        self.files = baseline["files"]

    def business_for(self, tid, request, supplied_card):
        identity = self.identities.get(tid)
        require(isinstance(identity, dict), "missing_identity")
        raw = lookup.original_bytes(self.inventory, self.files, identity)
        require(
            canon(preflight.card_object(raw)) == canon(supplied_card),
            "indexed_source_is_not_frozen_original",
        )
        return lookup.compare_projection(raw, request, identity["source"], self.rules)


def audit_case(tid, req, contract, evidence, sources, counts, bound):
    # 哈希既区分源文件精确字节、JSONL行/指针，也区分选中 CardSpec 的规范 JSON。
    card, _, card_location = sources.value(evidence["cardspec"], {"original_cardspec"})
    business = bound.business_for(tid, req, card)
    require(
        business.get("size") == contract.get("size") and bool(contract.get("size")),
        "caller_size_mismatch",
    )
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


def verify(
    package,
    source_index,
    dispositions,
    manifest_sha,
    target_splits=("report",),
    source_index_sha=None,
    dispositions_sha=None,
    inventory=None,
):
    require(inventory is not None, "inventory_required")
    require(
        inventory.package.resolve() == package.resolve()
        and inventory.release_hash == manifest_sha,
        "inventory_release_mismatch",
    )
    bound = BoundSources(inventory)
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
                require(
                    bound.identities.get(tid, {}).get("collection") == split,
                    "wrong_source_split",
                )
                require(tid in evidence, "original_pair_evidence_missing")
                digest = audit_case(
                    tid, req, fixed, evidence[tid], sources, counts, bound
                )
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
        "schema": "card-pairing-aggregate-v2",
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
        "lookup_code_sha256": sha(Path(lookup.__file__).read_bytes()),
        "view_code_sha256": sha(Path(preflight.__file__).read_bytes()),
        "source_verifier_v1_sha256": sha(Path(v1.__file__).read_bytes()),
        "projection_source_sha256": preflight.PROJECTION_SOURCES,
        "identity_manifest_sha256": bound.inventory.identity_manifest_hash,
        "baseline_manifest_sha256": bound.inventory.p0_hash,
        "pr798_whitelist_manifest_sha256": bound.inventory.old_identity_manifest_hash
        if "whitelist" in vars(bound.rules)
        else None,
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
    ap.add_argument("--inventory", type=Path, required=True)
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
            inventory=lookup.load_inventory(args.inventory),
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
            "schema": "card-pairing-aggregate-v2",
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
