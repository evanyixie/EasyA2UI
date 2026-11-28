"""生成用于区分文字绑定和行对齐的四个合成 A2UI 输入。"""

import argparse
import copy
import json
from pathlib import Path

SURFACE = "surface_card"

DATA = {"data": {"probe": {"whole": "蓝莓 42", "first": "蓝莓", "second": "42"}}}

BIND = "{{ ${/data/probe/whole} }}"

COMPOUND = "{{ ${/data/probe/first} + ' ' + ${/data/probe/second} }}"

SETTINGS = {
    "template_top": (BIND, "top"),
    "object_top": ({"path": "/data/probe/whole"}, "top"),
    "compound_top": (COMPOUND, "top"),
    "template_start": (BIND, "start"),
}

def encode(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()

def fixture(content, align):
    def label(name, text, height, color):
        return {
            "id": name,
            "component": "Text",
            "content": text,
            "styles": {
                "width": 132,
                "height": height,
                "fontSize": 16,
                "fontWeight": 500,
                "fontColor": color,
                "maxLines": 1,
                "flexShrink": 0,
            },
        }

    components = [
        {
            "id": "root",
            "component": "Column",
            "children": ["heading", "probeRow"],
            "itemMargin": 8,
            "styles": {"width": 300, "height": 150, "padding": 12, "backgroundColor": "#FFFFFFFF"},
        },
        label("heading", "文字对照", 24, "#FF202020"),
        {
            "id": "probeRow",
            "component": "Row",
            "children": ["literal", "reference"],
            "itemMargin": 8,
            "styles": {
                "width": 276,
                "height": 72,
                "alignItems": align,
                "backgroundColor": "#FFE8F0F8",
            },
        },
        label("literal", "蓝莓 42", 40, "#FF293563"),
        label("reference", content, 24, "#FF11603B"),
    ]
    return [
        {
            "version": "v0.9",
            "createSurface": {"surfaceId": SURFACE, "catalogId": "ohos.a2ui.extended.catalog.form"},
        },
        {
            "version": "v0.9",
            "updateComponents": {"surfaceId": SURFACE, "root": "root", "components": components},
        },
        {
            "version": "v0.9",
            "updateDataModel": {"surfaceId": SURFACE, "path": "/", "value": copy.deepcopy(DATA)},
        },
    ]


def write_probes(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    for name, settings in SETTINGS.items():
        data = b"\n".join(map(encode, fixture(*settings))) + b"\n"
        (output / f"{name}.jsonl").write_bytes(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    write_probes(parser.parse_args().output)
