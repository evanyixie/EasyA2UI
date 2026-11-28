"""Resolve the formal A2UI bytes and requested canvas for offline Web geometry replay."""

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from six_arms.fixed_content_repeats import FORMAL_PLAN, canonical, check, digest
from six_arms.harness_v2 import trial
from six_arms.native_repeated_facts import PINS, checked_rows
from six_arms.paired_delivery_bounds import ROSTER, verified

MOMENTS = {"raw_first": "first_native", "after_common_repair": "final_native"}
VIEWPORTS = {"2x2": (150, 150), "2x4": (300, 150)}


@dataclass(frozen=True)
class GeometryInput:
    task: str
    family: str
    arm: str
    checkpoint: str
    size: str
    artifact_sha256: str | None
    path: Path | None
    execution_status: str

    @property
    def viewport(self):
        return VIEWPORTS[self.size]

    @property
    def cache_key(self):
        return (self.size, self.artifact_sha256) if self.path is not None else None


def artifact_path(batch, folder, moment, observation, execution):
    path = folder / (moment + ".a2ui.jsonl")
    endpoint_sha = observation["artifact_sha256"]
    artifact = execution[moment]
    reference = observation["provenance"]["artifact_ref"]
    if artifact is None:
        check(
            endpoint_sha is None and reference is None and not path.exists(),
            "Conflicting absence evidence",
        )
        return None
    check(
        reference == path.relative_to(batch).as_posix()
        and endpoint_sha == artifact["sha256"],
        "Endpoint and outcome identify different artifacts",
    )
    check(
        verified(path, endpoint_sha) == artifact["text"].encode("utf-8"),
        "Stored A2UI bytes differ from outcome",
    )
    return path


def load_inputs(batch):
    """Validate all 2,628 rows before exposing any. Paths and row identifiers are private."""
    batch = Path(batch).resolve()
    plan = json.loads(verified(batch / "live/plan.json", FORMAL_PLAN))
    completion = trial.read(
        batch / "tech_metrics/continuation_final/completion_receipt.json"
    )
    check(
        completion["complete"] and completion["plan_sha256"] == FORMAL_PLAN,
        "Batch is incomplete or mismatched",
    )
    roster_rows = checked_rows(batch / "analysis/roster.jsonl", ROSTER)
    roster = {r["task_id"]: r for r in roster_rows}
    endpoint_rows = checked_rows(
        batch / "pre_score_evidence/endpoint/observations.private.jsonl",
        PINS["observations"],
    )
    endpoints = {(r["task_id"], r["arm"], r["checkpoint"]): r for r in endpoint_rows}
    cases = plan["assignment"]["cases"]
    check(
        len(roster) == len(roster_rows) == len(cases) == 219
        and {c["id"] for c in cases} == roster.keys(),
        "Invalid roster",
    )
    check(
        len(endpoints)
        == len(endpoint_rows)
        == len(cases) * len(trial.ARMS) * len(MOMENTS),
        "Incomplete or duplicate endpoints",
    )
    rows = []
    for case in cases:
        task = case["id"]
        family = roster[task]["family"]
        fid = case["file_id"]
        check(
            fid == digest(task.encode())
            and bool(family)
            and sorted(case["arms"]) == list(trial.ARMS),
            "Invalid plan assignment",
        )
        filename = fid + ".json"
        package = batch / "queue/package"
        req = json.loads(
            verified(package / "requests" / filename, case["input_sha256"])
        )
        reg = json.loads(
            verified(package / "registry" / filename, case["registry_sha256"])
        )
        size = req["size"]
        check(
            size in VIEWPORTS
            and size == case["size"]
            and req["_custody_original_envelope_sha256"]
            == roster[task]["raw_request_sha256"]
            and (reg["id"], reg["input_sha"]) == (task, case["input_sha256"]),
            "Frozen request, canvas or registry mismatch",
        )
        source_sha = digest(canonical(trial.source_for(req, reg["data_model"])))
        for arm in trial.ARMS:
            folder = batch / "live" / fid / arm
            path = folder / "outcome.json"
            observations = {point: endpoints[task, arm, point] for point in MOMENTS}
            proof = observations["raw_first"]["provenance"]
            receipt = json.loads(verified(path, proof["outcome_sha256"]))
            run = receipt["execution"]
            check(
                (receipt["task"], receipt["arm"], receipt["plan_sha256"])
                == (task, arm, FORMAL_PLAN)
                and run["arm"] == arm
                and source_sha == run["source_canonical_sha256"]
                and digest(canonical(run)) == receipt["execution_sha256"],
                "Outcome does not match frozen task, source or execution",
            )
            for point, moment in MOMENTS.items():
                obs = observations[point]
                p = obs["provenance"]
                check(
                    obs["version_sha256"] == FORMAL_PLAN
                    and p["outcome_ref"] == path.relative_to(batch).as_posix()
                    and p["outcome_sha256"] == proof["outcome_sha256"]
                    and p["execution_sha256"] == receipt["execution_sha256"]
                    and p["raw_request_sha256"] == roster[task]["raw_request_sha256"]
                    and p["packaged_request_sha256"] == case["input_sha256"]
                    and p["registry_sha256"] == case["registry_sha256"]
                    and obs["original_artifact_sha256"]
                    == observations["raw_first"]["artifact_sha256"],
                    "Endpoint provenance does not identify this request or checkpoint",
                )
                artifact = artifact_path(batch, folder, moment, obs, run)
                rows.append(
                    GeometryInput(
                        task,
                        family,
                        arm,
                        point,
                        size,
                        obs["artifact_sha256"],
                        artifact,
                        obs["execution"]["status"],
                    )
                )
    check(
        all(
            sum(r.path is not None for r in rows if r.checkpoint == point) == 984
            for point in MOMENTS
        ),
        "Unexpected formal artifact count",
    )
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-root", type=Path, required=True)
    args = parser.parse_args()
    rows = load_inputs(args.formal_root)
    print(
        json.dumps(
            {
                "seats_per_checkpoint": dict(Counter(r.checkpoint for r in rows)),
                "artifacts_per_checkpoint": dict(
                    Counter(r.checkpoint for r in rows if r.path is not None)
                ),
                "families": len({r.family for r in rows}),
                "unique_sha_and_canvas": len(
                    {r.cache_key for r in rows if r.cache_key is not None}
                ),
            },
            sort_keys=True,
        )
    )
