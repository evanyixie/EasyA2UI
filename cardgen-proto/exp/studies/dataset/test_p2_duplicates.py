"""P2输入独立、全部保留、图分组与阈值敏感性的离线回归。"""

import copy
import hashlib
import json

import pytest

from p2_duplicates import (
    THRESHOLDS,
    audit_duplicates,
    canonical_json,
    capability_signature,
    digest,
    load_jsonl,
    main,
    normalize_query,
    prepare_records,
    similarity,
    unresolved_capability_fields,
    write_audit,
)


def record(identity, query, *, bindings=None):
    view = {
        "userQuery": query,
        "size": "2x2",
        "title": "输入标题",
        "description": "输入描述",
        "candidateDataBindings": bindings or [],
        "candidateEventCandidates": [],
        "candidateAssetIds": [],
    }
    return {
        "case_id": identity,
        "source": "online_updated",
        "query": query,
        "size": "2x2",
        "input_sha256": hashlib.sha256(identity.encode()).hexdigest(),
        "input_view_sha256": digest(view),
        "input": view,
    }


def binding(identity="GetSomething", arguments=None):
    return {
        "capabilityId": identity,
        "arguments": {} if arguments is None else arguments,
        "writeResultTo": "/data/source",
        "sampleValue": "不参与能力签名",
    }


def grouped_members(result, threshold="0.85"):
    return {frozenset(group["members"]) for group in result["groups"][threshold]}


def test_similarity_normalization_preserves_meaningful_characters():
    assert normalize_query("　Ａ  １２\n不显示\t日期 ") == "A 12 不显示 日期"
    assert normalize_query("北京日期2026") != normalize_query("上海日期2025")
    assert normalize_query("显示日期") != normalize_query("不显示日期")
    assert normalize_query("Ab") != normalize_query("ab")


def test_similarity_is_set_jaccard_of_normalized_character_bigrams():
    assert similarity("ABCD", "ABCE") == pytest.approx(0.5)
    assert similarity("ＡＢＣＤ", "ABCD") == 1
    assert similarity("ABAB", "AB") == pytest.approx(0.5)
    assert similarity("甲乙丙丁", "甲乙戊己") == pytest.approx(0.2)


@pytest.mark.parametrize(
    "left,right", [("", ""), (" ", "\n"), ("甲", "甲"), ("甲", "甲乙")]
)
def test_missing_short_queries_do_not_create_near_duplicate_evidence(left, right):
    assert similarity(left, right) == 0


def test_exact_input_uses_canonical_json_not_serialization_order():
    first = record("first", "相同输入")
    second = copy.deepcopy(first)
    second["case_id"] = "second"
    second["input"] = dict(reversed(list(first["input"].items())))
    result = audit_duplicates([first, second])
    assert grouped_members(result) == {frozenset({"first", "second"})}
    assert "exact_input" in result["pairs"][0]["base_reasons"]


def test_full_nonempty_capability_signature_ignores_write_location_and_sample_values():
    first = binding(arguments={"place": "甲", "options": [1, 2]})
    second = binding(arguments={"options": [1, 2], "place": "甲"})
    second.update(writeResultTo="/data/another", sampleValue="完全不同")
    first_key, _, _ = capability_signature({"candidateDataBindings": [first]})
    second_key, _, _ = capability_signature({"candidateDataBindings": [second]})
    assert first_key == second_key
    result = audit_duplicates(
        [
            record("one", "abcdefgh", bindings=[first]),
            record("two", "一二三四五六", bindings=[second]),
        ]
    )
    assert grouped_members(result) == {frozenset({"one", "two"})}
    assert result["pairs"][0]["base_reasons"] == ["same_capabilities_arguments"]


def test_capability_match_requires_complete_multiset_not_any_shared_capability():
    values = [
        record("one", "abcdefgh", bindings=[binding("A")]),
        record("two", "一二三四五六", bindings=[binding("A"), binding("B")]),
        record("three", "壹贰叁肆伍陆", bindings=[binding("A"), binding("A")]),
    ]
    result = audit_duplicates(values)
    assert len(grouped_members(result)) == 3
    assert not result["pairs"]


def test_argument_values_types_order_and_missing_state_are_not_collapsed():
    variants = [
        {"capabilityId": "A"},
        {"capabilityId": "A", "arguments": None},
        {"capabilityId": "A", "arguments": {}},
        {"capabilityId": "A", "arguments": False},
        {"capabilityId": "A", "arguments": 0},
        {"capabilityId": "A", "arguments": [1, 2]},
        {"capabilityId": "A", "arguments": [2, 1]},
    ]
    signatures = set()
    for value in variants:
        signature, _, _ = capability_signature({"candidateDataBindings": [value]})
        signatures.add(signature)
    assert len(signatures) == len(variants)


def test_empty_capability_sets_do_not_merge_all_static_inputs():
    result = audit_duplicates([record("a", "abcdefgh"), record("b", "一二三四五六")])
    assert grouped_members(result) == {frozenset({"a"}), frozenset({"b"})}
    assert all(item.capability_sha256 is None for item in result["records"])


def test_other_data_declarations_are_diagnosed_without_changing_canonical_signature():
    view = {"candidateDataBindings": [binding()]}
    before = capability_signature(view)
    view.update(
        dataCapabilityIds=["Other"],
        dataCapabilityParams={"Other": {"place": "甲"}},
        arguments='{"candidateDataBindings": [{"capabilityId": "Opaque"}]}',
    )
    assert capability_signature(view) == before
    assert unresolved_capability_fields(view) == [
        "arguments",
        "dataCapabilityIds",
        "dataCapabilityParams",
    ]
    value = record("one", "输入")
    value["input"] = view
    prepared = prepare_records([value])[0]
    assert "capability_schema_unresolved" in prepared.issues
    assert prepared.capability_sha256 == before[0]


def test_unknown_declarations_do_not_fabricate_signatures_or_merge_empty_canonical_inputs(
    tmp_path,
):
    values = [record("one", "abcdefgh"), record("two", "一二三四五六")]
    for value in values:
        value["input"]["dataCapabilities"] = ["Other"]
        value["input"]["dataCapabilitySchemas"] = {"opaque": True}
    result = audit_duplicates(values)
    assert len(grouped_members(result)) == 2
    assert all(item.capability_sha256 is None for item in result["records"])
    output = tmp_path / "p2"
    manifest = write_audit(
        result, output, input_path=tmp_path / "input", input_file_sha256="input"
    )
    assert manifest["capability_coverage"]["unresolved_declaration_records"] == 2
    review = load_jsonl(output / "capability_schema_unresolved.jsonl")
    assert {row["case_id"] for row in review} == {"one", "two"}
    assert all(row["canonical_signature_available"] is False for row in review)


def test_chain_components_are_visible_instead_of_claimed_pairwise_duplicates():
    first = "abcdefghijklmnopqrstu"
    middle = first + "v"
    last = middle[1:]
    result = audit_duplicates(
        [record("a", first), record("b", middle), record("c", last)]
    )
    assert similarity(first, middle) >= 0.95
    assert similarity(middle, last) >= 0.95
    assert similarity(first, last) < 0.95
    group = result["groups"]["0.95"][0]
    assert group["members"] == ["a", "b", "c"]
    assert group["transitive_only_pair_count"] == 1
    assert group["transitive_examples"][0]["first"] == "a"
    assert group["transitive_examples"][0]["second"] == "c"


def test_threshold_statistics_and_near_only_curve_are_all_reported():
    result = audit_duplicates([record("a", "abcdefghij"), record("b", "abcdefghik")])
    assert tuple(result["groups"]) == ("0.75", "0.85", "0.95")
    assert len(result["stability"]) == 2
    assert result["statistics"]["0.75"]["combined"]["group_count"] == 1
    assert result["statistics"]["0.95"]["combined"]["group_count"] == 2
    assert result["stability"][0]["changed_membership_records"] == 2


def test_fixed_capability_edges_do_not_hide_the_near_only_threshold_curve():
    result = audit_duplicates(
        [
            record("a", "abcdefghij", bindings=[binding()]),
            record("b", "abcdefghik", bindings=[binding()]),
        ]
    )
    assert all(
        stats["combined"]["group_count"] == 1 for stats in result["statistics"].values()
    )
    assert result["statistics"]["0.75"]["near_only"]["group_count"] == 1
    assert result["statistics"]["0.95"]["near_only"]["group_count"] == 2


def test_representative_is_hash_then_id_and_does_not_depend_on_input_order():
    first = record("z", "相同输入")
    second = record("a", "相同输入")
    first["input_sha256"] = "0" * 64
    second["input_sha256"] = "f" * 64
    one = audit_duplicates([first, second])
    two = audit_duplicates([second, first])
    assert one["groups"] == two["groups"]
    assert one["groups"]["0.85"][0]["representative_case_id"] == "z"


def test_prior_exposure_metadata_is_retained_but_does_not_change_grouping_or_representative():
    rows = [record("a", "相同输入"), record("b", "相同输入")]
    initial = audit_duplicates(rows)
    rows[0]["pre_exposed"] = True
    rows[1]["pre_exposed"] = False
    changed = audit_duplicates(rows)
    assert changed["groups"] == initial["groups"]
    assert changed["statistics"] == initial["statistics"]
    assert changed["records"][0].row["pre_exposed"] is True


def test_all_records_including_empty_queries_and_bad_capability_metadata_are_retained():
    rows = [
        record("good", "abcdefgh"),
        record("empty", ""),
        record("missing", None),
        record("bad_capability", "一二三四五六"),
    ]
    rows[-1]["input"]["candidateDataBindings"] = ["invalid"]
    before = copy.deepcopy(rows)
    result = audit_duplicates(rows)
    assert {item.case_id for item in result["records"]} == {
        row["case_id"] for row in rows
    }
    for groups in result["groups"].values():
        assert sum(group["size"] for group in groups) == len(rows)
    assert rows == before


def test_large_capability_groups_and_divergent_queries_are_exposed():
    rows = []
    for index in range(10):
        rows.append(record(str(index), chr(0x4E00 + index) * 5, bindings=[binding()]))
    result = audit_duplicates(rows)
    group = result["groups"]["0.85"][0]
    assert group["size"] == 10 and group["large_group"]
    assert group["heterogeneous_query_group"]
    assert group["minimum_query_similarity"] == 0


def test_answer_metadata_or_duplicate_identity_stops_audit_instead_of_leaking_or_dropping():
    value = record("one", "输入")
    value["gold_path"] = "must_not_be_read"
    with pytest.raises(ValueError, match="额外字段"):
        prepare_records([value])
    clean = record("one", "输入")
    with pytest.raises(ValueError, match="case_id重复"):
        prepare_records([clean, clean])


def test_jsonl_duplicate_keys_and_blank_rows_are_not_silently_repaired(tmp_path):
    path = tmp_path / "input.jsonl"
    path.write_text('{"case_id":"a","case_id":"b"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="重复JSON键"):
        load_jsonl(path)
    path.write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError, match="为空"):
        load_jsonl(path)


def test_cli_writes_complete_input_only_review_package_without_making_p5_decisions(
    tmp_path,
):
    source = tmp_path / "input.jsonl"
    output = tmp_path / "p2"
    rows = [record("one", "相同输入"), record("two", "相同输入"), record("blank", "")]
    source.write_text(
        "\n".join(canonical_json(row) for row in rows) + "\n", encoding="utf-8"
    )
    assert main(["--input", str(source), "--output", str(output)]) == 0
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["record_count"] == 3 and manifest["deleted_records"] == 0
    assert len(manifest["script_sha256"]) == 64
    assert manifest["thresholds"] == list(THRESHOLDS)
    assert manifest["draft_config"]["status"] == "pending_manual_review"
    assert manifest["draft_config"]["automatically_selected"] is False
    assert not manifest["answers_read"] and not manifest["p5_decision_made"]
    assert len(load_jsonl(output / "memberships.jsonl")) == 3
    assert len(load_jsonl(output / "manual_review/input_only_records.jsonl")) == 3
    decisions = (output / "manual_review/decisions_template.csv").read_text(
        encoding="utf-8-sig"
    )
    assert "reviewer_1,reviewer_2,decision,split_groups,reason" in decisions
    assert not any("split" in path.name for path in output.glob("*.json"))
    assert main(["--input", str(source), "--output", str(output)]) == 0


def test_output_does_not_overwrite_results_from_different_frozen_input(tmp_path):
    rows = [record("a", "输入")]
    result = audit_duplicates(rows)
    output = tmp_path / "p2"
    write_audit(
        result, output, input_path=tmp_path / "input.jsonl", input_file_sha256="first"
    )
    with pytest.raises(ValueError, match="不同冻结输入"):
        write_audit(
            result,
            output,
            input_path=tmp_path / "input.jsonl",
            input_file_sha256="changed",
        )
