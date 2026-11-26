"""首次语义选择直接消费事实与动作候选，不允许模型提交组件或布局。"""

import asyncio
import copy
import json

import pytest
from test_cardspec_entry import content, entry  # noqa: F401

from genui_device.contracts import CardRequest, InformationGroup
from genui_device.semantic_selection import (
    PROTOCOL,
    SemanticPlan,
    decode_selection,
    readout_value_source,
    record_time_sources,
    select_semantic,
    semantic_messages,
)


def request_value():
    return CardRequest(
        case_id="semantic-candidates", query="显示两个设备的电量和状态", size="2x4",
        surface={"width_vp": 300, "height_vp": 150},
        component_contract="upstream-card-v1", requirement_mode="query_candidates",
        title_fact_id="title", card_spec={
            "title": "设备状态", "suggestSize": "2x4",
            "dataBindings": [{"writeResultTo": "/data"}],
        },
        facts=[
            {"id": "title", "text": "设备状态", "required": False, "semantic": "title"},
            {"id": "battery", "text": "68%", "required": True, "path": "/data/battery",
             "entity": "phone", "kind": "quantity", "value": 68, "unit": "%"},
            {"id": "state", "text": "未充电", "required": False, "entity": "phone"},
            {"id": "earphone", "text": "80%", "required": False,
             "entity": "headphone", "path": "/data/earphone", "kind": "quantity"},
        ],
        actions=[
            {"id": "power", "label": "省电模式", "event": {"call": "Power", "args": {}},
             "required": True, "entity": "phone"},
            {"id": "music", "label": "打开歌单", "event": {"call": "Playlist"},
             "required": False},
        ],
        data_model={"data": {"battery": 68, "earphone": 80}},
    )


def selection_value():
    return {
        "version": PROTOCOL,
        "selections": [
            {"id": "reading", "fact_refs": ["battery"], "role": "primary",
             "entity": "phone", "view": "readout"},
            {"id": "status", "fact_refs": ["state"], "role": "secondary",
             "entity": "phone", "view": "details", "mandatory": False},
        ],
        "actions": [{"ref": "power", "owner": "phone", "required": True}],
        "relations": [],
    }


def decode(value, request=None):
    return decode_selection(json.dumps(value, ensure_ascii=False), request or request_value())


def test_selection_only_projects_chosen_candidates_and_preserves_source_and_handlers():
    request = request_value()
    original = request.model_dump()
    resolved, plan = decode(selection_value(), request)
    assert isinstance(plan, SemanticPlan)
    assert {fact.id for fact in resolved.facts} == {"title", "battery", "state"}
    assert resolved.title_fact_id == "title"
    assert {fact.id for fact in resolved.facts if fact.required} == {"battery"}
    assert resolved.actions[0].event == request.actions[0].event
    assert resolved.actions[0].entity == "phone"
    assert resolved.card_spec == request.card_spec
    assert resolved.data_model == request.data_model
    assert resolved.provenance["semantic_selection"]["unselected_facts"] == ["title", "earphone"]
    assert request.model_dump() == original


@pytest.mark.parametrize("key,value", [
    ("component", "InfoBlock"), ("fontSize", 30), ("color", "red"),
    ("children", []), ("layout", "S-center"),
])
def test_model_cannot_choose_component_or_visual_fields(key, value):
    selected = selection_value()
    selected["selections"][0][key] = value
    with pytest.raises(ValueError, match="Extra inputs"):
        decode(selected)


@pytest.mark.parametrize("kind", ["missing_fact", "optional_fact", "missing_action",
                                 "optional_action", "duplicate_fact", "unknown_fact"])
def test_required_unknown_and_repeated_references_are_rejected(kind):
    value = selection_value()
    if kind == "missing_fact":
        value["selections"] = value["selections"][1:]
    elif kind == "optional_fact":
        value["selections"][0]["mandatory"] = False
    elif kind == "missing_action":
        value["actions"] = []
    elif kind == "optional_action":
        value["actions"][0]["required"] = False
    elif kind == "duplicate_fact":
        value["selections"][1]["fact_refs"] = ["battery"]
    else:
        value["selections"][0]["fact_refs"] = ["unknown"]
    with pytest.raises(ValueError, match="SEMANTIC_"):
        decode(value)


@pytest.mark.parametrize("change", ["entity", "owner", "unknown_owner", "mix"])
def test_fact_and_action_ownership_cannot_be_guessed_or_reassigned(change):
    value = selection_value()
    if change == "entity":
        value["selections"][0]["entity"] = "headphone"
    elif change == "owner":
        value["actions"][0]["owner"] = None
    elif change == "unknown_owner":
        value["actions"][0]["owner"] = "third_device"
    else:
        value["selections"][0].update(view="details", fact_refs=["battery", "earphone"])
    with pytest.raises(ValueError, match="SEMANTIC_"):
        decode(value)


def test_record_list_can_retain_multiple_real_entities_without_merging_them():
    value = selection_value()
    value["selections"] = [{"id": "devices", "fact_refs": ["battery", "earphone"],
                             "role": "primary", "entity": None, "view": "list"}]
    resolved, plan = decode(value)
    assert plan.selections[0].entity is None
    assert {fact.id: fact.entity for fact in resolved.facts if fact.path} == {
        "battery": "phone", "earphone": "headphone",
    }


def test_known_entity_can_be_omitted_without_losing_existing_ownership():
    value = selection_value()
    value["selections"][0].pop("entity")
    _, plan = decode(value)
    assert plan.selections[0].entity == "phone"


@pytest.mark.parametrize("mode", ["unknown", "self", "repeated"])
def test_relation_references_are_closed_and_unambiguous(mode):
    value = selection_value()
    value["selections"].append({"id": "ear", "fact_refs": ["earphone"],
                                 "role": "primary", "entity": "headphone", "view": "readout"})
    relation = {"from_entity": "phone", "to_entity": "headphone", "kind": "peer"}
    if mode == "unknown":
        relation["to_entity"] = "other"
    elif mode == "self":
        relation["to_entity"] = "phone"
    value["relations"] = [relation, copy.deepcopy(relation)] if mode == "repeated" else [relation]
    with pytest.raises(ValueError, match="SEMANTIC_"):
        decode(value)


def test_accepted_title_and_host_group_remain_protected():
    request = request_value()
    request.facts[0].required = True
    value = selection_value()
    with pytest.raises(ValueError, match="REQUIRED_FACT: title"):
        decode(value, request)
    value["selections"].append({"id": "header", "fact_refs": ["title"],
                                 "role": "title", "view": "text"})
    resolved, _ = decode(value, request)
    assert next(fact for fact in resolved.facts if fact.id == "title").required
    request.information_groups = [InformationGroup(id="closed", fact_refs=["battery", "earphone"])]
    with pytest.raises(ValueError, match="INFORMATION_GROUP"):
        decode(value, request)


def test_literal_span_is_restored_verbatim_without_model_rewriting():
    request = request_value()
    request.query = "显示电量，备用电话12345"
    value = selection_value()
    value["selections"].append({"id": "literal", "fact_refs": ["q1"], "role": "secondary",
                                 "entity": "phone", "view": "text"})
    resolved, plan = decode(value, request)
    literal = next(fact for fact in resolved.facts if fact.id == "literal_q1")
    assert literal.text == "备用电话12345"
    assert literal.path is None
    assert plan.selections[-1].fact_refs == ["literal_q1"]
    assert resolved.provenance["semantic_selection"]["literal_sources"][0]["text"] == literal.text


def test_raw_cardspec_candidates_use_the_same_semantic_protocol(entry):  # noqa: F811
    request = entry.prepare(content(), case_id="real-cardspec")
    reference = next(fact for fact in request.facts
                     if fact.path and fact.path.endswith("temperatureText"))
    value = {"selections": [{"id": "temperature", "fact_refs": [reference.id],
                              "role": "primary", "view": "readout"}]}
    resolved, plan = decode(value, request)
    assert reference.id in plan.selections[0].fact_refs
    assert next(fact for fact in resolved.facts if fact.id == reference.id).path == reference.path
    assert resolved.source_content == request.source_content


def test_static_source_rejects_before_requesting_a_model(entry):  # noqa: F811
    raw = content()
    raw["candidateDataBindings"] = []
    request = entry.prepare(raw, case_id="static")
    with pytest.raises(ValueError, match="SEMANTIC_SOURCE_UNSUPPORTED"):
        semantic_messages(request)


def test_record_detail_action_uses_selected_time_metadata_without_a_timeline_choice():
    request = request_value()
    value = selection_value()
    value["actions"][0]["scope"] = "record"
    with pytest.raises(ValueError, match="SEMANTIC_RECORD_ACTION"):
        decode(value, request)
    request.facts.append(request.facts[2].model_copy(update={
        "id": "record_time", "text": "14:00", "kind": "time", "path": "/data/time",
    }))
    value["selections"][1]["fact_refs"].append("record_time")
    resolved, plan = decode(value, request)
    assert plan.actions[0].scope == "record"
    assert {selected.view for selected in plan.selections} == {"readout", "details"}
    assert resolved.actions[0].event == request.actions[0].event
    assert next(fact for fact in resolved.facts if fact.id == "record_time").path == "/data/time"
    value["actions"][0]["owner"] = None
    with pytest.raises(ValueError, match="SEMANTIC_RECORD_ACTION"):
        decode(value, request)


def test_timeline_view_cannot_invent_real_time_for_a_record_action():
    value = selection_value()
    value["actions"][0]["scope"] = "record"
    value["selections"][0]["view"] = "timeline"
    with pytest.raises(ValueError, match="SEMANTIC_RECORD_ACTION"):
        decode(value)


def test_unselected_time_cannot_authorize_record_clicks():
    request = request_value()
    request.facts.append(request.facts[2].model_copy(update={
        "id": "record_time", "text": "14:00", "kind": "time", "path": "/data/time",
    }))
    value = selection_value()
    value["actions"][0]["scope"] = "record"
    with pytest.raises(ValueError, match="SEMANTIC_RECORD_ACTION"):
        decode(value, request)


@pytest.mark.parametrize("time_field", ["dtStart", "dtEnd", "startDate"])
def test_registered_calendar_time_path_retains_record_click_when_kind_is_text(time_field):
    request = request_value()
    request.card_spec["dataBindings"] = [{
        "capabilityId": "GetCalendarEvents", "writeResultTo": "/data/agenda",
    }]
    request.facts.append(request.facts[2].model_copy(update={
        "id": "record_time", "text": "示例", "kind": "text",
        "path": "/data/agenda/events/0/" + time_field,
    }))
    value = selection_value()
    value["actions"][0]["scope"] = "record"
    value["selections"][1]["fact_refs"].append("record_time")
    resolved, plan = decode(value, request)
    assert plan.actions[0].scope == "record"
    assert resolved.actions[0].event == request.actions[0].event
    time_fact = next(fact for fact in resolved.facts if fact.id == "record_time")
    assert time_fact.kind == "text"
    assert time_fact.path == "/data/agenda/events/0/" + time_field
    assert time_fact.text == "示例"
    assert record_time_sources(resolved, resolved.facts) == {"record_time"}


@pytest.mark.parametrize("capability,path", [
    ("OtherCapability", "/data/agenda/events/0/dtStart"),
    ("GetCalendarEvents", "/data/another/events/0/dtStart"),
    ("GetCalendarEvents", "/data/agenda/eventsOther/0/dtStart"),
    ("GetCalendarEvents", "/data/agenda/events/0/title"),
    ("GetCalendarEvents", "/data/agenda/events/0/countdownDays"),
    ("GetCalendarEvents", "/data/agenda/events/0/notDtStart"),
])
def test_calendar_record_time_requires_the_registered_root_and_exact_time_field(capability, path):
    request = request_value()
    request.card_spec["dataBindings"] = [{
        "capabilityId": capability, "writeResultTo": "/data/agenda",
    }]
    request.facts.append(request.facts[2].model_copy(update={
        "id": "looks_like_time", "text": "2026-11-20 14:00", "kind": "text", "path": path,
    }))
    request.query = "日程事件14:00，点击记录查看详情"
    value = selection_value()
    value["actions"][0]["scope"] = "record"
    value["selections"][1]["fact_refs"].append("looks_like_time")
    assert record_time_sources(request, request.facts) == set()
    with pytest.raises(ValueError, match="SEMANTIC_RECORD_ACTION"):
        decode(value, request)


@pytest.mark.parametrize("kind", ["date", "time"])
def test_explicit_time_type_still_works_without_calendar_bindings(kind):
    request = request_value()
    request.facts[2].kind = kind
    assert record_time_sources(request, request.facts) == {"state"}


def test_record_detail_action_cannot_bind_a_different_record():
    value = selection_value()
    value["selections"].append({"id": "record", "fact_refs": ["earphone"],
                                 "role": "primary", "view": "timeline"})
    value["actions"][0]["scope"] = "record"
    with pytest.raises(ValueError, match="SEMANTIC_RECORD_ACTION"):
        decode(value)


def record_readout_value():
    path = "/data/records/events/0/"
    fields = {
        "name": ("title", "记录甲"), "date": ("startDate", "08-06"),
        "time": ("dtStart", "14:00"), "days": ("countdownDays", "0天后"),
        "place": ("eventLocation", "位置甲"),
    }
    facts = []
    for identity, (leaf, text) in fields.items():
        facts.append(dict(id=identity, text=text, path=path + leaf, entity="record"))
    request = CardRequest(case_id="record-readout", query="展示完整记录并点击查看详情",
        size="2x4", component_contract="upstream-card-v1",
        surface=dict(width_vp=300, height_vp=150), facts=facts,
        actions=[dict(id="open", label="详情", entity="record",
                      event=dict(call="openRecord", args=dict(identity="original")))],
        card_spec=dict(dataBindings=[dict(capabilityId="GetCalendarEvents",
                                         writeResultTo="/data/records")]),
        data_model=dict(data=dict(records=dict(events=[dict(
            title="记录甲", startDate="08-06", dtStart="14:00", countdownDays=0,
            eventLocation="位置甲")]))))
    value = dict(selections=[
        dict(id="record", fact_refs=["name", "date", "time", "days"],
             role="primary", view="readout", focus_ref="name"),
        dict(id="place", fact_refs=["place"], role="secondary", view="text"),
    ], actions=[dict(ref="open", owner="record", scope="record")])
    return request, value


def test_verified_record_readout_keeps_text_focus_and_all_fields_before_component_selection():
    request, value = record_readout_value()
    before = request.model_dump()
    resolved, plan = decode(value, request)
    assert plan.selections[0].focus_ref == "name"
    assert plan.selections[0].fact_refs == ["name", "date", "time", "days"]
    assert [selected.role for selected in plan.selections] == ["primary", "secondary"]
    assert {fact.id for fact in resolved.facts} == {fact.id for fact in request.facts}
    assert all(fact.required for fact in resolved.facts)
    assert resolved.actions[0].event == request.actions[0].event
    assert request.model_dump() == before


def test_ordinary_readout_does_not_gain_record_shape_or_text_focus_exceptions():
    request, value = record_readout_value()
    value["actions"][0]["scope"] = "entity"
    with pytest.raises(ValueError, match="SEMANTIC_READOUT_SHAPE"):
        decode(value, request)


@pytest.mark.parametrize("change,error", [
    ("unknown_action", "SEMANTIC_UNKNOWN_ACTION"),
    ("wrong_owner", "SEMANTIC_RECORD_ACTION"),
    ("untrusted_time", "SEMANTIC_RECORD_ACTION"),
    ("unknown_focus", "SEMANTIC_FOCUS_REFERENCE"),
    ("progress", "SEMANTIC_RECORD_VISUAL"),
    ("excess_fields", "SEMANTIC_RECORD_FIELDS"),
])
def test_record_declaration_cannot_bypass_source_ownership_or_existing_limits(change, error):
    request, value = record_readout_value()
    if change == "unknown_action":
        value["actions"][0]["ref"] = "unknown"
    elif change == "wrong_owner":
        value["actions"][0]["owner"] = "other"
    elif change == "untrusted_time":
        request.card_spec["dataBindings"][0]["capabilityId"] = "OtherCapability"
    elif change == "unknown_focus":
        value["selections"][0]["focus_ref"] = "place"
    elif change == "progress":
        value["selections"][1]["view"] = "progress"
    else:
        for index in range(3):
            identity = "extra" + str(index)
            request.facts.append(request.facts[-1].model_copy(update={
                "id": identity, "path": None,
            }))
            value["selections"].append(dict(
                id=identity, fact_refs=[identity], role="secondary", view="text",
            ))
    with pytest.raises(ValueError, match=error):
        decode(value, request)


def test_explicit_global_action_cannot_gain_a_local_owner():
    value = selection_value()
    value["actions"][0]["scope"] = "global"
    with pytest.raises(ValueError, match="SEMANTIC_GLOBAL_ACTION"):
        decode(value)
    value["actions"][0].pop("scope")
    value["actions"].append({"ref": "music", "scope": "global", "owner": None})
    _, plan = decode(value)
    assert plan.actions[-1].scope == "global"
    assert plan.actions[-1].owner is None


def test_prompt_contains_source_context_and_schema_without_component_catalog():
    messages = semantic_messages(request_value())
    payload = json.loads(messages[1]["content"])
    assert payload["facts"][1]["path"] == "/data/battery"
    assert payload["actions"][0]["event"] == {"call": "Power", "args": {}}
    assert "component" not in json.dumps(payload["response_schema"])
    assert payload["response_schema"]["additionalProperties"] is False
    assert payload["title_ref"] == "t"
    assert payload["facts"][1]["id"] == "f1"
    assert payload["facts"][1]["entity"] == "e0"
    assert payload["actions"][0]["id"] == "a0"


def test_prompt_distinguishes_object_relations_requirements_and_optional_output_defaults():
    instructions = semantic_messages(request_value())[0]["content"]
    assert "两个不同对象" in instructions
    assert "只有一个对象时relations留空" in instructions
    assert "同一对象内的主辅由selection.role表达" in instructions
    assert "required:false仅表示宿主尚未强制" in instructions
    assert "用户明确要求的事实须选入并保持mandatory=true" in instructions
    assert "不要求选择timeline，程序负责选型" in instructions
    assert "不要机械重复所有默认字段" in instructions
    assert '"selections":[{"id":"main","fact_refs":["f1"]' in instructions


def test_prompt_leaves_optional_public_title_with_program_and_preserves_necessary_identity():
    instructions = semantic_messages(request_value())[0]["content"]
    assert "公共title_ref默认由程序托管" in instructions
    assert "宿主required=true或用户明确指定要展示的标题才选入" in instructions
    assert "业务对象及记录的必要名称仍须按需求选择" in instructions
    assert "label不是每个读数必选" in instructions
    assert "多个同类裸读数需消歧时" in instructions


def test_prompt_prefers_one_business_focus_without_dropping_requirements_or_forbidding_peers():
    instructions = semantic_messages(request_value())[0]["content"]
    assert "同一业务未被用户明确要求并列强调时，优先一个主焦点" in instructions
    assert "其余明确要求字段完整保留为辅助" in instructions
    assert "多个独立业务或用户明确要求对比、并列强调时，仍可有多个primary" in instructions
    assert "required不等于primary" in instructions
    assert "候选顺序靠前也不代表更重要" in instructions


@pytest.mark.parametrize("accept_title", [False, True])
def test_optional_title_is_metadata_until_selected_but_accepted_title_stays_protected(accept_title):
    request, value = request_value(), selection_value()
    if accept_title:
        value["selections"].append({
            "id": "heading", "fact_refs": ["title"], "role": "title", "view": "text",
        })
    resolved, _ = decode(value, request)
    title = next(fact for fact in resolved.facts if fact.id == "title")
    assert title.text == request.card_spec.get("title")
    assert title.required is accept_title
    assert title.path is None


def test_unused_optional_label_is_not_promoted_to_a_host_requirement():
    request, value = request_value(), selection_value()
    request.facts.append(request.facts[2].model_copy(update={
        "id": "name", "text": "设备名称", "semantic": "label",
    }))
    resolved, _ = decode(value, request)
    assert "name" not in {fact.id for fact in resolved.facts}
    assert "name" in resolved.provenance["semantic_selection"]["unselected_facts"]
    assert next(fact for fact in resolved.facts if fact.id == "battery").required


def test_omitted_defaults_promote_selected_unadjudicated_candidates_to_mandatory():
    value = {
        "selections": [
            {"id": "main", "fact_refs": ["battery"], "role": "primary", "view": "readout"},
            {"id": "state", "fact_refs": ["state"], "role": "secondary", "view": "text"},
        ],
        "actions": [{"ref": "power", "owner": "phone"}],
    }
    resolved, plan = decode(value)
    assert plan.version == PROTOCOL
    assert plan.relations == [] and plan.unresolved == []
    assert all(selected.mandatory for selected in plan.selections)
    assert next(fact for fact in resolved.facts if fact.id == "state").required
    assert plan.selections[0].entity == "phone"


@pytest.mark.parametrize("reverse", [False, True])
def test_readout_can_keep_real_name_and_bound_value_in_either_reference_order(reverse):
    request = request_value()
    request.facts.append(request.facts[2].model_copy(update={
        "id": "name", "text": "手机", "semantic": "label", "path": "/data/name",
    }))
    refs = ["name", "battery"]
    if reverse:
        refs.reverse()
    value = selection_value()
    value["selections"][0]["fact_refs"] = refs
    before = request.model_dump()
    resolved, plan = decode(value, request)
    assert plan.selections[0].fact_refs == refs
    assert plan.selections[0].entity == "phone"
    restored = {fact.id: fact for fact in resolved.facts}
    assert restored["name"].path == "/data/name"
    assert restored["battery"].path == "/data/battery"
    assert request.model_dump() == before


@pytest.mark.parametrize("view", ["text", "progress"])
def test_text_and_progress_views_do_not_gain_multiple_reference_slots(view):
    value = selection_value()
    value["selections"][0].update(view=view, fact_refs=["battery", "state"])
    with pytest.raises(ValueError, match="SEMANTIC_ATOMIC_VIEW"):
        decode(value)


def test_readout_can_group_one_bound_reading_with_its_existing_support_text():
    value = selection_value()
    value["selections"] = [value["selections"][0]]
    value["selections"][0]["fact_refs"] = ["battery", "state"]
    resolved, plan = decode(value)
    assert plan.selections[0].focus_ref == "battery"
    assert plan.selections[0].fact_refs == ["battery", "state"]
    assert {fact.id for fact in resolved.facts if fact.required} == {"battery", "state"}


def grouped_readout():
    request = request_value()
    request.facts.append(request.facts[2].model_copy(update={
        "id": "name", "text": "手机", "semantic": "label", "path": "/data/name",
    }))
    value = selection_value()
    value["selections"] = [value["selections"][0]]
    value["selections"][0]["fact_refs"] = ["name", "battery", "state"]
    return request, value


@pytest.mark.parametrize("refs", [
    ["name", "battery", "state"], ["state", "name", "battery"], ["battery", "state", "name"],
])
def test_grouped_readout_recovers_only_the_unique_trusted_main_without_reordering(refs):
    request, value = grouped_readout()
    value["selections"][0]["fact_refs"] = refs
    before = request.model_dump()
    resolved, plan = decode(value, request)
    selected = plan.selections[0]
    assert selected.focus_ref == "battery"
    assert selected.fact_refs == refs
    assert selected.role == "primary"
    assert selected.entity == "phone"
    assert {fact.id for fact in resolved.facts if fact.required} == set(refs)
    assert resolved.actions[0].event == request.actions[0].event
    audit = resolved.provenance["semantic_selection"]["readout_sources"]
    assert audit == [{
        "selection_id": "reading", "focus_ref": "battery", "focus_role": "primary",
        "supporting_refs": [ref for ref in refs if ref != "battery"],
        "supporting_role": "secondary",
    }]
    assert request.model_dump() == before


@pytest.mark.parametrize("kind", ["quantity", "duration"])
def test_grouped_main_uses_trusted_value_type_instead_of_preview_text(kind):
    request, value = grouped_readout()
    main = next(fact for fact in request.facts if fact.id == "battery")
    main.kind, main.value, main.text = kind, None, "示例"
    resolved, plan = decode(value, request)
    assert plan.selections[0].focus_ref == "battery"
    assert next(fact for fact in resolved.facts if fact.id == "battery").text == "示例"


def test_dates_are_supporting_not_a_second_numeric_main():
    request, value = grouped_readout()
    request.facts[2].kind = "date"
    request.facts[2].text = "2026-11-20"
    _, plan = decode(value, request)
    assert plan.selections[0].focus_ref == "battery"


def test_two_possible_main_values_require_explicit_focus_and_keep_the_other_value():
    request, value = grouped_readout()
    request.facts[2].kind = "quantity"
    request.facts[2].value = 2
    with pytest.raises(ValueError, match="SEMANTIC_FOCUS_REQUIRED"):
        decode(value, request)
    value["selections"][0]["focus_ref"] = "state"
    resolved, plan = decode(value, request)
    assert plan.selections[0].focus_ref == "state"
    assert plan.selections[0].fact_refs == ["name", "battery", "state"]
    assert next(fact for fact in resolved.facts if fact.id == "battery").value == 68
    assert {fact.id for fact in resolved.facts if fact.required} == {"name", "battery", "state"}


@pytest.mark.parametrize("focus", ["name", "missing", "earphone"])
def test_focus_cannot_refer_to_labels_unknown_or_unselected_candidates(focus):
    request, value = grouped_readout()
    value["selections"][0]["focus_ref"] = focus
    with pytest.raises(ValueError, match="SEMANTIC_FOCUS_"):
        decode(value, request)


def test_focus_uses_the_same_short_alias_restore_as_selected_facts():
    request, value = grouped_readout()
    value["selections"][0].update(fact_refs=["f4", "f1", "f2"], focus_ref="f1", entity="e0")
    _, plan = decode(value, request)
    assert plan.selections[0].focus_ref == "battery"
    assert plan.selections[0].fact_refs == ["name", "battery", "state"]


def test_focus_only_describes_readout_not_visual_style_or_other_views():
    value = selection_value()
    value["selections"][1]["focus_ref"] = "state"
    with pytest.raises(ValueError, match="SEMANTIC_FOCUS_VIEW"):
        decode(value)


def test_untyped_support_text_cannot_be_guessed_as_a_grouped_main():
    request, value = grouped_readout()
    main = next(fact for fact in request.facts if fact.id == "battery")
    main.kind, main.value, main.text = "text", None, "99999"
    request.data_model = {"data": {"battery": "99999"}}
    with pytest.raises(ValueError, match="SEMANTIC_READOUT_VALUE"):
        decode(value, request)


@pytest.mark.parametrize("number", [0, 12, -4, 0.5, -1.25])
def test_untyped_main_can_use_finite_numeric_binding_without_rewriting_the_fact(number):
    request, value = grouped_readout()
    main = next(fact for fact in request.facts if fact.id == "battery")
    main.kind, main.value, main.text = "text", None, "原预览文字"
    request.data_model = {"data": {"battery": number}}
    before = request.model_dump()
    resolved, plan = decode(value, request)
    restored = next(fact for fact in resolved.facts if fact.id == "battery")
    assert plan.selections[0].focus_ref == "battery"
    assert restored.kind == "text" and restored.value is None
    assert restored.text == "原预览文字"
    assert restored.path == "/data/battery"
    assert restored.model_dump(exclude={"required"}) == main.model_dump(exclude={"required"})
    assert readout_value_source(request, main)
    assert request.model_dump() == before


@pytest.mark.parametrize("preview", [True, False, None, "68", "说明", float("inf"), float("nan")])
def test_untyped_binding_does_not_treat_boolean_missing_or_string_as_numeric(preview):
    request, value = grouped_readout()
    main = next(fact for fact in request.facts if fact.id == "battery")
    main.kind, main.value, main.text = "text", None, "68"
    request.data_model = {"data": {"battery": preview}}
    assert not readout_value_source(request, main)
    with pytest.raises(ValueError, match="SEMANTIC_READOUT_VALUE"):
        decode(value, request)


def test_numeric_binding_requires_a_declared_runtime_root_and_existing_pointer():
    request, _ = grouped_readout()
    main = next(fact for fact in request.facts if fact.id == "battery")
    main.kind, main.value = "text", None
    request.data_model = {"data": {}}
    assert not readout_value_source(request, main)
    request.data_model = {"data": {"battery": 68}}
    request.card_spec["dataBindings"] = [{"writeResultTo": "/data/unrelated"}]
    assert not readout_value_source(request, main)


def test_numeric_source_uses_existing_json_pointer_array_and_escape_handling():
    request, _ = grouped_readout()
    main = next(fact for fact in request.facts if fact.id == "battery")
    main.kind, main.value, main.path = "text", None, "/data/records/0/read~1value"
    request.data_model = {"data": {"records": [{"read/value": 0}]}}
    assert readout_value_source(request, main)
    main.semantic = "label"
    assert not readout_value_source(request, main)


def test_grouped_readout_rejects_extra_labels_or_excess_auxiliary_fields():
    request, value = grouped_readout()
    request.facts[2].semantic = "label"
    with pytest.raises(ValueError, match="SEMANTIC_READOUT_SHAPE"):
        decode(value, request)
    request.facts[2].semantic = "detail"
    for index in range(2):
        identity = "extra" + str(index)
        request.facts.append(request.facts[2].model_copy(update={"id": identity}))
        value["selections"][0]["fact_refs"].append(identity)
    with pytest.raises(ValueError, match="SEMANTIC_READOUT_SHAPE"):
        decode(value, request)


def test_readout_name_and_value_cannot_cross_existing_objects():
    request = request_value()
    request.facts.append(request.facts[2].model_copy(update={
        "id": "name", "text": "耳机", "semantic": "label", "entity": "headphone",
    }))
    value = selection_value()
    value["selections"][0]["fact_refs"] = ["name", "battery"]
    with pytest.raises(ValueError, match="SEMANTIC_ENTITY_MIX"):
        decode(value, request)


def test_short_transmission_references_restore_original_facts_owners_and_relations():
    value = {
        "selections": [
            {"id": "phone", "fact_refs": ["f1"], "role": "primary", "view": "readout"},
            {"id": "ear", "fact_refs": ["f3"], "role": "primary", "view": "readout",
             "entity": "e1"},
        ],
        "actions": [{"ref": "a0", "owner": "e0"}],
        "relations": [{"from_entity": "e0", "to_entity": "e1", "kind": "peer"}],
    }
    resolved, plan = decode(value)
    assert plan.selections[0].fact_refs == ["battery"]
    assert plan.selections[0].entity == "phone"
    assert plan.selections[1].fact_refs == ["earphone"]
    assert plan.actions[0].ref == "power"
    assert resolved.actions[0].entity == "phone"
    assert plan.relations[0].from_entity == "phone"
    assert plan.relations[0].to_entity == "headphone"


@pytest.mark.parametrize("language", ["", "json"])
def test_single_whole_response_fence_preserves_closed_json_protocol(language):
    request = request_value()
    raw = f"```{language}\n{json.dumps(selection_value())}\n```"
    resolved, plan = decode_selection(raw, request)
    assert plan.selections[0].fact_refs == ["battery"]
    assert resolved.actions[0].event == request.actions[0].event


@pytest.mark.parametrize("prefix,suffix", [("说明：", ""), ("", "\n补充解释")])
def test_fence_tolerance_does_not_extract_embedded_or_extra_content(prefix, suffix):
    raw = prefix + "```json\n" + json.dumps(selection_value()) + "\n```" + suffix
    with pytest.raises(ValueError):
        decode_selection(raw, request_value())


@pytest.mark.parametrize("raw", ["invalid", '{"selections":[],"selections":[]}',
                               json.dumps({"unresolved": ["用户需要的数据没有可用候选"]})])
def test_one_model_call_keeps_invalid_response_and_marks_protocol_error(raw):
    class Model:
        def __init__(self):
            self.calls = []

        async def complete(self, messages, phase):
            self.calls.append({"phase": phase})
            return raw

    model, attempts = Model(), []
    with pytest.raises(ValueError):
        asyncio.run(select_semantic(request_value(), model, attempts))
    assert len(model.calls) == 1
    assert model.calls[0]["phase"] == "semantic_selection"
    assert model.calls[0]["output_protocol"] == PROTOCOL
    assert model.calls[0]["validation_error"]
    assert attempts[0]["raw_response"] == raw
    assert attempts[0]["status"] == "failed"


def test_valid_response_is_accepted_with_exactly_one_mock_call():
    class Model:
        calls = []

        async def complete(self, messages, phase):
            self.calls.append({"phase": phase})
            return json.dumps(selection_value())

    model, attempts = Model(), []
    resolved, plan = asyncio.run(select_semantic(request_value(), model, attempts))
    assert len(model.calls) == 1
    assert plan.version == PROTOCOL
    assert resolved.requirement_mode == "resolved_query"
    assert attempts[0]["status"] == "accepted"


def test_unsupported_source_does_not_relabel_previous_model_call(entry):  # noqa: F811
    class Model:
        def __init__(self):
            self.calls = [{"phase": "theme_selection", "output_protocol": "previous"}]

        async def complete(self, messages, phase):
            raise AssertionError("unsupported source must not call a model")

    raw = content()
    raw["candidateDataBindings"] = []
    request = entry.prepare(raw, case_id="static-reused-model")
    model, attempts = Model(), []
    before = copy.deepcopy(model.calls)
    with pytest.raises(ValueError, match="SEMANTIC_SOURCE_UNSUPPORTED"):
        asyncio.run(select_semantic(request, model, attempts))
    assert model.calls == before
    assert attempts[0]["raw_response"] is None
    assert attempts[0]["status"] == "failed"


def test_transport_failure_does_not_masquerade_as_response_validation():
    class Model:
        def __init__(self):
            self.calls = [{"phase": "previous", "status": "complete"}]

        async def complete(self, messages, phase):
            self.calls.append({"phase": phase, "status": "failed"})
            raise ConnectionError("mock connection failure")

    model, attempts = Model(), []
    with pytest.raises(ConnectionError, match="mock connection failure"):
        asyncio.run(select_semantic(request_value(), model, attempts))
    assert model.calls[0] == {"phase": "previous", "status": "complete"}
    assert model.calls[1]["selection_error"] == "mock connection failure"
    assert "validation_error" not in model.calls[1]
    assert attempts[0]["raw_response"] is None
    assert attempts[0]["error_type"] == "ConnectionError"
