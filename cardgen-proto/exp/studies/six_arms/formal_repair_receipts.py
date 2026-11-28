"""Read the formal common-exit receipts. Returned identifiers and traces are private."""

import json
import sys
from pathlib import Path, PureWindowsPath

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from six_arms.fixed_content_repeats import FORMAL_PLAN, check, digest
from six_arms.native_repeated_facts import PINS, checked_rows
from six_arms.paired_delivery_bounds import verified
from six_arms.portable_layout_engine import HERE, load_engine
from six_arms.web_geometry_inputs import load_inputs


def _bytes(artifact):
    if artifact is None:
        return None
    raw = artifact["text"].encode("utf-8")
    check(digest(raw) == artifact["sha256"], "Artifact text and SHA differ")
    return raw


def _issues(items):
    result = {(v["id"], v["code"]): v["excess"] for v in items}
    check(len(result) == len(items), "Duplicate node and violation code")
    return result


def read_exit(run, evidence, *, replay_geometry=False):
    """Return receipt facts for one signed execution. Each attempt starts from its original."""
    report = run["exit"]
    status = report["status"]
    first, final = (_bytes(run[key]) for key in ("first_native", "final_native"))
    rounds = report["rounds"]
    before, after = report.get("before"), report.get("after")
    measured = status in {"no_change", "repaired", "unresolved"}
    check(
        status in {"not_reached", "skipped_source_check", "unsupported"} or measured,
        "Unknown common-exit status",
    )
    check(
        (first is None) == (final is None) == (status == "not_reached")
        and measured == (before is not None) == (after is not None)
        and bool(rounds) == (status in {"repaired", "unresolved"}),
        "Exit status and artifact/diagnosis availability disagree",
    )
    if first is not None:
        check(
            bool(run["first_native"]["checks"]["errors"])
            == (status == "skipped_source_check"),
            "Original source-check gate differs",
        )
    if measured:
        check(
            bool(before) == bool(rounds)
            and report["maximum_rounds"] == evidence.native.MAX_ROUNDS
            and len(rounds) <= evidence.native.MAX_ROUNDS,
            "Invalid common-exit round budget",
        )
    uncommitted = report.get("effective_candidate_committed") is False
    proposed_end = _bytes(report["uncommitted_native"]) if uncommitted else final
    if uncommitted:
        check(
            run["failed_stage"] == "post_repair_output_check"
            and bool(report["uncommitted_native"]["checks"]["errors"])
            and first == final,
            "Post-check rollback did not retain original",
        )
    # The original function also checks moved good boxes and material preservation.
    if replay_geometry and (measured or status == "unsupported"):
        reproduced, geometry_log = evidence.native.repair(first)
        sealed = {
            k: v
            for k, v in report.items()
            if k not in {"uncommitted_native", "effective_candidate_committed"}
        }
        sealed["rounds"] = [
            {k: v for k, v in r.items() if k != "candidate"} for r in rounds
        ]
        check(
            geometry_log == sealed and reproduced == proposed_end,
            "Frozen geometry replay differs from original receipt",
        )
    entries = []
    baseline = _issues(before or [])
    for number, attempt in enumerate(rounds, 1):
        candidate = _bytes(attempt["candidate"])
        restored = evidence.replay_changes(first, attempt)
        check(
            attempt["from"] == "original"
            and attempt["round"] == number
            and candidate == evidence.encode(restored),
            "Candidate round or replayed action bytes differ",
        )
        defects = _issues(attempt["candidate_violations"])
        introduced = {k: v for k, v in defects.items() if k not in baseline}
        worsened = {
            k: v
            for k, v in defects.items()
            if k in baseline and v > baseline[k] + evidence.native.EPS
        }
        accepted = attempt["accepted"]
        check(
            introduced == _issues(attempt["introduced_by_repair"])
            and worsened == _issues(attempt["worsened"])
            and accepted
            is bool(
                attempt["actions"]
                and not defects
                and not attempt["moved_previously_valid_boxes"]
                and attempt["protected_semantics_equal"]
            ),
            "Candidate issue delta or acceptance differs",
        )
        if accepted:
            check(
                number == len(rounds)
                and number == report.get("accepted_round")
                and candidate == proposed_end
                and candidate != first,
                "Accepted proposal differs from the selected output",
            )
        committed = accepted and not uncommitted
        entries.append(
            {
                **{k: v for k, v in attempt.items() if k not in {"from", "candidate"}},
                "candidate_sha256": attempt["candidate"]["sha256"],
                "committed": committed,
                "rolled_back": not committed,
            }
        )
    accepted = any(r["accepted"] for r in entries)
    committed = any(r["committed"] for r in entries)
    check(
        accepted == (status == "repaired")
        and (not accepted or after == [])
        and (accepted or after == before)
        and (first != final) == committed,
        "Exit report and returned artifact differ",
    )
    return {
        "first_sha256": digest(first) if first is not None else None,
        "final_sha256": digest(final) if final is not None else None,
        "execution_status": run["status"],
        "exit_status": status,
        "before": before,
        # For a failed post-check the archived 'after' describes an uncommitted proposal.
        "after": before if uncommitted else after,
        "committed": committed,
        "rounds": entries,
    }


def load_repair_rows(batch, *, replay_geometry=False):
    """Verify all 219×6 signed seat, source and first/final artifact identities."""
    batch = Path(batch).resolve()
    seats = load_inputs(batch)
    endpoints = checked_rows(
        batch / "pre_score_evidence/endpoint/observations.private.jsonl",
        PINS["observations"],
    )
    proofs = {
        (r["task_id"], r["arm"]): r["provenance"]
        for r in endpoints
        if r["checkpoint"] == "raw_first"
    }
    terminal = {
        (s.task, s.arm): s.artifact_sha256
        for s in seats
        if s.checkpoint == "after_common_repair"
    }
    if replay_geometry:
        evidence = load_engine().evidence
        plan = json.loads(verified(batch / "live/plan.json", FORMAL_PLAN))
        pins = {PureWindowsPath(k).name: v for k, v in plan["dependencies"].items()}
        files = evidence.native.dependency_files()
        for key, name in (
            ("regular.ttf", "HarmonyOS_Sans_SC_Regular.ttf"),
            ("bold.ttf", "HarmonyOS_Sans_SC_Bold.ttf"),
            ("measure.py", "measure.py"),
        ):
            verified(files[key], pins[name])
    else:
        # Replaying the recorded primitive edits requires no fonts or measurements.
        sys.path.insert(0, str(HERE))
        try:
            from repair import evidence
        finally:
            sys.path.remove(str(HERE))
    rows = []
    for seat in seats:
        if seat.checkpoint != "raw_first":
            continue
        key = (seat.task, seat.arm)
        proof = proofs[key]
        receipt = json.loads(
            verified(batch / proof["outcome_ref"], proof["outcome_sha256"])
        )
        row = read_exit(receipt["execution"], evidence, replay_geometry=replay_geometry)
        check(
            row["first_sha256"] == seat.artifact_sha256
            and row["final_sha256"] == terminal[key],
            "Endpoint artifact and common exit differ",
        )
        rows.append({"task": seat.task, "family": seat.family, "arm": seat.arm, **row})
    return rows
