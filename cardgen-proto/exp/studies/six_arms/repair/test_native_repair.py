"""共享原生出口的合成卡回归，无模型计划、业务答案及设备依赖。"""

import json
import unittest

import pytest

from . import native_repair as repairer


@pytest.fixture(scope="module", autouse=True)
def reference_dependencies():
    pytest.importorskip("PIL")
    try:
        repairer.dependency_files()
    except RuntimeError as exc:
        pytest.skip(str(exc))


def card(children, leaves, *, height=150, gap=0, data=None):
    root = {
        "id": "root",
        "component": "Column",
        "children": children,
        "itemMargin": gap,
        "styles": {"width": 150, "height": height, "padding": 8, "clip": True},
    }
    surface = {"surfaceId": "s"}
    records = [
        ("createSurface", {**surface, "catalogId": "ohos.a2ui.extended.catalog.form"}),
        ("updateComponents", {**surface, "components": [root, *leaves]}),
        ("updateDataModel", {**surface, "path": "/", "value": data or {}}),
    ]
    return b"\n".join(
        json.dumps({"version": "v0.9", key: val}).encode() for key, val in records
    )


def leaf(key, text, height=28):
    return {
        "id": key,
        "component": "Text",
        "content": text,
        "styles": {"width": 134, "height": height, "fontSize": 16, "maxLines": 1},
    }


class NativeRepairTests(unittest.TestCase):
    def test_good_raw_bytes_preserved(self):
        original = card(["a"], [leaf("a", {"path": "/a"})], data={"a": "晴"})
        output, receipt = repairer.repair(original)
        self.assertEqual(output, original)
        self.assertEqual((receipt["status"], receipt["rounds"]), ("no_change", []))

    def test_first_round_resolves_local_height_without_extra_input(self):
        original = card(["a"], [leaf("a", {"path": "/a"}, height=13)], data={"a": "晴"})
        output, receipt = repairer.repair(original)
        self.assertEqual(receipt["accepted_round"], 1)
        self.assertFalse(receipt["rounds"][0]["introduced_by_repair"])
        self.assertEqual(
            repairer.material(repairer.parse(original)),
            repairer.material(repairer.parse(output)),
        )
        self.assertEqual(
            repairer.parse(output)[1]["updateComponents"]["components"][1]["content"],
            {"path": "/a"},
        )

    def test_second_round_keeps_button_in_place_with_bound_label_and_action(self):
        text = leaf("a", "天气", height=20)
        button = leaf("go", "", height=36)
        button["component"] = "Button"
        button.pop("content")
        button["label"] = "{{ '查看' + ${/place} }}"
        button["onClick"] = [{"call": "clickToDeeplink", "args": {"uri": "weather"}}]
        original = card(["a", "go"], [text, button], gap=10, data={"place": "北京"})
        output, receipt = repairer.repair(original)
        self.assertEqual(receipt["accepted_round"], 2)
        self.assertIn("go", receipt["rounds"][0]["moved_previously_valid_boxes"])
        self.assertFalse(receipt["rounds"][1]["moved_previously_valid_boxes"])
        before, after = map(repairer.parse, (original, output))
        self.assertEqual(
            repairer.inspect(before)[1]["go"], repairer.inspect(after)[1]["go"]
        )
        self.assertEqual(after[1]["updateComponents"]["components"][2], button)

    def test_rollback_retains_every_byte_and_logs_introduced_defects(self):
        original = card(
            ["a", "b"], [leaf("a", "科学", 10), leaf("b", "读书", 28)], height=54
        )
        output, receipt = repairer.repair(original)
        self.assertEqual(output, original)
        self.assertEqual(receipt["status"], "unresolved")
        self.assertEqual(len(receipt["rounds"]), repairer.MAX_ROUNDS)
        self.assertTrue(any(r["introduced_by_repair"] for r in receipt["rounds"]))
        self.assertFalse(any(r["accepted"] for r in receipt["rounds"]))

    def test_unknown_missing_dangling_or_bad_native_fails_closed(self):
        for raw in [
            card(["a"], [leaf("a", {"path": "/missing"}, 10)]),
            card(["a"], [leaf("a", "{{ unsupported }}")]),
            card(["a", "missing"], [leaf("a", "晴")]),
            card(["a", "a"], [leaf("a", "晴")]),
            b"[]",
        ]:
            with self.subTest(raw=raw):
                output, receipt = repairer.repair(raw)
                self.assertEqual(output, raw)
                self.assertEqual(receipt["status"], "unsupported")
                self.assertIsNone(receipt["before"])
                self.assertIsNone(receipt["after"])
                self.assertFalse(receipt["rounds"])


if __name__ == "__main__":
    unittest.main()
