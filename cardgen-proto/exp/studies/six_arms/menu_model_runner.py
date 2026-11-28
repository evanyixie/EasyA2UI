"""One official selector call per multi-option frozen public-information wire."""

import argparse
import hashlib
import json
import os
import tempfile
import time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx

API = "https://api.deepseek.com/chat/completions"
SERVICE = {
    "model": "deepseek-flash",
    "temperature": 0,
    "thinking": {"type": "disabled"},
    "stream": False,
    "max_tokens": 8192,
}
SYSTEM = (
    "为给定尺寸的桌面卡从提供的布局结构中选择一个。目标是以既定标准字号完整容纳所有文字和操作，"
    "保持主次、对象归属和文字可读，避免裁切、重叠与溢出。"
    "只能使用本题给出的候选及共享信息，候选中的尺寸估计不是编译结论。"
    "只能选择，不可重新排版或删改内容。只返回一个 JSON 对象，其中唯一字段 choice "
    "的值为所选候选的实际字符串 id。不要解释。"
)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(obj):
    return (
        json.dumps(
            obj,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()


def read(path):
    return json.loads(path.read_bytes())


def require(test, message):
    if not test:
        raise ValueError(message)


def publish(path, data, *, replace=False):
    if path.exists() and not replace:
        require(path.read_bytes() == data, f"sealed file differs: {path.name}")
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        name = tmp.name
    try:
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def writer(folder):
    # OS closes/relinquishes the byte-range lock on process death.
    import msvcrt

    with (folder / ".writer").open("a+b") as handle:
        if handle.seek(0, 2) == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def verify_row(r):
    raw = Path(r["wire_path"]).read_bytes()
    require(sha(raw) == r["wire_sha256"], "common wire differs")
    data = json.loads(raw)
    require(
        isinstance(data, dict) and isinstance(data["choices"], list), "missing choices"
    )
    opts = [c["id"] for c in data["choices"]]
    require(
        r["options"] == opts
        and all(isinstance(k, str) and k for k in opts)
        and len(set(opts)) == len(opts),
        "public menu IDs differ",
    )
    return raw.decode("utf-8")


def freeze(index, fingerprint, dest):
    require(sha(index.read_bytes()) == fingerprint.lower(), "index digest differs")
    rows = read(index)["rows"]
    require(len(rows) == len({r["task_id"] for r in rows}), "duplicate task")
    for r in rows:
        require(isinstance(r["task_id"], str) and r["task_id"], "invalid task ID")
        verify_row(r)
    dest.mkdir(parents=True, exist_ok=True)
    with writer(dest):
        plan = {
            "runner_sha256": sha(Path(__file__).read_bytes()),
            "index": str(index.resolve()),
            "index_sha256": fingerprint.lower(),
            "service": SERVICE,
            "endpoint": API,
            "system": SYSTEM,
            "attempts_per_multi_choice": 1,
            "credential_variable": "FUSION_OFFICIAL_API_KEY",
            "timing": "Model decision_ms = messages/payload construction + real HTTP wall time + response decoding; excludes persistence. http_ms = time spent awaiting the official HTTP response.",
            "rows": len(rows),
            "multi_choice": sum(len(r["options"]) > 1 for r in rows),
        }
        publish(dest / "plan.json", blob(plan))
    return plan


def decode(text, options):
    def unique(pairs):
        d = dict(pairs)
        require(len(d) == len(pairs), "duplicate key")
        return d

    answer = json.loads(text, object_pairs_hook=unique)
    require(
        isinstance(answer, dict)
        and set(answer) == {"choice"}
        and isinstance(answer["choice"], str)
        and answer["choice"] in options,
        "invalid selection",
    )
    return answer["choice"]


def issue(client, request, options):
    t0 = time.perf_counter()
    response = None
    info = {
        "http_status": None,
        "http_ms": None,
        "actual_model": None,
        "usage": None,
        "request_id": None,
        "finish_reason": None,
        "choice": None,
        "status": "transport_unknown",
        "confirmed_requests": None,
    }
    try:
        response = client.post(
            API, content=request, headers={"Content-Type": "application/json"}
        )
        info.update(
            http_status=response.status_code,
            confirmed_requests=1,
            request_id=response.headers.get("x-ds-trace-id"),
        )
    except httpx.RequestError as err:
        info["error_class"] = type(err).__name__
    info["http_ms"] = round(1000 * (time.perf_counter() - t0), 3)
    body = None
    if response is None or response.status_code != 200:
        return info, body
    try:
        body = response.json()
        info.update(
            actual_model=body.get("model"),
            usage=body.get("usage"),
            request_id=info["request_id"] or body.get("id"),
            finish_reason=body["choices"][0].get("finish_reason"),
        )
        if info["actual_model"] != SERVICE["model"]:
            info["status"] = "unexpected_model"
        else:
            info.update(
                choice=decode(body["choices"][0]["message"]["content"], options),
                status="selected",
            )
    except (TypeError, KeyError, ValueError, IndexError, AttributeError) as err:
        info.update(status="invalid_response", error_class=type(err).__name__)
        if body is None:
            body = {"non_json_response_sha256": sha(response.content)}
    return info, body


def select(row, client, folder):
    raw = verify_row(row)
    options = row["options"]
    tid = row["task_id"]
    task = folder / sha(tid.encode())
    task.mkdir(exist_ok=True)
    dest = task / "result.json"
    if dest.exists():
        previous = read(dest)
        require(
            previous["task_id"] == tid
            and previous["wire_sha256"] == row["wire_sha256"]
            and previous["options"] == options,
            "result identity differs",
        )
        return previous
    info = {
        "task_id": tid,
        "wire_sha256": row["wire_sha256"],
        "options": options,
        "actual_model": None,
        "usage": None,
        "http_status": None,
        "http_ms": None,
        "decision_ms": None,
        "confirmed_requests": 0,
        "local_intents": 0,
        "choice": None,
    }
    if len(options) < 2:
        info.update(
            status="forced" if options else "empty",
            choice=options[0] if options else None,
        )
    else:
        start = time.perf_counter()
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": raw},
        ]
        payload = blob(dict(**SERVICE, messages=messages))
        prep_ms = (time.perf_counter() - start) * 1000
        publish(task / "request.json", payload)
        evidence = task / "http.json"
        intent = task / "intent.json"
        info["local_intents"] = 1
        if not intent.exists():
            publish(
                intent, blob({"started_utc": now(), "request_sha256": sha(payload)})
            )
            start = time.perf_counter()
            receipt, answer = issue(client, payload, options)
            receipt["decision_ms"] = round(
                prep_ms + (time.perf_counter() - start) * 1000, 3
            )
            publish(evidence, blob({"receipt": receipt, "answer": answer}))
        require(read(intent)["request_sha256"] == sha(payload), "intent differs")
        if evidence.is_file():
            info.update(read(evidence)["receipt"])
        else:
            info.update(confirmed_requests=None, status="interrupted_unknown")
    publish(dest, blob(info))
    return info


def run_locked(dest, client):
    plan = read(dest / "plan.json")
    idx = Path(plan["index"])
    require(
        sha(idx.read_bytes()) == plan["index_sha256"]
        and sha(Path(__file__).read_bytes()) == plan["runner_sha256"]
        and plan["system"] == SYSTEM
        and plan["service"] == SERVICE
        and plan["endpoint"] == API,
        "frozen execution changed",
    )
    entries = read(idx)["rows"]
    seats = dest / "seats"
    seats.mkdir(exist_ok=True)
    results = []
    for row in entries:
        result = select(row, client, seats)
        results.append(result)
        if result["http_status"] in (401, 402):
            break
        if len(results) % 20 == 0:
            print("已登记席位", len(results), "/", len(entries), flush=True)
    summary = {
        "rows": len(entries),
        "registered": len(results),
        "unexecuted": len(entries) - len(results),
        "statuses": dict(Counter(r["status"] for r in results)),
        "local_intents": sum(r["local_intents"] for r in results),
        "confirmed_requests": sum(r["confirmed_requests"] or 0 for r in results),
        "uncertain_request_count": sum(
            r["confirmed_requests"] is None for r in results
        ),
        "endpoint": API,
        "stopped_http": next(
            (r["http_status"] for r in results if r["http_status"] in (401, 402)), None
        ),
    }
    publish(dest / "choices.jsonl", b"".join(blob(r) for r in results), replace=True)
    publish(dest / "summary.json", blob(summary), replace=True)
    return summary


def run(dest):
    api_key = os.environ.get("FUSION_OFFICIAL_API_KEY")
    require(bool(api_key), "official endpoint key is not configured")
    with (
        writer(dest),
        httpx.Client(
            headers={"Authorization": "Bearer " + api_key},
            timeout=httpx.Timeout(120, connect=15),
            follow_redirects=False,
        ) as client,
    ):
        return run_locked(dest, client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    register = sub.add_parser("freeze")
    register.add_argument("index", type=Path)
    register.add_argument("index_sha256")
    register.add_argument("out", type=Path)
    execute = sub.add_parser("run")
    execute.add_argument("out", type=Path)
    args = parser.parse_args()
    if args.command == "freeze":
        result = freeze(args.index, args.index_sha256, args.out)
        print("已冻结", result["rows"], "题，多候选", result["multi_choice"])
    else:
        print(json.dumps(run(args.out), ensure_ascii=False))
