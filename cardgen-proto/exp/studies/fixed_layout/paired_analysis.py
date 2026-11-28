"""在冻结名单上分析首轮绝对合格判定。空白或未执行不会转成零。"""

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, quantiles

SEED = 20261124
N_BOOT = 10000
VALID = {"pass", "fail", "missing"}


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines()]


def analyze(roster, decisions):
    families = {r["task_id"]: r["family_id"] for r in roster}
    if not families or len(families) != len(roster) or not all(families.values()):
        raise ValueError("冻结名单为空、编号重复或缺少题组")
    votes = {}
    eligibility = {}
    for row in decisions:
        tid = row["task_id"]
        if tid in votes or tid not in families:
            raise ValueError("判定文件出现重复或名单外编号")
        pair = (row["A"], row["B"])
        if not all(v in VALID for v in pair):
            raise ValueError("判定必须为 pass、fail 或 missing")
        if "missing" in pair and not row.get("missing_reason"):
            raise ValueError("缺测需要说明原因")
        admission = row.get("pre_admission", "unknown")
        if admission not in {"admitted", "shared_blocked", "unknown"}:
            raise ValueError("前置准入状态无效")
        if admission == "shared_blocked" and ("pass" in pair or not row.get("admission_reason")):
            raise ValueError("共同适配阻断须有原因且不能同时判为通过")
        eligibility[tid] = admission
        votes[tid] = pair
    if set(votes) != set(families):
        raise ValueError("必须覆盖整个冻结名单，未执行应明确填 missing")
    counts = Counter(votes.values())
    n = len(roster)
    minimum, maximum = 0, 0
    clustered = defaultdict(list)
    for tid, (a, b) in votes.items():
        minimum += int(b == "pass") - int(a != "fail")
        maximum += int(b != "fail") - int(a == "pass")
        if "missing" not in (a, b):
            clustered[families[tid]].append(int(b == "pass") - int(a == "pass"))
    complete = sum(len(values) for values in clustered.values())
    admitted = [pair for tid, pair in votes.items() if eligibility[tid] == "admitted"]
    admitted_delta = None
    if admitted and all("missing" not in pair for pair in admitted):
        admitted_delta = mean(int(b == "pass") - int(a == "pass") for a, b in admitted)
    result = {
        "total_assigned": n,
        "complete_pairs": complete,
        "pairs_with_missing": n - complete,
        "both_pass": counts["pass", "pass"],
        "only_A_model_pass": counts["pass", "fail"],
        "only_B_program_pass": counts["fail", "pass"],
        "both_fail": counts["fail", "fail"],
        "all_assigned_difference_bounds_B_minus_A": [minimum / n, maximum / n],
        "all_assigned_point_difference": minimum / n if complete == n else None,
        "paired_cluster_percentile_ci95": None,
        "equal_family_weight_sensitivity_difference": None,
        "pre_admission_counts": dict(Counter(eligibility.values())),
        "descriptive_difference_on_pre_admitted_pairs": admitted_delta,
    }
    if complete != n:
        result["interval_status"] = "有缺测；仅全队列差值上下界，不把缺测剔除后宣告优效。"
        return result
    clusters = [(sum(clustered[k]), len(clustered[k])) for k in sorted(clustered)]
    result["equal_family_weight_sensitivity_difference"] = mean(s / k for s, k in clusters)
    if len(clusters) < 2 or len({s / k for s, k in clusters}) < 2:
        result["interval_status"] = "独立题组或差异变异不足，百分位区间无法提供可靠不确定性。"
        return result
    rng = random.Random(SEED)
    deltas = []
    for _ in range(N_BOOT):
        draw = rng.choices(clusters, k=len(clusters))
        deltas.append(sum(s for s, _ in draw) / sum(k for _, k in draw))
    cuts = quantiles(deltas, n=1000, method="inclusive")
    result["paired_cluster_percentile_ci95"] = [cuts[24], cuts[974]]
    result["interval_status"] = "按登记题组保留两臂配对，整组有放回重采样。"
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("roster", type=Path)
    cli.add_argument("decisions", type=Path)
    args = cli.parse_args()
    print(
        json.dumps(
            analyze(read_rows(args.roster), read_rows(args.decisions)), ensure_ascii=False, indent=2
        )
    )
