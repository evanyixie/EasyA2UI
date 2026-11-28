"""把调用方冻结的显示合同投影为保留来源、归属与动作的共有单元。"""

import copy
import re
from collections import Counter

from expressions import UNKNOWN, tokens
from runtime import data_model as DATA


def require(condition, cause):
    if not condition:
        raise ValueError(cause)


def shown(expression, samples):
    stream = tokens(expression)
    require(stream is not UNKNOWN, "未覆盖显示表达式")
    return "".join(DATA.display(samples[x]) if kind == "path" else x for kind, x in stream)


def affix(expression, prefix="", suffix=""):
    if not prefix and not suffix:
        return expression
    if not expression.lstrip().startswith("{{"):
        return prefix + expression + suffix

    def literal(value):
        require(not any(ch in value for ch in "'\\\r\n"), "标签超出原生单引号文本的保真范围")
        return "'" + value + "'"

    core = expression.strip()[2:-2].strip()
    pieces = ([literal(prefix)] if prefix else []) + [core] + ([literal(suffix)] if suffix else [])
    return "{{ " + " + ".join(pieces) + " }}"


def support_leaf(idx, raw, role, entity=None, for_unit=None):
    return {
        "id": f"support_{idx + 1}",
        "kind": "text",
        "role": role,
        "entity": entity,
        "expression": raw,
        "original_expression": raw,
        "sample_text": raw,
        "paths": [],
        "source_refs": [],
        "supported_text_indices": [idx],
        "for_unit": for_unit,
    }


def document(row):
    limits = row["constraints"]
    require(
        limits["content_selection_locked"]
        and not any(
            limits[k] for k in ("may_delete_content", "may_add_data_facts", "may_reassign_actions")
        ),
        "需要锁定的选择合同",
    )
    groups, refs, samples = row["content_groups"], row["semantic_units"], row["binding_samples"]
    require(
        row["D"] == sum(g["count"] for g in groups) and row["A"] == len(row["actions"]),
        "冻结计数错误",
    )
    entities = {e["id"]: e for e in row["entities"]}
    units, assigned = [], []
    for group in groups:
        g_refs = [(i, s) for i, s in enumerate(refs) if s["parent"] == group["id"]]
        require(sum(s.get("count", 1) for _, s in g_refs) == group["count"], "语义叶计数不等")
        for j, source in enumerate(group["selected_value_sources"], 1):
            exp = source["content"]
            stream = tokens(exp)
            require(stream is not UNKNOWN, "不支持原始表达式")
            paths = [v for k, v in stream if k == "path"]
            require(
                paths == [b["path"] for b in source["bindings"]]
                and all(
                    samples[b["path"]] == b["sample_value"]
                    and type(samples[b["path"]]) is type(b["sample_value"])
                    for b in source["bindings"]
                ),
                "路径序列或冻结样值冲突",
            )
            owners = [
                (i, s)
                for i, s in g_refs
                if (s["take"] == "all" and len(group["selected_value_sources"]) == 1)
                or (isinstance(s["take"], dict) and s["take"]["path"] in paths)
            ]
            require(
                owners and len({(s["entity"], s["role"]) for _, s in owners}) == 1,
                "原表达式跨实体或跨角色",
            )
            entity, role = owners[0][1]["entity"], owners[0][1]["role"]
            require(
                entity in entities and role in {"identity", "primary", "secondary", "context"},
                "未知实体/角色",
            )
            owned = [i for i, _ in owners]
            assigned.extend(owned)
            units.append(
                {
                    "id": f"{group['id']}_{j}",
                    "kind": "text",
                    "role": role,
                    "entity": entity,
                    "expression": exp,
                    "original_expression": exp,
                    "sample_text": shown(exp, samples),
                    "paths": paths,
                    "source_refs": owned,
                    "supported_text_indices": [],
                }
            )
    require(Counter(assigned) == Counter(range(len(refs))), "存在未投影或重复投影的语义事实")

    # 旧适配器只把 supporting_text 的真实字符串排进卡；其余语义标签只解释来源和角色。
    action_units = []
    for a in row["actions"]:
        require(a["handlers"] and set(a["owners"]) <= set(entities), "非法动作实体或处理器")
        if a["interaction"] == "independent_entry":
            require(a["caption"] and len(a["owners"]) <= 1, "独立入口缺标题或拥有多个实体")
            u = support_leaf(-1, a["caption"], "action", next(iter(a["owners"]), None))
            u.update(
                id=a["action_id"],
                kind="button",
                supported_text_indices=[],
                action_ref=a["action_id"],
            )
            action_units.append(u)
        elif a["interaction"] == "record_click":
            require(len(a["owners"]) == 1 and a["caption"] is None, "记录动作归属或标签歧义")
        else:
            require(a["interaction"] == "whole_card" and a["caption"] is None, "未知动作拓扑")
    titles, labels = [], {}
    for ix, raw in enumerate(row["supporting_text"]):
        unit_options = [
            u for u in units if any(refs[i].get("unit") == raw for i in u["source_refs"])
        ]
        exact = [u for u in units + action_units if u["sample_text"] == raw]
        if len(exact) == 1:
            exact[0]["supported_text_indices"].append(ix)
        elif len(unit_options) == 1:
            u = unit_options[0]
            if not u["sample_text"].endswith(raw):
                u["expression"] = affix(u["expression"], suffix=raw)
                u["sample_text"] = shown(u["expression"], samples)
            u["supported_text_indices"].append(ix)
        else:
            require(not unit_options and not exact, "辅助文本有多个相同归属")
            lit = raw.strip()
            hits = [
                u
                for u in units
                if lit
                and any(
                    lit in refs[i].get("label", "") or lit == entities[u["entity"]]["name"]
                    for i in u["source_refs"]
                )
            ]
            if len(hits) == 1:
                u = hits[0]
                if re.fullmatch(r"([+-]?\d+(?:\.\d+)?)(%|℃|天|步|分)?", u["sample_text"]):
                    require(u["id"] not in labels, "数值读数存在不唯一的单独标签")
                    labels[u["id"]] = support_leaf(ix, raw, "identity", u["entity"], u["id"])
                elif (
                    u["sample_text"].startswith(raw)
                    and str(u["original_expression"]).lstrip().startswith("{{")
                    and (tokens(u["original_expression"])[0] == ("text", raw))
                ):
                    u["supported_text_indices"].append(ix)
                else:
                    u["expression"] = affix(u["expression"], prefix=raw)
                    u["sample_text"] = shown(u["expression"], samples)
                    u["supported_text_indices"].append(ix)
            else:
                titles.append(support_leaf(ix, raw, "title"))
    require(len(titles) <= 1, "未归属的首部文字超过一个")
    visible = list(titles)
    for u in units:
        if u["id"] in labels:
            visible.append(labels[u["id"]])
        visible.append(u)
    visible.extend(action_units)
    require(
        Counter(i for u in visible for i in u["supported_text_indices"])
        == Counter(range(len(row["supporting_text"]))),
        "辅助文字未完整使用一次",
    )
    size = row["size"]
    require(size in ("2x2", "2x4"), "不支持画布")
    result = {
        k: copy.deepcopy(row[k])
        for k in (
            "task_id",
            "size",
            "D",
            "A",
            "entities",
            "relations",
            "actions",
            "semantic_units",
            "numeric_semantics",
            "binding_samples",
            "supporting_text",
            "user_preferences",
            "constraints",
        )
    }
    result.update(
        canvas={"width": 150 if size == "2x2" else 300, "height": 150},
        units=visible,
        preference_issues=[
            {
                "kind": p["kind"],
                "quote": p["quote"],
                "cause": "冻结输入仅含偏好文字，未提供参考图像资产",
                "fulfilled": None,
            }
            for p in row["user_preferences"]
        ],
    )
    return result
