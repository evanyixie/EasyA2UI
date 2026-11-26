"""商用双业务分区保护显式动作归属，包含共享动作与历史入口对照。"""

import asyncio
import copy
from pathlib import Path

import pytest
from test_entity_capacity import FixedGlyphMeasure

from genui_device.container_layout import leaves, plan_card_containers
from genui_device.contracts import CardRequest, Intent
from genui_device.intent_integrity import peer_action_owners
from genui_device.native_layout import container_nodes
from genui_device.pipeline import generate
from genui_device.semantic_regions import card_document
from genui_device.themes import load_themes


def peer_card(width=300, height=150, *, long_state=False):
    facts = []
    actions = []
    items = []
    for entity, title, value, unit, state in (
        ('weather', '天气', 29, '℃', '多云'),
        ('battery', '电量', 68, '%',
         '设备当前尚未充电并处于正常工作状态' if long_state else '未充电'),
    ):
        facts.extend([
            dict(id=entity + '_name', text=title, semantic='label', entity=entity,
                 presentation='context'),
            dict(id=entity + '_value', text=str(value) + unit, value=value, unit=unit,
                 semantic='metric', kind='quantity', entity=entity),
            dict(id=entity + '_state', text=state, entity=entity),
        ])
        actions.append(dict(id=entity + '_action', label='查看详情', entity=entity,
                            event=dict(call='open', args=dict(target=entity))))
        items.extend([
            dict(id=entity + '_heading', component='SecondaryBody',
                 fact_refs=[entity + '_name'], role='secondary', group=entity),
            dict(id=entity + '_core', component='EmphasizedData',
                 fact_refs=[entity + '_value'], role='primary', group=entity),
            dict(id=entity + '_support', component='SecondaryBody',
                 fact_refs=[entity + '_state'], role='secondary', group=entity),
            dict(id=entity + '_button', component='PillButton', fact_refs=[],
                 role='action', group=entity, action_ref=entity + '_action'),
        ])
    request = CardRequest(case_id='peer-independent-actions', query='查看两个设备并分别操作',
                          size='2x4', surface=dict(width_vp=width, height_vp=height),
                          component_contract='upstream-card-v1', facts=facts, actions=actions,
                          provenance={'component_selection': {'protocol': 'component-rows-v2'}})
    return request, Intent(items=items)


def walk(tree):
    yield tree
    for child in tree.get('children', []):
        yield from walk(child)


@pytest.mark.parametrize('width,height,long_state', [
    (300, 150, False), (360, 180, True), (400, 200, False),
])
def test_independent_actions_stay_in_equal_peer_regions(width, height, long_state):
    request, intent = peer_card(width, height, long_state=long_state)
    before = copy.deepcopy((request.model_dump(), intent.model_dump()))
    result = plan_card_containers(request, intent, FixedGlyphMeasure(), width_policy='balanced')
    assert result['status'] == 'PLANNED'
    panels = [node for node in walk(result['tree'])
              if node.get('anchor') == 'entity_action_footer']
    assert len(panels) == 2
    for panel, entity in zip(panels, ('weather', 'battery'), strict=True):
        assert panel['surface_inset'] == 8
        assert panel['surface_radius'] == 16
        assert panel['children'][-1]['id'] == entity + '_button'
        assert panel['children'][-2]['kind'] == 'Spacer'
        assert panel['children'][-2]['height'] >= 6
        assert {leaf['block']['item']['group'] for leaf in leaves(panel)} == {entity}
    peer_row = next(node for node in walk(result['tree'])
                    if node['kind'] == 'Row' and node.get('children') == panels)
    assert peer_row['equal'] is True
    assert peer_row['gap'] == 12
    assert [item['component'] for item in result['intent']['items']
            if item['action_ref']] == ['PillButton', 'PillButton']
    assert [item['action_ref'] for item in result['intent']['items']
            if item['action_ref']] == ['weather_action', 'battery_action']
    assert (request.model_dump(), intent.model_dump()) == before
    nodes = {node['id']: node for node in container_nodes(request, result)}
    for entity in ('weather', 'battery'):
        assert nodes[entity + '_button']['onClick'] == [
            dict(call='open', args=dict(target=entity))]
        assert nodes[entity + '_button']['styles']['height'] == 36


@pytest.mark.parametrize('metadata', ['entity', 'group'])
def test_only_explicit_unambiguous_ownership_is_used(metadata):
    request, intent = peer_card()
    if metadata == 'entity':
        for item in intent.items:
            if item.role == 'action':
                item.group = 'actions'
    else:
        for action in request.actions:
            action.entity = None
    document, _ = card_document(request, intent)
    assert not any(region.purpose == 'actions' for region in document.regions)
    assert len(peer_action_owners(request, intent)) == 2


def test_peer_widths_remain_equal_when_one_entity_has_more_support_components():
    request, intent = peer_card(height=180)
    request.facts.append(request.facts[2].model_copy(update={
        'id': 'weather_warning', 'text': '空气优'}))
    intent.items.insert(3, intent.items[2].model_copy(update={
        'id': 'weather_extra', 'fact_refs': ['weather_warning']}))
    result = plan_card_containers(request, intent, FixedGlyphMeasure(), width_policy='balanced')
    assert result['status'] == 'PLANNED'
    panels = [node for node in walk(result['tree'])
              if node.get('anchor') == 'entity_action_footer']
    peer_row = next(node for node in walk(result['tree'])
                    if node['kind'] == 'Row' and node.get('children') == panels)
    assert peer_row['equal'] is True
    assert {leaf['block']['width'] for panel in panels for leaf in leaves(panel)} == {116}


@pytest.mark.parametrize('scenario', [
    'shared', 'unassigned', 'conflicting', 'local', 'title', 'same_entity',
])
def test_shared_ambiguous_and_legacy_actions_keep_existing_layout_path(scenario):
    request, intent = peer_card()
    if scenario == 'shared':
        request.actions[0].entity = 'both'
        intent.items[3].group = 'actions'
    elif scenario == 'unassigned':
        for action in request.actions:
            action.entity = None
        for item in intent.items:
            if item.role == 'action':
                item.group = 'actions'
    elif scenario == 'conflicting':
        request.actions[0].entity = 'battery'
    elif scenario == 'local':
        request.component_contract = 'local-card-v1'
    elif scenario == 'title':
        request.facts.append(request.facts[0].model_copy(update={
            'id': 'title', 'text': '概览', 'semantic': 'title', 'entity': None}))
        intent.items.insert(0, intent.items[0].model_copy(update={
            'id': 'title_node', 'component': 'SingleLineTitle', 'fact_refs': ['title'],
            'role': 'title', 'group': 'header'}))
    else:
        for fact in request.facts:
            fact.entity = 'same'
    assert peer_action_owners(request, intent) == {}
    document, _ = card_document(request, intent)
    assert any(region.purpose == 'actions' for region in document.regions)


def test_peer_layout_reports_true_capacity_failure_without_losing_content():
    request, intent = peer_card(height=80)
    result = plan_card_containers(request, intent, FixedGlyphMeasure())
    assert result['status'] == 'BOUNDED_REJECTED'
    assert result['tree'] is None
    assert result['intent'] == intent.model_dump()


def test_complete_reference_generation_preserves_owned_actions(oracle, tmp_path):
    request, intent = peer_card()
    registry = Path(__file__).resolve().parents[1] / 'examples/themes.example.json'
    themes = load_themes(Path('.'), registry)
    result = asyncio.run(generate(request, output=tmp_path / 'generation', intent=intent,
                                  oracle=oracle, themes=themes, fixed_theme='gradient-blue'))
    assert result['result']['status'] == 'GENERATED'
    assert result['result']['model_calls'] == []
    assert result['layout']['intent'] == intent.model_dump()
    panels = [node for node in walk(result['layout']['tree'])
              if node.get('anchor') == 'entity_action_footer']
    outer = next(node for node in walk(result['layout']['tree'])
                 if node.get('children') == panels)
    assert outer['equal'] is True
    inner_rows = [node for node in walk(result['layout']['tree'])
                  if node.get('cross_alignment') == 'bottom']
    assert inner_rows
    assert any(not node['equal'] for node in inner_rows)
    for row in inner_rows:
        assert row['gap'] == 8
        assert [leaf['block']['item']['role'] for leaf in leaves(row)] == [
            'primary', 'secondary']
        support = leaves(row)[-1]['block']
        for part in support['parts']:
            if part['metrics']['lines'] > 1:
                assert part['metrics']['font_size'] == 12
    nodes = {node['id']: node for node in result['nodes']}
    for entity in ('weather', 'battery'):
        assert nodes['gd_' + entity + '_heading_text_0']['styles']['fontSize'] == 12
        assert nodes['gd_' + entity + '_core_text_0']['styles']['fontSize'] == 30
        assert nodes[entity + '_button']['onClick'] == [
            dict(call='open', args=dict(target=entity))]
        assert nodes[entity + '_button']['styles']['height'] == 36
    assert any(node['styles'].get('alignItems') == 'bottom' for node in result['nodes']
               if node['component'] == 'Row')


def test_long_required_state_remains_capacity_failure():
    request, intent = peer_card()
    request.facts[-1].text = '完整必留的设备状态与适用条件' * 20
    before = request.model_dump()
    result = plan_card_containers(request, intent, FixedGlyphMeasure(), width_policy='balanced')
    assert result['status'] == 'BOUNDED_REJECTED'
    assert result['tree'] is None
    assert result['intent'] == intent.model_dump()
    assert request.model_dump() == before


def test_owned_card_buttons_use_the_registered_region_action_recipe():
    request, intent = peer_card()
    for item in intent.items:
        if item.role == 'action':
            item.component = 'CardButton'
    _, normalized = card_document(request, intent)
    assert [item.component for item in normalized.items
            if item.action_ref] == ['PillButton', 'PillButton']
    assert [item.action_ref for item in normalized.items
            if item.action_ref] == ['weather_action', 'battery_action']
