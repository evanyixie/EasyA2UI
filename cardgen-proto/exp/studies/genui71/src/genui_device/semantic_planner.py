"""从已接受语义选择构造有界商用组件候选，不生成布局、样式或业务事实。"""

from __future__ import annotations

from itertools import islice, product

from .contracts import Intent, Item, normalize_intent, validate_intent
from .semantic_components import numeric_value, scalar_readout, validate_peer_readouts
from .semantic_selection import SemanticPlan, readout_value_source, record_time_sources

MAX_CANDIDATES = 12


def _item(identity, component, references, role, entity):
    return Item(id=identity, component=component, fact_refs=list(references),
                role=role, group=entity or identity)


def _records(selection, facts):
    groups = {}
    for reference in selection.fact_refs:
        fact = facts.get(reference)
        if fact is None:
            raise ValueError(f"SEMANTIC_COMPONENT_UNKNOWN_FACT: {reference}")
        group = fact.entity or selection.entity
        if group is None:
            if selection.view == 'timeline':
                raise ValueError('SEMANTIC_TIMELINE_ENTITY: 时间线每条记录需要明确对象')
            group = selection.id
        groups.setdefault(group, []).append(reference)
    return groups


def _partitions(length):
    """同字号摘要组件按2/3项顺序分段，不改引用顺序或穷举任意树。"""
    if length == 0:
        return [()]
    choices = []
    for count in (3, 2):
        if count > length:
            continue
        for remaining in _partitions(length - count):
            choices.append((count, *remaining))
            if len(choices) == MAX_CANDIDATES:
                return choices
    return choices


def _table_references(records, facts):
    references = []
    if not 2 <= len(records) <= 3:
        return None
    for fields in records.values():
        if len(fields) != 2:
            return None
        labels = [ref for ref in fields if facts[ref].semantic == 'label']
        if len(labels) != 1:
            return None
        label = labels[0]
        value = next(ref for ref in fields if ref != label)
        references.extend((label, value))
    return references


def _ordered_pairs(references, facts):
    if len(references) not in {4, 6}:
        return None
    for start in range(0, len(references), 2):
        label, value = (facts[ref] for ref in references[start:start + 2])
        if label.semantic != 'label' or value.semantic == 'label':
            return None
        if label.entity != value.entity:
            return None
    return list(references)


def _readout_main(selection, facts):
    focus = getattr(selection, 'focus_ref', None)
    if focus is not None:
        return focus
    values = [reference for reference in selection.fact_refs
              if facts[reference].semantic != 'label']
    if len(values) != 1:
        raise ValueError('SEMANTIC_READOUT_FOCUS: 组合读数需要唯一可信主值来源')
    return values[0]


def _compound_readout(selection, facts, number):
    """主辅信息由已选关系确定；按商用18/12复合配方投影，不先试30再缩小。"""
    core = _readout_main(selection, facts)
    others = [reference for reference in selection.fact_refs if reference != core]
    supporting = [reference for reference in others if facts[reference].semantic != 'label']
    auxiliary = supporting[0] if supporting else (others[0] if others else None)
    main_refs = [core] if auxiliary is None else [core, auxiliary]
    main = _item(f'semantic_readout_{number}', 'EmphasisText', main_refs,
                 selection.role, selection.entity)
    before, after = [], []
    core_index = selection.fact_refs.index(core)
    for index, reference in enumerate(selection.fact_refs):
        if reference in main_refs:
            continue
        leaf = _item(f'semantic_readout_{number}_support_{index}', 'SecondaryBody',
                     [reference], 'secondary', selection.entity)
        (before if index < core_index else after).append(leaf)
    return [*before, main, *after]


def _closed_readout(request, selection, index, plan, facts):
    """闭合表示已有主值和唯一已选辅助，不从候选池寻找额外字段。"""
    core = _readout_main(selection, facts)
    if len(selection.fact_refs) == 2:
        auxiliary = next(reference for reference in selection.fact_refs if reference != core)
        return core, auxiliary, None
    if len(selection.fact_refs) != 1 or index + 1 >= len(plan.selections):
        return None
    supporting = plan.selections[index + 1]
    if supporting.role != 'secondary' or supporting.entity != selection.entity:
        return None
    if len(supporting.fact_refs) != 1 or supporting.view in {'progress', 'timeline'}:
        return None
    from .presentation import fact_role

    auxiliary = supporting.fact_refs[0]
    if fact_role(request, facts[auxiliary]) == 'context':
        return None
    return core, auxiliary, supporting.id


def _summary_with_details(request, selection, index, plan, facts):
    """单数量主值已有状态结论和独立详情时，初始使用商用双槽信息块。"""
    from .presentation import fact_role

    if len(selection.fact_refs) != 1:
        return None
    core = facts[selection.fact_refs[0]]
    if core.kind in {'date', 'time', 'duration'} or not readout_value_source(request, core):
        return None
    if sum(other.role == 'primary' for other in plan.selections) != 1:
        return None
    pair = _closed_readout(request, selection, index, plan, facts)
    if pair is None:
        return None
    _, auxiliary, supporting_id = pair
    if supporting_id is None or fact_role(request, facts[auxiliary]) != 'summary':
        return None
    has_details = False
    for other in plan.selections:
        if other.role != 'secondary' or other.entity != selection.entity:
            continue
        if other.id == supporting_id:
            continue
        if other.view == 'readout':
            if any(numeric_value(facts[ref]) for ref in other.fact_refs):
                return None  # 独立对比读数不视为普通详情，继续既有编排。
        if other.view not in {'text', 'details'}:
            continue
        if any(fact_role(request, facts[ref]) == 'detail' for ref in other.fact_refs):
            has_details = True
    return pair if has_details else None


def _commercial_readouts(request, plan, facts):
    """按整组语义一次决定组件族，测量只在该族的既有规格内编排。"""
    groups = {}
    indices = {}
    record_owners = {action.owner for action in plan.actions if action.scope == 'record'}
    for index, selection in enumerate(plan.selections):
        if selection.role != 'primary' or selection.view != 'readout':
            continue
        if selection.entity in record_owners:
            continue
        if selection.entity is not None:
            groups.setdefault(selection.entity, []).append(selection)
            indices[selection.id] = index
    compound_entities = set()
    for entity, selections in groups.items():
        for selection in selections:
            if len(selection.fact_refs) >= 3:
                compound_entities.add(entity)
                continue
            if len(selection.fact_refs) == 2:
                if all(facts[ref].semantic != 'label' for ref in selection.fact_refs):
                    compound_entities.add(entity)
    # 显式平级区域用同一复合主值规格；不因两边文字长度不同改变层级。
    changed = True
    while changed:
        changed = False
        for relation in plan.relations:
            if relation.kind != 'peer':
                continue
            pair = {relation.from_entity, relation.to_entity}
            if pair & compound_entities and not pair <= compound_entities:
                compound_entities.update(pair)
                changed = True
    overrides, consumed = {}, set()
    for entity, selections in groups.items():
        adjacent = [indices[selection.id] for selection in selections]
        consecutive = adjacent == list(range(adjacent[0], adjacent[0] + len(adjacent)))
        paired = all(len(selection.fact_refs) == 2 for selection in selections)
        if len(selections) in {2, 3} and consecutive and paired:
            references = []
            for selection in selections:
                references.extend(selection.fact_refs)
            pairs = _ordered_pairs(references, facts)
            if pairs is not None:
                first = selections[0]
                overrides[first.id] = [_item('semantic_readout_table_' + str(indices[first.id]),
                                            'TableText', pairs, 'primary', entity)]
                consumed.update(selection.id for selection in selections[1:])
                continue
        if len(selections) in {2, 3} and consecutive:
            named = True
            references = []
            for selection in selections:
                references.extend(selection.fact_refs)
                if len(selection.fact_refs) != 1:
                    named = False
                    continue
                if not facts[selection.fact_refs[0]].prefix.strip():
                    named = False
            if request.size == '2x4' and named:
                first = selections[0]
                overrides[first.id] = [_item('semantic_readout_summary_' + str(indices[first.id]),
                                            'SummaryList', references, 'primary', entity)]
                consumed.update(selection.id for selection in selections[1:])
                continue
        if len(selections) == 1:
            selection = selections[0]
            index = indices[selection.id]
            pair = _summary_with_details(request, selection, index, plan, facts)
            if pair is not None:
                core, auxiliary, supporting_id = pair
                overrides[selection.id] = [_item(f'semantic_readout_info_{index}', 'InfoBlock',
                    [core, auxiliary], 'primary', entity)]
                if supporting_id is not None:
                    consumed.add(supporting_id)
                continue
        closed = []
        if len(selections) >= 2:
            for selection in selections:
                pair = _closed_readout(request, selection, indices[selection.id], plan, facts)
                if pair is None:
                    closed = []
                    break
                closed.append(pair)
        if closed:
            for selection, pair in zip(selections, closed, strict=True):
                core, auxiliary, supporting_id = pair
                index = indices[selection.id]
                overrides[selection.id] = [_item(f'semantic_readout_info_{index}', 'InfoBlock',
                    [core, auxiliary], 'primary', entity)]
                if supporting_id is not None:
                    consumed.add(supporting_id)
            continue
        for selection in selections:
            index = indices[selection.id]
            if entity in compound_entities:
                overrides[selection.id] = _compound_readout(selection, facts, index)
                continue
            if len(selections) < 2:
                continue
            if len(selection.fact_refs) > 1:
                overrides[selection.id] = _compound_readout(selection, facts, index)
                continue
            # 已选单个辅助紧随主值时，它是本对象复合槽；不从候选池补造配料。
            if index + 1 >= len(plan.selections):
                continue
            supporting = plan.selections[index + 1]
            if supporting.role != 'secondary' or supporting.entity != entity:
                continue
            if len(supporting.fact_refs) != 1 or supporting.view in {'progress', 'timeline'}:
                continue
            auxiliary = facts[supporting.fact_refs[0]]
            from .presentation import fact_role

            if fact_role(request, auxiliary) == 'context':
                continue
            overrides[selection.id] = [_item(f'semantic_readout_info_{index}', 'InfoBlock',
                [selection.fact_refs[0], auxiliary.id], 'primary', entity)]
            consumed.add(supporting.id)
    return overrides, consumed


def _selection_options(request, selection, facts, number, record_actions):
    prefix = f'semantic_{number}'
    records = _records(selection, facts)
    references = selection.fact_refs
    if selection.role == 'title':
        return [[_item(prefix, 'SingleLineTitle', references, 'title', None)]]
    if selection.view == 'timeline':
        items = []
        for index, (entity, fields) in enumerate(records.items()):
            if not 2 <= len(fields) <= 7:
                raise ValueError('SEMANTIC_TIMELINE_FIELDS: 每条事件需要2至7个完整字段')
            event = _item(f'{prefix}_{index}', 'EventCard', fields, selection.role, entity)
            event.action_ref = record_actions.get(entity)
            items.append(event)
        return [items]
    if selection.role == 'secondary':
        items = []
        for entity, fields in records.items():
            for start in range(0, len(fields), 6):
                items.append(_item(f'{prefix}_{len(items)}', 'SecondaryBody',
                                   fields[start:start + 6], 'secondary', entity))
        return [items]
    if selection.view == 'readout' and len(references) >= 3:
        return [_compound_readout(selection, facts, number)]
    if selection.view == 'readout' and len(references) == 2:
        if not any(facts[reference].semantic == 'label' for reference in references):
            return [_compound_readout(selection, facts, number)]
        items = []
        for index, reference in enumerate(references):
            fact = facts[reference]
            if fact.semantic == 'label':
                component, role = 'SecondaryBody', 'secondary'
            else:
                component = 'EmphasizedData' if numeric_value(fact) else 'EmphasisText'
                role = selection.role
            items.append(_item(f'{prefix}_{index}', component, [reference], role,
                               selection.entity))
        return [items]
    if selection.view in {'details', 'list'}:
        pairs = _ordered_pairs(references, facts)
        if pairs is not None:
            return [[_item(prefix, 'TableText', pairs, selection.role, selection.entity)]]
    if selection.view == 'list':
        pairs = _table_references(records, facts)
        if pairs is not None:
            return [[_item(prefix, 'TableText', pairs, selection.role, selection.id)]]
        if request.size == '2x4' and len(records) == 1:
            options = []
            for partition in _partitions(len(references)):
                items, offset = [], 0
                for index, count in enumerate(partition):
                    items.append(_item(f'{prefix}_{index}', 'SummaryList',
                                       references[offset:offset + count], selection.role,
                                       selection.entity))
                    offset += count
                options.append(items)
            if options:
                return options
        if len(records) != len(references):
            raise ValueError('SEMANTIC_LIST_SHAPE: 列表需要完整标签值对或合法同对象摘要')
    items = []
    for entity, fields in records.items():
        for reference in fields:
            component = 'EmphasizedData' if numeric_value(facts[reference]) else 'EmphasisText'
            items.append(_item(f'{prefix}_{len(items)}', component, [reference],
                               selection.role, entity))
    return [items]


def _two_info_blocks(request, plan, facts):
    """双等权小块是初始商用选型，不是30fp读数容量失败后的降档。"""
    if request.size != '2x2' or plan.actions or len(plan.selections) != 4:
        return None
    primary = [selection for selection in plan.selections if selection.role == 'primary']
    if len(primary) != 2:
        return None
    if any(selection.view not in {'readout', 'text'} for selection in primary):
        return None
    if any(len(selection.fact_refs) != 1 for selection in primary):
        return None
    entities = {selection.entity for selection in primary}
    if None in entities or len(entities) != 2:
        return None
    if any(relation.kind == 'primary_support' for relation in plan.relations):
        return None
    items = []
    used = set()
    for number, core in enumerate(primary):
        context = []
        for selection in plan.selections:
            if selection.role != 'secondary' or selection.entity != core.entity:
                continue
            if len(selection.fact_refs) != 1:
                return None
            fact = facts[selection.fact_refs[0]]
            if fact.semantic == 'label' or fact.presentation == 'context':
                context.append(selection)
        if len(context) != 1:
            return None
        used.update((core.id, context[0].id))
        items.append(_item(f'semantic_info_{number}', 'InfoBlock',
                           [core.fact_refs[0], context[0].fact_refs[0]], 'primary', core.entity))
    if len(used) != len(plan.selections):
        return None
    return Intent(items=items)


def _single_focus(request, plan, facts):
    if request.size != '2x2' or plan.actions:
        return None
    primary = [selection for selection in plan.selections if selection.role == 'primary']
    if len(primary) != 1 or len(primary[0].fact_refs) != 1:
        return None
    if primary[0].view not in {'readout', 'text'}:
        return None
    core = facts[primary[0].fact_refs[0]]
    if core.kind in {'duration', 'date', 'time'} or core.unit or core.suffix:
        return None
    label, supporting = None, None
    for selection in plan.selections:
        if selection is primary[0]:
            continue
        if len(selection.fact_refs) != 1:
            return None
        fact = facts[selection.fact_refs[0]]
        if fact.entity is not None and fact.entity != core.entity:
            return None
        if selection.role == 'title' or fact.semantic == 'label':
            if label is not None or fact.path:
                return None
            label = fact.id
        elif fact.kind in {'date', 'time'} and supporting is None:
            supporting = fact.id
        else:
            return None
    if label is None:
        title = facts.get(request.title_fact_id)
        if title is None or title.path:
            return None
        label = title.id
    references = [label, core.id]
    if supporting is not None:
        references.append(supporting)
    return Intent(items=[_item('semantic_focus', 'DataDisplay', references,
                               primary[0].role, primary[0].entity)])


def _progress_items(plan, facts):
    items, consumed = {}, set()
    for selection in plan.selections:
        if selection.view != 'progress':
            continue
        value = facts[selection.fact_refs[0]]
        labels = []
        for other in plan.selections:
            if other.role != 'secondary' or len(other.fact_refs) != 1:
                continue
            fact = facts[other.fact_refs[0]]
            if fact.entity == value.entity and fact.semantic == 'label':
                labels.append(other)
        if len(labels) != 1:
            raise ValueError('SEMANTIC_PROGRESS_LABEL: 进度需要一个已选同对象标签')
        label = labels[0]
        consumed.add(label.id)
        items[selection.id] = _item('semantic_progress_' + str(len(items)),
                                   'ProgressCircleSingle', [label.fact_refs[0], value.id],
                                   selection.role, selection.entity)
    return items, consumed


def _actions(request, plan):
    result = []
    has_body = any(selection.role != 'title' for selection in plan.selections)
    for number, action in enumerate(plan.actions):
        if action.scope == 'record':
            continue
        component = 'PillButton'
        if len(plan.actions) >= 2 and (request.size == '2x4' or not has_body):
            component = 'CardButton'
        result.append(Item(id=f'semantic_action_{number}', component=component,
                           fact_refs=[], role='action', group=action.owner or 'actions',
                           action_ref=action.ref))
    return result


def _record_actions(plan):
    result = {}
    for action in plan.actions:
        if action.scope != 'record':
            continue
        if action.owner is None or action.owner in result:
            raise ValueError('SEMANTIC_RECORD_ACTION: 每条记录仅支持一个明确归属的点击动作')
        result[action.owner] = action.ref
    return result


def _record_items(request, plan, facts, actions):
    """点击记录本体是语义承诺；程序据明确归属聚合完整事件，不要求模型选组件。"""
    fields, roles = {}, {}
    time_sources = record_time_sources(request, facts.values())
    for selection in plan.selections:
        for reference in selection.fact_refs:
            entity = facts[reference].entity
            if entity not in actions:
                continue
            if selection.view == 'progress':
                raise ValueError('SEMANTIC_RECORD_VISUAL: 记录点击不能替代明确选择的进度表达')
            fields.setdefault(entity, []).append(reference)
            roles.setdefault(entity, set()).add(selection.role)
    result = {}
    for entity, action_ref in actions.items():
        references = fields.get(entity, [])
        if not 2 <= len(references) <= 7:
            raise ValueError('SEMANTIC_RECORD_FIELDS: 每条可点击记录需要2至7个完整字段')
        if not set(references) & time_sources:
            raise ValueError('SEMANTIC_RECORD_TIME: 可点击记录需要已选真实日期或时间')
        role = 'primary' if 'primary' in roles[entity] else 'secondary'
        item = _item(f'semantic_record_{len(result)}', 'EventCard', references, role, entity)
        item.action_ref = action_ref
        result[entity] = item
    return result


def _selection_parts(selection, facts, records, emitted):
    """已有记录与其余选择分离，顺序按首次出现保留，原合同和引用不改写。"""
    parts, remaining, inserted = [], [], False
    for reference in selection.fact_refs:
        entity = facts[reference].entity
        if entity in records:
            if entity not in emitted:
                parts.append(records[entity])
                emitted.add(entity)
        else:
            remaining.append(reference)
            if not inserted:
                parts.append(None)
                inserted = True
    if remaining:
        part = selection.model_copy(update={'fact_refs': remaining}, deep=True)
        parts = [part if value is None else value for value in parts]
    return parts


def _relation_constraints(plan, facts):
    """仅编译显式关系，未声明的顺序保持首次选择的稳定阅读顺序。"""
    roles, order = {}, []
    for selection in plan.selections:
        for reference in selection.fact_refs:
            entity = facts[reference].entity or selection.entity
            if entity is None:
                continue
            if entity not in roles:
                roles[entity] = set()
                order.append(entity)
            roles[entity].add(selection.role)
    edges = {entity: set() for entity in order}
    peers, supports = set(), set()
    for relation in plan.relations:
        source, target = relation.from_entity, relation.to_entity
        if source == target or source not in roles or target not in roles:
            raise ValueError('SEMANTIC_RELATION_ENTITY: 关系需要两个不同的已选对象')
        source_role = 'primary' if 'primary' in roles[source] else 'secondary'
        target_role = 'primary' if 'primary' in roles[target] else 'secondary'
        pair = frozenset((source, target))
        if relation.kind == 'peer':
            if source_role != target_role:
                raise ValueError('SEMANTIC_PEER_ROLE: 平级对象必须选择相同主次层级')
            peers.add(pair)
        elif relation.kind == 'primary_support':
            if source_role != 'primary' or target_role != 'secondary':
                raise ValueError('SEMANTIC_PRIMARY_SUPPORT_ROLE: 主辅关系与已选角色不一致')
            supports.add(pair)
            edges[source].add(target)
        else:
            edges[source].add(target)
    if peers & supports:
        raise ValueError('SEMANTIC_RELATION_CONFLICT: 同一对象对不能同时平级和主辅')
    remaining, ranked = set(order), []
    while remaining:
        ready = []
        for entity in order:
            if entity not in remaining:
                continue
            if not any(entity in edges[other] for other in remaining):
                ready.append(entity)
        if not ready:
            raise ValueError('SEMANTIC_RELATION_CYCLE: 对象先后关系存在循环')
        ranked.extend(ready)
        remaining.difference_update(ready)
    return ranked, edges, peers


def _apply_relations(request, items, facts, constraints):
    order, edges, peers = constraints
    rank = {entity: index for index, entity in enumerate(order)}
    content, headers, actions = [], [], []
    positions, levels = {}, {}
    for item in items:
        if item.role == 'title':
            headers.append(item)
            continue
        if item.role == 'action':
            actions.append(item)
            continue
        entities = {facts[ref].entity for ref in item.fact_refs if facts[ref].entity}
        for pair in peers:
            if len(entities) > 1 and entities & pair:
                raise ValueError('SEMANTIC_PEER_REGION_UNSUPPORTED: 平级对象需要独立组件区域')
        first = min((rank[entity] for entity in entities), default=len(order))
        content.append((first, item))
    content.sort(key=lambda entry: entry[0])
    result = [item for _, item in content]
    position = 0
    for item in result:
        for reference in item.fact_refs:
            fact = facts[reference]
            if fact.entity is not None:
                positions.setdefault(fact.entity, []).append(position)
            position += 1
            if item.role != 'primary' or fact.entity is None:
                continue
            is_readout = scalar_readout(fact) or fact.kind == 'duration'
            if reference != item.fact_refs[0] or not is_readout:
                continue
            level = {'EmphasizedData': 30, 'EmphasisText': 18,
                     'InfoBlock': 16 if request.size == '2x2' else 14,
                     'DataDisplay': 48}.get(item.component)
            if level is not None:
                levels.setdefault(fact.entity, set()).add(level)
    for source, targets in edges.items():
        for target in targets:
            if max(positions[source]) >= min(positions[target]):
                raise ValueError('SEMANTIC_ORDER_UNSUPPORTED: 当前复合组件不能表达明确对象顺序')
    for pair in peers:
        first, second = tuple(pair)
        if levels.get(first) and levels.get(second) and levels[first] != levels[second]:
            raise ValueError('SEMANTIC_PEER_LEVEL: 平级读数不能以不同字号通关')
    return [*headers, *result, *actions]


def _ensure_header(request, items, facts):
    title = facts.get(request.title_fact_id)
    if title is None or any(title.id in item.fact_refs for item in items):
        return items
    from .title_policy import representation

    intent = Intent(items=items)
    if representation(request, intent) != 'card_header':
        return items
    header = _item('semantic_header', 'SingleLineTitle', [title.id], 'title', None)
    return [header, *items]


def _plain_secondary(request, item, facts):
    from .presentation import fact_role

    if item.component != 'SecondaryBody' or item.role != 'secondary':
        return False
    if item.action_ref is not None or not item.fact_refs:
        return False
    entities = {facts[reference].entity for reference in item.fact_refs}
    if len(entities) != 1 or None in entities:
        return False
    return all(fact_role(request, facts[reference]) != 'context' for reference in item.fact_refs)


def _coalesce_secondary(request, items, facts):
    """相邻同对象普通正文沿既有成组配方测量，身份标题及业务边界保持独立。"""
    result = []
    for item in items:
        if result and _plain_secondary(request, item, facts):
            previous = result[-1]
            if _plain_secondary(request, previous, facts) and previous.group == item.group:
                references = [*previous.fact_refs, *item.fact_refs]
                if len(references) <= 6:
                    result[-1] = previous.model_copy(update={'fact_refs': references}, deep=True)
                    continue
        result.append(item)
    return result


def component_candidates(request, plan: SemanticPlan) -> list[Intent]:
    """保留已选内容和动作；只在同规格组件组合内生成最多12份完整意图。"""
    if request.component_contract != 'upstream-card-v1':
        raise ValueError('SEMANTIC_COMPONENT_PROFILE: 新策略需要商用组件合同')
    if plan.unresolved:
        raise ValueError('SEMANTIC_UNRESOLVED: 有未解决需求，不能程序补猜')
    facts = {fact.id: fact for fact in request.facts}
    constraints = _relation_constraints(plan, facts)
    readouts, readout_consumed = _commercial_readouts(request, plan, facts)
    paired = _two_info_blocks(request, plan, facts)
    if paired is not None:
        paired = Intent(items=_apply_relations(request, paired.items, facts, constraints))
        validate_intent(request, paired)
        validate_peer_readouts(request, paired)
        return [paired]
    focus = _single_focus(request, plan, facts)
    if focus is not None:
        focus = Intent(items=_apply_relations(request, focus.items, facts, constraints))
        validate_intent(request, focus)
        return [focus]
    progress, consumed = _progress_items(plan, facts)
    record_actions = _record_actions(plan)
    records = _record_items(request, plan, facts, record_actions)
    emitted = set()
    options = []
    for number, selection in enumerate(plan.selections):
        if selection.id in consumed or selection.id in readout_consumed:
            continue
        if selection.id in readouts:
            options.append([readouts[selection.id]])
        elif selection.id in progress:
            options.append([[progress[selection.id]]])
        else:
            parts = _selection_parts(selection, facts, records, emitted)
            for index, part in enumerate(parts):
                if isinstance(part, Item):
                    options.append([[part]])
                else:
                    identity = number if len(parts) == 1 else f'{number}_{index}'
                    options.append(_selection_options(request, part, facts, identity,
                                                       record_actions))
    actions = _actions(request, plan)
    results, seen = [], set()
    for combination in islice(product(*options), MAX_CANDIDATES):
        items = []
        for selected in combination:
            items.extend(selected)
        items.extend(actions)
        items = _coalesce_secondary(request, items, facts)
        items = _ensure_header(request, items, facts)
        items = _apply_relations(request, items, facts, constraints)
        intent = normalize_intent(request, Intent(items=items))
        validate_intent(request, intent)
        validate_peer_readouts(request, intent)
        identity = intent.model_dump_json()
        if identity not in seen:
            results.append(intent)
            seen.add(identity)
        if len(results) == MAX_CANDIDATES:
            break
    if not results:
        raise ValueError('SEMANTIC_NO_COMPONENTS: 没有完整商用组件候选')
    return results
