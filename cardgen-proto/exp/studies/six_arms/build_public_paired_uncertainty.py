"""Build anonymous family and bootstrap frequencies from verified final artifacts in custody."""

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fixed_layout.paired_analysis import N_BOOT, SEED
from six_arms import formal_numeric_fidelity as historical
from six_arms import repair_content_yield as rq2
from six_arms.fixed_content_repeats import check, digest
from six_arms.formal_arm_content_yield import technical
from six_arms.formal_reference_cost import ROOT, registered_sources
from six_arms.formal_repair_receipts import load_repair_rows
from six_arms.paired_delivery_bounds import ROSTER, verified
from six_arms.public_paired_uncertainty import verify_public
from six_arms.technical_yield import read_lines
from six_arms.web_geometry_inputs import load_inputs

TABLES = ROOT / "paper/out/tables"
TABLE = TABLES / "public_paired_uncertainty.json"
ARMS = ("L4", "L5", "L6")


def contrast(pairs, *, seed=SEED, draws=N_BOOT):
    """Take (private family, left state, right state) for exactly one pair per task."""
    families = defaultdict(Counter)
    left_pass = right_pass = lower = upper = 0
    for family, left, right in pairs:
        check(left in rq2.STATES and right in rq2.STATES, "Unrecognized state")
        left_pass += left == "pass"
        right_pass += right == "pass"
        lower += int(left == "pass") - int(right != "fail")
        upper += int(left != "fail") - int(right == "pass")
        families[family]["tasks"] += 1
        families[family]["net"] += int(left == "pass") - int(right == "pass")

    # Both original analyses seeded their draws in private sorted-family order.
    # Publish independent marginal frequencies, never family identities or draw order.
    clusters = [(families[f]["tasks"], families[f]["net"]) for f in sorted(families)]
    check(clusters and draws >= 2, "Empty population or insufficient draws")
    rng = random.Random(seed)
    freq = Counter()
    for _ in range(draws):
        sample = rng.choices(clusters, k=len(clusters))
        freq[Fraction(sum(d for _, d in sample), sum(n for n, _ in sample))] += 1
    return {
        "pass_left": left_pass,
        "pass_right": right_pass,
        "latent_net_bounds": [lower, upper],
        "family_histogram": [
            [n, d, k] for (n, d), k in sorted(Counter(clusters).items())
        ],
        "bootstrap_histogram": [
            [v.numerator, v.denominator, freq[v]] for v in sorted(freq)
        ],
    }


def load_decisions(batch, vault):
    """Reuse the joint endpoint's checks for actual terminal status, sources and artifact bytes."""
    batch, vault = Path(batch).resolve(), Path(vault).resolve()
    check(
        batch.is_relative_to(vault) and not vault.is_relative_to(ROOT),
        "Expected isolated custody inputs",
    )
    matcher = ROOT / "cardgen-proto/src/measure.py"
    check(
        digest(matcher.read_bytes().replace(b"\r\n", b"\n")) == historical.MATCHER_SHA,
        "Historical matcher changed",
    )
    roster = {
        r["task_id"]: r["family"]
        for r in read_lines(batch / "analysis/roster.jsonl", ROSTER)
    }
    check(
        len(roster) == 219 and len(set(roster.values())) == 200,
        "Unexpected formal cohort",
    )
    refs = historical.refs.load_references(batch, vault)
    sources = {
        t: (query, registry) for t, _, query, registry in registered_sources(batch)
    }
    check(roster.keys() == refs.keys() == sources.keys(), "Unmatched source rosters")
    facts = {
        t: historical.registered_reference(
            ref.a2ui_bytes() if isinstance(ref, historical.refs.Reference) else None
        )
        for t, ref in refs.items()
    }
    receipts = {(r["task"], r["arm"]): r for r in load_repair_rows(batch)}
    scores, seats = {}, {}
    for s in load_inputs(batch):
        if s.arm not in ARMS or s.checkpoint != "after_common_repair":
            continue
        seat = (s.task, s.arm)
        r = receipts[seat]
        check(
            seat not in seats
            and s.family == roster[s.task] == r["family"]
            and s.artifact_sha256 == r["final_sha256"],
            "Invalid final checkpoint",
        )
        tech = technical(r)[s.checkpoint]
        check(
            tech != "pass" or s.path is not None,
            "Technical pass without final artifact",
        )
        key = (s.task, s.artifact_sha256)
        if key not in scores:
            raw = verified(s.path, s.artifact_sha256) if s.path else None
            scores[key] = rq2.content_scores(raw, facts[s.task], *sources[s.task])
        score = scores[key]
        seats[seat] = {
            "technical": tech,
            "joint": rq2.joint(tech, score["coverage"], score["fidelity"]),
        }
    check(
        set(seats) == {(t, a) for t in roster for a in ARMS},
        "Incomplete comparison grid",
    )
    return roster, seats


def run(batch, vault):
    roster, seats = load_decisions(batch, vault)
    contrasts = {}
    for endpoint in ("technical", "joint"):
        for arm in ("L4", "L6"):
            pairs = (
                (family, seats[t, "L5"][endpoint], seats[t, arm][endpoint])
                for t, family in roster.items()
            )
            contrasts[f"{endpoint}/L5-{arm}"] = contrast(pairs)
    result = {
        "schema": "public-paired-uncertainty-v1",
        "seed": SEED,
        "bootstrap_replicates": N_BOOT,
        "contrasts": contrasts,
    }
    published = (
        "six_arm_evidence_20261128.json",
        "formal_arm_content_yield.json",
        "repair_content_yield.json",
    )
    verify_public(
        result, *(json.loads((TABLES / name).read_bytes()) for name in published)
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("vault", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Create a new anonymous table; default compares with the published one",
    )
    args = parser.parse_args()
    result = run(args.batch, args.vault)
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as out:
            json.dump(result, out, separators=(",", ":"), allow_nan=False)
            out.write("\n")
    else:
        check(
            result == json.loads(TABLE.read_bytes()),
            "Custody and published histograms differ",
        )
    print(
        "Verified four paired contrasts against the earlier published estimates and intervals."
    )


if __name__ == "__main__":
    main()
