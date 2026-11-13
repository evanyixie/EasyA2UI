"""资源路径的架构检查（4 项断言）。

目的：让"路径前缀只允许出现在 `src/paths.py`"这条约定**可执行**——
任何人以后在 rules 里写死 `resources/xxx/` 前缀、或挪目录忘了改常量，
这里会先红。

    python tests/test_paths.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.paths import MEDIA_DIR, MEDIA_PREFIX, media_path, media_src  # noqa: E402

ok = True


def case(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print(f"{'✅' if cond else '❌'} {name}" + (f"  {detail}" if detail and not cond else ""))


assets = json.loads((ROOT / "rules/assets.json").read_text(encoding="utf-8"))["assets"]
icons = json.loads((ROOT / "rules/icons.json").read_text(encoding="utf-8"))
icon_names = (set(icons["header_icon_by_domain"].values())
              | {src for _, src in icons["action_icon_by_keyword"]}
              | {icons["default_action_icon"], icons["default_header_icon"]})

# 1) 目录存在且非空
case("资源目录存在", MEDIA_DIR.is_dir(), str(MEDIA_DIR))
case("资源目录非空", len(list(MEDIA_DIR.glob("*"))) > 0, str(MEDIA_DIR))

# 2) rules 里不得出现路径分隔符（前缀只属于 paths.py）
bad_assets = [a["src"] for a in assets if "/" in a["src"]]
case("assets.json 只登记文件名", not bad_assets, str(bad_assets[:3]))
bad_icons = [n for n in icon_names if "/" in n]
case("icons.json 只登记文件名", not bad_icons, str(bad_icons[:3]))

# 3) 登记的每个文件都真实存在
missing = [a["src"] for a in assets if not media_path(a["src"]).exists()]
case("白名单文件全部存在", not missing, str(missing[:3]))
missing_icon = [n for n in icon_names if not media_path(n).exists()]
case("图标文件全部存在", not missing_icon, str(missing_icon[:3]))

# 4) 拼出来的 src 前缀正确，且图标必须在白名单内
case("media_src 前缀正确", media_src("a.svg") == f"{MEDIA_PREFIX}/a.svg", media_src("a.svg"))
case("传入旧路径也能归一", media_src("resources/media/a.svg") == f"{MEDIA_PREFIX}/a.svg",
     media_src("resources/media/a.svg"))
whitelist = {a["src"] for a in assets}
not_listed = sorted(icon_names - whitelist)
case("图标都在素材白名单内", not not_listed, str(not_listed[:3]))

print("\n== 路径检查 %s ==" % ("通过" if ok else "失败"))
sys.exit(0 if ok else 1)
