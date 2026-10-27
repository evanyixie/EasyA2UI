"""P6 主题装配：整条流水线中唯一处理主题的环节。

职责（只碰颜色/背景/透明度，禁止改几何、结构、行数、内容）：
  1. 选主题：按主题目录（registry/themes.json）的 priority 链执行——
     M1 用户偏好 > domain 映射 > 默认；
  2. 解析色板：渐变 / 色彩角色 / 白背板（按尺寸）落成具体值，写入 ir["palette"]；
  3. 涂装骨架树：tree 上的语义背景（background: "gradient" /
     backgroundColor: "backboard"）替换为具体样式，解析后的树写入 ir["tree"]；
  4. 涂装条目：entry spec 中的 color_role / bg_role / ink_role 替换为具体色值。

输入契约：ir 由 P5 拼装完成；m1_theme 为 P1 校验后的合法枚举或 None。
挂载点：对比度校验（着色后执行，当前未实现）。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / "registry/themes.json").read_text(encoding="utf-8"))


def select_theme(domain: str, m1_theme, log: list) -> str:
    """按目录 priority 链选主题：M1 用户偏好 > domain 映射 > 默认。"""
    themes = CATALOG["themes"]
    pri = CATALOG["selection"]["priority"]
    picked = None

    if "m1_user_preference" in pri and m1_theme:
        if m1_theme in themes:
            picked = m1_theme

    if picked is None and "domain_map" in pri:
        for tid, entry in themes.items():
            if domain in entry.get("select", {}).get("domains", []):
                picked = tid
                break

    if picked is None:
        picked = CATALOG["selection"]["default"]
    return picked


def _resolve_tree_styles(tree: dict, palette: dict, size: str) -> None:
    """递归把树上的语义背景 token 替换为具体样式（原地修改）。"""
    def walk(node):
        styles = node.get("styles") or {}
        if styles.get("background") == "gradient":
            styles["linearGradient"] = palette["gradient"]
            del styles["background"]
        if styles.get("color") == "divider":  # 分隔线：主题动作底（20%），few-shot 同源
            styles["color"] = palette["roles"]["action_bg"]
        if styles.get("backgroundColor") == "backboard":
            styles["backgroundColor"] = palette["backboard"]["2x4" if size == "2x4" else "2x2"]
        for ch in node.get("children", []) or []:
            walk(ch)
    walk(tree)


def _resolve_entry_spec(spec: dict, palette: dict) -> None:
    """把 entry spec 中的色彩角色替换为具体色值（原地修改）。"""
    roles = palette["roles"]
    for role_key, target in (("color_role", "fontColor"),
                             ("bg_role", "backgroundColor"),
                             ("ink_role", "fontColor")):
        if role_key in spec:
            spec[target] = roles[spec.pop(role_key)]


def apply_theme(ir: dict, m1_theme=None) -> None:
    """P6 主入口：选主题 → 解析色板 → 涂树 → 涂条目（原地更新 ir）。"""
    log = ir.setdefault("fallback_log", [])
    theme_id = select_theme(ir.get("domain", "unknown"), m1_theme, log)
    entry = CATALOG["themes"][theme_id]
    palette = {"gradient": entry["palette"]["gradient"],
               "roles": entry["palette"]["roles"],
               "backboard": entry["palette"]["backboard"]}

    ir["theme"] = theme_id
    ir["palette"] = palette
    ir["theme_entry"] = {"desc": entry.get("desc", "")}

    # 骨架树着色（解析后的树写入 ir["tree"]，发射器不再回读 registry）
    skels = json.loads((ROOT / "registry/skeletons.json").read_text(encoding="utf-8"))
    tree = json.loads(json.dumps(skels["skeletons"][ir["skeleton_id"]]["tree"], ensure_ascii=False))
    _resolve_tree_styles(tree, palette, ir["size"])
    ir["tree"] = tree

    # 条目着色
    for e in ir.get("entries", []):
        _resolve_entry_spec(e["spec"], palette)

    # 挂载点：对比度校验（对 palette 与着色结果做渐变取样校验，当前未实现）
