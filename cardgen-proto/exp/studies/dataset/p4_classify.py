"""P4：只读金标拓扑与请求能力标识；不是产品合规或必显条目判定。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from audit_common import private_destination

VERSION = "p4-ux14-structural-v2"
SMALL = {
    "S-center",
    "S-title-content",
    "S-title-dual-content",
    "S-quad-content",
    "S-title-content-action",
    "S-title-primary-secondary-action",
    "S-title-dual-column-action",
    "S-title-anchor",
    "S-content-dual-action",
    "S-dual-info",
}
WIDE = {"W-top-bottom", "W-split-panels", "W-content-side-slots", "W-four-slots"}
LAYOUTS = SMALL | WIDE
WRAPPERS = {"__genui_render_component__root", "__post_theme_foreground"}
DOMAIN_BY_CAPABILITY = {
    "ViewWeather": "weather",
    "GetCalendarEvents": "calendar",
    "GetCountdownDays": "countdown",
    "GetEarphoneInfo": "earphone",
    "GetPhoneBatteryInfo": "battery",
    "GetHealthAndSportSummary": "healthSport",
    "GetCurrentTime": "time",
    "GetAppPowerConsumptionRanking": "app_power",
    "GetDailyMostUsage": "app_usage",
    "GetPhoneCallRecords": "phone",
    "GetMemoData": "memo",
}
OTHER_DATA_DECLARATIONS = {
    "dataCapabilityIds",
    "dataCapabilitySchemas",
    "dataCapabilities",
    "dataCapabilityParams",
    "dataBindings",
    "arguments",
}
REQUEST_ENVELOPES = {
    "content",
    "request",
    "params",
    "parameters",
    "payload",
    "cardSpec",
    "cardspec",
    "taskSpec",
}


def read_json_objects(path: Path) -> list[dict]:
    text = path.read_text("utf-8-sig").strip()
    fenced = re.fullmatch(r"```[^\r\n]*\r?\n([\s\S]*)\r?\n```", text)
    if fenced is not None:
        text = fenced.group(1).strip()
    decoder, values, offset = json.JSONDecoder(), [], 0
    while offset < len(text):
        value, end = decoder.raw_decode(text, offset)
        values.extend(value if isinstance(value, list) else [value])
        offset = end
        while offset < len(text) and text[offset].isspace():
            offset += 1
    if not values or not all(isinstance(value, dict) for value in values):
        raise ValueError("A2UI_OBJECTS: 需要对象数组、JSONL或串接JSON对象")
    return values


def children(node: dict) -> list[str]:
    value = node.get("children", [])
    if isinstance(value, dict):
        value = value.get("explicitList", [])
    if not isinstance(value, list) or not all(isinstance(part, str) for part in value):
        raise ValueError("CHILDREN_UNSUPPORTED: 子节点不是显式ID列表")
    return value


def reachable(nodes: dict, root: str) -> list[str]:
    seen, result, stack = set(), [], [(root, ())]
    while stack:
        identity, ancestors = stack.pop()
        if identity in ancestors:
            raise ValueError("TREE_CYCLE: 组件循环")
        if identity not in nodes:
            raise ValueError("MISSING_NODE: " + identity)
        if identity in seen:
            continue
        if len(ancestors) >= 128:
            raise ValueError("TREE_DEPTH: 无法安全解释过深组件树")
        seen.add(identity)
        result.append(identity)
        for child in reversed(children(nodes[identity])):
            stack.append((child, (*ancestors, identity)))
    return result


def component_graph(messages: list[dict]) -> tuple[dict, str]:
    nodes, root, surfaces = {}, None, set()
    for message in messages:
        update = message.get("updateComponents")
        if not isinstance(update, dict):
            continue
        surfaces.add(update.get("surfaceId"))
        root = update.get("root", root)
        for node in update.get("components", []):
            if not isinstance(node, dict) or not isinstance(node.get("id"), str):
                raise TypeError("NODE_ID: 缺少字符串ID")
            identity = node["id"]
            if identity in nodes:
                raise ValueError("REPEATED_NODE: 多次定义需单独审查流式语义")
            nodes[identity] = node
    if len(surfaces) != 1:
        raise ValueError("SURFACE_UNSUPPORTED: 需要单个surface")
    if root is None and "root" in nodes:
        root = "root"
    if root not in nodes:
        raise ValueError("ROOT_UNKNOWN: 无法确定根节点")
    reachable(nodes, root)
    return nodes, root


def foreground(nodes: dict, root: str) -> tuple[str, list[str]]:
    candidates = [
        identity for identity in reachable(nodes, root) if identity in WRAPPERS
    ]
    if not candidates:
        return root, []
    last = []
    for candidate in candidates:
        descendants = set(reachable(nodes, candidate)) - {candidate}
        if not descendants & WRAPPERS:
            last.append(candidate)
    if len(last) != 1:
        raise ValueError("WRAPPER_AMBIGUOUS: 多个并列前景包装")
    return last[0], candidates


def styles(node: dict) -> dict:
    value = node.get("styles", {})
    return value if isinstance(value, dict) else {}


def number(value):
    return (
        value
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else None
    )


def surface(node: dict) -> bool:
    appearance = styles(node)
    return bool(appearance.get("backgroundColor") or appearance.get("linearGradient"))


def button(node: dict) -> bool:
    if not node.get("onClick"):
        return False
    if node.get("component") == "Button":
        return True
    appearance = styles(node)
    height = number(appearance.get("height"))
    radius = number(appearance.get("borderRadius"))
    if height not in {36, 40, 57} or radius is None:
        return False
    return surface(node) and radius >= 12


def header(nodes: dict, identity: str) -> bool:
    node = nodes[identity]
    if node.get("component") != "Row" or button(node) or surface(node):
        return False
    texts = [
        nodes[key]
        for key in reachable(nodes, identity)
        if nodes[key].get("component") == "Text"
    ]
    if len(texts) != 1:
        return False
    appearance = styles(texts[0])
    return appearance.get("fontSize") == 12 and appearance.get("fontWeight", 400) == 400


def _grid(nodes, kids):
    return len(kids) == 2 and all(
        nodes[key].get("component") == "Row" and len(children(nodes[key])) == 2
        for key in kids
    )


def _full_panel(nodes, identity):
    node = nodes[identity]
    if node.get("component") != "Column" or not surface(node):
        return False
    appearance = styles(node)
    if appearance.get("height") in {"matchParent", "100%"}:
        return True
    prefix = "__layout__" + identity + "__"
    return any(key.startswith(prefix) for key in reachable(nodes, identity))


def structural_candidates(
    nodes: dict, root: str, size: str | None
) -> tuple[list[dict], dict]:
    ids = reachable(nodes, root)
    node, evidence = nodes[root], {}
    kids = children(node)
    kind = node.get("component")
    roles = {}
    for identity in ids:
        if identity.startswith("__layout__root__"):
            roles[identity.removeprefix("__layout__root__")] = identity
    buttons = [
        identity for identity in ids if identity != root and button(nodes[identity])
    ]
    has_header = bool(kids and header(nodes, kids[0]))
    progress = [
        identity for identity in ids if nodes[identity].get("component") == "Progress"
    ]
    counts = Counter(nodes[key].get("component") for key in ids)
    evidence.update(
        root=root,
        component=kind,
        direct_children=kids,
        generated_roles=roles,
        visible_button_ids=buttons,
        header_candidate=has_header,
        progress_ids=progress,
        component_counts=dict(counts),
    )
    evidence["confidence_semantics"] = "heuristic_rule_strength_not_probability"
    evidence["recipe_conformance"] = "not_validated_from_low_level_tree"
    candidates = []

    def add(label, confidence, reason):
        if size == "2x2" and label not in SMALL:
            return
        if size == "2x4" and label not in WIDE:
            return
        candidates.append({"layout": label, "confidence": confidence, "rule": reason})

    if kind == "Row" and len(kids) == 2:
        if "slots" in roles and len(children(nodes[roles["slots"]])) == 2:
            add("W-content-side-slots", 0.98, "generated_content_and_two_side_slots")
        elif all(_full_panel(nodes, key) for key in kids):
            add("W-split-panels", 0.94, "two_direct_full_panels")
        else:
            for child in kids:
                blocks = children(nodes[child])
                if len(blocks) == 2 and all(surface(nodes[block]) for block in blocks):
                    add("W-content-side-slots", 0.65, "unmarked_side_slot_shape")
    if kind == "Column" and _grid(nodes, kids):
        marked_grid = {"row0", "row1"} <= roles.keys()
        if marked_grid:
            if not buttons:
                add("S-quad-content", 0.96, "generated_two_rows_two_modules_no_buttons")
            add("W-four-slots", 0.96, "generated_two_rows_two_modules")
    if kind == "Column":
        if {"primary", "details"} <= roles.keys():
            add("W-top-bottom", 0.98, "generated_primary_details")
        if {"bottom", "action_slot", "primary"} <= roles.keys() and has_header:
            add("S-title-anchor", 0.99, "generated_bottom_support_icon_action")
        elif "primary_support" in roles and len(buttons) == 1 and has_header:
            add(
                "S-title-primary-secondary-action",
                0.99,
                "generated_tight_primary_support_action",
            )
        elif (
            ("ratios" in roles or "ratiorow0" in roles)
            and len(progress) == 2
            and has_header
        ):
            add("S-title-dual-column-action", 0.98, "generated_two_ratio_cells")
        elif {"action0", "action1"} <= roles.keys() and not has_header:
            add("S-content-dual-action", 0.99, "generated_content_two_actions")
        elif "content" in roles and len(kids) == 3 and not has_header:
            if kids[0] == roles["content"] and all(
                button(nodes[key]) for key in kids[1:]
            ):
                add(
                    "S-content-dual-action",
                    0.95,
                    "generated_content_two_direct_actions",
                )
        elif {"primary", "support"} <= roles.keys() and not buttons and has_header:
            add("S-title-dual-content", 0.98, "generated_primary_independent_support")
        elif "content" in roles and has_header:
            if len(buttons) == 1 and "action" in roles:
                add("S-title-content-action", 0.97, "generated_content_single_action")
            elif not buttons:
                add("S-title-content", 0.97, "generated_single_complete_content")
        elif "action" in roles and has_header and len(buttons) == 1:
            body_roles = {
                "content",
                "primary",
                "primary_support",
                "support",
                "ratiorow0",
            }
            if not body_roles & roles.keys():
                add("S-title-content-action", 0.96, "generated_title_action_only")
        if has_header and len(kids) == 3 and len(buttons) == 1:
            direct_action = (
                kids[-1] == buttons[0] and styles(nodes[kids[-1]]).get("height") == 36
            )
            direct_body = styles(nodes[kids[1]]).get("layoutWeight") == 1
            direct_gap = styles(node).get("itemMargin", node.get("itemMargin")) in {
                0,
                2,
                4,
                6,
            }
            if (
                direct_action
                and direct_body
                and direct_gap
                and "primary_support" not in roles
            ):
                add("S-title-content-action", 0.94, "direct_registered_content_action")
        if (
            len(kids) == 2
            and all(button(nodes[key]) for key in kids)
            and not has_header
        ):
            add("S-content-dual-action", 0.97, "two_direct_actions_only")
        if len(kids) == 2 and not buttons and not has_header:
            panels = all(surface(nodes[key]) for key in kids)
            fixed = all(styles(nodes[key]).get("height") == 63 for key in kids)
            weighted = all(styles(nodes[key]).get("layoutWeight") == 1 for key in kids)
            if panels and (fixed or weighted):
                add("S-dual-info", 0.94, "two_equal_short_info_panels")
        centered = styles(node).get("alignItems") == "center"
        centered = centered and styles(node).get("justifyContent") == "center"
        fonts = {
            styles(nodes[key]).get("fontSize")
            for key in ids
            if nodes[key].get("component") == "Text"
        }
        if len(kids) == 1 and centered and not buttons and fonts & {21, 48}:
            add("S-center", 0.97, "single_centered_registered_focus_typography")
        if not candidates and has_header:
            if not buttons and len(kids) >= 2:
                add("S-title-content", 0.55, "unmarked_header_content_ambiguous")
                add("S-title-dual-content", 0.55, "unmarked_header_content_ambiguous")
            elif len(buttons) == 1:
                add("S-title-content-action", 0.55, "unmarked_content_action_ambiguous")
                add(
                    "S-title-primary-secondary-action",
                    0.55,
                    "unmarked_content_action_ambiguous",
                )
    unique = {}
    for candidate in candidates:
        label = candidate["layout"]
        if label not in unique or candidate["confidence"] > unique[label]["confidence"]:
            unique[label] = candidate
    ordered = sorted(
        unique.values(), key=lambda value: (-value["confidence"], value["layout"])
    )
    return ordered, evidence


def compact_hint(path: Path | None):
    if path is None or not path.is_file():
        return None
    try:
        text = path.read_text("utf-8-sig").strip()
        fenced = re.fullmatch(r"```[^\r\n]*\r?\n([\s\S]*)\r?\n```", text)
        if fenced is not None:
            text = fenced.group(1).strip()
        decoder, offset = json.JSONDecoder(), 0
        while offset < len(text):
            while offset < len(text) and text[offset].isspace():
                offset += 1
            if offset == len(text):
                break
            value, offset = decoder.raw_decode(text, offset)
            if not isinstance(value, list):
                continue
            rows = value if value and isinstance(value[0], list) else [value]
            for row in rows:
                if len(row) < 3 or row[0] != "root" or row[1] != "Layout":
                    continue
                if isinstance(row[2], dict):
                    return row[2].get("layout")
    except (OSError, ValueError, TypeError):
        return None
    return None


def path_value(record, name, base):
    value = record.get(name)
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else base / path


def classify_domain(view: dict) -> tuple[list[str], str, dict]:
    candidates = view.get("candidateDataBindings")
    if not isinstance(candidates, list):
        return (
            [],
            "unknown_input",
            {"data_capability_ids": [], "unknown_capability_ids": []},
        )
    identifiers = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        identity = candidate.get("capabilityId", candidate.get("id"))
        if isinstance(identity, str) and identity not in identifiers:
            identifiers.append(identity)
    known, unknown = set(), []
    for identity in identifiers:
        domain = DOMAIN_BY_CAPABILITY.get(identity)
        if domain is None:
            unknown.append(identity)
        else:
            known.add(domain)
    if not identifiers:
        status = "no_data_candidates"
    elif not known:
        status = "unknown_capabilities"
    else:
        status = "partial_unknown" if unknown else "classified"
    source = {
        "data_capability_ids": identifiers,
        "unknown_capability_ids": unknown,
        "domain_source": "input_view.candidateDataBindings only",
    }
    return sorted(known), status, source


def data_declaration_signals(value, path: str, depth: int = 0) -> list[dict]:
    """仅诊断声明键，不把未解析schema或动作参数猜成数据候选。"""
    if depth > 6:
        return []
    if isinstance(value, str):
        content = value.strip()
        fenced = re.fullmatch(r"```[^\r\n]*\r?\n([\s\S]*)\r?\n```", content)
        if fenced is not None:
            content = fenced.group(1).strip()
        try:
            value = json.loads(content)
        except ValueError:
            return []
    if not isinstance(value, dict):
        return []
    signals = []
    for name, declaration in value.items():
        declaration_path = path + "." + name
        if name in OTHER_DATA_DECLARATIONS and declaration not in (None, "", [], {}):
            signals.append(
                {"path": declaration_path, "declared_type": type(declaration).__name__}
            )
        if name in REQUEST_ENVELOPES:
            signals.extend(
                data_declaration_signals(declaration, declaration_path, depth + 1)
            )
    return signals


def domain_declaration_evidence(
    view: dict, record: dict, base: Path, status: str
) -> dict:
    signals = data_declaration_signals(view, "input_view")
    diagnostic = {
        "other_data_declarations": signals,
        "declaration_values_interpreted": False,
    }
    if signals or status not in {"no_data_candidates", "unknown_input"}:
        return diagnostic
    raw_path = path_value(record, "input_path", base)
    if raw_path is None:
        return diagnostic
    try:
        raw = json.loads(raw_path.read_text("utf-8-sig"))
        diagnostic["other_data_declarations"] = data_declaration_signals(
            raw, "raw_input"
        )
    except (OSError, ValueError, TypeError) as exc:
        diagnostic["data_declaration_scan_error"] = type(exc).__name__
    return diagnostic


def classify(record: dict, base: Path) -> dict:
    result = {
        "case_id": record.get("case_id"),
        "source": record.get("source"),
        "size": record.get("size"),
        "p1_status": record.get("p1_status"),
        "layout": None,
        "layout_status": "unavailable",
        "domain": [],
        "domain_status": "unknown_input",
        "evidence": {
            "version": VERSION,
            "uses_gold_artifact": True,
            "forbidden_as_generation_or_p7_input": True,
            "input_view_sha256": record.get("input_view_sha256"),
        },
    }
    evidence = result["evidence"]
    view_path = path_value(record, "input_view_path", base)
    try:
        view = json.loads(view_path.read_text("utf-8-sig")) if view_path else {}
        if not isinstance(view, dict):
            raise TypeError("INPUT_VIEW_TYPE: 需要JSON对象")
        domains, status, domain_evidence = classify_domain(view)
        declarations = domain_declaration_evidence(view, record, base, status)
        if (
            status in {"no_data_candidates", "unknown_input"}
            and declarations["other_data_declarations"]
        ):
            status = "schema_unresolved"
        result.update(domain=domains, domain_status=status)
        evidence.update(domain_evidence)
        evidence.update(declarations)
        if view_path is not None:
            evidence["input_view_file_sha256"] = hashlib.sha256(
                view_path.read_bytes()
            ).hexdigest()
    except (OSError, ValueError, TypeError) as exc:
        evidence["domain_error"] = type(exc).__name__
    artifact = path_value(record, "a2ui_path", base)
    if artifact is None or not artifact.is_file():
        evidence["reason"] = "missing_normalized_artifact"
        return result
    evidence["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    try:
        nodes, root = component_graph(read_json_objects(artifact))
        root, wrappers = foreground(nodes, root)
        candidates, structure = structural_candidates(nodes, root, record.get("size"))
        evidence.update(
            structure, wrappers=wrappers or ["unwrapped"], candidates=candidates
        )
        evidence["physical_geometry"] = (
            "caller_supplied"
            if record.get("host_size_vp")
            else "unknown_not_a_product_failure"
        )
        evidence["geometry_validation"] = "not_performed_no_render_or_host_assumption"
        hint = compact_hint(path_value(record, "compact_path", base))
        evidence["compact_layout_hint"] = hint
        evidence["compact_is_independent_hint_not_a2ui_proof"] = True
        static_roles = any(
            role.startswith("static_") for role in structure["generated_roles"]
        )
        if static_roles:
            result["layout_status"] = "source_layout_outside_14"
            evidence["outside_catalogue_kind"] = "static_semantic_layout"
        elif record.get("size") not in {"2x2", "2x4"}:
            result["layout_status"] = "geometry_unknown"
        elif not candidates:
            result["layout_status"] = "unclassified_or_outside_14"
        elif candidates[0]["confidence"] < 0.9 or len(candidates) > 1:
            result["layout_status"] = "low_confidence_or_ambiguous"
        elif hint in LAYOUTS and hint != candidates[0]["layout"]:
            result["layout_status"] = "compact_a2ui_conflict"
        elif hint is not None and hint not in LAYOUTS:
            result["layout_status"] = "source_layout_outside_14"
        else:
            result.update(
                layout=candidates[0]["layout"], layout_status="classified_structural"
            )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result["layout_status"] = "structure_unresolved"
        evidence.update(error_type=type(exc).__name__, reason=str(exc))
    return result


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output = private_destination(args.output)
    records = [
        json.loads(line)
        for line in args.records.read_text("utf-8-sig").splitlines()
        if line.strip()
    ]
    results = [classify(record, args.records.parent) for record in records]
    args.output.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output / "records.jsonl", results)
    domain_counts = Counter()
    for item in results:
        domain_counts.update(item["domain"])
    summary = {
        "version": VERSION,
        "count": len(results),
        "source_records_sha256": hashlib.sha256(args.records.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "layout_status": dict(Counter(item["layout_status"] for item in results)),
        "layout": dict(Counter(item["layout"] for item in results if item["layout"])),
        "catalogue": sorted(LAYOUTS),
        "unobserved_catalogue": sorted(LAYOUTS - {item["layout"] for item in results}),
        "domain": dict(domain_counts),
        "domain_status": dict(Counter(item["domain_status"] for item in results)),
        "physical_geometry": dict(
            Counter(
                item["evidence"].get("physical_geometry", "unavailable")
                for item in results
            )
        ),
        "limitation": "结构标签不是产品/视觉通过；P6双人独立复核前仍为草稿；不得输入P7或生成模型",
    }
    summary_text = json.dumps(summary, ensure_ascii=False, indent=2)
    (args.output / "summary.json").write_text(summary_text, "utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
