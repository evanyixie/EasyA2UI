"""六档 v2 首件冻结、执行与逐请求离线复算。各命令的参数见 --help。"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from contextlib import nullcontext
from pathlib import Path

from harness_v2 import frozen_calls, model_stages, program_stages, trial

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "synthetic.json"


def write(path, obj):
    data = json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    path.write_bytes(data.encode("utf-8"))


def initial(cases_file, arms):
    cases = frozen_calls.read(cases_file)
    subjects = {}
    for case in cases["cases"]:
        task = case["id"]
        if (
            not isinstance(task, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", task)
            or Path(task).is_reserved()
            or task.casefold() in {t.casefold() for t in subjects}
            or task.lower() == "sources"
        ):
            raise ValueError("题号须为不重复的文件名，可使用字母、数字、下划线和短横线")
        subjects[task] = trial.source_for(case["request"], case["sample_data"])
        if subjects[task]["size"] not in model_stages.DIMENSIONS:
            raise ValueError("尺寸只支持 2x2 或 2x4")
    if not subjects or len(set(arms)) != len(arms) or not set(arms) <= set(trial.ARMS):
        raise ValueError("需要非空题单和有效的无重复档位")
    return subjects


def dependencies(arms):
    files = {
        str(p.relative_to(HERE).as_posix()): p
        for p in (HERE / "harness_v2").glob("*.py")
    }
    files["study.py"] = Path(__file__)
    files["emit_fidelity.py"] = HERE / "emit_fidelity.py"
    files["paired_replay.py"] = HERE / "paired_replay.py"
    for name in (
        "exp/conditions.py",
        "src/validate.py",
        "src/P6_theme.py",
        "rules/themes.json",
    ):
        files["cardgen-proto/" + name] = trial.UPSTREAM / name
    if {"L5", "L6"}.intersection(arms):
        files.update(program_stages.measurement_files())
    return {name: trial.hashfile(path) for name, path in sorted(files.items())}


def runtime(arms):
    versions = {"python": sys.version.split()[0]}
    if {"L5", "L6"}.intersection(arms):
        from PIL import __version__, features

        versions.update(
            pillow=__version__, freetype=features.version_module("freetype2")
        )
    return versions


def snapshot(cases_file, arms, sources):
    ids = list(sources)
    return {
        "format": 1,
        "arms": list(arms),
        "input_sha256": trial.hashfile(cases_file),
        "source_hashes": {
            task: hashlib.sha256(source_bytes(source)).hexdigest()
            for task, source in sources.items()
        },
        "dependencies": dependencies(arms),
        "runtime": runtime(arms),
        "queue": [
            [task, arm] for task, arm in trial.balanced_queue(ids) if arm in arms
        ],
        "model": trial.MODEL,
        "api": trial.API,
        "temperature": 0,
        "thinking": False,
        "max_tokens": 8192,
        "repair": "none",
    }


def source_bytes(source):
    return (
        json.dumps(source, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf8")


def freeze(cases_file, out, arms):
    sources = initial(cases_file, arms)
    lock = snapshot(cases_file, arms, sources)
    out.mkdir(parents=True, exist_ok=False)
    (out / "sources").mkdir()
    shutil.copyfile(cases_file, out / "cases.json")
    for task, source in sources.items():
        (out / "sources" / (task + ".json")).write_bytes(source_bytes(source))
    write(out / "freeze.json", lock)


def verified(root):
    lock = frozen_calls.read(root / "freeze.json")
    cases_file = root / "cases.json"
    sources = initial(cases_file, lock["arms"])
    if snapshot(cases_file, lock["arms"], sources) != lock:
        raise ValueError("冻结的输入、程序依赖、队列或模型设置发生变化")
    for task, source in sources.items():
        if (root / "sources" / (task + ".json")).read_bytes() != source_bytes(source):
            raise ValueError("已冻结的业务源发生变化")
    return lock, sources


def synthetic_call(out):
    def reply(phase, messages):
        records = {
            "content": model_stages._EXAMPLE_CONTENT,
            "structure": model_stages._EXAMPLE_STRUCTURE,
            "geometry": model_stages._EXAMPLE_GEOMETRY,
            "theme": model_stages._EXAMPLE_THEME,
        }
        raw = (
            model_stages._example_native()
            if phase in {"emit", "one_shot"}
            else json.dumps(records[phase], ensure_ascii=False)
        )
        folder = out / phase
        folder.mkdir()
        write(folder / "messages.json", messages)
        (folder / "response.txt").write_bytes(raw.encode("utf8"))
        write(
            folder / "call.json",
            {
                "origin": "synthetic",
                "stage": phase,
                "physical_attempts": 0,
                "http_status": None,
                "returned_model": None,
                "request_id": None,
                "http_ms": None,
                "usage": None,
            },
        )
        return raw

    return reply


def seat_hashes(seat):
    return {
        p.relative_to(seat).as_posix(): trial.hashfile(p)
        for p in sorted(seat.rglob("*"))
        if p.is_file() and p.name != "seal.json"
    }


def mark_mode(root, mode):
    marker = root / "execution.json"
    try:
        with marker.open("x", encoding="utf8") as handle:
            json.dump({"mode": mode}, handle)
    except FileExistsError:
        if frozen_calls.read(marker) != {"mode": mode}:
            raise ValueError("该批次已按其他模式执行") from None


def execute(root, mode):
    lock, sources = verified(root)
    if mode == "fixture" and lock["input_sha256"] != trial.hashfile(FIXTURE):
        raise ValueError("合成应答仅供附带的虚构输入使用")
    context = nullcontext(None)
    if mode == "live":
        import httpx

        token = os.getenv("DEEPSEEK_API_KEY")
        if not token:
            raise ValueError("缺少环境变量 DEEPSEEK_API_KEY")
        context = httpx.Client(
            headers={"Authorization": "Bearer " + token},
            timeout=httpx.Timeout(180, connect=15),
            follow_redirects=False,
        )
    mark_mode(root, mode)
    counts = {}
    with context as client:
        for task, arm in lock["queue"]:
            seat = root / task / arm
            if seat.exists():
                rec = frozen_calls.read(seat / "receipt.json")
                if rec["mode"] != mode or rec["status"] in {
                    "in_progress",
                    "transport_failed",
                }:
                    raise RuntimeError(
                        "席位有未决或失败的物理尝试，须人工核查后另开批次"
                    )
            else:
                call = synthetic_call(seat) if mode == "fixture" else None
                try:
                    rec = trial.perform(
                        seat,
                        sources[task],
                        arm,
                        client,
                        model_stages,
                        program_stages,
                        model_call=call,
                        mode=mode,
                    )
                except trial.ServiceFailure:
                    write(seat / "seal.json", seat_hashes(seat))
                    raise
                write(seat / "seal.json", seat_hashes(seat))
            if frozen_calls.read(seat / "seal.json") != seat_hashes(seat):
                raise ValueError("首件或模型调用归档与已封存摘要不符")
            counts[rec["status"]] = counts.get(rec["status"], 0) + 1
    print(json.dumps({"mode": mode, "seats": counts}, ensure_ascii=False))


def replay(root, archive, out):
    lock, sources = verified(root)
    archive = archive if archive is not None else root
    if any(out.resolve().is_relative_to(path.resolve()) for path in (root, archive)):
        raise ValueError("重放输出须在冻结批次和归档目录之外")
    public_archive = (archive / "execution.json").is_file()
    run_mode = (
        frozen_calls.read(archive / "execution.json")["mode"]
        if (archive / "execution.json").is_file()
        else "live"
    )
    # 旧版首件归档没有 execution.json；只有本版明确标识 fixture 才可读合成回执。
    if run_mode not in {"live", "fixture"}:
        raise ValueError("未知归档类型")
    out.mkdir(parents=True, exist_ok=False)
    shutil.copytree(root / "sources", out / "sources")
    rows = []
    for task, arm in lock["queue"]:
        past = archive / task / arm
        archive_source = archive / "sources" / (task + ".json")
        if (
            not archive_source.is_file()
            or frozen_calls.read(archive_source) != sources[task]
        ):
            rows.append(
                {"task": task, "arm": arm, "result": "missing_or_different_source"}
            )
            continue
        if not (past / "receipt.json").is_file():
            rows.append({"task": task, "arm": arm, "result": "unexecuted"})
            continue
        if public_archive and (
            not (past / "seal.json").is_file()
            or frozen_calls.read(past / "seal.json") != seat_hashes(past)
        ):
            rows.append(
                {"task": task, "arm": arm, "result": "unsealed_or_changed_archive"}
            )
            continue
        previous = frozen_calls.read(past / "receipt.json")
        if previous["arm"] != arm or previous["source_sha256"] != trial.hashfile(
            archive_source
        ):
            raise ValueError("原席位回执与题源不符")
        if previous["status"] in {"transport_failed", "in_progress"}:
            rows.append(
                {
                    "task": task,
                    "arm": arm,
                    "result": "no_complete_response",
                    "original_status": previous["status"],
                    "reason": previous.get("first_error"),
                }
            )
            continue
        calls = frozen_calls.FrozenCalls(
            archive, task, arm, synthetic=run_mode == "fixture"
        )
        seat = out / task / arm

        def answer(phase, messages, frozen=calls):
            return frozen(phase, messages)["raw"].decode("utf8")

        result = trial.perform(
            seat,
            sources[task],
            arm,
            None,
            model_stages,
            program_stages,
            model_call=answer,
            mode="replay",
        )
        matched = (
            previous["status"] == result["status"]
            and previous["stages_completed"] == result["stages_completed"]
            and previous.get("first_error") == result.get("first_error")
            and previous.get("issues") == result.get("issues")
        )
        old_calls = {stage for stage in model_stages.STAGES if (past / stage).is_dir()}
        matched &= old_calls == {event["stage"] for event in calls.events}
        matched &= all(
            event["status"] == "exact_request_reused" for event in calls.events
        )
        old_card, new_card = past / "card.a2ui.jsonl", seat / "card.a2ui.jsonl"
        same_bytes = None
        if old_card.exists() or new_card.exists():
            same_bytes = (
                old_card.is_file()
                and new_card.is_file()
                and old_card.read_bytes() == new_card.read_bytes()
            )
            matched &= same_bytes
        rows.append(
            {
                "task": task,
                "arm": arm,
                "result": "matched" if matched else "mismatch",
                "original_status": previous["status"],
                "replay_status": result["status"],
                "card_bytes_equal": same_bytes,
                "requests": calls.events,
            }
        )
    write(
        out / "replay.json",
        {"archive_mode": run_mode, "new_physical_requests": 0, "seats": rows},
    )
    print(
        json.dumps(
            {
                "seats": len(rows),
                "matched": sum(r["result"] == "matched" for r in rows),
                "new_physical_requests": 0,
            }
        )
    )
    return all(r["result"] == "matched" for r in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    first = commands.add_parser("freeze", help="冻结输入、实现、队列和模型参数")
    first.add_argument("cases", type=Path)
    first.add_argument("out", type=Path)
    first.add_argument("--arms", nargs="+", choices=trial.ARMS, default=trial.ARMS)
    for command, help_text in (
        ("fixture", "用内置虚构应答做离线演练"),
        ("live", "向冻结的模型服务实发请求"),
    ):
        item = commands.add_parser(command, help=help_text)
        item.add_argument("batch", type=Path)
    last = commands.add_parser("replay", help="同题同档逐请求、首件字节复算")
    last.add_argument("batch", type=Path)
    last.add_argument("out", type=Path)
    last.add_argument("--archive", type=Path, help="可选的同源 v2 首件归档目录")
    args = parser.parse_args()
    if args.command == "freeze":
        freeze(args.cases, args.out, args.arms)
    elif args.command == "replay":
        return 0 if replay(args.batch, args.archive, args.out) else 1
    else:
        execute(args.batch, args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
