"""Optional 2×2 reference geometry for one pair of labelled supporting fields.

The caller preserves accepted cards and runs the usual structure, geometry,
theme, emission and fidelity checks before using a result. This experiment
uses the frozen sample strings and reference fonts.
"""

from functools import cache

_SIDE = 150
_PADDING = 10
_GAP = 4
_INNER = _SIDE - 2 * _PADDING


def _leaves(node):
    if "ref" in node:
        yield node
    else:
        for child in node["children"]:
            yield from _leaves(child)


def _geometry_shape(node):
    if "ref" in node:
        return {"kind": node["kind"], "ref": node["ref"]}
    return {
        "kind": node["kind"],
        "children": [_geometry_shape(c) for c in node["children"]],
    }


def _widths(text, size, weight, measure):
    # The reference wrapper reserves 4vp and compares the advance of each
    # growing line against the rest. Its font is sampled at four times scale.
    font = measure._font(size, weight >= 600)
    widths = set()
    for paragraph in text.split("\n"):
        for start in range(len(paragraph)):
            for stop in range(start + 1, len(paragraph) + 1):
                width = font.getlength(paragraph[start:stop]) / 4 + 4
                if width <= _INNER - _GAP:
                    widths.add(width)
    return widths


def try_geometry(content, standard_tree, stages):
    """Return one candidate, or None if this narrow layout is inapplicable."""
    if stages._canvas(content["size"]) != (_SIDE, _SIDE):
        return None
    entries, actions = stages._index(content)
    stages._check_tree(standard_tree, entries, actions)
    leaves = list(_leaves(standard_tree["root"]))
    owners = {e["entity"] for e in entries.values() if e.get("entity")}
    if len(owners) != 1:
        return None

    def eligible(i):
        node = leaves[i]
        item = entries[node["ref"]]
        return (
            node["kind"] == "text"
            and item.get("role") == "secondary"
            and isinstance(item.get("label"), str)
            and item["label"].strip()
        )

    pairs = [
        i
        for i in range(len(leaves) - 1)
        if eligible(i)
        and eligible(i + 1)
        and any(entries[n["ref"]].get("entity") for n in leaves[i : i + 2])
    ]
    if not pairs:
        return None
    measure = stages._measure()
    styles = [stages._font_style(node, entries, False) for node in leaves]
    texts = [stages._leaf_text(node, entries) for node in leaves]

    @cache
    def cell(i, width):
        node = leaves[i]
        size, weight = styles[i]
        button = node["ref"] in actions
        try:
            metrics = measure.text(
                texts[i],
                width - (12 if button else 0),
                size,
                max_lines=1 if button else int(_SIDE / size),
                bold=weight >= 600,
                line_height=1.3,
            )
        except ValueError:
            return None
        height = max(30, metrics.height + 6) if button else metrics.height
        style = {
            "width": width,
            "height": height,
            "fontSize": size,
            "fontWeight": weight,
            "maxLines": metrics.lines,
            "textAlign": "center" if button else "start",
            "lineHeight": 1.3,
        }
        if button:
            style["borderRadius"] = 16
        return {**node, "style": style}

    full = [cell(i, _INNER) for i in range(len(leaves))]
    if any(node is None for node in full):
        return None
    common = {"itemMargin": _GAP, "alignItems": "start", "justifyContent": "start"}
    total = _INNER - _GAP
    for i in pairs:
        remaining = (
            _INNER
            - _GAP * (len(leaves) - 2)
            - sum(
                n["style"]["height"] for j, n in enumerate(full) if j not in (i, i + 1)
            )
        )
        if max(full[j]["style"]["height"] for j in (i, i + 1)) > remaining:
            continue
        preferred = [stages._natural_width(texts[j], *styles[j]) for j in (i, i + 1)]
        default = stages._row_widths(preferred, total)[0]
        options = {default, total / 2}
        options.update(_widths(texts[i], *styles[i], measure))
        options.update(
            total - w for w in _widths(texts[i + 1], *styles[i + 1], measure)
        )
        # Try the unmodified allocation first. Otherwise prefer a nearby split
        # at a real wrap boundary. Both sides must show their complete text.
        for width in sorted(options, key=lambda w: (abs(w - default), w)):
            if not 0 < width < total:
                continue
            left, right = cell(i, width), cell(i + 1, total - width)
            if left is None or right is None:
                continue
            row_height = max(left["style"]["height"], right["style"]["height"])
            if row_height > remaining:
                continue
            row = {
                "kind": "row",
                "children": [left, right],
                "style": {**common, "width": _INNER, "height": row_height},
            }
            root = {
                "kind": "column",
                "children": [*full[:i], row, *full[i + 2 :]],
                "style": {
                    **common,
                    "padding": _PADDING,
                    "width": _SIDE,
                    "height": _SIDE,
                    "borderRadius": 20,
                    "clip": True,
                },
            }
            return {
                "tree": {"root": _geometry_shape(root)},
                "geometry": {"root": root},
                "pair_refs": [left["ref"], right["ref"]],
                "row_widths": [width, total - width],
                "default_widths": [default, total - default],
            }
    return None
