import json
import unittest
from copy import deepcopy

from harness_v2 import model_stages as m


class ModelContractTest(unittest.TestCase):
    def setUp(self):
        self.source = deepcopy(m._EXAMPLE_SOURCE)
        self.content = deepcopy(m._EXAMPLE_CONTENT)
        self.structure = deepcopy(m._EXAMPLE_STRUCTURE)
        self.geometry = deepcopy(m._EXAMPLE_GEOMETRY)
        self.theme = deepcopy(m._EXAMPLE_THEME)

    def parse(self, stage, value, prior=None):
        return m.parse_output(stage, json.dumps(value), self.source, self.content, prior)

    def test_shared_example_and_all_stages(self):
        for phase, value, prior in (("content", self.content, None), ("structure", self.structure, None),
                                   ("geometry", self.geometry, self.structure), ("theme", self.theme, self.geometry)):
            self.assertEqual(self.parse(phase, value, prior), value)
        for phase in m.STAGES:
            messages = m.build_messages(phase, self.source, self.content, self.theme)
            self.assertIn(m._example_native(), messages[0]["content"])
            self.assertIn(m._json(self.source), messages[1]["content"])
        for phase in m.NATIVE:
            self.assertEqual(len(m.parse_output(phase, m._example_native(), self.source)), 3)

    def test_stage_responsibilities(self):
        self.structure["root"]["style"] = {"width": 150}
        with self.assertRaises(m.ProtocolError):
            self.parse("structure", self.structure)
        self.structure["root"].pop("style")
        self.geometry["root"]["style"]["fontColor"] = "#FFFFFF"
        with self.assertRaises(m.ProtocolError):
            self.parse("geometry", self.geometry, self.structure)
        self.geometry["root"]["style"].pop("fontColor")
        self.theme["root"]["style"]["width"] = 300
        with self.assertRaises(m.ProtocolError):
            self.parse("theme", self.theme, self.geometry)

    def test_grounding(self):
        item = self.content["items"][0]
        for replacement in ({"path": "/elsewhere"}, {"text": "118℃"}, {"wrong": 4}):
            with self.subTest(replacement), self.assertRaises(m.ProtocolError):
                plan = deepcopy(self.content)
                plan["items"][0].update(replacement)
                self.parse("content", plan)
        item.pop("path")
        with self.assertRaises(m.ProtocolError):
            self.parse("content", self.content)
        item["text"] = "庭院温度"
        self.parse("content", self.content)
        self.content["actions"][0]["handler"] = {"call": "openLog", "args": {"tampered": True}}
        with self.assertRaises(m.ProtocolError):
            self.parse("content", self.content)

    def test_caller_size_and_tree_are_preserved(self):
        self.geometry["root"]["style"]["width"] = 300
        with self.assertRaises(m.ProtocolError):
            self.parse("geometry", self.geometry, self.structure)
        self.geometry["root"]["style"]["width"] = 150
        self.geometry["root"]["children"].reverse()
        with self.assertRaises(m.ProtocolError):
            self.parse("geometry", self.geometry, self.structure)
        self.structure["root"]["children"][0]["ref"] = "v"
        with self.assertRaises(m.ProtocolError):
            self.parse("structure", self.structure)

    def test_no_salvage_of_malformed_output(self):
        for bad in ("{}", "```json\n" + m._example_native() + "\n```",
                    "[" + m._example_native().replace("\n", ",") + "]"):
            with self.assertRaises(m.ProtocolError):
                m.parse_output("one_shot", bad, self.source)
        for bad in ('{"a":1,"a":2}', '{"a":NaN}'):
            with self.assertRaises(m.ProtocolError):
                m.parse_output("content", bad, self.source)


if __name__ == "__main__":
    unittest.main()
