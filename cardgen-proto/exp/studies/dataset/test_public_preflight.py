"""仅使用合成输入测试两个历史投影及全字段匹配。"""

import json

import pytest

from public_preflight import aggregate, legacy_view


def test_legacy_projections_preserve_outer_fields_and_business_conflicts():
    inner = {"userQuery": "合成请求", "size": "s", "romVersion": None}
    card = {
        "content": inner,
        "size": "other",
        "extraCapability": [],
        "utterance": {"original": "合成原文"},
        "session": {"ignored": 6},
    }
    view, identity = legacy_view(card)
    assert view == {**inner, "extraCapability": [], "originalQuery": "合成原文"}
    assert identity == legacy_view({**card, "session": {}})[1]
    assert identity != legacy_view({**card, "size": "different"})[1]
    requests = [view, {k: v for k, v in view.items() if k != "romVersion"}]
    revision = [{"content": {"userQuery": "其他"}}]
    stats = aggregate(requests, [card, {**card, "size": "different"}], revision)
    assert stats["multiple_distinct_compatible_business_contents"] == 1
    assert stats["no_compatible_business_content"] == 1


def test_incremental_projection_parses_string_and_keeps_types_and_array_order():
    request = {"field": [True, 1]}
    revision = [{"content": json.dumps(request), "utterance": {"original": "外层"}}]
    stats = aggregate(
        [request, {"field": [1, True]}, {"field": [1, 1]}],
        [{"content": {"field": [0]}}],
        revision,
    )
    assert stats["exactly_one_distinct_compatible_business_content"] == 1
    assert stats["no_compatible_business_content"] == 2
    assert stats["requests_matching_incremental_projection"] == 1


def test_incremental_unknown_whitelist_membership_cannot_be_guessed():
    request = {"field": 3}
    with pytest.raises(ValueError, match="private_whitelist_required"):
        aggregate(
            [request], [{"content": request}], [{"content": {**request, "unknown": 1}}]
        )
    stats = aggregate(
        [request], [{"content": request}], [{"content": {"field": 4, "unknown": 1}}]
    )
    assert stats["exactly_one_distinct_compatible_business_content"] == 1


def test_deduplication_across_files_and_candidate_path_counts():
    request = {
        "candidateDataBindings": [
            {"writeResultTo": "/data", "candidateOutputFields": ["a", "a", "b", "c/0"]},
        ],
        "data": {"a": None, "c": []},
    }
    card = {"content": request}
    stats = aggregate([request], [card, card], [card])
    assert stats["distinct_business_contents_in_both_inventories"] == 1
    assert stats["exactly_one_distinct_compatible_business_content"] == 1
    assert stats["candidate_paths_declared_per_request_deduplicated"] == 3
    assert (
        stats[
            "candidate_paths_with_same_direct_value_in_all_compatible_business_objects"
        ]
        == 1
    )
    assert stats["runtime_first_frame_verified"] is None


def test_full_projection_does_not_drop_unseen_outer_business_field():
    retained = {"field": 0, "anotherField": {}}
    basic = {"field": 0}
    stats = aggregate(
        [basic],
        [{"content": retained}],
        [{"content": {"field": 1}}],
    )
    assert stats["no_compatible_business_content"] == 1
