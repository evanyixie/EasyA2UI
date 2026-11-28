"""独立内容选择实验的模型提示、引用合同及 JSON 解码规则。"""

import json

SYSTEM = (
    "你负责桌面卡片的内容选择。阅读用户原始需求与候选，决定要展示哪些数据字段、提供哪些动作。"
    "结合用户说的对象、范围、意图和明确限制，合理选择。登记样值缺失不影响选择用户所需字段。"
    "只输出一个 JSON 对象，含 fact_ids 和 action_ids 两个数组。fact_ids 的值逐字取自 "
    "candidate_paths，action_ids 的值逐字取自 candidate_actions 的 id；可以为空，各数组内不重复。"
    "仅在可用候选中选择，不输出布局或解释。"
)


def check(answer, source):
    if not isinstance(answer, dict) or set(answer) != {"fact_ids", "action_ids"}:
        raise ValueError("输出需要且仅有 fact_ids 和 action_ids")
    allowed = {
        "fact_ids": source["candidate_paths"],
        "action_ids": [item["id"] for item in source["candidate_actions"]],
    }
    for key, pool in allowed.items():
        chosen = answer[key]
        if not isinstance(chosen, list) or not all(isinstance(v, str) for v in chosen):
            raise ValueError(key + " 应为字符串数组")
        if len(set(chosen)) != len(chosen) or set(chosen).difference(pool):
            raise ValueError(key + " 含重复或候选范围外的引用")
    return answer


def messages(source):
    return [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": json.dumps(
                source, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ),
        },
    ]


def no_duplicate_keys(pairs):
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError("JSON 有重复键")
    return obj
