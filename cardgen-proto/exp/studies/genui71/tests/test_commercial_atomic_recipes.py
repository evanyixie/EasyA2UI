"""商用规格同时约束参考测量与实际 A2UI，历史回放保留原合同。"""

import pytest
from test_entity_capacity import FixedGlyphMeasure

from genui_device.catalog import measure_block, restore_block
from genui_device.container_layout import record
from genui_device.contracts import CardRequest, Item
from genui_device.emit import build_component_nodes


def reading(component, values, *, size="2x2", role="primary", legacy=False):
    request = CardRequest(
        case_id="commercial-reading", query="展示读数", size=size,
        surface={"width_vp": 300 if size == "2x4" else 150, "height_vp": 150},
        component_contract="local-card-v1" if legacy else "upstream-card-v1",
        facts=[{"id": f"f{number}", "text": value, "entity": "reader"}
               for number, value in enumerate(values)],
    )
    item = Item(id="reading", component=component, role=role, group="reader",
                fact_refs=[fact.id for fact in request.facts])
    return request, item


@pytest.mark.parametrize("component,values,fonts,weights,heights", [
    ("EmphasizedData", ["12345"], [30], [700], [30]),
    ("EmphasisText", ["7小时1分", "昨晚"], [18, 12], [700, 400], [18, 16]),
    ("InfoBlock", ["80%", "耳机"], [16, 12], [700, 500], [22, 16]),
    ("DataDisplay", ["倒计时", "12345", "10:30"], [12, 48, 14], [500, 700, 400],
     [18, 60, 20]),
])
def test_measured_and_emitted_text_share_recipe(component, values, fonts, weights, heights):
    request, item = reading(component, values)
    block = measure_block(item, request, 126, FixedGlyphMeasure())
    nodes = build_component_nodes(request, block)
    texts = [node for node in nodes if node["component"] == "Text"]
    assert [part.metrics.font_size for part in block.parts] == fonts
    assert [node["styles"]["fontSize"] for node in texts] == fonts
    assert [node["styles"]["fontWeight"] for node in texts] == weights
    assert [part.metrics.height for part in block.parts] == heights
    assert restore_block(record(block)) == block


@pytest.mark.parametrize("component,values,font", [
    ("EmphasizedData", ["80%"], 30),
    ("EmphasisText", ["7小时1分"], 18),
])
def test_component_role_does_not_reduce_registered_primary_slot(component, values, font):
    request, item = reading(component, values, role="secondary")
    block = measure_block(item, request, 126, FixedGlyphMeasure())
    assert block.parts[0].metrics.font_size == font


def test_wide_info_block_uses_wide_slot_specification():
    request, item = reading("InfoBlock", ["80%", "耳机"], size="2x4")
    block = measure_block(item, request, 132, FixedGlyphMeasure())
    texts = [node for node in build_component_nodes(request, block)
             if node["component"] == "Text"]
    assert [part.metrics.font_size for part in block.parts] == [14, 12]
    assert [part.metrics.height for part in block.parts] == [19, 16]
    assert [node["styles"]["fontWeight"] for node in texts] == [700, 500]


@pytest.mark.parametrize("value", ["12345", "-12.5", "68%", "68％"])
def test_numeric_focus_ignores_optional_semantic_annotation(value):
    request, item = reading("DataDisplay", ["读数", value, "10:30"])
    block = measure_block(item, request, 126, FixedGlyphMeasure())
    assert block.parts[1].metrics.font_size == 48
    assert block.height >= 114
    assert block.gap == 8


def test_short_text_focus_preserves_commercial_size_and_minimum_frame():
    request, item = reading("DataDisplay", ["结论", "甲乙丙丁戊己庚辛壬癸", "10:30"])
    request.facts[1].semantic = "metric"
    block = measure_block(item, request, 80, FixedGlyphMeasure())
    assert block.parts[1].metrics.font_size == 21
    assert block.parts[1].metrics.lines == 2
    assert block.height >= 122
    nodes = build_component_nodes(request, block)
    assert nodes[0]["styles"]["justifyContent"] == "center"
    value = next(node for node in nodes if node["id"] == "gd_reading_text_1")
    area = next(node for node in nodes if node["id"] == "gd_reading_value_area")
    assert value["styles"]["height"] < area["styles"]["height"]
    assert area["styles"]["height"] == 60
    assert area["styles"]["justifyContent"] == "center"
    assert area["children"] == [value["id"]]
    support = next(node for node in nodes if node["id"] == "gd_reading_text_2")
    assert support["styles"]["margin"]["top"] == 16
    request.facts[1].text += "子"
    with pytest.raises(ValueError, match="1至10"):
        measure_block(item, request, 126, FixedGlyphMeasure())


def test_info_block_unit_and_historical_profile_remain_distinct():
    request, item = reading("InfoBlock", ["30天", "剩余天数"])
    request.card_spec["dataBindings"] = [{"writeResultTo": "/data"}]
    request.facts[0].path = "/data/days"
    request.facts[0].value = 30
    request.facts[0].suffix = "天"
    block = measure_block(item, request, 126, FixedGlyphMeasure())
    assert block.parts[0].unit_metrics.font_size == 10
    nodes = build_component_nodes(request, block)
    unit = next(node for node in nodes if node["id"].endswith("_unit"))
    assert unit["styles"]["fontSize"] == 10
    assert unit["styles"]["fontWeight"] == 500
    request, item = reading("InfoBlock", ["30天", "剩余天数"], legacy=True)
    legacy = measure_block(item, request, 126, FixedGlyphMeasure())
    assert all(part.font_weight is None for part in legacy.parts)


def test_plain_commercial_title_uses_single_registered_line():
    request, item = reading("SingleLineTitle", ["天气"])
    block = measure_block(item, request, 126, FixedGlyphMeasure())
    assert block.parts[0].metrics.font_size == 12
    assert block.parts[0].metrics.line_height == 1
    assert block.height == 12


def test_old_frozen_block_without_weight_field_keeps_legacy_text_weights():
    request, item = reading("EmphasisText", ["设备运行", "当前状态"], legacy=True)
    block = measure_block(item, request, 126, FixedGlyphMeasure())
    old_record = record(block)
    for part in old_record["parts"]:
        part.pop("font_weight")
    restored = restore_block(old_record)
    assert restored == block
    nodes = build_component_nodes(request, restored)
    weights = [node["styles"]["fontWeight"] for node in nodes if node["component"] == "Text"]
    assert weights == [700, 400]


@pytest.mark.parametrize("value", ["", "   ", "甲乙丙丁戊己庚辛壬癸子"])
def test_focus_rejects_missing_or_overlong_text(value):
    # Fact自身禁止空字符串；全空白和超长结论由组件合同明确拒绝。
    if not value:
        with pytest.raises(ValueError):
            reading("DataDisplay", ["结论", value, "10:30"])
        return
    request, item = reading("DataDisplay", ["结论", value, "10:30"])
    with pytest.raises(ValueError, match="1至10"):
        measure_block(item, request, 126, FixedGlyphMeasure())


@pytest.mark.parametrize("size,primary_font", [("2x2", 16), ("2x4", 14)])
def test_scaled_info_block_keeps_registered_text_and_unit_relationship(size, primary_font):
    request, item = reading("InfoBlock", ["30天", "剩余天数"], size=size)
    request.surface.font_scale = 1.5
    request.card_spec["dataBindings"] = [{"writeResultTo": "/data"}]
    request.facts[0].path = "/data/days"
    request.facts[0].value = 30
    request.facts[0].suffix = "天"
    block = measure_block(item, request, 180, FixedGlyphMeasure())
    nodes = build_component_nodes(request, block)
    number = next(node for node in nodes if node["id"].endswith("_number"))
    unit = next(node for node in nodes if node["id"].endswith("_unit"))
    assert block.parts[0].metrics.font_size == primary_font * 1.5
    assert block.parts[0].unit_metrics.font_size == 15
    assert unit["styles"]["height"] >= 24
    assert number["styles"]["fontSize"] == primary_font * 1.5
    assert unit["styles"]["fontSize"] == 15
    assert restore_block(record(block)) == block


def structured_temperature():
    request, item = reading("EmphasizedData", ["29℃"], size="2x4")
    request.card_spec["dataBindings"] = [{"writeResultTo": "/data"}]
    request.facts[0].path = "/data/temperature"
    request.facts[0].value = 29
    request.facts[0].suffix = "℃"
    return request, item


def test_split_unit_measurement_matches_live_number_and_unit_nodes():
    from genui_device.bindings import binding_plan, materialize
    from genui_device.data_model import read
    from genui_device.measure import CapacityError

    class RecordingOracle(FixedGlyphMeasure):
        def __init__(self):
            self.queries = []

        def text(self, text, width, font_size, **kwargs):
            self.queries.append((text, width, font_size))
            return super().text(text, width, font_size, **kwargs)

    request, item = structured_temperature()
    oracle = RecordingOracle()
    block = measure_block(item, request, 43, oracle)
    assert ("29℃", 41, 30) not in oracle.queries
    assert any(text == "29" and font == 30 for text, _, font in oracle.queries)
    assert any(text == "℃" and font == 12 for text, _, font in oracle.queries)
    nodes = build_component_nodes(request, block)
    number = next(node for node in nodes if node["id"].endswith("_number"))
    unit = next(node for node in nodes if node["id"].endswith("_unit"))
    assert unit["content"] == "℃"
    plan = binding_plan(nodes)
    changed = materialize({"data": {"temperature": 123}}, plan)
    assert read(changed, number["content"]["path"]) == 123
    with pytest.raises(CapacityError, match="三种宽度分配"):
        measure_block(item, request, 35, oracle)


def test_reference_font_temperature_fits_real_narrow_region(oracle):
    # 300×150宿主中的69vp正文窄区；参考字体结果不冒充真机测量。
    request, item = structured_temperature()
    block = measure_block(item, request, 69, oracle)
    nodes = build_component_nodes(request, block)
    number = next(node for node in nodes if node["id"].endswith("_number"))
    unit = next(node for node in nodes if node["id"].endswith("_unit"))
    assert block.parts[0].metrics.lines == 1
    assert number["styles"]["fontSize"] == 30
    assert unit["styles"]["fontSize"] == 12
    assert request.surface.width_vp == 300
    assert request.surface.height_vp == 150


