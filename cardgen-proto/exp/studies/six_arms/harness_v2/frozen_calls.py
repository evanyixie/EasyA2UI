"""按原协议比对同题、同档、同阶段的完整请求，仅在完全相同时复用已存响应。"""

import hashlib
import json

PHASES = ("one_shot", "content", "structure", "geometry", "theme", "emit")


def demand(ok, why):
    if not ok:
        raise ValueError(why)


def parse_unique(pairs):
    d = {}
    for k, v in pairs:
        demand(k not in d, "JSON 重复键")
        d[k] = v
    return d


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=parse_unique)


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def wire(messages):
    return json.dumps(
        messages, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf8")


class MissingHistoricalResponse(RuntimeError):
    """修复后的真实请求在这个席位上没有历史对照。"""


class FrozenCalls:
    def __init__(self, root, task, arm, *, synthetic=False):
        self.synthetic = synthetic
        self.seat = root / task / arm
        self.task = task
        self.arm = arm
        self.events = []

    def __call__(self, stage, messages):
        demand(
            stage in PHASES and all(e["stage"] != stage for e in self.events),
            "重复调用或未知阶段",
        )
        saved = self.seat / stage
        msg, call, response = (
            saved / "messages.json",
            saved / "call.json",
            saved / "response.txt",
        )
        event = {
            "task": self.task,
            "arm": self.arm,
            "stage": stage,
            "requested_wire_sha256": digest(wire(messages)),
            "saved_wire_sha256": None,
            "saved_messages_file_sha256": None,
            "status": "missing_historical_response",
        }
        self.events.append(event)
        if not msg.is_file():
            event["reason"] = "no_request_at_this_seat_and_stage"
            raise MissingHistoricalResponse(event["reason"])
        logged = read(msg)
        event.update(
            saved_wire_sha256=digest(wire(logged)), saved_messages_file_sha256=sha(msg)
        )
        if wire(logged) != wire(messages):
            event["reason"] = "different_messages_at_this_seat_and_stage"
            raise MissingHistoricalResponse(event["reason"])
        if not call.is_file() or not response.is_file():
            event["reason"] = "no_reusable_complete_response_at_this_seat_and_stage"
            raise MissingHistoricalResponse(event["reason"])
        receipt = read(call)
        demand(
            receipt["stage"] == stage
            and receipt["physical_attempts"] == (0 if self.synthetic else 1)
            and receipt["http_status"] == (None if self.synthetic else 200)
            and receipt["returned_model"] == (None if self.synthetic else "deepseek-flash")
            and (not self.synthetic or receipt["origin"] == "synthetic"),
            "原模型调用回执不完整",
        )
        raw = response.read_bytes()
        event.update(
            status="exact_request_reused",
            raw_response_sha256=digest(raw),
            old_call_sha256=sha(call),
            old_call_file=str(call.relative_to(self.seat)),
            request_id=receipt["request_id"],
            http_ms=receipt["http_ms"],
            usage=receipt["usage"],
        )
        return {"raw": raw, "receipt": receipt}
