"""语义程序路线的候选试排、预算终止与入口隔离。"""

import asyncio
import json

import pytest
from test_entity_capacity import FixedGlyphMeasure
from test_semantic_selection import request_value, selection_value

from genui_device.pipeline import generate
from genui_device.semantic_generation import explicit_peer_regions, plan_components


class Pool:
    def __init__(self, statuses):
        self.statuses = iter(statuses)
        self.calls = []

    def evaluate(self, route, request, intent):
        self.calls.append(intent.model_dump())
        return dict(status=next(self.statuses), intent=intent.model_dump(),
                    measurement_kind='test_only', new_native_queries=0)


def test_program_search_tries_alternative_without_model_or_content_changes(focus, tmp_path):
    request, intent = focus
    pool = Pool(['BOUNDED_REJECTED', 'PLANNED'])
    row = {}
    result = plan_components(request, [intent, intent.model_copy(deep=True)], pool, tmp_path, row)
    assert result['status'] == 'PLANNED'
    assert row['program_selected_candidate'] == 1
    assert len(row['program_layout_attempts']) == 2
    assert all(call['items'][0]['fact_refs'] == ['f0', 'f1'] for call in pool.calls)
    assert json.loads((tmp_path/'program-layout-attempts.json').read_text('utf8')) == (
        row['program_layout_attempts'])


def test_program_search_keeps_all_failure_evidence(focus, tmp_path):
    request, intent = focus
    row = {}
    with pytest.raises(ValueError, match='不代表全域无解'):
        plan_components(request, [intent], Pool(['BOUNDED_REJECTED']), tmp_path, row)
    assert row['layout_status'] == 'BOUNDED_REJECTED'
    assert json.loads((tmp_path/'layout.json').read_text('utf8'))['status'] == 'BOUNDED_REJECTED'
    failure = json.loads((tmp_path/'program-candidate-0.json').read_text('utf8'))
    assert failure['status'] == 'BOUNDED_REJECTED'
    assert row['program_layout_attempts'][0]['capacity_diagnostic']['available_height'] == 126


def test_program_search_stops_on_measurement_budget_instead_of_expanding(focus, tmp_path):
    request, intent = focus
    pool = Pool(['PROBE_BUDGET_EXHAUSTED', 'PLANNED'])
    with pytest.raises(ValueError, match='MEASUREMENT_INCOMPLETE'):
        plan_components(request, [intent, intent], pool, tmp_path, {})
    assert len(pool.calls) == 1


def test_semantic_strategy_refuses_frozen_component_shortcut(focus, tmp_path):
    request, intent = focus
    with pytest.raises(ValueError, match='不能混用冻结组件意图'):
        asyncio.run(generate(request, output=tmp_path/'shortcut', intent=intent,
                             generation_strategy='semantic-program-v1'))
    result = json.loads((tmp_path/'shortcut'/'result.json').read_text('utf8'))
    assert result['status'] == 'FAILED' and result['model_calls'] == []


class SemanticModel:
    config = {'semantic_replan': True}

    def __init__(self):
        self.calls = []

    async def complete(self, messages, phase):
        assert phase == 'semantic_selection'
        self.calls.append(dict(phase=phase, status='test_response'))
        return json.dumps(selection_value())


def example_themes():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    return json.loads((root/'examples/themes.example.json').read_text('utf8'))['themes']


def test_semantic_full_pipeline_uses_one_selection_and_preserves_binding(tmp_path):
    model = SemanticModel()
    request = request_value()
    next(fact for fact in request.facts if fact.id == 'battery').suffix = '%'
    result = asyncio.run(generate(request, output=tmp_path/'new', model=model,
        oracle=FixedGlyphMeasure(), themes=example_themes(), fixed_theme='gradient-blue',
        generation_strategy='semantic-program-v1'))
    assert result['result']['status'] == 'GENERATED'
    assert len(model.calls) == 1 and model.calls[0]['phase'] == 'semantic_selection'
    assert '/data/battery' in result['source']
    assert result['result']['retained_contract']['status'] == 'PASS'
    assert result['intent'].items[0].component == 'SingleLineTitle'
    reading = next(node for node in result['nodes']
                   if node.get('component') == 'Text' and node['styles'].get('fontSize') == 30)
    assert reading['styles']['fontWeight'] == 700
    assert result['result']['generation_strategy'] == 'semantic-program-v1'


def test_semantic_capacity_failure_does_not_enter_original_model_repair(tmp_path):
    model = SemanticModel()
    request = request_value()
    request.surface.height_vp = 49
    with pytest.raises(ValueError, match='SEMANTIC_PROGRAM_NO_PLAN'):
        asyncio.run(generate(request, output=tmp_path/'small', model=model,
            oracle=FixedGlyphMeasure(), themes=example_themes(), fixed_theme='gradient-blue',
            generation_strategy='semantic-program-v1'))
    assert len(model.calls) == 1
    row = json.loads((tmp_path/'small'/'result.json').read_text('utf8'))
    assert row['selection_attempts'][0]['raw_response'] == json.dumps(selection_value())
    assert row['layout_status'] == 'BOUNDED_REJECTED'
    assert not (tmp_path/'small'/'card.a2ui.jsonl').exists()


def test_only_explicit_peer_relation_protects_unequal_content_regions():
    from genui_device.contracts import CardRequest, Intent
    from genui_device.semantic_regions import card_document

    request = CardRequest(case_id='relation-groups', query='两个对象平级展示', size='2x4',
        surface=dict(width_vp=300, height_vp=150), component_contract='upstream-card-v1',
        facts=[dict(id='a', text='26', kind='quantity', entity='first'),
               dict(id='b', text='78', kind='quantity', entity='second'),
               dict(id='c', text='运行正常', entity='second')])
    intent = Intent(items=[
        dict(id='first_main', component='EmphasizedData', fact_refs=['a'],
             role='primary', group='first'),
        dict(id='second_main', component='EmphasizedData', fact_refs=['b'],
             role='primary', group='second'),
        dict(id='second_support', component='SecondaryBody', fact_refs=['c'],
             role='secondary', group='second')])
    document, _ = card_document(request, intent)
    assert explicit_peer_regions(request, document) == set()
    request.provenance['semantic_selection'] = dict(protocol='semantic-selection-v1',
        plan=dict(relations=[dict(from_entity='first', to_entity='second', kind='peer')]))
    pairs = explicit_peer_regions(request, document)
    assert len(pairs) == 1
    entity_ids = {region.id for region in document.regions if region.purpose == 'entity'}
    assert pairs == {frozenset(entity_ids)}


def test_program_compilation_retains_existing_peer_identity_guard(tmp_path):
    from genui_device.contracts import Fact

    request = request_value()
    request.facts.extend([
        Fact(id='first_name', text='甲设备', semantic='label', required=False, entity='phone'),
        Fact(id='second_name', text='乙设备', semantic='label', required=False,
             entity='headphone')])
    next(fact for fact in request.facts if fact.id == 'earphone').unit = '%'
    response = selection_value()
    response['selections'] = [response['selections'][0], dict(
        id='second', fact_refs=['earphone'], role='primary', entity='headphone', view='readout')]
    response['relations'] = [dict(from_entity='phone', to_entity='headphone', kind='peer')]

    class NoNames(SemanticModel):
        async def complete(self, messages, phase):
            self.calls.append(dict(phase=phase, status='test_response'))
            return json.dumps(response)

    model = NoNames()
    with pytest.raises(ValueError, match='UX_READOUT_IDENTITY'):
        asyncio.run(generate(request, output=tmp_path/'missing-identity', model=model,
            oracle=FixedGlyphMeasure(), themes=example_themes(), fixed_theme='gradient-blue',
            generation_strategy='semantic-program-v1'))
    assert len(model.calls) == 1
    row = json.loads((tmp_path/'missing-identity'/'result.json').read_text('utf8'))
    assert row['phase_states']['selection'] == 'complete'
    assert row['phase_states']['program_component_selection'] == 'failed'
