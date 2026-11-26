"""固定内容审核汇总的防误标/防丢引用测试，不评判UI效果。"""

import copy
import unittest

from semantic_contract import contract, references, validate


def fixture():
    packet = {
        "case_id": "QTEST",
        "task_id": "T-test",
        "size": "2x4",
        "D": 2,
        "A": 1,
        "items": [
            {
                "fact_id": "fact_1",
                "count": 2,
                "sources": [
                    {
                        "type": "bound_text",
                        "content": "{{ ${/data/date} + ' ' + ${/data/time} }}",
                        "bindings": [
                            {"path": "/data/date", "sample_value": "08-06"},
                            {"path": "/data/time", "sample_value": "14:00"},
                        ],
                    }
                ],
            }
        ],
        "actions": [
            {
                "action_id": "action_1",
                "caption": "详情",
                "handlers": [
                    {"call": "clickToIntent", "args": {"entityId": "{{ ${/data/id} }}"}}
                ],
            }
        ],
        "original_request": {"userQuery": "显示日期和时间，红色背景"},
        "supporting_text": [{"content": "当前日期", "counted_in_D": False}],
        "private_source_evidence": {"original_graphic_evidence": []},
        "private_original_compacts": [
            {
                "rows": [
                    ["root", "Layout", {"layout": "W-test"}],
                    ["/data/date", "08-06"],
                    ["/data/time", "14:00"],
                    ["/data/id", "id-1"],
                    ["/data/unused", "不得进入固定输入"],
                ]
            }
        ],
    }
    review = {
        "case_id": "QTEST",
        "status": "clear_ai",
        "entities": [
            {
                "id": "e1",
                "name": "当前日期与时间",
                "kind": "context",
                "evidence": "同一data对象",
            }
        ],
        "atoms": [
            {
                "parent": "fact_1",
                "entity": "e1",
                "role": "primary",
                "take": {"path": "/data/date"},
            },
            {
                "parent": "fact_1",
                "entity": "e1",
                "role": "secondary",
                "take": {"path": "/data/time"},
            },
        ],
        "relations": [],
        "actions": [
            {
                "action_id": "action_1",
                "owners": ["e1"],
                "scope": "entity",
                "interaction": "record_click",
                "evidence": "原记录点击id",
            }
        ],
        "preferences": [{"kind": "style", "quote": "红色背景"}],
        "issues": [],
        "review_note": "逐字段固定，未换布局",
        "human_confirmed": False,
        "ready_for_experiment": False,
    }
    return packet, review


class SemanticAuditTests(unittest.TestCase):
    def test_complete_audit_can_remain_unaccepted(self):
        packet, review = fixture()
        self.assertEqual(validate(packet, review), [])
        result = contract(packet, review)
        self.assertFalse(result["human_confirmed"])
        self.assertFalse(result["ready_for_experiment"])

    def test_cannot_claim_human_or_experiment_acceptance(self):
        packet, review = fixture()
        review["human_confirmed"] = True
        self.assertIn("unearned_acceptance", validate(packet, review))

    def test_deleted_or_duplicate_count_is_rejected(self):
        packet, review = fixture()
        review["atoms"].pop()
        errors = validate(packet, review)
        self.assertIn("D_or_parent_count_changed", errors)
        self.assertIn("selected_binding_coverage", errors)

    def test_same_D_but_missing_other_binding_is_rejected(self):
        packet, review = fixture()
        review["atoms"][1]["take"] = {"path": "/data/date"}
        self.assertIn("selected_binding_coverage", validate(packet, review))

    def test_unselected_reference_cannot_be_added(self):
        packet, review = fixture()
        review["atoms"][1]["take"] = {"path": "/data/unselected"}
        self.assertIn("path_not_in_parent", validate(packet, review))

    def test_compound_all_not_silently_marked_resolved(self):
        packet, review = fixture()
        review["atoms"] = [
            {
                "parent": "fact_1",
                "entity": "e1",
                "role": "mixed",
                "take": "all",
                "count": 2,
            }
        ]
        self.assertIn("composite_all_claimed_resolved", validate(packet, review))
        review["status"] = "needs_human"
        self.assertEqual(validate(packet, review), [])

    def test_bound_expression_does_not_become_static_literal(self):
        packet, review = fixture()
        packet["D"] = packet["items"][0]["count"] = 1
        expr = packet["items"][0]["sources"][0]["content"]
        review["atoms"] = [
            {
                "parent": "fact_1",
                "entity": "e1",
                "role": "primary",
                "take": {"text": expr},
            }
        ]
        self.assertEqual(validate(packet, review), [])
        result = contract(packet, review)
        self.assertEqual(
            result["content_groups"][0]["selected_value_sources"][0]["type"],
            "bound_text",
        )
        self.assertEqual(
            result["content_groups"][0]["selected_value_sources"][0]["content"], expr
        )
        self.assertEqual(references(expr), {"/data/date", "/data/time"})

    def test_source_graphic_reference_must_be_retained(self):
        packet, review = fixture()
        packet["D"] += 1
        packet["items"].append(
            {
                "fact_id": "fact_2",
                "count": 1,
                "sources": [
                    {"type": "bound_graphic", "binding_paths": ["/data/progress"]}
                ],
            }
        )
        review["atoms"].append(
            {"parent": "fact_2", "entity": "e1", "role": "secondary", "take": "all"}
        )
        self.assertEqual(validate(packet, review), [])

    def test_original_handlers_and_interaction_are_preserved(self):
        packet, review = fixture()
        result = contract(packet, review)
        self.assertEqual(
            result["actions"][0]["handlers"], packet["actions"][0]["handlers"]
        )
        self.assertEqual(result["actions"][0]["interaction"], "record_click")
        self.assertEqual(result["binding_samples"]["/data/id"], "id-1")
        review["actions"][0]["handlers"] = []
        self.assertIn("review_must_not_rewrite_handler", validate(packet, review))

    def test_no_unselected_values_or_geometry_exported(self):
        packet, review = fixture()
        result = contract(packet, review)
        self.assertNotIn("/data/unused", result["binding_samples"])
        self.assertNotIn("private_original_compacts", result)
        self.assertNotIn("case_id", result)
        self.assertNotIn("layout", result)

    def test_unknown_owner_or_relation_is_rejected(self):
        packet, review = fixture()
        review["actions"][0]["owners"] = ["unknown"]
        review["relations"] = [
            {"type": "peer", "from": "e1", "to": "unknown", "evidence": "无来源"}
        ]
        errors = validate(packet, review)
        self.assertIn("action_owner_unknown", errors)
        self.assertIn("relation_entity_unknown", errors)

    def test_preference_must_be_verbatim(self):
        packet, review = fixture()
        review["preferences"][0]["quote"] = "蓝色背景"
        self.assertIn("preference_not_source_quote", validate(packet, review))

    def test_contract_does_not_mutate_source(self):
        packet, review = fixture()
        frozen = copy.deepcopy(packet)
        result = contract(packet, review)
        result["actions"][0]["handlers"].clear()
        result["content_groups"][0]["selected_value_sources"].clear()
        self.assertEqual(packet, frozen)

    def test_alias_sample_conflict_cannot_be_silently_overwritten(self):
        packet, review = fixture()
        packet["private_original_compacts"].append({"rows": [["/data/date", "12-31"]]})
        with self.assertRaisesRegex(ValueError, "别名"):
            contract(packet, review)


if __name__ == "__main__":
    unittest.main()
