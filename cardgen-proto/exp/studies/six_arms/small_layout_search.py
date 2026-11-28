"""Search standard-font horizontal bands after a small card's existing options fail.

Each band is one leaf, or a row of up to three side-by-side stacks. Stacks and
bands follow the original leaf order. The search uses the existing program's
text measurement and width allocation. Its results still need the normal
downstream checks. Exhausting this grammar is not a general capacity proof.
"""

from copy import deepcopy
from dataclasses import dataclass
from functools import cache
from itertools import combinations, groupby, pairwise
from math import inf

# Standard (non-compact) geometry in harness_v2.program_stages.
_PADDING = 10
_GAP = 4


def _leaves(node):
    if "ref" in node:
        yield node
    else:
        for child in node["children"]:
            yield from _leaves(child)


def _container(kind, children):
    return {"kind": kind, "children": list(children)}


@dataclass
class _Band:
    end: int
    height: float
    wraps: int
    stacks: int
    tree: dict


def iter_layouts(content, base_tree, program):
    """Yield complete trees fitting a 2×2 standard-font reference canvas."""
    if program._canvas(content["size"]) != (150, 150):
        return
    entries, action_refs = program._index(content)
    program._check_tree(base_tree, entries, action_refs)
    leaves = list(_leaves(base_tree["root"]))
    count = len(leaves)
    if not count:
        return
    # Reordering or relabelling the leaves would change the shared input.
    owners = [entries[n["ref"]].get("entity") for n in leaves]
    actions = [n["ref"] in action_refs for n in leaves]
    named_owners = {owner for owner in owners if owner}
    texts = [program._leaf_text(n, entries) for n in leaves]
    styles = [program._font_style(n, entries, False) for n in leaves]
    inside = 150 - 2 * _PADDING
    # Even ignoring all gaps and wraps, at most three stacks can occupy the
    # same vertical space. Reject impossible loads before enumerating cuts.
    if (
        sum(max(30 if a else 0, 1.3 * f + 2) for a, (f, _) in zip(actions, styles))
        > 3 * inside
    ):
        return
    preferred = [
        program._natural_width(text, size, weight) + (12 if action else 0)
        for text, (size, weight), action in zip(texts, styles, actions)
    ]
    measure = program._measure()

    @cache
    def cell(index, width):
        size, weight = styles[index]
        action = actions[index]
        try:
            metric = measure.text(
                texts[index],
                width - (12 if action else 0),
                size,
                max_lines=1 if action else int(150 / size),
                bold=weight >= 600,
                line_height=1.3,
            )
        except ValueError:
            return inf, 0
        height = max(30, metric.height + 6) if action else metric.height
        return height, metric.lines - 1

    def same_scope(start, end):
        return all(owner == owners[start] for owner in owners[start:end])

    def allowed(start, end, cuts):
        # The title keeps a separate band. A global action can form a right
        # rail only beside the entire body, never beside an arbitrary record.
        if any(n["ref"] == "title" for n in leaves[start:end]):
            return end == start + 1
        if not cuts:
            return True
        global_actions = [i for i in range(start, end) if actions[i] and not owners[i]]
        if global_actions and len(global_actions) != end - start:
            body_start = int(leaves[0]["ref"] == "title")
            return (
                start == body_start
                and end == count
                and cuts == (global_actions[0],)
                and global_actions == list(range(global_actions[0], end))
            )
        # Attached actions stay with their record if sharing horizontal space
        # with a different owner. Preserve complete contiguous records at cuts.
        if not same_scope(start, end):
            # With just one named entity, a separately labelled card-level
            # field can sit alongside its labelled data. Neither field adopts
            # the other's scope; values and entity names are not compared.
            if any(not owner for owner in owners[start:end]):
                fields = [entries[n["ref"]] for n in leaves[start:end]]
                return (
                    end - start == 2
                    and len(named_owners) == 1
                    and not any(actions[start:end])
                    and all(
                        f.get("role") == "secondary" and f.get("label") for f in fields
                    )
                )
            for cut in (start, *cuts, end):
                if 0 < cut < count and owners[cut] and owners[cut] == owners[cut - 1]:
                    return False
            bounds = (start, *cuts, end)
            for a, b in pairwise(bounds):
                if not same_scope(a, b):
                    return False
                if not any(
                    not actions[i] and entries[leaves[i]["ref"]].get("label")
                    for i in range(a, b)
                ):
                    return False
        return True

    def stack(a, b):
        groups = []
        for _, positions in groupby(range(a, b), owners.__getitem__):
            members = [leaves[i] for i in positions]
            groups.append(
                members[0] if len(members) == 1 else _container("column", members)
            )
        return groups[0] if len(groups) == 1 else _container("column", groups)

    def band(start, end, cuts):
        bounds = (start, *cuts, end)
        spans = list(pairwise(bounds))
        widths = program._row_widths(
            [max(preferred[a:b]) for a, b in spans], inside - _GAP * (len(spans) - 1)
        )
        stacks = []
        height = wraps = 0
        for (a, b), width in zip(spans, widths):
            cells = [cell(index, width) for index in range(a, b)]
            column_height = sum(h for h, _ in cells) + _GAP * (b - a - 1)
            height = max(height, column_height)
            if height > inside:
                return None
            wraps += sum(w for _, w in cells)
            stacks.append(stack(a, b))
        tree = stacks[0] if len(stacks) == 1 else _container("row", stacks)
        return _Band(end, height, wraps, len(stacks), tree)

    # Dynamic programming gives an exact suffix height for this band grammar.
    # A vertical run is represented by successive single-leaf bands so the
    # same grouping does not need to be considered repeatedly.
    best = [inf] * (count + 1)
    best[count] = 0
    options = [[] for _ in range(count)]
    for start in reversed(range(count)):
        for end in range(start + 1, count + 1):
            suffix = (_GAP if end < count else 0) + best[end]
            if suffix > inside:
                continue
            for columns in range(1 if end == start + 1 else 2, min(3, end - start) + 1):
                for cuts in combinations(range(start + 1, end), columns - 1):
                    if not allowed(start, end, cuts):
                        continue
                    candidate = band(start, end, cuts)
                    if candidate and candidate.height + suffix <= inside:
                        options[start].append(candidate)
                        best[start] = min(best[start], candidate.height + suffix)
        options[start].sort(key=lambda b: (b.wraps, b.stacks, b.height + best[b.end]))

    def paths(start, remaining, prefix):
        if start == count:
            yield {"root": _container("column", deepcopy(prefix))}
            return
        for candidate in options[start]:
            space = (
                remaining - candidate.height - (_GAP if candidate.end < count else 0)
            )
            if best[candidate.end] <= space:
                yield from paths(candidate.end, space, [*prefix, candidate.tree])

    yield from paths(0, inside, [])


def find_layout(content, base_tree, program):
    return next(iter_layouts(content, base_tree, program), None)
