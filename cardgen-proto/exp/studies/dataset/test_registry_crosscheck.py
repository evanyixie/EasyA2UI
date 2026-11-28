"""仅合成材料；验证版本、相对字段、索引、JSON 类型及两个路径分母。"""

import json
from decimal import Decimal

import pytest

import registry_crosscheck as rc


def interval(name, app_min, app_max):
    return {
        "registryVersion": name,
        "appVersion": {"minInclusive": app_min, "maxExclusive": app_max},
        "romVersion": {"minInclusive": "6.0", "maxExclusive": "8.0"},
    }


RANGES = [interval("a", "1.2", "1.9"), interval("b", "1.9", "2")]


def leaf(value):
    return {"sampleValue": value}


def props(**fields):
    return {"type": "object", "properties": fields}


def test_version_mapping_exclusive_end_and_unknowns():
    assert rc.possible_scopes(
        {"prdVer": "V1.9", "romVersion": "ROM 7.0.123"}, RANGES
    ) == ("identified", ["b"])
    assert rc.possible_scopes({"appVersion": "1.2.0", "romVersion": "6"}, RANGES) == (
        "identified",
        ["a"],
    )
    assert rc.possible_scopes({"appVersion": "2", "romVersion": "7"}, RANGES) == (
        "outside_approved_ranges",
        [],
    )
    assert rc.possible_scopes({"romVersion": "device 6.1.123"}, RANGES) == (
        "partial_version_metadata",
        ["a", "b"],
    )
    assert rc.possible_scopes({}, RANGES) == ("absent_version_metadata", ["a", "b"])
    assert rc.possible_scopes({"romVersion": None}, RANGES) == (
        "invalid_version_metadata",
        [],
    )
    assert rc.possible_scopes({"appVersion": "1.2", "prdVer": "1.9"}, RANGES) == (
        "invalid_version_metadata",
        [],
    )


@pytest.mark.parametrize("value", [None, "", [], {}, 0, False])
def test_explicit_empty_is_available(value):
    assert rc.example(props(a=leaf(value)), ("a",)) == ("available", value)
    assert rc.example(props(a={}), ("a",))[1] is rc.MISSING


def test_types_and_numeric_precision():
    assert not rc.equal(0, False)
    assert not rc.equal([{"v": True}], [{"v": 1}])
    assert not rc.equal([], {})
    assert not rc.equal("", None)
    assert rc.equal(1, Decimal("1.0"))
    assert not rc.equal(rc.parse("1.000000000000000001"), 1)


def test_array_needs_real_sample_at_index():
    schema = props(arr={"type": "array", "items": props(x=leaf("fake"))})
    for i in ("0", "1", "01"):
        assert rc.example(schema, ("arr", i, "x"))[1] is rc.MISSING
    array = props(arr=leaf([{"x": None}]))
    assert rc.example(array, ("arr", "0", "x")) == ("available", None)
    assert rc.example(array, ("arr", "1", "x"))[0] == "concrete_index_absent"
    assert rc.example(array, ("arr", "00", "x"))[0] == "concrete_index_absent"
    assert rc.example(props(arr=leaf([])), ("arr", "0"))[1] is rc.MISSING
    assert rc.example(props(arr=leaf([])), ("arr",)) == ("available", [])


def test_strict_relative_fields_do_not_match_leaf_or_wrong_capability():
    cap = {"a": {"one": props(x=leaf("me"), nested=props(x=leaf("other")))}}
    raw = {
        "candidateDataBindings": [
            {
                "writeResultTo": "/data",
                "candidateOutputFields": ["/nested/x", "/a~1b", "/n~0"],
                "capabilityId": "two",
            }
        ]
    }
    declared = rc.declarations(raw)
    assert set(declared) == {("data", "nested", "x"), ("data", "a/b"), ("data", "n~")}
    assert (
        rc.compare_path("me", declared[("data", "x")], ["a"], cap)
        == "no_exact_candidate_declaration"
    )
    assert (
        rc.compare_path("other", declared[("data", "nested", "x")], ["a"], cap)
        == "registry_capability_absent"
    )
    refs = [("one", ("nested", "x"))]
    assert rc.compare_path("me", refs, ["a"], cap) == "different_example"
    assert (
        rc.compare_path("other", refs + refs, ["a"], cap)
        == "ambiguous_candidate_declaration"
    )
    with pytest.raises(ValueError):
        rc.tokens("/invalid~9")


def test_two_ranges_require_same_value_and_json_type():
    decl = [("one", ("x",))]
    registry = {"a": {"one": props(x=leaf(False))}, "b": {"one": props(x=leaf(0))}}
    assert (
        rc.compare_path(False, decl, ["a", "b"], registry)
        == "registry_versions_disagree"
    )
    assert rc.compare_path(0, decl, ["a"], registry) == "different_example"
    assert rc.compare_path(0, decl, [], registry) == "no_supported_registry_scope"
    assert rc.compare_path(False, decl, ["a"], registry) == "same_example"


def test_counts_keep_two_denominators_and_export_no_case_or_values():
    tid = "private-test-id"
    value = "private-test-value"
    req = {
        tid: {
            "original_request": {
                "romVersion": "7",
                "size": "small",
                "candidateDataBindings": [
                    {
                        "writeResultTo": "/secretbase",
                        "candidateOutputFields": ["/x", "/y"],
                        "capabilityId": "one",
                    }
                ],
            }
        }
    }
    contract = {
        "size": "small",
        "binding_samples": {"/secretbase/x": value, "/secretbase/y": None},
        "content_groups": [
            {
                "selected_value_sources": [
                    {"bindings": [{"path": "/secretbase/x", "sample_value": value}]}
                ]
            }
        ],
        "semantic_units": [{"take": {"path": "/secretbase/x"}}],
    }
    schema = props(x=leaf(value), y=leaf(0))
    registry = {"a": {"one": schema}, "b": {"one": schema}}
    result = rc.aggregate(req, {tid: contract}, RANGES, registry, 1)
    assert result["frozen_binding_samples"]["paths"] == {
        "same_example": 1,
        "different_example": 1,
    }
    assert result["frozen_binding_samples"]["frozen_empty_values"] == {"NoneType": 1}
    assert result["distinct_paths_explicitly_referenced_in_groups_or_semantic_units"][
        "paths"
    ] == {"same_example": 1}
    assert result["actual_same_task_first_frame_agreement"] is None
    assert all(
        secret not in json.dumps(result) for secret in (value, tid, "secretbase")
    )
    contract["content_groups"][0]["selected_value_sources"][0]["bindings"][0][
        "sample_value"
    ] = False
    contract["semantic_units"].append({"take": {"path": "/secretbase/missing"}})
    changed = rc.aggregate(req, {tid: contract}, RANGES, registry, 1)
    assert changed["distinct_paths_explicitly_referenced_in_groups_or_semantic_units"][
        "paths"
    ] == {"selected_value_conflict_in_release": 1, "no_frozen_sample": 1}
    with pytest.raises(ValueError):
        rc.aggregate(req, {}, RANGES, registry, 1)


def test_input_hash_anchor_and_strict_json(tmp_path):
    file = tmp_path / "fixture.json"
    file.write_bytes(b'{"v":null}')
    with pytest.raises(ValueError):
        rc.verified_file(file, "0" * 64)
    with pytest.raises(ValueError):
        rc.rows(b'{"task_id":"demo"}\n{"task_id":"demo"}')
    with pytest.raises(ValueError):
        rc.parse(b'{"v":0,"v":false}')
