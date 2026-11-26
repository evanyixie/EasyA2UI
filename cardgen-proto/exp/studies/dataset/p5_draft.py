"""P5分题集草稿与独立复核：不读金标答案，不放宽目标，不代替人工或P8。"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from audit_common import private_destination

SEEDS = (17, 29, 43, 71, 101)
TARGETS = {"dev": 100, "report": 250, "extension": 60, "reserve": 84}
HEX = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class Group:
    identity: str
    representative: dict
    members: tuple[dict, ...]
    exposed: bool


def similarity(left: str, right: str) -> float:
    # 技术选择由P2单点定义；论文没有指定分词/相似函数，不在此复制另一套。
    from p2_duplicates import similarity as compare

    return compare(left, right)


def stratum(row: dict) -> tuple[str, str, str, str]:
    domain = row.get("domain")
    if isinstance(domain, list):
        domain = "|".join(sorted(set(domain)))
    return (
        row.get("layout") or "UNDETERMINED",
        row.get("size") or "UNKNOWN",
        row.get("source"),
        domain or "UNDETERMINED",
    )


def population(rows: list[dict]) -> tuple[list[Group], list[dict]]:
    ids, grouped = {}, defaultdict(list)
    errors = []
    for row in rows:
        if not isinstance(row, dict):
            errors.append({"code": "INVALID_RECORD_OBJECT"})
            continue
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            errors.append({"code": "INVALID_OR_DUPLICATE_ID", "case_id": case_id})
            continue
        ids[case_id] = row
        if row.get("source") != "online_updated":
            errors.append({"code": "UNEXPECTED_DATA_SOURCE", "case_id": case_id})
        for field in ("eligible", "is_representative", "pre_exposed"):
            if type(row.get(field)) is not bool:
                errors.append(
                    {"code": "INVALID_BOOLEAN", "case_id": case_id, "field": field}
                )
        if not isinstance(row.get("query"), str):
            errors.append({"code": "INVALID_QUERY", "case_id": case_id})
        for field in ("p1_status", "layout_status", "domain_status"):
            if not isinstance(row.get(field), str):
                errors.append(
                    {"code": "INVALID_STATUS", "case_id": case_id, "field": field}
                )
        if row.get("eligible") and row.get("size") not in {"2x2", "2x4"}:
            errors.append({"code": "ELIGIBLE_WITH_UNKNOWN_SIZE", "case_id": case_id})
        if row.get("layout") is not None and not isinstance(row.get("layout"), str):
            errors.append({"code": "INVALID_LAYOUT", "case_id": case_id})
        for field in ("input_sha256", "input_view_sha256"):
            if not isinstance(row.get(field), str) or not HEX.fullmatch(row.get(field)):
                errors.append(
                    {"code": "INVALID_HASH", "case_id": case_id, "field": field}
                )
        domain = row.get("domain")
        if domain is not None and not isinstance(domain, (str, list)):
            errors.append({"code": "INVALID_DOMAIN", "case_id": case_id})
        if isinstance(domain, list) and any(
            not isinstance(value, str) for value in domain
        ):
            errors.append({"code": "INVALID_DOMAIN", "case_id": case_id})
        group_id = row.get("group_id")
        if isinstance(group_id, str) and group_id:
            grouped[group_id].append(row)
        elif row.get("eligible"):
            errors.append({"code": "ELIGIBLE_WITHOUT_GROUP", "case_id": case_id})
    groups = []
    for group_id, members in sorted(grouped.items()):
        eligible = [row for row in members if row.get("eligible") is True]
        if not eligible:
            continue
        representatives = [
            row for row in members if row.get("is_representative") is True
        ]
        if len(representatives) != 1 or not representatives[0].get("eligible"):
            errors.append(
                {
                    "code": "GROUP_REPRESENTATIVE_NOT_UNIQUE_OR_ELIGIBLE",
                    "group": group_id,
                }
            )
            continue
        representative = representatives[0]
        if any(
            row.get("representative_id") != representative.get("case_id")
            for row in members
        ):
            errors.append({"code": "GROUP_REPRESENTATIVE_MISMATCH", "group": group_id})
            continue
        exposed = any(
            row.get("pre_exposed") or row.get("registered_exposure") is True
            for row in members
        )
        groups.append(Group(group_id, representative, tuple(members), exposed))
    return groups, errors


def group_similarity(first: Group, second: Group, compare) -> float:
    maximum = 0.0
    for left in first.members:
        for right in second.members:
            maximum = max(maximum, compare(left.get("query"), right.get("query")))
    return maximum


def leak_graph(groups: list[Group], compare) -> dict[str, set[str]]:
    graph = {group.identity: set() for group in groups}
    for index, first in enumerate(groups):
        for second in groups[index + 1 :]:
            if group_similarity(first, second, compare) >= 0.7:
                graph.get(first.identity).add(second.identity)
                graph.get(second.identity).add(first.identity)
    return graph


def distribution(groups: list[Group]) -> dict[str, int]:
    return dict(
        sorted(
            Counter(
                json.dumps(stratum(group.representative), ensure_ascii=False)
                for group in groups
            ).items()
        )
    )


def proportional_pick(
    pool: list[Group], count: int, whole: list[Group], ranks: dict
) -> list[Group]:
    """按去重后总体分布逐项弥补份额差；不看产物或成功率。"""
    weights = Counter(stratum(group.representative) for group in whole)
    chosen, counters = [], Counter()
    available = list(pool)
    for _ in range(min(count, len(available))):
        best = min(
            available,
            key=lambda group: (
                counters[stratum(group.representative)]
                - count * weights[stratum(group.representative)] / len(whole),
                ranks.get(group.identity),
                group.identity,
            ),
        )
        chosen.append(best)
        counters[stratum(best.representative)] += 1
        available.remove(best)
    return chosen


def audit_split(
    rows: list[dict], proposal: dict, targets: dict | None = None, *, compare=None
) -> dict:
    """不信任分配器的图/计数，重新从记录和清单检查约束。"""
    targets = TARGETS if targets is None else targets
    compare = similarity if compare is None else compare
    groups, errors = population(rows)
    if set(proposal) != set(targets):
        errors.append({"code": "INVALID_SPLIT_NAMES"})
    representatives = {group.representative.get("case_id"): group for group in groups}
    all_cases = {}
    for group in groups:
        for row in group.members:
            all_cases[row.get("case_id")] = group
    assignments, selected = {}, {}
    for split, expected in targets.items():
        case_ids = proposal.get(split, [])
        if not isinstance(case_ids, list):
            errors.append({"code": "INVALID_SPLIT_LIST", "split": split})
            continue
        if len(case_ids) != expected:
            errors.append(
                {
                    "code": "TARGET_COUNT_MISMATCH",
                    "split": split,
                    "expected": expected,
                    "actual": len(case_ids),
                }
            )
        selected[split] = []
        for case_id in case_ids:
            if not isinstance(case_id, str):
                errors.append({"code": "INVALID_SELECTED_ID", "split": split})
                continue
            group = all_cases.get(case_id)
            if group is None:
                errors.append(
                    {"code": "UNKNOWN_OR_INELIGIBLE_CASE", "case_id": case_id}
                )
                continue
            if case_id not in representatives:
                errors.append(
                    {"code": "NON_REPRESENTATIVE_SELECTED", "case_id": case_id}
                )
            if group.identity in assignments:
                errors.append(
                    {
                        "code": "GROUP_REPEATED_OR_CROSSES_SPLITS",
                        "group": group.identity,
                        "previous": assignments.get(group.identity),
                        "split": split,
                    }
                )
            assignments[group.identity] = split
            selected.get(split).append(group)
    for group in groups:
        if group.exposed and assignments.get(group.identity) != "dev":
            errors.append({"code": "EXPOSED_GROUP_NOT_DEV", "group": group.identity})
    nearest = []
    for report in selected.get("report", []):
        maximum, closest = 0.0, None
        for dev in selected.get("dev", []):
            score = group_similarity(report, dev, compare)
            if score > maximum:
                maximum, closest = score, dev.identity
        nearest.append(
            {
                "report_group": report.identity,
                "nearest_dev_group": closest,
                "similarity": maximum,
            }
        )
        if maximum >= 0.7:
            errors.append(
                {
                    "code": "REPORT_DEV_LEAK",
                    "group": report.identity,
                    "nearest_dev": closest,
                    "similarity": maximum,
                }
            )
    return {
        "status": "PASS" if not errors else "BLOCKED",
        "errors": errors,
        "nearest_report_to_dev": nearest,
        "distribution": None
        if errors
        else {name: distribution(value) for name, value in selected.items()},
        "assigned_groups": len(assignments),
        "unassigned_eligible_groups": sorted(
            {group.identity for group in groups} - assignments.keys()
        ),
    }


def allocate_seed(
    groups: list[Group],
    graph: dict,
    targets: dict,
    seed: int,
    rows: list[dict],
    compare,
) -> dict:
    rng = random.Random(seed)
    shuffled = list(groups)
    rng.shuffle(shuffled)
    ranks = {group.identity: index for index, group in enumerate(shuffled)}
    dev = [group for group in groups if group.exposed]
    chosen = {group.identity for group in dev}
    by_layout = defaultdict(list)
    for group in groups:
        if group.representative.get("layout"):
            pair = group.representative.get("layout"), group.representative.get("size")
            by_layout[pair].append(group)

    def cost(candidate):
        denied = set(chosen)
        for identity in chosen:
            denied.update(graph.get(identity, set()))
        extra = graph.get(candidate.identity, set()) | {candidate.identity}
        return len(extra - denied), ranks.get(candidate.identity), candidate.identity

    ordered_layouts = sorted(
        by_layout.items(), key=lambda item: (len(item[1]), str(item[0]))
    )
    for _pair, candidates in ordered_layouts:
        required = min(3, len(candidates))
        while sum(group.identity in chosen for group in candidates) < required:
            if len(dev) >= targets.get("dev"):
                break
            remaining = [group for group in candidates if group.identity not in chosen]
            best = min(remaining, key=cost)
            dev.append(best)
            chosen.add(best.identity)
    while len(dev) < targets.get("dev"):
        remaining = [group for group in groups if group.identity not in chosen]
        best = min(remaining, key=cost)
        dev.append(best)
        chosen.add(best.identity)
    report_pool = [
        group
        for group in groups
        if group.identity not in chosen
        and not graph.get(group.identity, set()) & chosen
    ]
    if len(report_pool) < targets.get("report"):
        return {
            "seed": seed,
            "status": "BLOCKED",
            "proposal": None,
            "blockers": [
                {
                    "code": "REPORT_POOL_AFTER_DEV_TOO_SMALL",
                    "required": targets.get("report"),
                    "actual": len(report_pool),
                    "deficit": targets.get("report") - len(report_pool),
                }
            ],
            "partial_dev_representatives": [
                group.representative.get("case_id") for group in dev
            ],
            "scope": "有界贪心草稿未找到方案，不是全域不可行证明",
        }
    selected = {"dev": dev}
    selected["report"] = proportional_pick(
        report_pool, targets.get("report"), groups, ranks
    )
    chosen.update(group.identity for group in selected.get("report"))
    for split in ("extension", "reserve"):
        remaining = [group for group in groups if group.identity not in chosen]
        selected[split] = proportional_pick(
            remaining, targets.get(split), groups, ranks
        )
        chosen.update(group.identity for group in selected.get(split))
    proposal = {}
    for name, values in selected.items():
        proposal[name] = [group.representative.get("case_id") for group in values]
    audit = audit_split(rows, proposal, targets, compare=compare)
    coverage = []
    dev_ids = {value.identity for value in dev}
    for pair, candidates in sorted(by_layout.items(), key=lambda item: str(item[0])):
        count = sum(group.identity in dev_ids for group in candidates)
        if count < 3:
            coverage.append(
                {
                    "layout_size": pair,
                    "dev_count": count,
                    "available_groups": len(candidates),
                    "target": 3,
                }
            )
    report_counts = Counter(
        group.representative.get("layout") for group in selected.get("report")
    )
    adequacy = []
    for layout, count in sorted(report_counts.items(), key=lambda item: str(item[0])):
        if count < 15 or layout is None:
            adequacy.append(
                {
                    "layout": layout,
                    "count": count,
                    "major_layout_target": 15,
                    "inference_allowed": count >= 8 and layout is not None,
                    "note": "主布局目标未满足；低于8或未判定只报数量，不推断",
                }
            )
    return {
        "seed": seed,
        "status": "DRAFT_PENDING_HUMAN" if audit.get("status") == "PASS" else "BLOCKED",
        "proposal": proposal,
        "independent_audit": audit,
        "dev_coverage_shortfalls": coverage,
        "report_sample_adequacy": adequacy,
        "blindness_verified": False,
        "p6_p7": "pending_real_human_review",
        "p8": "not_executed",
    }


def build_drafts(
    rows: list[dict], targets: dict | None = None, *, compare=None
) -> dict:
    targets = dict(TARGETS if targets is None else targets)
    invalid_value = any(
        type(value) is not int or value < 0 for value in targets.values()
    )
    if set(targets) != set(TARGETS) or invalid_value:
        raise ValueError("四题集目标必须是非负整数，不允许隐式缩放")
    compare = similarity if compare is None else compare
    groups, errors = population(rows)
    blockers = list(errors)
    total = sum(targets.values())
    forced = [group for group in groups if group.exposed]
    if len(groups) < total:
        blockers.append(
            {
                "code": "INSUFFICIENT_INDEPENDENT_GROUPS",
                "required": total,
                "actual": len(groups),
                "deficit": total - len(groups),
            }
        )
    if len(forced) > targets.get("dev"):
        blockers.append(
            {
                "code": "EXPOSED_GROUPS_EXCEED_DEV",
                "required_dev": len(forced),
                "available_dev": targets.get("dev"),
            }
        )
    graph = {} if blockers else leak_graph(groups, compare)
    trials = []
    for seed in SEEDS:
        if blockers:
            trials.append(
                {
                    "seed": seed,
                    "status": "BLOCKED",
                    "proposal": None,
                    "blockers": blockers,
                    "leak_audit": "not_executed_preflight_block",
                }
            )
        else:
            trials.append(allocate_seed(groups, graph, targets, seed, rows, compare))
    spreads = {}
    for split in targets:
        available = []
        keys = set()
        for trial in trials:
            counts = trial.get("independent_audit", {}).get("distribution")
            if counts is not None:
                current = counts.get(split, {})
                available.append(current)
                keys.update(current)
        split_spreads = {}
        for key in sorted(keys):
            values = [counts.get(key, 0) for counts in available]
            split_spreads[key] = {
                "min": min(values),
                "max": max(values),
                "counts_all_feasible_seeds": values,
            }
        spreads[split] = {
            "measured_seed_count": len(available),
            "strata": split_spreads,
            "pass_threshold": None,
            "decision": "pending_human_stability_review",
        }
    exposure_corrections = []
    for row in rows:
        if (
            isinstance(row, dict)
            and isinstance(row.get("case_id"), str)
            and row.get("registered_exposure") is True
            and row.get("pre_exposed") is False
        ):
            exposure_corrections.append(row["case_id"])
    eligible_count = sum(
        isinstance(row, dict) and row.get("eligible") is True for row in rows
    )
    return {
        "status": "BLOCKED"
        if any(trial.get("status") == "BLOCKED" for trial in trials)
        else "DRAFT_PENDING_HUMAN",
        "targets": targets,
        "seeds": list(SEEDS),
        "trials": trials,
        "input_rows": len(rows),
        "eligible_rows": eligible_count,
        "independent_eligible_groups": len(groups),
        "forced_dev_groups": len(forced),
        "population_distribution": None if errors else distribution(groups),
        "schema_errors": errors,
        "known_exposure_flags_overridden_conservatively": exposure_corrections,
        "five_seed_stratum_spread": spreads,
        "seed_selection": "none_all_five_reported_primary_package_seed_predeclared_17",
        "technical_choices": {
            "similarity": "P2 NFKC whitespace character_2gram_set_Jaccard",
            "group_query_comparison": "max_over_all_group_member_queries",
            "duplicate_threshold": "0.85_draft_only_all_three_reported_by_P2",
            "report_dev_max_similarity": "strictly_less_than_0.7",
            "proportions": "deduplicated_representative_population",
            "stability_pass_threshold": "unspecified_pending_human_confirmation",
        },
        "unknown_prior_exposure": "historical_exposure_beyond_known_six_not_verified",
        "formal_split_frozen": False,
        "p6_p7": "pending_real_human_review",
        "p8": "not_executed",
        "physical_model_calls": 0,
        "phone_operations": 0,
    }


def human_package(rows: list[dict], draft: dict) -> dict:
    if draft.get("schema_errors"):
        return {"status": "BLOCKED_INVALID_SCHEMA", "human_answers_generated": False}
    rng = random.Random(SEEDS[0])
    case_ids = sorted(row.get("case_id") for row in rows)
    inspection_ids = rng.sample(case_ids, min(25, len(case_ids)))
    groups, _errors = population(rows)
    eligible_ids = sorted(group.representative.get("case_id") for group in groups)
    layout_ids = rng.sample(eligible_ids, min(50, len(eligible_ids)))
    reviewers = {}
    for reviewer, offset in (("A", 1), ("B", 2)):
        ordered = list(layout_ids)
        random.Random(SEEDS[0] + offset).shuffle(ordered)
        reviewers[reviewer] = [
            {
                "case_id": case_id,
                "reviewer_name": None,
                "human_layout": None,
                "reason": None,
            }
            for case_id in ordered
        ]
    proposal = draft.get("trials", [{}])[0].get("proposal")
    report_ids = proposal.get("report", []) if proposal else []
    by_id = {row.get("case_id"): row for row in rows}
    must_show = []
    for case_id in report_ids:
        row = by_id.get(case_id)
        must_show.append(
            {
                "case_id": case_id,
                "query": row.get("query"),
                "input_view_sha256": row.get("input_view_sha256"),
                "required_items": None,
                "reviewer_name": None,
                "source_rule": "only_query_and_candidates_no_gold_or_machine_layout",
            }
        )
    return {
        "status": "PENDING_REAL_HUMAN_REVIEW",
        "inspections_25": inspection_ids,
        "layout_50_independent_reviewers": reviewers,
        "layout_target_count": 50,
        "layout_actual_count": len(layout_ids),
        "layout_agreement_kappa": None,
        "gold_review_error_rate": None,
        "gold_review_50": [
            {
                "case_id": case_id,
                "reviewer_name": None,
                "protocol_ok": None,
                "content_complete": None,
                "binding_correct": None,
                "reason": None,
            }
            for case_id in layout_ids
        ],
        "must_show_forms": must_show,
        "must_show_trial_target": 10,
        "must_show_dual_annotation_target": 20,
        "report_not_selected_reason": None
        if proposal
        else "seed17_preflight_or_leak_blocked",
        "candidate_payload": "pending_root_join_of_frozen_input_view_by_sha256",
        "limits": "只创建空白表与受控输入索引；不包含金标答案，"
        "不代人签名，不填人工判定或必显标签。",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--exposure-registry",
        type=Path,
        required=True,
        help="私有JSON数组，列入有历史暴露的完整案例编号",
    )
    args = parser.parse_args()
    output = private_destination(args.output)
    raw = args.records.read_bytes()
    rows = [
        json.loads(line)
        for line in raw.decode("utf-8-sig").splitlines()
        if line.strip()
    ]
    history_raw = args.exposure_registry.read_bytes()
    prior = json.loads(history_raw.decode("utf-8-sig"))
    if not isinstance(prior, list) or not all(isinstance(i, str) and i for i in prior):
        raise ValueError("历史暴露登记格式不符")
    known = set(prior)
    for row in rows:
        row["registered_exposure"] = row["case_id"] in known
    draft = build_drafts(rows)
    draft["exposure_registry_sha256"] = hashlib.sha256(history_raw).hexdigest()
    draft["records_sha256"] = hashlib.sha256(raw).hexdigest()
    output.mkdir(parents=True, exist_ok=False)
    (output / "draft.json").write_text(
        json.dumps(draft, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    package = human_package(rows, draft)
    reviewers = package.pop("layout_50_independent_reviewers", {})
    reviewer_paths = {}
    for reviewer, forms in reviewers.items():
        filename = "human-layout-reviewer-" + reviewer.lower() + "-blank.json"
        (output / filename).write_text(
            json.dumps(forms, ensure_ascii=False, indent=2) + "\n", "utf-8"
        )
        reviewer_paths[reviewer] = filename
    package["layout_50_independent_reviewers"] = reviewer_paths
    (output / "human-package-draft.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    if args.records.read_bytes() != raw:
        raise RuntimeError("运行期间records变化，不能交付混合版本草稿")
    print(
        json.dumps(
            {
                "status": draft.get("status"),
                "rows": len(rows),
                "groups": draft.get("independent_eligible_groups"),
                "formal_split_frozen": False,
            }
        )
    )


if __name__ == "__main__":
    main()
