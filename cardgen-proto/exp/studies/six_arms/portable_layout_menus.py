"""Candidate grammars and deterministic tie-breaking from the registered layout experiment.

Menus use only accepted content, its initial tree and the fixed opaque task key.
The small-card tie breaker uses a task key because the experiment randomized
candidate presentation before ranking; keep it constant when replaying a case.
"""

import copy
import hashlib
import json
import math
import unicodedata
from itertools import pairwise

if __package__:
    from .harness_v2 import program_stages as stage
else:
    from harness_v2 import program_stages as stage


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()


def nodes(root):
    yield root
    for child in root.get("children", []):
        yield from nodes(child)


def leaf_sequence(node):
    return [(leaf["kind"], leaf["ref"]) for leaf in _leaves(node)]


def _leaves(node):
    if "ref" in node:
        yield node
    else:
        for child in node["children"]:
            yield from _leaves(child)


def _category(node, entries):
    row = entries[node["ref"]]
    if node["kind"] == "button":
        return "action"
    return (
        "primary"
        if row.get("role") in stage.PRIMARY_ROLES
        else row.get("role") or "body"
    )


def _group_owner(nodes, entries):
    owners = {entries[n["ref"]].get("entity") or "" for n in nodes}
    return next(iter(owners)) if len(owners) == 1 else None


def _can_pair(a, b, entries, policies):
    left, right = list(_leaves(a)), list(_leaves(b))
    if any(n["ref"] == "title" for n in left + right):
        return False
    owner_a, owner_b = _group_owner(left, entries), _group_owner(right, entries)
    if a["kind"] == b["kind"] == "button":
        return "actions" in policies and owner_a == owner_b
    if a["kind"] == b["kind"] == "text":
        same_role = _category(a, entries) == _category(b, entries)
        if owner_a and owner_a == owner_b and "within" in policies:
            return True
        # An independent cell must carry a visible name before placing it beside a peer.
        visible_labels = all(entries[n["ref"]].get("label") for n in (a, b))
        return "peers" in policies and same_role and visible_labels
    if not ("peers" in policies and owner_a and owner_b and owner_a != owner_b):
        return False
    # Keep each intact record as a column, including any action belonging to it.
    return [(_category(n, entries), n["kind"]) for n in left] == [
        (_category(n, entries), n["kind"]) for n in right
    ]


def _packed(node, entries, policies, target=None, fitting_only=False):
    if "ref" in node:
        return node.copy()
    children = [
        _packed(c, entries, policies, target, fitting_only) for c in node["children"]
    ]
    if node["kind"] != "column":
        return {"kind": node["kind"], "children": children}
    grouped = []
    i = 0
    while i < len(children):
        if i + 1 < len(children) and _can_pair(
            children[i], children[i + 1], entries, policies
        ):
            pair = {"kind": "row", "children": children[i : i + 2]}
            refs = tuple(n["ref"] for n in _leaves(pair))
            if (target is None or target == refs) and (
                not fitting_only or _rough_width(pair, entries) <= 130
            ):
                grouped.append(pair)
                i += 2
                continue
        grouped.append(children[i])
        i += 1
    return {"kind": "column", "children": grouped}


def _rough_glyph_width(s, font):
    # No font engine or measured wrapping. These values are shared estimates in vp.
    return (
        sum(
            0
            if unicodedata.combining(c)
            else 1
            if unicodedata.east_asian_width(c) in ("W", "F")
            else 0.32
            if c.isspace()
            else 0.56
            for c in s
        )
        * font
    )


def _rough_width(node, entries):
    if "ref" in node:
        font, _ = stage._font_style(node, entries, False)
        width = max(
            _rough_glyph_width(s, font)
            for s in stage._leaf_text(node, entries).split("\n")
        )
        return width + (16 if node["kind"] == "button" else 4)
    parts = [_rough_width(child, entries) for child in node["children"]]
    return max(parts) if node["kind"] == "column" else sum(parts) + 4 * (len(parts) - 1)


def _individual_pairs(node, entries):
    children = node.get("children", [])
    if node["kind"] == "column":
        for a, b in pairwise(children):
            if _can_pair(a, b, entries, ("within", "peers", "actions")):
                pair = {"kind": "row", "children": [a, b]}
                yield (
                    _rough_width(pair, entries),
                    tuple(n["ref"] for n in _leaves(pair)),
                )
    for child in children:
        yield from _individual_pairs(child, entries)


def _features(tree, entries, *, canvas_width=150):
    gap, padding = 4, 10
    stats = {
        "action_width_excess_vp": 0.0,
        "extra_text_lines": 0,
        "horizontal_groups": 0,
    }

    def height(node, width):
        kind = node["kind"]
        if kind in ("text", "button"):
            font, _ = stage._font_style(node, entries, False)
            widths = [
                _rough_glyph_width(s, font)
                for s in stage._leaf_text(node, entries).split("\n")
            ]
            usable = max(1.0, width - 4 - (12 if kind == "button" else 0))
            if kind == "button":
                excess = max(0, max(widths) - usable)
                stats["action_width_excess_vp"] = max(
                    stats["action_width_excess_vp"], excess
                )
                return 30
            lines = sum(max(1, math.ceil(w / usable)) for w in widths)
            stats["extra_text_lines"] += lines - 1
            return lines * math.ceil(1.3 * font)
        children = node["children"]
        spaces = gap * (len(children) - 1)
        if kind == "row":
            stats["horizontal_groups"] += 1
            share = (width - spaces) / len(children)
            return max(height(c, share) for c in children)
        return sum(height(c, width) for c in children) + spaces

    stats["estimated_height_vp"] = 2 * padding + height(
        tree["root"], canvas_width - 2 * padding
    )
    stats["action_width_excess_vp"] = round(stats["action_width_excess_vp"], 2)
    return stats


def feature_rank(features):
    height = features["estimated_height_vp"]
    height_excess = max(0, height - 150)
    action_excess = features["action_width_excess_vp"]
    return (
        bool(height_excess or action_excess),
        bool(action_excess),
        height_excess,
        action_excess,
        features["extra_text_lines"],
        features["horizontal_groups"],
        height,
    )


def small_menu(content, base, task_key):
    """The lowest feature score runs first, followed by the remaining frozen menu order."""
    if stage._canvas(content["size"]) != (150, 150):
        raise ValueError("Small-card menu requires a square canvas")
    entries, actions = stage._index(content)
    original = base["root"]
    sequence = leaf_sequence(original)
    seen = set()
    candidates = []

    def add(root):
        key = canonical(root)
        if key in seen:
            return False
        seen.add(key)
        tree = {"root": root}
        stage._check_tree(tree, entries, actions)
        if leaf_sequence(root) != sequence:
            raise ValueError("Candidate changed reference order")
        features = _features(tree, entries)
        score = feature_rank(features)
        order = hashlib.sha256(
            canonical(["small-structure-v1-20261128", task_key, tree])
        ).hexdigest()
        candidates.append((order, score, tree))
        return True

    add(original)
    policies = ("within", "peers", "actions")
    for options in (
        ("within",),
        ("peers",),
        ("actions",),
        ("within", "peers"),
        policies,
    ):
        add(_packed(original, entries, options))
    add(_packed(original, entries, policies, fitting_only=True))
    added = 0
    for _, refs in sorted(
        _individual_pairs(original, entries), key=lambda pair: pair[0]
    ):
        added += add(_packed(original, entries, policies, target=refs))
        if added == 2:
            break
    candidates.sort(key=lambda c: c[0])
    first = min(range(len(candidates)), key=lambda i: candidates[i][1])
    yield candidates[first][2]
    for i, candidate in enumerate(candidates):
        if i != first:
            yield candidate[2]


def _wide_variants(structure, content):
    """仅宽版程序路由。保持实体分组、阅读次序及引用，枚举组内并排和末尾动作区。"""
    if content["size"] != "2x4":
        return []
    entries, _ = stage._index(content)
    original = structure["root"]
    if original["kind"] != "column":
        return []

    def compatible(first, second):
        if first["kind"] != second["kind"] or first["kind"] not in ("text", "button"):
            return False
        if first["kind"] == "button":
            return True
        a, b = entries[first["ref"]], entries[second["ref"]]
        return bool(
            a.get("entity")
            and a["entity"] == b.get("entity")
            and a.get("role") == b.get("role")
            and "title" not in (first["ref"], second["ref"])
        )

    def grouped(node, stride):
        if "children" not in node:
            return copy.deepcopy(node)
        children = [grouped(child, stride) for child in node["children"]]
        if node["kind"] != "column":
            return {**node, "children": children}
        packed = []
        i = 0
        while i < len(children):
            group = [children[i]]
            while (
                len(group) < stride
                and i + len(group) < len(children)
                and compatible(group[0], children[i + len(group)])
            ):
                group.append(children[i + len(group)])
            packed.append(
                group[0] if len(group) == 1 else {"kind": "row", "children": group}
            )
            i += len(group)
        return {**node, "children": packed}

    def group(nodes, kind="column"):
        return nodes[0] if len(nodes) == 1 else {"kind": kind, "children": nodes}

    options = []
    observed = {canonical(original)}

    def append(name, root):
        blob = canonical(root)
        if blob not in observed:
            if leaf_sequence(root) != leaf_sequence(original):
                raise ValueError("Candidate changed reference order")
            observed.add(blob)
            options.append((name, {"root": root}))

    for span in (2, 3):
        append("grouped", grouped(original, span))
    trailing = len(original["children"])
    while trailing and original["children"][trailing - 1]["kind"] == "button":
        trailing -= 1
    if 0 < trailing < len(original["children"]):
        # 整体移动末尾动作区，保留其中所有独立按钮及原顺序；可见标签和事件仍按原引用发射。
        before = group(original["children"][:trailing])
        after = group(original["children"][trailing:])
        for span in (1, 2, 3):
            left = grouped(before, span)
            append("action_rail", {"kind": "row", "children": [left, after]})
    # 宽卡的左主右辅布局将标题锚在左上。根部已接受的操作仍在独立底部区域，
    # 不分配到任一实体，只有已明确的内容分区进入左右两栏。
    head = original["children"][:trailing]
    if len(head) == 2 and head[0].get("ref") == "title":
        title, body = head
        if body["kind"] == "row" and len(body["children"]) == 2:
            lead, detail = body["children"]
        elif body["kind"] == "column" and all(
            n["kind"] == "text" for n in body["children"]
        ):
            members = body["children"]
            cut = 0
            while (
                cut < len(members)
                and entries[members[cut]["ref"]].get("role") in stage.PRIMARY_ROLES
            ):
                cut += 1
            if not 0 < cut < len(members):
                return options
            lead, detail = group(members[:cut]), group(members[cut:])
        else:
            return options
        footer = original["children"][trailing:]
        for span in (1, 2, 3):
            panes = {
                "kind": "row",
                "children": [group([title, lead]), grouped(detail, span)],
            }
            root = group([panes, group(footer, "row")]) if footer else panes
            append("wide_detail", root)
    return options


def wide_menu(content, base):
    """Include the default tree first, then variants preserving action ownership and reading order."""
    yield base
    entries, _ = stage._index(content)
    trailing = []
    for child in reversed(base["root"].get("children", [])):
        if child["kind"] != "button":
            break
        trailing.append(child)
    for name, tree in _wide_variants(base, content):
        if name != "grouped" and any(entries[n["ref"]].get("entity") for n in trailing):
            continue
        for row in nodes(tree["root"]):
            owners = {
                entries[n["ref"]].get("entity")
                for n in row.get("children", ())
                if n["kind"] == "button"
            }
            if row["kind"] == "row" and len(owners) > 1:
                break
        else:
            yield tree
