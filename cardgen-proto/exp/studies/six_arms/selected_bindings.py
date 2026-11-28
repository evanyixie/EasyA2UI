"""Trace exact selected paths into reachable A2UI Text.content and Button.label.

The caller binds the frozen selection and artifact bytes to the same subject.
This checks declared dependencies only. It does not score sample values, entity
ownership, native rendering or device updates.
"""

import json
import re

from six_arms import emit_fidelity
from six_arms.reference_content import surface_data

TEXT_FIELDS = {"Text": "content", "Button": "label"}
CONTAINERS = {"Column", "Row", "Stack", "List", "Grid"}
BASE_FIELDS = {"id", "component", "children", "styles", "itemMargin", "onClick"}


def _pointer(value):
    return (
        isinstance(value, str)
        and value.startswith("/")
        and not re.search(r"~(?![01])", value)
    )


def _unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate A2UI property")
    return result


def _tree(raw):
    # The shared parser accepts JSONL or an array. Reject ambiguous JSON first:
    # parsers may otherwise disagree about which text or child list was kept.
    try:
        json.loads(raw, object_pairs_hook=_unique_object)
    except json.JSONDecodeError:
        for line in raw.splitlines():
            if line.strip():
                json.loads(line, object_pairs_hook=_unique_object)
    graph, _, _ = surface_data(raw)
    nodes = graph["components"]
    if "root" not in graph:
        roots = {c["id"] for c in nodes} - {
            child for c in nodes for child in c.get("children", [])
        }
        if len(roots) != 1:
            raise ValueError("No unique A2UI root")
        graph = {**graph, "root": roots.pop()}
    # This verifies reachability for every returned node, as well as acyclicity,
    # unique IDs, one parent per node and the types of the children and styles.
    return emit_fidelity.graph(graph)


def _dependencies(value):
    if (
        isinstance(value, str)
        and not value.strip().startswith("{{")
        and any(marker in value for marker in ("${", "{{", "}}"))
    ):
        return None
    parts = emit_fidelity.tokens(value)
    if parts is emit_fidelity.UNKNOWN:
        return None
    paths = {token for kind, token in parts if kind == "path"}
    return paths if all(_pointer(p) for p in paths) else None


def inspect_selected(expected_paths, raw):
    """Partition selected paths into present, absent and unresolved frozensets.

    Absence means no exact reference in the fully understood display carriers.
    If a carrier cannot be inspected, matches in understood carriers still count.
    A partial state can have no unresolved paths when all selections were found.
    """
    if expected_paths is None or isinstance(expected_paths, (str, bytes, dict)):
        raise TypeError("Expected a collection of frozen dynamic paths")
    expected = frozenset(expected_paths)
    if not all(_pointer(p) for p in expected):
        raise ValueError("Invalid selected dynamic path")
    found = set()
    if not expected:
        state = "no_selected_paths"
    elif raw is None:
        state = "no_artifact"
    else:
        try:
            root = _tree(raw)
        except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
            state = "invalid_artifact"
        else:
            state = "complete"
            pending = [root]
            while pending:
                branch = pending.pop()
                node = branch["component"]
                kind = node["component"]
                field = TEXT_FIELDS.get(kind)
                if field:
                    paths = _dependencies(node.get(field))
                    if paths is None or node.get("children"):
                        state = "partial"
                    else:
                        found.update(paths)
                elif kind in CONTAINERS:
                    pending.extend(branch["children"])
                elif kind != "Divider" or branch["children"]:
                    state = "partial"
                # Extra component attributes may supply another display carrier
                # (for example a list template). Event arguments are separate.
                if node.keys() - BASE_FIELDS - ({field} if field else set()):
                    state = "partial"
    present = expected & found
    missing = expected - present
    return {
        "expected": expected,
        "present": present,
        "absent": missing if state == "complete" else frozenset(),
        "unresolved": missing if state != "complete" else frozenset(),
        "state": state,
    }
