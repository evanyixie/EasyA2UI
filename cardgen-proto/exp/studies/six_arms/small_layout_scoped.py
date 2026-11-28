"""Explore order-preserving two-column bands within a single record on a 2×2 card.

The caller tries this only after the frozen candidates have failed and must still
run the original structure, geometry, fidelity and emission checks. Calculations
use the supplied first-frame strings and the standard reference typography.
"""

import re
from functools import cache
from itertools import groupby

_SIDE = 150
_PAD = 10
_GAP = 4
_INNER = _SIDE - 2 * _PAD
_NUMBER = r"[+−-]?\d+(?:[.,]\d+)*(?:[%‰°℃℉]+|[A-Za-zµμ]+)?"
_NUMBER_SPAN = re.compile(rf"{_NUMBER}(?:[:/～~–-]{_NUMBER})*")


def _leaves(node):
    if "ref" in node:
        yield node
    else:
        for child in node["children"]:
            yield from _leaves(child)


def _shape(node):
    if "ref" in node:
        return {"kind": node["kind"], "ref": node["ref"]}
    return {"kind": node["kind"], "children": [_shape(c) for c in node["children"]]}


def _box(kind, children, width):
    if not children or any(c is None for c in children):
        return None
    heights = [c["style"]["height"] for c in children]
    height = max(heights) if kind == "row" else sum(heights) + _GAP * (len(heights) - 1)
    if height > _INNER:
        return None
    if len(children) == 1:
        return children[0]
    return {
        "kind": kind,
        "children": children,
        "style": {
            "width": width,
            "height": height,
            "itemMargin": _GAP,
            "alignItems": "start",
            "justifyContent": "start",
        },
    }


def _value_spans(text, field, stages):
    """Keep each numeric value token together, including its supplied unit."""
    prefix, value, unit = stages._parts(field, field["text"])
    assert prefix + value + unit == text
    printed = value + unit
    if re.fullmatch(r"(?:\d+[^\W\d_])+", printed):
        # A compact value entirely made of number-unit pairs (e.g. 3h5m).
        return [(len(prefix), len(text))]
    spans = []
    for token in _NUMBER_SPAN.finditer(printed):
        end = token.end()
        declared = field.get("unit") or ""
        if declared and printed.startswith(declared, end):
            end += len(declared)
        spans.append((len(prefix) + token.start(), len(prefix) + end))
    return spans


def _unreadable_wrap(text, spans, font, inner):
    def vertical_rail(lines):
        return len(lines) >= 3 and all(len(value.strip()) <= 1 for value in lines)

    lines = []
    line = ""
    for pos, char in enumerate(text):
        if char == "\n":
            lines.append(line)
            if vertical_rail(lines):
                return True
            lines = []
            line = ""
        elif line and font.getlength(line + char) / 4 > inner:
            if any(first < pos < last for first, last in spans):
                return True
            lines.append(line)
            line = char
        else:
            line += char
    lines.append(line)
    return vertical_rail(lines)


def try_geometry(content, base, stages):
    """Return structure and measured geometry, or None if this grammar cannot fit."""
    if stages._canvas(content["size"]) != (_SIDE, _SIDE):
        return None
    entries, action_refs = stages._index(content)
    stages._check_tree(base, entries, action_refs)
    leaves = list(_leaves(base["root"]))
    if not leaves:
        return None
    refs = [n["ref"] for n in leaves]
    fields = [entries[ref] for ref in refs]
    styles = [stages._font_style(n, entries, False) for n in leaves]
    # Even with the operation rail, at most three leaves can occupy the same
    # vertical interval. Bound the search before enumerating possible bands.
    if (
        sum(
            30 if ref in action_refs else size * 1.3 + 2
            for ref, (size, _) in zip(refs, styles)
        )
        > 3 * _INNER
    ):
        return None
    texts = [stages._leaf_text(n, entries) for n in leaves]
    measure = stages._measure()
    # An indivisible leaf that already exceeds maximum lines/cell height at
    # full width cannot become smaller when placed in a narrower column.
    for text, (size, weight), ref in zip(texts, styles, refs):
        button = ref in action_refs
        try:
            m = measure.text(
                text,
                _INNER - (12 if button else 0),
                size,
                max_lines=1 if button else int(_SIDE / size),
                bold=weight >= 600,
                line_height=1.3,
            )
        except ValueError:
            return None
        if m.height + (6 if button else 0) > _INNER:
            return None
    lengths = [stages._natural_width(t, *s) for t, s in zip(texts, styles)]
    spans = [
        _value_spans(t, f, stages) if ref not in action_refs else []
        for t, f, ref in zip(texts, fields, refs)
    ]
    label_width = {
        ref: measure._font(size, weight >= 600).getlength(field["label"]) / 4 + 4
        for ref, field, (size, weight) in zip(refs, fields, styles)
        if ref not in action_refs and field.get("label")
    }

    @cache
    def cell(i, width):
        font_size, weight = styles[i]
        action = refs[i] in action_refs
        text_width = width - (12 if action else 0)
        font = measure._font(font_size, weight >= 600)
        try:
            m = measure.text(
                texts[i],
                text_width,
                font_size,
                max_lines=1 if action else int(_SIDE / font_size),
                bold=weight >= 600,
                line_height=1.3,
            )
        except ValueError:
            return None
        if m.lines > 1 and _unreadable_wrap(texts[i], spans[i], font, text_width - 4):
            return None
        style = {
            "width": width,
            "height": max(30, m.height + 6) if action else m.height,
            "fontSize": font_size,
            "fontWeight": weight,
            "maxLines": m.lines,
            "lineHeight": 1.3,
            "textAlign": "center" if action else "start",
        }
        if action:
            style["borderRadius"] = 16
        return {"kind": leaves[i]["kind"], "ref": refs[i], "style": style}

    @cache
    def breaks(i):
        size, weight = styles[i]
        font = measure._font(size, weight >= 600)
        values = set()
        for line in texts[i].split("\n"):
            for start in range(len(line)):
                for stop in range(start + 1, len(line) + 1):
                    width = font.getlength(line[start:stop]) / 4 + 4
                    if width < _INNER:
                        values.add(width)
        return values

    def stack(a, b, width):
        return _box("column", [cell(i, width) for i in range(a, b)], width)

    def score(node):
        cells = list(_leaves(node))
        return (
            node["style"]["height"],
            sum(n["style"]["maxLines"] for n in cells),
            sum(label_width.get(n["ref"], 0) > n["style"]["width"] for n in cells),
        )

    @cache
    def bands(a, b, width):
        """One record. Only data may share a row. Bound actions get their own line."""
        full = cell(a, width)
        if a + 1 == b:
            return full
        best = _box("column", [full, bands(a + 1, b, width)], width)
        total = width - _GAP
        for end in range(a + 2, b + 1):
            if any(ref in action_refs for ref in refs[a:end]):
                break
            tail = [] if end == b else [bands(end, b, width)]
            if tail and tail[0] is None:
                continue
            for cut in range(a + 1, end):
                options = {total / 2}
                for i in range(a, cut):
                    options.update(breaks(i))
                for i in range(cut, end):
                    options.update(total - w for w in breaks(i))
                for left in sorted(
                    (w for w in options if 0 < w < total),
                    key=lambda w: (abs(w - total / 2), w),
                ):
                    row = _box(
                        "row",
                        [stack(a, cut, left), stack(cut, end, total - left)],
                        width,
                    )
                    proposal = _box("column", [row, *tail], width)
                    if proposal and (not best or score(proposal) < score(best)):
                        best = proposal
        return best

    title_count = int(refs[0] == "title")
    if "title" in refs[title_count:]:
        return None
    action_start = next(
        (
            i
            for i, ref in enumerate(refs)
            if ref in action_refs and not fields[i].get("entity")
        ),
        len(refs),
    )
    if any(
        refs[i] not in action_refs or fields[i].get("entity")
        for i in range(action_start, len(refs))
    ):
        return None

    def records(width):
        groups = []
        for entity, positions in groupby(
            range(title_count, action_start), key=lambda i: fields[i].get("entity")
        ):
            group = list(positions)
            # Independent records occupy separate vertical sections. A missing
            # owner cannot grant permission to place unrelated fields side by side.
            if entity:
                groups.append(bands(group[0], group[-1] + 1, width))
            else:
                groups.extend(cell(i, width) for i in group)
        return _box("column", groups, width)

    if title_count == action_start:
        return None
    data = records(_INNER)
    foot = list(range(action_start, len(refs)))
    alternatives = [data] if not foot else []
    if foot:
        actions = stack(action_start, len(refs), _INNER)
        alternatives.append(_box("column", [data, actions], _INNER))
        # A global action rail can sit next to the entire body, never next
        # to just the last record. Buttons keep their natural single-line width.
        rail = max(lengths[i] for i in foot) + 12
        left = _INNER - _GAP - rail
        if left > 4:
            alternatives.append(
                _box(
                    "row", [records(left), stack(action_start, len(refs), rail)], _INNER
                )
            )

    heading = [cell(0, _INNER)] if title_count else []
    for body in alternatives:
        if body is None:
            continue
        children = [*heading, body]
        inner = _box("column", children, _INNER)
        if inner is None:
            continue
        root = {
            "kind": "column",
            "children": children,
            "style": {
                "width": _SIDE,
                "height": _SIDE,
                "padding": _PAD,
                "itemMargin": _GAP,
                "alignItems": "start",
                "justifyContent": "start",
                "borderRadius": 20,
                "clip": True,
            },
        }
        return {"tree": {"root": _shape(root)}, "geometry": {"root": root}}
    return None
