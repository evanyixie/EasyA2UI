"""冻结六档队列的入口：保留首轮和共同修复后两个检查点及缺测。"""

import re
from collections import Counter

from endpoint import assess
from paired_stats import analyze_pairs, holm_adjust

ARMS = ("L1", "L2", "L3", "L4", "L5", "L6")
POINTS = ("raw_first", "after_common_repair")
PRIMARY = ("L4", "L5")
SECONDARY = (("L1", "L2"), ("L2", "L3"), ("L3", "L4"), ("L5", "L6"))
VALUES = {"pass": True, "fail": False, "unknown": None}


def digest(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def collect(roster, observations, version_hash):
    if not digest(version_hash):
        raise ValueError("实验版本需要冻结 SHA-256")
    tasks = {r["task_id"]: r for r in roster}
    if (
        not tasks
        or len(tasks) != len(roster)
        or len({r["input_sha256"] for r in roster}) != len(roster)
    ):
        raise ValueError("名单为空，或题目编号、原始输入出现重复")
    if any(not tid or not digest(r["input_sha256"]) for tid, r in tasks.items()):
        raise ValueError("名单缺题目或原始输入 SHA-256")
    decisions = {}
    for row in observations:
        key = tid, arm, point = row["task_id"], row["arm"], row["checkpoint"]
        if (
            tid not in tasks
            or arm not in ARMS
            or point not in POINTS
            or key in decisions
        ):
            raise ValueError(f"名单外或重复记录 {key}")
        if (
            tasks[tid]["input_sha256"] != row["input_sha256"]
            or row["version_sha256"] != version_hash
        ):
            raise ValueError(f"同题输入或版本与冻结名单不一致 {key}")
        for field in ("original_artifact_sha256", "artifact_sha256"):
            if field not in row or row[field] is not None and not digest(row[field]):
                raise ValueError(f"产物摘要未登记或无效 {key} {field}")
        original = row["original_artifact_sha256"]
        current = row["artifact_sha256"]
        if point == "raw_first" and original != current or current and not original:
            raise ValueError(f"首轮原件及其派生产物无法配对 {key}")
        if (
            row["execution"]["status"]
            in {"artifact_checks_pass", "artifact_emitted", "native_captured"}
            and not current
        ):
            raise ValueError(f"已发射的产物缺字节摘要 {key}")
        if not current and row.get("c04"):
            raise ValueError(f"没有本检查点的产物，不可附原生测量 {key}")
        subject = {
            "task_id": tid,
            "arm": arm,
            "checkpoint": point,
            "artifact_sha256": current,
        }
        if "artifact" in row and (
            not current or row["artifact"].get("subject") != subject
        ):
            raise ValueError(f"评估的字节与本次发射产物不符 {key}")
        for name, proof in row.get("primary_evidence", {}).items():
            if name in {"first_response_lineage", "common_repair_lineage"}:
                continue
            if proof.get("status") in {"pass", "fail"} and (
                not current or proof.get("subject") != subject
            ):
                raise ValueError(f"评分证据与检查点或产物未配对 {key} {name}")
        decision = assess(row)
        decisions[key] = {
            "input_sha256": row["input_sha256"],
            "version_sha256": version_hash,
            "original_artifact_sha256": original,
            "artifact_sha256": current,
            "execution_ref": row["execution"]["evidence_ref"],
            **decision,
        }
    expected = {(tid, arm, point) for tid in tasks for arm in ARMS for point in POINTS}
    if set(decisions) != expected:
        raise ValueError("须显式逐格登记未执行、拒绝或未知，不能漏行或缩减分母")
    for tid in tasks:
        for arm in ARMS:
            first, repaired = (decisions[tid, arm, p] for p in POINTS)
            if first["artifact_sha256"] != repaired["original_artifact_sha256"]:
                raise ValueError(f"两个检查点引用了不同的首轮原件 {tid} {arm}")
    return decisions


def endpoint_value(decision, outcome):
    if outcome in {"primary", "c04"}:
        return decision[outcome]["status"]
    return decision["c04"]["sensitivity"][outcome]["status"]


def summarize(roster, decisions, *, descriptive=False, **options):
    summary = {}
    for point in POINTS:
        for outcome in ("primary", "c04", "60_percent", "100_percent"):
            label = f"{point}/{outcome}"
            counts = {}
            for arm in ARMS:
                states = Counter(
                    endpoint_value(decisions[r["task_id"], arm, point], outcome)
                    for r in roster
                )
                counts[arm] = {k: states[k] for k in VALUES}
            contrasts = {}
            for left, right in (PRIMARY, *SECONDARY):
                pairs = [
                    {
                        "input_sha256": r["input_sha256"],
                        "family": r.get("family"),
                        "left": VALUES[
                            endpoint_value(
                                decisions[r["task_id"], left, point], outcome
                            )
                        ],
                        "right": VALUES[
                            endpoint_value(
                                decisions[r["task_id"], right, point], outcome
                            )
                        ],
                    }
                    for r in roster
                ]
                contrasts[f"{right}-{left}"] = analyze_pairs(
                    pairs, descriptive=descriptive, **options
                )
            confirmatory = (
                point == "after_common_repair"
                and outcome == "primary"
                and not descriptive
            )
            adjusted = None
            if confirmatory:
                names = [f"{right}-{left}" for left, right in SECONDARY]
                p_values = [
                    (contrasts[n]["family_permutation"] or {}).get("p_two_sided")
                    for n in names
                ]
                adjusted = dict(zip(names, holm_adjust(p_values), strict=True))
            summary[label] = {
                "N": len(roster),
                "arms": counts,
                "contrasts": contrasts,
                "predeclared_primary": confirmatory,
                "holm_secondary": adjusted,
            }
    return summary
