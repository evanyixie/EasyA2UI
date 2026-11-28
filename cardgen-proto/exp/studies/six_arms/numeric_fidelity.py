"""A5 first-frame Text-token counts, with conservative whole-token diagnostics.

The main score is the frozen bidirectional-contains metric. For diagnostics,
both display and source use its numeric regex and token normalization. Each
Text is checked separately and contributes only tokens in the original denominator. Discard
spans touching a sign, ASCII word prefix, digit separator, unconsumed ASCII
letter/percent/degree suffix, or a bare number followed by a CJK suffix.
Suffix checks allow whitespace. Exact equality of the remaining tokens is
only evidence about their spelling, not their entity, binding, or truth.
"""

import re
import unicodedata

from six_arms.reference_content import artifact_text
from src import measure

COUNT_FIELDS = (
    "total",
    "supported",
    "fact_only_supported",
    "query_only_supported",
    "both_supported",
    "strict_supported",
    "snapshot_supported_extra",
)


def whole_tokens(value):
    """Compare complete historical numeric tokens; abstain on split numbers and unknown suffixes.

    For example, the legacy scanner sees two tokens in 1,234. Neither fragment
    establishes an exact match for 1 or 234. Negative values are also outside
    its unsigned grammar. Date and time spans already matched in full remain usable.
    """
    if type(value) not in (str, int, float):
        return set()
    text = str(value)
    found = set()
    for match in measure._CONTENT_TOKEN_RE.finditer(text):
        token = match.group().rstrip()
        before = unicodedata.normalize("NFKC", text[: match.start()])
        after = unicodedata.normalize("NFKC", text[match.start() + len(token) :])
        if (
            re.search(r"(?:[A-Za-z+−-]|\d[.,:/])$", before)
            or re.match(r"^[.,:/+-]\d", after)
            or re.match(r"^[A-Za-z%°]", after.lstrip())
            or (token[-1].isdigit() and re.match(r"^[\u3400-\u9fff]", after.lstrip()))
        ):
            continue
        found.add(measure._content_norm(token))
    return found


def score(raw, facts, query, registered):
    """Return counts only. None means unavailable. An empty measured card has a 0/0 ratio.

    facts contains the original unique display values, or None for a missing
    reference. registered maps candidate paths to their frozen sample values.
    Only scalar samples contribute to the exact-value diagnostic.
    """
    row = dict.fromkeys(COUNT_FIELDS)
    if raw is None:
        return {**row, "status": "no_artifact"}
    try:
        nodes = artifact_text(raw)
    except (ValueError, TypeError, KeyError, IndexError):
        return {**row, "status": "unresolved_text"}

    if not isinstance(query, str):
        raise TypeError("Original query must be a string")
    text = "\n".join(nodes)
    fact_rows = [{"value": value} for value in facts] if facts is not None else []
    original = measure.check_content(text, fact_rows, query)
    total = original["tokens"]
    if not total:
        return {**dict.fromkeys(COUNT_FIELDS, 0), "status": "empty_data"}
    if facts is None:
        return {**row, "total": total, "status": "missing_reference"}

    unsupported = set(original["unsupported"])
    unsupported_facts = set(measure.check_content(text, fact_rows)["unsupported"])
    unsupported_query = set(measure.check_content(text, [], query)["unsupported"])
    supported = total - len(unsupported)
    fact_only = len(unsupported_query - unsupported)
    query_only = len(unsupported_facts - unsupported)

    denominator = {
        measure._content_norm(t) for t in measure._CONTENT_TOKEN_RE.findall(text)
    }
    displayed = {t for node in nodes for t in whole_tokens(node)} & denominator
    exact = whole_tokens(query)
    for value in facts:
        exact.update(whole_tokens(value))
    snapshots = set()
    for value in registered.values():
        snapshots.update(whole_tokens(value))
    return {
        "status": "measured",
        "total": total,
        "supported": supported,
        "fact_only_supported": fact_only,
        "query_only_supported": query_only,
        "both_supported": supported - fact_only - query_only,
        "strict_supported": len(displayed & exact),
        "snapshot_supported_extra": len(displayed & unsupported & snapshots),
    }
