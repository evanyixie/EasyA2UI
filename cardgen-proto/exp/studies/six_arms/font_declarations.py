"""C-05 declared font sizes in A2UI. The device's rendered size is not inferred."""

import json
from collections import Counter
from math import isfinite

from six_arms import emit_fidelity
from six_arms.reference_content import KNOWN_COMPONENTS, surface_data
from src.measure import static_metrics


def _legacy(raw):
    """The original second-line reader includes containers, booleans and nonpositive numbers.

    Report unparseable inputs and nonfinite values as unassessed rather than
    exporting the historical reader's silent empty default or invalid JSON.
    """
    try:
        nodes = json.loads(raw.splitlines()[1])["updateComponents"]["components"]
        if not isinstance(nodes, list) or not all(isinstance(c, dict) for c in nodes):
            return None
        fonts = [
            c["styles"]["fontSize"]
            for c in nodes
            if isinstance(c.get("styles"), dict)
            and isinstance(c["styles"].get("fontSize"), (int, float))
        ]
        if any(type(f) is float and not isfinite(f) for f in fonts):
            return None
        original = static_metrics(raw)
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    minimum = original["min_font"]
    return {
        "min_font": int(minimum) if type(minimum) is bool else minimum,
        "below_12fp": original["below_12fp"],
        "below_10fp": original["below_10fp"],
        "numeric_nodes": len(fonts),
    }


def reachable_nodes(graph):
    """Validate one rooted component tree and return its nodes in artifact order."""
    nodes = graph["components"]
    if "root" not in graph:
        roots = {c["id"] for c in nodes} - {
            child for c in nodes for child in c.get("children", [])
        }
        if len(roots) != 1:
            raise ValueError("No unique component-tree root")
        graph = {**graph, "root": roots.pop()}
    emit_fidelity.graph(graph)
    for node in nodes:
        kind = node["component"]
        if kind not in KNOWN_COMPONENTS or (
            kind in {"Text", "Button", "Image", "Checkbox", "Progress", "Divider"}
            and node.get("children")
        ):
            raise ValueError("Unknown component or children under a leaf")
    return nodes


def valid_font_size(value):
    """Numeric, positive and finite; a boolean cannot declare a font size."""
    return (
        type(value) in (int, float)
        and value > 0
        and (type(value) is int or isfinite(value))
    )


def _group(nodes, kind):
    sizes = Counter()
    missing = invalid = 0
    for node in nodes:
        if node["component"] != kind:
            continue
        styles = node.get("styles", {})
        if "fontSize" not in styles:
            missing += 1
            continue
        size = styles["fontSize"]
        if not valid_font_size(size):
            invalid += 1
            continue
        sizes[int(size) if type(size) is float and size.is_integer() else size] += 1
    declared = sizes.total()
    return {
        "nodes": declared + missing + invalid,
        "declared": declared,
        "missing": missing,
        "invalid": invalid,
        "min_font": min(sizes, default=None),
        "below_12fp": sum(n for size, n in sizes.items() if size < 12),
        "below_10fp": sum(n for size, n in sizes.items() if size < 10),
        "histogram": {str(size): sizes[size] for size in sorted(sizes)},
    }


def score(raw):
    """Score one first/final artifact; retain only counts and declared sizes.

    Each Button contributes one label-bearing node. Groups count their own
    positive finite declarations only. A group's known minimum and small-node
    counts do not resolve the font sizes of its missing or invalid declarations.
    """
    if raw is None:
        return {"status": "no_artifact", "legacy": None, "text": None, "button": None}
    legacy = _legacy(raw)
    try:
        graph, _, _ = surface_data(raw)
        nodes = reachable_nodes(graph)
    except (ValueError, TypeError, KeyError, IndexError, RecursionError):
        return {
            "status": "unresolved_tree",
            "legacy": legacy,
            "text": None,
            "button": None,
        }
    return {
        "status": "measured",
        "legacy": legacy,
        "text": _group(nodes, "Text"),
        "button": _group(nodes, "Button"),
    }
