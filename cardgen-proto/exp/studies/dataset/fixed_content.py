"""从答案侧已审核的节点证据提取有序展示来源。"""

import hashlib
import json
from collections import defaultdict
from copy import deepcopy

from audit_common import bindings

REVIEW_FLAGS = {
    "semantic_overlap_needs_review",
    "request_display_mismatch",
    "label_binding_mismatch",
    "slot_content_mismatch",
    "source_consistency_review",
    "semantic_role_review",
    "missing_age_value",
    "unfilled_age_template",
    "no_business_values",
    "placeholder_without_value",
    "progress_total_mismatch",
}


def validate(annotation: dict, source: dict) -> None:
    if annotation.get("case_id") != source["case_id"]:
        raise ValueError("案例来源不一致")
    texts = {item["id"] for item in source["texts"]}
    graphical = {item["id"] for item in source["non_text_data_nodes"]}
    covered, excluded = set(), []
    items = annotation.get("items")
    if not isinstance(items, list):
        raise TypeError("缺少独立数据证据")
    for item in items:
        number = item.get("n")
        if type(number) is not int or number <= 0:
            raise ValueError("数据项次数必须为正整数")
        identities = item.get("text_ids", [])
        non_text = item.get("non_text_ids", [])
        if not isinstance(identities, list) or not isinstance(non_text, list):
            raise TypeError("节点证据必须为列表")
        if not identities and not non_text:
            raise ValueError("数据项没有最终展示节点证据")
        if not set(identities) <= texts or not set(non_text) <= graphical:
            raise ValueError("引用了不在金标最终树中的展示节点")
        covered.update(identities)
    for item in annotation.get("excluded", []):
        if not item.get("reason"):
            raise ValueError("排除文字没有角色理由")
        excluded.append(item["id"])
    if len(excluded) != len(set(excluded)):
        raise ValueError("排除证据有重复ID")
    if set(excluded) & covered:
        raise ValueError("同一Text被同时作为数据和非数据排除")
    if covered | set(excluded) != texts:
        raise ValueError("存在遗漏或未知的Text，不能默默跳过")
    total = annotation.get("D")
    if total is not None and (type(total) is not int or total < 0):
        raise ValueError("D应为非负整数或未知")
    if total is not None and total != sum(item["n"] for item in items):
        raise ValueError("D与数据项计数不一致")
    if total is None and not annotation.get("notes"):
        raise ValueError("未知D必须给出原因")
    if "A" in annotation and annotation["A"] != source["A"]:
        raise ValueError("不可用需求或候选覆盖金标真实入口数")


def reviewed_source(source: dict, decision: dict | None) -> dict:
    """仅覆盖审计标注；保留原金标与原标注，不在程序中按样例选规则。"""
    updated = deepcopy(source)
    if decision is None:
        return updated
    if (
        decision["case_id"] != source["case_id"]
        or decision["old_D"] != source["D"]
        or decision["A"] != source["A"]
    ):
        raise ValueError("审核决定与冻结来源不一致")
    replacements = decision.get("replace_items", [])
    indices = [replacement["index"] for replacement in replacements]
    if len(indices) != len(set(indices)):
        raise ValueError("一个原始数据项不能被两次替换")
    for replacement in sorted(
        replacements, key=lambda item: item["index"], reverse=True
    ):
        index = replacement["index"]
        if not 0 <= index < len(source["items"]):
            raise ValueError("审核覆盖引用不存在的数据项")
        updated["items"][index : index + 1] = deepcopy(replacement["items"])
    for text in decision.get("exclude_texts", []):
        if any(existing["id"] == text["id"] for existing in updated["excluded"]):
            raise ValueError("不计D的展示文字已存在，不能重复登记")
        updated["excluded"].append(deepcopy(text))
    updated["D"] = decision["D"]
    updated["flags"] = [
        flag
        for flag in source.get("flags", [])
        if flag not in decision.get("remove_flags", [])
    ]
    updated["notes"] = decision["note"]
    validate(updated, source)
    return updated


def sampling_eligibility(quality_review: dict) -> bool:
    """审核历史保留在清单中；按状态准入，不以是否存在历史记录判断。"""
    if not quality_review:
        return True
    status = quality_review.get("status")
    if status == "context_rule_accepted":
        return True
    if status in {"excluded_duplicate", "context_review_hold"}:
        return False
    raise ValueError("未知的金标质量审核状态，不能自动纳入抽样")


def is_main_layout_candidate(record: dict) -> bool:
    return (
        record.get("eligible_for_sampling", True)
        and record.get("evaluation_subset", "main_layout") == "main_layout"
    )


def static_empty_texts(source: dict, decision: dict) -> list[dict]:
    texts = {text["id"]: text for text in source["texts"]}
    used, parts = set(), []
    for part in decision["text_parts"]:
        identities = part["source_text_ids"]
        if (
            not identities
            or set(identities) & used
            or len(identities) != len(set(identities))
        ):
            raise ValueError("静态空态文字来源重复或为空")
        values = [texts[identity] for identity in identities]
        if any(
            value["bindings"] or not isinstance(value["content"], str)
            for value in values
        ):
            raise ValueError("静态空态不得把动态绑定或非文字误作静态正文")
        parts.append(
            {
                "role": part["role"],
                "content": "".join(value["content"] for value in values),
            }
        )
        used.update(identities)
    if used != set(texts):
        raise ValueError("静态空态遗漏了原金标文字")
    return parts


def extract_item(item: dict, texts: dict, graphical: dict) -> tuple[dict, list[str]]:
    sources, issues = [], []
    for identity in item.get("text_ids", []):
        text = texts[identity]
        content = item.get("text_quotes", {}).get(identity, text["content"])
        if content != text["content"] and (
            text["bindings"]
            or not isinstance(content, str)
            or not content
            or content not in text["content"]
        ):
            raise ValueError("事实片段必须是原静态文字的非空精确子串，不能改写绑定")
        sources.append(
            {
                "type": "bound_text" if text["bindings"] else "static_text",
                "content": content,
                "bindings": text["bindings"],
            }
        )
    for identity in item.get("non_text_ids", []):
        found = sorted({path for _, path in bindings(graphical[identity])})
        sources.append(
            {"type": "bound_graphic" if found else "graphic", "binding_paths": found}
        )
    refs = {entry["path"] for source in sources for entry in source.get("bindings", [])}
    refs.update(path for source in sources for path in source.get("binding_paths", []))
    has_static = any(source["type"] == "static_text" for source in sources)
    if refs and item["n"] != len(refs):
        issues.append("dynamic_atomic_count_needs_confirmation")
    if not refs and item["n"] > 1:
        issues.append("static_atomic_breakdown_needs_confirmation")
    if not refs and not has_static:
        issues.append("graphic_fact_source_needs_confirmation")
    return {
        "name": item["name"],
        "count": item["n"],
        "sources": sources,
        "has_dynamic_reference": bool(refs),
        "has_static_text_evidence": has_static,
    }, issues


def classify(source: dict) -> dict:
    texts = {item["id"]: item for item in source["texts"]}
    graphical = {item["id"]: item for item in source["non_text_data_nodes"]}
    items, issues, ref_owners = [], set(), defaultdict(set)
    for index, item in enumerate(source["items"]):
        fact, found = extract_item(item, texts, graphical)
        fact["fact_id"] = f"fact_{index + 1}"
        items.append(fact)
        issues.update(found)
        for part in fact["sources"]:
            for binding in part.get("bindings", []):
                ref_owners[binding["path"]].add(index)
    if any(len(owners) > 1 for owners in ref_owners.values()):
        issues.add("same_binding_across_data_items_needs_confirmation")
    dynamic = any(item["has_dynamic_reference"] for item in items)
    static = any(item["has_static_text_evidence"] for item in items)
    if source["D"] == 0:
        kind = "actions_only" if source["A"] else "zero_data"
    elif dynamic:
        kind = "dynamic"
    elif static:
        kind = "static"
    else:
        kind = "unknown"
    if kind in {"zero_data", "unknown"}:
        issues.add("display_content_needs_confirmation")
    semantic = sorted(set(source.get("flags", [])) & REVIEW_FLAGS)
    if semantic:
        issues.add("existing_semantic_annotation_risk")
    supporting = [
        {
            "content": texts[item["id"]]["content"],
            "counted_in_D": False,
            "reason": item["reason"],
        }
        for item in source["excluded"]
    ]
    static_lengths = [
        len(part["content"])
        for item in items
        for part in item["sources"]
        if part["type"] == "static_text" and isinstance(part["content"], str)
    ]
    sample_lengths = [
        len(binding["sample_value"])
        for item in items
        for part in item["sources"]
        for binding in part.get("bindings", [])
        if isinstance(binding["sample_value"], str)
    ]
    return {
        "case_id": source["case_id"],
        "size": source["size"],
        "data_kind": kind,
        "mixed_static_dynamic": True
        if dynamic and static
        else None
        if dynamic
        else False,
        "mixed_marker_basis": "独立静态文字证据；表达式内部的静态事实尚待语义确认",
        "D": source["D"],
        "A": source["A"],
        "T": source["D"] + source["A"],
        "items": items,
        "supporting_text": supporting,
        "display_binding_paths": sorted(ref_owners),
        "count_review_reasons": sorted(issues),
        "semantic_flags": semantic,
        "existing_annotation_flags": source.get("flags", []),
        "existing_annotation_note": source.get("notes", ""),
        "max_static_text_chars": max(static_lengths, default=0),
        "max_dynamic_sample_chars": max(sample_lengths, default=0),
        "dynamic_max_length": None,
        "text_lengths_are_native_measurements": False,
        "basis": "candidate_layout_content_reconstructed_from_final_gold",
        "initial_model_selection_recovered": False,
        "independent_human_content_confirmation": False,
        "priority_entities_preferences_fully_confirmed": False,
        "ready_for_layout_experiment": False,
    }


def extract(source, annotation, messages):
    """仅使用已核对的展示节点、原始 onClick 和注释。"""
    validate(annotation, source)
    if annotation["D"] is None:
        raise ValueError("展示事实数仍待确定")
    record = classify(
        {
            **source,
            **{k: annotation[k] for k in ("items", "D", "excluded")},
            "flags": annotation.get("flags", []),
        }
    )
    updates = [
        message["updateComponents"]
        for message in messages
        if "updateComponents" in message
    ]
    if len(updates) != 1:
        raise ValueError("需要一份组件更新")
    nodes = {node["id"]: node for node in updates[0]["components"]}
    owners = {owner["id"]: owner for owner in source["compact_components"]}
    actions = []
    for index, action in enumerate(source["actions"], 1):
        node = nodes[action["id"]]
        handlers = node["onClick"]
        signature = hashlib.sha256(
            json.dumps(handlers, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        if (
            action["handler_sha256"] != signature
            or len(handlers) != action["handler_count"]
        ):
            raise ValueError("动作与冻结节点证据不符")
        caption = node.get("label")
        if caption is None:
            caption = owners.get(action.get("owner"), {}).get("args", {}).get("label")
        actions.append(
            {
                "action_id": f"action_{index}",
                "handlers": deepcopy(handlers),
                "caption": caption,
                "ownership_confirmed": False,
            }
        )
    return {
        **record,
        "actions": actions,
        "source_hashes": {k: source[k] for k in ("a2ui_sha256", "compact_sha256")},
    }
