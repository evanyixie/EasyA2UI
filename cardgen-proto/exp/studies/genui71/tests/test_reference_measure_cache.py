"""一次只读试排复用完全相同的文字查询，不吞掉缺测或通信异常。"""

import pytest

from genui_device.measure import CachedMeasure, CapacityError, TextMetrics


class CountingOracle:
    kind = 'pillow_reference_not_native'

    def __init__(self, error=None):
        self.calls = 0
        self.error = error

    def text(self, value, width, font_size, *, max_lines, bold=False, line_height=1.35):
        self.calls += 1
        if self.error:
            raise self.error
        return TextMetrics(18, 1, font_size, line_height)


def test_identical_queries_reuse_immutable_metrics_and_preserve_kind():
    source = CountingOracle()
    cached = CachedMeasure(source)
    first = cached.text('完整文字', 80, 14, max_lines=2)
    second = cached.text('完整文字', 80, 14, max_lines=2)
    assert first is second
    assert source.calls == 1
    assert cached.kind == source.kind
    assert cached.evidence()['hits'] == 1
    assert cached.evidence()['unique_queries'] == 1


@pytest.mark.parametrize('field,value', [
    ('value', '另一段文字'), ('width', 81), ('font_size', 16),
    ('max_lines', 1), ('bold', True), ('line_height', 1.5),
])
def test_every_measurement_parameter_participates_in_cache_key(field, value):
    source = CountingOracle()
    cached = CachedMeasure(source)
    query = dict(value='完整文字', width=80, font_size=14, max_lines=2,
                 bold=False, line_height=1.35)
    cached.text(**query)
    cached.text(**dict(query, **{field: value}))
    assert source.calls == 2
    assert cached.evidence()['hits'] == 0


def test_capacity_failure_is_reused_without_changing_error():
    source = CountingOracle(CapacityError('完整文字需要 3 行'))
    cached = CachedMeasure(source)
    for _ in range(2):
        with pytest.raises(CapacityError, match='完整文字需要 3 行'):
            cached.text('完整文字', 80, 14, max_lines=2)
    assert source.calls == 1
    assert cached.evidence()['hits'] == 1


@pytest.mark.parametrize('error', [RuntimeError('通信失败'), KeyError('缺测')])
def test_transient_or_missing_measurements_are_not_cached(error):
    source = CountingOracle(error)
    cached = CachedMeasure(source)
    for _ in range(2):
        with pytest.raises(type(error)):
            cached.text('完整文字', 80, 14, max_lines=2)
    assert source.calls == 2
    assert cached.evidence()['unique_queries'] == 0


def test_new_evaluation_does_not_reuse_previous_cache():
    source = CountingOracle()
    for _ in range(2):
        CachedMeasure(source).text('完整文字', 80, 14, max_lines=2)
    assert source.calls == 2
