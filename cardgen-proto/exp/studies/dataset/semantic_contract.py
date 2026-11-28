"""保管侧固定内容语义草案。以原证据核对主次、实体、关系及动作。"""

import copy
import json
import re
from collections import Counter

STATUSES = {"clear_ai", "needs_human", "source_quality_hold", "insufficient_evidence"}
ROLES = {"primary", "secondary", "identity", "context", "mixed"}
SCOPES = {"entity", "task_global", "shared", "unresolved"}
INTERACTIONS = {"whole_card", "record_click", "independent_entry", "preserve_unknown"}
REF = re.compile(r"\$\{([^}]+)\}")


def references(value):
    if isinstance(value, str):
        return set(REF.findall(value))
    if isinstance(value, list):
        return set().union(*(references(item) for item in value)) if value else set()
    if isinstance(value, dict):
        result = references(list(value.values()))
        if isinstance(value.get("path"), str):
            result.add(value["path"])
        return result
    return set()


def binding_paths(item):
    return {
        binding["path"]
        for source in item["sources"]
        for binding in source.get("bindings", [])
    } | {path for source in item["sources"] for path in source.get("binding_paths", [])}


def validate(packet, review):
    """仅结构与证据对应检查；此函数不推断语义正确或判人工通过。"""
    errors = []
    required = {
        "case_id",
        "status",
        "entities",
        "atoms",
        "relations",
        "actions",
        "preferences",
        "issues",
        "review_note",
        "human_confirmed",
        "ready_for_experiment",
    }
    if not required <= review.keys():
        return ["missing_required_fields"]
    if review["case_id"] != packet["case_id"] or review["status"] not in STATUSES:
        errors.append("identity_or_status")
    if (
        review["human_confirmed"] is not False
        or review["ready_for_experiment"] is not False
    ):
        errors.append("unearned_acceptance")
    entity_ids = [entity["id"] for entity in review["entities"]]
    if len(set(entity_ids)) != len(entity_ids):
        errors.append("duplicate_entity_id")
    parents = {item["fact_id"]: item for item in packet["items"]}
    counts = Counter()
    selected_paths = set()
    for atom in review["atoms"]:
        parent = parents.get(atom.get("parent"))
        if parent is None:
            errors.append("unknown_parent")
            continue
        counts[atom["parent"]] += atom.get("count", 1)
        if atom.get("entity") not in entity_ids or atom.get("role") not in ROLES:
            errors.append("atom_entity_or_role")
        take = atom.get("take")
        paths = binding_paths(parent)
        if take == "all":
            selected_paths |= paths
            if parent["count"] != 1:
                unresolved = (
                    atom.get("count") == parent["count"] and atom["role"] == "mixed"
                )
                if not unresolved or review["status"] == "clear_ai":
                    errors.append("composite_all_claimed_resolved")
        elif isinstance(take, dict) and set(take) == {"path"}:
            if take["path"] not in paths:
                errors.append("path_not_in_parent")
            selected_paths.add(take["path"])
        elif isinstance(take, dict) and set(take) == {"text"}:
            source_texts = [s.get("content", "") for s in parent["sources"]]
            if not take["text"] or not any(
                take["text"] in text for text in source_texts
            ):
                errors.append("text_not_in_parent")
            selected_paths |= references(take["text"])
        else:
            errors.append("unsupported_take")
        extra_paths = references(atom.get("derived_expression", ""))
        extra_paths |= set(atom.get("source_paths", []))
        if not extra_paths <= paths:
            errors.append("derived_reference_not_in_parent")
        selected_paths |= extra_paths
    expected_counts = Counter({key: item["count"] for key, item in parents.items()})
    if counts != expected_counts or sum(counts.values()) != packet["D"]:
        errors.append("D_or_parent_count_changed")
    expected_paths = set().union(*(binding_paths(item) for item in packet["items"]))
    if selected_paths != expected_paths:
        errors.append("selected_binding_coverage")
    source_ids = [action["action_id"] for action in packet["actions"]]
    action_ids = [action["action_id"] for action in review["actions"]]
    if Counter(source_ids) != Counter(action_ids) or len(action_ids) != packet["A"]:
        errors.append("A_or_action_coverage_changed")
    for action in review["actions"]:
        if (
            action.get("scope") not in SCOPES
            or action.get("interaction") not in INTERACTIONS
        ):
            errors.append("action_scope_or_interaction")
        if not set(action.get("owners", [])) <= set(entity_ids):
            errors.append("action_owner_unknown")
        if action.get("scope") == "unresolved" and not review["issues"]:
            errors.append("unresolved_action_without_issue")
        if "handlers" in action:
            errors.append("review_must_not_rewrite_handler")
    for relation in review["relations"]:
        if (
            relation.get("from") not in entity_ids
            or relation.get("to") not in entity_ids
        ):
            errors.append("relation_entity_unknown")
        if not relation.get("type") or not relation.get("evidence"):
            errors.append("relation_without_evidence")
    raw_text = json.dumps(packet["original_request"], ensure_ascii=False)
    for preference in review["preferences"]:
        if not preference.get("quote") or preference["quote"] not in raw_text:
            errors.append("preference_not_source_quote")
    if not review["review_note"]:
        errors.append("empty_review_note")
    return sorted(set(errors))


def contract(packet, review):
    """无旧布局/组件/样式答案的语义合同草案；保留原表达式不降级成字面文本。"""
    actions = {row["action_id"]: row for row in packet["actions"]}
    graph = packet["private_source_evidence"]["original_graphic_evidence"]
    needed = set().union(*(binding_paths(item) for item in packet["items"]))
    needed |= references([row["handlers"] for row in packet["actions"]])
    samples = {}
    for source in packet["private_original_compacts"]:
        for row in source["rows"]:
            if len(row) != 2 or not isinstance(row[0], str):
                continue
            if row[0] in needed:
                if row[0] in samples and samples[row[0]] != row[1]:
                    raise ValueError("同一任务别名的冻结样值冲突，不能默取最后一份")
                samples[row[0]] = row[1]
    groups = []
    for item in packet["items"]:
        groups.append(
            {
                "id": item["fact_id"],
                "count": item["count"],
                "selected_value_sources": copy.deepcopy(item["sources"]),
            }
        )
    action_rows = []
    for row in review["actions"]:
        action_rows.append(
            {
                key: copy.deepcopy(value)
                for key, value in row.items()
                if key != "evidence"
            }
        )
        action_rows[-1]["handlers"] = copy.deepcopy(
            actions[row["action_id"]]["handlers"]
        )
        action_rows[-1]["caption"] = actions[row["action_id"]]["caption"]
    return {
        "task_id": packet["task_id"],
        "schema": "fixed-layout-content-audit-v1",
        "size": packet["size"],
        "D": packet["D"],
        "A": packet["A"],
        "content_groups": groups,
        "semantic_units": copy.deepcopy(review["atoms"]),
        "entities": [
            {key: value for key, value in entity.items() if key != "evidence"}
            for entity in review["entities"]
        ],
        "relations": [
            {key: value for key, value in relation.items() if key != "evidence"}
            for relation in review["relations"]
        ],
        "actions": action_rows,
        "supporting_text": copy.deepcopy(packet["supporting_text"]),
        "numeric_semantics": [
            {"value": row["value"], "scale_total": row.get("total")} for row in graph
        ],
        "binding_samples": samples,
        "user_preferences": copy.deepcopy(review["preferences"]),
        "constraints": {
            "content_selection_locked": True,
            "may_delete_content": False,
            "may_add_data_facts": False,
            "may_reassign_actions": False,
            "use_frozen_gold_samples_only": True,
            "dynamic_length_stress_enabled": False,
            "roles_are_entity_local": True,
            "semantic_entity_names_are_metadata_not_additional_display_facts": True,
            "supporting_labels_units_and_original_expression_meaning_must_be_preserved": True,
        },
        "audit_status": review["status"],
        "human_confirmed": False,
        "ready_for_experiment": False,
        "limitation": "逐例AI审核草案；暂挂项不能执行。不是历史首次模型输出或独立视觉验收。",
    }
