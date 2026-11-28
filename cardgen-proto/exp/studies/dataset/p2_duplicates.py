"""输入独立的 P2 重复题组审计；保留全部记录，不决定最终阈值或 P5 切分。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations, pairwise
from pathlib import Path
from typing import Any

from audit_common import private_destination

VERSION = "p2-duplicates-v1"
SIMILARITY_VERSION = "nfkc-whitespace-char2gram-jaccard-v1"
THRESHOLDS = (0.75, 0.85, 0.95)
LEAKAGE_THRESHOLD = 0.7
LARGE_GROUP_SIZE = 10
INPUT_KEYS = {
    "case_id",
    "source",
    "query",
    "size",
    "input_sha256",
    "input_view_sha256",
    "input",
    "pre_exposed",
}
UNRESOLVED_CAPABILITY_FIELDS = {
    "dataCapabilityIds",
    "dataCapabilitySchemas",
    "dataCapabilities",
    "dataCapabilityParams",
    "arguments",
}


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_query(text: str) -> str:
    """仅 NFKC 与空白折叠；保留大小写、数字、标点、否定及所有业务文字。"""
    return " ".join(unicodedata.normalize("NFKC", text).split())


def char_bigrams(text: str) -> set[str]:
    return {text[index : index + 2] for index in range(len(text) - 1)}


def similarity(left: str, right: str) -> float:
    first = char_bigrams(normalize_query(left))
    second = char_bigrams(normalize_query(right))
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def capability_signature(
    input_view: dict[str, Any],
) -> tuple[str | None, list, list[str]]:
    """完整非空能力多重集合；只读能力 ID 和 arguments，不读样值或输出绑定位置。"""
    bindings = input_view.get("candidateDataBindings", [])
    if not isinstance(bindings, list):
        return None, [], ["candidateDataBindings_not_list"]
    if not bindings:
        return None, [], []
    entries = []
    for binding in bindings:
        if not isinstance(binding, dict):
            return None, [], ["candidateDataBindings_contains_non_object"]
        identity = binding.get("capabilityId")
        if not isinstance(identity, str) or not identity.strip():
            return None, [], ["data_binding_missing_capability_id"]
        arguments_present = "arguments" in binding
        entries.append(
            {
                "capability_id": identity,
                "arguments_present": arguments_present,
                "arguments": binding.get("arguments"),
            }
        )
    entries.sort(key=canonical_json)
    return digest(entries), entries, []


def unresolved_capability_fields(input_view: dict[str, Any]) -> list[str]:
    """仅报告其他声明格式，既不解释别名也不补造能力或参数。"""
    return sorted(UNRESOLVED_CAPABILITY_FIELDS & input_view.keys())


@dataclass(frozen=True)
class InputRecord:
    row: dict[str, Any]
    case_id: str
    query: str
    normalized_query: str
    canonical_input_sha256: str
    capability_sha256: str | None
    capabilities: list
    unresolved_capability_fields: tuple[str, ...]
    issues: tuple[str, ...]

    @property
    def representative_key(self):
        source_hash = self.row.get("input_sha256")
        if not isinstance(source_hash, str) or not source_hash:
            source_hash = self.canonical_input_sha256
        return source_hash, self.case_id


def prepare_records(rows: list[dict[str, Any]]) -> list[InputRecord]:
    records, identities = [], set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise TypeError(f"记录{index + 1}不是对象；停止审计，不跳过记录")
        unexpected = set(row) - INPUT_KEYS
        if unexpected:
            raise ValueError(f"输入专用schema含额外字段：{sorted(unexpected)}")
        identity = row.get("case_id")
        if not isinstance(identity, str) or not identity:
            raise ValueError(f"记录{index + 1}缺少稳定case_id")
        if identity in identities:
            raise ValueError(f"case_id重复：{identity}；停止审计，不删除重复记录")
        identities.add(identity)
        input_view = row.get("input")
        if not isinstance(input_view, dict):
            raise TypeError(f"{identity}缺少输入对象")
        query = row.get("query")
        issues = []
        if not isinstance(query, str):
            issues.append("query_not_string")
            query = ""
        normalized = normalize_query(query)
        if len(normalized) < 2:
            issues.append("query_too_short_for_bigrams")
        signature, capabilities, capability_issues = capability_signature(input_view)
        issues.extend(capability_issues)
        unresolved = unresolved_capability_fields(input_view)
        if unresolved:
            issues.append("capability_schema_unresolved")
        records.append(
            InputRecord(
                row=row,
                case_id=identity,
                query=query,
                normalized_query=normalized,
                canonical_input_sha256=digest(input_view),
                capability_sha256=signature,
                capabilities=capabilities,
                unresolved_capability_fields=tuple(unresolved),
                issues=tuple(issues),
            )
        )
    return sorted(records, key=lambda record: record.case_id)


class DisjointSet:
    def __init__(self, identities):
        self.parents = {identity: identity for identity in identities}

    def find(self, identity):
        root = identity
        while self.parents[root] != root:
            root = self.parents[root]
        while self.parents[identity] != identity:
            parent = self.parents[identity]
            self.parents[identity] = root
            identity = parent
        return root

    def union(self, first, second):
        first_root, second_root = self.find(first), self.find(second)
        if first_root != second_root:
            low, high = sorted((first_root, second_root))
            self.parents[high] = low


def _base_edges(records):
    exact, capability = defaultdict(list), defaultdict(list)
    reasons = defaultdict(set)
    for record in records:
        exact[record.canonical_input_sha256].append(record.case_id)
        if record.capability_sha256 is not None:
            capability[record.capability_sha256].append(record.case_id)
    for buckets, reason in (
        (exact, "exact_input"),
        (capability, "same_capabilities_arguments"),
    ):
        for identities in buckets.values():
            for first, second in combinations(identities, 2):
                reasons[first, second].add(reason)
    return reasons


def _partition(records, scores, base_reasons, threshold, *, near_only=False):
    components = DisjointSet(record.case_id for record in records)
    for pair, score in scores.items():
        if score >= threshold or (not near_only and base_reasons.get(pair)):
            components.union(*pair)
    members = defaultdict(list)
    for record in records:
        members[components.find(record.case_id)].append(record.case_id)
    return sorted(
        (tuple(group) for group in members.values()), key=lambda group: group[0]
    )


def _group_rows(records, groups, scores, base_reasons, threshold):
    indexed = {record.case_id: record for record in records}
    results = []
    for members in groups:
        evidence = Counter()
        values, transitive = [], []
        for pair in combinations(members, 2):
            score = scores[pair]
            values.append(score)
            reasons = base_reasons.get(pair, set())
            evidence.update(reasons)
            if score >= threshold:
                evidence["near_query"] += 1
            elif not reasons:
                transitive.append(
                    {"first": pair[0], "second": pair[1], "similarity": score}
                )
        representative = min(
            members, key=lambda identity: indexed[identity].representative_key
        )
        minimum = min(values) if values else None
        results.append(
            {
                "group_id": "dup_" + digest(list(members))[:16],
                "threshold": threshold,
                "representative_case_id": representative,
                "members": list(members),
                "size": len(members),
                "evidence_pair_counts": dict(sorted(evidence.items())),
                "minimum_query_similarity": minimum,
                "maximum_query_similarity": max(values) if values else None,
                "transitive_only_pair_count": len(transitive),
                "transitive_examples": sorted(
                    transitive,
                    key=lambda entry: (
                        entry["similarity"],
                        entry["first"],
                        entry["second"],
                    ),
                )[:10],
                "large_group": len(members) >= LARGE_GROUP_SIZE,
                "heterogeneous_query_group": minimum is not None
                and minimum < threshold,
            }
        )
    return results


def _stats(groups):
    return {
        "group_count": len(groups),
        "singleton_count": sum(g["size"] == 1 for g in groups),
        "duplicate_group_count": sum(g["size"] > 1 for g in groups),
        "record_count": sum(g["size"] for g in groups),
        "variant_count": sum(g["size"] - 1 for g in groups),
        "largest_group_size": max((g["size"] for g in groups), default=0),
        "large_group_count": sum(g["large_group"] for g in groups),
        "transitive_group_count": sum(
            g["transitive_only_pair_count"] > 0 for g in groups
        ),
        "heterogeneous_query_group_count": sum(
            g["heterogeneous_query_group"] for g in groups
        ),
    }


def _stability(first, second):
    first_members, second_members = {}, {}
    first_pairs, second_pairs = set(), set()
    for groups, membership, pairs in (
        (first, first_members, first_pairs),
        (second, second_members, second_pairs),
    ):
        for group in groups:
            members = tuple(group["members"])
            for identity in members:
                membership[identity] = members
            pairs.update(combinations(members, 2))
    union = first_pairs | second_pairs
    return {
        "from_threshold": first[0]["threshold"] if first else None,
        "to_threshold": second[0]["threshold"] if second else None,
        "group_count_delta": len(second) - len(first),
        "changed_membership_records": sum(
            first_members[key] != second_members[key] for key in first_members
        ),
        "coassignment_jaccard": len(first_pairs & second_pairs) / len(union)
        if union
        else 1.0,
        "limitation": "描述阈值敏感性，不定义稳定容差或自动确认阈值",
    }


def audit_duplicates(rows):
    records = prepare_records(rows)
    base_reasons = _base_edges(records)
    scores = {}
    for first, second in combinations(records, 2):
        scores[first.case_id, second.case_id] = similarity(first.query, second.query)
    groups_by_threshold, near_only_stats = {}, {}
    for threshold in THRESHOLDS:
        key = f"{threshold:.2f}"
        partition = _partition(records, scores, base_reasons, threshold)
        groups_by_threshold[key] = _group_rows(
            records, partition, scores, base_reasons, threshold
        )
        near = _partition(records, scores, base_reasons, threshold, near_only=True)
        near_rows = _group_rows(records, near, scores, {}, threshold)
        near_only_stats[key] = _stats(near_rows)
    pairs = []
    for pair, score in scores.items():
        reasons = sorted(base_reasons.get(pair, set()))
        if reasons or score >= LEAKAGE_THRESHOLD:
            pairs.append(
                {
                    "first": pair[0],
                    "second": pair[1],
                    "similarity": score,
                    "base_reasons": reasons,
                    "near_thresholds": [t for t in THRESHOLDS if score >= t],
                }
            )
    statistics = {}
    for key, groups in groups_by_threshold.items():
        statistics[key] = {
            "combined": _stats(groups),
            "near_only": near_only_stats[key],
        }
    stability = []
    for lower, upper in pairwise(THRESHOLDS):
        stability.append(
            _stability(
                groups_by_threshold[f"{lower:.2f}"], groups_by_threshold[f"{upper:.2f}"]
            )
        )
    return {
        "records": records,
        "groups": groups_by_threshold,
        "pairs": pairs,
        "statistics": statistics,
        "stability": stability,
    }


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"输入含重复JSON键：{key}")
        result[key] = value
    return result


def load_jsonl(path):
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"输入第{number}行为空，不静默跳过")
        rows.append(json.loads(line, object_pairs_hook=_unique_object))
    return rows


def _write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(canonical_json(row) + "\n")


def write_audit(result, output, *, input_path, input_file_sha256):
    output = private_destination(output)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if previous.get("input_file_sha256") != input_file_sha256:
            raise ValueError("输出目录已有不同冻结输入，禁止覆盖；请指定新目录")
    output.mkdir(parents=True, exist_ok=True)
    review = output / "manual_review"
    review.mkdir(exist_ok=True)
    records = result["records"]
    memberships = {record.case_id: {} for record in records}
    decisions = []
    for key, groups in result["groups"].items():
        _write_jsonl(output / f"groups_{key}.jsonl", groups)
        for group in groups:
            for identity in group["members"]:
                memberships[identity][key] = {
                    "group_id": group["group_id"],
                    "representative": identity == group["representative_case_id"],
                }
            if group["size"] > 1:
                decisions.append(
                    {
                        "threshold": key,
                        "group_id": group["group_id"],
                        "representative_case_id": group["representative_case_id"],
                        "members": ";".join(group["members"]),
                        "reviewer_1": "",
                        "reviewer_2": "",
                        "decision": "",
                        "split_groups": "",
                        "reason": "",
                    }
                )
    membership_rows, input_rows = [], []
    issue_counts = Counter()
    for record in records:
        issue_counts.update(record.issues)
        membership_rows.append(
            {
                "case_id": record.case_id,
                "source": record.row.get("source"),
                "pre_exposed": record.row.get("pre_exposed"),
                "input_sha256": record.row.get("input_sha256"),
                "input_view_sha256": record.row.get("input_view_sha256"),
                "canonical_input_sha256": record.canonical_input_sha256,
                "capability_signature_sha256": record.capability_sha256,
                "normalized_query_sha256": digest(record.normalized_query),
                "normalized_query_length": len(record.normalized_query),
                "issues": list(record.issues),
                "unresolved_capability_fields": list(
                    record.unresolved_capability_fields
                ),
                "threshold_memberships": memberships[record.case_id],
            }
        )
        input_rows.append(
            {
                "case_id": record.case_id,
                "source": record.row.get("source"),
                "pre_exposed": record.row.get("pre_exposed"),
                "query": record.row.get("query"),
                "size": record.row.get("size"),
                "input": record.row["input"],
                "unresolved_capability_fields": list(
                    record.unresolved_capability_fields
                ),
                "capabilities_arguments": record.capabilities,
            }
        )
    _write_jsonl(output / "memberships.jsonl", membership_rows)
    _write_jsonl(output / "pair_evidence.jsonl", result["pairs"])
    capability_edges = [
        row
        for row in result["pairs"]
        if "same_capabilities_arguments" in row["base_reasons"]
    ]
    _write_jsonl(output / "capability_argument_edges.jsonl", capability_edges)
    unresolved_rows = []
    for record in records:
        if record.unresolved_capability_fields:
            unresolved_rows.append(
                {
                    "case_id": record.case_id,
                    "diagnostic": "capability_schema_unresolved",
                    "fields": list(record.unresolved_capability_fields),
                    "canonical_signature_available": record.capability_sha256
                    is not None,
                    "review_status": "pending_P6_schema_review",
                }
            )
    _write_jsonl(output / "capability_schema_unresolved.jsonl", unresolved_rows)
    _write_jsonl(review / "input_only_records.jsonl", input_rows)
    with (review / "decisions_template.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        names = [
            "threshold",
            "group_id",
            "representative_case_id",
            "members",
            "reviewer_1",
            "reviewer_2",
            "decision",
            "split_groups",
            "reason",
        ]
        writer = csv.DictWriter(stream, fieldnames=names)
        writer.writeheader()
        writer.writerows(decisions)
    manifest = {
        "version": VERSION,
        "input_file": input_path.name,
        "input_file_sha256": input_file_sha256,
        "record_count": len(records),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "case_ids_sha256": digest([record.case_id for record in records]),
        "thresholds": list(THRESHOLDS),
        "statistics": result["statistics"],
        "stability": result["stability"],
        "draft_config": {
            "threshold": 0.85,
            "status": "pending_manual_review",
            "automatically_selected": False,
        },
        "method": {
            "similarity": SIMILARITY_VERSION,
            "normalization": "Unicode NFKC + whitespace collapse; no casefold or word deletion",
            "short_query_policy": "fewer than two normalized characters => similarity zero",
            "exact": "canonical JSON of entire input view; array order retained",
            "capability": (
                "complete nonempty canonical candidateDataBindings multiset and arguments"
            ),
            "other_capability_declarations": "diagnostic only; no alias or argument inference",
            "missing_arguments": "distinct from explicit null and empty object",
            "graph": "union of exact, threshold near-query, and full-capability-arguments edges",
            "representative": (
                "lexicographic input_sha256 (canonical input hash fallback), then case_id"
            ),
            "large_group_diagnostic_size": LARGE_GROUP_SIZE,
            "leakage_threshold": LEAKAGE_THRESHOLD,
            "basis": "本轮技术方案；Easy论文只规定阈值，未指定相似度算法与稳定容差",
        },
        "issue_counts": dict(issue_counts),
        "deleted_records": 0,
        "p5_decision_made": False,
        "answers_read": False,
        "human_review_status": "not_performed",
        "capability_coverage": {
            "canonical_nonempty_records": sum(
                record.capability_sha256 is not None for record in records
            ),
            "canonical_empty_or_unavailable_records": sum(
                record.capability_sha256 is None for record in records
            ),
            "unresolved_declaration_records": len(unresolved_rows),
            "limitation": "canonical为空不代表真实无数据；其他声明格式尚未解析，需P6复核",
        },
        "limitations": [
            "重复候选不是人工确认的同义问题",
            "连通分量可能包含链式合并或能力同参大组",
            "0.85只是草稿，需确认阈值及疑似重复题组",
            "本步骤不选择P5题集，不调用模型或渲染",
        ],
    }
    _write_json(manifest_path, manifest)
    _write_json(output / "threshold_stability.json", result["stability"])
    lines = [
        "# P2 重复题组候选审计",
        "",
        f"全部输入：{len(records)}；删除：0。",
        "",
        "| 阈值 | 合并后题组 | 单例 | 最大组 | 仅近似题组 | 链式组 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for key, statistics in result["statistics"].items():
        combined, near = statistics["combined"], statistics["near_only"]
        lines.append(
            f"| {key} | {combined['group_count']} | {combined['singleton_count']} | "
            f"{combined['largest_group_size']} | {near['group_count']} | "
            f"{combined['transitive_group_count']} |"
        )
    lines.extend(
        [
            "",
            "三档全部保留；0.85仅为待人工确认的草稿，不自动定阈值或P5。",
            "相似方法为本轮固定技术方案，不声称论文已指定算法或稳定性容差。",
            "能力边仅比较完整非空能力多重集合及参数，不比较输出位置或样值。",
            "此处能力仅指canonical candidateDataBindings；为空不证明请求真实无数据。",
            "其他数据声明只写capability_schema_unresolved诊断，交P6，不补造别名或参数。",
            "人工请复核：是否同题变体、同参但不同需求、大组边界及链式连接；可拆组或记不确定。",
            "manual_review仅含输入和空白裁决表，无金标、产物、质量或成功状态。",
            "所有原始记录仍在memberships中，代表不是删除变体，也不是按答案好坏选取。",
        ]
    )
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    raw = arguments.input.read_bytes()
    result = audit_duplicates(load_jsonl(arguments.input))
    manifest = write_audit(
        result,
        arguments.output,
        input_path=arguments.input,
        input_file_sha256=hashlib.sha256(raw).hexdigest(),
    )
    print(
        json.dumps(
            {
                "record_count": manifest["record_count"],
                "deleted_records": 0,
                "output": str(arguments.output.resolve()),
                "draft_status": manifest["draft_config"]["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
