"""P4分类只用结构和请求候选，未知几何不判产品失败。"""

import hashlib
import json
import sys
from itertools import pairwise

import pytest

from p4_classify import classify, main, read_json_objects


def text(identity, font=12):
    return {
        "id": identity,
        "component": "Text",
        "content": "unread_by_classifier",
        "styles": {"fontSize": font, "fontWeight": 400},
    }


def title():
    return [
        {
            "id": "title",
            "component": "Row",
            "children": ["title_text"],
            "styles": {"height": 20},
        },
        text("title_text"),
    ]


def dual_content():
    return [
        {
            "id": "root",
            "component": "Column",
            "children": ["title", "__layout__root__body"],
            "styles": {"width": "matchParent", "height": "matchParent"},
        },
        *title(),
        {
            "id": "__layout__root__body",
            "component": "Column",
            "children": ["__layout__root__primary", "__layout__root__support"],
        },
        {"id": "__layout__root__primary", "component": "Column", "children": ["main"]},
        {
            "id": "__layout__root__support",
            "component": "Column",
            "children": ["detail"],
        },
        text("main", 30),
        text("detail"),
    ]


def messages(nodes):
    return [
        {"version": "v0.9", "createSurface": {"surfaceId": "s"}},
        {
            "version": "v0.9",
            "updateComponents": {"surfaceId": "s", "root": "root", "components": nodes},
        },
        {
            "version": "v0.9",
            "updateDataModel": {"surfaceId": "s", "path": "/", "value": {}},
        },
    ]


def wrapped(nodes, names):
    if not names:
        return nodes
    nodes[0]["id"] = names[-1]
    outer = [
        {"id": "root", "component": "Stack", "children": ["paint", names[0]]},
        {"id": "paint", "component": "Image"},
    ]
    for current, following in pairwise(names):
        outer.append({"id": current, "component": "Column", "children": [following]})
    return [*outer, *nodes]


def record(tmp_path, nodes=None, *, size="2x2", binding_ids=None, compact=None):
    input_path = tmp_path / "input.json"
    bindings = [{"capabilityId": value} for value in (binding_ids or ["ViewWeather"])]
    input_path.write_text(json.dumps({"candidateDataBindings": bindings}), "utf-8")
    value = {
        "case_id": "opaque-example",
        "source": "user",
        "size": size,
        "input_view_path": str(input_path),
        "a2ui_path": None,
        "p1_status": "usable",
        "host_size_vp": None,
    }
    if nodes is not None:
        artifact = tmp_path / "card.jsonl"
        artifact.write_text(json.dumps(messages(nodes)), "utf-8")
        value["a2ui_path"] = str(artifact)
    if compact is not None:
        path = tmp_path / "compact.jsonl"
        path.write_text(
            json.dumps(["root", "Layout", {"layout": compact}, []]), "utf-8"
        )
        value["compact_path"] = str(path)
    return value


@pytest.mark.parametrize(
    "wrappers",
    [
        [],
        ["__genui_render_component__root"],
        ["__post_theme_foreground"],
        ["__post_theme_foreground", "__genui_render_component__root"],
        ["__genui_render_component__root", "__post_theme_foreground"],
    ],
)
def test_both_wrappers_nested_wrappers_and_unwrapped_roots_are_supported(
    tmp_path, wrappers
):
    value = record(tmp_path, wrapped(dual_content(), wrappers))
    result = classify(value, tmp_path)
    assert result["layout"] == "S-title-dual-content"
    assert result["layout_status"] == "classified_structural"
    assert result["evidence"]["physical_geometry"] == "unknown_not_a_product_failure"


@pytest.mark.parametrize("format_name", ["array", "jsonl", "concat", "fence"])
def test_three_json_packaging_formats_are_read_without_changing_source(
    tmp_path, format_name
):
    objects = messages(dual_content())
    content = json.dumps(objects)
    if format_name == "jsonl":
        content = "\n".join(json.dumps(value) for value in objects)
    elif format_name == "concat":
        content = "".join(json.dumps(value) for value in objects)
    elif format_name == "fence":
        content = "```json\n" + content + "\n```"
    path = tmp_path / "artifact.txt"
    path.write_text(content, "utf-8")
    before = path.read_bytes()
    assert read_json_objects(path) == objects
    assert path.read_bytes() == before


def test_physical_geometry_unknown_does_not_erase_a_structural_label(tmp_path):
    value = record(tmp_path, dual_content())
    result = classify(value, tmp_path)
    assert result["layout"] == "S-title-dual-content"
    assert result["evidence"]["geometry_validation"].startswith("not_performed")
    assert "product_failed" not in result


def test_missing_logical_size_is_unknown_without_forcing_small_or_wide(tmp_path):
    value = record(tmp_path, dual_content(), size=None)
    result = classify(value, tmp_path)
    assert result["layout"] is None
    assert result["layout_status"] == "geometry_unknown"
    assert result["evidence"]["candidates"]


def test_compact_label_alone_is_not_a2ui_proof(tmp_path):
    value = record(tmp_path, compact="S-center")
    result = classify(value, tmp_path)
    assert result["layout"] is None
    assert result["layout_status"] == "unavailable"


def test_compact_conflict_is_reported_instead_of_overriding_tree(tmp_path):
    value = record(tmp_path, dual_content(), compact="S-center")
    result = classify(value, tmp_path)
    assert result["layout"] is None
    assert result["layout_status"] == "compact_a2ui_conflict"
    assert result["evidence"]["candidates"][0]["layout"] == "S-title-dual-content"


def test_static_source_layout_outside_fourteen_is_not_renamed(tmp_path):
    value = record(tmp_path, dual_content(), compact="S-static-content")
    result = classify(value, tmp_path)
    assert result["layout"] is None
    assert result["layout_status"] == "source_layout_outside_14"


def test_static_generated_source_ids_remain_outside_fourteen_without_compact(tmp_path):
    nodes = [
        {
            "id": "root",
            "component": "Column",
            "children": ["__layout__root__static_body"],
        },
        {
            "id": "__layout__root__static_body",
            "component": "Column",
            "children": ["value"],
        },
        text("value"),
    ]
    result = classify(record(tmp_path, nodes), tmp_path)
    assert result["layout"] is None
    assert result["layout_status"] == "source_layout_outside_14"


def test_content_with_two_direct_actions_does_not_require_action_wrappers(tmp_path):
    nodes = [
        {
            "id": "root",
            "component": "Column",
            "children": ["__layout__root__content", "first_action", "second_action"],
        },
        {"id": "__layout__root__content", "component": "Column", "children": ["value"]},
        text("value"),
        action("first_action"),
        action("second_action"),
    ]
    result = classify(record(tmp_path, nodes), tmp_path)
    assert result["layout"] == "S-content-dual-action"
    assert (
        result["evidence"]["recipe_conformance"] == "not_validated_from_low_level_tree"
    )


def test_isomorphic_unmarked_content_does_not_force_a_layout(tmp_path):
    nodes = [
        {"id": "root", "component": "Column", "children": ["title", "body"]},
        *title(),
        {"id": "body", "component": "Column", "children": ["first", "second"]},
        text("first"),
        text("second"),
    ]
    result = classify(record(tmp_path, nodes), tmp_path)
    assert result["layout"] is None
    assert result["layout_status"] == "low_confidence_or_ambiguous"
    assert len(result["evidence"]["candidates"]) == 2


def test_two_label_value_rows_are_not_misclassified_as_four_modules(tmp_path):
    nodes = [
        {"id": "root", "component": "Column", "children": ["row_a", "row_b"]},
        {"id": "row_a", "component": "Row", "children": ["label_a", "value_a"]},
        {"id": "row_b", "component": "Row", "children": ["label_b", "value_b"]},
        text("label_a"),
        text("value_a"),
        text("label_b"),
        text("value_b"),
    ]
    result = classify(record(tmp_path, nodes), tmp_path)
    assert result["layout"] is None
    assert not result["evidence"]["candidates"]


@pytest.mark.parametrize(
    "size,expected",
    [
        ("2x2", "S-quad-content"),
        ("2x4", "W-four-slots"),
    ],
)
def test_registered_grid_source_ids_distinguish_four_real_slots(
    tmp_path, size, expected
):
    nodes = [
        {
            "id": "root",
            "component": "Column",
            "children": ["__layout__root__row0", "__layout__root__row1"],
        },
        {"id": "__layout__root__row0", "component": "Row", "children": ["a", "b"]},
        {"id": "__layout__root__row1", "component": "Row", "children": ["c", "d"]},
        text("a"),
        text("b"),
        text("c"),
        text("d"),
    ]
    result = classify(record(tmp_path, nodes, size=size), tmp_path)
    assert result["layout"] == expected


def test_full_regions_are_distinct_from_two_short_info_panels(tmp_path):
    nodes = [
        {"id": "root", "component": "Row", "children": ["left", "right"]},
        {
            "id": "left",
            "component": "Column",
            "children": ["a"],
            "styles": {"height": "matchParent", "backgroundColor": "#33000000"},
        },
        {
            "id": "right",
            "component": "Column",
            "children": ["b"],
            "styles": {"height": "matchParent", "backgroundColor": "#33000000"},
        },
        text("a"),
        text("b"),
    ]
    value = record(tmp_path, nodes, size="2x4")
    assert classify(value, tmp_path)["layout"] == "W-split-panels"
    nodes[1]["styles"]["height"] = 57
    nodes[2]["styles"]["height"] = 57
    value = record(tmp_path, nodes, size="2x4")
    assert classify(value, tmp_path)["layout"] is None


def action(identity, height=36):
    return {
        "id": identity,
        "component": "Row",
        "children": [],
        "onClick": [{"call": "opaque"}],
        "styles": {
            "height": height,
            "width": height if height == 40 else "matchParent",
            "borderRadius": 20,
            "backgroundColor": "#33000000",
        },
    }


@pytest.mark.parametrize(
    "layout",
    [
        "S-title-content",
        "S-title-content-action",
        "S-title-primary-secondary-action",
        "S-title-anchor",
        "S-title-dual-column-action",
        "S-content-dual-action",
        "S-center",
        "S-dual-info",
        "W-top-bottom",
        "W-content-side-slots",
    ],
)
def test_registered_source_shapes_cover_remaining_catalogue_branches(tmp_path, layout):
    nodes = [
        {"id": "root", "component": "Column", "children": ["title", "body"]},
        *title(),
        {"id": "body", "component": "Column", "children": []},
        text("value", 18),
    ]
    root, body = nodes[0], nodes[-2]
    if layout in {"S-title-content", "S-title-content-action"}:
        body["children"] = ["__layout__root__content"]
        nodes.append(
            {
                "id": "__layout__root__content",
                "component": "Column",
                "children": ["value"],
            }
        )
        if layout.endswith("-action"):
            body["children"].append("__layout__root__action")
            nodes.extend(
                [
                    {
                        "id": "__layout__root__action",
                        "component": "Column",
                        "children": ["go"],
                    },
                    action("go"),
                ]
            )
    elif layout == "S-title-primary-secondary-action":
        body["children"] = ["__layout__root__primary_support", "go"]
        nodes.extend(
            [
                {
                    "id": "__layout__root__primary_support",
                    "component": "Column",
                    "children": ["value"],
                },
                action("go"),
            ]
        )
    elif layout == "S-title-anchor":
        body["children"] = ["__layout__root__primary", "__layout__root__bottom"]
        nodes.extend(
            [
                {
                    "id": "__layout__root__primary",
                    "component": "Column",
                    "children": ["value"],
                },
                {
                    "id": "__layout__root__bottom",
                    "component": "Row",
                    "children": ["support", "__layout__root__action_slot"],
                },
                {
                    "id": "__layout__root__action_slot",
                    "component": "Stack",
                    "children": ["go"],
                },
                text("support"),
                action("go", 40),
            ]
        )
    elif layout == "S-title-dual-column-action":
        body["children"] = ["__layout__root__ratiorow0"]
        nodes.extend(
            [
                {
                    "id": "__layout__root__ratiorow0",
                    "component": "Row",
                    "children": ["p1", "p2"],
                },
                {"id": "p1", "component": "Progress"},
                {"id": "p2", "component": "Progress"},
            ]
        )
    elif layout == "S-content-dual-action":
        root["children"] = [
            "value",
            "__layout__root__action0",
            "__layout__root__action1",
        ]
        nodes.extend(
            [
                {
                    "id": "__layout__root__action0",
                    "component": "Column",
                    "children": ["go"],
                },
                {
                    "id": "__layout__root__action1",
                    "component": "Column",
                    "children": ["go2"],
                },
                action("go"),
                action("go2"),
            ]
        )
    elif layout == "S-center":
        root["children"] = ["value"]
        root["styles"] = {"alignItems": "center", "justifyContent": "center"}
        nodes[-1]["styles"]["fontSize"] = 48
    elif layout == "S-dual-info":
        root["children"] = ["a", "b"]
        for key in ("a", "b"):
            nodes.append(
                {
                    "id": key,
                    "component": "Column",
                    "styles": {"height": 63, "backgroundColor": "#33FFFFFF"},
                }
            )
    elif layout == "W-top-bottom":
        body["children"] = ["__layout__root__primary", "__layout__root__details"]
        nodes.extend(
            [
                {
                    "id": "__layout__root__primary",
                    "component": "Column",
                    "children": ["value"],
                },
                {"id": "__layout__root__details", "component": "Column"},
            ]
        )
    else:
        root.update(component="Row", children=["body", "__layout__root__slots"])
        body["children"] = ["value"]
        nodes.extend(
            [
                {
                    "id": "__layout__root__slots",
                    "component": "Column",
                    "children": ["a", "b"],
                },
                text("a"),
                text("b"),
            ]
        )
    size = "2x4" if layout.startswith("W-") else "2x2"
    result = classify(record(tmp_path, nodes, size=size), tmp_path)
    assert result["layout"] == layout


def test_domain_is_multilabel_from_input_and_ignores_gold_business_text(tmp_path):
    value = record(
        tmp_path,
        dual_content(),
        binding_ids=["GetPhoneBatteryInfo", "GetCalendarEvents"],
    )
    result = classify(value, tmp_path)
    assert result["domain"] == ["battery", "calendar"]
    assert result["domain_status"] == "classified"
    assert (
        result["evidence"]["domain_source"] == "input_view.candidateDataBindings only"
    )


def test_unknown_capability_is_not_guessed_from_name_substring(tmp_path):
    value = record(
        tmp_path, dual_content(), binding_ids=["ViewWeatherUnknown", "ViewWeather"]
    )
    result = classify(value, tmp_path)
    assert result["domain"] == ["weather"]
    assert result["domain_status"] == "partial_unknown"
    assert result["evidence"]["unknown_capability_ids"] == ["ViewWeatherUnknown"]


def test_no_data_candidates_is_not_guessed_from_query_or_event_id(tmp_path):
    value = record(tmp_path, dual_content())
    path = tmp_path / "input.json"
    path.write_text(
        json.dumps(
            {
                "userQuery": "weather",
                "candidateDataBindings": [],
                "candidateEventCandidates": [{"capabilityId": "event.open.weather"}],
            }
        ),
        "utf-8",
    )
    result = classify(value, tmp_path)
    assert result["domain"] == []
    assert result["domain_status"] == "no_data_candidates"


@pytest.mark.parametrize(
    "declaration",
    [
        {"dataCapabilityIds": ["ViewWeather"]},
        {"dataCapabilitySchemas": {"ViewWeather": {}}},
        {"dataCapabilities": [{"id": "ViewWeather"}]},
        {"dataCapabilityParams": {"ViewWeather": {}}},
        {"dataBindings": [{"id": "ViewWeather"}]},
        {"arguments": '{"candidateDataBindings":[{"capabilityId":"ViewWeather"}]}'},
    ],
)
@pytest.mark.parametrize("standard_candidates", [None, []])
def test_alternate_data_declarations_are_unresolved_without_inventing_domains(
    tmp_path, declaration, standard_candidates
):
    value = record(tmp_path, dual_content())
    view = dict(declaration)
    if standard_candidates is not None:
        view["candidateDataBindings"] = standard_candidates
    (tmp_path / "input.json").write_text(json.dumps(view), "utf-8")
    result = classify(value, tmp_path)
    assert result["domain"] == []
    assert result["domain_status"] == "schema_unresolved"
    assert result["layout"] == "S-title-dual-content"
    assert result["evidence"]["declaration_values_interpreted"] is False
    assert len(result["evidence"]["other_data_declarations"]) == 1


def test_raw_request_envelope_only_adds_schema_evidence_without_parsing_binding(
    tmp_path,
):
    value = record(tmp_path, dual_content())
    (tmp_path / "input.json").write_text('{"candidateDataBindings": []}', "utf-8")
    raw = tmp_path / "raw.json"
    raw.write_text(
        json.dumps(
            {"content": '```cardspec\n{"dataCapabilityIds":["GetCurrentTime"]}\n```'}
        ),
        "utf-8",
    )
    value["input_path"] = str(raw)
    before = raw.read_bytes()
    result = classify(value, tmp_path)
    assert result["domain_status"] == "schema_unresolved"
    assert result["domain"] == []
    assert result["evidence"]["other_data_declarations"] == [
        {"path": "raw_input.content.dataCapabilityIds", "declared_type": "list"}
    ]
    assert raw.read_bytes() == before


def test_action_arguments_and_empty_alternate_keys_do_not_imply_data(tmp_path):
    value = record(tmp_path, dual_content())
    view = {
        "candidateDataBindings": [],
        "dataCapabilityIds": [],
        "dataCapabilities": {},
        "candidateEventCandidates": [
            {"action": {"arguments": {"target": "somewhere"}}}
        ],
    }
    (tmp_path / "input.json").write_text(json.dumps(view), "utf-8")
    result = classify(value, tmp_path)
    assert result["domain_status"] == "no_data_candidates"
    assert result["evidence"]["other_data_declarations"] == []


def test_standard_data_classification_is_preserved_despite_alternate_declarations(
    tmp_path,
):
    value = record(tmp_path, dual_content())
    view = {
        "candidateDataBindings": [{"capabilityId": "ViewWeather"}],
        "dataCapabilityIds": ["GetCurrentTime"],
    }
    (tmp_path / "input.json").write_text(json.dumps(view), "utf-8")
    result = classify(value, tmp_path)
    assert result["domain_status"] == "classified"
    assert result["domain"] == ["weather"]
    assert result["evidence"]["data_capability_ids"] == ["ViewWeather"]
    assert result["evidence"]["other_data_declarations"]


def test_input_view_canonical_digest_and_file_digest_have_distinct_names(tmp_path):
    value = record(tmp_path, dual_content())
    value["input_view_sha256"] = "a" * 64
    result = classify(value, tmp_path)
    assert result["evidence"]["input_view_sha256"] == "a" * 64
    expected = hashlib.sha256((tmp_path / "input.json").read_bytes()).hexdigest()
    assert result["evidence"]["input_view_file_sha256"] == expected


def test_cycle_is_unresolved_not_product_failure_or_dropped_row(tmp_path):
    nodes = [{"id": "root", "component": "Column", "children": ["root"]}]
    result = classify(record(tmp_path, nodes), tmp_path)
    assert result["layout"] is None
    assert result["layout_status"] == "structure_unresolved"
    assert result["evidence"]["reason"].startswith("TREE_CYCLE")


def test_two_parallel_known_wrappers_are_ambiguous(tmp_path):
    nodes = [
        {
            "id": "root",
            "component": "Stack",
            "children": sorted(
                ["__post_theme_foreground", "__genui_render_component__root"]
            ),
        },
        {"id": "__post_theme_foreground", "component": "Column"},
        {"id": "__genui_render_component__root", "component": "Column"},
    ]
    result = classify(record(tmp_path, nodes), tmp_path)
    assert result["layout_status"] == "structure_unresolved"
    assert result["evidence"]["reason"].startswith("WRAPPER_AMBIGUOUS")


def test_cli_keeps_missing_and_excluded_records(tmp_path, monkeypatch):
    value = record(tmp_path, dual_content())
    excluded = dict(value, case_id="excluded", p1_status="excluded", a2ui_path=None)
    unknown = dict(value, case_id="unknown-size", size=None)
    source = tmp_path / "records.jsonl"
    content = "\n".join(json.dumps(item) for item in [value, excluded, unknown])
    source.write_text(content, "utf-8")
    output = tmp_path / "out"
    monkeypatch.setattr(
        sys, "argv", ["p4", "--records", str(source), "--output", str(output)]
    )
    main()
    rows = [
        json.loads(line)
        for line in (output / "records.jsonl").read_text("utf-8").splitlines()
    ]
    assert len(rows) == 3
    assert [row["case_id"] for row in rows] == [
        "opaque-example",
        "excluded",
        "unknown-size",
    ]
    assert rows[1]["layout_status"] == "unavailable"
    assert source.read_text("utf-8") == content
    assert all(row["evidence"]["forbidden_as_generation_or_p7_input"] for row in rows)
