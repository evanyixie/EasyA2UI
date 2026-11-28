"""Replay the two frozen enhanced-program policies on the independently selected 12 cases.

Custodian replay needs the prior benchmark implementation, fonts and private evidence.
The public table contains method counts only. No model calls, device use or human ratings.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter

PUBLIC = (
    Path(__file__).resolve().parents[4] / "paper/out/tables/enhanced_repeat_bridge.json"
)
POLICIES = {"compatible": "compatibility_program", "standard": "strict_program"}
PINS = {
    "selection": "819a5f79679ca24caa62137b8c5c9a647c94319e367e0ed7a25ed50405baf444",
    "matched_plan": "89e5882deb5615a414671d69ae4f208aea5299333bff4af834cd09a9413ce041",
    "matched_complete": "03386f6d151a860cf1198aa81443463f85fd74844489f06fa6c7dd8a283549f8",
    "paired187": "67442c8bd70bb82a85b85a86d61208c801a4c5364ed1157ce9da5cb45a954651",
    "timed187": "cfa535dbc31f3f846f4323b6851de827285ef180e8245986b9d33d97929b47e2",
    "small": "58151ddfd06ee432e5bda663608025e77e99eba3b13788c350bd3c68deb8be6f",
    "wide": "fb950950ad042afb86adeb7ef590a1a3c4825c95d3f1a985fb01830d88af7824",
    "benchmark": "c421c3b3cbd9b54ec21d78ab31af13b1b3e2a994d7d45ff12921f3b07c8a5aec",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def check_file(path, expected):
    require(digest(path.read_bytes()) == expected, "Evidence mismatch: " + path.name)


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    text = (
        json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        + "\n"
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def indexed(rows):
    idx = {r["task"]: r for r in rows}
    require(len(idx) == len(rows), "Duplicate historical case")
    return idx


def no_network(event, _args):
    if event in {"socket.connect", "socket.getaddrinfo"}:
        raise RuntimeError("Offline program replay")


def sealed_inputs(batch, bench_path):
    matched = batch / "fixed_content_repeat12_20261128"
    old = batch / "same_content_l56_followup"
    paths = {
        "selection": matched / "selection.private.json",
        "matched_plan": matched / "plan.json",
        "matched_complete": matched / "complete.json",
        "paired187": old / "paired187.private.json",
        "timed187": old / "timing/times.private.json",
        "small": old / "compact/cases.private.jsonl",
        "wide": old / "wide/pairs.private.json",
        "benchmark": bench_path,
    }
    for key, path in paths.items():
        check_file(path, PINS[key])
    chosen = load(paths["selection"])["cases"]
    plan = indexed(load(paths["matched_plan"])["specification"]["tasks"])
    paired = indexed(load(paths["paired187"]))
    timed = indexed(load(paths["timed187"]))
    compact = indexed(
        [json.loads(line) for line in paths["small"].read_bytes().splitlines()]
    )
    wide = indexed(load(paths["wide"]))
    require(
        len(paired) == len(timed) == 187 and len(chosen) == 12, "Frozen populations"
    )
    require(
        set(indexed(chosen)) == set(plan) and len({r["family"] for r in chosen}) == 12,
        "Wrong 12-case selection",
    )
    references = {}
    for r in chosen:
        t = r["task"]
        p, times = paired[t], timed[t]
        require(
            p["content_sha256"]
            == times["content_sha"]
            == plan[t]["content_sha256"]
            == r["content_sha256"],
            "Contents differ",
        )
        require(
            p["size"] == times["size"] == plan[t]["size"] == r["size"], "Canvas differs"
        )
        refs = {}
        for key, expected_bool, path_name in (
            ("compatible", p["l6"], p["native_l6"]),
            (
                "standard",
                p["strict_program"],
                compact[t]["program_strict_artifact"]
                if t in compact
                else wide[t]["l6_strict_native"],
            ),
        ):
            old_sha = times["compatible" if key == "compatible" else "strict"][
                "program_sha"
            ]
            require(
                bool(old_sha) == expected_bool and bool(path_name) == bool(old_sha),
                "Historical pass or source disagrees",
            )
            if key == "compatible":
                require(
                    old_sha == p["sha_l6"], "Historical compatible artifact disagrees"
                )
            if old_sha:
                # Some older references use backslashes even for repository-relative paths.
                pth = Path(path_name.replace("\\", "/"))
                check_file(pth if pth.is_absolute() else batch / pth, old_sha)
            refs[key] = old_sha
        refs["content"] = r["content_sha256"]
        refs["canvas"] = r["size"]
        references[t] = refs
    return matched, references


def original_l6(matched, task, repetition, content_sha):
    row = load(
        matched / "seats" / task / "L6" / f"rep{repetition:02d}" / "outcome.json"
    )
    ex = row["execution"]
    require(
        row["plan_sha256"] == PINS["matched_plan"]
        and row["job"] == {"task": task, "arm": "L6", "rep": repetition},
        "Unmatched primary seat",
    )
    canon = lambda v: json.dumps(
        v, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    require(
        digest(canon(ex)) == row["execution_sha256"]
        and digest(canon(ex["stages"][0]["product"])) == content_sha,
        "Wrong primary content",
    )
    return ex["final_native"]["sha256"] if ex["status"] == "accepted" else None


def public_report(rows):
    public = {
        "design": "Post-hoc program-only replay of the two locked 187-case policies on the same 12 independently selected cases, "
        "ten independent executions of each policy per case. Each method recomputes the layout from frozen content. "
        "A match on an accepted artifact requires a hash of the historical A2UI file. Missing outputs only count as missing.",
        "cases": 12,
        "families": 12,
        "repetitions": 10,
        "method_executions": len(rows),
        "new_model_calls": 0,
        "device_runs": 0,
        "methods": {},
        "source_sha256": PINS,
    }
    for policy in POLICIES:
        subset = [r for r in rows if r["policy"] == policy]
        require(len(subset) == 120, "Missing policy records")
        by_task = {}
        for r in subset:
            by_task.setdefault(r["task"], []).append(r)
        require(len(by_task) == 12, "Missing task")
        for rr in by_task.values():
            require(
                {r["rep"] for r in rr} == set(range(1, 11)) and len(rr) == 10,
                "Missing or repeated execution",
            )
            require(
                len({r["content_sha256"] for r in rr})
                == len({r["historical_sha256"] for r in rr})
                == 1,
                "Historical target changed",
            )
        by_case = list(by_task.values())
        passed = [r for r in subset if r["result_sha256"]]
        size_counts = {}
        for size in ("2x2", "2x4"):
            seats = [r for r in subset if r["size"] == size]
            size_counts[size] = {
                "cases": len({r["task"] for r in seats}),
                "accepted": sum(bool(r["result_sha256"]) for r in seats),
                "executions": len(seats),
            }
        stats = {
            "technical_accepted": len(passed),
            "no_accepted_artifact": len(subset) - len(passed),
            "technical_outcome_matches_historical": sum(
                bool(r["result_sha256"]) == bool(r["historical_sha256"]) for r in subset
            ),
            "accepted_hash_matches_historical_file": sum(
                r["result_sha256"] == r["historical_sha256"] for r in passed
            ),
            "cases_with_all_10_accepted_and_byte_identical": sum(
                all(r["result_sha256"] for r in g)
                and len({r["result_sha256"] for r in g}) == 1
                for g in by_case
            ),
            "cases_with_no_accepted_artifact_in_10": sum(
                not any(r["result_sha256"] for r in g) for g in by_case
            ),
            "by_canvas": size_counts,
        }
        if policy == "compatible":
            pairs = Counter(
                (bool(r["old_program_sha256"]), bool(r["result_sha256"]))
                for r in subset
            )
            stats["matched_original_program_by_repetition"] = {
                "both_accepted": pairs[True, True],
                "enhanced_only": pairs[False, True],
                "original_only": pairs[True, False],
                "neither_accepted": pairs[False, False],
                "previously_accepted_byte_identical": sum(
                    bool(r["old_program_sha256"])
                    and r["old_program_sha256"] == r["result_sha256"]
                    for r in subset
                ),
            }
        public["methods"][policy] = stats
    return public


def replay(batch, bench_path, private):
    sys.addaudithook(no_network)
    matched, refs = sealed_inputs(batch, bench_path)
    spec = importlib.util.spec_from_file_location(
        "archived_repeat_benchmark", bench_path
    )
    bench = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bench)
    data, dev, mods, _footprint = bench.load()
    bench.warm_fonts()
    # Each method invokes the original 187-case selection and layout procedure. Only the
    # historical truth and its authentication are shared between repeated executions.
    steps = []
    started = perf_counter()
    for rep in range(1, 11):
        for index, (task, ref) in enumerate(sorted(refs.items())):
            item = data[task]
            require(
                item["old"]["content_sha"] == ref["content"],
                "Wrong loaded benchmark item",
            )
            original = original_l6(matched, task, rep, ref["content"])
            keys = (
                ("standard", "compatible")
                if (index + rep) % 2
                else ("compatible", "standard")
            )
            for policy in keys:
                tick = perf_counter()
                result, method_ms = bench.measure(item, POLICIES[policy], dev, mods)
                elapsed_ms = (perf_counter() - tick) * 1000
                require(
                    result == ref[policy],
                    "Computed artifact differs from archived 187-case result",
                )
                steps.append(
                    {
                        "task": task,
                        "rep": rep,
                        "size": ref["canvas"],
                        "policy": policy,
                        "content_sha256": ref["content"],
                        "old_program_sha256": original,
                        "historical_sha256": ref[policy],
                        "result_sha256": result,
                        "method_reported_ms": method_ms,
                        "measured_wall_ms": elapsed_ms,
                    }
                )
    output = public_report(steps)
    if private:
        private.mkdir(parents=True, exist_ok=True)
        # Preserve first measurements across subsequent reproducibility checks.
        record = private / "repetitions.private.json"
        require(
            not record.exists(),
            "Existing private readings; rerun with no --private-output or choose a new directory",
        )
        save(
            record,
            {
                "source_sha256": PINS,
                "measurement_wall_seconds": perf_counter() - started,
                "rows": steps,
            },
        )
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-batch", type=Path, required=True)
    parser.add_argument("--historical-benchmark", type=Path, required=True)
    parser.add_argument("--private-output", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = replay(args.formal_batch, args.historical_benchmark, args.private_output)
    if args.check:
        require(report == load(PUBLIC), "Public aggregate differs")
        print("Enhanced-program repeat table matched.")
    else:
        save(args.output, report)


if __name__ == "__main__":
    main()
