"""用冻结提示自带的合成庭院卡检验 RQ2 共同出口，不依赖模型响应或正式样本。"""

from copy import deepcopy

import pytest

from . import wide_check

evidence = wide_check.evidence


def nodes(card):
    return {n["id"]: n for n in card[1]["updateComponents"]["components"]}


def assess(original, candidate, source):
    return wide_check.assess(
        evidence.encode(original), evidence.encode(candidate), source
    )


@pytest.fixture
def garden():
    pytest.importorskip("PIL")
    try:
        evidence.native.dependency_files()
    except RuntimeError as exc:
        pytest.skip(str(exc))
    card = evidence.native.parse(evidence.model._example_native().encode())
    source = deepcopy(evidence.model._EXAMPLE_SOURCE)
    by_id = nodes(card)
    by_id["caption"]["styles"]["height"] = 24
    by_id["value"]["styles"]["height"] = 36
    # 两个动态事实具有相同样值。另一个只供动作使用的参数可独立验证。
    source["candidate_paths"].extend(["/garden/backup", "/garden/logId"])
    source["sample_data"]["garden"].update(backup=18, logId="east")
    card[2]["updateDataModel"]["value"] = deepcopy(source["sample_data"])
    handler = source["candidate_actions"][0]["handler"]
    handler["args"] = {"record": {"path": "/garden/logId"}}
    by_id["open"]["onClick"] = [deepcopy(handler)]
    return card, source


def group_readings(card):
    by_id = nodes(card)
    by_id["root"]["children"] = ["readings", "open"]
    card[1]["updateComponents"]["components"].append(
        {
            "id": "readings",
            "component": "Column",
            "children": ["caption", "value"],
            "itemMargin": 2,
            "styles": {"width": 126, "height": 66},
        }
    )


def test_new_container_can_rescue_geometry_with_same_order_bindings_actions_and_paint(
    garden,
):
    original, source = garden
    candidate = deepcopy(original)
    nodes(original)["value"]["styles"]["height"] = 24
    group_readings(candidate)
    got = assess(original, candidate, source)
    assert got["before"]["geometry"]["pass"] is False
    assert all(
        got["after"][k]["pass"] is True for k in ("protocol", "source", "geometry")
    )
    assert got["accepted"] is True and got["violations"] == []
    assert all(got["preservation"].values()) and got["local_rule_pass"] is False


@pytest.mark.parametrize("change", ["owner", "descendants"])
def test_click_target_requires_same_owner_and_same_descendant_leaves(garden, change):
    original, source = garden
    group_readings(original)
    nodes(original)["readings"]["onClick"] = deepcopy(
        nodes(original)["open"]["onClick"]
    )
    candidate = deepcopy(original)
    by_id = nodes(candidate)
    if change == "owner":
        by_id["root"]["onClick"] = by_id["readings"].pop("onClick")
    else:
        by_id["root"]["children"] = ["caption", "readings", "open"]
        by_id["readings"]["children"] = ["value"]
        by_id["readings"]["styles"]["height"] = 36
    got = assess(original, candidate, source)
    assert got["accepted"] is False and got["violations"] == ["actions_and_descendants"]
    assert got["preservation"]["leaves_in_order"] is True
    assert (
        got["after"]["source"]["pass"] is True
        and got["after"]["geometry"]["pass"] is True
    )


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("static_same_value", "leaves_in_order"),
        ("equal_sample_other_path", "leaves_in_order"),
        ("lose_unit", "leaves_in_order"),
        ("reorder", "leaves_in_order"),
        ("smaller_font", "leaves_in_order"),
        ("weight", "leaves_in_order"),
        ("line_height", "leaves_in_order"),
        ("title_color", "node_colors"),
        ("button_label", "leaves_in_order"),
        ("unrendered_frame_field", "first_frame"),
    ],
)
def test_individually_forbidden_changes_fail_even_when_all_absolute_gates_pass(
    garden, change, reason
):
    original, source = garden
    candidate = deepcopy(original)
    by_id = nodes(candidate)
    metric = by_id["value"]
    if change == "static_same_value":
        metric["content"] = "读数 18℃"
    elif change == "equal_sample_other_path":
        metric["content"] = metric["content"].replace("/garden/value", "/garden/backup")
    elif change == "lose_unit":
        metric["content"] = metric["content"].replace(" + '℃'", "")
    elif change == "reorder":
        by_id["root"]["children"] = ["value", "caption", "open"]
    elif change == "smaller_font":
        metric["styles"]["fontSize"] -= 2
    elif change == "weight":
        metric["styles"]["fontWeight"] = 400
    elif change == "line_height":
        metric["styles"]["lineHeight"] = 1.15
    elif change == "title_color":
        by_id["caption"]["styles"]["fontColor"] = "#FF123456"
    elif change == "button_label":
        by_id["open"]["label"] = "详情"
    else:
        candidate[2]["updateDataModel"]["value"]["garden"]["backup"] = 19
    got = assess(original, candidate, source)
    assert got["accepted"] is False and got["violations"] == [reason]
    assert got["preservation"][reason] is False
    assert all(
        got["after"][k]["pass"] is True for k in ("protocol", "source", "geometry")
    )


@pytest.mark.parametrize(
    "state", ["missing_in_artifact", "changed", "caller_sample_unknown"]
)
def test_dynamic_action_parameter_needs_caller_and_first_frame_data_even_if_inputs_match(
    garden, state
):
    original, source = garden
    frame = original[2]["updateDataModel"]["value"]["garden"]
    if state == "missing_in_artifact":
        del frame["logId"]
    elif state == "changed":
        frame["logId"] = "west"
    else:
        del source["sample_data"]["garden"]["logId"]
    got = assess(original, original, source)
    assert got["accepted"] is False and got["violations"] == ["action_parameter_source"]
    assert got["after"]["source"]["pass"] is True and all(got["preservation"].values())
    assert got["after"]["source"]["action_parameter_samples"] == [
        {
            "owner": "open",
            "path": "/garden/logId",
            "exact_handler_allowed": True,
            "state": state,
        }
    ]


def test_plausible_action_with_unregistered_arguments_is_rejected(garden):
    original, source = garden
    candidate = deepcopy(original)
    handler = nodes(candidate)["open"]["onClick"][0]
    handler["args"]["record"]["path"] = "/garden/backup"
    got = assess(original, candidate, source)
    assert got["accepted"] is False
    assert {"source", "action_parameter_source", "actions_and_descendants"} <= set(
        got["violations"]
    )
    assert "UNAUTHORIZED_HANDLER" in got["after"]["source"]["issues"]
    (sample,) = got["after"]["source"]["action_parameter_samples"]
    assert sample["state"] == "matched" and sample["exact_handler_allowed"] is False


def test_removing_a_selected_leaf_cannot_be_hidden_by_a_valid_smaller_tree(garden):
    original, source = garden
    candidate = deepcopy(original)
    nodes(candidate)["root"]["children"].remove("value")
    components = candidate[1]["updateComponents"]["components"]
    components.remove(nodes(candidate)["value"])
    got = assess(original, candidate, source)
    assert got["accepted"] is False and "leaves_in_order" in got["violations"]
    assert all(
        got["after"][k]["pass"] is True for k in ("protocol", "source", "geometry")
    )


def test_changed_displayed_first_frame_hits_source_and_preservation(garden):
    original, source = garden
    candidate = deepcopy(original)
    candidate[2]["updateDataModel"]["value"]["garden"]["value"] = 19
    got = assess(original, candidate, source)
    assert got["accepted"] is False and set(got["violations"]) == {
        "source",
        "first_frame",
    }
    assert "SAMPLE_CHANGED /garden/value" in got["after"]["source"]["issues"]
    assert got["preservation"]["leaves_in_order"] is True


@pytest.mark.parametrize(
    "field,value", [("width", 148), ("clip", False), ("borderRadius", 12)]
)
def test_root_dimensions_and_shell_are_protected(garden, field, value):
    original, source = garden
    candidate = deepcopy(original)
    nodes(candidate)["root"]["styles"][field] = value
    got = assess(original, candidate, source)
    assert got["accepted"] is False and "protocol" in got["violations"]
    if field == "clip":
        assert got["preservation"] == {}
        assert any(v.startswith("protected_content_unknown") for v in got["violations"])
    else:
        assert "canvas_and_shell" in got["violations"]


def test_invalid_bytes_preserve_unknown_status_and_cannot_pass(garden):
    original, source = garden
    got = wide_check.assess(evidence.encode(original), b"{}", source)
    assert got["accepted"] is False and got["after"]["protocol"]["pass"] is False
    assert (
        got["after"]["source"]["pass"] is None
        and got["after"]["geometry"]["pass"] is None
    )
    assert got["preservation"] == {}
    assert any(v.startswith("protected_content_unknown") for v in got["violations"])
