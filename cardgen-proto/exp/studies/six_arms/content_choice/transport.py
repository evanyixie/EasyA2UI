"""六档单席位请求日志。先持久化占位，再发一次；完整响应可在本地复演。"""

import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path

API = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"
TOKEN_FIELDS = (
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "prompt_cache_hit_tokens",
    "prompt_cache_miss_tokens",
)


class TransportUncertain(RuntimeError):
    """已开始或已封存失败，不能自动重发。"""

    def __init__(self, message, receipt=None):
        super().__init__(message)
        self.receipt = receipt


class EvidenceMismatch(ValueError):
    """提示、文件或日志校验和不符。"""


class CallInProgress(RuntimeError):
    """另一线程或进程正在处理该席位。"""


def wire(obj):
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode(
        "utf-8"
    )


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.now(UTC).isoformat()


def export(path, data):
    """已有投影不可覆盖。缺文件可从原子提交的日志重建。"""
    if path.exists():
        if path.read_bytes() != data:
            raise EvidenceMismatch(f"{path.name} 摘要失配")
        return
    temp = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".tmp")
    with temp.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


@contextmanager
def seat_lock(root):
    with (root / ".seat.lock").open("a+b") as handle:
        if os.name == "nt":
            import msvcrt

            if handle.seek(0, 2) == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise CallInProgress("该席位正在执行，稍后读取其状态") from exc
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise CallInProgress("该席位正在执行，稍后读取其状态") from exc
        yield


def connect(root):
    db = sqlite3.connect(root / "ledger.sqlite3", timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA synchronous=FULL")
    db.execute("""CREATE TABLE IF NOT EXISTS calls(
        stage TEXT PRIMARY KEY, local_id TEXT UNIQUE NOT NULL, started TEXT NOT NULL,
        state TEXT NOT NULL, messages BLOB NOT NULL, messages_sha TEXT NOT NULL,
        raw BLOB, raw_sha TEXT, receipt BLOB, receipt_sha TEXT,
        origin TEXT NOT NULL DEFAULT 'injected_unknown')""")
    if "origin" not in {column[1] for column in db.execute("PRAGMA table_info(calls)")}:
        db.execute("ALTER TABLE calls ADD COLUMN origin TEXT NOT NULL DEFAULT 'injected_unknown'")
    return db


def unknown_receipt(stage, started):
    return {
        "stage": stage,
        "started_utc": started,
        "physical_attempts": None,
        "http_status": None,
        "request_id": None,
        "http_ms": None,
        "usage": None,
    }


def validated(row):
    if sha(row["messages"]) != row["messages_sha"]:
        raise EvidenceMismatch("消息日志校验失败")
    if row["state"] == "pending":
        return None
    if row["state"] not in ("completed", "failed") or row["receipt"] is None:
        raise EvidenceMismatch("请求日志终态无效")
    if sha(row["receipt"]) != row["receipt_sha"]:
        raise EvidenceMismatch("回执日志校验失败")
    if row["raw"] is not None and sha(row["raw"]) != row["raw_sha"]:
        raise EvidenceMismatch("响应日志校验失败")
    if row["state"] == "completed" and row["raw"] is None:
        raise EvidenceMismatch("完整回执缺少响应")
    return json.loads(row["receipt"])


def stage_result(root, row, prompt):
    receipt = validated(row)
    if prompt != row["messages"]:
        raise EvidenceMismatch("同一阶段的调用消息与已登记字节不同")
    folder = root / row["stage"]
    folder.mkdir(exist_ok=True)
    intent = {
        "stage": row["stage"],
        "local_request_id": row["local_id"],
        "started_utc": row["started"],
        "messages_sha256": row["messages_sha"],
    }
    export(folder / "messages.json", row["messages"])
    export(folder / "intent.json", wire(intent))
    if receipt is None:
        raise TransportUncertain(
            "发现未结占位，是否发出或完成未知", unknown_receipt(row["stage"], row["started"])
        )
    export(folder / "call.json", row["receipt"])
    if row["raw"] is not None:
        export(folder / "response.txt", row["raw"])
    export(
        folder / "seal.json",
        wire(
            {
                **intent,
                "state": row["state"],
                "raw_sha256": row["raw_sha"],
                "receipt_sha256": row["receipt_sha"],
            }
        ),
    )
    if row["state"] == "failed":
        raise TransportUncertain("已有失败或不确定回执，停止重发", receipt)
    return {"raw": row["raw"].decode("utf-8"), "receipt": receipt}


def make_caller(arm_dir, issue, *, origin=None):
    origin = origin or getattr(issue, "transport_origin", "injected_unknown")
    if origin not in {"official_http", "historical_replay", "synthetic", "injected_unknown"}:
        raise ValueError("传输来源须能区分本轮、历史或合成回执")
    root = Path(arm_dir) / "calls"
    root.mkdir(parents=True, exist_ok=True)

    def caller(stage, messages):
        if not isinstance(stage, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", stage):
            raise ValueError("不合法阶段名")
        prompt = wire(messages)
        folder = root / stage
        with seat_lock(root), closing(connect(root)) as db:
            query = "SELECT * FROM calls WHERE stage = ?"
            row = db.execute(query, (stage,)).fetchone()
            if row:
                return stage_result(root, row, prompt)
            if folder.exists():
                raise EvidenceMismatch("阶段归档已存在，但无相配请求日志")
            local_id, started = uuid.uuid4().hex, utc()
            with db:
                db.execute(
                    "INSERT INTO calls(stage,local_id,started,state,messages,messages_sha,origin)"
                    " VALUES(?,?,?,'pending',?,?,?)",
                    (stage, local_id, started, prompt, sha(prompt), origin),
                )
            folder.mkdir()
            intent = {
                "stage": stage,
                "local_request_id": local_id,
                "started_utc": started,
                "messages_sha256": sha(prompt),
            }
            export(folder / "messages.json", prompt)
            export(folder / "intent.json", wire(intent))
            raw = None
            receipt = unknown_receipt(stage, started)
            try:
                result = issue(stage, json.loads(prompt))
                if not isinstance(result["raw"], (str, bytes)) or not isinstance(
                    result["receipt"], dict
                ):
                    raise TypeError("传输层未返回文本与回执")
                raw = result["raw"]
                if isinstance(raw, bytes):
                    raw.decode("utf-8")
                else:
                    raw = raw.encode("utf-8")
                receipt = dict(result["receipt"])
                if receipt.get("stage", stage) != stage:
                    raise ValueError("回执阶段不符")
                if receipt.get("http_status") is not None and receipt["http_status"] != 200:
                    raise ValueError("未取得成功 HTTP 回执")
                state = "completed"
            except Exception as exc:  # noqa: BLE001 — 记录回调失败，防止席位重发
                if isinstance(exc, TransportUncertain) and isinstance(exc.receipt, dict):
                    receipt.update(exc.receipt)
                receipt["transport_error_type"] = type(exc).__name__
                state = "failed"
            data = wire(receipt)
            with db:
                db.execute(
                    "UPDATE calls SET state=?,raw=?,raw_sha=?,receipt=?,receipt_sha=?"
                    " WHERE stage=?",
                    (state, raw, sha(raw) if raw is not None else None, data, sha(data), stage),
                )
            return stage_result(root, db.execute(query, (stage,)).fetchone(), prompt)

    return caller


def physical_ledger(arm_dir):
    root = Path(arm_dir) / "calls"
    records = []
    if root.is_dir():
        db_file = root / "ledger.sqlite3"
        if not db_file.exists() and any(p.is_dir() for p in root.iterdir()):
            raise EvidenceMismatch("席位有归档但缺少日志")
        if db_file.exists():
            with closing(sqlite3.connect(db_file.resolve().as_uri() + "?mode=ro", uri=True)) as db:
                db.row_factory = sqlite3.Row
                for row in db.execute("SELECT * FROM calls ORDER BY rowid"):
                    receipt = validated(row)
                    if receipt is None:
                        receipt = unknown_receipt(row["stage"], row["started"])
                    records.append(
                        {
                            "stage": row["stage"],
                            "local_request_id": row["local_id"],
                            "state": row["state"],
                            "origin": row["origin"]
                            if "origin" in row.keys()  # noqa: SIM118 — sqlite3.Row 的成员测试检查值
                            else "injected_unknown",
                            "messages_sha256": row["messages_sha"],
                            "raw_sha256": row["raw_sha"],
                            "receipt_sha256": row["receipt_sha"],
                            "receipt": receipt,
                        }
                    )
    ids = [r["receipt"].get("request_id") for r in records if r["receipt"].get("request_id")]
    if len(ids) != len(set(ids)):
        raise EvidenceMismatch("不同阶段出现同一供应方请求编号")

    def summed(values, *, confirmed_empty=False):
        return (
            sum(values)
            if (values or confirmed_empty) and all(type(v) is int and v >= 0 for v in values)
            else None
        )

    def metric(record, key):
        values = record["receipt"].get("usage")
        return values.get(key) if isinstance(values, dict) else None

    usage = {k: summed([metric(r, k) for r in records]) for k in TOKEN_FIELDS}
    new = [r for r in records if r["origin"] not in {"historical_replay", "synthetic"}]
    unconfirmed_origin = any(r["origin"] == "injected_unknown" for r in new)
    new_attempts = (
        None
        if unconfirmed_origin
        else summed([r["receipt"].get("physical_attempts") for r in new], confirmed_empty=True)
    )
    new_usage = {
        k: None if unconfirmed_origin else summed([metric(r, k) for r in new], confirmed_empty=True)
        for k in TOKEN_FIELDS
    }
    return {
        "records": records,
        "unique_local_intents": len(records),
        "known_provider_request_ids": len(ids),
        "physical_attempts": summed(
            [r["receipt"].get("physical_attempts") for r in records], confirmed_empty=True
        ),
        "usage": usage,
        "usage_scope": "注入或供应方回执上记录的物理量，一份原回执只计一次",
        "new_physical_attempts": new_attempts,
        "new_usage": new_usage,
    }


def make_deepseek_issue(*, env_var="DEEPSEEK_API_KEY", transport=None):
    """可选官方网适配器。仅在调用回调时读取原 v2 授权变量，HTTP 配置沿用原版本。"""
    if env_var != "DEEPSEEK_API_KEY":
        raise ValueError("此适配器读取 DEEPSEEK_API_KEY")

    def issue(stage, messages):
        import httpx

        token = os.environ.get(env_var)
        receipt = unknown_receipt(stage, utc())
        receipt.update(requested_model=MODEL, returned_model=None, finish_reason=None)
        if not token:
            raise TransportUncertain("缺少已授权凭据", receipt)
        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0,
            "thinking": {"type": "disabled"},
            "stream": False,
            "max_tokens": 8192,
        }
        start = time.perf_counter()
        try:
            with httpx.Client(
                headers={"Authorization": "Bearer " + token},
                timeout=httpx.Timeout(180, connect=15),
                follow_redirects=False,
                transport=transport,
            ) as client:
                response = client.post(API, json=payload)
                receipt.update(
                    http_status=response.status_code,
                    physical_attempts=1,
                    request_id=response.headers.get("x-ds-trace-id"),
                )
                if response.status_code != 200:
                    raise ValueError("HTTP 未成功")
                body = response.json()
                receipt.update(
                    usage=body.get("usage"),
                    returned_model=body.get("model"),
                    request_id=receipt["request_id"] or body.get("id"),
                    finish_reason=body["choices"][0].get("finish_reason"),
                )
                answer = body["choices"][0]["message"]["content"]
                if receipt["returned_model"] != MODEL or not isinstance(answer, str):
                    raise ValueError("实际模型或消息类型与冻结条件不符")
        except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError) as exc:
            receipt["error_class"] = type(exc).__name__
            raise TransportUncertain("供应方回执失败或未完整返回", receipt) from None
        finally:
            receipt["http_ms"] = round(1000 * (time.perf_counter() - start), 3)
        return {"raw": answer, "receipt": receipt}

    issue.transport_origin = "official_http" if transport is None else "injected_unknown"
    return issue
