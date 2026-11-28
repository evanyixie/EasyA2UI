"""独立内容首选对照。三方使用同一业务源，评分参考不进入模型提示。"""

import argparse
import json
import os
import shutil
from pathlib import Path
from time import perf_counter

import study
from content_choice import method, program_choice, score, transport

HERE = Path(__file__).resolve().parent


def register(source, ref):
    pools = {
        "required_fact": set(source["candidate_paths"]),
        "required_action": {a["id"] for a in source["candidate_actions"]},
    }
    for clause in ref["clauses"]:
        if clause["kind"] in pools:
            alternatives = clause["alternatives"]
            if not alternatives or set(alternatives) - pools[clause["kind"]]:
                raise ValueError("必选条款须有共同候选中的可表达方案")
    if (
        set(ref["excluded"]) - set.union(*pools.values())
        or set(ref["sample_missing_candidate_ids"]) - pools["required_fact"]
    ):
        raise ValueError("排除项或缺样值字段不属于本题的共同候选")


def lock_for(path):
    sources = study.initial(path, ("L1",))
    cases = study.frozen_calls.read(path)["cases"]
    for case in cases:
        register(sources[case["id"]], case["reference"])
    files = {
        p.relative_to(HERE).as_posix(): p
        for p in (HERE / "content_choice").glob("*.py")
        if not p.name.startswith("test_")
    }
    files.update(
        {
            "choice.py": Path(__file__),
            "study.py": HERE / "study.py",
            "harness_v2/trial.py": HERE / "harness_v2/trial.py",
            "harness_v2/frozen_calls.py": HERE / "harness_v2/frozen_calls.py",
        }
    )
    return (
        {
            "input_sha256": study.trial.hashfile(path),
            "subjects": list(sources),
            "dependencies": {k: study.trial.hashfile(v) for k, v in files.items()},
            "model": transport.MODEL,
            "api": transport.API,
            "temperature": 0,
            "thinking": False,
            "max_tokens": 8192,
            "model_request_limit_per_case": 1,
        },
        cases,
        sources,
    )


def freeze(path, out):
    lock, _, _ = lock_for(path)
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(path, out / "cases.json")
    study.write(out / "freeze.json", lock)


def model_phase(seat, source, mode, issue):
    prompt = method.messages(source)
    if mode in {"score", "program"}:
        records = transport.physical_ledger(seat)["records"]
        if not records:
            return {"status": "unexecuted"}
        if len(records) != 1 or records[0]["stage"] != "content_only":
            raise ValueError("首选只允许一次模型首答")
        record = records[0]
        if transport.sha(transport.wire(prompt)) != record["messages_sha256"]:
            raise ValueError("归档提示与当前业务源不匹配")
        if record["state"] != "completed":
            return {"status": "transport_failure", "receipt": record["receipt"]}
        answer = (seat / "calls/content_only/response.txt").read_bytes()
        if transport.sha(answer) != record["raw_sha256"]:
            raise ValueError("首答投影文件与日志不符")
        receipt = record["receipt"]
    else:
        caller = transport.make_caller(
            seat, issue, origin="synthetic" if mode == "fixture" else "official_http"
        )
        try:
            result = caller("content_only", prompt)
        except transport.TransportUncertain as exc:
            return {"status": "transport_failure", "receipt": exc.receipt}
        answer, receipt = result["raw"], result["receipt"]
    try:
        choice = method.check(
            json.loads(answer, object_pairs_hook=method.no_duplicate_keys), source
        )
    except ValueError as exc:
        return {"status": "invalid", "error": str(exc), "receipt": receipt}
    return {"status": "ok", "choice": choice, "receipt": receipt}


def synthetic_issue(stage, messages):
    return {
        "raw": '{"fact_ids":["/garden/value"],"action_ids":["a1"]}',
        "receipt": {
            "stage": stage,
            "physical_attempts": 0,
            "usage": None,
            "http_ms": None,
        },
    }


def perform(batch, mode):
    lock, cases, sources = lock_for(batch / "cases.json")
    if lock != study.frozen_calls.read(batch / "freeze.json"):
        raise ValueError("冻结的内容对照输入、评分参考、模型或实现发生变化")
    if mode == "fixture" and lock["input_sha256"] != study.trial.hashfile(
        study.FIXTURE
    ):
        raise ValueError("合成模型应答仅适用于附带虚构输入")
    issue = synthetic_issue
    if mode in {"fixture", "live"}:
        if mode == "live":
            if not os.getenv("DEEPSEEK_API_KEY"):
                raise ValueError("缺少环境变量 DEEPSEEK_API_KEY")
            issue = transport.make_deepseek_issue()
        study.mark_mode(batch, mode)
    marker = batch / "execution.json"
    model_mode = study.frozen_calls.read(marker)["mode"] if marker.exists() else None
    rows = []
    stopped = False
    for case in cases:
        task = case["id"]
        source, ref = sources[task], case["reference"]
        seat = batch / task
        if mode != "score":
            seat.mkdir(exist_ok=True)
        program_file = seat / "program.json"
        if mode != "score" and not program_file.exists():
            started = perf_counter()
            choice = program_choice.choose_content(source)
            elapsed = 1000 * (perf_counter() - started)
            try:
                method.check(choice, source)
                state, error = "ok", None
            except ValueError as exc:
                state, error = "invalid", str(exc)
            transport.export(
                program_file,
                transport.wire(
                    {
                        "status": state,
                        "choice": choice,
                        "error": error,
                        "function_ms": elapsed,
                    }
                ),
            )
        program = (
            study.frozen_calls.read(program_file)
            if program_file.exists()
            else {"status": "unexecuted"}
        )
        if program["status"] == "ok" and program[
            "choice"
        ] != program_choice.choose_content(source):
            raise ValueError("程序首选无法复现")
        model = model_phase(seat, source, "score" if stopped else mode, issue)
        stopped |= model["status"] == "transport_failure"
        methods = {
            "program": program,
            "model": model,
            "select_all": {
                "status": "ok",
                "choice": {
                    "fact_ids": source["candidate_paths"],
                    "action_ids": [a["id"] for a in source["candidate_actions"]],
                },
            },
        }
        for record in methods.values():
            if record["status"] == "ok":
                record["evaluation"] = score.evaluate(record["choice"], ref)
        rows.append(
            {
                "task": task,
                "origin": case.get("origin", "unspecified"),
                "unaligned": ref.get("unaligned", []),
                **methods,
            }
        )
    groups = {"all": rows}
    for origin in sorted({r["origin"] for r in rows}):
        groups["origin/" + origin] = [r for r in rows if r["origin"] == origin]
    summary = {
        name: {
            k: score.summarize(subset, k) for k in ("model", "program", "select_all")
        }
        for name, subset in groups.items()
    }
    return {"model_source": model_mode, "groups": summary, "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    first = commands.add_parser("freeze", help="先冻结原请求、候选、条款及程序实现")
    first.add_argument("cases", type=Path)
    first.add_argument("out", type=Path)
    for cmd in ("program", "fixture", "live", "score"):
        sub = commands.add_parser(cmd)
        sub.add_argument("batch", type=Path)
        sub.add_argument("--out", type=Path, help="可选的新报告路径，默认只打印汇总")
    args = parser.parse_args()
    if args.command == "freeze":
        freeze(args.cases, args.out)
        return
    result = perform(args.batch, args.command)
    if args.out is not None:
        with args.out.open("x", encoding="utf8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(
        json.dumps(
            {"model_source": result["model_source"], "groups": result["groups"]},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
