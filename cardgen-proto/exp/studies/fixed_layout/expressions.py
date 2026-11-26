"""冻结表达式与协议树的独立解析。"""

import json
import re

UNKNOWN = object()


def same(left, right):
    # JSON 的真假值与 0、1 应当分开；整数与同值小数的原生尺寸可等价。
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right, strict=True))
    return left == right


def tokens(value):
    """只解释直接路径、原生 '+' 拼接及静态文本；其他语法保留未知。"""
    if isinstance(value, dict):
        if set(value) == {"path"} and isinstance(value["path"], str):
            return [("path", value["path"])]
        return UNKNOWN
    if not isinstance(value, str):
        return UNKNOWN
    stripped = value.strip()
    if not stripped.startswith("{{"):
        return [("text", value)] if value else []
    if not stripped.endswith("}}"):
        return UNKNOWN
    expr = stripped[2:-2].strip()
    result = []
    while expr:
        if expr.startswith(('"', "'")):
            if expr[0] == "'":
                match = re.match(r"'([^'\\]*)'", expr)
                if match is None:
                    return UNKNOWN
                literal, end = match.group(1), match.end()
            else:
                try:
                    literal, end = json.JSONDecoder().raw_decode(expr)
                except ValueError:
                    return UNKNOWN
            if not isinstance(literal, str):
                return UNKNOWN
            if literal:
                if result and result[-1][0] == "text":
                    result[-1] = ("text", result[-1][1] + literal)
                else:
                    result.append(("text", literal))
            expr = expr[end:].strip()
        else:
            m = re.match(r"\$\{(/[^}]*)\}", expr)
            if not m:
                return UNKNOWN
            result.append(("path", m.group(1)))
            expr = expr[m.end() :].strip()
        if not expr:
            return result
        if not expr.startswith("+") or not expr[1:].strip():
            return UNKNOWN
        expr = expr[1:].strip()
    return UNKNOWN


def graph(message):
    by_id = {}
    components = message["components"]
    if not isinstance(components, list):
        raise TypeError("components 不是数组")
    for c in components:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str) or c["id"] in by_id:
            raise ValueError("节点 ID 缺失或重复")
        by_id[c["id"]] = c
    seen = set()

    def visit(cid):
        if not isinstance(cid, str) or cid not in by_id or cid in seen:
            raise ValueError("存在悬空节点、多父节点或环")
        seen.add(cid)
        c = by_id[cid]
        children = c.get("children", [])
        if not isinstance(children, list):
            raise TypeError("children 不是有序数组")
        kind = c.get("component")
        styles = c.get("styles", {})
        if not isinstance(kind, str) or not isinstance(styles, dict):
            raise TypeError("组件类型或样式对象无效")
        styles = dict(styles)
        if "itemMargin" in c:
            if "itemMargin" in styles and not same(c["itemMargin"], styles["itemMargin"]):
                raise ValueError("顶层 itemMargin 与样式冲突")
            styles["itemMargin"] = c["itemMargin"]
        return {
            "kind": kind.lower(),
            "styles": styles,
            "id": cid,
            "component": c,
            "children": [visit(i) for i in children],
        }

    root = visit(message.get("root", "root"))
    if set(by_id) != seen:
        raise ValueError("存在未连接节点")
    return root
