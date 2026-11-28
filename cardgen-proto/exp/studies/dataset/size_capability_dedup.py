"""按用户确认的尺寸＋完整能力参数精确去重；保留全部原始用例。"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from pathlib import Path

from p2_duplicates import canonical_json, capability_signature


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deduplicate(rows: list[dict]) -> dict:
    buckets, pending = defaultdict(list), []
    seen = set()
    for row in rows:
        identity, size, view = row["case_id"], row["size"], row["input"]
        if identity in seen:
            raise ValueError("输入案例ID重复")
        seen.add(identity)
        if size not in {"2x2", "2x4"}:
            raise ValueError("尺寸未知，不得推断")
        signature, entries, errors = capability_signature(view)
        reasons = list(errors)
        if signature is None:
            reasons.append("canonical_data_not_available")
        if row.get("unresolved_capability_fields"):
            reasons.append("other_data_schema_unresolved")
        if any(not entry["arguments_present"] for entry in entries):
            reasons.append("arguments_missing")
        item = {
            "case_id": identity,
            "size": size,
            "query": row["query"],
            "input_sha256": hashlib.sha256(canonical_json(view).encode()).hexdigest(),
        }
        if reasons:
            pending.append({**item, "reasons": reasons})
            continue
        buckets[(size, signature)].append((item, entries))
    groups = []
    for (size, signature), values in sorted(buckets.items()):
        items = sorted(
            (value[0] for value in values),
            key=lambda item: (item["input_sha256"], item["case_id"]),
        )
        groups.append(
            {
                "group_id": size + "_" + signature,
                "size": size,
                "capability_arguments": values[0][1],
                "representative_case_id": items[0]["case_id"],
                "members": items,
            }
        )
    coverage = [item["case_id"] for group in groups for item in group["members"]]
    coverage.extend(item["case_id"] for item in pending)
    if len(coverage) != len(seen) or set(coverage) != seen:
        raise ValueError("去重后的代表、变体、待核记录未完整覆盖原输入")
    counts = {}
    for size in ("2x2", "2x4"):
        selected = [group for group in groups if group["size"] == size]
        count = sum(len(group["members"]) for group in selected)
        unresolved = [item for item in pending if item["size"] == size]
        counts[size] = {
            "original_inputs": sum(row["size"] == size for row in rows),
            "parsed_inputs": count,
            "exact_groups": len(selected),
            "variants_retained": count - len(selected),
            "pending_kept_individually": len(unresolved),
        }
    return {
        "counts_by_size": counts,
        "groups": groups,
        "pending": pending,
        "pending_reason_counts": dict(
            Counter(reason for item in pending for reason in item["reasons"])
        ),
    }
