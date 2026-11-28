"""冻结固定内容，执行模型/程序双臂；默认离线输入可通过 --replay 提供。"""

import argparse
import copy
import json
import os
import secrets
import sys
import time
from collections import Counter
from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime
from pathlib import Path

import httpx
import PIL

from evidence import ARMS, digest, read, require, safe_name, sealed_seats, sha
from evidence import atomic as save

HERE = Path(__file__).resolve().parent
ALIASES = dict(zip("AB", ARMS, strict=True))


def utc():
    return datetime.now(UTC).isoformat()


def write_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + secrets.token_hex(6) + ".tmp")
    with temp.open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


@contextmanager
def single_writer(root):
    with (root / "writer.lock").open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def sources(inputs, order, roster):
    input_bytes, order_bytes, roster_bytes = (
        p.read_bytes() for p in (inputs, order, roster)
    )
    lines = input_bytes.splitlines()
    cases = {}
    for line in lines:
        obj = json.loads(line)
        tid = safe_name(obj["task_id"])
        require(tid not in cases, "重复题号")
        cases[tid] = (obj, digest(line))
    queue = [json.loads(line) for line in order_bytes.splitlines()]
    families = [json.loads(line) for line in roster_bytes.splitlines()]
    require(
        cases
        and len(cases) == len(queue) == len(families)
        and set(cases)
        == {r["task_id"] for r in queue}
        == {r["task_id"] for r in families},
        "输入、顺序与题组必须一一对应",
    )
    for pos, row in enumerate(queue, 1):
        require(
            row["n"] == pos
            and row["execute"] in ("AB", "BA")
            and row["input_line_sha256"] == cases[row["task_id"]][1],
            "正式队列编号、顺序或原行摘要不符",
        )
    require(all(r["family_id"] for r in families), "缺少题组")
    require(
        len({os.path.normcase(k) for k in cases}) == len(cases),
        "题号在本文件系统上发生重名",
    )
    hashes = {
        "input_sha256": digest(input_bytes),
        "order_sha256": digest(order_bytes),
        "roster_sha256": digest(roster_bytes),
    }
    return cases, queue, families, hashes


def lock_frame(hashes, queue, families):
    dep = runtime.dependencies()
    dep.update({f"fixed_layout/{p.name}": sha(p) for p in sorted(HERE.glob("*.py"))})
    config = {
        **hashes,
        "denominator": len(queue),
        "families": len({r["family_id"] for r in families}),
        "queue": queue,
        "arms": ALIASES,
        "dependencies": dep,
        "python": sys.version,
        "httpx": httpx.__version__,
        "pillow": PIL.__version__,
        "model": runtime.model,
        "api": runtime.api if REPLAY is None else None,
        "temperature": 0,
        "thinking": False,
        "max_tokens": 8192,
        "attempts_per_model_stage": 1,
        "repairs": 0,
        "retry_unknown": False,
        "mode": "live" if REPLAY is None else "offline_replay",
    }
    if REPLAY is not None:
        config["replay_sha256"] = {
            p.relative_to(REPLAY).as_posix(): sha(p)
            for p in sorted(REPLAY.glob("*/*/*"))
            if p.name in ("messages.json", "response.body")
        }
    blind = ROOT / "blind_map.json"
    if (ROOT / "freeze.json").exists():
        old = read(ROOT / "freeze.json")
        require(
            all(old[k] == v for k, v in config.items())
            and sha(blind) == old["blind_map_sha256"],
            "输入、实现、配置、匿名映射或回放源漂移",
        )
    else:
        require(
            all(p.name == "writer.lock" for p in ROOT.iterdir()),
            "请使用新的输出目录",
        )
        save(
            blind,
            {r["task_id"]: {arm: secrets.token_hex(16) for arm in ARMS} for r in queue},
        )
        save(
            ROOT / "freeze.json",
            {**config, "created_utc": utc(), "blind_map_sha256": sha(blind)},
        )
    return read(blind)


def folder(tid):
    return ROOT / "results" / tid


def prepare(row, row_sha):
    tid = row["task_id"]
    dest = folder(tid)
    receipt = dest / "input_receipt.json"
    shared_file = ROOT / "shared_inputs" / (tid + ".json")
    reference_file = dest / "reference.json"
    if not receipt.is_file():
        common = {"source_row_sha256": row_sha}
        phase = "adapter"
        start = time.perf_counter()
        try:
            shared = adapter.document(row)
            common["adapter_wall_ms"] = (time.perf_counter() - start) * 1000
            save(shared_file, shared)
            common["shared_sha256"] = sha(shared_file)
            phase = "reference"
            start = time.perf_counter()
            reference = layout.measurements(shared)
            common["reference_wall_ms"] = (time.perf_counter() - start) * 1000
            save(reference_file, reference)
            common.update(reference_sha256=sha(reference_file), status="accepted")
        except (
            ValueError,
            KeyError,
            TypeError,
            IndexError,
            ArithmeticError,
            RecursionError,
        ) as exc:
            common.update(
                status=phase + "_rejected",
                detail=str(exc),
                error_type=type(exc).__name__,
            )
            common[phase + "_wall_ms"] = (time.perf_counter() - start) * 1000
        save(receipt, common)
    rec = read(receipt)
    require(rec["source_row_sha256"] == row_sha, "共同输入来源变更")
    if rec["status"] == "accepted":
        require(
            rec["shared_sha256"] == sha(shared_file)
            and rec["reference_sha256"] == sha(reference_file),
            "逐题共同输入变更",
        )
        return rec, read(shared_file), read(reference_file)
    return rec, None, None


def exchange(client, call_dir, phase, messages):
    """先落盘提交意图。收到响应先保存完整信封，再解析。未知请求永不重发。"""
    path = call_dir / "call.json"
    message_file = call_dir / "messages.json"
    response_file = call_dir / "response.body"
    key = digest(runtime.signature(messages).encode())
    payload = {
        "model": runtime.model,
        "messages": messages,
        "temperature": 0,
        "thinking": {"type": "disabled"},
        "stream": False,
        "max_tokens": 8192,
    }
    rec = None
    if REPLAY is not None and not path.is_file():
        task = call_dir.parents[2].name
        entry = REPLAY / task / phase
        save(message_file, messages)
        rec = {
            "stage": phase,
            "prompt_sha256": key,
            "http_status": None,
            "http_ms": None,
            "physical_attempts": 0,
            "physical_attempt_bounds": [0, 0],
            "state": "offline_response_missing",
            "usage": None,
            "source": "offline_fixture_or_replay",
        }

        def frozen_blob(name):
            external = entry / name
            rel = external.relative_to(REPLAY).as_posix()
            expected = REPLAY_HASHES.get(rel)
            if not external.is_file():
                if expected is not None:
                    raise RuntimeError("冻结的回放文件丢失，保留本次批次")
                return None
            blob = external.read_bytes()
            if digest(blob) != expected:
                raise RuntimeError("回放源在冻结后变化，保留本次批次")
            return blob

        raw_prompt = frozen_blob("messages.json")
        envelope = frozen_blob("response.body")
        if raw_prompt is not None:
            rec["exported_prompt_sha256"] = digest(raw_prompt)
            try:
                matches = json.loads(raw_prompt) == messages
            except (ValueError, UnicodeError):
                matches = False
            if not matches:
                rec["state"] = "offline_prompt_mismatch"
            elif envelope is not None:
                write_bytes(response_file, envelope)
                rec.update(state="offline_envelope", envelope_sha256=digest(envelope))
        elif envelope is not None:
            rec["state"] = "offline_prompt_missing"
        save(path, rec)
    if path.is_file():
        rec = read(path)
        if rec["prompt_sha256"] != key or read(message_file) != messages:
            raise RuntimeError("持久化请求与重建的请求不符，原件已保留")

    else:
        if response_file.exists() or (call_dir / "response.txt").exists():
            raise RuntimeError("已有响应但缺调用回执，禁止重发")
        save(message_file, messages)
        rec = {
            "stage": phase,
            "requested_model": runtime.model,
            "prompt_sha256": key,
            "payload_sha256": digest(runtime.signature(payload).encode()),
            "started_utc": utc(),
            "physical_attempts": None,
            "physical_attempt_bounds": [0, 1],
            "usage": None,
            "http_status": None,
            "http_ms": None,
            "state": "dispatch_intent",
        }
        save(path, rec)
        start = time.perf_counter()
        try:
            response = client.post(runtime.api, json=payload)
            rec.update(
                http_status=response.status_code,
                physical_attempts=1,
                physical_attempt_bounds=[1, 1],
                http_ms=round((time.perf_counter() - start) * 1000, 3),
                request_id=response.headers.get("x-ds-trace-id"),
                state="http_returned",
                expected_body_sha256=digest(response.content),
            )
            # 响应元数据先持久化，使写入正文后的断点可以恢复且无需再次请求。
            save(path, rec)
            write_bytes(response_file, response.content)
            rec["envelope_sha256"] = rec["expected_body_sha256"]
        except httpx.RequestError as exc:
            rec.update(
                state="transport_unknown",
                error_type=type(exc).__name__,
                physical_attempts=1,
                physical_attempt_bounds=[1, 1],
                http_ms=round((time.perf_counter() - start) * 1000, 3),
            )
        rec["ended_utc"] = utc()
        save(path, rec)
    if (REPLAY is None and rec["http_status"] != 200) or not response_file.is_file():
        return None, rec
    if not rec.get("envelope_sha256") and rec.get("expected_body_sha256"):
        rec["envelope_sha256"] = rec["expected_body_sha256"]
    if sha(response_file) != rec.get("envelope_sha256"):
        raise RuntimeError("服务响应摘要不符，原件已保留")
    try:
        body = json.loads(response_file.read_bytes())
        choice = body["choices"][0]
        answer = choice["message"]["content"]
        if not isinstance(answer, str):
            raise TypeError("无正文")
        rec.update(
            usage=body.get("usage") if REPLAY is None else None,
            returned_model=body.get("model"),
            request_id=rec.get("request_id") or body.get("id"),
            finish_reason=choice.get("finish_reason"),
            state="offline_response_recorded"
            if REPLAY is not None
            else "response_recorded",
            response_sha256=digest(answer.encode()),
        )
        write_bytes(call_dir / "response.txt", answer.encode())
        save(path, rec)
        return answer, rec
    except (ValueError, TypeError, IndexError, KeyError, AttributeError) as exc:
        rec.update(state="invalid_service_envelope", error_type=type(exc).__name__)
        save(path, rec)
        return None, rec


def decide(dest, arm, phase, shared, reference, client, tree=None):
    outcome = dest / (phase + "_receipt.json")
    selected = dest / (phase + ".json")
    if outcome.exists():
        rec = read(outcome)
        if rec["status"] == "accepted":
            require(sha(selected) == rec["decision_sha256"], "阶段产物摘要不符")
            return read(selected), rec
        return None, rec
    owner = arm.split("_")[0]
    call_dir = dest / "calls" / phase
    recovered = (call_dir / "call.json").is_file()
    rec = {
        "owner": owner,
        "stage": phase,
        "first_pass": True,
        "started_utc": utc(),
        "replayed_from_persisted_call": recovered,
    }
    start = time.perf_counter()
    result = None
    try:
        if owner == "model":
            messages = layout.prompt(phase, shared, reference, tree)
            raw, call = exchange(client, call_dir, phase, messages)
            rec.update(
                request_dir=(Path("calls") / phase).as_posix(),
                prompt_sha256=call["prompt_sha256"],
                http_ms=call["http_ms"],
                http_status=call["http_status"],
                service_state=call["state"],
                cache_reused=recovered,
            )
            if raw is None:
                rec.update(
                    status="transport_unknown",
                    detail="HTTP " + str(call["http_status"]) + " " + call["state"],
                )
            else:
                result = layout.parse(raw)
                if phase == "geometry":
                    result = native.apply_decisions(tree, result, shared)
        elif phase == "structure":
            result = program_layout.program_route(shared)
        else:
            result = program_layout.program_geometry(tree, shared)
        if "status" not in rec:
            if phase == "structure":
                native.roles_and_clicks(result, shared)
                program_layout.validate_tree(result, shared)
            rec["status"] = "accepted"
    except (ValueError, KeyError, TypeError, RecursionError) as exc:
        result = None
        rec.update(status="rejected", detail=str(exc), error_type=type(exc).__name__)
    except (IndexError, ArithmeticError, AttributeError) as exc:
        result = None
        rec.update(
            status="implementation_unknown",
            detail=str(exc),
            error_type=type(exc).__name__,
        )
    rec.update(
        ended_utc=utc(),
        wall_ms=None if recovered else (time.perf_counter() - start) * 1000,
    )
    if result is not None:
        save(selected, result)
        rec["decision_sha256"] = sha(selected)
    save(outcome, rec)
    return result, rec


def run_arm(tid, arm, prepared, client, code):
    dest = folder(tid) / arm
    receipt = dest / "receipt.json"
    if receipt.exists():
        return read(receipt)
    common, shared, reference = prepared
    rec = {
        "task_id": tid,
        "cell": arm,
        "first_pass": True,
        "source_row_sha256": common["source_row_sha256"],
        "shared_sha256": common.get("shared_sha256"),
        "reference_sha256": common.get("reference_sha256"),
        "started_utc": utc(),
        "structure": None,
        "geometry": None,
        "business_pass": None,
        "native_visual_pass": None,
        "independent_reference_pass": None,
        "anonymous_id": code,
        "emit_wall_ms": None,
    }
    if shared is None:
        rec.update(status="common_" + common["status"], detail=common["detail"])
    else:
        tree, sr = decide(dest, arm, "structure", shared, reference, client)
        rec["structure"] = sr
        if sr["status"] != "accepted":
            rec.update(status="structure_" + sr["status"], detail=sr["detail"])
        else:
            geo, gr = decide(
                dest, arm, "geometry", shared, reference, client, copy.deepcopy(tree)
            )
            rec["geometry"] = gr
            if gr["status"] != "accepted":
                rec.update(status="geometry_" + gr["status"], detail=gr["detail"])
            else:
                start = time.perf_counter()
                try:
                    messages = native.emit(geo, shared, tree)
                    wire = "\n".join(runtime.signature(m) for m in messages)
                    complaints = list(
                        runtime.validate(wire, "surface_card", shared["size"])
                    )
                    require(not complaints, "Easy共同出口拒绝 " + str(complaints))
                    data = (wire + "\n").encode()
                    write_bytes(dest / "card.a2ui.jsonl", data)
                    write_bytes(ROOT / "anonymous" / code / "card.a2ui.jsonl", data)
                    rec.update(status="artifact_ready", artifact_sha256=digest(data))
                except (ValueError, KeyError, TypeError) as exc:
                    rec.update(
                        status="emit_rejected",
                        detail=str(exc),
                        error_type=type(exc).__name__,
                    )
                rec["emit_wall_ms"] = (time.perf_counter() - start) * 1000
    rec["ended_utc"] = utc()
    save(receipt, rec)
    return rec


def execute(cases, queue, mapping, client):
    susp = "缺少运行时凭据，模型席位暂缓" if REPLAY is None and client is None else None
    failures = 0
    counts = Counter()
    receipts = {}
    calls = []
    for entry in queue:
        tid = entry["task_id"]
        prepared = prepare(*cases[tid])
        for letter in entry["execute"]:
            arm = ALIASES[letter]
            dest = folder(tid) / arm
            path = dest / "receipt.json"
            if (
                not path.exists()
                and arm == ARMS[0]
                and prepared[1] is not None
                and susp
            ):
                continue
            recorded = path.is_file()
            rec = run_arm(tid, arm, prepared, client, mapping[tid][arm])
            receipts[path.relative_to(ROOT).as_posix()] = sha(path)
            counts[rec["status"]] += 1
            for phase in ("structure", "geometry"):
                call = dest / "calls" / phase / "call.json"
                if call.exists():
                    calls.append(read(call))
            if (
                REPLAY is not None
                or recorded
                or arm != ARMS[0]
                or rec["structure"] is None
            ):
                continue
            if rec["status"].endswith("transport_unknown"):
                stage = rec["geometry"] or rec["structure"]
                failures += 1
                if stage.get("http_status") in (401, 402) or failures >= 3:
                    susp = "模型服务异常，保留已发席位；可再次运行以继续未发席位"
                else:
                    time.sleep(20)
            else:
                failures = 0
    anon = ROOT / "anonymous"
    manifest = [
        {
            "anonymous_id": p.parent.name,
            "relative_card_path": p.relative_to(anon).as_posix(),
            "sha256": sha(p),
        }
        for p in sorted(anon.glob("*/card.a2ui.jsonl"))
    ]
    save(anon / "manifest.json", manifest)
    complete = len(receipts) == len(queue) * 2
    status = {
        "assigned": len(queue) * 2,
        "terminal_slots": len(receipts),
        "unexecuted": len(queue) * 2 - len(receipts),
        "generation": dict(counts),
        "model_service_pause": susp,
        "sealed": complete,
        "mode": "offline_replay" if REPLAY is not None else "live",
        "physical_attempts_known": sum(c["physical_attempts"] or 0 for c in calls),
        "physical_attempts_unknown_calls": sum(
            c["physical_attempts"] is None for c in calls
        ),
        "missing_usage_live_calls": sum(c.get("usage") is None for c in calls)
        if REPLAY is None
        else None,
        "known_usage": dict(
            sum(
                (
                    Counter(
                        {
                            k: v
                            for k, v in (c.get("usage") or {}).items()
                            if type(v) is int
                        }
                    )
                    for c in calls
                ),
                Counter(),
            )
        )
        if REPLAY is None
        else None,
    }
    if complete:
        evidence_hashes = {
            p.relative_to(ROOT).as_posix(): sha(p)
            for sub in ("results", "shared_inputs", "anonymous")
            for p in (ROOT / sub).rglob("*")
            if p.is_file()
        }
        save(
            ROOT / "seal.json",
            {
                "evidence_sha256": evidence_hashes,
                "freeze_sha256": sha(ROOT / "freeze.json"),
                "anonymous_manifest_sha256": sha(anon / "manifest.json"),
                "receipts_count": len(receipts),
                "arm_receipt_sha256": receipts,
            },
        )
        sealed_seats(ROOT, len(queue))
    save(ROOT / "status.json", status)
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run"))
    for name in ("input", "order", "roster", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument(
        "--formal219",
        action="store_true",
        help="核对原正式框的输入、顺序、题组摘要及分母",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--replay",
        type=Path,
        help="本地 TASK/STAGE/{messages.json,response.body} 目录，不联网",
    )
    mode.add_argument(
        "--live", action="store_true", help="使用实际服务，凭据从 DEEPSEEK_API_KEY 读取"
    )
    args = parser.parse_args()
    global ROOT, REPLAY, REPLAY_HASHES, runtime, layout, native, program_layout, adapter
    import common_native as native
    import layout_decisions as layout
    import program_layout
    import runtime
    import shared_adapter as adapter

    ROOT, REPLAY = (
        args.out.resolve(),
        args.replay.resolve() if args.replay is not None else None,
    )
    require(REPLAY is None or REPLAY.is_dir(), "回放目录不存在")
    require(
        REPLAY is None or not ROOT.is_relative_to(REPLAY),
        "输出目录不能位于离线回放源内",
    )
    ROOT.mkdir(parents=True, exist_ok=True)
    with single_writer(ROOT):
        cases, queue, families, hashes = sources(args.input, args.order, args.roster)
        if args.formal219:
            require(
                len(queue) == 219
                and len({r["family_id"] for r in families}) == 200
                and (
                    hashes["input_sha256"],
                    hashes["order_sha256"],
                    hashes["roster_sha256"],
                )
                == (
                    "fa0371fc56f9a3973b77e541fef81b5dc77672f718a1b4f26fe397abf432d2de",
                    "47f889933a46c364da21078aee2f86bbe1e7a8d546b2797feceaec77d1ad321e",
                    "bf42e4a0cfd4d5698f3a9057231acaf9040a58380f3131a172cde3297e8a4b1b",
                ),
                "原正式框的输入、队列或题组版本不同",
            )
        mapping = lock_frame(hashes, queue, families)
        REPLAY_HASHES = read(ROOT / "freeze.json").get("replay_sha256", {})
        if args.command == "freeze":
            print(
                json.dumps(
                    {"pairs": len(queue), "freeze_sha256": sha(ROOT / "freeze.json")}
                )
            )
            return
        if (ROOT / "seal.json").exists():
            seats, _ = sealed_seats(ROOT, len(queue))
            print(json.dumps({"sealed_seats": len(seats), "unchanged": True}))
            return
        key = os.getenv("DEEPSEEK_API_KEY")

        context = (
            nullcontext(None)
            if REPLAY is not None or not key
            else httpx.Client(
                headers={"Authorization": "Bearer " + key},
                timeout=httpx.Timeout(180, connect=15),
                follow_redirects=False,
            )
        )
        with context as client:
            print(
                json.dumps(execute(cases, queue, mapping, client), ensure_ascii=False)
            )


if __name__ == "__main__":
    main()
