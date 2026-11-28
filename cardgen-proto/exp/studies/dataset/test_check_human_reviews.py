"""仅合成人工导出合同；不代真人填写任何真实案例。"""

import copy
import hashlib

import pytest

from check_human_reviews import (
    UNKNOWN_LAYOUTS,
    check_reviews,
    cohens_kappa,
    context_from_inputs,
    unique_object,
)


def fixtures():
    samples = []
    records = []
    for index in range(50):
        identity = f"SYNTHETIC_{index:03}"
        samples.append({"case_id": identity})
        records.append(
            {
                "case_id": identity,
                "input_sha256": hashlib.sha256(identity.encode()).hexdigest(),
            }
        )
    catalogue = {"catalogue": [f"Layout{index:02}" for index in range(14)]}
    manifest = {"tree_sha256": "a" * 64}
    context = context_from_inputs(samples, records, manifest, catalogue)
    documents = []
    for suffix in ("a", "b"):
        mode = "p6-layout-" + suffix
        answers = []
        for index, record in enumerate(records):
            answers.append(
                {
                    **record,
                    "audit_mode": mode,
                    "manifest": context.manifest,
                    "human_layout": f"Layout{index % 2:02}",
                    "reviewer": "合成签名" + suffix,
                }
            )
        documents.append(
            {
                "version": "human-review-v1",
                "mode": mode,
                "manifest": context.manifest,
                "answers": answers,
            }
        )
    return context, documents[0], documents[1]


def error_codes(result):
    return {error["code"] for error in result["errors"]}


def test_valid_fifty_pair_documents_do_not_claim_human_phase_or_accuracy_completed():
    context, first, second = fixtures()
    result = check_reviews(first, second, context)
    assert result["documents_valid"] is True
    assert result["agreement"]["kappa"] == 1
    assert result["agreement"]["n"] == 50
    assert result["layout_agreement_pass"] is True
    assert result["p6_complete"] is False
    assert result["p4_accuracy"] == {
        "status": "PENDING_INDEPENDENT_ADJUDICATION",
        "value": None,
    }
    assert result["human_answers_generated"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", "human-review-v0"),
        ("mode", "p7"),
        ("manifest", "b" * 64),
    ],
)
def test_wrong_document_protocol_mode_or_manifest_blocks_agreement(field, value):
    context, first, second = fixtures()
    first[field] = value
    result = check_reviews(first, second, context)
    assert "DOCUMENT_FIELD_MISMATCH" in error_codes(result)
    assert result["agreement"] is None
    assert result["p6_complete"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("input_sha256", "b" * 64),
        ("audit_mode", "p6-layout-b"),
        ("manifest", "b" * 64),
    ],
)
def test_per_answer_hash_mode_or_manifest_mismatch_blocks(field, value):
    context, first, second = fixtures()
    first["answers"][0][field] = value
    result = check_reviews(first, second, context)
    assert "ANSWER_FIELD_MISMATCH" in error_codes(result)
    assert result["agreement"] is None


def test_missing_answer_and_duplicate_answer_are_not_fifty_complete_cases():
    context, first, second = fixtures()
    first["answers"].pop()
    second["answers"][-1] = copy.deepcopy(second["answers"][0])
    result = check_reviews(first, second, context)
    required = {"ANSWER_COUNT_MISMATCH", "CASE_SET_MISMATCH", "DUPLICATE_CASE_ID"}
    assert required <= error_codes(result)
    assert result["documents_valid"] is False
    assert result["agreement"] is None


@pytest.mark.parametrize("name", ["", "   ", None, 15])
def test_missing_nonempty_reviewer_name_blocks(name):
    context, first, second = fixtures()
    first["answers"][0]["reviewer"] = name
    result = check_reviews(first, second, context)
    assert "REVIEWER_MISSING" in error_codes(result)
    assert result["layout_agreement_pass"] is False


def test_each_file_requires_one_signature_and_two_files_require_different_people():
    context, first, second = fixtures()
    first["answers"][0]["reviewer"] = "另一个合成签名"
    result = check_reviews(first, second, context)
    assert "REVIEWER_NOT_SINGLE" in error_codes(result)
    _, first, second = fixtures()
    for answer in second["answers"]:
        answer["reviewer"] = "  合成签名a  "
    result = check_reviews(first, second, context)
    assert "SAME_REVIEWER" in error_codes(result)


@pytest.mark.parametrize("value", ["", None, "尚未审核", "InventedLayout"])
def test_unfilled_or_unrecognized_layout_is_not_complete(value):
    context, first, second = fixtures()
    second["answers"][0]["human_layout"] = value
    result = check_reviews(first, second, context)
    assert "LAYOUT_UNFILLED_OR_UNKNOWN" in error_codes(result)
    assert result["agreement"] is None


def test_unknown_categories_are_permitted_and_included_not_dropped_from_kappa():
    context, first, second = fixtures()
    unknown = sorted(UNKNOWN_LAYOUTS)
    for document in (first, second):
        for index, answer in enumerate(document["answers"]):
            answer["human_layout"] = unknown[index % len(unknown)]
    result = check_reviews(first, second, context)
    assert result["documents_valid"] is True
    assert result["agreement"]["n"] == 50
    assert result["agreement"]["included_labels"] == unknown
    assert result["agreement"]["kappa"] == 1


def test_perfect_expected_agreement_is_undefined_not_perfect_kappa():
    context, first, second = fixtures()
    for document in (first, second):
        for answer in document["answers"]:
            answer["human_layout"] = "无法判定"
    result = check_reviews(first, second, context)
    assert result["documents_valid"] is True
    assert result["agreement"]["observed_agreement"] == 1
    assert result["agreement"]["expected_agreement"] == 1
    assert result["agreement"]["kappa"] is None
    assert result["agreement"]["undefined_reason"] == "EXPECTED_AGREEMENT_EQUALS_ONE"
    assert result["layout_agreement_pass"] is False


def test_disagreement_is_not_accuracy_or_consensus():
    context, first, second = fixtures()
    for answer in second["answers"]:
        answer["human_layout"] = "无法判定"
    result = check_reviews(first, second, context)
    assert result["documents_valid"] is True
    assert result["agreement"]["kappa"] == 0
    assert result["layout_agreement_pass"] is False
    assert result["p4_accuracy"]["value"] is None


def test_pairing_uses_case_ids_not_export_order():
    context, first, second = fixtures()
    second["answers"].reverse()
    assert check_reviews(first, second, context)["agreement"]["kappa"] == 1


def test_missing_or_foreign_case_is_rejected_even_when_answer_count_is_fifty():
    context, first, second = fixtures()
    first["answers"][0]["case_id"] = "UNKNOWN_CASE"
    result = check_reviews(first, second, context)
    assert "CASE_ID_NOT_EXPECTED" in error_codes(result)
    assert "CASE_SET_MISMATCH" in error_codes(result)


@pytest.mark.parametrize("document", [None, [], "not-json-object"])
def test_non_object_document_is_blocked(document):
    context, _, second = fixtures()
    result = check_reviews(document, second, context)
    assert "DOCUMENT_NOT_OBJECT" in error_codes(result)
    assert result["agreement"] is None


def test_invalid_answer_types_are_blocked():
    context, first, second = fixtures()
    first["answers"][0] = "not-answer"
    result = check_reviews(first, second, context)
    assert "ANSWER_NOT_OBJECT" in error_codes(result)
    first["answers"] = {}
    assert "ANSWERS_NOT_LIST" in error_codes(check_reviews(first, second, context))


def test_expected_context_cannot_be_created_with_fewer_than_fifty_samples():
    with pytest.raises(ValueError, match="fifty"):
        context_from_inputs(
            [],
            [],
            {"tree_sha256": "a" * 64},
            {"catalogue": [f"Layout{index}" for index in range(14)]},
        )


@pytest.mark.parametrize("bad_manifest", [{}, {"tree_sha256": "not-a-hash"}, None])
def test_expected_manifest_must_be_a_real_sha256_shape(bad_manifest):
    with pytest.raises(ValueError, match="tree_sha256"):
        context_from_inputs(
            [],
            [],
            bad_manifest,
            {"catalogue": [f"Layout{index}" for index in range(14)]},
        )


@pytest.mark.parametrize(
    "bad_catalogue",
    [
        {},
        {"catalogue": ["Layout"] * 14},
        {"catalogue": ["Layout"] * 13},
    ],
)
def test_expected_fourteen_classes_must_be_unique_and_complete(bad_catalogue):
    with pytest.raises(ValueError):
        context_from_inputs([], [], {"tree_sha256": "a" * 64}, bad_catalogue)


@pytest.mark.parametrize(
    "records",
    [
        [{"case_id": "Synthetic", "input_sha256": "bad"}],
        [{"case_id": "Synthetic", "input_sha256": "a" * 64}] * 2,
    ],
)
def test_expected_inputs_cannot_silently_replace_invalid_or_repeated_ids(records):
    with pytest.raises(ValueError, match="repeated or SHA256 invalid"):
        context_from_inputs(
            [],
            records,
            {"tree_sha256": "a" * 64},
            {"catalogue": [f"Layout{index}" for index in range(14)]},
        )


def test_expected_sample_must_belong_to_input_records():
    with pytest.raises(ValueError, match="unknown or repeated"):
        context_from_inputs(
            [{"case_id": "Missing"}],
            [],
            {"tree_sha256": "a" * 64},
            {"catalogue": [f"Layout{index}" for index in range(14)]},
        )


def test_repeated_json_object_keys_are_not_silently_accepted():
    with pytest.raises(ValueError, match="duplicate JSON key"):
        unique_object([("manifest", "first"), ("manifest", "second")])


def test_kappa_handles_known_nonperfect_example_without_excluding_unknown_labels():
    result = cohens_kappa(["a", "a", "b", "b"], ["a", "a", "b", "无法判定"])
    assert result["n"] == 4
    assert result["observed_agreement"] == 0.75
    assert result["expected_agreement"] == 0.375
    assert result["kappa"] == 0.6
    assert result["threshold_pass"] is False


def test_kappa_threshold_is_exactly_inclusive_at_point_nine():
    left = ["a"] * 20 + ["b"] * 20
    right = list(left)
    right[0] = "b"
    right[20] = "a"
    result = cohens_kappa(left, right)
    assert result["kappa"] == 0.9
    assert result["threshold_pass"] is True


@pytest.mark.parametrize("left,right", [([], []), (["a"], [])])
def test_kappa_rejects_empty_or_unpaired_data(left, right):
    with pytest.raises(ValueError, match="nonempty paired"):
        cohens_kappa(left, right)
