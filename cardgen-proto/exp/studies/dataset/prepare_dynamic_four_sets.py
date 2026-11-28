"""动态/混合内容的四题集候选清单；严格匹配与关联隔离分开，不按能力参数删题。"""

from __future__ import annotations

from collections import Counter, defaultdict

from audit_common import digest

TARGETS = {"dev": 100, "report": 250, "extension": 60, "reserve": 84}
NAMES = {"dev": "开发", "report": "报告", "extension": "扩展", "reserve": "保留"}
SEEDS = (20261123, 20261124, 20261125, 20261126, 20261127)


def content_payload(row: dict) -> dict:
    """保留事实表达式/样值、文字、动作及其顺序；不传原组件、几何、颜色。"""
    return {
        "size": row["size"],
        "D": row["D"],
        "A": row["A"],
        "facts": [
            {"count": item["count"], "sources": item["sources"]}
            for item in row["items"]
        ],
        "supporting_text": [item["content"] for item in row["supporting_text"]],
        "actions": [
            {"handlers": item["handlers"], "caption": item["caption"]}
            for item in row["actions"]
        ],
    }


def prepare_tasks(records: list[dict], inputs: dict) -> list[dict]:
    buckets = defaultdict(list)
    for row in records:
        payload = content_payload(row)
        signature = digest(
            {"business_input": inputs[row["case_id"]]["input"], "content": payload}
        )
        buckets[signature].append(row)
    tasks = []
    for signature, members in sorted(buckets.items()):
        members = sorted(members, key=lambda item: item["case_id"])
        representative = members[0]
        identity = representative["case_id"]
        tasks.append(
            {
                "task_id": identity,
                "source_case_ids": [item["case_id"] for item in members],
                "size": representative["size"],
                "D": representative["D"],
                "A": representative["A"],
                "content_match_sha256": signature,
                "input_sha256": digest(inputs[identity]["input"]),
                "selected_content_sha256": digest(content_payload(representative)),
                "layout_input_candidate": content_payload(representative),
                "original_request_for_review": inputs[identity]["input"],
                "known_development_exposed": any(
                    inputs[item["case_id"]].get("pre_exposed") for item in members
                ),
                "matching_scope": "仅完整业务输入与已选内容的严格序列化匹配候选",
                "priority_entities_action_ownership_fully_confirmed": False,
                "ready_for_layout_experiment": False,
                "reference_artifacts": [
                    {"case_id": item["case_id"], "hashes": item["source_hashes"]}
                    for item in members
                ],
            }
        )
    return sorted(tasks, key=lambda item: item["task_id"])


def relation_families(tasks: list[dict]) -> list[dict]:
    """同输入或同已选内容仅关联同集，不删除需求/偏好不同的题。"""
    parents = {task["task_id"]: task["task_id"] for task in tasks}

    def find(identity):
        while parents[identity] != identity:
            parents[identity] = parents[parents[identity]]
            identity = parents[identity]
        return identity

    for key in ("input_sha256", "selected_content_sha256"):
        lookup = {}
        for task in tasks:
            previous = lookup.setdefault(task[key], task["task_id"])
            parents[find(task["task_id"])] = find(previous)
    buckets = defaultdict(list)
    for task in tasks:
        buckets[find(task["task_id"])].append(task)
    return [
        {
            "family_id": digest(sorted(task["task_id"] for task in members)),
            "task_ids": sorted(task["task_id"] for task in members),
            "known_development_exposed": any(
                task["known_development_exposed"] for task in members
            ),
        }
        for members in buckets.values()
    ]


def planned_counts(number: int, targets: dict) -> dict:
    if number > sum(targets.values()):
        raise ValueError("候选超过四题集总名额，须明确额外候选池，不能静默丢弃")
    result, remaining = {}, number
    for name, target in targets.items():
        result[name] = min(target, remaining)
        remaining -= result[name]
    return result


def cell(task: dict) -> tuple:
    return task["size"], task["D"], task["A"]


def balanced_size_counts(tasks: list[dict], quota: dict) -> dict:
    population = Counter(task["size"] for task in tasks)
    sizes = sorted(population)
    if not 1 <= len(sizes) <= 2:
        raise ValueError("尺寸数量未知，不能猜测分层名额")
    first = sizes[0]
    first_counts = {
        name: count * population[first] // len(tasks) for name, count in quota.items()
    }
    remainder = population[first] - sum(first_counts.values())
    ranked = sorted(
        quota,
        key=lambda name: (
            -(quota[name] * population[first] % len(tasks)),
            list(quota).index(name),
        ),
    )
    for name in ranked[:remainder]:
        first_counts[name] += 1
    return {
        name: {
            first: first_counts[name],
            **({sizes[1]: count - first_counts[name]} if len(sizes) == 2 else {}),
        }
        for name, count in quota.items()
    }


def allocate(
    tasks: list[dict], families: list[dict], seed: int, targets: dict | None = None
) -> dict:
    targets = TARGETS if targets is None else targets
    quota = planned_counts(len(tasks), targets)
    indexed = {task["task_id"]: task for task in tasks}
    weights = Counter(cell(task) for task in tasks)
    primary_weights = Counter((task["size"], task["D"]) for task in tasks)
    size_quota = balanced_size_counts(tasks, quota)
    left = list(families)
    selected, counters = (
        {name: [] for name in targets},
        {name: Counter() for name in targets},
    )
    primary_counts = {name: Counter() for name in targets}
    size_counts = {name: Counter() for name in targets}
    family_sizes = {
        family["family_id"]: Counter(
            indexed[identity]["size"] for identity in family["task_ids"]
        )
        for family in families
    }

    def accept(name, family):
        selected[name].extend(family["task_ids"])
        counters[name].update(
            cell(indexed[identity]) for identity in family["task_ids"]
        )
        primary_counts[name].update(
            (indexed[identity]["size"], indexed[identity]["D"])
            for identity in family["task_ids"]
        )
        size_counts[name].update(family_sizes[family["family_id"]])
        left.remove(family)

    for family in list(left):
        if family["known_development_exposed"]:
            accept("dev", family)
    if len(selected["dev"]) > quota["dev"]:
        raise ValueError("已知开发使用的相关题组超过开发名额，不能移入报告")
    if any(
        count > size_quota["dev"].get(size, 0)
        for size, count in size_counts["dev"].items()
    ):
        raise ValueError("已知开发样本超过尺寸分层名额，须显式调整不能挪入闭卷集")
    for name in targets:
        while len(selected[name]) < quota[name]:
            remaining = quota[name] - len(selected[name])
            available = [
                family
                for family in left
                if len(family["task_ids"]) <= remaining
                and all(
                    size_counts[name][size] + count <= size_quota[name].get(size, 0)
                    for size, count in family_sizes[family["family_id"]].items()
                )
            ]
            if not available:
                raise ValueError("关联题组整体无法精确填入名额；不能拆组或虚增样本")

            def score(family, target_name=name):
                additions = Counter(
                    cell(indexed[identity]) for identity in family["task_ids"]
                )
                primary_additions = {(key[0], key[1]) for key in additions}
                new_primary = sum(
                    1 / primary_weights[key]
                    for key in primary_additions
                    if primary_counts[target_name][key] == 0
                )
                new_coverage = sum(
                    1 / weights[key]
                    for key in additions
                    if counters[target_name][key] == 0
                )
                gain = sum(
                    abs(
                        counters[target_name][key]
                        - quota[target_name] * weights[key] / len(tasks)
                    )
                    - abs(
                        counters[target_name][key]
                        + count
                        - quota[target_name] * weights[key] / len(tasks)
                    )
                    for key, count in additions.items()
                ) / len(family["task_ids"])
                return (
                    new_primary if target_name == "dev" else 0,
                    new_coverage if target_name == "dev" else 0,
                    gain,
                    digest([seed, target_name, family["family_id"]]),
                )

            accept(name, max(available, key=score))
    if left:
        raise ValueError("存在未归入四题集的候选，停止而非丢弃")
    if any(dict(size_counts[name]) != size_quota[name] for name in quota):
        raise ValueError("尺寸分层数量未满足，不能冒充已平衡")
    return {name: sorted(identities) for name, identities in selected.items()}


def validate_assignment(
    tasks: list[dict], families: list[dict], allocation: dict, counts: dict
) -> dict:
    indexed = {task["task_id"]: task for task in tasks}
    owners, original_cases = {}, []
    size_quota = balanced_size_counts(tasks, counts)
    for name, identities in allocation.items():
        if len(identities) != counts[name]:
            raise ValueError("候选分集数量与计划不一致")
        if (
            Counter(indexed[identity]["size"] for identity in identities)
            != size_quota[name]
        ):
            raise ValueError("候选集合尺寸分布与预设名额不一致")
        for identity in identities:
            if identity not in indexed or identity in owners:
                raise ValueError("候选任务丢失、重复或跨集")
            owners[identity] = name
            original_cases.extend(indexed[identity]["source_case_ids"])
    if set(owners) != set(indexed) or len(original_cases) != len(set(original_cases)):
        raise ValueError("原始用例覆盖错误")
    for family in families:
        placements = {owners[identity] for identity in family["task_ids"]}
        if len(placements) != 1 or (
            family["known_development_exposed"] and placements != {"dev"}
        ):
            raise ValueError("关联题组跨集或开发曝光样例流入其它题集")
    for key in ("input_sha256", "selected_content_sha256"):
        seen = {}
        for identity, name in owners.items():
            if key_value := indexed[identity].get(key):
                previous = seen.setdefault(key_value, name)
                if previous != name:
                    raise ValueError("完全相同输入或内容跨集")
    return {
        "candidate_tasks_covered": len(owners),
        "original_cases_preserved": len(original_cases),
        "exact_input_or_content_cross_set_overlap": 0,
        "known_development_cases_kept_in_dev": True,
        "size_stratification_matches_prespecified_population_proportions": True,
        "semantic_near_duplicate_audit_completed": False,
        "independent_sample_count": None,
    }
