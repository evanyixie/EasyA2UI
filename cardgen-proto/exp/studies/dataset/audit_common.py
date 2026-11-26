"""只读金标审计的格式与来源工具；不执行表达式、不修改源数据。"""

import hashlib
import json
import re
from pathlib import Path


def private_destination(path, *, input_package=None):
    """逐题文件留在保管区。检查实际目标，防止误写发布仓库或冻结输入包。"""
    target = Path(path).resolve()
    code = Path(__file__).resolve().parent
    # 只识别本次发布的代码位置及其 GitHub 仓库，保管方可将数据放在独立私有 Git 仓。
    if code.parts[-4:] == ("cardgen-proto", "exp", "studies", "dataset"):
        checkout = code.parents[3]
        if target.is_relative_to(checkout) and (checkout / ".git").exists():
            from subprocess import DEVNULL, PIPE, run

            origin = (
                run(
                    ["git", "-C", str(checkout), "remote", "get-url", "origin"],
                    check=False,
                    stdin=DEVNULL,
                    stdout=PIPE,
                    stderr=DEVNULL,
                )
                .stdout.decode("utf8", errors="replace")
                .strip()
                .rstrip("/")
                .lower()
            )
            if re.fullmatch(
                r"(?:https?://(?:[^/@]+@)?github\.com/|(?:ssh://)?git@github\.com[:/])evanyixie/easya2ui(?:\.git)?",
                origin,
            ):
                raise ValueError("逐题材料需写入发布仓库之外的私有目录")
    if input_package is not None:
        public = Path(input_package).resolve()
        if target.is_relative_to(public) or public.is_relative_to(target):
            raise ValueError("人审私有目录与冻结输入包必须分开")
    return target


FORM_COMPONENTS = {
    "Text",
    "Image",
    "Divider",
    "Progress",
    "Button",
    "Checkbox",
    "Row",
    "Column",
    "List",
    "Stack",
}
EXPRESSION_PATH = re.compile(r"\$\{(/[^{}]+)\}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path):
    return json.loads(
        Path(path).read_text("utf-8-sig"), object_pairs_hook=unique_object
    )


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", "utf8")


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), "utf8"
    )


def rows(path):
    return [
        json.loads(line)
        for line in Path(path).read_text("utf8").splitlines()
        if line.strip()
    ]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def messages(path):
    """接受原始数组、JSONL和相邻JSON对象；每个对象原样保留。"""
    text = Path(path).read_text("utf-8-sig").strip()
    if not text:
        raise ValueError("empty A2UI")
    decoder = json.JSONDecoder(object_pairs_hook=unique_object)
    parsed, offset = [], 0
    while offset < len(text):
        value, end = decoder.raw_decode(text, offset)
        parsed.extend(value if isinstance(value, list) else [value])
        offset = end
        while offset < len(text) and text[offset].isspace():
            offset += 1
    if not parsed or not all(isinstance(item, dict) for item in parsed):
        raise ValueError("A2UI messages must be objects")
    return parsed


def pointer(value, path):
    if path == "/":
        return value
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("unsupported non-absolute binding")
    result = value
    for segment in path[1:].split("/"):
        segment = segment.replace("~1", "/").replace("~0", "~")
        if isinstance(result, dict) and segment in result:
            result = result[segment]
        elif (
            isinstance(result, list)
            and segment.isdecimal()
            and int(segment) < len(result)
        ):
            result = result[int(segment)]
        else:
            raise ValueError(f"unresolved pointer: {path}")
    return result


def bindings(value, location=""):
    if isinstance(value, dict):
        for key, child in value.items():
            current = f"{location}/{key}"
            if key == "path" and isinstance(child, str):
                yield current, child
            else:
                yield from bindings(child, current)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from bindings(child, f"{location}/{index}")
    elif isinstance(value, str):
        for path in EXPRESSION_PATH.findall(value):
            yield location, path


def child_refs(component):
    children = component.get("children", [])
    if isinstance(children, dict):
        if set(children) != {"explicitList"}:
            raise ValueError("dynamic or unsupported children representation")
        children = children["explicitList"]
    if not isinstance(children, list) or not all(
        isinstance(child, str) for child in children
    ):
        raise ValueError("children must be an explicit list of IDs")
    return children


def graph_evidence(update):
    components = update.get("components")
    if not isinstance(components, list) or not all(
        isinstance(item, dict) for item in components
    ):
        raise ValueError("components must be a list of objects")
    ids = [item.get("id") for item in components]
    if not all(isinstance(identity, str) and identity for identity in ids):
        raise ValueError("component ID missing")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate component ID")
    nodes = {item["id"]: item for item in components}
    root = update.get("root")
    if root not in nodes:
        raise ValueError("root component missing")
    parents, edges = {}, {}
    for identity, node in nodes.items():
        edges[identity] = child_refs(node)
        for child in edges[identity]:
            if child not in nodes:
                raise ValueError(f"unknown child: {child}")
            if child in parents:
                raise ValueError(f"multiple parents: {child}")
            parents[child] = identity
    visited, active = set(), set()

    def visit(identity):
        if identity in active:
            raise ValueError("component cycle")
        if identity in visited:
            return
        active.add(identity)
        for child in edges[identity]:
            visit(child)
        active.remove(identity)
        visited.add(identity)

    visit(root)
    if set(nodes) != visited or root in parents:
        raise ValueError("unreachable nodes or root has a parent")
    texts = [
        identity for identity in visited if nodes[identity].get("component") == "Text"
    ]
    return {
        "component_count": len(nodes),
        "text_count": len(texts),
        "root": root,
        "text_node_ids": texts,
        "reachable_count": len(visited),
    }


TRANSPORT_KEYS = {
    "deviceInfo",
    "session",
    "userAuth",
    "pagination",
    "version",
    "bundleName",
}


def input_view(raw):
    """只移除明确的外层传输元信息，所有业务子树与未知业务字段保留。"""
    if not isinstance(raw, dict):
        raise TypeError("request must be an object")
    nested = raw.get("content")
    base = dict(nested) if isinstance(nested, dict) else dict(raw)
    conflicts, removed = [], []
    if isinstance(nested, dict):
        for key, value in raw.items():
            if key in TRANSPORT_KEYS | {"content", "utterance"}:
                continue
            if key in base and base[key] != value:
                conflicts.append(key)
            elif key not in base:
                base[key] = value
    for key in TRANSPORT_KEYS:
        if key in base:
            base.pop(key)
            removed.append(key)
    original = (
        raw.get("utterance", {}).get("original")
        if isinstance(raw.get("utterance"), dict)
        else None
    )
    if original is not None:
        base["originalQuery"] = original
    query = base.get("userQuery")
    if not isinstance(query, str):
        query = original if isinstance(original, str) else ""
    return (
        base,
        query,
        {
            "conflicting_business_fields": conflicts,
            "removed_outer_fields": sorted(removed),
            "original_query_differs": original is not None and original != query,
            "semantic_filtering": False,
        },
    )
