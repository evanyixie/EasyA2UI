"""Join original protocol checks, frozen Edge measurements and final request costs for B4."""

import json
from collections import Counter
from pathlib import Path
from runpy import run_path

from six_arms import cache_token_cost, protocol_mutations
from six_arms.cost_frontier import TECH_LEDGER, usage
from six_arms.fixed_content_repeats import check, digest
from six_arms.native_repeated_facts import PINS, checked_rows
from six_arms.paired_delivery_bounds import verified
from six_arms.technical_yield import read_lines
from six_arms.web_geometry_inputs import MOMENTS, load_inputs

TABLE = (
    Path(__file__).resolve().parents[4] / "paper/out/tables/formal_web_geometry.json"
)
EDGE_TABLE_SHA = "d27678681f8ef9af88dcc99f46ecc107885e13b5005836a09ba10052abb66672"
EDGE_OBSERVATIONS_SHA = (
    "1a36df991ba39ecfa1c406bbd5bdeed25018e1e69da1f4ee57697bf009d77143"
)
WEB_PHASE = {"raw_first": "first", "after_common_repair": "final"}
ENDPOINT_INDEX = "pre_score_evidence/endpoint/observations.private.jsonl"


def validator():
    source = protocol_mutations.VALIDATOR
    check(
        digest(source.read_bytes().replace(b"\r\n", b"\n"))
        == protocol_mutations.FROZEN_LF_SHA,
        "Frozen protocol validator changed",
    )
    return run_path(str(source))["validate_a2ui"]


def protocol_result(raw, size, original, validate):
    """Reproduce the production validator, then match only its own codes in the original exit receipt."""
    try:
        violations = validate(raw.decode("utf-8"), "surface_card", size)
    except (
        TypeError,
        KeyError,
        ValueError,
        AttributeError,
        IndexError,
        RecursionError,
    ) as exc:
        return None, "validator_exception_" + type(exc).__name__, {}
    recorded = [
        e
        for e in original["errors"]
        if e.partition(" @ ")[0] in protocol_mutations.EDITS
    ]
    check(
        all(v.code in protocol_mutations.EDITS for v in violations),
        "Unexpected frozen validator code",
    )
    if "check_exception" not in original:
        check(
            recorded == [str(v) for v in violations],
            "Original and replayed protocol violations differ",
        )
    evidence = "empty_violations" if not violations else "protocol_violations"
    if "check_exception" in original:
        evidence += "_replay_only"
    return not violations, evidence, dict(Counter(v.code for v in violations))


def geometry_result(seat, row, measurements):
    check(
        (
            seat.task,
            seat.family,
            seat.arm,
            WEB_PHASE[seat.checkpoint],
            seat.artifact_sha256,
        )
        == tuple(row[k] for k in ("task", "family", "arm", "phase", "artifact_sha256")),
        "Edge observation is from a different seat or artifact",
    )
    if seat.path is None:
        check(
            row["status"] == "missing" and "observation_key" not in row,
            "Unexpected Edge outcome without artifact",
        )
        return None, "no_artifact"
    key = f"{seat.size}-{seat.artifact_sha256}"
    check(row["observation_key"] == key, "Edge canvas or artifact changed")
    obs = measurements[key]
    check(obs["key"] == key, "Mismatched Edge observation")
    if row["status"] == "unsupported":
        check(obs["state"] == "unassessed", "Inconsistent unsupported measurement")
        return None, "unsupported"
    check(
        row["status"] == obs["state"] == "measured"
        and row["text_nodes"]
        == obs["expected_text_nodes"]
        == obs["measured_text_nodes"]
        and row["above4_nodes"] == obs["above4_nodes"]
        and row["overflow_px"] == obs["overflow_sum_px"]
        and 0 <= row["above4_nodes"] <= row["text_nodes"],
        "Inconsistent Edge geometry measurement",
    )
    if not row["text_nodes"]:
        return None, "zero_text"
    return row["above4_nodes"] == 0, "measured"


def cost_indices(root):
    rows = read_lines(root / TECH_LEDGER, cache_token_cost.FROZEN_SEATS)
    costs, ledger = {}, {}
    for row in rows:
        task, arm = row["task_id"], row["arm"]
        key = task, arm
        check(key not in costs, "Duplicate cost seat")
        totals, unknown = usage(row["calls"])
        known_tokens = totals["total_tokens"]
        costs[key] = (None if unknown else known_tokens, known_tokens)
        for call in row["calls"]:
            check(call["local"] not in ledger, "Duplicate physical request")
            ledger[call["local"]] = arm, call
            path = (
                root
                / "live"
                / digest(task.encode())
                / arm
                / "calls"
                / call["phase"]
                / "seal.json"
            )
            check(
                digest(json.loads(path.read_bytes())["local_request_id"].encode())
                == call["local"],
                "Cost receipt belongs to a different task or stage",
            )
    cache_token_cost.verify_receipts(root, ledger)
    return costs


def edge_evidence(root):
    public = TABLE.read_bytes().replace(b"\r\n", b"\n")
    check(digest(public) == EDGE_TABLE_SHA, "Published Edge table changed")
    check(
        json.loads(public)["private_observations_sha256"] == EDGE_OBSERVATIONS_SHA,
        "Unexpected Edge measurement ledger",
    )
    path = root / "web_geometry_formal_20261128/edge_formal_observations.private.json"
    private = json.loads(verified(path, EDGE_OBSERVATIONS_SHA))
    index = {(r["task"], r["arm"], r["phase"]): r for r in private["seats"]}
    check(
        len(index) == len(private["seats"]) == 2628,
        "Incomplete or duplicated Edge evidence",
    )
    return index, private["observations"]


def load_rows(formal_root):
    """Return custody-only records. First-artifact token costs are intentionally unavailable."""
    root = Path(formal_root)
    seats = load_inputs(root)
    edge, observations = edge_evidence(root)
    costs = cost_indices(root)
    endpoints = {
        (r["task_id"], r["arm"], r["checkpoint"]): r["provenance"]
        for r in checked_rows(root / ENDPOINT_INDEX, PINS["observations"])
    }
    validate = validator()
    protocol = {}
    rows = []
    for s in seats:
        key = (s.task, s.arm)
        phase = s.checkpoint
        geo, geo_basis = geometry_result(
            s, edge[(*key, WEB_PHASE[phase])], observations
        )
        if s.path is None:
            check(
                s.execution_status in {"stage_rejected", "transport_failed"},
                "Unexpected absence reason",
            )
            ok, basis, codes = False, "no_artifact", {}
        else:
            proof = endpoints[(*key, phase)]
            if key not in protocol:
                outcome = json.loads(
                    verified(root / proof["outcome_ref"], proof["outcome_sha256"])
                )
                protocol[key] = {
                    moment: outcome["execution"][moment]["checks"]
                    for moment in MOMENTS.values()
                    if outcome["execution"][moment] is not None
                }
            raw = verified(s.path, s.artifact_sha256)
            ok, basis, codes = protocol_result(
                raw, s.size, protocol[key][MOMENTS[phase]], validate
            )
        rows.append(
            {
                "task": s.task,
                "family": s.family,
                "arm": s.arm,
                "phase": phase,
                "protocol": ok,
                "geometry": geo,
                "total_tokens": costs[key][0]
                if phase == "after_common_repair"
                else None,
                "known_tokens": costs[key][1]
                if phase == "after_common_repair"
                else None,
                "execution_status": s.execution_status,
                "absence_reason": s.execution_status if s.path is None else None,
                "protocol_evidence": basis,
                "protocol_codes": codes,
                "geometry_evidence": geo_basis,
            }
        )
    check(
        {(s.task, s.arm) for s in seats} == costs.keys(),
        "Cost and artifact task grids differ",
    )
    return rows


def diagnostic_counts(rows):
    result = {}
    for phase in MOMENTS:
        group = [r for r in rows if r["phase"] == phase]
        categories = {}
        for field in ("protocol_evidence", "geometry_evidence", "absence_reason"):
            categories[field] = dict(
                sorted(Counter(r[field] for r in group if r[field] is not None).items())
            )
        codes = Counter()
        for r in group:
            codes.update(r["protocol_codes"])
        categories["violation_occurrences_by_code"] = dict(sorted(codes.items()))
        categories["token_meter_complete_seats"] = sum(
            r["total_tokens"] is not None for r in group
        )
        result[phase] = categories
    return result
