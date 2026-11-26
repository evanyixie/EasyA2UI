"""开发集 L1–L6 配对组装器。六档共用同一份阶段实现、原始数据和产物检查。"""

import hashlib
import importlib.util
import json
import os
import random
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

UPSTREAM = Path(os.environ.get("EASY_CARDGEN_ROOT") or Path(__file__).resolve().parents[4])
MODEL = "deepseek-flash"
ARMS = ("L1", "L2", "L3", "L4", "L5", "L6")
PHASES = ("content", "structure", "geometry", "theme", "emit")
API = "https://api.deepseek.com/chat/completions"
BOUND = re.compile(r"\$\{(/[^}]+)\}")


def imported(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CONDITIONS = imported("easy_pinned_conditions", UPSTREAM / "exp/conditions.py")
VALIDATE = imported("easy_pinned_validate", UPSTREAM / "src/validate.py").validate_a2ui


def read(p):
    return json.loads(p.read_bytes())


def write(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf8",
    )


def hashfile(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signature(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def lookup(data, path):
    for part in path.strip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        data = data[int(part)] if isinstance(data, list) else data[part]
    return data


def lookup_wrapped(data, path):
    if path == "/":
        return data
    return lookup(data, path)


def outgoing_data(message):
    data = message["updateDataModel"]
    path = data["path"]
    if path == "/":
        return data["value"]
    result = data["value"]
    for word in reversed(path.strip("/").split("/")):
        result = {word: result}
    return result


def source_for(req, samples):
    paths = []
    for row in req.get("candidateDataBindings", []):
        stem = row["writeResultTo"].rstrip("/")
        for suffix in row.get("candidateOutputFields", []):
            if not isinstance(suffix, str):
                raise TypeError("candidateOutputFields 中有未支持的字段表达")
            path = (
                suffix
                if suffix.startswith(stem + "/")
                else stem + "/" + suffix.lstrip("/")
            )
            if path not in paths:
                paths.append(path)
    actions = []
    for i, act in enumerate(req.get("candidateEventCandidates", []), 1):
        action = {
            "id": "a" + str(i),
            "capabilityId": act.get("capabilityId"),
            "handler": act.get("action"),
        }
        for label_key in ("label", "description"):
            if act.get(label_key):
                action["label"] = act[label_key]
                break
        actions.append(action)
    business = {
        k: req[k]
        for k in (
            "title",
            "description",
            "size",
            "userQuery",
            "originalQuery",
            "candidateAssetIds",
            "candidateEventCandidates",
            "candidateDataBindings",
        )
        if k in req
    }
    return {
        "size": req["size"],
        "query": req.get("userQuery") or req.get("originalQuery") or "",
        "title": req.get("title", ""),
        "description": req.get("description", ""),
        "request": business,
        "candidate_paths": paths,
        "candidate_actions": actions,
        "sample_data": samples,
    }


def context_for(source):
    return {
        "size": source["size"],
        "sample_data": source["sample_data"],
        "action_handlers": {
            a["id"]: a["handler"]
            for a in source["candidate_actions"]
            if a.get("handler")
        },
    }


def inspect_card(messages, source):
    """仅测量原生协议、树完整性、动态证据、动作白名单。语义与可见性另审。"""
    errors = []
    encoded = "\n".join(signature(m) for m in messages)
    errors.extend(str(v) for v in VALIDATE(encoded, "surface_card", source["size"]))
    update = messages[1]["updateComponents"]
    comps = update["components"]
    by_id = {n["id"]: n for n in comps}
    seen = set()

    def visit(node_id):
        if node_id in seen:
            errors.append("DUPLICATE_PARENT_OR_CYCLE " + node_id)
            return
        seen.add(node_id)
        for child in by_id.get(node_id, {}).get("children", []):
            visit(child)

    visit(update.get("root", "root"))
    if len(by_id) != len(comps) or seen != set(by_id):
        errors.append("DUPLICATE_ID_OR_DISCONNECTED_TREE")
    data = outgoing_data(messages[2])
    stored = source["sample_data"]
    used = set()
    handlers = []
    unknown_samples = []
    visible_fragments = []

    def inspect(value):
        if isinstance(value, str):
            used.update(BOUND.findall(value))
        elif isinstance(value, list):
            for v in value:
                inspect(v)
        elif isinstance(value, dict):
            if isinstance(value.get("path"), str):
                used.add(value["path"])
            for v in value.values():
                inspect(v)

    for node in comps:
        for attr in ("content", "label", "src", "text", "value", "progress"):
            if attr in node:
                inspect(node[attr])
                if attr in ("content", "text", "label"):
                    visible_fragments.append(node[attr])
        for handler in node.get("onClick", []):
            handlers.append(signature(handler))
    available = {
        signature(a["handler"]) for a in source["candidate_actions"] if a.get("handler")
    }
    if set(handlers) - available:
        errors.append("UNAUTHORIZED_HANDLER")
    # 数据候选的使用数量单列；独立评价时才能断言用户明确要求的内容是否保全。
    for path in sorted(used):
        if path not in source["candidate_paths"]:
            errors.append("UNREGISTERED_BINDING " + path)
            continue
        try:
            wanted = lookup_wrapped(stored, path)
        except (KeyError, IndexError, TypeError, ValueError):
            unknown_samples.append(path)
            continue
        try:
            actual = lookup_wrapped(data, path)
        except (KeyError, IndexError, TypeError, ValueError):
            errors.append("MISSING_INITIAL_BINDING " + path)
            continue
        if signature(actual) != signature(wanted):
            errors.append("SAMPLE_CHANGED " + path)
    if unknown_samples:
        errors.append("MISSING_TRUSTED_INITIAL_SAMPLE " + ",".join(unknown_samples))
    if not visible_fragments:
        errors.append("NO_VISIBLE_TEXT")
    return {
        "errors": errors,
        "bound_paths": sorted(used),
        "unknown_sample_paths": unknown_samples,
        "candidate_path_count": len(source["candidate_paths"]),
        "action_handlers": handlers,
        "visible_fragments": visible_fragments,
        "visual_review": None,
        "business_review": None,
    }


def balanced_queue(ids):
    ids, arms = list(ids), list(ARMS)
    seed = random.Random(20261124)
    seed.shuffle(ids)
    seed.shuffle(arms)
    return [
        (task, arms[(i + j) % len(arms)])
        for i, task in enumerate(ids)
        for j in range(len(arms))
    ]


class ServiceFailure(Exception):
    pass


def request(client, messages, out, stage):
    import httpx

    folder = out / stage
    folder.mkdir()
    write(folder / "messages.json", messages)
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0,
        "thinking": {"type": "disabled"},
        "stream": False,
        "max_tokens": 8192,
    }
    rec = {
        "stage": stage,
        "requested_model": MODEL,
        "started_utc": datetime.now(UTC).isoformat(),
        "physical_attempts": 1,
        "usage": None,
        "http_status": None,
    }
    write(folder / "call.json", rec)
    start = time.perf_counter()
    try:
        response = client.post(API, json=payload)
        rec["http_status"] = response.status_code
        if response.status_code != 200:
            raise ServiceFailure(f"HTTP {response.status_code}")
        body = response.json()
        rec["usage"] = body.get("usage")
        rec["returned_model"] = body.get("model")
        rec["request_id"] = response.headers.get("x-ds-trace-id") or body.get("id")
        rec["finish_reason"] = body["choices"][0].get("finish_reason")
        answer = body["choices"][0]["message"]["content"]
        (folder / "response.txt").write_text(answer, encoding="utf8")
        if rec["returned_model"] != MODEL:
            raise ServiceFailure("返回的模型与冻结配置不符")
        return answer
    except (ValueError, TypeError, IndexError, KeyError) as exc:
        raise ServiceFailure("响应或回执格式异常") from exc
    except httpx.RequestError as exc:
        raise ServiceFailure(type(exc).__name__) from exc
    finally:
        rec["http_ms"] = round(1000 * (time.perf_counter() - start), 3)
        write(folder / "call.json", rec)


def perform(out, source, arm, client, model, program, *, model_call=None, mode="live"):
    out.mkdir(parents=True, exist_ok=False)
    phase = "input"
    rec = {
        "arm": arm,
        "mode": mode,
        "status": "in_progress",
        "first_pass": True,
        "stages_completed": [],
        "source_sha256": hashfile(
            out.parents[1] / "sources" / (out.parent.name + ".json")
        ),
    }
    write(out / "receipt.json", rec)
    start = time.perf_counter()
    try:
        content, tree, messages = None, None, None
        for phase in ("one_shot",) if arm == "L1" else PHASES:
            owner = CONDITIONS.CONDITIONS[arm].get(phase, "one_shot")
            if phase == "one_shot" or owner.startswith("model_"):
                prompt = model.build_messages(phase, source, content=content, tree=tree)
                raw = (request(client, prompt, out, phase) if model_call is None
                       else model_call(phase, prompt))
                product = model.parse_output(
                    phase, raw, source, content=content, tree=tree
                )
            elif phase == "structure":
                product = program.program_route(content)
            elif phase == "geometry":
                product = program.program_geometry(tree, content)
            elif phase == "theme":
                product = program.program_theme(tree, content)
            else:
                product = program.program_emit(tree, content, context_for(source))
            if phase != "one_shot" and not owner.startswith("model_"):
                wire = (
                    "\n".join(signature(m) for m in product)
                    if phase == "emit"
                    else signature(product)
                )
                product = model.parse_output(
                    phase, wire, source, content=content, tree=tree
                )
            if phase == "content":
                content = product
            elif phase in ("one_shot", "emit"):
                messages = product
            else:
                tree = product
            write(out / (phase + ".json"), product)
            rec["stages_completed"].append(phase)
        phase = "independent_output_check"
        (out / "card.a2ui.jsonl").write_text(
            "\n".join(json.dumps(m, ensure_ascii=False) for m in messages) + "\n",
            encoding="utf8",
        )
        details = inspect_card(messages, source)
        write(out / "checks.json", details)
        rec["status"] = (
            "artifact_checks_rejected" if details["errors"] else "artifact_checks_pass"
        )
        rec["issues"] = details["errors"]
    except ServiceFailure as exc:
        rec.update(status="transport_failed", first_error=f"{phase}: {exc}")
        raise
    except (
        ValueError,
        KeyError,
        IndexError,
        TypeError,
        RuntimeError,
        AttributeError,
        RecursionError,
    ) as exc:
        rec.update(
            status="stage_rejected",
            first_error=f"{phase}: {type(exc).__name__}: {str(exc)[:400]}",
        )
    finally:
        rec["duration_ms"] = round((time.perf_counter() - start) * 1000, 3)
        write(out / "receipt.json", rec)
    return rec
