"""首次模型只选择可信内容和信息关系，组件与几何由程序决定。"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .contracts import CardRequest, Fact
from .query_requirements import query_spans
from .query_transport import reference_view

PROTOCOL = "semantic-selection-v1"
IDENTITY = r"^[a-zA-Z][a-zA-Z0-9_]{0,31}$"


class SemanticContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SemanticSelection(SemanticContract):
    id: str = Field(pattern=IDENTITY)
    fact_refs: list[str] = Field(min_length=1, max_length=31)
    role: Literal["title", "primary", "secondary"]
    entity: str | None = Field(default=None, pattern=IDENTITY)
    view: Literal["readout", "text", "details", "list", "timeline", "progress"]
    mandatory: bool = True
    focus_ref: str | None = Field(default=None, min_length=1)


class SemanticAction(SemanticContract):
    ref: str = Field(min_length=1)
    owner: str | None = Field(default=None, pattern=IDENTITY)
    scope: Literal["entity", "record", "global"] = "entity"
    required: bool = True


class SemanticRelation(SemanticContract):
    from_entity: str = Field(pattern=IDENTITY)
    to_entity: str = Field(pattern=IDENTITY)
    kind: Literal["peer", "primary_support", "ordered"]


class SemanticPlan(SemanticContract):
    version: Literal["semantic-selection-v1"] = PROTOCOL
    selections: list[SemanticSelection] = Field(default_factory=list, max_length=16)
    actions: list[SemanticAction] = Field(default_factory=list, max_length=8)
    relations: list[SemanticRelation] = Field(default_factory=list, max_length=32)
    unresolved: list[str] = Field(default_factory=list, max_length=16)


def _check_route(request: CardRequest) -> None:
    from .selection_routing import request_route

    if request_route(request)["profile"] == "static_source":
        raise ValueError("SEMANTIC_SOURCE_UNSUPPORTED: 本地新策略尚未适配静态原文入口")


def semantic_messages(request: CardRequest) -> list[dict[str, str]]:
    _check_route(request)
    view, _ = reference_view(request)
    payload = {
        "query": view.query,
        "size": view.size,
        "title_ref": view.title_fact_id,
        "facts": [fact.model_dump(exclude_none=True) for fact in view.facts],
        "actions": [action.model_dump(exclude_none=True) for action in view.actions],
        "information_groups": [group.model_dump() for group in view.information_groups],
        "field_descriptions": request.provenance.get("field_descriptions", {}),
        "query_spans": query_spans(request.query),
        "response_schema": SemanticPlan.model_json_schema(),
    }
    instructions = (
        "按用户原需求一次选定内容和信息关系，只输出符合schema的JSON。"
        "事实与动作必须引用输入ID，不生成数值、单位、路径、动作参数或正文。"
        "候选存在不等于需要展示；按需求选择，原需求明确要求的数据或动作不可漏选。"
        "无法满足的要求或未解决歧义写入unresolved，不能用说明文字冒充所需数据。"
        "禁止组件名、骨架、布局树、坐标、宽高、字号和颜色。"
        "每个事实仅选一次；名称、数值、日期和条件属于原对象，不能跨对象挪用。"
        "每个selection表示一个语义展示单元，role表达主次；mandatory与主次相互独立。"
        "同一业务未被用户明确要求并列强调时，优先一个主焦点，"
        "其余明确要求字段完整保留为辅助；多个独立业务或用户明确要求对比、并列强调时，"
        "仍可有多个primary。required不等于primary，候选顺序靠前也不代表更重要。"
        "候选required:false仅表示宿主尚未强制，不代表用户允许省略；"
        "用户明确要求的事实须选入并保持mandatory=true（默认）。"
        "text/progress只引用一个事实；readout可单独引用一个读数，"
        "或合组同对象的一个可信numeric/quantity/duration主读数、至多一个已有label和"
        "至多两项紧密辅助，合组最多4个引用。readout的role只表达主读数层级，其余为secondary；"
        "多个可能主读数时必须用focus_ref指定已选引用，不能让程序猜测或丢弃其他值。"
        "唯一可信主读数可省focus_ref；原label加一个真实读数的写法保持兼容。"
        "details可引用同实体有序属性，list/timeline可引用多条记录且保留原实体身份。"
        "relations仅表达两个不同对象之间的平级、主辅或先后；不能自关联。"
        "只有一个对象时relations留空；同一对象内的主辅由selection.role表达，"
        "不能为同一对象写e0到e0的关系，也不能通过字段数量推断关系。"
        "动作owner指向其真实对象；共享或无法归属的动作用null，已有归属不能改。"
        "动作scope=record表示点击记录本体查看该记录详情，owner须对应已选记录对象，"
        "且该对象已选事实中须有真实date/time类型信息；不要求选择timeline，程序负责选型。"
        "scope=entity表示独立的对象操作，scope=global表示整卡共享且owner必须为null。"
        "宿主required事实和动作必须选入且保留mandatory/required=true。"
        "标题role仅引用title_ref。公共title_ref默认由程序托管；"
        "仅宿主required=true或用户明确指定要展示的标题才选入，不主动补选公共标题。"
        "业务对象及记录的必要名称仍须按需求选择，不能因标题托管而省略。"
        "label不是每个读数必选：已选名称或原文足以辨识时，不逐值叠加同义名称；"
        "用户要求名称或多个同类裸读数需消歧时，仍保留对应的已有名称。"
        "若确需显示用户给出的字面事实，可引用query_spans的qN整段原文ID；"
        "只能选择完整的事实原文，不能把请求指令当成显示内容，不能自由改写。"
        "精简输出：version、已知selection.entity、mandatory=true以及空的actions/relations/"
        "unresolved均可省略；不要机械重复所有默认字段。"
        '通用格式示意：{"selections":[{"id":"main","fact_refs":["f1"],'
        '"role":"primary","view":"readout"}]}；实际引用和条数必须按本次需求与候选选择。'
    )
    return [
        {"role": "system", "content": instructions},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _restore_references(plan, request):
    view, references = reference_view(request)
    entities = {}
    for original, alias in zip([*request.facts, *request.actions],
                               [*view.facts, *view.actions], strict=True):
        if original.entity is not None and alias.entity is not None:
            entities[alias.entity] = original.entity
    restored = plan.model_copy(deep=True)
    for selected in restored.selections:
        selected.fact_refs = [references.get(ref, ref) for ref in selected.fact_refs]
        selected.entity = entities.get(selected.entity, selected.entity)
        if selected.focus_ref is not None:
            selected.focus_ref = references.get(selected.focus_ref, selected.focus_ref)
    for action in restored.actions:
        action.ref = references.get(action.ref, action.ref)
        action.owner = entities.get(action.owner, action.owner)
    for relation in restored.relations:
        relation.from_entity = entities.get(relation.from_entity, relation.from_entity)
        relation.to_entity = entities.get(relation.to_entity, relation.to_entity)
    return restored


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"SEMANTIC_DUPLICATE_KEY: {key}")
        result[key] = value
    return result


def _materialize_literal(request, reference, selected, literal_sources):
    from .query_sources import numeric_shape

    span = next((part for part in query_spans(request.query) if part["id"] == reference), None)
    if span is None:
        raise ValueError(f"SEMANTIC_UNKNOWN_FACT: {reference}")
    identity = f"literal_{reference}"
    if any(fact.id == identity for fact in request.facts):
        raise ValueError(f"SEMANTIC_LITERAL_COLLISION: {identity}")
    literal_sources.append(dict(span))
    return Fact(id=identity, text=span["text"], required=selected.mandatory,
                entity=selected.entity, semantic="detail", **numeric_shape(span["text"]))


def _bound_numeric_source(request, fact):
    from .data_model import read

    if not fact.path:
        return False
    declared = False
    for binding in request.card_spec.get("dataBindings", []):
        target = binding.get("writeResultTo")
        if not isinstance(target, str) or not target:
            continue
        if fact.path == target or fact.path.startswith(target + "/"):
            declared = True
            break
    if not declared:
        return False
    try:
        value = read(request.data_model, fact.path)
    except ValueError:
        return False
    if type(value) is int:
        return True
    return type(value) is float and math.isfinite(value)


def readout_value_source(request: CardRequest, fact: Fact) -> bool:
    """信任宿主类型或已绑定快照中的真实数字，不解析文字样值或猜测字段名。"""
    if fact.semantic in {"label", "title"}:
        return False
    if fact.value is not None or fact.kind in {"quantity", "duration"}:
        return True
    return _bound_numeric_source(request, fact)


def _legacy_readout_value(chosen):
    labels = [fact for fact in chosen if fact.semantic == "label"]
    values = [fact for fact in chosen if fact.semantic not in {"label", "title"}]
    result: str | None = None
    if len(chosen) == 2 and len(labels) == 1 and len(values) == 1:
        value = values[0]
        if value.path or value.value is not None or value.kind in {
                "quantity", "duration", "date", "time"}:
            result = value.id
    return result


def _validate_readout(request, chosen, focus_ref):
    identities = {fact.id for fact in chosen}
    if focus_ref is not None and focus_ref not in identities:
        raise ValueError("SEMANTIC_FOCUS_REFERENCE: focus_ref必须引用本单元已选事实")
    if len(chosen) == 1:
        return chosen[0].id
    if len(chosen) > 4:
        raise ValueError("SEMANTIC_READOUT_SHAPE: readout最多一个主值、一个label和两项紧密辅助")
    labels = [fact for fact in chosen if fact.semantic == "label"]
    if len(labels) > 1 or any(fact.semantic == "title" for fact in chosen):
        raise ValueError("SEMANTIC_READOUT_SHAPE: readout至多一个同对象label，不能混入卡片标题")
    if len(chosen) - len(labels) - 1 > 2:
        raise ValueError("SEMANTIC_READOUT_SHAPE: readout至多两项紧密辅助")
    possible = [fact.id for fact in chosen if readout_value_source(request, fact)]
    legacy = _legacy_readout_value(chosen)
    if focus_ref is not None:
        if focus_ref not in possible and focus_ref != legacy:
            raise ValueError(
                "SEMANTIC_FOCUS_VALUE: focus_ref必须指向可信主读数，不能指向名称或说明"
            )
        return focus_ref
    if len(possible) == 1:
        return possible[0]
    if len(possible) > 1:
        raise ValueError("SEMANTIC_FOCUS_REQUIRED: 多个可能主读数须显式提供focus_ref")
    if legacy is not None:
        return legacy
    raise ValueError("SEMANTIC_READOUT_VALUE: 组合readout缺少可信主读数")


def _selected_facts(request, plan):
    candidates = {fact.id: fact for fact in request.facts}
    facts, seen, identities, selected_refs, literal_sources = [], set(), set(), {}, []
    normalized = []
    for selected in plan.selections:
        if selected.id in identities:
            raise ValueError(f"SEMANTIC_DUPLICATE_SELECTION: {selected.id}")
        identities.add(selected.id)
        if selected.view in {"text", "progress"} and len(selected.fact_refs) != 1:
            raise ValueError("SEMANTIC_ATOMIC_VIEW: text/progress仅接受一个事实")
        if selected.focus_ref is not None and selected.view != "readout":
            raise ValueError("SEMANTIC_FOCUS_VIEW: focus_ref仅用于readout")
        chosen, source_refs = [], {}
        for reference in selected.fact_refs:
            if reference in seen:
                raise ValueError(f"SEMANTIC_DUPLICATE_FACT: {reference}")
            seen.add(reference)
            fact = candidates.get(reference)
            if fact is None:
                fact = _materialize_literal(request, reference, selected, literal_sources)
            if fact.required and not selected.mandatory:
                raise ValueError(f"SEMANTIC_REQUIRED_FACT: {reference}")
            chosen.append(fact)
            source_refs[reference] = fact.id
        focus_ref = source_refs.get(selected.focus_ref, selected.focus_ref)
        entities = {fact.entity for fact in chosen if fact.entity is not None}
        if len(entities) > 1:
            if selected.view not in {"list", "timeline"} or selected.entity is not None:
                raise ValueError("SEMANTIC_ENTITY_MIX: 多实体记录只允许list/timeline且entity为null")
        elif entities and selected.entity not in entities | {None}:
            raise ValueError("SEMANTIC_ENTITY_CHANGED: 不能改写事实既有对象归属")
        entity = next(iter(entities)) if len(entities) == 1 else selected.entity
        if selected.role == "title":
            if selected.fact_refs != [request.title_fact_id] or entity is not None:
                raise ValueError("SEMANTIC_TITLE: 标题只能引用可信title_ref且不归属业务实体")
        for fact in chosen:
            selected_refs[fact.id] = selected.mandatory
            facts.append(fact.model_copy(update={
                "required": fact.required or selected.mandatory,
                "entity": fact.entity or entity,
            }, deep=True))
        normalized.append(selected.model_copy(update={
            "entity": entity, "fact_refs": [fact.id for fact in chosen], "focus_ref": focus_ref,
        }))
    for candidate in request.facts:
        if candidate.required and candidate.id not in selected_refs:
            raise ValueError(f"SEMANTIC_REQUIRED_FACT: {candidate.id}")
    for group in request.information_groups:
        references = set(group.fact_refs)
        if references & selected_refs.keys() and not references <= selected_refs.keys():
            raise ValueError(f"SEMANTIC_INFORMATION_GROUP: {group.id}")
    if request.title_fact_id and request.title_fact_id not in selected_refs:
        title = candidates.get(request.title_fact_id)
        if title is None:
            raise ValueError("SEMANTIC_TITLE: 可信标题引用不存在")
        facts.append(title.model_copy(deep=True))
    return facts, plan.model_copy(update={"selections": normalized}), literal_sources


def record_time_sources(request: CardRequest, facts: Iterable[Fact]) -> set[str]:
    """沿既有事实类型和已注册日程绑定识别时间，不从query或预览样值猜测。"""
    roots = []
    bindings = request.card_spec.get("dataBindings", [])
    for binding in bindings if isinstance(bindings, list) else []:
        if not isinstance(binding, dict) or binding.get("capabilityId") != "GetCalendarEvents":
            continue
        target = binding.get("writeResultTo")
        if isinstance(target, str) and target.startswith("/"):
            roots.append(target + "/events/")
    result = set()
    for fact in facts:
        if fact.kind in {"date", "time"}:
            result.add(fact.id)
            continue
        if not fact.path or fact.path.rsplit("/", 1)[-1] not in {"dtStart", "dtEnd", "startDate"}:
            continue
        if any(fact.path.startswith(root) for root in roots):
            result.add(fact.id)
    return result


def _selected_actions(request, plan, entities, facts):
    candidates = {action.id: action for action in request.actions}
    time_sources = record_time_sources(request, facts)
    record_owners = {fact.entity for fact in facts
                     if fact.entity is not None and fact.id in time_sources}
    chosen, seen = [], set()
    for selected in plan.actions:
        if selected.ref in seen:
            raise ValueError(f"SEMANTIC_DUPLICATE_ACTION: {selected.ref}")
        seen.add(selected.ref)
        action = candidates.get(selected.ref)
        if action is None:
            raise ValueError(f"SEMANTIC_UNKNOWN_ACTION: {selected.ref}")
        if action.required and not selected.required:
            raise ValueError(f"SEMANTIC_REQUIRED_ACTION: {selected.ref}")
        if selected.scope == "global" and selected.owner is not None:
            raise ValueError("SEMANTIC_GLOBAL_ACTION: 整卡共享动作不能声明局部owner")
        if selected.scope == "record":
            if selected.owner is None or selected.owner not in record_owners:
                raise ValueError(
                    "SEMANTIC_RECORD_ACTION: 记录详情动作须对应已选date/time事实的实体"
                )
        if selected.owner is not None and selected.owner not in entities:
            raise ValueError(f"SEMANTIC_UNKNOWN_OWNER: {selected.owner}")
        if action.entity is not None and selected.owner != action.entity:
            raise ValueError("SEMANTIC_ACTION_OWNER_CHANGED: 不能更改已知动作归属")
        chosen.append(action.model_copy(update={
            "entity": selected.owner, "required": action.required or selected.required,
        }, deep=True))
    for action in request.actions:
        if action.required and action.id not in seen:
            raise ValueError(f"SEMANTIC_REQUIRED_ACTION: {action.id}")
    return chosen


def _record_owners(request, plan, facts):
    """动作已核实后沿现有记录合同准入；不能用record声明绕过来源和容量边界。"""
    owners = set()
    for selected in plan.actions:
        if selected.scope != "record":
            continue
        if selected.owner in owners:
            raise ValueError("SEMANTIC_RECORD_ACTION: 每条记录仅支持一个明确归属的点击动作")
        owners.add(selected.owner)
    time_sources = record_time_sources(request, facts)
    for owner in owners:
        fields = [fact for fact in facts if fact.entity == owner]
        if not 2 <= len(fields) <= 7:
            raise ValueError("SEMANTIC_RECORD_FIELDS: 每条可点击记录需要2至7个完整字段")
        if not {fact.id for fact in fields} & time_sources:
            raise ValueError("SEMANTIC_RECORD_TIME: 可点击记录需要已选真实日期或时间")
    for selection in plan.selections:
        if selection.view == "progress" and selection.entity in owners:
            raise ValueError("SEMANTIC_RECORD_VISUAL: 记录点击不能替代明确选择的进度表达")
    return owners


def _readout_contracts(request, plan, facts):
    record_owners = _record_owners(request, plan, facts)
    available = {fact.id: fact for fact in facts}
    selections = []
    for selected in plan.selections:
        if selected.view != "readout":
            selections.append(selected)
            continue
        chosen = [available[ref] for ref in selected.fact_refs]
        if selected.entity in record_owners:
            if selected.focus_ref is not None and selected.focus_ref not in selected.fact_refs:
                raise ValueError("SEMANTIC_FOCUS_REFERENCE: focus_ref必须引用本单元已选事实")
            selections.append(selected)
            continue
        focus_ref = _validate_readout(request, chosen, selected.focus_ref)
        selections.append(selected.model_copy(update={"focus_ref": focus_ref}))
    return plan.model_copy(update={"selections": selections})


def decode_selection(raw: str, request: CardRequest) -> tuple[CardRequest, SemanticPlan]:
    _check_route(request)
    text = raw.strip()
    fence = re.fullmatch(r"```(?:json)?[ \t]*\r?\n([\s\S]*)\r?\n```", text)
    if fence is not None:
        text = fence.group(1)
    plan = SemanticPlan.model_validate(json.loads(text, object_pairs_hook=_unique_object))
    plan = _restore_references(plan, request)
    if plan.unresolved:
        raise ValueError("SEMANTIC_UNRESOLVED: " + json.dumps(plan.unresolved, ensure_ascii=False))
    if not plan.selections and not plan.actions:
        raise ValueError("SEMANTIC_EMPTY: 必须明确选择内容或真实动作")
    facts, plan, literal_sources = _selected_facts(request, plan)
    entities = {fact.entity for fact in facts if fact.entity is not None}
    actions = _selected_actions(request, plan, entities, facts)
    plan = _readout_contracts(request, plan, facts)
    seen_relations = set()
    for relation in plan.relations:
        if {relation.from_entity, relation.to_entity} - entities:
            raise ValueError("SEMANTIC_UNKNOWN_RELATION_ENTITY: 关系必须引用已选实体")
        key = (relation.from_entity, relation.to_entity, relation.kind)
        if relation.from_entity == relation.to_entity or key in seen_relations:
            raise ValueError("SEMANTIC_INVALID_RELATION: 关系重复或自引用")
        seen_relations.add(key)
    selected_refs = {reference for item in plan.selections for reference in item.fact_refs}
    selected_action_refs = {action.ref for action in plan.actions}
    audit = {
        "protocol": PROTOCOL,
        "plan": plan.model_dump(),
        "literal_sources": literal_sources,
        "unselected_facts": [fact.id for fact in request.facts if fact.id not in selected_refs],
        "unselected_actions": [action.id for action in request.actions
                               if action.id not in selected_action_refs],
        "limits": "引用和宿主义务已校验；未声称证明任意自然语言需求完整性",
    }
    readout_sources = []
    for selected in plan.selections:
        if selected.view != "readout":
            continue
        supporting = [ref for ref in selected.fact_refs if ref != selected.focus_ref]
        readout_sources.append(dict(
            selection_id=selected.id, focus_ref=selected.focus_ref, focus_role=selected.role,
            supporting_refs=supporting, supporting_role="secondary",
        ))
    audit["readout_sources"] = readout_sources
    resolved = request.model_copy(update={
        "facts": facts,
        "actions": actions,
        "requirement_mode": "resolved_query",
        "information_groups": [group for group in request.information_groups
                               if set(group.fact_refs) <= selected_refs],
        "independent_time_points": [ref for ref in request.independent_time_points
                                    if ref in selected_refs],
        "provenance": {**request.provenance, "semantic_selection": audit},
    }, deep=True)
    return resolved, plan


async def select_semantic(request, model, attempts):
    attempt = {"phase": "semantic_selection", "status": "started", "raw_response": None}
    attempts.append(attempt)
    call_start = len(getattr(model, 'calls', []))
    try:
        raw = await model.complete(semantic_messages(request), phase="semantic_selection")
        attempt["raw_response"] = raw
        result = decode_selection(raw, request)
    except Exception as exc:
        attempt.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        calls = getattr(model, "calls", [])
        if len(calls) > call_start and isinstance(calls[-1], dict):
            calls[-1].update(output_protocol=PROTOCOL, selection_error=str(exc))
            if attempt['raw_response'] is not None:
                calls[-1]['validation_error'] = str(exc)
        raise
    attempt["status"] = "accepted"
    calls = getattr(model, "calls", [])
    if len(calls) > call_start and isinstance(calls[-1], dict):
        calls[-1]["output_protocol"] = PROTOCOL
    return result
