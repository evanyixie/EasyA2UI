import copy
import unittest

import emit_fidelity as e


def fixture():
    h = {"call": "show", "args": {"tab": 2}}
    s = {"candidate_actions": [{"id": "act", "handler": h}], "sample_data": {"g": {"x": 7}}}
    p = {"title": "报读", "items": [{"id": "t", "text": "7", "label": "实测", "unit": "℃", "path": "/g/x"}],
         "actions": [{"id": "act", "label": "查看"}]}
    ls = {"width": 100, "height": 20, "fontColor": "#FF112233"}
    nodes = [{"kind": k, "ref": r, "style": ls} for k, r in (("text", "title"), ("text", "t"), ("button", "act"))]
    th = {"root": {"kind": "column", "style": {"width": 150, "height": 150, "itemMargin": 5}, "children": nodes}}
    c = [{"component": "Button", "id": "btn", "styles": dict(ls), "label": "查看", "onClick": [h]},
         {"component": "Text", "id": "r", "styles": {**ls, "fontColor": "#112233"}, "content": "报读"},
         {"component": "Column", "id": "root", "styles": {"width": 150.0, "height": 150},
          "itemMargin": 5, "children": ["r", "b", "btn"]},
         {"component": "Text", "id": "b", "styles": dict(ls), "content": '{{"实测"+" "+${/g/x}+"℃"}}'}]
    card = [{}, {"updateComponents": {"components": c}}, {"updateDataModel": {"path": "/g", "value": {"x": 7}}}]
    return p, th, card, s


class FidelityTest(unittest.TestCase):
    def test_equivalent_encoded_values(self):
        result = e.audit(*fixture())
        self.assertEqual(result["status"], "matched", result)
        self.assertTrue(all(v == "matched" for v in result["dimensions"].values()))
        self.assertEqual(e.tokens("{{'实测 ' + ${/g/x} + '℃'}}"), e.tokens('{{"实测 " + ${/g/x} + "℃"}}'))

    def test_changed_binding_style_handler_and_order(self):
        p, th, card, s = fixture()
        card = copy.deepcopy(card)
        c = card[1]["updateComponents"]["components"]
        c[0]["onClick"][0]["args"]["tab"] = 3
        c[3]["content"] = "实测 7℃"
        c[3]["styles"]["fontColor"] = "#FF000000"
        c[3]["styles"]["height"] = 1
        card[2]["updateDataModel"]["value"]["x"] = 8
        result = e.audit(p, th, card, s)
        for section in ("data", "theme", "actions", "geometry", "bindings"):
            self.assertEqual(result["dimensions"][section], "different")
        _, _, swapped, _ = fixture()
        swapped[1]["updateComponents"]["components"][2]["children"] = ["b", "r", "btn"]
        self.assertEqual(e.audit(p, th, swapped, s)["dimensions"]["order"], "different")

    def test_wrapper_semantics_and_unknown_layout(self):
        p, th, card, s = fixture()
        comps = card[1]["updateComponents"]["components"]
        comps[2]["children"][1] = "group"
        comps[3]["content"] = {"path": "/g/x"}
        comps.extend([{"component": "Row", "id": "group", "children": ["l", "b", "u"]},
                      {"component": "Text", "id": "l", "content": "实测 "},
                      {"component": "Text", "id": "u", "content": "℃"}])
        result = e.audit(p, th, card, s)
        self.assertEqual(result["dimensions"]["text"], "matched")
        self.assertEqual(result["dimensions"]["bindings"], "matched")
        self.assertEqual(result["dimensions"]["geometry"], "unknown")
        self.assertEqual(result["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
