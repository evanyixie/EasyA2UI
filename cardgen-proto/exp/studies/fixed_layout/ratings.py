"""在管理员侧解码双盲原判与配对一致性。"""

import hashlib
import json

SCHEMA = "dev-primary-review-v1"

LABELS = {"A", "B"}
DIMENSIONS = (
    "independent_business",
    "title_anchor",
    "body_alignment",
    "readable_text",
    "specialized_presentation",
    "schedule_timeline",
)
JUDGMENTS = {None, "pass", "fail", "unknown"}


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"重复 JSON 键 {key}")
        result[key] = value
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    data = path.read_bytes()
    return json.loads(data, object_pairs_hook=unique_keys), digest(data)


def option_rating(option, image_sha):
    scores = option["scores"]
    overall = option["overall"]
    note = option["note"]
    require(set(scores) == set(DIMENSIONS), "量表维度缺失或多余，未评分的维度写 null")
    require(isinstance(note, str), "评语须为文本")
    require(overall in JUDGMENTS, "整体判断无效")
    for key, value in scores.items():
        if value == "not_applicable":
            require(key != "independent_business", "独立业务判断不可选不适用")
        else:
            require(value in JUDGMENTS, f"{key} 的取值无效")
    missing_reason = "not_applicable" in scores.values() and not note.strip()
    contradicted = overall == "pass" and any(v in {"fail", "unknown"} for v in scores.values())
    if image_sha is None:
        require(overall is None and all(v is None for v in scores.values()), "缺图席位不能评分")
        state = "no_image"
    elif contradicted:
        state = "inconsistent"
    elif missing_reason or (overall == "pass" and None in scores.values()):
        state = "partially_rated"
    elif overall is None:
        state = "partially_rated" if any(v is not None for v in scores.values()) else "unrated"
    else:
        state = overall
    return {
        "state": state,
        "overall": overall,
        "effective_overall": state if state in {"pass", "fail", "unknown"} else None,
        "unexplained_na": bool(missing_reason),
        "scores": dict(scores),
        "note": note,
    }


def decode(export, packets):
    pid = export["packet_id"]
    require(export["schema"] == SCHEMA and pid in packets, "提交的协议或盲包身份不匹配")
    book = packets[pid]["items"]
    rows = export["items"]
    require(isinstance(rows, list) and len(rows) == len(book), f"{pid} 缺题或多题")
    decoded = {}
    for row in rows:
        code = row["code"]
        require(code in book, f"{pid} 含其他包或未知题号 {code}")
        source = book[code]
        task = source["task"]
        require(task not in decoded, f"{pid}/{code} 被评分两次")
        options = row["options"]
        labels = [o["label"] for o in options]
        require(len(labels) == 2 and set(labels) == LABELS, f"{pid}/{code} 缺少一个席位或重复")
        arms = {}
        for option in options:
            label = option["label"]
            arm = source["map"][label]
            arms[arm] = {"shown_as": label, **option_rating(option, source["images"][label])}
        preference = row["preference"]
        require(preference in {None, "A", "B", "tie", "unknown"}, "偏好取值无效")
        eligible = all(item["effective_overall"] == "pass" for item in arms.values())
        require(preference is None or eligible, "偏好仅限同一评审判定两侧均整体通过的题")
        decoded[task] = {
            "code": code,
            "arms": arms,
            "preference_eligible": eligible,
            "shown_preference": preference,
            "decoded_preference": source["map"].get(preference, preference),
        }
    return pid, decoded


def agreement(pairs, left_id, right_id):
    """只有双方的同席整体判定均为 pass/fail 时才计算二分类的一致性。"""
    counts = {x: {"pass": 0, "fail": 0} for x in ("pass", "fail")}
    for left, right in pairs:
        if left in counts and right in counts:
            counts[left][right] += 1
    n = sum(sum(row.values()) for row in counts.values())
    matches = sum(row[label] for label, row in counts.items())
    chance_numerator = sum(
        sum(row.values()) * sum(other[label] for other in counts.values())
        for label, row in counts.items()
    )
    denominator = n * n - chance_numerator
    return {
        "row_packet": left_id,
        "column_packet": right_id,
        "binary_confusion": counts,
        "jointly_binary": n,
        "other_seats": len(pairs) - n,
        "agreeing": matches,
        "observed_agreement": matches / n if n else None,
        "cohen_kappa": (matches * n - chance_numerator) / denominator if denominator else None,
    }
