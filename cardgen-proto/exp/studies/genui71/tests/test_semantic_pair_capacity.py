"""相同文字规格的窄可行宽度区间与既有前缀投影，不读取业务样例判布局。"""

import math

import pytest

from genui_device.catalog import measure_block, variants
from genui_device.contracts import CardRequest, Item
from genui_device.emit import build_component_nodes
from genui_device.measure import CapacityError, TextMetrics


class NarrowIntervalMeasure:
    kind = 'test_only'

    def __init__(self):
        self.calls = 0

    def text(self, text, width, font_size, *, max_lines, bold=False, line_height=1.35):
        self.calls += 1
        needed = {'主读数': 69.75, '名称': 52}[text]
        if width < needed:
            raise CapacityError('完整单行宽度不足')
        return TextMetrics(math.ceil(font_size * line_height), 1, font_size, line_height)


def pair_request(*, semantic=True):
    request = CardRequest(case_id='narrow-pair', query='展示完整同对象主辅信息',
        component_contract='upstream-card-v1', size='2x2',
        surface=dict(width_vp=150, height_vp=150),
        facts=[dict(id='value', text='主读数', entity='record'),
               dict(id='label', text='名称', entity='record', semantic='label')])
    if semantic:
        request.provenance['semantic_selection'] = dict(protocol='semantic-selection-v1')
    item = Item(id='pair', component='InfoBlock', fact_refs=['value', 'label'],
                role='primary', group='record')
    return request, item


def test_same_font_pair_finds_narrow_interval_missed_by_fraction_grid():
    request, item = pair_request()
    oracle = NarrowIntervalMeasure()
    block = measure_block(item, request, 126, oracle, variant=1)
    assert block.part_widths[0] >= 69.75 and block.part_widths[1] >= 52
    assert sum(block.part_widths) + block.gap == 126
    assert [part.metrics.font_size for part in block.parts] == [16, 12]
    assert oracle.calls < 80
    assert item.fact_refs == ['value', 'label']


def test_existing_route_keeps_registered_width_candidates():
    request, item = pair_request(semantic=False)
    with pytest.raises(CapacityError):
        measure_block(item, request, 126, NarrowIntervalMeasure(), variant=1)


@pytest.mark.parametrize('width', [126.1, 126.13])
def test_fractional_caller_width_keeps_feasible_pair_within_unchanged_budget(width):
    request, item = pair_request()
    block = measure_block(item, request, width, NarrowIntervalMeasure(), variant=1)
    assert block.width == width
    assert block.part_widths[0] >= 69.75 and block.part_widths[1] >= 52
    assert sum(block.part_widths) + block.gap <= width
    assert [part.metrics.font_size for part in block.parts] == [16, 12]


def test_small_pair_budget_remains_capacity_failure_not_grid_contract_error():
    request, item = pair_request()
    with pytest.raises(CapacityError):
        measure_block(item, request, 4.1, NarrowIntervalMeasure(), variant=1)


def test_insufficient_pair_budget_is_still_rejected_without_shrinking():
    request, item = pair_request()
    oracle = NarrowIntervalMeasure()
    with pytest.raises(CapacityError):
        measure_block(item, request, 125, oracle, variant=1)
    assert oracle.calls < 80


def test_registered_prefix_projection_matches_measurement_and_binding(oracle):
    request = CardRequest(case_id='registered-display', query='同对象主值与辅助结论',
        component_contract='upstream-card-v1', size='2x2',
        surface=dict(width_vp=150, height_vp=150),
        card_spec=dict(dataBindings=[dict(capabilityId='GetHealthAndSportSummary',
                                         writeResultTo='/data/source')]),
        data_model=dict(data=dict(source=dict(sleepScore=82, sleepStatus='良好'))),
        facts=[dict(id='value', text='睡眠评分 82', prefix='睡眠评分 ', value=82,
                    path='/data/source/sleepScore', entity='record'),
               dict(id='support', text='睡眠状态 良好', prefix='睡眠状态 ',
                    path='/data/source/sleepStatus', entity='record')],
        provenance=dict(semantic_selection=dict(protocol='semantic-selection-v1')))
    item = Item(id='pair', component='InfoBlock', fact_refs=['value', 'support'],
                role='primary', group='record')
    original = request.model_dump()
    assert variants(item, request=request) == (0, 1, 2, 3)
    block = measure_block(item, request, 126, oracle, variant=3)
    assert block.compact_presentation and block.flow == 'inline-pair'
    assert [part.metrics.font_size for part in block.parts] == [16, 12]
    nodes = build_component_nodes(request, block)
    fragments = [fragment for node in nodes for fragment in
                 node.get('_text_binding', {}).get('fragments', [])]
    assert [fragment['prefix'] for fragment in fragments] == ['评分 ', '状态 ']
    assert [fragment['path'] for fragment in fragments] == [
        '/data/source/sleepScore', '/data/source/sleepStatus']
    assert request.model_dump() == original
    request.provenance = {}
    assert variants(item, request=request) == (0, 1)
