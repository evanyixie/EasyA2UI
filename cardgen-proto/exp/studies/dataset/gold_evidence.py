"""冻结金标展示端计数证据；不把原需求或未展示的模型叶当作展示项。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from audit_common import bindings, child_refs, graph_evidence, messages, pointer


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_case(row: dict, compact: Path, standard: Path) -> dict:
    compact_rows = [
        json.loads(line)
        for line in compact.read_text("utf-8-sig").splitlines()
        if line.strip()
    ]
    components = {
        item[0]: {"id": item[0], "type": item[1], "args": item[2]}
        for item in compact_rows
        if len(item) >= 3 and not item[0].startswith("/")
    }
    all_messages = messages(standard)
    updates = [
        item["updateComponents"] for item in all_messages if "updateComponents" in item
    ]
    models = [
        item["updateDataModel"] for item in all_messages if "updateDataModel" in item
    ]
    if len(updates) != 1 or len(models) != 1 or models[0].get("path") != "/":
        raise ValueError("不支持的更新序列，需人工保留而非猜测")
    update, model = updates[0], models[0]["value"]
    graph_evidence(update)
    nodes = {item["id"]: item for item in update["components"]}
    parents = {
        child: identity
        for identity, node in nodes.items()
        for child in child_refs(node)
    }

    def owner(identity):
        cursor = identity
        while cursor in nodes:
            if cursor in components:
                return cursor
            cursor = parents.get(cursor)
        return None

    texts, actions, non_text = [], [], []
    for identity, node in nodes.items():
        if node.get("component") == "Text":
            refs = []
            for _, path in bindings(node.get("content")):
                refs.append({"path": path, "sample_value": pointer(model, path)})
            texts.append(
                {
                    "id": identity,
                    "content": node.get("content"),
                    "owner": owner(identity),
                    "bindings": refs,
                }
            )
        handlers = node.get("onClick")
        if handlers:
            if not isinstance(handlers, list):
                raise ValueError("点击绑定不是指令列表")
            actions.append(
                {
                    "id": identity,
                    "component": node.get("component"),
                    "owner": owner(identity),
                    "handler_count": len(handlers),
                    "handler_sha256": hashlib.sha256(
                        json.dumps(
                            handlers, ensure_ascii=False, sort_keys=True
                        ).encode()
                    ).hexdigest(),
                }
            )
        if node.get("component") in {"Progress", "Checkbox"}:
            non_text.append(node)
    return {
        "case_id": row["case_id"],
        "size": row["size"],
        "compact_components": list(components.values()),
        "texts": texts,
        "non_text_data_nodes": non_text,
        "actions": actions,
        "A": len(actions),
        "compact_sha256": sha(compact),
        "a2ui_sha256": sha(standard),
        "basis": "gold_actual_display_declaration_not_request_or_candidate",
        "pixel_visibility_independently_verified": False,
    }
