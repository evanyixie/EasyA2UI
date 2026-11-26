"""按输入候选领域补 P1 描述性交叉表，不读取金标内容，不新增剔除。"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

COHORTS = ("eligible", "missing_artifact", "other_not_eligible")


def missing_artifact(record):
    for criterion in record.get("criteria", []):
        if (
            criterion.get("code") != "P1_C1_MESSAGES"
            or criterion.get("status") != "fail"
        ):
            continue
        if criterion.get("evidence", {}).get("reason") == "MISSING_ARTIFACT":
            return True
    return False


def cohort(record):
    eligible = record.get("eligible")
    if not isinstance(eligible, bool):
        raise ValueError("P1 eligibility must be explicitly boolean")  # noqa: TRY004 -- 保留既有数据准入校验的异常合同
    if eligible:
        return "eligible"
    if missing_artifact(record):
        return "missing_artifact"
    return "other_not_eligible"


def index_rows(rows, name):
    indexed = {}
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError(f"{name} row must be an object")
        identity = row.get("case_id")
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError(f"{name} case ID missing")
        if identity in indexed:
            raise ValueError(f"{name} case ID repeated")
        indexed[identity] = row
    return indexed


def membership(cases, case_cohorts, denominators):
    result = {}
    for name in COHORTS:
        identities = sorted(
            identity for identity in cases if case_cohorts[identity] == name
        )
        denominator = denominators[name]
        result[name] = {
            "count": len(identities),
            "denominator": denominator,
            "case_ids": identities,
            "percentage": None
            if denominator == 0
            else 100 * len(identities) / denominator,
        }
    return result


def summarize_domain_bias(p1_rows, p4_rows, unresolved_rows):
    p1 = index_rows(p1_rows, "P1")
    p4 = index_rows(p4_rows, "P4")
    if set(p1) != set(p4):
        raise ValueError("P1 and P4 must cover exactly the same cases")
    case_cohorts = {identity: cohort(record) for identity, record in p1.items()}
    denominators = Counter(case_cohorts.values())
    for name in COHORTS:
        denominators.setdefault(name, 0)
    domains = {}
    unknown = set()
    known = set()
    status_counts = Counter()
    for identity, record in p4.items():
        status = record.get("domain_status")
        if not isinstance(status, str) or not status:
            raise ValueError("P4 domain status missing")
        status_counts[status] += 1
        labels = record.get("domain")
        if status != "classified":
            if labels:
                raise ValueError("unknown domain status must not carry asserted labels")
            unknown.add(identity)
            continue
        if not isinstance(labels, list) or not labels:
            raise ValueError("classified domain must contain a nonempty label list")
        seen = set()
        for label in labels:
            if not isinstance(label, str) or not label.strip():
                raise ValueError("domain label must be a nonempty string")
            if label in seen:
                raise ValueError("domain labels repeated within a case")
            seen.add(label)
            domains.setdefault(label, set()).add(identity)
        known.add(identity)
    unresolved = set()
    for record in unresolved_rows:
        if not isinstance(record, dict):
            raise TypeError("unresolved declaration record must be an object")
        identity = record.get("case_id")
        if not isinstance(identity, str) or identity not in p1:
            raise ValueError("unresolved declaration references unknown case")
        unresolved.add(identity)
    domain_rows = []
    for label, cases in sorted(domains.items()):
        domain_rows.append(
            {
                "domain": label,
                "known_member_count": len(cases),
                "by_cohort": membership(cases, case_cohorts, denominators),
            }
        )
    return {
        "scope": "P1 descriptive domain bias from P4 input candidateDataBindings only; "
        "no golden content, layout, screenshot or model output used.",
        "total_requests": len(p1),
        "cohort_denominators": dict(denominators),
        "p4_domain_status": dict(status_counts),
        "known_canonical_domain_cases": membership(known, case_cohorts, denominators),
        "unknown_canonical_domain_cases": membership(
            unknown, case_cohorts, denominators
        ),
        "unparsed_declaration_cases": membership(
            unresolved, case_cohorts, denominators
        ),
        "unparsed_overlap_known_canonical": len(unresolved & known),
        "unparsed_overlap_unknown_canonical": len(unresolved & unknown),
        "by_domain": domain_rows,
        "multi_label_rule": "Each case counts once per observed domain. Domain rows overlap; "
        "their counts or percentages must not be summed as a partition.",
        "denominator_rule": "Each percentage uses every request in that P1 cohort, "
        "including unknown domains, not the number of labels.",
        "unknown_rule": "No canonical label is unknown, not proof of no business data. "
        "Unparsed declarations may add domains; observed membership "
        "is not exhaustive. A zero observed count does not rule out "
        "membership in the unknown pool.",
        "statistical_inference": "not_performed_descriptive_only",
        "causal_inference": "not_performed",
        "new_exclusions": 0,
        "human_validation": "not_performed",
    }


def render_markdown(result):
    denominators = result["cohort_denominators"]
    eligible = denominators["eligible"]
    missing = denominators["missing_artifact"]
    lines = [
        "# P1 领域偏倚交叉表（描述性）",
        "",
        "领域仅取P4对输入候选的能力标识，不读取金标、截图或布局来反推业务。",
        "",
        (
            f"全部{result['total_requests']}条：结构准入{eligible}条，缺产物{missing}条，"
            f"其他未准入{denominators['other_not_eligible']}条。没有新增剔除。"
        ),
        "",
        f"| 输入候选可识别的领域 | 准入：计数/{eligible} | 缺产物：计数/{missing} |",
        "| --- | ---: | ---: |",
    ]
    for row in result["by_domain"]:
        counts = row["by_cohort"]
        cells = []
        for name in ("eligible", "missing_artifact"):
            item = counts[name]
            percentage = item["percentage"]
            suffix = (
                "比例未知（分母为0）" if percentage is None else f"{percentage:.1f}%"
            )
            cells.append(f"{item['count']}/{item['denominator']}（{suffix}）")
        lines.append(f"| {row['domain']} | {cells[0]} | {cells[1]} |")
    lines.extend(["", "## 未知与重叠边界", ""])
    for key, title in (
        ("known_canonical_domain_cases", "至少一个标准候选领域可识别"),
        (
            "unknown_canonical_domain_cases",
            "标准候选未提供可识别领域，不能当成无业务数据",
        ),
        ("unparsed_declaration_cases", "另有未解析声明或arguments，领域可能不完整"),
    ):
        counts = result[key]
        eligible_count = counts["eligible"]["count"]
        missing_count = counts["missing_artifact"]["count"]
        lines.append(f"- {title}：准入{eligible_count}条，缺产物{missing_count}条。")
    lines.extend(
        [
            (
                f"- 未解析声明与已识别标准候选重叠{result['unparsed_overlap_known_canonical']}条，"
                f"与标准领域未知池重叠{result['unparsed_overlap_unknown_canonical']}条。"
            ),
            "- 多领域卡对每个已知领域各计一次；各行有重叠，不能相加当作互斥总体或100%。",
            "- 分母固定为对应P1组的全部请求，未知领域仍在分母中，不改用标签数量。",
            "- 表格中的0仅表示未观察到该标准候选标签，不证明未知池中没有该领域。",
            "- 未知不能填成0、无数据或已确认其他领域；未解析声明也不自动推断参数。",
            "- 缺产物仅8条，全部结果只作描述；不检验显著性，不推因果或模型失败率。",
            "- 未新增人工裁决、模型调用或真机验证。",
            "",
            "完整逐领域案例ID、未知池和来源哈希见同目录 `domain-bias.json`。",
            "",
        ]
    )
    return "\n".join(lines)


def read_rows(path):
    return [
        json.loads(line)
        for line in path.read_text("utf-8-sig").splitlines()
        if line.strip()
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("p1", "p4", "unparsed", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    paths = {name: getattr(args, name) for name in ("p1", "p4", "unparsed")}
    hashes = {
        key: hashlib.sha256(path.read_bytes()).hexdigest()
        for key, path in paths.items()
    }
    result = summarize_domain_bias(
        read_rows(paths["p1"]), read_rows(paths["p4"]), read_rows(paths["unparsed"])
    )
    for key, path in paths.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[key]:
            raise RuntimeError("source changed during domain bias audit")
    result["source_sha256"] = hashes
    with args.out.open("x", encoding="utf8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "total": result["total_requests"],
                "cohorts": result["cohort_denominators"],
                "domains": len(result["by_domain"]),
                "new_exclusions": 0,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
