"""首次语义合同由程序选型，固定内容、主次和对象，不锁唯一容器骨架。"""

import copy
import json

import pytest
from test_commercial_peer_actions import peer_card, walk
from test_entity_capacity import FixedGlyphMeasure

from genui_device.container_layout import leaves, plan_card_containers
from genui_device.contracts import CardRequest, validate_intent
from genui_device.native_layout import container_nodes
from genui_device.semantic_planner import MAX_CANDIDATES, component_candidates
from genui_device.semantic_selection import decode_selection


def request_value(facts, *, size='2x4', actions=None, title=None, height=150):
    return CardRequest(
        case_id='semantic-program', query='展示所选内容并保留操作', size=size,
        component_contract='upstream-card-v1', facts=facts, actions=actions or [],
        surface=dict(width_vp=300 if size == '2x4' else 150, height_vp=height),
        title_fact_id='title' if title else None,
        card_spec=dict(title=title) if title else {},
    )


def selected(identity, refs, *, role='primary', view='readout', entity=None):
    return dict(id=identity, fact_refs=refs, role=role, view=view, entity=entity)


def compile_plan(request, selections, *, actions=None, relations=None):
    value = dict(selections=selections, actions=actions or [], relations=relations or [])
    resolved, plan = decode_selection(json.dumps(value, ensure_ascii=False), request)
    return resolved, plan, component_candidates(resolved, plan)


def numeric_fact(identity='value', *, entity='device', value=68, unit='%'):
    return dict(id=identity, text=str(value) + unit, kind='quantity', semantic='metric',
                value=value, unit=unit, entity=entity)


@pytest.mark.parametrize('kind,text,component', [
    ('quantity', '68%', 'EmphasizedData'),
    ('duration', '7小时10分', 'EmphasisText'),
    ('date', '2026-11-20', 'EmphasisText'),
    ('time', '18:30', 'EmphasisText'),
    ('text', '正常工作', 'EmphasisText'),
])
def test_atomic_readout_preserves_commercial_font_class(kind, text, component):
    fact = dict(id='reading', text=text, kind=kind, entity='device')
    if kind == 'quantity':
        fact.update(value=68, unit='%')
    request = request_value([fact])
    _, _, candidates = compile_plan(request, [selected('reading', ['reading'])])
    assert len(candidates) == 1
    assert candidates[0].items[0].component == component
    assert candidates[0].items[0].role == 'primary'
    assert candidates[0].items[0].fact_refs == ['reading']


def test_focus_uses_trusted_title_and_does_not_generate_a_label():
    request = request_value([
        dict(id='title', text='未接来电', semantic='title', required=False),
        numeric_fact(unit='', value=3),
    ], size='2x2', title='未接来电')
    resolved, _, candidates = compile_plan(request, [selected('reading', ['value'])])
    assert len(candidates[0].items) == 1
    assert candidates[0].items[0].component == 'DataDisplay'
    assert candidates[0].items[0].fact_refs == ['title', 'value']
    assert [fact.id for fact in resolved.facts] == ['value', 'title']


def test_complete_duration_never_uses_focus_or_numeric_slot():
    request = request_value([
        dict(id='title', text='睡眠时长', semantic='title', required=False),
        dict(id='duration', text='7小时10分', kind='duration', entity='sleep'),
    ], size='2x2', title='睡眠时长')
    _, _, candidates = compile_plan(request, [selected('reading', ['duration'])])
    assert [item.component for item in candidates[0].items] == ['SingleLineTitle', 'EmphasisText']
    assert candidates[0].items[1].fact_refs == ['duration']


@pytest.mark.parametrize('references', [['name', 'value'], ['value', 'name']])
def test_labelled_readout_is_one_primary_reading_and_one_secondary_identity(references):
    request = request_value([
        dict(id='name', text='指标名称', semantic='label', entity='device'),
        numeric_fact(),
    ])
    _, _, candidates = compile_plan(request, [selected('reading', references)])
    items = candidates[0].items
    assert [ref for item in items for ref in item.fact_refs] == references
    by_fact = {item.fact_refs[0]: item for item in items}
    assert by_fact['value'].component == 'EmphasizedData'
    assert by_fact['value'].role == 'primary'
    assert by_fact['name'].component == 'SecondaryBody'
    assert by_fact['name'].role == 'secondary'
    assert {item.group for item in items} == {'device'}


def test_labelled_readout_string_binding_stays_complete_and_uses_text_recipe():
    request = request_value([
        dict(id='name', text='睡眠状态', semantic='label', entity='device'),
        dict(id='value', text='完整状态', entity='device'),
    ])
    request.card_spec = dict(dataBindings=[dict(writeResultTo='/data')])
    request.facts[1].path = '/data/state'
    request = CardRequest.model_validate(request.model_dump())
    _, _, candidates = compile_plan(request, [selected('reading', ['name', 'value'])])
    assert [item.component for item in candidates[0].items] == ['SecondaryBody', 'EmphasisText']
    assert candidates[0].items[1].fact_refs == ['value']


def test_two_equal_small_blocks_are_an_initial_uniform_recipe():
    request = request_value([
        numeric_fact('first', entity='first_device'),
        dict(id='first_name', text='设备甲', semantic='label', entity='first_device'),
        numeric_fact('second', entity='second_device', value=80),
        dict(id='second_name', text='设备乙', semantic='label', entity='second_device'),
    ], size='2x2')
    _, _, candidates = compile_plan(request, [
        selected('first', ['first']),
        selected('first_name', ['first_name'], role='secondary', view='text'),
        selected('second', ['second']),
        selected('second_name', ['second_name'], role='secondary', view='text'),
    ], relations=[dict(from_entity='first_device', to_entity='second_device', kind='peer')])
    assert len(candidates) == 1
    assert [item.component for item in candidates[0].items] == ['InfoBlock', 'InfoBlock']
    assert [item.fact_refs for item in candidates[0].items] == [
        ['first', 'first_name'], ['second', 'second_name']]


@pytest.mark.parametrize('width,height', [(300, 150), (340, 180)])
def test_owned_peer_actions_reach_equal_native_regions(width, height, oracle):
    request, _ = peer_card(width, height)
    selections, actions = [], []
    for entity in ('weather', 'battery'):
        selections.extend([
            selected(entity + '_heading', [entity + '_name'], role='secondary', view='text'),
            selected(entity + '_core', [entity + '_value']),
            selected(entity + '_support', [entity + '_state'], role='secondary', view='details'),
        ])
        actions.append(dict(ref=entity + '_action', owner=entity))
    request_before = request.model_dump()
    resolved, plan, candidates = compile_plan(request, selections, actions=actions,
        relations=[dict(from_entity='weather', to_entity='battery', kind='peer')])
    plan_before = copy.deepcopy(plan.model_dump())
    layout = plan_card_containers(resolved, candidates[0], oracle, width_policy='balanced')
    assert layout['status'] == 'PLANNED'
    panels = [node for node in walk(layout['tree'])
              if node.get('anchor') == 'entity_action_footer']
    assert len(panels) == 2
    row = next(node for node in walk(layout['tree']) if node.get('children') == panels)
    assert row['equal'] is True
    for panel, entity in zip(panels, ('weather', 'battery'), strict=True):
        assert panel['children'][-1]['block']['item']['action_ref'] == entity + '_action'
        assert {leaf['block']['item']['group'] for leaf in leaves(panel)} == {entity}
    nodes = container_nodes(resolved, layout)
    numbers = [node for node in nodes if node['id'] in {
        'gd_semantic_1_0_text_0', 'gd_semantic_4_0_text_0'}]
    assert len(numbers) == 2
    assert {node['styles']['fontSize'] for node in numbers} == {30}
    assert request.model_dump() == request_before
    assert plan.model_dump() == plan_before


def test_focus_does_not_merge_independent_clock_into_a_device():
    request = request_value([
        dict(id='title', text='数量与日期', semantic='title', required=False),
        numeric_fact(unit='', value=3),
        dict(id='date', text='2026-11-20', kind='date', entity='clock'),
    ], size='2x2', title='数量与日期')
    _, _, candidates = compile_plan(request, [selected('reading', ['value']),
        selected('date', ['date'], role='secondary', view='text')])
    assert [item.component for item in candidates[0].items] == [
        'SingleLineTitle', 'EmphasizedData', 'SecondaryBody']
    assert [item.group for item in candidates[0].items[1:]] == ['device', 'clock']


def test_shared_action_stays_separate_and_handler_is_not_modified():
    request = request_value([numeric_fact()], actions=[
        dict(id='open', label='打开', event=dict(call='open', args=dict(target='original'))),
    ])
    resolved, _, candidates = compile_plan(request, [selected('reading', ['value'])],
        actions=[dict(ref='open', owner=None, scope='global')])
    button = candidates[0].items[-1]
    assert button.action_ref == 'open'
    assert button.group == 'actions'
    assert button.component == 'PillButton'
    assert resolved.actions[0].event == request.actions[0].event
    assert resolved.actions[0].entity is None


def test_two_actions_without_content_choose_card_buttons_and_keep_optional_header():
    request = request_value([
        dict(id='title', text='快捷操作', semantic='title', required=False),
    ], size='2x2', title='快捷操作', actions=[
        dict(id='first', label='动作甲', event=dict(call='first')),
        dict(id='second', label='动作乙', event=dict(call='second')),
    ])
    _, _, candidates = compile_plan(request, [], actions=[dict(ref='first'), dict(ref='second')])
    assert [item.component for item in candidates[0].items] == ['CardButton', 'CardButton']


def calendar_request():
    facts, actions = [], []
    for index in range(2):
        entity = f'event{index}'
        facts.extend([
            dict(id=entity + '_title', text='项目例会', entity=entity,
                 path=f'/data/calendar/events/{index}/title'),
            dict(id=entity + '_time', text='14:00', kind='time', entity=entity,
                 path=f'/data/calendar/events/{index}/dtStart'),
        ])
        actions.append(dict(id=entity + '_open', label='查看详情', entity=entity,
                            event=dict(call='eventDetail', args=dict(index=index))))
    return CardRequest(
        case_id='semantic-calendar', query='显示两条日程，点击日程查看详情', size='2x4',
        component_contract='upstream-card-v1', surface=dict(width_vp=300, height_vp=150),
        facts=facts, actions=actions,
        card_spec=dict(dataBindings=[dict(capabilityId='GetCalendarEvents',
                                          writeResultTo='/data/calendar')]),
    )


def test_timeline_is_event_cards_and_record_clicks_do_not_create_extra_buttons():
    request = calendar_request()
    actions = [dict(ref=action.id, owner=action.entity, scope='record')
               for action in request.actions]
    resolved, _, candidates = compile_plan(request, [selected('events',
        [fact.id for fact in request.facts], view='timeline')], actions=actions,
        relations=[dict(from_entity='event0', to_entity='event1', kind='ordered')])
    assert [item.component for item in candidates[0].items] == ['EventCard', 'EventCard']
    assert [item.action_ref for item in candidates[0].items] == ['event0_open', 'event1_open']
    assert [item.group for item in candidates[0].items] == ['event0', 'event1']
    assert [action.event for action in resolved.actions] == [
        action.event for action in request.actions]
    validate_intent(resolved, candidates[0])


@pytest.mark.parametrize('separate_fields', [False, True])
@pytest.mark.parametrize('typed_time', [False, True])
def test_record_action_compiles_details_to_event_without_model_component_choice(
        separate_fields, typed_time):
    request = calendar_request()
    if not typed_time:
        for fact in request.facts:
            fact.kind = 'text'
    selections = []
    for index in range(2):
        entity = f'event{index}'
        if separate_fields:
            selections.extend([
                selected(entity + '_name', [entity + '_title'], view='text'),
                selected(entity + '_when', [entity + '_time'], view='text', role='secondary'),
            ])
        else:
            selections.append(selected(entity, [entity + '_title', entity + '_time'],
                                       view='details'))
    before = request.model_dump()
    resolved, plan, candidates = compile_plan(request, selections, actions=[
        dict(ref=action.id, owner=action.entity, scope='record') for action in request.actions])
    assert [item.component for item in candidates[0].items] == ['EventCard', 'EventCard']
    assert [item.fact_refs for item in candidates[0].items] == [
        ['event0_title', 'event0_time'], ['event1_title', 'event1_time']]
    assert [item.action_ref for item in candidates[0].items] == ['event0_open', 'event1_open']
    assert [selection.view for selection in plan.selections] == [
        selection['view'] for selection in selections]
    assert request.model_dump() == before
    assert [action.event for action in resolved.actions] == [
        action.event for action in request.actions]


def test_record_click_keeps_an_important_readout_inside_its_complete_event():
    request = calendar_request()
    request.facts.append(request.facts[0].model_copy(update={
        'id': 'number', 'text': '30', 'path': None, 'kind': 'quantity', 'value': 30.0,
    }))
    resolved, plan, candidates = compile_plan(request, [
        selected('events', [fact.id for fact in request.facts if fact.id != 'number'],
                 view='timeline'), selected('readout', ['number']),
    ], actions=[dict(ref=action.id, owner=action.entity, scope='record')
                for action in request.actions])
    assert [item.component for item in candidates[0].items] == ['EventCard', 'EventCard']
    assert candidates[0].items[0].fact_refs == ['event0_title', 'event0_time', 'number']
    assert candidates[0].items[0].role == 'primary'
    assert candidates[0].items[0].action_ref == 'event0_open'
    assert plan.selections[1].role == 'primary'
    assert [action.event for action in resolved.actions] == [
        action.event for action in request.actions]


def test_record_projection_precedes_compound_readout_component_selection():
    request = calendar_request()
    request.facts.append(request.facts[0].model_copy(update={
        'id': 'countdown', 'text': '30天', 'path': '/data/calendar/events/0/countdownDays',
        'kind': 'quantity', 'value': 30.0, 'unit': '天',
    }))
    readout = selected('readout', ['event0_time', 'countdown'])
    readout['focus_ref'] = 'countdown'
    _, plan, candidates = compile_plan(request, [
        selected('name', ['event0_title'], view='text'), readout,
        selected('other_event', ['event1_title', 'event1_time'], view='details'),
    ], actions=[dict(ref=action.id, owner=action.entity, scope='record')
                for action in request.actions])
    assert [item.component for item in candidates[0].items] == ['EventCard', 'EventCard']
    assert candidates[0].items[0].fact_refs == ['event0_title', 'event0_time', 'countdown']
    assert plan.selections[1].focus_ref == 'countdown'
    assert [ref for item in candidates[0].items for ref in item.fact_refs].count('countdown') == 1


@pytest.mark.parametrize('record_action', [True, False])
def test_record_title_focus_requires_verified_record_action(record_action):
    request = calendar_request()
    request.facts.extend([
        request.facts[0].model_copy(update={
            'id': 'date', 'text': '2026-11-20', 'path': '/data/calendar/events/0/startDate',
        }),
        request.facts[0].model_copy(update={
            'id': 'countdown', 'text': '0', 'path': '/data/calendar/events/0/countdownDays',
        }),
    ])
    request.data_model = dict(data=dict(calendar=dict(events=[dict(countdownDays=0)])))
    record = selected('record', ['event0_title', 'date', 'event0_time', 'countdown'])
    record['focus_ref'] = 'event0_title'
    selections = [record, selected('other', ['event1_title', 'event1_time'], view='details')]
    if not record_action:
        request.actions = []
        with pytest.raises(ValueError, match='SEMANTIC_(FOCUS|READOUT)'):
            compile_plan(request, selections)
        return
    before = request.model_dump()
    _, plan, candidates = compile_plan(request, selections, actions=[
        dict(ref=action.id, owner=action.entity, scope='record') for action in request.actions])
    assert [item.component for item in candidates[0].items] == ['EventCard', 'EventCard']
    assert candidates[0].items[0].fact_refs == ['event0_title', 'date', 'event0_time', 'countdown']
    assert candidates[0].items[0].action_ref == 'event0_open'
    assert plan.selections[0].focus_ref == 'event0_title'
    assert request.model_dump() == before


def test_record_selection_acceptance_cannot_bypass_calendar_component_title_contract():
    request = calendar_request()
    request.facts = [fact for fact in request.facts if fact.id != 'event0_title']
    time = next(fact for fact in request.facts if fact.id == 'event0_time')
    request.facts.append(time.model_copy(update={
        'id': 'location', 'path': '/data/calendar/events/0/eventLocation',
        'kind': 'text', 'text': '会议室',
    }))
    record = selected('record', ['event0_time', 'location'])
    record['focus_ref'] = 'location'
    value = dict(selections=[record,
        selected('other', ['event1_title', 'event1_time'], view='details')],
        actions=[dict(ref=action.id, owner=action.entity, scope='record')
                 for action in request.actions])
    resolved, plan = decode_selection(json.dumps(value, ensure_ascii=False), request)
    assert plan.actions[0].scope == 'record'
    with pytest.raises(ValueError, match='真实事件名称'):
        component_candidates(resolved, plan)


def test_record_click_does_not_swallow_an_explicit_progress_view():
    request = calendar_request()
    request.facts.extend([
        request.facts[0].model_copy(update={
            'id': 'percent', 'text': '68%', 'path': None, 'kind': 'quantity',
            'value': 68.0, 'unit': '%',
        }),
        request.facts[0].model_copy(update={
            'id': 'label', 'text': '完成进度', 'path': None, 'semantic': 'label',
        }),
    ])
    with pytest.raises(ValueError, match='SEMANTIC_RECORD_VISUAL'):
        compile_plan(request, [
            selected('events', ['event0_title', 'event0_time', 'event1_title', 'event1_time'],
                     view='timeline'),
            selected('readout', ['percent'], view='progress'),
            selected('label', ['label'], role='secondary', view='text'),
        ], actions=[dict(ref=action.id, owner=action.entity, scope='record')
                    for action in request.actions])


def test_multiple_record_clicks_are_explicitly_unsupported():
    request = calendar_request()
    request.actions[1].entity = 'event0'
    actions = [dict(ref=action.id, owner=action.entity, scope='record')
               for action in request.actions]
    with pytest.raises(ValueError, match='SEMANTIC_RECORD_ACTION'):
        compile_plan(request, [selected('events', [fact.id for fact in request.facts],
                                       view='timeline')], actions=actions)


def test_selected_progress_label_and_value_keep_complete_ring_semantics():
    request = request_value([
        dict(id='name', text='今日目标', semantic='label', entity='step'),
        numeric_fact('percent', entity='step'),
    ])
    _, _, candidates = compile_plan(request, [
        selected('progress', ['percent'], view='progress'),
        selected('label', ['name'], role='secondary', view='text'),
    ])
    assert len(candidates[0].items) == 1
    assert candidates[0].items[0].component == 'ProgressCircleSingle'
    assert candidates[0].items[0].fact_refs == ['name', 'percent']


def test_missing_progress_label_fails_instead_of_inventing_one():
    request = request_value([numeric_fact()])
    with pytest.raises(ValueError, match='SEMANTIC_PROGRESS_LABEL'):
        compile_plan(request, [selected('progress', ['value'], view='progress')])


def test_complete_name_value_records_use_table_without_first_record_detail_bias():
    facts = []
    for index in range(3):
        entity = f'application{index}'
        facts.extend([
            dict(id=entity + '_name', text='应用' + str(index), semantic='label', entity=entity),
            dict(id=entity + '_duration', text='4小时41分', kind='duration', entity=entity),
        ])
    request = request_value(facts)
    _, _, candidates = compile_plan(request, [selected('applications',
        [fact.id for fact in request.facts], view='list')])
    assert [item.component for item in candidates[0].items] == ['TableText']
    assert candidates[0].items[0].fact_refs == [fact.id for fact in request.facts]


def test_many_same_entity_items_have_bounded_same_font_summary_candidates():
    request = request_value([dict(id=f'f{index}', text='完整项目' + str(index), entity='items')
                             for index in range(12)])
    _, _, candidates = compile_plan(request, [selected('records',
        [fact.id for fact in request.facts], view='list')])
    assert 1 < len(candidates) <= MAX_CANDIDATES
    for intent in candidates:
        assert {item.component for item in intent.items} == {'SummaryList'}
        assert [ref for item in intent.items for ref in item.fact_refs] == [
            fact.id for fact in request.facts]
        assert {item.role for item in intent.items} == {'primary'}


@pytest.mark.parametrize('kind', ['ordered', 'primary_support'])
def test_explicit_relation_orders_entities_without_changing_fact_roles(kind):
    second_role = 'secondary' if kind == 'primary_support' else 'primary'
    request = request_value([
        numeric_fact('first', entity='a'), numeric_fact('second', entity='b'),
    ])
    _, _, candidates = compile_plan(request, [
        selected('second', ['second'], role=second_role), selected('first', ['first']),
    ], relations=[dict(from_entity='a', to_entity='b', kind=kind)])
    assert [item.group for item in candidates[0].items] == ['a', 'b']
    assert [item.role for item in candidates[0].items] == ['primary', second_role]


@pytest.mark.parametrize('relations,message', [
    ([dict(from_entity='a', to_entity='b', kind='ordered'),
      dict(from_entity='b', to_entity='a', kind='ordered')], 'SEMANTIC_RELATION_CYCLE'),
    ([dict(from_entity='a', to_entity='b', kind='primary_support')],
     'SEMANTIC_PRIMARY_SUPPORT_ROLE'),
])
def test_conflicting_relations_do_not_silently_fall_back(relations, message):
    request = request_value([
        numeric_fact('first', entity='a'), numeric_fact('second', entity='b'),
    ])
    with pytest.raises(ValueError, match=message):
        compile_plan(request, [selected('first', ['first']), selected('second', ['second'])],
                     relations=relations)


def test_peer_readout_contract_never_lowers_numeric_font_to_match_duration():
    request = request_value([
        numeric_fact('first', entity='a'),
        dict(id='second', text='7小时10分', kind='duration', entity='b'),
    ])
    with pytest.raises(ValueError, match='SEMANTIC_PEER_LEVEL'):
        compile_plan(request, [selected('first', ['first']), selected('second', ['second'])],
            relations=[dict(from_entity='a', to_entity='b', kind='peer')])


def test_secondary_fields_are_not_dropped_when_component_arity_splits():
    request = request_value([numeric_fact(), *[
        dict(id=f's{index}', text='辅助字段' + str(index), entity='device')
        for index in range(8)]])
    selections = [selected('reading', ['value']), selected('support',
        [f's{index}' for index in range(8)], role='secondary', view='details')]
    _, _, candidates = compile_plan(request, selections)
    assert [len(item.fact_refs) for item in candidates[0].items] == [1, 6, 2]
    assert [item.component for item in candidates[0].items] == [
        'EmphasizedData', 'SecondaryBody', 'SecondaryBody']


def test_adjacent_same_entity_secondary_selections_share_existing_body_recipe():
    request = request_value([numeric_fact(), *[
        dict(id=f's{index}', text='辅助字段' + str(index), entity='device')
        for index in range(8)]])
    selections = [selected('reading', ['value'])]
    selections.extend(selected(f'support{index}', [f's{index}'], role='secondary', view='text')
                      for index in range(8))
    original = copy.deepcopy(selections)
    _, plan, candidates = compile_plan(request, selections)
    assert [len(item.fact_refs) for item in candidates[0].items] == [1, 6, 2]
    assert [ref for item in candidates[0].items for ref in item.fact_refs] == [
        fact.id for fact in request.facts]
    assert [selection.fact_refs for selection in plan.selections] == [
        selection['fact_refs'] for selection in original]
    assert selections == original


@pytest.mark.parametrize('boundary', ['primary', 'identity', 'other_entity'])
def test_body_coalescing_does_not_cross_content_identity_or_entity_boundaries(boundary):
    facts = [numeric_fact(), dict(id='before', text='前一辅助', entity='device'),
             dict(id='after', text='后一辅助', entity='device')]
    if boundary == 'primary':
        facts.append(numeric_fact('middle'))
        middle = selected('middle', ['middle'])
    elif boundary == 'identity':
        facts.append(dict(id='middle', text='身份名称', entity='device', semantic='label'))
        middle = selected('middle', ['middle'], role='secondary', view='text')
    else:
        facts.append(dict(id='middle', text='其他设备', entity='other'))
        middle = selected('middle', ['middle'], role='secondary', view='text')
    request = request_value(facts)
    _, _, candidates = compile_plan(request, [
        selected('reading', ['value']),
        selected('before', ['before'], role='secondary', view='text'), middle,
        selected('after', ['after'], role='secondary', view='text'),
    ])
    references = [item.fact_refs for item in candidates[0].items]
    if boundary == 'primary':
        assert references == [['value', 'before'], ['middle', 'after']]
        assert {item.role for item in candidates[0].items} == {'primary'}
        return
    assert ['before'] in references
    assert ['after'] in references
    assert ['middle'] in references


@pytest.mark.parametrize('count', [2, 3])
def test_same_entity_peer_readouts_choose_registered_table_before_measurement(count):
    facts, selections = [], []
    for index in range(count):
        identity = f'item{index}'
        facts.extend([
            dict(id=identity + '_name', text='指标' + str(index),
                 semantic='label', entity='record'),
            numeric_fact(identity + '_value', entity='record', value=80 + index),
        ])
        selections.append(selected(identity, [identity + '_name', identity + '_value']))
    request = request_value(facts)
    before = request.model_dump()
    _, _, candidates = compile_plan(request, selections)
    assert len(candidates) == 1
    assert len(candidates[0].items) == 1
    table = candidates[0].items[0]
    assert table.component == 'TableText'
    assert table.role == 'primary'
    assert table.fact_refs == [fact.id for fact in request.facts]
    assert request.model_dump() == before


def test_multiple_primary_readout_groups_use_business_slots_without_changing_roles():
    request = request_value([
        numeric_fact('score', entity='record', unit=''),
        dict(id='state', text='状态良好', entity='record'),
        dict(id='duration_name', text='完整时长', entity='record', semantic='label'),
        dict(id='duration', text='7小时1分', kind='duration', entity='record'),
    ], size='2x2')
    _, _, candidates = compile_plan(request, [
        selected('score', ['score']),
        selected('state', ['state'], role='secondary', view='text'),
        selected('duration', ['duration_name', 'duration']),
    ])
    assert [item.component for item in candidates[0].items] == ['InfoBlock', 'InfoBlock']
    assert [item.role for item in candidates[0].items] == ['primary', 'primary']
    assert [item.fact_refs for item in candidates[0].items] == [
        ['score', 'state'], ['duration', 'duration_name']]


@pytest.mark.parametrize('width,height', [(150, 150), (240, 300)])
def test_closed_peer_readout_family_is_decided_before_canvas_capacity(width, height):
    request = request_value([
        numeric_fact('score', entity='record', unit=''),
        dict(id='state', text='状态良好', entity='record'),
        dict(id='duration_name', text='完整时长', entity='record', semantic='label'),
        dict(id='duration', text='7小时1分', kind='duration', entity='record'),
    ], size='2x2')
    request.surface.width_vp = width
    request.surface.height_vp = height
    before = request.model_dump()
    _, _, candidates = compile_plan(request, [
        selected('score', ['score']),
        selected('state', ['state'], role='secondary', view='text'),
        selected('duration', ['duration_name', 'duration']),
    ])
    assert len(candidates) == 1
    assert [item.component for item in candidates[0].items] == ['InfoBlock', 'InfoBlock']
    assert [item.fact_refs for item in candidates[0].items] == [
        ['score', 'state'], ['duration', 'duration_name']]
    assert request.model_dump() == before


def test_one_unclosed_peer_does_not_trigger_uniform_infoblock_projection():
    request = request_value([
        numeric_fact('score', entity='record', unit=''),
        dict(id='duration_name', text='完整时长', entity='record', semantic='label'),
        dict(id='duration', text='7小时1分', kind='duration', entity='record'),
    ], size='2x2')
    _, _, candidates = compile_plan(request, [selected('score', ['score']),
        selected('duration', ['duration_name', 'duration'])])
    assert [item.component for item in candidates[0].items] == ['EmphasizedData', 'EmphasisText']
    assert [item.fact_refs for item in candidates[0].items] == [
        ['score'], ['duration', 'duration_name']]


def summary_detail_card(*, kind='quantity', details=True, adjacent=True, contrast=False):
    core = numeric_fact('reading', entity='object', unit='')
    core['kind'] = kind
    if kind != 'quantity':
        core['value'] = None
        core['text'] = '7小时1分' if kind == 'duration' else '2026-11-20'
    facts = [core, dict(id='summary', text='状态良好', entity='object', presentation='summary')]
    selections = [selected('reading', ['reading'])]
    if details:
        facts.append(dict(id='detail', text='完整详情', entity='object', presentation='detail'))
    support = selected('summary', ['summary'], role='secondary', view='text')
    detail = selected('detail', ['detail'], role='secondary', view='details')
    if details and not adjacent:
        selections.extend([detail, support])
    else:
        selections.append(support)
        if details:
            selections.append(detail)
    if contrast:
        facts.append(numeric_fact('contrast', entity='object'))
        selections.append(selected('contrast', ['contrast'], role='secondary'))
    return request_value(facts, size='2x2'), selections


@pytest.mark.parametrize('value', [0, 82, 1000])
def test_numeric_primary_with_summary_and_details_uses_initial_two_slot_info(value):
    request, selections = summary_detail_card()
    request.facts[0].value = float(value)
    request.facts[0].text = str(value)
    before = request.model_dump()
    _, plan, candidates = compile_plan(request, selections)
    assert len(candidates) == 1
    assert [item.component for item in candidates[0].items] == ['InfoBlock', 'SecondaryBody']
    assert candidates[0].items[0].fact_refs == ['reading', 'summary']
    assert candidates[0].items[0].role == 'primary'
    assert candidates[0].items[1].fact_refs == ['detail']
    assert candidates[0].items[1].role == 'secondary'
    assert plan.selections[1].role == 'secondary'
    assert request.model_dump() == before


@pytest.mark.parametrize('kind,details,adjacent,contrast', [
    ('quantity', False, True, False),
    ('quantity', True, False, False),
    ('quantity', True, True, True),
    ('duration', True, True, False),
    ('date', True, True, False),
])
def test_single_summary_recipe_does_not_rewrite_bodyless_dates_or_independent_readouts(
        kind, details, adjacent, contrast):
    request, selections = summary_detail_card(kind=kind, details=details,
        adjacent=adjacent, contrast=contrast)
    _, _, candidates = compile_plan(request, selections)
    assert not any(item.component == 'InfoBlock' for item in candidates[0].items)
    primary = next(item for item in candidates[0].items if item.role == 'primary')
    assert primary.component == ('EmphasizedData' if kind == 'quantity' else 'EmphasisText')
    assert primary.fact_refs == ['reading']


def test_summary_recipe_does_not_consume_detail_from_another_entity():
    request, selections = summary_detail_card()
    request.facts[-1].entity = 'another'
    _, _, candidates = compile_plan(request, selections)
    assert not any(item.component == 'InfoBlock' for item in candidates[0].items)
    primary = next(item for item in candidates[0].items if item.role == 'primary')
    assert primary.component == 'EmphasizedData'


def test_compound_readout_peers_use_a_common_registered_family_and_preserve_all_refs():
    request = request_value([
        dict(id='first_name', text='第一对象', semantic='label', entity='first'),
        numeric_fact('first_reading', entity='first', unit='℃'),
        dict(id='first_state', text='正常状态', entity='first'),
        dict(id='second_name', text='第二对象', semantic='label', entity='second'),
        numeric_fact('second_reading', entity='second'),
    ])
    _, plan, candidates = compile_plan(request, [
        selected('first', ['first_name', 'first_reading', 'first_state']),
        selected('second', ['second_name', 'second_reading']),
    ], relations=[dict(from_entity='first', to_entity='second', kind='peer')])
    primary = [item for item in candidates[0].items if item.role == 'primary']
    assert [item.component for item in primary] == ['EmphasisText', 'EmphasisText']
    assert [item.fact_refs for item in primary] == [
        ['first_reading', 'first_state'], ['second_reading', 'second_name']]
    assert sorted(ref for item in candidates[0].items for ref in item.fact_refs) == sorted(
        fact.id for fact in request.facts)
    assert plan.selections[0].fact_refs == ['first_name', 'first_reading', 'first_state']


def test_explicit_focus_owns_numeric_support_without_losing_value_unit_or_bindings():
    request = request_value([
        dict(id='name', text='对象名称', semantic='label', entity='record'),
        numeric_fact('core', entity='record', value=29, unit='℃'),
        numeric_fact('support', entity='record', value=31, unit='℃'),
    ])
    choice = selected('reading', ['name', 'core', 'support'])
    choice['focus_ref'] = 'core'
    resolved, plan, candidates = compile_plan(request, [choice])
    primary = next(item for item in candidates[0].items if item.role == 'primary')
    assert primary.component == 'EmphasisText'
    assert primary.fact_refs == ['core', 'support']
    assert plan.selections[0].focus_ref == 'core'
    assert [fact.model_dump() for fact in resolved.facts] == [
        fact.model_dump() for fact in request.facts]


@pytest.mark.parametrize('entity', [None, 'device'])
def test_two_reference_readout_without_label_keeps_state_in_supporting_slot(entity):
    request = request_value([
        numeric_fact('core', entity=entity),
        dict(id='state', text='完整状态', entity=entity),
    ])
    before = request.model_dump()
    _, plan, candidates = compile_plan(request, [selected('reading', ['core', 'state'])])
    assert len(candidates[0].items) == 1
    item = candidates[0].items[0]
    assert item.component == 'EmphasisText'
    assert item.role == 'primary'
    assert item.fact_refs == ['core', 'state']
    assert plan.selections[0].focus_ref == 'core'
    assert request.model_dump() == before


@pytest.mark.parametrize('references', [['core', 'support'], ['support', 'core']])
def test_two_numeric_refs_respect_explicit_focus_instead_of_becoming_two_primaries(references):
    request = request_value([
        numeric_fact('core', value=29, unit='℃'),
        numeric_fact('support', value=31, unit='℃'),
    ])
    choice = selected('reading', references)
    choice['focus_ref'] = 'core'
    _, plan, candidates = compile_plan(request, [choice])
    assert len(candidates[0].items) == 1
    assert candidates[0].items[0].component == 'EmphasisText'
    assert candidates[0].items[0].fact_refs == ['core', 'support']
    assert candidates[0].items[0].role == 'primary'
    assert plan.selections[0].fact_refs == references
    assert plan.selections[0].focus_ref == 'core'


def test_two_reference_compound_participates_in_common_peer_font_family():
    request = request_value([
        numeric_fact('first', entity='first'),
        dict(id='state', text='完整状态', entity='first'),
        numeric_fact('second', entity='second'),
        dict(id='name', text='第二对象', semantic='label', entity='second'),
    ])
    _, _, candidates = compile_plan(request, [
        selected('first', ['first', 'state']), selected('second', ['name', 'second']),
    ], relations=[dict(from_entity='first', to_entity='second', kind='peer')])
    assert [item.component for item in candidates[0].items] == ['EmphasisText', 'EmphasisText']
    assert [item.fact_refs for item in candidates[0].items] == [
        ['first', 'state'], ['second', 'name']]


def test_primary_and_secondary_readouts_are_not_flattened_into_a_peer_table():
    request = request_value([
        dict(id='first_name', text='主要指标', semantic='label', entity='record'),
        numeric_fact('first', entity='record'),
        dict(id='second_name', text='辅助指标', semantic='label', entity='record'),
        numeric_fact('second', entity='record'),
    ])
    _, _, candidates = compile_plan(request, [
        selected('first', ['first_name', 'first']),
        selected('second', ['second_name', 'second'], role='secondary'),
    ])
    assert not any(item.component == 'TableText' for item in candidates[0].items)
    primary = next(item for item in candidates[0].items if item.role == 'primary')
    assert primary.component == 'EmphasizedData'
    assert primary.fact_refs == ['first']
    secondary = next(item for item in candidates[0].items if 'second' in item.fact_refs)
    assert secondary.role == 'secondary'


def test_complete_named_peer_values_can_choose_summary_without_creating_names():
    facts = []
    for index in range(3):
        prefix = '指标' + str(index) + ' '
        facts.append(dict(id=f'f{index}', text=prefix + '82', prefix=prefix,
                          value=82.0, entity='record'))
    request = request_value(facts)
    _, _, candidates = compile_plan(request, [selected(f's{index}', [f'f{index}'])
                                             for index in range(3)])
    assert len(candidates[0].items) == 1
    assert candidates[0].items[0].component == 'SummaryList'
    assert candidates[0].items[0].fact_refs == ['f0', 'f1', 'f2']


def test_real_capacity_failure_preserves_complete_intent_and_never_shrinks_main():
    request = request_value([numeric_fact(),
        dict(id='long', text='完整辅助信息不可随意删除' * 20, entity='device')],
        size='2x2', height=70)
    resolved, _, candidates = compile_plan(request, [
        selected('reading', ['value']),
        selected('support', ['long'], role='secondary', view='text'),
    ])
    assert candidates[0].items[0].component == 'EmphasizedData'
    before = candidates[0].model_dump()
    layout = plan_card_containers(resolved, candidates[0], FixedGlyphMeasure())
    assert layout['status'] == 'BOUNDED_REJECTED'
    assert candidates[0].model_dump() == before
    assert [ref for item in candidates[0].items for ref in item.fact_refs] == ['value', 'long']
