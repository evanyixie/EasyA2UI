"""同题二元配对分析。方向为 right − left；仅处理调用者提供的记录。"""

import math
import random
import re
from collections import Counter, defaultdict


def _table(known):
    counts = Counter((left, right) for left, right in known)
    return {
        "both_fail": counts[False, False],
        "right_only": counts[False, True],
        "left_only": counts[True, False],
        "both_pass": counts[True, True],
    }


def _quantile(ordered, p):
    """线性插值的经验分位数（R type 7）。"""
    index = (len(ordered) - 1) * p
    lo = math.floor(index)
    hi = math.ceil(index)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)


def _cluster_bootstrap(groups, reps, seed):
    # 每次等概率抽家族；题目等权使每轮分母随抽中家族的大小变化。
    target, count = groups[0]
    degenerate = all(net * count == target * n for net, n in groups)
    if degenerate:
        limits = [target / count, target / count]
        status = "single_observed_family" if len(groups) == 1 else "constant_observed_family_effect"
    else:
        rng = random.Random(seed)
        estimates = []
        for _ in range(reps):
            sampled = rng.choices(groups, k=len(groups))
            numerator = sum(net for net, _ in sampled)
            denominator = sum(n for _, n in sampled)
            estimates.append(numerator / denominator)
        estimates.sort()
        limits = [_quantile(estimates, 0.025), _quantile(estimates, 0.975)]
        status = "coincident_empirical_percentiles" if limits[0] == limits[1] else "estimated"
    return {
        "reps": reps, "seed": seed, "quantile_method": "linear_type_7",
        "empirical_percentiles": limits, "ci95": limits if status == "estimated" else None,
        "precision_status": status,
    }


def _permutation(groups, reps, seed):
    # 交换整族两边等价于给该族净差加一个公平随机符号；零差家族不改变统计量。
    # 同幅度家族累计独立符号的正逆次数，不改变置换分布。
    observed = abs(sum(net for net, _ in groups))
    weights = sorted(Counter(abs(net) for net, _ in groups if net).items())
    if observed == 0:
        extreme = reps
    else:
        rng = random.Random(seed)
        extreme = 0
        for _ in range(reps):
            randomized = sum(weight * (2 * rng.getrandbits(n).bit_count() - n) for weight, n in weights)
            extreme += abs(randomized) >= observed
    return {"p_two_sided": (extreme + 1) / (reps + 1), "extreme": extreme, "reps": reps, "seed": seed}


def _representatives(families):
    # 先按输入摘要选代表；选择不使用结果。
    picked = [min(records, key=lambda entry: entry[0]) for records in families.values()]
    table = _table((left, right) for _, left, right in picked)
    plus, minus = table["right_only"], table["left_only"]
    discordant = plus + minus
    if discordant:
        numerator = 2 * sum(math.comb(discordant, i) for i in range(min(plus, minus) + 1))
        p = min(numerator, 2**discordant) / 2**discordant
    else:
        p = 1.0
    return {"n": len(picked), "paired_table": table, "discordant": discordant,
            "effect": (plus - minus) / len(picked), "p_exact_two_sided": p}


def analyze_pairs(rows, *, boot_reps=10000, perm_reps=100000, seed=20261124, descriptive=False):
    """完整分母上的效应界限；全已知时再计算题目等权效应及预注册家族统计。"""
    if any(type(rep) is not int or rep < 1 for rep in (boot_reps, perm_reps)) or type(seed) is not int:
        raise ValueError("重采样次数必须为正整数，随机种子必须为整数")
    families = defaultdict(list)
    all_families_known = True
    seen = set()
    known = []
    missing = Counter()
    lower = upper = 0
    for row in rows:
        if not isinstance(row, dict) or not {"family", "input_sha256", "left", "right"} <= row.keys():
            raise ValueError("缺少预注册配对字段")
        family, digest, left, right = (row[key] for key in ("family", "input_sha256", "left", "right"))
        if family is None and descriptive:
            all_families_known = False
        elif not isinstance(family, str) or not family.strip():
            raise ValueError("family 需要非空家族标识")
        if not isinstance(digest, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
            raise ValueError("input_sha256 需要 64 位十六进制摘要")
        digest = digest.lower()
        if digest in seen:
            raise ValueError("重复 input_sha256")
        seen.add(digest)
        if any(value is not None and type(value) is not bool for value in (left, right)):
            raise ValueError("配对结局仅允许 True、False 或 None")
        if family is not None:
            families[family].append((digest, left, right))
        lower += (0 if right is None else right) - (1 if left is None else left)
        upper += (1 if right is None else right) - (0 if left is None else left)
        if left is None and right is None:
            missing["both"] += 1
        elif left is None:
            missing["left_only"] += 1
        elif right is None:
            missing["right_only"] += 1
        else:
            known.append((left, right))
    n = len(seen)
    if not n:
        raise ValueError("空队列没有可定义的配对效应")
    table = _table(known)
    result = {
        "n_total": n, "n_known": len(known), "n_unknown": n - len(known),
        "n_families": len(families) if all_families_known else None,
        "coverage": len(known) / n, "paired_table": table,
        "missing_pattern": {key: missing[key] for key in ("both", "left_only", "right_only")},
        "discordant_known": table["right_only"] + table["left_only"],
        "effect_bounds": [lower / n, upper / n], "effect": None, "cluster_bootstrap": None,
        "family_permutation": None, "representative_mcnemar": None,
        "inference_status": "incomplete_endpoints" if len(known) < n else "complete",
    }
    if len(known) == n:
        result["effect"] = (table["right_only"] - table["left_only"]) / n
        if descriptive:
            result["inference_status"] = "descriptive_only"
            return result
        groups = []
        for family in sorted(families):
            records = families[family]
            groups.append((sum(right - left for _, left, right in records), len(records)))
        result.update(cluster_bootstrap=_cluster_bootstrap(groups, boot_reps, seed),
                      family_permutation=_permutation(groups, perm_reps, seed),
                      representative_mcnemar=_representatives(families))
    return result


def holm_adjust(p_values):
    """四个预注册比较顺序不变。缺测占据 p=1 的保守位置，结果仍为 None。"""
    values = list(p_values)
    if len(values) != 4 or any(
        p is not None and (type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1)
        for p in values
    ):
        raise ValueError("Holm 需要四个预注册比较，每个取 [0,1] 或 None")
    adjusted = [None] * 4
    running = 0.0
    for rank, i in enumerate(sorted(range(4), key=lambda k: 1 if values[k] is None else values[k])):
        p = 1 if values[i] is None else values[i]
        running = max(running, min(1.0, (4 - rank) * p))
        if values[i] is not None:
            adjusted[i] = running
    return adjusted
