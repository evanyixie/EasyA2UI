"""首次语义选择后的有界组件试排；共享既有容器与测量，不调用模型。"""

import time

from .artifact_io import put
from .capacity_repair import diagnostics
from .contracts import validate_intent


def explicit_peer_regions(request, document):
    """只有首轮明确的实体平级关系约束区域份额，不按文字长短或数量推断。"""
    semantic = request.provenance.get('semantic_selection', {})
    if semantic.get('protocol') != 'semantic-selection-v1':
        return set()
    peers = {frozenset((relation['from_entity'], relation['to_entity']))
             for relation in semantic.get('plan', {}).get('relations', [])
             if relation['kind'] == 'peer'}
    if not peers:
        return set()
    facts = {fact.id: fact for fact in request.facts}
    components = {component.id: component for component in document.components}
    regions = {}
    for region in document.regions:
        if region.purpose != 'entity':
            continue
        entities = {facts[ref].entity for child in region.children if child in components
                    for ref in components[child].refs if ref in facts and facts[ref].entity}
        if len(entities) == 1:
            regions[region.id] = next(iter(entities))
    return {frozenset((left, right)) for left, first in regions.items()
            for right, second in regions.items() if left != right
            and frozenset((first, second)) in peers}


def plan_components(request, candidates, pool, folder, row):
    """保留每个候选的真实结果；未完成测量不作为容量拒绝继续消耗预算。"""
    attempts = []
    row['program_layout_attempts'] = attempts
    for index, intent in enumerate(candidates):
        validate_intent(request, intent)
        started = time.perf_counter()
        layout = pool.evaluate('container', request, intent)
        put(folder/f'program-candidate-{index}.json', layout)
        attempts.append(dict(index=index, intent=intent.model_dump(),
            status=layout['status'], elapsed_ms=(time.perf_counter()-started)*1000,
            measurement_kind=layout.get('measurement_kind'),
            new_native_queries=layout.get('new_native_queries'),
            allocation_stages=layout.get('allocation_stages'),
            search_incomplete=layout.get('search_incomplete'),
            capacity_diagnostic=diagnostics(request, layout)))
        put(folder/'program-layout-attempts.json', attempts)
        if layout['status'] == 'PLANNED':
            row['program_selected_candidate'] = index
            layout['program_layout_attempts'] = attempts
            return layout
        if layout.get('search_incomplete') or layout['status'] != 'BOUNDED_REJECTED':
            row['layout_status'] = layout['status']
            put(folder/'layout.json', layout)
            raise ValueError('SEMANTIC_PROGRAM_MEASUREMENT_INCOMPLETE: ' + layout['status'])
    row['layout_status'] = 'BOUNDED_REJECTED'
    put(folder/'layout.json', dict(status='BOUNDED_REJECTED',
                                  program_layout_attempts=attempts))
    raise ValueError('SEMANTIC_PROGRAM_NO_PLAN: 已登记候选未容纳，不代表全域无解')
