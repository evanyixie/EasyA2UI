"""Frozen enhanced program policies for already-selected card content.

The caller supplies the common six-stage execution engine, including its fonts,
measurement and final source/geometry checks. No dataset, experiment outcomes,
model callbacks or device are consulted. The two returned SHA-256 identities
refer to exact accepted A2UI bytes. The compatible policy permits original
compact typography. The standard policy verifies the reference role sizes.
"""

import hashlib
from dataclasses import dataclass

if __package__:
    from . import (
        emit_fidelity,
        small_layout_column_widths,
        small_layout_scoped,
        small_layout_search,
    )
    from . import portable_layout_menus as menus
    from .small_layout_measure_cache import ScopedSearch
else:
    import emit_fidelity
    import portable_layout_menus as menus
    import small_layout_column_widths
    import small_layout_scoped
    import small_layout_search
    from small_layout_measure_cache import ScopedSearch


def require(condition, message):
    if not condition:
        raise ValueError(message)


def frame_issue(root):
    for node in menus.nodes(root):
        children = node.get("children", ())
        if not children:
            continue
        style = node["style"]
        gap = style.get("itemMargin", 0) * (len(children) - 1)
        pad = 2 * style.get("padding", 0)
        for dimension, axis in (("width", "row"), ("height", "column")):
            lengths = [child["style"][dimension] for child in children]
            need = sum(lengths) + gap if node["kind"] == axis else max(lengths)
            if need + pad > style[dimension] + 1e-5:
                return dimension + "_overflow"
    return None


def advance(engine, phase, content, tree, source):
    wire = engine._program_wire(phase, content, tree, source)
    return engine.model.parse_output(phase, wire, source, content=content, tree=tree)


def parse(engine, phase, content, value, source, prior=None):
    return engine.model.parse_output(
        phase, engine.trial.signature(value), source, content=content, tree=prior
    )


@dataclass(frozen=True)
class TreeResult:
    status: str
    strict_verdict: str
    accepted_sha: str | None = None
    standard_sha: str | None = None
    compatible_fallback_sha: str | None = None


def score_tree(engine, content, source, entry, tree):
    try:
        shape = parse(engine, "structure", content, tree, source)
        geometry = advance(engine, "geometry", content, shape, source)
        theme = advance(engine, "theme", content, geometry, source)
        messages = advance(engine, "emit", content, theme, source)
    except engine.STAGE_ERRORS:
        return TreeResult("stage_rejected", "fail")
    entries, _ = engine.program._index(content)
    fonts_ok = all(
        n["style"]["fontSize"] == engine.program._font_style(n, entries, False)[0]
        for n in menus.nodes(geometry["root"])
        if "ref" in n
    )
    review = emit_fidelity.audit(content, theme, messages, source)["status"]
    result = {"entry": {"status": entry["status"]}}
    engine._finish(messages, source, result)
    status = result["status"]
    first, last = result["first_native"]["sha256"], result["final_native"]["sha256"]
    unchanged = first == last
    accepted_sha = last if status == "accepted" else None
    fallback = accepted_sha if fonts_ok and unchanged else None
    if (
        not fonts_ok
        or frame_issue(geometry["root"])
        or review == "different"
        or not unchanged
        or status not in ("accepted", "geometry_unknown")
    ):
        strict = "fail"
    elif status == "geometry_unknown" or review == "unknown":
        strict = "unknown"
    else:
        strict = "pass"
    return TreeResult(
        status, strict, accepted_sha, first if strict == "pass" else None, fallback
    )


def evaluate_model(content, source, entry, tree, engine):
    """Score exactly the supplied structure and its order under both policies."""
    result = score_tree(engine, content, source, entry, tree)
    return (
        {"compatible": result.accepted_sha, "standard": result.standard_sha},
        {"compatible": result.status, "standard": result.strict_verdict},
    )


def strip_style(node):
    return {
        k: [strip_style(child) for child in value] if k == "children" else value
        for k, value in node.items()
        if k != "style"
    }


def refs(node):
    return [ref for _, ref in menus.leaf_sequence(node)]


def check_scopes(root, entries, actions):
    global_actions = {r for r in actions if not entries[r].get("entity")}
    body = [r for r in refs(root) if r != "title" and r not in global_actions]
    for node in menus.nodes(root):
        if node["kind"] != "row":
            continue
        columns = [refs(child) for child in node["children"]]
        members = [ref for column in columns for ref in column]
        rail = global_actions.intersection(members)
        if rail:
            require(
                set(members) == rail
                or (
                    len(columns) == 2
                    and columns[0] == body
                    and set(columns[1]) == global_actions
                ),
                "Global action appears beside a partial record",
            )
        else:
            owners = {entries[r].get("entity") for r in members}
            require(
                "title" not in members
                and len(owners) == 1
                and None not in owners
                and "" not in owners,
                "Horizontal row mixed record owners",
            )


def check_secondary_pair(root, entries, proposal):
    rows = [n for n in root["children"] if "children" in n]
    require(
        root["kind"] == "column" and len(rows) == 1 and rows[0]["kind"] == "row",
        "Expected one horizontal band",
    )
    pair = rows[0]["children"]
    require(
        len(pair) == 2
        and all(n["kind"] == "text" and n.get("ref") in entries for n in pair),
        "Expected two fields",
    )
    items = [entries[n["ref"]] for n in pair]
    require(
        all(
            x.get("role") == "secondary"
            and isinstance(x.get("label"), str)
            and x["label"].strip()
            for x in items
        ),
        "Two visible secondary labels required",
    )
    require(
        any(x.get("entity") for x in items)
        and len({x["entity"] for x in entries.values() if x.get("entity")}) == 1,
        "Ambiguous ownership",
    )
    require(
        [n["ref"] for n in pair] == proposal["pair_refs"]
        and [n["style"]["width"] for n in pair] == proposal["row_widths"],
        "Reported pair disagrees with geometry",
    )


def wrap(text, font, width):
    lines = [""]
    for char in text:
        if char == "\n":
            lines.append("")
        elif lines[-1] and font.getlength(lines[-1] + char) / 4 > width - 4:
            lines.append(char)
        else:
            lines[-1] += char
    return lines


def check_line_breaks(lines, text, spans):
    require(
        len(lines) < 3 or any(len(line.strip()) > 1 for line in lines),
        "Vertical chain of single glyphs",
    )
    offset = 0
    for line in lines[:-1]:
        offset += len(line)
        if text[offset : offset + 1] == "\n":
            offset += 1
        else:
            require(
                not any(lo < offset < hi for lo, hi in spans),
                "Split numeric token or unit",
            )


def check_measured_leaf(node, engine, entries, actions, scoped):
    ref = node["ref"]
    style = node["style"]
    size, weight = engine.program._font_style(node, entries, False)
    require(
        (style["fontSize"], style["fontWeight"], style["lineHeight"])
        == (size, weight, 1.3),
        "Nonstandard typography",
    )
    button = node["kind"] == "button"
    require(button == (ref in actions), "Changed action role")
    padding = 2 * style.get("padding", 0)
    width = style["width"] - padding - (12 if button else 0)
    text = engine.program._leaf_text(node, entries)
    oracle = engine.program._measure()
    measured = oracle.text(
        text,
        width,
        size,
        bold=weight >= 600,
        max_lines=1 if button else int(150 / size),
        line_height=1.3,
    )
    height = max(30, measured.height + 6) if button else measured.height
    require(
        style["maxLines"] == measured.lines
        and style["height"] - padding + (1e-7 if scoped else 1e-6) >= height,
        "Measured text exceeds frame",
    )
    if scoped:
        lines = wrap(text, oracle._font(size, weight >= 600), width)
        require(len(lines) == measured.lines, "Reference wrapping disagrees")
        if not button and len(lines) > 1:
            spans = small_layout_scoped._value_spans(text, entries[ref], engine.program)
            check_line_breaks(lines, text, spans)


def assess_geometry(content, source, base, proposal, engine, scoped):
    """Validate a custom small-card width allocation and return exact native bytes."""
    tree = parse(engine, "structure", content, proposal["tree"], source)
    geometry = parse(engine, "geometry", content, proposal["geometry"], source, tree)
    root = geometry["root"]
    require(
        strip_style(root) == tree["root"], "Geometry differs from proposed structure"
    )
    sequence = menus.leaf_sequence(root)
    entries, actions = engine.program._index(content)
    require(
        sequence == menus.leaf_sequence(base["root"])
        and {r for _, r in sequence} == set(entries),
        "Changed selected references or order",
    )
    require(
        "title" not in entries or root["children"][0].get("ref") == "title",
        "Title lost its own line",
    )
    if scoped:
        require(
            len(sequence) == len(set(sequence))
            and ("title" not in entries or root["kind"] == "column"),
            "Duplicate reference or title frame",
        )
        check_scopes(root, entries, actions)
    else:
        check_secondary_pair(root, entries, proposal)
    style = root["style"]
    require(
        (style["width"], style["height"], style["padding"]) == (150, 150, 10)
        and frame_issue(root) is None,
        "Canvas overflow",
    )
    for node in menus.nodes(root):
        if "children" in node:
            style = node["style"]
            require(
                style["itemMargin"] == 4
                and (
                    not scoped or style.get("padding", 0) == (10 if node is root else 0)
                ),
                "Changed spacing",
            )
        else:
            check_measured_leaf(node, engine, entries, actions, scoped)
    theme = advance(engine, "theme", content, geometry, source)
    messages = advance(engine, "emit", content, theme, source)
    fidelity = emit_fidelity.audit(content, theme, messages, source)
    require(
        fidelity["status"] == "matched" and not fidelity["findings"],
        "Native fidelity unresolved",
    )
    result = {"entry": {"status": "valid"}}
    engine._finish(messages, source, result)
    native = engine._native_wire(messages, "\r\n")
    require(
        result["status"] == "accepted"
        and result["first_native"]["text"].encode()
        == native
        == result["final_native"]["text"].encode(),
        "Reference exit changed the emitted artifact",
    )
    return hashlib.sha256(native).hexdigest()


def small_standard(task, content, source, entry, engine, base):
    unknown = False
    for trees in (
        menus.small_menu(content, base, task),
        small_layout_search.iter_layouts(content, base, engine.program),
    ):
        for tree in trees:
            require(
                menus.leaf_sequence(tree["root"]) == menus.leaf_sequence(base["root"]),
                "Candidate reordered references",
            )
            result = score_tree(engine, content, source, entry, tree)
            if result.standard_sha:
                return result.standard_sha, False
            unknown |= result.strict_verdict == "unknown"
    for scoped, proposer in (
        (False, small_layout_column_widths),
        (True, ScopedSearch(small_layout_scoped)),
    ):
        proposal = proposer.try_geometry(content, base, engine.program)
        if proposal is None:
            continue
        try:
            return assess_geometry(
                content, source, base, proposal, engine, scoped
            ), False
        except (ValueError, RuntimeError):
            # Frozen custom-geometry verification marks unresolved proposals separately.
            unknown = True
    return None, unknown


def select(task_key, content, source, entry, engine):
    """Return (exact_artifact_hashes, decisions) keyed by compatible and standard."""
    base = engine.program.program_route(content)
    if content["size"] == "2x2":
        standard, standard_unknown = small_standard(
            task_key, content, source, entry, engine, base
        )
        original = score_tree(engine, content, source, entry, base)
        compatible = original.accepted_sha or standard
        compatible_unknown = standard_unknown or original.status in {
            "geometry_unknown",
            "execution_error",
        }
    else:
        require(content["size"] == "2x4", "Unsupported canvas")
        standard = compatible = None
        standard_unknown = compatible_unknown = False
        for i, tree in enumerate(menus.wide_menu(content, base)):
            result = score_tree(engine, content, source, entry, tree)
            if not compatible:
                compatible = (
                    result.accepted_sha if i == 0 else result.compatible_fallback_sha
                )
                compatible_unknown |= result.status in {
                    "geometry_unknown",
                    "execution_error",
                }
            if not standard:
                standard = result.standard_sha
                standard_unknown |= result.strict_verdict == "unknown"
            if standard and compatible:
                break

    def decision(artifact, uncertain):
        if artifact:
            return "pass"
        return "unknown" if uncertain else "no_policy_hit"

    return (
        {"compatible": compatible, "standard": standard},
        {
            "compatible": decision(compatible, compatible_unknown),
            "standard": decision(standard, standard_unknown),
        },
    )
