"""Reproduce the historical A4a value-set rule on a sealed reference and first-frame Text nodes."""

import json
import re
import sys
from pathlib import Path

from six_arms import emit_fidelity
from six_arms.web_geometry_browser import resolve_value

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.measure import check_content

# Frozen build_content_oracle.py at blob 38c27401ca02da87b1b914b587b452af3feb84fd.
SKIP_KEY = re.compile(r"code|id|url|icon|color|type|unit|timestamp|ts$", re.IGNORECASE)
SEPARATOR = re.compile(r"\s*(?:/|~|～|—|→|至|，|,)\s*")


def parts(value):
    if type(value) not in (str, int, float):
        return ()
    text = str(value).strip()
    if not text or len(text) > 20:
        return ()
    tokens = tuple(p for p in (s.strip() for s in SEPARATOR.split(text)) if p)
    return tokens if len(tokens) > 1 else (text,)


def reference_facts(data, prefix=()):
    """Deduplicate by original display value, preserving every source pointer for the input audit."""
    facts = {}

    def visit(node, path):
        if isinstance(node, (dict, list)):
            entries = node.items() if isinstance(node, dict) else enumerate(node)
            for key, child in entries:
                visit(child, (*path, str(key)))
        elif not SKIP_KEY.search(path[-1] if path else ""):
            pointer = "/" + "/".join(
                k.replace("~", "~0").replace("/", "~1") for k in (*prefix, *path)
            )
            for val in parts(node):
                facts.setdefault(val, set()).add(pointer)

    visit(data, ())
    return facts


def messages(raw):
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not isinstance(result, list) or len(result) != 3:
        raise ValueError("Unsupported A2UI message set")
    return result


def read_reference(raw):
    model = messages(raw)[2]["updateDataModel"]
    if "value" not in model:
        raise ValueError("Missing reference data model")
    path = model.get("path") or "/"
    if (
        not isinstance(path, str)
        or not path.startswith("/")
        or re.search(r"~(?![01])", path)
    ):
        raise ValueError("Unknown reference data-model root")
    prefix = (
        tuple(p.replace("~1", "/").replace("~0", "~") for p in path[1:].split("/"))
        if path != "/"
        else ()
    )
    return reference_facts(model["value"], prefix)


def registered_value_support(facts, registered):
    """Count oracle values present among registered candidate samples, with and without path identity."""
    by_path = {path: set(parts(value)) for path, value in registered.items()}
    available = set().union(*by_path.values())
    return {
        "total": len(facts),
        "same_value_any_candidate": sum(v in available for v in facts),
        "same_value_same_path": sum(
            any(v in by_path.get(path, ()) for path in paths)
            for v, paths in facts.items()
        ),
    }


def artifact_text(raw):
    """For the original Text-only metric, resolve each reachable node in component order."""
    creation, graph, model = messages(raw)
    graph, model = graph["updateComponents"], model["updateDataModel"]
    if (
        creation["createSurface"]["surfaceId"] != graph["surfaceId"]
        or model["surfaceId"] != graph["surfaceId"]
    ):
        raise ValueError("Unsupported generated data-model root or surface")
    if "root" not in graph:
        nodes = graph["components"]
        roots = {c["id"] for c in nodes} - {
            child for c in nodes for child in c.get("children", [])
        }
        if len(roots) != 1:
            raise ValueError("No unique component-tree root")
        graph = {**graph, "root": roots.pop()}
    emit_fidelity.graph(graph)
    path = model.get("path") or "/"
    if (
        not isinstance(path, str)
        or not path.startswith("/")
        or re.search(r"~(?![01])", path)
    ):
        raise ValueError("Unsupported data-model pointer")
    data = model["value"]
    if path != "/":
        for part in reversed(path[1:].split("/")):
            data = {part.replace("~1", "/").replace("~0", "~"): data}
    return [
        resolve_value(c["content"], data)
        for c in graph["components"]
        if c["component"] == "Text"
    ]


def coverage(raw, facts):
    """Counts only; keep individual facts, card text and missing values inside the evaluator."""
    if facts is None:
        return None, None, "missing_reference"
    total = len(facts)
    if raw is None:
        return 0, total, "no_artifact"
    if not total:
        return None, 0, "empty_reference"
    try:
        text = artifact_text(raw)
    except (ValueError, TypeError, KeyError, IndexError):
        return None, total, "unresolved_text"
    count = check_content("\n".join(text), [{"value": v} for v in facts])
    return count["covered"], total, "measured"
