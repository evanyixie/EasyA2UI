"""只读完整金标拓扑，提供入口/文本风险证据，不冒充原生可见性或P7真值。"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from p4_classify import (
    button,
    component_graph,
    foreground,
    reachable,
    read_json_objects,
)

MISSING = object()
BINDING = re.compile(r"^\{\{\s*\$\{(/[^{}]*)\}\s*\}\}$")


def digest(value):
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def compact_rows(path):
    if not path:
        return []
    content = Path(path).read_text("utf-8-sig").strip()
    fenced = re.fullmatch(r"```[^\r\n]*\r?\n([\s\S]*)\r?\n```", content)
    if fenced:
        content = fenced.group(1).strip()
    decoder, offset, result = json.JSONDecoder(), 0, []
    while offset < len(content):
        while offset < len(content) and content[offset].isspace():
            offset += 1
        if offset == len(content):
            break
        value, offset = decoder.raw_decode(content, offset)
        if isinstance(value, list):
            result.extend(value if value and isinstance(value[0], list) else [value])
    return result


def pointer(model, path):
    value = model
    for part in path.removeprefix("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            value = value.get(part, MISSING)
        elif isinstance(value, list) and part.isdecimal():
            index = int(part)
            value = value[index] if index < len(value) else MISSING
        else:
            value = MISSING
        if value is MISSING:
            break
    return value


def descendants(nodes, identity):
    return set(reachable(nodes, identity)) - {identity}


def sample_kind(value):
    if value is MISSING:
        return "missing"
    if value is None:
        return "null"
    if isinstance(value, str) and not value.strip():
        return "empty_string"
    return type(value).__name__


def analyse(record):
    case_id = record["case_id"]
    path = record.get("a2ui_path")
    if not path:
        return {"case_id": case_id, "status": "missing_gold", "A_declared": None}
    messages = read_json_objects(Path(path))
    nodes, root = component_graph(messages)
    ids = reachable(nodes, root)
    logical_root, wrappers = foreground(nodes, root)
    sources = {}
    for row in compact_rows(record.get("compact_path")):
        if (
            len(row) >= 2
            and isinstance(row[1], str)
            and not str(row[0]).startswith("/")
        ):
            sources[row[0]] = row[1]
    models = [
        message["updateDataModel"]
        for message in messages
        if isinstance(message.get("updateDataModel"), dict)
    ]
    root_models = [model.get("value") for model in models if model.get("path") == "/"]
    model = root_models[-1] if root_models else {}
    actions, texts, bindings, risks = [], [], [], set()
    for identity in ids:
        node = nodes[identity]
        handlers = node.get("onClick")
        if handlers:
            if not isinstance(handlers, list):
                risks.add("unsupported_onclick_shape")
            actions.append(
                {
                    "id": identity,
                    "component": node.get("component"),
                    "source_component": sources.get(identity),
                    "handlers": len(handlers),
                    "payload_sha256": digest(handlers),
                    "global_root": identity in {root, logical_root},
                    "button_shape": button(node),
                    "styles": node.get("styles", {}),
                }
            )
        if node.get("component") != "Text":
            continue
        content = node.get("content")
        evidence = {"id": identity, "content_kind": "literal"}
        if not isinstance(content, str):
            evidence["content_kind"] = "unsupported"
            risks.add("unsupported_text_content")
        elif not content.strip():
            evidence["content_kind"] = "empty_literal"
            risks.add("empty_literal_text")
        else:
            paths = re.findall(r"\$\{(/[^{}]*)\}", content)
            if paths:
                bindings.extend(paths)
                direct = BINDING.fullmatch(content.strip())
                evidence.update(content_kind="expression", binding_paths=paths)
                samples = []
                for data_path in paths:
                    kind = sample_kind(pointer(model, data_path))
                    samples.append({"path": data_path, "kind": kind})
                    if kind in {"missing", "null", "empty_string"}:
                        risks.add("empty_or_missing_sample_text")
                evidence["binding_sample_kinds"] = samples
                if direct:
                    kind = sample_kind(pointer(model, direct.group(1)))
                    evidence.update(content_kind="direct_binding", sample_kind=kind)
                else:
                    risks.add("compound_expression_text")
        appearance = node.get("styles", {})
        if appearance.get("width") == 0 or appearance.get("height") == 0:
            evidence["zero_declared_dimension"] = True
            risks.add("zero_text_dimension")
        color = appearance.get("fontColor")
        if isinstance(color, str) and re.fullmatch(r"#00[0-9a-fA-F]{6}", color):
            evidence["transparent_text_color"] = True
            risks.add("transparent_text_color")
        texts.append(evidence)
    nested, sibling_repeats = [], []
    for index, first in enumerate(actions):
        first_descendants = descendants(nodes, first["id"])
        for second in actions[index + 1 :]:
            second_descendants = descendants(nodes, second["id"])
            same = first["payload_sha256"] == second["payload_sha256"]
            if second["id"] in first_descendants or first["id"] in second_descendants:
                nested.append(
                    {"first": first["id"], "second": second["id"], "same_payload": same}
                )
                nested_risk = (
                    "nested_action_same_payload"
                    if same
                    else "nested_action_different_payload"
                )
                risks.add(nested_risk)
            elif same:
                sibling_repeats.append([first["id"], second["id"]])
                risks.add("separate_nodes_same_payload")
    global_actions = [action for action in actions if action["global_root"]]
    other_actions = [action for action in actions if not action["global_root"]]
    if global_actions and other_actions:
        risks.add("global_and_child_actions")
    if any(action["handlers"] > 1 for action in actions):
        risks.add("multiple_handlers_one_node")
    counter = Counter(sources.values())
    if counter.get("EventCard"):
        risks.add("event_record_structure")
    if counter.get("SecondaryBody") or counter.get("TableText"):
        risks.add("key_value_or_table_structure")
    if len(bindings) != len(set(bindings)):
        risks.add("repeated_text_binding")
    unreachable = []
    for identity, node in nodes.items():
        if identity not in ids and node.get("onClick"):
            unreachable.append(identity)
    if unreachable:
        risks.add("unreachable_onclick")
    return {
        "case_id": case_id,
        "status": "topology_only_not_visual",
        "A_declared": len(actions),
        "A_distinct_payloads": len({action["payload_sha256"] for action in actions}),
        "A_actual_visible": None,
        "A_actual_status": "pending_native_visibility",
        "actions": actions,
        "nested_actions": nested,
        "separate_same_payload": sibling_repeats,
        "unreachable_onclick": unreachable,
        "text_nodes": len(texts),
        "text_evidence": texts,
        "binding_paths": sorted(set(bindings)),
        "source_component_counts": dict(counter),
        "risks": sorted(risks),
        "wrappers": wrappers or ["unwrapped"],
        "artifact_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
    }
