"""RQ2 开发 L1 的共同检查与确定性回放。修复器不接收来源、金标或其他档的内容计划。"""

from __future__ import annotations

import hashlib
import json

from harness_v2 import model_stages as model
from harness_v2 import trial

from . import native_repair as native

FAILURES = (
    ValueError,
    TypeError,
    KeyError,
    IndexError,
    RecursionError,
    UnicodeError,
    AttributeError,
)
UNMEASURED = [
    "必显人工判断、业务事实完整性与文字准确性",
    "原生可见字形、遮挡及参考字体与端侧的偏差",
    "独立 UX 与交互目的地、下一帧真实更新、端侧性能",
]
FIELDS = (
    "structure_reading_order",
    "visible_text",
    "visible_bindings",
    "actions_with_owners",
    "action_bindings",
    "theme",
    "typography",
    "canvas",
    "first_frame",
    "immutable_native_fields",
)


def signature(obj):
    return json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=native.unique)


def encode(messages):
    return (
        "\n".join(json.dumps(m, ensure_ascii=False, allow_nan=False) for m in messages)
        + "\n"
    ).encode("utf8")


def bindings(value):
    paths = []

    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("path"), str):
                paths.append(x["path"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            paths.extend(trial.BOUND.findall(x))

    walk(value)
    return paths


def dimensions(msgs):
    packet = msgs[1]["updateComponents"]
    root = native.fidelity.graph(packet)
    readings, visible, bounds, actions, action_paths, theme, font = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )

    def visit(n):
        key = n["id"]
        node = n["component"]
        style = n["styles"]
        readings.append((key, node["component"], [c["id"] for c in n["children"]]))
        for k in ("content", "text", "label", "src", "value", "progress"):
            if k in node:
                visible.append((key, k, node[k]))
                bounds.append((key, k, bindings(node[k])))
        if "onClick" in node:
            actions.append((key, node["onClick"]))
            action_paths.append((key, bindings(node["onClick"])))
        theme.append((key, {k: style[k] for k in style if k in native.fidelity.THEME}))
        font.append(
            (
                key,
                {
                    k: style[k]
                    for k in ("fontSize", "fontWeight", "lineHeight")
                    if k in style
                },
            )
        )
        for c in n["children"]:
            visit(c)

    visit(root)
    return dict(
        zip(
            FIELDS,
            (
                readings,
                visible,
                bounds,
                actions,
                action_paths,
                theme,
                font,
                [root["id"], root["styles"]["width"], root["styles"]["height"]],
                msgs[2]["updateDataModel"],
                native.material(msgs),
            ),
            strict=True,
        )
    )


def action_source(msgs, source):
    frame = trial.outgoing_data(msgs[2])
    allowed = {
        trial.signature(a["handler"])
        for a in source["candidate_actions"]
        if a.get("handler")
    }
    records = []
    for n in msgs[1]["updateComponents"]["components"]:
        for handler in n.get("onClick", []):
            registered = trial.signature(handler) in allowed
            for path in bindings(handler):
                row = {
                    "owner": n["id"],
                    "path": path,
                    "exact_handler_allowed": registered,
                }
                try:
                    wanted = trial.lookup_wrapped(source["sample_data"], path)
                except (IndexError, KeyError, ValueError, TypeError):
                    row["state"] = "caller_sample_unknown"
                else:
                    try:
                        v = trial.lookup_wrapped(frame, path)
                    except (IndexError, KeyError, ValueError, TypeError):
                        row["state"] = "missing_in_artifact"
                    else:
                        row["state"] = (
                            "matched"
                            if signature(v) == signature(wanted)
                            else "changed"
                        )
                records.append(row)
    return records


def inspect_card(raw: bytes, source: dict) -> dict:
    """真实冻结来源与参考几何各自给出三值判定，trigger 给出是否有已知触发依据。"""
    rec = {
        "sha256": digest(raw),
        "protocol": {"pass": None, "issues": []},
        "source": {"pass": None, "issues": []},
        "geometry": {"pass": None, "issues": None},
        "trigger": None,
    }
    try:
        msgs = model.parse_output("one_shot", raw.decode("utf8"), source)
        errors = [
            str(e)
            for e in trial.VALIDATE(
                "\n".join(trial.signature(m) for m in msgs),
                "surface_card",
                source["size"],
            )
        ]
        rec["protocol"] = {"pass": not errors, "issues": errors}
    except FAILURES as exc:
        rec["protocol"] = {"pass": False, "issues": [str(exc)]}
        rec["trigger"] = True
        return rec
    try:
        checks = trial.inspect_card(msgs, source)
        other = [e for e in checks["errors"] if e not in errors]
        rec["source"] = {
            "pass": not other,
            "issues": other,
            "bound_paths": checks["bound_paths"],
            "action_handlers": checks.get("action_handlers"),
            "action_parameter_samples": action_source(msgs, source),
        }
    except FAILURES as exc:
        rec["source"]["issues"] = [str(exc)]
    try:
        issues, rects, _ = native.inspect(native.parse(raw))
        rec["geometry"] = {
            "pass": not issues,
            "issues": native.issue_list(issues),
            "rectangles": rects,
        }
    except FAILURES as exc:
        rec["geometry"]["reason"] = str(exc)
    gates = [rec[k]["pass"] for k in ("protocol", "source", "geometry")]
    rec["trigger"] = True if False in gates else None if None in gates else False
    return rec


def compare_candidate(original: bytes, candidate: bytes, source: dict) -> dict:
    """在同一份原件上比较两份三消息；结构、颜色及文字绑定均按原声明核对。"""
    before, after = [inspect_card(raw, source) for raw in (original, candidate)]
    preserved = dict.fromkeys(FIELDS, None)
    why = None
    geometry_limits = None
    try:
        parsed = [
            [
                json.loads(line, object_pairs_hook=native.unique)
                for line in raw.splitlines()
            ]
            for raw in (original, candidate)
        ]
        old, new = [dimensions(m) for m in parsed]
        preserved = {k: signature(old[k]) == signature(new[k]) for k in FIELDS}
        nodes = [
            {n["id"]: n for n in m[1]["updateComponents"]["components"]} for m in parsed
        ]
        geometry_limits = []
        for key in nodes[0].keys() & nodes[1].keys():
            a_node, b_node = [index[key] for index in nodes]
            if (
                a_node["component"] in native.SUPPORTED
                and "maxLines" in a_node["styles"]
                and b_node["styles"].get("maxLines", 0) < a_node["styles"]["maxLines"]
            ):
                geometry_limits.append({"id": key, "code": "maxLines_decreased"})
            if a_node["component"] in ("Column", "Row") and b_node.get(
                "itemMargin", 0
            ) < min(2, a_node.get("itemMargin", 0)):
                geometry_limits.append(
                    {"id": key, "code": "itemMargin_below_original_or_2vp"}
                )
        geometry_limits.sort(key=lambda e: (e["id"], e["code"]))
    except FAILURES as exc:
        why = str(exc)
    delta = {"introduced": None, "worsened": None, "shifted_originally_valid": None}
    a, b = before["geometry"], after["geometry"]
    if a["pass"] is not None and b["pass"] is not None:
        indexes = [
            {(e["id"], e["code"]): e["excess"] for e in x["issues"]} for x in (a, b)
        ]
        x, y = indexes
        protected = set(a["rectangles"]) - {node for node, _ in x}
        delta = {
            "introduced": native.issue_list({k: v for k, v in y.items() if k not in x}),
            "worsened": native.issue_list(
                {k: v for k, v in y.items() if k in x and v > x[k] + native.EPS}
            ),
            "shifted_originally_valid": sorted(
                k
                for k in protected
                if k not in b["rectangles"]
                or any(
                    abs(v - w) > native.EPS
                    for v, w in zip(a["rectangles"][k], b["rectangles"][k], strict=True)
                )
            ),
        }
    absolute = after["trigger"] is False
    action_gate = all(
        x["state"] == "matched" and x["exact_handler_allowed"]
        for x in after["source"].get("action_parameter_samples", [])
    )
    return {
        "before": before,
        "after": after,
        "preservation": preserved,
        "preservation_unknown": why,
        "geometry_delta": delta,
        "geometry_limit_violations": geometry_limits,
        "action_parameter_sources_verified": action_gate
        if after["source"]["pass"] is not None
        else None,
        "accepted": absolute
        and all(v is True for v in preserved.values())
        and action_gate
        and delta["shifted_originally_valid"] == []
        and geometry_limits == [],
    }


def replay_changes(original, roundlog):
    msgs = native.parse(original)
    ns = {n["id"]: n for n in msgs[1]["updateComponents"]["components"]}
    for change in roundlog["actions"]:
        n = ns[change["id"]]
        key = change["key"]
        if key == "itemMargin":
            obj = n
        else:
            if key not in {"width", "height", "maxLines"} or n["id"] == msgs[1][
                "updateComponents"
            ].get("root", "root"):
                raise ValueError("修复日志试图修改受保护字段")
            obj = n["styles"]
        if obj[key] != change["old"]:
            raise ValueError("修复日志的初值与输入不符")
        if key == "maxLines" and change["new"] < obj[key]:
            raise ValueError("修复日志试图减少允许行数")
        obj[key] = change["new"]
    return msgs


def program_arm(original: bytes, source: dict) -> tuple[bytes, dict]:
    """最多两次原版确定性候选，按原日志还原每一轮；任何无法复核的已接受候选显式阻断。"""
    first = inspect_card(original, source)
    output, old = native.repair(original)
    rounds = []
    for r in old["rounds"]:
        messages = replay_changes(original, r)
        candidate = encode(messages)
        compared = compare_candidate(original, candidate, source)
        if compared["after"]["geometry"]["issues"] != r["candidate_violations"] or (
            compared["geometry_delta"]["introduced"] != r["introduced_by_repair"]
            or compared["geometry_delta"]["worsened"] != r["worsened"]
            or compared["geometry_delta"]["shifted_originally_valid"]
            != r["moved_previously_valid_boxes"]
        ):
            raise ValueError("冻结几何候选回放不一致")
        if r["accepted"] and not compared["accepted"]:
            raise ValueError("旧修复返回物未通过独立逐轮核验")
        rounds.append(
            {
                "round": r["round"],
                "base": "original",
                "actions": r["actions"],
                "candidate_sha256": digest(candidate),
                "historical_accepted": r["accepted"],
                "source": compared["after"]["source"],
                "protocol": compared["after"]["protocol"],
                "geometry": {
                    k: v
                    for k, v in compared["after"]["geometry"].items()
                    if k != "rectangles"
                },
                **{
                    k: compared[k]
                    for k in (
                        "preservation",
                        "geometry_delta",
                        "geometry_limit_violations",
                        "action_parameter_sources_verified",
                        "accepted",
                    )
                },
            }
        )
    if len(rounds) > 2:
        raise ValueError("超过已登记的两轮上限")
    final = compare_candidate(original, output, source)
    if output != original and (
        not final["accepted"]
        or not any(
            r["historical_accepted"] and r["candidate_sha256"] == digest(output)
            for r in rounds
        )
    ):
        raise ValueError("返回字节不属于已验收候选")
    return output, {
        "status": old["status"],
        "trigger": first["trigger"],
        "before": first,
        "rounds": rounds,
        "output_sha256": digest(output),
        "output_byte_changed": output != original,
        "after": final["after"],
        "final_preservation": final["preservation"],
        "unmeasured": UNMEASURED,
    }
