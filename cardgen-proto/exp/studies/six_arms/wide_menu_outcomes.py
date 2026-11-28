"""Evaluate sealed first choices against every frozen wide-card menu candidate."""

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from statistics import median

from PIL import __version__ as pillow_version
from PIL import features

if __package__:
    from . import menu_model_runner, portable_enhanced_layout, portable_layout_engine
else:
    import menu_model_runner
    import portable_enhanced_layout
    import portable_layout_engine


VERDICTS = ("pass", "fail", "unknown")
BLOCKED = {"empty", "content_rejected", "content_transport_unknown"}
FONTS = {
    "REGULAR": "297b088424be212207df2ce8b98e335468b782aa6b96832af0b8b773d711e2b1",
    "BOLD": "43a424b85e47fb53a17b3b32026a71801f86f8e022ca6798d186b47d39fa5f01",
}
MEASURERS = {
    "c5ebc7d13c94a73f2e48af6df51a045b8dd8b61c68a40c2dfc0ec69e16526f17": "original",
    "253ff21ca8747eff7edbba742d3e32f95a20f8ccd59761ba4efbcde6114ca056": "portable",
}


def require(test, message):
    if not test:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sealed(path, expected):
    data = path.read_bytes()
    require(digest(data) == expected, f"Digest mismatch: {path.name}")
    return data


def keyed(rows):
    result = {r["task_id"]: r for r in rows}
    require(len(result) == len(rows), "Duplicate task")
    return result


def clock(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def measure_identity(engine):
    for k, h in FONTS.items():
        sealed(Path(getattr(engine.program, k)), h)
    measurer = digest(Path(engine.program.MEASURE_FILE).read_bytes())
    require(measurer in MEASURERS, "Unregistered text measurer")
    freetype = features.version_module("freetype2")
    require(
        (pillow_version, freetype) == ("12.3.0", "2.14.3"),
        "Font engine version differs",
    )
    return {
        "fonts": FONTS,
        "measurer": measurer,
        "pillow": pillow_version,
        "freetype": freetype,
    }


def verify_receipt(root, plan, row, wire):
    """Check the recorded attempt, provider envelope, answer and first choice together."""
    place = root / "model/seats" / digest(row["task_id"].encode())
    require(json.loads((place / "result.json").read_bytes()) == row, "Seat differs")
    raw = (place / "request.json").read_bytes()
    request = json.loads(raw)
    intent = json.loads((place / "intent.json").read_bytes())
    require(digest(raw) == intent["request_sha256"], "Request differs from intent")
    expected = [
        {"role": "system", "content": plan["system"]},
        {"role": "user", "content": wire.decode("utf-8")},
    ]
    require(
        request == {**plan["service"], "messages": expected}, "Selector inputs differ"
    )
    require(row["local_intents"] == 1, "Unexpected number of attempts")
    if row["status"] == "interrupted_unknown":
        require(not (place / "http.json").exists(), "Interrupted receipt has response")
        require(
            row["confirmed_requests"] is None and row["choice"] is None,
            "Interrupted receipt",
        )
        return "interrupted"
    envelope = json.loads((place / "http.json").read_bytes())
    receipt, body = envelope["receipt"], envelope["answer"]
    require(all(row[k] == v for k, v in receipt.items()), "HTTP/choice receipt differs")
    status = row["http_status"]
    require(
        row["confirmed_requests"] == (None if status is None else 1), "Unconfirmed HTTP"
    )
    require(
        clock(row["http_ms"]) and clock(row["decision_ms"]), "Missing observed clock"
    )
    if status != 200:
        require(
            row["status"] == "transport_unknown" and row["choice"] is None,
            "HTTP status",
        )
        return "transport_unknown" if status is None else "http_error"
    model = body.get("model") if isinstance(body, dict) else None
    require(model == row["actual_model"], "Response model differs")
    require(
        row["usage"] == (body.get("usage") if isinstance(body, dict) else None),
        "Usage differs",
    )
    if model != plan["service"]["model"]:
        require(row["choice"] is None, "Choice credited to another model")
        return "unexpected_model" if model else "unreadable_response"
    try:
        text = body["choices"][0]["message"]["content"]
    except (TypeError, AttributeError, IndexError, KeyError):
        text = None
    if not isinstance(text, str):
        require(
            row["status"] == "invalid_response" and row["choice"] is None,
            "Missing reply",
        )
        return "unreadable_response"
    try:
        choice = menu_model_runner.decode(text, row["options"])
    except ValueError:
        require(
            row["status"] == "invalid_response" and row["choice"] is None,
            "Invalid reply",
        )
        return "invalid_choice"
    require(row["status"] == "selected" and row["choice"] == choice, "Wrong selection")
    require(bool(row["request_id"]), "Missing provider identity for selected choice")
    return "selected"


def frozen_seats(root, cohort_sha, program_sha, model_sha, expected_tasks):
    cases = keyed(json.loads(sealed(root / "cohort.private.json", cohort_sha))["cases"])
    programs = json.loads(sealed(root / "program_choices.json", program_sha))
    replies = keyed(
        [
            json.loads(s)
            for s in sealed(root / "model/choices.jsonl", model_sha).splitlines()
        ]
    )
    plan = json.loads((root / "model/plan.json").read_bytes())
    require(len(cases) == expected_tasks, "Incomplete formal-wide cohort")
    require(
        plan["runner_sha256"] == digest(Path(menu_model_runner.__file__).read_bytes())
        and plan["service"] == menu_model_runner.SERVICE
        and plan["system"] == menu_model_runner.SYSTEM
        and plan["endpoint"] == menu_model_runner.API
        and plan["attempts_per_multi_choice"] == 1,
        "Selector protocol differs from the registered runner",
    )
    index = keyed(json.loads(sealed(root / "index.json", plan["index_sha256"]))["rows"])
    selectable = {
        key for key, c in cases.items() if c["status"] in {"multiple", "forced"}
    }
    multiple = {key for key, c in cases.items() if c["status"] == "multiple"}
    require(
        set(programs) == selectable and set(index) == multiple, "Menu roster differs"
    )
    require(
        set(replies) <= multiple and plan["rows"] == len(multiple), "Unknown model seat"
    )
    seen_requests = set()
    seats = []
    for task, case in cases.items():
        state = case["status"]
        row = {
            "task_id": task,
            "family": case["family"],
            "state": state,
            "model_record": replies.get(task),
        }
        require(bool(row["family"]), "Missing family")
        if task not in selectable:
            require(
                state in BLOCKED and case["options"] == [], "Unexpected blocked menu"
            )
            seats.append(row)
            continue
        wire = sealed(root / "shared" / f"{task}.json", case["wire_sha256"])
        data = json.loads(wire)
        options = [c["id"] for c in data["choices"]]
        require(
            options == case["options"] and len(set(options)) == len(options),
            "Menu order differs",
        )
        require(
            len(options) >= 2 if state == "multiple" else len(options) == 1, "Menu size"
        )
        require(
            data["canvas"] == {"width_vp": 300, "height_vp": 150}, "Unexpected size"
        )
        source = json.loads(
            sealed(
                root / "private_inputs" / f"{task}.json", case["private_input_sha256"]
            )
        )
        pr = programs[task]
        require(
            pr["wire_sha256"] == case["wire_sha256"] and pr["choice"] in options,
            "Program choice",
        )
        require(clock(pr["elapsed_ms"]), "Invalid program clock")
        if state == "multiple":
            require(
                index[task]["options"] == options
                and index[task]["wire_sha256"] == case["wire_sha256"],
                "Index mismatch",
            )
        reply = row["model_record"]
        disposition = "forced" if state == "forced" else "not_attempted"
        if reply:
            require(
                reply["options"] == options
                and reply["wire_sha256"] == case["wire_sha256"],
                "Model menu",
            )
            disposition = verify_receipt(root, plan, reply, wire)
            rid = reply.get("request_id")
            if rid:
                require(rid not in seen_requests, "Duplicate provider request")
                seen_requests.add(rid)
        model_choice = options[0] if state == "forced" else (reply or {}).get("choice")
        row.update(
            wire=data,
            inputs=source,
            program_choice=pr["choice"],
            program_ms=pr["elapsed_ms"],
            model_choice=model_choice,
            disposition=disposition,
        )
        seats.append(row)
    return seats


def paired(rows):
    matrix = Counter((r["model"], r["program"]) for r in rows)
    low = high = shared_unknown = 0
    for row in rows:
        m, p = row["model"], row["program"]
        same_choice = row.get("program_choice") is not None and row[
            "program_choice"
        ] == row.get("model_choice")
        if same_choice or row["state"] in BLOCKED:
            require(m == p, "Shared outcome disagrees")
            shared_unknown += m == "unknown"
            continue
        low += (p == "pass") - (m != "fail")
        high += (p != "fail") - (m == "pass")
    return {
        "tasks": len(rows),
        "families": len({r["family"] for r in rows}),
        "assessed_pairs": sum(
            n for (m, p), n in matrix.items() if "unknown" not in (m, p)
        ),
        "model": {
            v: sum(n for (m, _), n in matrix.items() if m == v) for v in VERDICTS
        },
        "program": {
            v: sum(n for (_, p), n in matrix.items() if p == v) for v in VERDICTS
        },
        "model_by_program": {m: {p: matrix[m, p] for p in VERDICTS} for m in VERDICTS},
        "program_minus_model_pass_count_bounds": [low, high],
        "shared_unknown_pairs_contribute_zero_difference": shared_unknown,
        "same_selected_id": sum(
            r.get("program_choice") is not None
            and r["program_choice"] == r.get("model_choice")
            for r in rows
        ),
    }


def distribution(values):
    return {"n": len(values), "median_ms": median(values) if values else None}


def aggregate(rows):
    """Aggregate all assignments and the subsets with actual selection opportunities."""
    require(len({r["task_id"] for r in rows}) == len(rows), "Duplicate evaluated task")
    patterns = Counter()
    mixed, any_pass = [], []
    opportunities = [r for r in rows if r["state"] == "multiple"]
    for row in rows:
        states = set(row["oracle"].values())
        require(
            states <= set(VERDICTS) and {row["model"], row["program"]} <= set(VERDICTS),
            "Verdict",
        )
        if not states:
            continue
        patterns["+".join(v for v in VERDICTS if v in states)] += 1
        if row["state"] == "multiple" and "pass" in states:
            any_pass.append(row)
            if "fail" in states:
                mixed.append(row)
    records = [
        r["model_record"] for r in opportunities if r["model_record"] is not None
    ]
    decisions = [
        r
        for r in opportunities
        if r["model_record"] is not None and clock(r["model_record"]["decision_ms"])
    ]
    metered = [
        r["usage"]
        for r in records
        if isinstance(r["usage"], dict) and type(r["usage"].get("total_tokens")) is int
    ]
    token_keys = ("prompt_tokens", "completion_tokens", "total_tokens")
    for u in metered:
        require(
            all(type(u.get(k)) is int and u[k] >= 0 for k in token_keys)
            and u["prompt_tokens"] + u["completion_tokens"] == u["total_tokens"],
            "Invalid metering",
        )
    return {
        "all_assigned": paired(rows),
        "multiple": paired(opportunities),
        "forced": paired([r for r in rows if r["state"] == "forced"]),
        "multiple_with_any_known_pass": paired(any_pass),
        "multiple_with_known_pass_and_fail": paired(mixed),
        "cohort": dict(Counter(r["state"] for r in rows)),
        "candidate_count": sum(len(r["oracle"]) for r in rows),
        "candidate_verdicts": dict(
            Counter(v for r in rows for v in r["oracle"].values())
        ),
        "nonempty_menu_patterns": dict(patterns),
        "choice_dispositions_multiple": dict(
            Counter(r["disposition"] for r in opportunities)
        ),
        "requests": {
            "local_intents": sum(r["local_intents"] for r in records),
            "confirmed": sum(r["confirmed_requests"] or 0 for r in records),
            "uncertain": sum(r["confirmed_requests"] is None for r in records),
            "http_status": dict(Counter(str(r["http_status"]) for r in records)),
            "known_usage": len(metered),
            "attempts_without_usage": len(records) - len(metered),
            "known_tokens": {k: sum(u[k] for u in metered) for k in token_keys},
        },
        "choice_timing_multiple": {
            "program": distribution([r["program_ms"] for r in opportunities]),
            "model": distribution(
                [r["model_record"]["decision_ms"] for r in decisions]
            ),
            "http": distribution(
                [r["http_ms"] for r in records if clock(r["http_ms"])]
            ),
            "paired_model_minus_program": distribution(
                [r["model_record"]["decision_ms"] - r["program_ms"] for r in decisions]
            ),
        },
    }


def evaluate(
    root,
    cohort_sha,
    program_sha,
    model_sha,
    engine,
    expected_tasks=50,
    private_rows=None,
):
    if private_rows:
        dest = Path(private_rows).resolve()
        require(
            dest.is_relative_to(root.resolve()) and dest.suffix == ".jsonl",
            "Private rows must stay inside the study folder",
        )
    seats = frozen_seats(root, cohort_sha, program_sha, model_sha, expected_tasks)
    measure = measure_identity(engine)
    for row in seats:
        oracle = {}
        state = row["state"]
        if state in BLOCKED:
            program = model = (
                "unknown" if state == "content_transport_unknown" else "fail"
            )
        else:
            wire, inputs = row["wire"], row["inputs"]
            for candidate in wire["choices"]:
                score = portable_enhanced_layout.score_tree(
                    engine,
                    wire["content"],
                    inputs["source"],
                    inputs["entry"],
                    candidate["tree"],
                )
                oracle[candidate["id"]] = score.strict_verdict
            program = oracle[row["program_choice"]]
            model = oracle.get(
                row["model_choice"],
                "fail" if row["disposition"] == "invalid_choice" else "unknown",
            )
        row.update(oracle=oracle, program=program, model=model)
    result = aggregate(seats)
    result["evidence_sha256"] = {
        "cohort": cohort_sha,
        "program": program_sha,
        "model": model_sha,
    }
    result["measurement"] = measure
    if private_rows:
        with dest.open("x", encoding="utf-8") as handle:
            for r in seats:
                receipt = r["model_record"] or {}
                fields = (
                    "task_id",
                    "family",
                    "state",
                    "oracle",
                    "program_choice",
                    "model_choice",
                    "disposition",
                    "program",
                    "model",
                    "program_ms",
                )
                line = {k: r.get(k) for k in fields}
                line.update(
                    model_decision_ms=receipt.get("decision_ms"),
                    http_ms=receipt.get("http_ms"),
                )
                handle.write(json.dumps(line) + "\n")
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("folder", type=Path)
    for key in ("cohort", "program", "model"):
        cli.add_argument(f"--{key}-sha", required=True)
    cli.add_argument("--output", type=Path)
    cli.add_argument("--private-rows", type=Path)
    args = cli.parse_args()
    result = evaluate(
        args.folder,
        args.cohort_sha,
        args.program_sha,
        args.model_sha,
        portable_layout_engine.load_engine(),
        private_rows=args.private_rows,
    )
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(serialized)
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
