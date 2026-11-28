"""T03. Probe the frozen structural validator using labelled synthetic edits."""

import argparse
import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from runpy import run_path

PROTO = Path(__file__).resolve().parents[3]
VALIDATOR = PROTO / "src/validate.py"
DEFAULT_TABLE = PROTO.parent / "paper/out/tables/protocol_mutation_coverage.json"
FROZEN_LF_SHA = "294e79853b56dfd8fc319fb31c1e3025c85bd1b0897f7fb39f5b599673ae178e"
FROZEN_WINDOWS_SHA = "477ca13df088164a290140598ccf6910ce89c8ed1f42ac37629dded9eb28e9af"

# Expected primary codes are the experimental labels, defined before invoking the validator.
EDITS = {
    "jsonl.line_count": "Remove one complete message or append one additional message.",
    "jsonl.parse": "Corrupt one JSON message while retaining all three nonblank lines.",
    "envelope.line1": "Add an unexpected top-level key to the creation message.",
    "envelope.line2": "Add an unexpected top-level key to the component message.",
    "envelope.line3": "Add an unexpected top-level key to the data message.",
    "envelope.version": "Change or omit the version of exactly one message.",
    "surface.create_surface": "Change only the surface ID in the creation message.",
    "catalog.id": "Change only the declared catalogue ID.",
    "surface.update_components": "Change only the surface ID in the component message.",
    "tree.root_count": "Duplicate the root node or rename the only root.",
    "tree.dangling_child": "Change one child reference to an unregistered ID.",
    "component.not_allowed": "Change one text node's component type to a disallowed type.",
    "button.action_field": "Attach a legacy action field to a button with its original valid handler.",
    "button.on_click": "Violate the single call-handler contract on one button.",
    "root.canvas": "Change one root dimension.",
    "root.shell": "Change one root clipping or corner-radius property.",
    "data_model.path": "Break the absolute data path or the data message's surface association.",
    "data_model.value": "Remove the initial value from the data message.",
}

# The source facts for each base have their own canvas, tree and initial data.
# Nested (component, id, children...) tuples specify the tree independently of the emitter.
BASES = (
    ("timer", "2x2", ("Column", "root", "lead", "open"), {"minutes": 8}),
    (
        "meter",
        "2x2",
        ("Row", "root", ("Column", "value", "lead", "unit"), "open"),
        {"value": 64, "unit": "%"},
    ),
    (
        "journey",
        "2x4",
        (
            "Row",
            "root",
            ("Column", "out", "lead", "from"),
            ("Column", "back", "to", "open"),
        ),
        {"from": "East", "to": "West"},
    ),
    (
        "diary",
        "2x4",
        ("Column", "root", "lead", ("Row", "line", "day", "event"), "open"),
        {"day": "Fri", "event": "Review"},
    ),
    (
        "checklist",
        "2x2",
        (
            "Column",
            "root",
            ("Row", "heading", "lead", "count"),
            ("Column", "list", "first", "open"),
        ),
        {"items": ["Pack"], "total": 1},
    ),
)


def make_card(case):
    name, size, tree, data = case
    surface = "synthetic-" + name
    nodes = []

    def append(spec):
        if isinstance(spec, str):
            if spec == "open":
                nodes.append(
                    {
                        "id": spec,
                        "component": "Button",
                        "label": "Open",
                        "onClick": [{"call": "open-" + name, "args": {}}],
                    }
                )
            else:
                nodes.append(
                    {
                        "id": spec,
                        "component": "Text",
                        "content": name if spec == "lead" else spec,
                    }
                )
            return
        kind, node_id, *children = spec
        node = {
            "id": node_id,
            "component": kind,
            "children": [
                child if isinstance(child, str) else child[1] for child in children
            ],
        }
        if node_id == "root":
            node["styles"] = {
                "width": 150 if size == "2x2" else 300,
                "height": 150,
                "clip": True,
                "borderRadius": 20,
            }
        nodes.append(node)
        for child in children:
            append(child)

    append(tree)
    return [
        {
            "version": "v0.9",
            "createSurface": {
                "surfaceId": surface,
                "catalogId": "ohos.a2ui.extended.catalog.form",
            },
        },
        {
            "version": "v0.9",
            "updateComponents": {
                "surfaceId": surface,
                "root": "root",
                "components": nodes,
            },
        },
        {
            "version": "v0.9",
            "updateDataModel": {
                "surfaceId": surface,
                "path": "/",
                "value": deepcopy(data),
            },
        },
    ]


def wire(messages):
    return "\n".join(
        json.dumps(m, sort_keys=True, separators=(",", ":")) for m in messages
    )


def read_only_variant(base):
    """Legal control with a different component set; remove the action and its parent reference."""
    messages = deepcopy(base)
    update = messages[1]["updateComponents"]
    update["components"] = [
        node for node in update["components"] if node["id"] != "open"
    ]
    for node in update["components"]:
        if "open" in node.get("children", []):
            node["children"].remove("open")
    return messages


def mutate(base, code, index):
    messages = deepcopy(base)
    if code == "jsonl.line_count":
        if index % 2:
            messages.append(deepcopy(messages[index % 3]))
        else:
            del messages[index % 3]
        return wire(messages)
    if code == "jsonl.parse":
        lines = wire(messages).splitlines()
        lines[index % 3] = lines[index % 3][:-1]
        return "\n".join(lines)

    creation = messages[0]["createSurface"]
    nodes = messages[1]["updateComponents"]["components"]
    by_id = {node["id"]: node for node in nodes}
    root, button = by_id["root"], by_id["open"]
    model = messages[2]["updateDataModel"]
    if code.startswith("envelope.line"):
        messages[int(code[-1]) - 1]["unexpected"] = True
    elif code == "envelope.version":
        message = messages[index % 3]
        if index == 4:
            del message["version"]
        else:
            message["version"] = "v0.8"
    elif code == "surface.create_surface":
        creation["surfaceId"] = "wrong-surface"
    elif code == "catalog.id":
        creation["catalogId"] = "unknown-catalogue"
    elif code == "surface.update_components":
        messages[1]["updateComponents"]["surfaceId"] = "wrong-surface"
    elif code == "tree.root_count":
        if index % 2:
            nodes.append(deepcopy(root))
        else:
            root["id"] = "renamed-root"
    elif code == "tree.dangling_child":
        root["children"][0] = "absent-child"
    elif code == "component.not_allowed":
        by_id["lead"]["component"] = "NotInFormCatalogue"
    elif code == "button.action_field":
        button["action"] = "open"
    elif code == "button.on_click":
        button["onClick"] = (
            [],
            [{"args": {}}],
            [{"call": "a"}, {"call": "b"}],
            {"call": "a"},
            [None],
        )[index]
    elif code == "root.canvas":
        dimension = ("width", "height")[index % 2]
        root["styles"][dimension] -= 1
    elif code == "root.shell":
        if index % 2:
            root["styles"]["clip"] = False
        else:
            root["styles"]["borderRadius"] = 19
    elif code == "data_model.path":
        if index % 2:
            model["surfaceId"] = "wrong-surface"
        else:
            model["path"] = "relative/path"
    elif code == "data_model.value":
        del model["value"]
    else:
        raise ValueError(f"Unregistered mutation {code}")
    return wire(messages)


def observe(validate, text, surface, size):
    try:
        violations = validate(text, surface, size)
    except Exception as exc:  # noqa: BLE001 -- exceptions are a measured validator outcome
        # A validator exception is an observation; it is never credited as a code hit.
        return {"codes": {}, "exception_type": type(exc).__name__}
    return {
        "codes": dict(sorted(Counter(v.code for v in violations).items())),
        "exception_type": None,
    }


def classification(target, obs):
    if obs["exception_type"]:
        return "exception"
    codes = obs["codes"]
    if target in codes:
        return "target_only" if len(codes) == 1 else "target_and_other"
    return "other_only" if codes else "silent"


def build_report():
    source = VALIDATOR.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(source).hexdigest() != FROZEN_LF_SHA:
        raise ValueError("Changed validator source")
    validate = run_path(str(VALIDATOR))["validate_a2ui"]
    cases = [(case, make_card(case)) for case in BASES]
    digest = hashlib.sha256()
    controls = []
    rows = []
    for (name, size, _, _), base in cases:
        for kind, item in (("base", base), ("without_action", read_only_variant(base))):
            text = wire(item)
            digest.update(
                json.dumps([name, kind, text], separators=(",", ":")).encode() + b"\n"
            )
            obs = observe(validate, text, "synthetic-" + name, size)
            controls.append({"context": name, "variant": kind, **obs})
    totals = Counter()
    for code, definition in EDITS.items():
        results = []
        counts = Counter()
        for index, ((name, size, _, _), base) in enumerate(cases):
            text = mutate(base, code, index)
            digest.update(
                json.dumps([name, code, text], separators=(",", ":")).encode() + b"\n"
            )
            obs = observe(validate, text, "synthetic-" + name, size)
            category = classification(code, obs)
            counts[category] += 1
            results.append({"context": name, "outcome": category, **obs})
        totals.update(counts)
        rows.append(
            {
                "target": code,
                "edit": definition,
                "counts": dict(sorted(counts.items())),
                "observations": results,
            }
        )
    return {
        "study": "T03 synthetic A2UI protocol mutations",
        "scope": "The basic three-line protocol validator used by the original six arms. "
        "The host, content, interactions, geometry and additional formal output checks are outside this study.",
        "design": "Five authored tree and data contexts, all with buttons, and five paired display-only controls. "
        "One primary violation per intervention. Removing the version also changes envelope keys. "
        "Renaming the sole root removes the reference required to inspect canvas and shell. "
        "Reported accompanying codes describe the same intervention. Contexts are purposive and paired.",
        "code_inventory": {
            "literal_codes": 15,
            "expanded_line_specific_codes": 3,
            "targets": len(rows),
        },
        "validator_sha256_lf": FROZEN_LF_SHA,
        "formal_validator_sha256_crlf": FROZEN_WINDOWS_SHA,
        "labelled_inputs_sha256": digest.hexdigest(),
        "legal_observations": controls,
        "legal_with_codes": sum(bool(obs["codes"]) for obs in controls),
        "legal_exceptions": sum(obs["exception_type"] is not None for obs in controls),
        "mutation_observations": sum(totals.values()),
        "outcome_counts": dict(sorted(totals.items())),
        "target_code_hits": totals["target_only"] + totals["target_and_other"],
        "per_target": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    output = parser.add_mutually_exclusive_group()
    output.add_argument(
        "--check", action="store_true", help="Compare with the checked-in table"
    )
    output.add_argument("--output", type=Path, help="Write the resulting table")
    args = parser.parse_args()
    report = build_report()
    if args.check:
        if report != json.loads(DEFAULT_TABLE.read_text(encoding="utf-8")):
            raise SystemExit("Protocol mutation table differs from replay")
        print("Protocol mutation table matched.")
    else:
        text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.write_text(text, encoding="utf-8", newline="\n")
        else:
            print(text, end="")


if __name__ == "__main__":
    main()
