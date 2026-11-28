"""Summarize same-upstream stage substitutions without exposing held-out inputs."""

import argparse
import json
from collections import Counter
from pathlib import Path

from fixed_layout.paired_analysis import analyze, read_rows


def summarize(rows, roster):
    families = {r["task_id"]: r for r in roster}
    if len(families) != len(roster) or not families:
        raise ValueError("Invalid roster")
    if len(rows) != len(families) or {r["task"] for r in rows} != set(families):
        raise ValueError("Each frozen task must appear exactly once")
    if any(r["reach"] not in ("paired", "upstream_not_reached") for r in rows):
        raise ValueError("Unknown eligibility status")
    results = {}
    for cohort in ("all", "source_verified"):
        assigned = [
            r
            for r in rows
            if cohort == "all" or families[r["task"]]["included_in_217_sensitivity"]
        ]
        pairs = [r for r in assigned if r["reach"] == "paired"]
        decisions = []
        for row in pairs:
            decision = {"task_id": row["task"]}
            for key, owner in (("A", "model"), ("B", "program")):
                state = row[owner + "_terminal"]
                if state == "callback_failed":
                    decision[key] = "missing"
                    decision["missing_reason"] = "transport"
                elif state in ("accepted", "geometry_unresolved", "stage_rejected"):
                    decision[key] = "pass" if state == "accepted" else "fail"
                else:
                    raise ValueError(f"Unrecognized terminal state {state!r}")
            decisions.append(decision)
        eligible = [
            {"task_id": r["task"], "family_id": families[r["task"]]["family"]}
            for r in pairs
        ]
        paired = analyze(eligible, decisions) if pairs else None
        results[cohort] = {
            "assigned": len(assigned),
            "reached": len(pairs),
            "eligible_families": len({r["family_id"] for r in eligible}),
            "upstream_not_reached": len(assigned) - len(pairs),
            "outcomes_model_then_program": dict(
                sorted(Counter(r["A"] + "/" + r["B"] for r in decisions).items())
            ),
            "paired_terminal": paired,
        }
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roster", type=Path)
    parser.add_argument("replay_dir", type=Path)
    args = parser.parse_args()
    roster = read_rows(args.roster)
    report = {
        stage: summarize(
            read_rows(args.replay_dir / (stage + ".private.jsonl")), roster
        )
        for stage in ("emit", "theme", "structure")
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
