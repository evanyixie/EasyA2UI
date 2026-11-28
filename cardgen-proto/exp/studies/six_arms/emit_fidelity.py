"""从冻结语义与主题树独立核对发射结果。只读输入和产物，不加载任何生成实现。"""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

SECTIONS = ("structure", "order", "text", "bindings", "actions", "geometry", "theme", "data")
THEME = {"fontColor", "backgroundColor", "linearGradient"}
COLOR = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
UNKNOWN = object()


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_key(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def same(left, right):
    # JSON 的真假值与 0、1 应当分开；整数与同值小数的原生尺寸可等价。
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right, strict=True))
    return left == right


def color_value(value):
    if isinstance(value, str) and COLOR.fullmatch(value):
        return "#" + ("FF" if len(value) == 7 else "") + value[1:].upper()
    if isinstance(value, dict):
        return {k: color_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [color_value(v) for v in value]
    return value


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
            expr = expr[m.end():].strip()
        if not expr:
            return result
        if not expr.startswith("+") or not expr[1:].strip():
            return UNKNOWN
        expr = expr[1:].strip()
    return UNKNOWN


def combine(parts):
    result = []
    for part in parts:
        if part is UNKNOWN:
            return UNKNOWN
        for kind, value in part:
            if result and kind == result[-1][0] == "text":
                result[-1] = ("text", result[-1][1] + value)
            else:
                result.append((kind, value))
    return result


def expected_text(item):
    value = item["text"]
    label, unit = item.get("label", ""), item.get("unit", "")
    prefix = label + " " if label and not value.startswith(label) else ""
    suffix = unit if unit and not value.endswith(unit) else ""
    entries = [("text", prefix), ("path", item["path"]) if "path" in item else ("text", value), ("text", suffix)]
    return combine([[(k, v)] for k, v in entries if v])


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
        return {"kind": kind.lower(), "styles": styles, "id": cid, "component": c,
                "children": [visit(i) for i in children]}
    root = visit(message.get("root", "root"))
    if set(by_id) != seen:
        raise ValueError("存在未连接节点")
    return root


def leaf_stream(node):
    if node["kind"] == "text" and not node["children"]:
        return tokens(node["component"].get("content"))
    if node["kind"] == "row" and node["children"]:
        return combine([leaf_stream(c) for c in node["children"]])
    return UNKNOWN


def audit(content, theme, messages, source):
    findings = []
    verified = Counter()
    def flag(category, issue, at, detail, **values):
        findings.append({"dimension": category, "issue": issue, "where": at, "detail": detail, **values})
    def equal(category, expected, actual, at, name):
        if same(expected, actual):
            verified[category] += 1
        else:
            flag(category, "changed", at, name, expected=expected, observed=actual)

    items = {v["id"]: v for v in content["items"]}
    if content.get("title"):
        items["title"] = {"text": content["title"]}
    actions = {v["id"]: v for v in content["actions"]}
    handlers = {v["id"]: v.get("handler") for v in source.get("candidate_actions", [])}
    def text_compare(ref, stream, at):
        if stream is UNKNOWN:
            for dimension in ("text", "bindings"):
                flag(dimension, "unknown", at, f"引用 {ref} 的表达式无法静态还原")
            return
        expected = expected_text(items[ref])
        equal("bindings", [v for k, v in expected if k == "path"], [v for k, v in stream if k == "path"],
              at, f"{ref} 的绑定路径及顺序")
        # 保留动态值的位置，避免把交换的单位和前缀误作文字相等。
        def fmt(parts):
            return [value if kind == "text" else {"bound_value": True} for kind, value in parts]

        if any(k == "text" for k, _ in expected) and not any(k == "text" for k, _ in stream):
            flag("text", "missing", at, f"{ref} 的静态文字丢失", expected=fmt(expected), observed=fmt(stream))
        else:
            equal("text", fmt(expected), fmt(stream), at, f"{ref} 的可见文案及绑定位置")
    def compare_styles(want, got, at):
        a, b = dict(want.get("style", {})), dict(got["styles"])
        # 原生组件显式 0 间距与无指定间距等价。
        if got["kind"] in ("row", "column") and "itemMargin" not in a and b.get("itemMargin") == 0:
            b.pop("itemMargin")
        for k in sorted(a.keys() | b.keys()):
            dim = "theme" if k in THEME else "geometry"
            if k not in a:
                flag(dim, "added", at, k, observed=b[k])
            elif k not in b:
                flag(dim, "missing", at, k, expected=a[k])
            else:
                canon = color_value if dim == "theme" else lambda value: value
                equal(dim, canon(a[k]), canon(b[k]), at, k)
    def text_identity(stream):
        if stream is UNKNOWN:
            return None
        paths = [v for k, v in stream if k == "path"]
        return ("bound", paths) if paths else ("static", stream)
    def semantic_signature_expected(node):
        if node["kind"] == "text":
            return ("text", text_identity(expected_text(items[node["ref"]])))
        if node["kind"] == "button":
            ref = node["ref"]
            return ("button", [handlers.get(ref)])
        return (node["kind"], [semantic_signature_expected(c) for c in node["children"]])
    def semantic_signature_actual(node):
        c, kind = node["component"], node["kind"]
        if kind == "text":
            stream = tokens(c.get("content"))
            return (kind, text_identity(stream))
        if kind == "button":
            return (kind, c.get("onClick"))
        return (kind, [semantic_signature_actual(ch) for ch in node["children"]])
    def inventory(node, expected, at, collected):
        kind = node["kind"]
        if expected:
            if kind == "button":
                ref = node["ref"]
                collected["actions"].append(handlers.get(ref))
            elif kind == "text":
                item = items[node["ref"]]
                if "path" in item:
                    collected["bindings"].append(item["path"])
        else:
            c = node["component"]
            if "onClick" in c:
                if isinstance(c["onClick"], list):
                    collected["actions"].extend(c["onClick"])
                else:
                    flag("actions", "changed", at, "onClick 应为动作数组")
            if kind == "text":
                values = tokens(c.get("content"))
                if values is UNKNOWN:
                    collected["unknown_binding_count"] += 1
                else:
                    collected["bindings"].extend(v for k, v in values if k == "path")
            if kind in ("text", "button", "row", "column"):
                known = {"id", "component", "styles", "children", "itemMargin", "label", "onClick", "content"}
                extra = c.keys() - known
                if extra:
                    flag("structure", "unknown", at, "额外原生属性的宿主行为未断言", observed=sorted(extra))
        for index, child in enumerate(node.get("children", [])):
            inventory(child, expected, at + f"/{index}", collected)

    def compare_node(want, got, at):
        wk, gk = want["kind"], got["kind"]
        children = got["children"]
        # 有样式包裹可能改变排版；即使文案可独立验证也不自动通过几何检查。
        if wk != gk and wk == "text" and gk == "row" and len(children) > 1:
            stream = leaf_stream(got)
            if stream is not UNKNOWN:
                text_compare(want["ref"], stream, at)
                for dim in ("structure", "geometry", "theme"):
                    flag(dim, "unknown", at, "单个 Text 展开成多段 Row，外观等价需要布局证据")
                flag("order", "unknown", at, "文本片段排列已核对，跨组件阅读行为需宿主确认")
                return
        if wk != gk and gk in ("row", "column") and len(children) == 1 and children[0]["kind"] == wk:
            for dim in ("structure", "geometry"):
                flag(dim, "unknown", at, "额外单子容器的布局效果需宿主确认")
            if got["styles"]:
                flag("theme", "unknown", at, "包裹层额外样式可能产生遮挡或颜色变化")
            compare_node(want, children[0], at + "/wrap")
            return
        equal("structure", wk, gk, at, "组件角色")
        if wk != gk:
            for dim in ("order", "text", "bindings", "actions", "geometry", "theme"):
                flag(dim, "unknown", at, "节点角色变化，后代无法逐项对齐")
            return
        compare_styles(want, got, at)
        if wk == "text":
            text_compare(want["ref"], tokens(got["component"].get("content")), at)
        elif wk == "button":
            ref = want["ref"]
            equal("text", actions[ref]["label"], got["component"].get("label"), at, f"{ref} 按钮文案")
            if handlers.get(ref) is None:
                flag("actions", "unknown", at, f"{ref} 缺冻结 handler")
            else:
                equal("actions", [handlers[ref]], got["component"].get("onClick"), at, f"{ref} 的完整事件数组")
        else:
            before = want["children"]
            if len(before) != len(children):
                issue = "missing" if len(before) > len(children) else "added"
                flag("structure", issue, at, "子节点数不同", expected=len(before), observed=len(children))
                flag("order", "unknown", at, "子节点数变化，按位置对齐的后续差异可能源自前序增删")
            else:
                left = [semantic_signature_expected(n) for n in before]
                right = [semantic_signature_actual(n) for n in children]
                if left == right and len(set(map(json_key, left))) < len(left):
                    flag("order", "unknown", at, "同组存在相同绑定/动作/静态文字，两个节点身份不能区分")
                elif left == right:
                    verified["order"] += 1
                else:
                    # 显式识别换序；内容变化本身不构成换序证据。
                    if Counter(map(json_key, left)) == Counter(map(json_key, right)):
                        flag("order", "changed", at, "同组子节点按可见内容、绑定和动作识别后发生换序")
                    else:
                        flag("order", "unknown", at, "子节点语义签名发生变化，顺序无法独立断言")
            for index, (c1, c2) in enumerate(zip(before, children, strict=False)):
                compare_node(c1, c2, f"{at}/{index}")
        if wk in ("text", "button") and children:
            flag("structure", "added", at, "叶节点出现额外 children")
    try:
        tree = graph(messages[1]["updateComponents"])
    except (ValueError, KeyError, TypeError, RecursionError) as exc:
        flag("structure", "changed", "root", str(exc))
        for dim in ("text", "order", "bindings", "actions", "geometry", "theme"):
            flag(dim, "unknown", "root", "原生树无法可靠还原")
    else:
        compare_node(theme["root"], tree, "root")
        before = {"bindings": [], "actions": [], "unknown_binding_count": 0}
        after = {"bindings": [], "actions": [], "unknown_binding_count": 0}
        inventory(theme["root"], True, "root", before)
        inventory(tree, False, "root", after)
        for aspect in ("bindings", "actions"):
            if aspect == "bindings" and after["unknown_binding_count"]:
                flag(aspect, "unknown", "root", "部分原生表达式未识别，全卡路径清单不完整")
                continue
            expected_count = Counter(map(json_key, before[aspect]))
            observed_count = Counter(map(json_key, after[aspect]))
            for issue, counts in (("missing", expected_count - observed_count), ("added", observed_count - expected_count)):
                for item, count in counts.items():
                    flag(aspect, issue, "root", "全卡登记项计数变化", item=json.loads(item), count=count)
    data = messages[2].get("updateDataModel", {})
    value = data.get("value", UNKNOWN)
    path = data.get("path")
    if value is UNKNOWN or not isinstance(path, str) or not path.startswith("/"):
        flag("data", "missing", "/", "首帧值或绝对路径缺失")
    else:
        if path != "/":
            for token in reversed(path[1:].split("/")):
                value = {token.replace("~1", "/").replace("~0", "~"): value}
        equal("data", source["sample_data"], value, "/", "整份首帧数据")
    # 无动作时不计入动作维度的匹配样本。
    state = {}
    for dimension in SECTIONS:
        issues = {f["issue"] for f in findings if f["dimension"] == dimension}
        state[dimension] = ("different" if issues - {"unknown"} else "unknown" if issues else
                            "matched" if verified[dimension] else "not_applicable")
    return {"status": ("different" if "different" in state.values() else
                       "unknown" if "unknown" in state.values() else "matched"),
            "dimensions": state, "findings": findings}


def audit_run(run):
    lock = load(run / "freeze.json")
    rows = []
    for task, arm in lock["queue"]:
        dest = run / task / arm
        receipt = dest / "receipt.json"
        global_status = load(receipt)["status"] if receipt.exists() else "not_executed"
        row = {"task": task, "arm": arm, "generation_status": global_status}
        rows.append(row)
        if arm == "L1":
            row["status"] = "not_applicable_one_shot"
            continue
        if global_status in ("not_executed", "in_progress"):
            row["status"] = global_status
            continue
        paths = {k: dest / v for k, v in (("theme", "theme.json"), ("content", "content.json"),
                                         ("artifact", "card.a2ui.jsonl"))}
        paths["source"] = run / "sources" / (task + ".json")
        if not paths["theme"].exists():
            row["status"] = "not_reached"
            continue
        if not paths["artifact"].exists():
            row["status"] = "no_final_artifact"
            continue
        row["hashes"] = {k: digest(p) for k, p in paths.items() if p.is_file()}
        if row["hashes"].get("source") != lock["source_hashes"].get(task):
            row.update(status="unknown", reason="冻结输入哈希不匹配")
            continue
        try:
            lines = [json.loads(line) for line in paths["artifact"].read_text(encoding="utf8").splitlines()]
            row.update(audit(load(paths["content"]), load(paths["theme"]), lines, load(paths["source"])))
        except (ValueError, IndexError, KeyError, TypeError, AttributeError, RecursionError, OSError) as exc:
            row.update(status="unknown", reason=type(exc).__name__ + ": " + str(exc))
    summary = {arm: dict(Counter(r["status"] for r in rows if r["arm"] == arm)) for arm in sorted({r["arm"] for r in rows})}
    return {"freeze_sha256": digest(run / "freeze.json"), "evaluator_sha256": digest(Path(__file__)), "counts": summary,
            "scope": "静态比较已冻结内容、主题树与最终产物的声明。可还原的字符串拼接按其意图比对。宿主语法准入、实际显示、最终业务覆盖与交互须使用各自验收结果。", "rows": rows}


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("run", type=Path)
    cli.add_argument("--output", required=True, type=Path)
    args = cli.parse_args()
    result = audit_run(args.run)
    args.output.parent.mkdir(exist_ok=True, parents=True)
    with args.output.open("x", encoding="utf8") as report:
        json.dump(result, report, ensure_ascii=False, indent=2)
    print(json.dumps(result["counts"], ensure_ascii=False))
