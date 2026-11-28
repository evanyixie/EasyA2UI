"""Offline preflight for the prospective 12 × 6 × 10 full-request stability study.

No model, render, private answer or scoring dependency. The historical paper specified
report cases sampled after P8 by size and layout, six arms, ten draws at temperature
1. The family constraint, allocation rule, seed and ordering below were set after the
original six-arm run for this future study. They never alter that run.
"""

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path

SIZES = ("2x2", "2x4")
ARMS = tuple(f"L{i}" for i in range(1, 7))
SEED = "formal-endpoint-stability-prospective-20261128-v1"
N, DRAWS = 12, 10
ROOT = Path(__file__).resolve().parents[4]
JOB_WIRE = {
    "model": "deepseek-flash",
    "temperature": 1.0,
    "thinking": {"type": "disabled"},
    "stream": False,
    "max_tokens": 8192,
}
RULE = "Equalize the two size counts subject to 12 distinct families; within each size prefer the least represented feasible layout. Seeded SHA-256 breaks ties and determines arm/draw order."
UNDETERMINED = {
    "unknown",
    "undetermined",
    "unresolved",
    "未知",
    "待定",
    "未判定",
    "无法判定",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rank(*parts):
    return sha(canonical([SEED, *parts]))


def valid_rows(rows):
    require(isinstance(rows, list) and bool(rows), "Empty metadata roster")
    for row in rows:
        require(
            isinstance(row, dict) and set(row) == {"task", "family", "size", "layout"},
            "Use the four metadata fields only",
        )
        require(
            all(isinstance(v, str) and v.strip() == v and v for v in row.values()),
            "Missing metadata",
        )
        require(
            bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", row["task"])),
            "Invalid opaque task key",
        )
        require(row["size"] in SIZES, "Unknown size")
    require(
        len({r["task"].casefold() for r in rows}) == len(rows), "Duplicate task key"
    )


def match(groups, slots):
    """Assign a distinct family to every slot; (size, None) can take any layout."""
    owner, assigned = {}, {}

    def augment(i, visited):
        for family in groups[slots[i]]:
            if family not in visited:
                visited.add(family)
                if family not in owner or augment(owner[family], visited):
                    owner[family] = i
                    assigned[i] = family
                    return True
        return False

    for i in sorted(range(len(slots)), key=lambda j: len(groups[slots[j]])):
        if not augment(i, set()):
            return None
    return [assigned[i] for i in range(len(slots))]


def select(rows):
    valid_rows(rows)
    rows = [
        {**r, "layout": "undetermined"} if r["layout"].casefold() in UNDETERMINED else r
        for r in rows
    ]
    members = defaultdict(list)
    for r in rows:
        members[r["size"], r["layout"]].append(r)
    groups = {}
    for size in SIZES:
        for layout in [None, *sorted(layout for s, layout in members if s == size)]:
            family_set = {
                r["family"]
                for r in rows
                if r["size"] == size and (layout is None or r["layout"] == layout)
            }
            groups[size, layout] = sorted(
                family_set, key=lambda f: (rank("family", size, layout, f), f)
            )
    # First fix the best *feasible* size split while every layout is still available.
    splits = sorted(range(N + 1), key=lambda a: (abs(2 * a - N), rank("size-quota", a)))
    slots = []
    for a in splits:
        trial = [(SIZES[0], None)] * a + [(SIZES[1], None)] * (N - a)
        if match(groups, trial) is not None:
            slots = trial
            break
    if not slots:
        totals = {s: len(groups[s, None]) for s in SIZES}
        by_cell = {cell: len(groups[cell]) for cell in sorted(members)}
        raise ValueError(
            f"Cannot select 12 different families. Distinct families by size: {totals}; "
            f"by size/layout: {by_cell}; across sizes: {len({r['family'] for r in rows})}"
        )
    quota = Counter(s for s, _ in slots)
    sizes = sorted(SIZES, key=lambda s: rank("size-order", s))
    for step in range(max(quota.values())):
        for size in sizes:
            if step >= quota[size]:
                continue
            i = slots.index((size, None))
            cells = sorted(
                (c for c in members if c[0] == size),
                key=lambda c: (slots.count(c), rank("layout", *c), c),
            )
            for cell in cells:
                slots[i] = cell
                if match(groups, slots) is not None:
                    break
            else:
                raise AssertionError("A feasible size slot lost all available families")
    families = match(groups, slots)
    selected = [
        min(
            (r for r in members[cell] if r["family"] == family),
            key=lambda r: (rank("task", r["task"]), r["task"]),
        )
        for cell, family in zip(slots, families, strict=True)
    ]
    counts = [
        {
            "size": s,
            "layout": l,
            "candidates": len(items),
            "families": len(groups[s, l]),
            "selected": slots.count((s, l)),
        }
        for (s, l), items in sorted(members.items())
    ]
    return sorted(selected, key=lambda r: r["task"]), counts


def jobs(selected):
    rows = [
        {
            "task": r["task"],
            "arm": a,
            "rep": n,
            "order_hash": rank("execution", r["task"], a, n),
        }
        for r, a, n in product(selected, ARMS, range(1, DRAWS + 1))
    ]
    return sorted(rows, key=lambda j: j["order_hash"])


def layout_coverage(counts):
    unknown = [r for r in counts if r["layout"] == "undetermined"]
    observed = {
        r["layout"] for r in counts if r["layout"] != "undetermined" and r["selected"]
    }
    return {
        "undetermined_candidate_rows": sum(r["candidates"] for r in unknown),
        "undetermined_selected_rows": sum(r["selected"] for r in unknown),
        "known_layouts_in_roster": len(
            {r["layout"] for r in counts if r["layout"] != "undetermined"}
        ),
        "known_layouts_in_selection": len(observed),
        "interpretation": "known_layout_strata_reported"
        if observed
        else "conditional_schedule_only_no_known_layout_coverage",
    }


def make_plan(rows, mode, source):
    require(
        mode in {"synthetic_dry_run", "custodian_schedule_only"},
        "Invalid evidence mode",
    )
    require(len(rows) == 219, "Expected the full 219-row report metadata roster")
    selected, counts = select(rows)
    return {
        "specification": {
            "schema": "prospective-endpoint-stability-schedule-v1",
            "evidence_mode": mode,
            "seed": SEED,
            "allocation": RULE,
            "metadata_source": source,
            "candidate_rows": len(rows),
            "selected": selected,
            "strata": counts,
            "layout_coverage": layout_coverage(counts),
            "order": jobs(selected),
            "total_seats": N * len(ARMS) * DRAWS,
            "payload_except_messages": JOB_WIRE,
            "execution_status": "Schedule only. Before execution the custodian must authenticate P8 and independent metadata, register this plan digest, and separately freeze each source, registry, initial arm messages, runner, dependency and endpoint version. No calls are sent here.",
        }
    }


def private_plan(roster_bytes, expected_roster_sha, p8_bytes, expected_p8_sha):
    require(
        sha(roster_bytes) == expected_roster_sha
        and sha(p8_bytes) == expected_p8_sha
        and bool(p8_bytes),
        "Custody references differ from supplied fingerprints",
    )
    meta = json.loads(roster_bytes)
    require(
        isinstance(meta, dict)
        and set(meta) == {"split", "layout_source", "p8_receipt_sha256", "cases"}
        and meta["split"] == "report"
        and meta["layout_source"] == "independent_labels"
        and meta["p8_receipt_sha256"] == expected_p8_sha,
        "Use the report-only independent layout projection tied to P8",
    )
    return make_plan(
        meta["cases"],
        "custodian_schedule_only",
        {
            "roster_bytes_sha256": expected_roster_sha,
            "p8_receipt_bytes_sha256": expected_p8_sha,
        },
    )


def verify_receipts(plan_bytes, expected_plan_sha, outcomes):
    """Verify seat and payload identities only. Each item is (relative seat folder, receipt)."""
    require(sha(plan_bytes) == expected_plan_sha, "Unregistered plan bytes")
    spec = json.loads(plan_bytes)["specification"]
    require(
        spec["schema"] == "prospective-endpoint-stability-schedule-v1"
        and spec["evidence_mode"] in {"synthetic_dry_run", "custodian_schedule_only"},
        "Wrong schedule",
    )
    chosen = spec["selected"]
    valid_rows(chosen)
    require(
        len(chosen) == len({r["family"] for r in chosen}) == N
        and spec["seed"] == SEED
        and spec["candidate_rows"] == 219
        and canonical(spec["payload_except_messages"]) == canonical(JOB_WIRE)
        and spec["total_seats"] == 720
        and canonical(spec["order"]) == canonical(jobs(chosen)),
        "Invalid 12 × 6 × 10 schedule",
    )
    expected = {f"{j['task']}/{j['arm']}/rep{j['rep']:02}": j for j in spec["order"]}
    cells = {(c["size"], c["layout"]): c for c in spec["strata"]}
    selected_counts = Counter((r["size"], r["layout"]) for r in chosen)
    require(
        len(cells) == len(spec["strata"])
        and set(selected_counts) <= set(cells)
        and all(
            c["selected"] == selected_counts[key]
            and 0 <= c["selected"] <= c["families"] <= c["candidates"]
            for key, c in cells.items()
        )
        and sum(c["candidates"] for c in cells.values()) == spec["candidate_rows"]
        and spec["layout_coverage"] == layout_coverage(spec["strata"]),
        "Stratum or coverage counts differ",
    )
    seen = set()
    for rel, r in outcomes:
        require(
            rel in expected
            and rel not in seen
            and canonical(r["job"]) == canonical(expected[rel]),
            "Unexpected, repeated or misfiled seat",
        )
        require(r["plan_sha256"] == expected_plan_sha, "Seat belongs to another plan")
        require(
            isinstance(r["execution"], dict)
            and r["execution"]
            and sha(canonical(r["execution"])) == r["execution_sha256"],
            "Unbound execution payload",
        )
        if spec["evidence_mode"] == "synthetic_dry_run":
            require(
                r["execution"].get("synthetic_preflight") is True,
                "A synthetic plan takes fixtures only",
            )
        else:
            require(
                "synthetic_preflight" not in r["execution"],
                "Synthetic outcome supplied for a custody plan",
            )
        seen.add(rel)
    return {
        "evidence_mode": spec["evidence_mode"],
        "roster_rows": spec["candidate_rows"],
        "layout_coverage": spec["layout_coverage"],
        "selected_cases": N,
        "distinct_families": N,
        "arms": len(ARMS),
        "draws_per_case_per_arm": DRAWS,
        "scheduled_seats": len(expected),
        "bound_envelopes": len(seen),
        "missing_envelopes": len(expected) - len(seen),
        "scoring_performed": False,
    }


def dry_run():
    # Families deliberately overlap layouts; these labels have no relationship to any real case.
    rows = [
        {
            "task": f"SYN-{i:03}",
            "family": f"fake-family-{i % 173}",
            "size": SIZES[i % 2],
            "layout": "未判定" if i % 13 == 0 else f"synthetic-layout-{i % 7}",
        }
        for i in range(219)
    ]
    plan = make_plan(
        rows, "synthetic_dry_run", {"source": "generated fixture; no P6 or P8 receipt"}
    )
    raw = canonical(plan)
    digest = sha(raw)

    def envelopes():
        for job in plan["specification"]["order"]:
            payload = {"synthetic_preflight": True, "slot": job["order_hash"]}
            yield (
                f"{job['task']}/{job['arm']}/rep{job['rep']:02}",
                {
                    "job": job,
                    "plan_sha256": digest,
                    "execution": payload,
                    "execution_sha256": sha(canonical(payload)),
                },
            )

    return {
        **verify_receipts(raw, digest, envelopes()),
        "synthetic_plan_sha256": digest,
        "model_calls": 0,
        "device_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "dry-run",
        help="Exercise all 720 seats using synthetic metadata without writing any receipts",
    )
    prepare = sub.add_parser(
        "prepare-private",
        help="Create an offline custody draft from a previously registered metadata projection",
    )
    prepare.add_argument("roster", type=Path)
    prepare.add_argument("roster_sha256")
    prepare.add_argument("p8_receipt", type=Path)
    prepare.add_argument("p8_sha256")
    prepare.add_argument("new_private_output", type=Path)
    check = sub.add_parser(
        "check-receipts",
        help="Check receipt identity coverage, not results, independence or service provenance",
    )
    check.add_argument("plan", type=Path)
    check.add_argument("expected_plan_sha256")
    check.add_argument("seats", type=Path)
    args = parser.parse_args()
    if args.command == "dry-run":
        print(json.dumps(dry_run(), indent=2))
    elif args.command == "prepare-private":
        require(
            not args.new_private_output.resolve().is_relative_to(ROOT),
            "Keep genuine rosters and schedules outside the public repository",
        )
        plan = private_plan(
            args.roster.read_bytes(),
            args.roster_sha256,
            args.p8_receipt.read_bytes(),
            args.p8_sha256,
        )
        raw = canonical(plan)
        with args.new_private_output.open("xb") as f:
            f.write(raw)
        print("Private schedule draft SHA-256", sha(raw))
    else:
        require(args.seats.is_dir(), "Missing seats directory")
        observations = (
            (p.parent.relative_to(args.seats).as_posix(), json.loads(p.read_bytes()))
            for p in args.seats.rglob("outcome.json")
        )
        coverage = verify_receipts(
            args.plan.read_bytes(), args.expected_plan_sha256, observations
        )
        print(json.dumps(coverage, indent=2))
        if coverage["missing_envelopes"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
