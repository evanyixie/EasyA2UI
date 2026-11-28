"""A6. Count repeated reference values in the frozen first-frame Text nodes."""

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from itertools import product
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from six_arms import reference_content as content
from six_arms import reference_fact_sources as refs
from six_arms.composite_cost_stats import ARMS, PHASES
from six_arms.fixed_content_repeats import check, digest
from six_arms.formal_numeric_fidelity import MATCHER_SHA, registered_reference
from six_arms.formal_reference_cost import ROOT, encode
from six_arms.paired_delivery_bounds import verified
from six_arms.web_geometry_inputs import load_inputs
from src import measure

TABLE = ROOT / "paper/out/tables/formal_repeated_values.json"
GROUPS = ("all_values", "digit_values", "strict_numeric")
LOCATIONS = ("within_only", "across_only", "both", "joined_only")
STATES = (
    "measured",
    "no_artifact",
    "empty_reference",
    "missing_reference",
    "unresolved_text",
)


def numeric_terms(text):
    """Count intact numeric spans within one Text, retaining occurrence multiplicity.

    Apply NFKC before the original unsigned numeric grammar. Exclude matches inside
    ASCII identifiers, signed or separated numbers, or followed by an unconsumed
    unit/ASCII identifier. A bare number immediately followed by Chinese text is
    ambiguous. Explicitly separate adjacent fields at Text boundaries.
    """
    text = unicodedata.normalize("NFKC", text)
    terms = Counter()
    for m in measure._CONTENT_TOKEN_RE.finditer(text):
        token = m.group().rstrip()
        before = text[: m.start()]
        after = text[m.start() + len(token) :]
        if (
            re.search(r"[A-Za-z_0-9.]$|[+−-]\s*$|\d[,/:]$", before)
            or re.match(r"^[.,:/+-]\d", after)
            or re.match(r"^[A-Za-z_0-9]", after)
            or re.match(r"^[%°]", after.lstrip())
            or (token[-1].isdigit() and re.match(r"^[\u3400-\u9fff]", after.lstrip()))
        ):
            continue
        terms[measure._content_norm(token)] += 1
    return terms


def location(counts):
    within = any(n >= 2 for n in counts)
    across = sum(n > 0 for n in counts) >= 2
    if within:
        return "both" if across else "within_only"
    return "across_only" if across else "joined_only"


def tally(values, normalized_nodes, text, strict=None):
    counts = dict.fromkeys(LOCATIONS, 0)
    joined = measure._content_norm(text)
    for value in values:
        key = measure._content_norm(value)
        if strict is None:
            if not key or joined.count(key) < 2:
                continue
            occurrences = [node.count(key) for node in normalized_nodes]
        else:
            occurrences = [terms[key] for terms in strict]
            if sum(occurrences) < 2:
                continue
        counts[location(occurrences)] += 1
    duplicated = sum(counts.values())
    if strict is None:
        registered = measure.check_content(text, [{"value": v} for v in values])
        check(registered["duplicated"] == duplicated, "Historical A6 mismatch")
    return {"reference_values": len(values), "duplicated": duplicated, **counts}


def score(raw, facts):
    """Unknown or missing evidence is kept separate from a measured zero."""
    if raw is None:
        return {"status": "no_artifact"}
    if facts is None:
        return {"status": "missing_reference"}
    if not facts:
        return {"status": "empty_reference"}
    try:
        nodes = content.artifact_text(raw)
    except (ValueError, TypeError, KeyError, IndexError, UnicodeError):
        return {"status": "unresolved_text"}
    text = "\n".join(nodes)
    normalized = [measure._content_norm(node) for node in nodes]
    values = sorted(facts)
    numeric = [
        v
        for v in values
        if any(c.isdecimal() for c in unicodedata.normalize("NFKC", v))
    ]
    whole = [v for v in numeric if measure._content_norm(v) in numeric_terms(v)]
    return {
        "status": "measured",
        "all_values": tally(values, normalized, text),
        "digit_values": tally(numeric, normalized, text),
        "strict_numeric": tally(
            whole, normalized, text, [numeric_terms(node) for node in nodes]
        ),
    }


def summarize(rows):
    rows = list(rows)
    states = Counter(r["status"] for r in rows)
    measured = [r for r in rows if r["status"] == "measured"]
    out = {"assigned": len(rows), "states": {s: states[s] for s in STATES}}
    for group in GROUPS:
        panels = [r[group] for r in measured]
        out[group] = {
            "cards_with_reference_values": sum(
                p["reference_values"] > 0 for p in panels
            ),
            "cards_with_duplicate": sum(p["duplicated"] > 0 for p in panels),
            **{
                k: sum(p[k] for p in panels)
                for k in ("reference_values", "duplicated", *LOCATIONS)
            },
        }
    return out


def run(root, vault):
    root, vault = root.resolve(), vault.resolve()
    check(
        root.is_relative_to(vault) and not vault.is_relative_to(ROOT),
        "Expected isolated custody inputs",
    )
    matcher = ROOT / "cardgen-proto/src/measure.py"
    check(
        digest(matcher.read_bytes().replace(b"\r\n", b"\n")) == MATCHER_SHA,
        "Historical matcher changed",
    )
    references = refs.load_references(root, vault)
    facts, controls = {}, {}
    for task, reference in references.items():
        raw = reference.a2ui_bytes() if isinstance(reference, refs.Reference) else None
        facts[task] = registered_reference(raw)
        controls[task] = score(raw, facts[task])
    observations, cache = {}, {}
    for seat in load_inputs(root):
        key = seat.task, seat.arm, seat.checkpoint
        check(key not in observations, "Duplicate assigned checkpoint")
        lookup = seat.task, seat.artifact_sha256
        if lookup not in cache:
            raw = verified(seat.path, seat.artifact_sha256) if seat.path else None
            cache[lookup] = score(raw, facts[seat.task])
        observations[key] = (seat.artifact_sha256, cache[lookup])
    check(
        len(references) == 219
        and set(observations) == set(product(references, ARMS, PHASES)),
        "Incomplete formal grid",
    )
    return {
        "historical_matcher_sha256_lf": MATCHER_SHA,
        "assigned_checkpoints": len(observations),
        "checkpoint_counts_sha256": digest(
            encode([(*key, *observations[key]) for key in sorted(observations)])
        ),
        "reference_counts_sha256": digest(encode(sorted(controls.items()))),
        "reference_evidence": refs.summary(references),
        "reference_self_check": summarize(controls.values()),
        "formal": {
            phase: {
                arm: summarize(observations[t, arm, phase][1] for t in references)
                for arm in ARMS
            }
            for phase in PHASES
        },
        "interpretation": (
            "Each distinct original reference spelling contributes at most once per card. "
            "The historical count uses non-overlapping substrings after normalization on joined Text. "
            "Digit values include labels containing decimal digits. Strict counts require the entire reference value "
            "to match an intact numeric token in an individual Text. Within/across refer to Text controls, "
            "and joined_only requires concatenating them. No button labels, device pixels, referent identity, "
            "or judgment of unwanted redundancy are inferred."
        ),
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("formal_root", type=Path)
    cli.add_argument("--vault", type=Path)
    cli.add_argument(
        "--output",
        type=Path,
        help="Write a new anonymous aggregate; otherwise verify the published table",
    )
    args = cli.parse_args()
    report = run(args.formal_root, args.vault or args.formal_root.parent)
    if args.output:
        with args.output.open("xb") as handle:
            handle.write(encode(report))
    else:
        check(json.loads(TABLE.read_bytes()) == report, "Published A6 counts differ")
    print("Verified", report["assigned_checkpoints"], "formal checkpoints")
