"""Recompute fixed-content layout counts and latency quantiles without individual records."""

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path
from statistics import median, quantiles

POLICIES = {
    "original": ("l5", "original_prog"),
    "after_wide": ("l5", "previous_prog"),
    "legacy_compatible": ("l5", "l6"),
    "strict_model_native_order": ("strict_model", "strict_program"),
    "strict_original_order": ("fixed_model", "strict_program"),
}
SCOPES = ("all187", "compact153", "wide34", "family_external_compact96")
TIMED = (
    "compatible/all187/assigned",
    "compatible/all187/both_pass",
    "strict/all187/assigned",
    "strict/group_external96/assigned",
)
MEASURES = ("model_ms", "program_ms", "paired_model_minus_program_ms")
CELLS = ("both", "only_l5", "only_l6", "neither")


def bin_times(values):
    """Means of consecutive rank blocks preserve the median and nearest-rank P95."""
    v = sorted(values)
    n = len(v)
    if not n or not all(math.isfinite(x) for x in v):
        raise ValueError("Expected finite paired timing observations")
    p95 = math.ceil(0.95 * n) - 1
    cuts = sorted({0, n // 4, (n - 1) // 2, n // 2 + 1, 3 * n // 4, p95, p95 + 1, n})
    return [[j - i, round(sum(v[i:j]) / (j - i), 6)] for i, j in pairwise(cuts)]


def read_sealed(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"Seal mismatch for {path.name}")
    return raw


def from_vault(batch, reference):
    """Custodian-only compilation. No source identifier or selection order is exported."""
    from layout_fallback_replay import replay

    replay(
        batch, reference
    )  # Reconcile input and selected content with the sealed L5 calls.
    seals = json.loads(reference.read_bytes())["sources_sha256"]
    folder = batch / "same_content_l56_followup"
    pairs = json.loads(
        read_sealed(folder / "paired187.private.json", seals["joined_cases"])
    )
    timings = json.loads(
        read_sealed(folder / "timing/times.private.json", seals["paired_timings"])
    )
    baseline = read_sealed(
        batch / "l56_focus_20261128/candidate_followup/selection.private.jsonl",
        seals["selection.private.jsonl"],
    )
    prior = {
        row["task"]: row
        for row in map(json.loads, baseline.splitlines())
        if row.get("content_sha")
    }
    if len(prior) != len(pairs) or set(prior) != {r["task"] for r in pairs}:
        raise ValueError("Different eligible populations")
    for row in pairs:
        old = prior[row["task"]]
        if (
            old["content_sha"] != row["content_sha256"]
            or bool(old["baseline_sha"]) != row["original_prog"]
            or bool(old["selected_sha"]) != row["previous_prog"]
            or any(
                sha and sha != row["sha_l6"]
                for sha in (old["baseline_sha"], old["selected_sha"])
            )
        ):
            raise ValueError(
                "A prior successful result changed or selected content differs"
            )
    scopes = dict(
        zip(
            SCOPES,
            (
                pairs,
                [r for r in pairs if r["size"] == "2x2"],
                [r for r in pairs if r["size"] == "2x4"],
                [r for r in pairs if r["external"]],
            ),
        )
    )
    quality = {}
    for name, (a, b) in POLICIES.items():
        tables = {}
        for scope, rows in scopes.items():
            groups = defaultdict(lambda: [0, 0, 0, 0])
            for r in rows:
                if type(r[a]) is not bool or type(r[b]) is not bool:
                    raise ValueError("Missing paired decision")
                groups[r["family"]][(0 if r[a] else 2) + (0 if r[b] else 1)] += 1
            counts = list(map(sum, zip(*groups.values())))
            if scope == "all187":
                patterns = Counter((sum(c), c[2] - c[1]) for c in groups.values())
                tables[scope] = {
                    "counts": counts,
                    "families_by_size_and_net": [
                        [size, net, k] for (size, net), k in sorted(patterns.items())
                    ],
                }
            else:
                tables[scope] = counts
        quality[name] = tables
    latency = {}
    for label in TIMED:
        policy, scope, subset = label.split("/")
        rows = [
            r[policy]
            for r in timings
            if (scope == "all187" or r["transfer"])
            and (subset == "assigned" or all(r[policy]["passes"].values()))
        ]
        vectors = (
            [r["model_ms"] for r in rows],
            [r["program_ms"] for r in rows],
            [r["model_ms"] - r["program_ms"] for r in rows],
        )
        latency[label] = {k: bin_times(v) for k, v in zip(MEASURES, vectors)}
    return {
        "schema": "fixed-layout-distributions-v1",
        "cell_order": list(CELLS),
        "quality": quality,
        "latency_rank_blocks": latency,
    }


def group_interval(patterns):
    """Cluster percentile interval, deterministic using anonymous pattern order."""
    clusters = [
        (net, size) for size, net, count in sorted(patterns) for _ in range(count)
    ]
    rng = random.Random(20261124)
    samples = []
    for _ in range(10000):
        draw = rng.choices(clusters, k=len(clusters))
        samples.append(100 * sum(d for d, _ in draw) / sum(n for _, n in draw))
    cuts = quantiles(samples, n=1000, method="inclusive")
    return [round(cuts[24], 3), round(cuts[974], 3)]


def get_quantiles(blocks):
    if not blocks or any(
        type(n) is not int
        or n <= 0
        or type(x) not in (int, float)
        or not math.isfinite(x)
        for n, x in blocks
    ):
        raise ValueError("Invalid timing rank block")
    values = [x for n, x in blocks for _ in range(n)]
    if values != sorted(values):
        raise ValueError("Unordered timing rank blocks")
    return {
        "n": len(values),
        "median": median(values),
        "p95": values[math.ceil(0.95 * len(values)) - 1],
    }


def summarize(source):
    if (
        source["schema"] != "fixed-layout-distributions-v1"
        or source["cell_order"] != list(CELLS)
        or set(source["quality"]) != set(POLICIES)
        or set(source["latency_rank_blocks"]) != set(TIMED)
    ):
        raise ValueError("Unexpected distribution schema")
    results = {"quality": {}, "timing_ms": {}}
    for policy, scopes in source["quality"].items():
        if set(scopes) != set(SCOPES):
            raise ValueError("Missing quality population")
        tables = {}
        for scope, data in scopes.items():
            counts = data["counts"] if scope == "all187" else data
            if len(counts) != 4 or any(type(x) is not int or x < 0 for x in counts):
                raise ValueError("Invalid paired contingency table")
            both, model, program, _ = counts
            tables[scope] = {
                **dict(zip(CELLS, counts)),
                "requests": sum(counts),
                "l5": both + model,
                "l6": both + program,
            }
            if scope == "all187":
                groups = data["families_by_size_and_net"]
                if (
                    not groups
                    or any(
                        len(p) != 3
                        or any(type(x) is not int for x in p)
                        or p[0] < 1
                        or abs(p[1]) > p[0]
                        or p[2] < 1
                        for p in groups
                    )
                    or sum(size * n for size, _, n in groups) != sum(counts)
                    or sum(net * n for _, net, n in groups) != program - model
                ):
                    raise ValueError("Family patterns disagree with the paired table")
                tables[scope].update(
                    families=sum(n for _, _, n in groups),
                    anonymous_family_ci95_pp=group_interval(groups),
                )
        results["quality"][policy] = tables
    for label, measures in source["latency_rank_blocks"].items():
        if set(measures) != set(MEASURES):
            raise ValueError("Missing latency measure")
        results["timing_ms"][label] = {k: get_quantiles(v) for k, v in measures.items()}
    return results


def verify(result, reference):
    for policy, scopes in result["quality"].items():
        for scope, actual in scopes.items():
            compare = reference["paired_quality"]["legacy_compatible"][scope]
            if actual["requests"] != compare["requests"] or (
                policy in ("original", "after_wide") and actual["l5"] != compare["l5"]
            ):
                raise ValueError(
                    f"Different L5 baseline or population for {policy}/{scope}"
                )
            if policy in reference["paired_quality"]:
                old = reference["paired_quality"][policy][scope]
                if any(
                    actual[k] != old[k]
                    for k in actual
                    if k != "anonymous_family_ci95_pp"
                ):
                    raise ValueError(f"Paired counts disagree for {policy}/{scope}")
            elif scope == "all187":
                legacy = reference["baseline_to_enhanced_compatible"]
                if (
                    actual["l6"]
                    != legacy[
                        {"original": "original", "after_wide": "after_wide_candidates"}[
                            policy
                        ]
                    ]
                ):
                    raise ValueError(f"Baseline count differs for {policy}")
    for label, measures in result["timing_ms"].items():
        old = reference["paired_timing"][label]
        for k, actual in measures.items():
            if actual["n"] != old["n"] or any(
                abs(actual[q] - old[k][q]) > 0.000501 for q in ("median", "p95")
            ):
                raise ValueError(f"Latency disagrees for {label}/{k}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("distributions", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument(
        "--check-vault",
        type=Path,
        help="Independently rebuild the anonymous distributions in memory.",
    )
    args = parser.parse_args()
    public = json.loads(args.distributions.read_bytes())
    if args.check_vault and from_vault(args.check_vault, args.reference) != public:
        raise ValueError("Published distributions differ from sealed records")
    output = summarize(public)
    verify(output, json.loads(args.reference.read_bytes()))
    print(json.dumps(output, indent=2))
