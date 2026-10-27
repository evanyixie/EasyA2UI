"""从本地 asset-library.md 解析生成 registry/assets.json。

源文件：`ux-spec/asset-library.md`（设计资产清单规范，随项目维护，不依赖外部项目）。
src 一律只存**文件名**（前缀由 src/paths.py 统一拼，不在此处决定目录）。
资产清单更新时重跑本脚本。
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent          # cardgen-proto/
MD = HERE / "ux-spec" / "asset-library.md"
OUT = HERE / "registry" / "assets.json"
MEDIA_DIR = Path(r"F:\playground\workbuddy\nextgenui\cardgen-proto\resources\media")

KEEP_COLOR_MARKS = ("保留原色", "不可染色", "禁止染色", "多色", "渐变", "品牌")


def parse_rows(text: str):
    rows = []
    for m in re.finditer(r"\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|", text):
        src, desc = m.group(1), m.group(2)
        rows.append((src, desc))
    return rows


def main():
    text = MD.read_text(encoding="utf-8")
    seen, assets = set(), []
    for src, desc in parse_rows(text):
        name = src.rsplit("/", 1)[-1]
        if name in seen:
            continue
        if not (MEDIA_DIR / name).exists():
            continue
        seen.add(name)
        new_src = src.rsplit("/", 1)[-1]   # 只留文件名，前缀交给 src/paths.py
        dyeable = not any(k in desc for k in KEEP_COLOR_MARKS)
        assets.append({"src": new_src, "description": desc, "dyeable": dyeable})
    assets.sort(key=lambda a: a["src"])
    out = {
        "comment": "端侧素材库（复制自 CreateMyCard resources/base/media）。src 只存文件名。"
                   "dyeable=false 的素材不得写 fillColor；图标默认 20x20vp、objectFit contain。",
        "icon_spec": {"width": 20, "height": 20, "objectFit": "contain"},
        "max_icons_2x2": 2,
        "assets": assets,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"assets.json 生成完成：{len(assets)} 项 -> {OUT}")
    missing = [p.name for p in MEDIA_DIR.iterdir() if p.suffix in (".svg", ".png")
               and p.name not in seen]
    print(f"媒体目录中未入清单的文件 {len(missing)} 个（资源目录共 "
          f"{len(list(MEDIA_DIR.iterdir()))} 个文件）")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
