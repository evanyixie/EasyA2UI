"""Compare declared font sizes for identical, uniquely bound first-frame Text values.

The path index is private. Only aggregate paired_report output is for publication.
Roles and labels can differ across arms even when the bound value matches.
"""

import itertools
import re
from collections import Counter

from six_arms import emit_fidelity
from six_arms.composite_cost_stats import ARMS, PHASES
from six_arms.font_declarations import reachable_nodes, valid_font_size
from six_arms.harness_v2.program_stages import StageError, _sample
from six_arms.reference_content import surface_data

PATH_TOKEN = re.compile(r"\$\{(/[^{}]*)\}")
PURE_EXPRESSION = re.compile(r"\s*\{\{\s*\$\{(/[^{}]*)\}\s*\}\}\s*")


def _references(value):
    """Return every detectable referenced path and the exact unmixed path, if any."""
    if isinstance(value, dict):
        path = value.get("path")
        if isinstance(path, str):
            return {path}, path if set(value) == {"path"} else None
        return set(), None
    if not isinstance(value, str):
        return set(), None
    pure = PURE_EXPRESSION.fullmatch(value)
    if pure:
        return {pure[1]}, pure[1]
    tokens = emit_fidelity.tokens(value)
    if tokens is emit_fidelity.UNKNOWN or value.strip().startswith("${"):
        # An unsupported expression cannot supply a match. A mentioned registered
        # path can still make a separate, otherwise eligible Text ambiguous.
        return set(PATH_TOKEN.findall(value)), None
    return {token for kind, token in tokens if kind == "path"}, None


def match_inputs(raw, registered):
    """Return status, referenced paths, and eligible path -> (display text, fp)."""
    empty = {"referenced": set(), "fields": {}}
    if raw is None:
        return {"status": "no_artifact", **empty}
    try:
        graph, data, prefix = surface_data(raw)
        nodes = reachable_nodes(graph)
    except (TypeError, KeyError, IndexError, ValueError, RecursionError):
        return {"status": "unresolved_tree", **empty}
    for key in reversed(prefix):
        data = {key: data}
    occurrences = Counter()
    fields = {}
    for node in nodes:
        if node["component"] != "Text":
            continue
        paths, path = _references(node.get("content"))
        occurrences.update(paths & registered.keys())
        if path not in registered:
            continue
        size = node.get("styles", {}).get("fontSize")
        if not valid_font_size(size):
            continue
        try:
            display = _sample(data, path)
            expected = _sample({"sample": registered[path]}, "/sample")
        except (StageError, OverflowError):
            continue
        if display.strip() and display == expected:
            fields[path] = (display, size)
    return {
        "status": "measured",
        "referenced": set(occurrences),
        "fields": {p: obj for p, obj in fields.items() if occurrences[p] == 1},
    }


def _pairs(pairs):
    """The field denominator counts distinct task-paths, only for two readable graphs."""
    assigned = comparable = matched_cards = union_paths = shared_paths = 0
    field_counts, card_counts = Counter(), Counter()
    for before, after in pairs:
        assigned += 1
        if before["status"] != "measured" or after["status"] != "measured":
            continue
        comparable += 1
        union_paths += len(before["referenced"] | after["referenced"])
        shared_paths += len(before["referenced"] & after["referenced"])
        left, right = before["fields"], after["fields"]
        signs = set()
        for path in left.keys() & right.keys():
            lv, lf = left[path]
            rv, rf = right[path]
            if lv == rv:
                sign = (rf > lf) - (rf < lf)
                signs.add(sign)
                field_counts[sign] += 1
        if signs:
            matched_cards += 1
            changed = signs - {0}
            if len(changed) == 2:
                card_counts["mixed"] += 1
            elif 1 in changed:
                card_counts["only_larger"] += 1
            elif -1 in changed:
                card_counts["only_smaller"] += 1
            else:
                card_counts["all_equal"] += 1
    matched = field_counts.total()
    return {
        "assigned_task_pairs": assigned,
        "both_trees_assessed": comparable,
        "tasks_with_matched_fields": matched_cards,
        "matched_task_rate_assigned": matched_cards / assigned if assigned else None,
        "matched_task_rate_assessed": matched_cards / comparable
        if comparable
        else None,
        "union_referenced_paths_on_assessed_pairs": union_paths,
        "shared_referenced_paths_on_assessed_pairs": shared_paths,
        "matched_field_pairs": matched,
        "matched_rate_shared_paths": matched / shared_paths if shared_paths else None,
        "fields": {
            "larger": field_counts[1],
            "equal": field_counts[0],
            "smaller": field_counts[-1],
        },
        "tasks": {
            k: card_counts[k]
            for k in ("only_larger", "only_smaller", "mixed", "all_equal")
        },
    }


def paired_report(seats):
    """Accept a complete {(task, arm, checkpoint): match_inputs(...)} private mapping.

    Comparisons are second arm minus first, and final minus first. The output does
    not include task identifiers, paths, values, or declarations. Unbound text and
    all text excluded by this matching rule remain outside the field comparison.
    """
    tasks = {t for t, _, _ in seats}
    if not tasks or set(seats) != set(itertools.product(tasks, ARMS, PHASES)):
        raise ValueError("Expected the complete assigned six-arm, two-checkpoint grid")
    return {
        "between": {
            p: {
                f"{a}_to_{b}": _pairs((seats[t, a, p], seats[t, b, p]) for t in tasks)
                for a, b in (("L4", "L5"), ("L5", "L6"))
            }
            for p in PHASES
        },
        "first_to_final": {
            a: _pairs((seats[t, a, PHASES[0]], seats[t, a, PHASES[1]]) for t in tasks)
            for a in ARMS
        },
    }
