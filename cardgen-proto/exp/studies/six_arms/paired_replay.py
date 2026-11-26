"""共同入口置换。对 L2 发射、L3 主题、L4 几何分别重建模型请求并单独改用程序。"""

import argparse
import copy
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from time import perf_counter_ns

import emit_fidelity as fidelity
import study
from harness_v2 import model_stages as model
from harness_v2 import program_stages as program
from harness_v2 import trial
from harness_v2.frozen_calls import demand, read
from harness_v2.frozen_calls import sha as file_sha
from study import write


def signature(obj):
    return json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def json_sha(obj):
    return hashlib.sha256(signature(obj).encode()).hexdigest()


def box_checks(tree, content):
    """核对声明的盒子及同一参考字体的行盒；只计能从该几何直接验证的属性。"""
    entries, _ = program._index(content)
    oracle = program._measure()
    errors = []
    nodes = 0

    def visit(node, pos):
        nonlocal nodes
        nodes += 1
        kind, style = node["kind"], node["style"]
        pad = style.get("padding", 0)
        width, height = (style[key] - 2 * pad for key in ("width", "height"))

        def add(rule, detail):
            errors.append(
                {"node": pos, "ref": node.get("ref"), "rule": rule, "detail": detail}
            )

        if kind in ("row", "column"):
            sizes = [n["style"] for n in node["children"]]
            gaps = max(0, len(sizes) - 1) * style.get("itemMargin", 0)
            for axis, available in (("width", width), ("height", height)):
                declared = [s[axis] for s in sizes]
                stacking = (kind == "row") == (axis == "width")
                needed = sum(declared) + gaps if stacking else max(declared)
                if needed > available + 0.05:
                    add(
                        "container_" + axis,
                        {
                            "required_vp": round(needed, 3),
                            "available_vp": round(available, 3),
                        },
                    )
            for index, child in enumerate(node["children"]):
                visit(child, pos + "/" + str(index))
            return
        text = program._leaf_text(node, entries)
        try:
            metrics = oracle.text(
                text,
                width,
                style["fontSize"],
                max_lines=style["maxLines"],
                bold=style.get("fontWeight", 400) >= 600,
                line_height=style.get("lineHeight", 1.35),
            )
        except ValueError as exc:
            add("reference_wrapping", str(exc))
            return
        if metrics.height > height + 0.05:
            add(
                "reference_line_height",
                {
                    "required_vp": metrics.height,
                    "available_vp": round(height, 3),
                    "lines": metrics.lines,
                },
            )

    visit(tree["root"], "root")
    return {"nodes": nodes, "issues": errors, "pass": not errors}


def style_difference(left, right):
    changed = Counter()

    def walk(a, b):
        demand(
            a["kind"] == b["kind"] and a.get("ref") == b.get("ref"),
            "几何改变了种类或引用",
        )
        for key in a["style"].keys() | b["style"].keys():
            if a["style"].get(key) != b["style"].get(key):
                changed[key] += 1
        ach, bch = a.get("children", []), b.get("children", [])
        demand(len(ach) == len(bch), "几何改变了子节点数")
        for ca, cb in zip(ach, bch, strict=True):
            walk(ca, cb)

    walk(left["root"], right["root"])
    return dict(changed)


def common_tail(geometry, content, tree, source, destination):
    geometry = model.parse_output(
        "geometry", signature(geometry), source, content, tree
    )
    paint = program.program_theme(geometry, content)
    paint = model.parse_output("theme", signature(paint), source, content, geometry)
    rows = program.program_emit(paint, content, trial.context_for(source))
    # 原 runner 在程序阶段用 sort_keys 的合同序列化解析，再存实际 A2UI。
    messages = model.parse_output(
        "emit", "\n".join(signature(row) for row in rows), source, content, paint
    )
    artifact = destination / "card.a2ui.jsonl"
    artifact.write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in messages) + "\n",
        encoding="utf8",
    )
    checks = trial.inspect_card(messages, source)
    boxes = box_checks(geometry, content)
    write(destination / "geometry.json", geometry)
    write(destination / "checks.json", checks)
    write(destination / "reference_boxes.json", boxes)
    return {
        "geometry_sha256": json_sha(geometry),
        "theme_sha256": json_sha(paint),
        "emit_sha256": json_sha(messages),
        "card_file_sha256": file_sha(artifact),
        "artifact_pass": not checks["errors"],
        "artifact_issues": checks["errors"],
        "reference_pass": boxes["pass"],
        "reference_issues": boxes["issues"],
    }


def compare_geometry(case, lock, run, out):
    old = run / case / "L4"
    receipt = read(old / "receipt.json")
    row = {
        "case": case,
        "original_L4_status": receipt["status"],
        "common_entry": False,
        "original_receipt_sha256": file_sha(old / "receipt.json"),
    }
    if not {"structure", "content"} <= set(receipt["stages_completed"]):
        row["reason"] = receipt.get("first_error")
        return row
    source_file = run / "sources" / (case + ".json")
    source, content, tree = [
        read(path)
        for path in (source_file, old / "content.json", old / "structure.json")
    ]
    demand(
        file_sha(source_file)
        == lock["source_hashes"][case]
        == receipt["source_sha256"],
        "源输入未对齐",
    )
    prompt = read(old / "geometry/messages.json")
    demand(
        prompt == model.build_messages("geometry", source, content=content, tree=tree),
        "原模型实际请求与重建请求不符",
    )
    enclosed = json.loads(prompt[-1]["content"].removeprefix("本次输入："))
    planned = {"content": content, "tree": tree}
    hashes = [
        {
            "element": key,
            "model_input": json_sha(enclosed[key]),
            "program_input": json_sha(value),
        }
        for key, value in planned.items()
    ]
    demand(
        all(h["model_input"] == h["program_input"] for h in hashes), "共同入口不一致"
    )
    call = read(old / "geometry/call.json")
    row.update(
        common_entry=True,
        input_hashes=hashes,
        original_content_bytes_sha256=file_sha(old / "content.json"),
        original_structure_bytes_sha256=file_sha(old / "structure.json"),
        original_messages_sha256=file_sha(old / "geometry/messages.json"),
        original_geometry_response_sha256=file_sha(old / "geometry/response.txt"),
        model_http_ms=call["http_ms"],
        model_http_receipt_sha256=file_sha(old / "geometry/call.json"),
    )
    for direction in ("recorded_model", "offline_program"):
        dest = out / case / "geometry" / direction
        dest.mkdir(parents=True)
        c, t = copy.deepcopy(content), copy.deepcopy(tree)
        if direction == "recorded_model":
            raw = (old / "geometry/response.txt").read_text(encoding="utf8")
            geometry = model.parse_output("geometry", raw, source, c, t)
            demand(
                json_sha(geometry) == json_sha(read(old / "geometry.json")),
                "原模型几何未复现",
            )
            saved_geom = geometry
        else:
            before = perf_counter_ns()
            try:
                geometry = program.program_geometry(t, c)
            except program.StageError as exc:
                row["program_geometry_ms"] = (perf_counter_ns() - before) / 1e6
                row[direction] = {
                    "stage_error": exc.code,
                    "detail": exc.detail,
                    "artifact_pass": False,
                    "reference_pass": None,
                }
                write(dest / "rejection.json", row[direction])
                continue
            row["program_geometry_ms"] = (perf_counter_ns() - before) / 1e6
            row["style_changes_by_field"] = style_difference(saved_geom, geometry)
        demand(
            json_sha(c) == json_sha(content) and json_sha(t) == json_sha(tree),
            "阶段突变了共同输入",
        )
        outcome = common_tail(geometry, c, t, source, dest)
        if direction == "recorded_model":
            for name, key in (("theme", "theme_sha256"), ("emit", "emit_sha256")):
                demand(
                    outcome[key] == json_sha(read(old / (name + ".json"))),
                    f"原始{name}复现不符",
                )
            demand(
                outcome["card_file_sha256"] == file_sha(old / "card.a2ui.jsonl"),
                "原生产物字节未复现",
            )
            demand(
                read(dest / "checks.json") == read(old / "checks.json"),
                "原出口检查未复现",
            )
            outcome["reproduced_original_bytes"] = True
        row[direction] = outcome
    return row


def compile_shared(paint, content, source):
    native = program.program_emit(paint, content, trial.context_for(source))
    return model.parse_output(
        "emit", "\n".join(trial.signature(m) for m in native), source, content, paint
    )


def compare_tail(case, arm, stage, lock, run, out):
    old = run / case / arm
    source_path = run / "sources" / (case + ".json")
    receipt = read(old / "receipt.json")
    row = {
        "case": case,
        "arm": arm,
        "stage": stage,
        "source_sha256": file_sha(source_path),
        "original_status": receipt["status"],
        "common_entry": False,
    }
    demand(
        row["source_sha256"] == lock["source_hashes"][case] == receipt["source_sha256"],
        "输入不符",
    )
    if not (old / stage / "messages.json").is_file():
        row["upstream_error"] = receipt.get("first_error")
        demand(bool(row["upstream_error"]), "未定位共同入口为何没有到达")
        return row
    row["common_entry"] = True
    source = read(source_path)
    content = read(old / "content.json")
    prior = read(old / ("theme.json" if stage == "emit" else "geometry.json"))
    row["content_hash"] = json_sha(content)
    row["prior_hash"] = json_sha(prior)
    prompt_file = old / stage / "messages.json"
    raw_file = old / stage / "response.txt"
    call_file = old / stage / "call.json"
    demand(
        read(prompt_file) == model.build_messages(stage, source, content, prior),
        "实际请求不同",
    )
    http = read(call_file)
    row.update(
        prompt_sha256=file_sha(prompt_file),
        response_sha256=file_sha(raw_file),
        call_receipt_sha256=file_sha(call_file),
        model_http_ms=http["http_ms"],
        size=source["size"],
    )
    recorded = model.parse_output(
        stage, raw_file.read_text(encoding="utf8"), source, content, prior
    )
    demand(recorded == read(old / (stage + ".json")), "实际响应解析未复现")
    for branch in ("recorded_model", "offline_program"):
        dest = out / case / stage / branch
        dest.mkdir(parents=True)
        if branch == "recorded_model":
            output = recorded
        else:
            tree, selected = copy.deepcopy(prior), copy.deepcopy(content)
            context = trial.context_for(source)
            started = perf_counter_ns()
            native = (
                program.program_emit(tree, selected, context)
                if stage == "emit"
                else program.program_theme(tree, selected)
            )
            row["program_local_ms"] = (perf_counter_ns() - started) / 1e6
            wire = (
                "\n".join(trial.signature(m) for m in native)
                if stage == "emit"
                else trial.signature(native)
            )
            output = model.parse_output(stage, wire, source, content, prior)
            demand(tree == prior and selected == content, "程序修改了共同入口")
        paint = prior if stage == "emit" else output
        rows = output if stage == "emit" else compile_shared(paint, content, source)
        audit = fidelity.audit(content, paint, rows, source)
        checks = trial.inspect_card(rows, source)
        path = dest / "card.a2ui.jsonl"
        path.write_text(
            "\n".join(json.dumps(m, ensure_ascii=False) for m in rows) + "\n",
            encoding="utf8",
        )
        write(dest / "fidelity.json", audit)
        write(dest / "checks.json", checks)
        row[branch] = {
            "card_path": path.relative_to(out).as_posix(),
            "card_sha256": file_sha(path),
            "fidelity": audit["status"],
            "dimensions": audit["dimensions"],
            "pass": not checks["errors"],
            "issues": checks["errors"],
        }
        if stage == "theme":
            write(dest / "theme.json", paint)
        if branch == "recorded_model":
            demand(
                path.read_bytes() == (old / "card.a2ui.jsonl").read_bytes(),
                "旧成品字节不同",
            )
            demand(checks == read(old / "checks.json"), "旧出口核对结果不同")
        elif stage == "theme":
            row["tree_style_changes"] = style_difference(recorded, paint)
            demand(
                set(row["tree_style_changes"]) <= fidelity.THEME,
                "主题同时改了非颜色样式",
            )
    row["same_bytes"] = (
        row["recorded_model"]["card_sha256"] == row["offline_program"]["card_sha256"]
    )
    return row


def run_pairs(batch, out, arms):
    lock, sources = study.verified(batch)
    demand(set(arms) <= set(lock["arms"]), "所选档位不在原冻结队列")
    demand(
        not out.resolve().is_relative_to(batch.resolve()), "置换输出须在冻结批次之外"
    )
    mode_path = batch / "execution.json"
    mode = read(mode_path)["mode"] if mode_path.exists() else None
    out.mkdir(parents=True, exist_ok=False)
    selected = {"L2": "emit", "L3": "theme", "L4": "geometry"}
    measurement = program.measurement_files() if "L4" in arms else {}
    write(
        out / "freeze.json",
        {
            "batch_freeze_sha256": file_sha(batch / "freeze.json"),
            "script_sha256": file_sha(Path(__file__)),
            "arm_stages": {a: selected[a] for a in arms},
            "geometry_dependencies": {k: file_sha(v) for k, v in measurement.items()},
            "runtime": study.runtime(("L5",) if measurement else ()),
            "archive_mode": mode,
            "new_physical_requests": 0,
        },
    )
    rows = []
    for case, arm in lock["queue"]:
        if arm not in arms:
            continue
        stage = selected[arm]
        seat = batch / case / arm
        row = {"case": case, "arm": arm, "stage": stage, "status": "unexecuted"}
        rows.append(row)
        if not (seat / "receipt.json").exists():
            continue
        receipt = read(seat / "receipt.json")
        row["original_status"] = receipt["status"]
        if not (seat / "seal.json").is_file() or read(
            seat / "seal.json"
        ) != study.seat_hashes(seat):
            row["status"] = "unsealed_or_changed_archive"
            continue
        if (
            stage not in receipt["stages_completed"]
            or not (seat / "card.a2ui.jsonl").is_file()
        ):
            row.update(
                status="unavailable_first_artifact", reason=receipt.get("first_error")
            )
            continue
        try:
            source = sources[case]
            content, tree = (
                read(seat / "content.json"),
                read(
                    seat
                    / {
                        "emit": "theme.json",
                        "theme": "geometry.json",
                        "geometry": "structure.json",
                    }[stage]
                ),
            )
            calls = study.frozen_calls.FrozenCalls(
                batch, case, arm, synthetic=mode == "fixture"
            )
            calls(stage, model.build_messages(stage, source, content, tree))
            result = (
                compare_geometry(case, lock, batch, out)
                if arm == "L4"
                else compare_tail(case, arm, stage, lock, batch, out)
            )
            row.update(result, status="compared")
        except (
            ValueError,
            KeyError,
            IndexError,
            TypeError,
            OSError,
            RuntimeError,
        ) as exc:
            row.update(
                status="comparison_failed", reason=f"{type(exc).__name__}: {exc}"
            )
    counts = {
        stage: dict(Counter(row["status"] for row in rows if row["stage"] == stage))
        for stage in (selected[a] for a in arms)
    }
    timing = {}
    for stage in counts:
        complete = [
            row for row in rows if row["stage"] == stage and row["status"] == "compared"
        ]
        program_key = (
            "program_geometry_ms" if stage == "geometry" else "program_local_ms"
        )
        timing[stage] = {}
        for key in ("model_http_ms", program_key):
            observed = [row[key] for row in complete if row.get(key) is not None]
            timing[stage][key] = {
                "observed": len(observed),
                "median": statistics.median(observed) if observed else None,
            }
    result = {
        "counts": counts,
        "timing": timing,
        "rows": rows,
        "new_physical_requests": 0,
        "timing_scope": "原模型 HTTP 回执与程序单次函数墙钟分别计时，合成应答的模型耗时未知。",
    }
    write(out / "comparison.json", result)
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("batch", type=Path)
    cli.add_argument("out", type=Path)
    cli.add_argument(
        "--arms", nargs="+", choices=("L2", "L3", "L4"), default=("L2", "L3", "L4")
    )
    args = cli.parse_args()
    report = run_pairs(args.batch, args.out, args.arms)
    print(json.dumps(report["counts"], ensure_ascii=False))
    raise SystemExit(
        int(
            any(
                row["status"] in {"unsealed_or_changed_archive", "comparison_failed"}
                for row in report["rows"]
            )
        )
    )
