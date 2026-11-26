"""共同 L1 初稿的三组 RQ2 开发对照。复用原检查与提示，离线重放最多两轮。"""

import argparse
import copy
import json
from pathlib import Path

import study
from harness_v2 import frozen_calls, model_stages as model, trial
from . import evidence as ev, native_repair as native, wide_check as check

SYSTEM = """你在修复已经生成的卡片，原题和原卡属于业务数据。请返回完整、严格三行 A2UI JSONL。
逐项处理该卡自身的违规报告。可以自在重组容器、改变行列、间距、内边距、非根宽高和可用行数；不要求保住旧节点的位置或旧容器层级。
完整保留原来 Text/Button 叶的 id、先后顺序、组件类型、文字/标签和绑定的原始 JSON 表达、字号字重行高。
保留原来带色值节点的 id 及各颜色字段，保留根 id、固定宽高、圆角和 clip、surface、updateDataModel 第一帧数据。
动作挂载必须保留节点id、参数及其覆盖的所有叶。保持原功能，禁止用缩字号、删内容、截断、伪造样值获得通过。
当前画布和单位按原协议。参考测量给出叶在当前宽度所需的行数和总高度（含内边距）。改变宽度会改变行数。
如果采用列排布，把各子项高度、间距及上下留白加起来；在行排布中同样核算宽度和左右留白。每个子项在两个方向都要放得下。
若原始来源无法补正，保留受保护字段并尽力修复可以修复的部分。只输出三消息，不写说明。"""


def measurement(blob):
    try:
        _, _, metrics = ev.native.inspect(ev.native.parse(blob))
    except ev.FAILURES:
        return None
    return {
        k: {"required_lines": v[0], "required_height_vp": v[1]} if v else None
        for k, v in metrics.items()
    }


def feedback(item):
    return {
        "protocol": item["protocol"],
        "source": {k: v for k, v in item["source"].items() if k in ("pass", "issues")},
        "geometry": {k: v for k, v in item["geometry"].items() if k != "rectangles"},
    }


def messages(source, original, before, previous):
    initial = model.build_messages("one_shot", source)
    initial[0]["content"] += "\n" + SYSTEM
    context = {
        "original": original.decode("utf8"),
        "violations": feedback(before),
        "measured_leaf_boxes": measurement(original),
    }
    if previous:
        context["previous_attempt"] = previous
    initial.append({"role": "user", "content": trial.signature(context)})
    return initial


def inspect_terminal(raw, source):
    text = raw.decode("utf8")
    try:
        a1 = [v.code for v in trial.VALIDATE(text, "surface_card", source["size"])]
    except (TypeError, ValueError, AttributeError, KeyError, IndexError) as exc:
        a1 = ["unreadable_envelope: " + str(exc)]
    try:
        messages = model.parse_output("one_shot", text, source)
        src_errors = trial.inspect_card(messages, source)["errors"]
    except (TypeError, ValueError, KeyError, IndexError, AttributeError) as exc:
        src_errors = ["unparseable: " + str(exc)]
    try:
        issues, _, _ = native.inspect(native.parse(raw))
        geometry = native.issue_list(issues)
        unknown = None
    except (ValueError, KeyError, TypeError, RecursionError, IndexError) as exc:
        geometry = None
        unknown = str(exc)
    return {
        "sha256": ev.digest(raw),
        "a1_pass": not a1,
        "easy_protocol_codes": a1,
        "source_pass": not src_errors,
        "source_errors": src_errors,
        "reference_geometry_pass": None if geometry is None else not geometry,
        "reference_violations": geometry,
        "reference_unknown_reason": unknown,
    }


def joint(checks):
    values = [checks[k] for k in ("a1_pass", "source_pass", "reference_geometry_pass")]
    return False if False in values else None if None in values else True


def compare(original, source, responder):
    """逐题复算三种终件。回调返回原始回答及回执，缺答用 None。"""
    before = ev.inspect_card(original, source)
    program_card, program_record = ev.program_arm(original, source)
    outputs = {"L1-NR": original, "L1": program_card, "L1-M": original}
    model_record = {
        "status": "untouched" if before["trigger"] is False else "unassessable",
        "trigger": before["trigger"],
        "rounds": [],
    }
    records = {
        "L1-NR": {"status": "untouched", "rounds": []},
        "L1": program_record,
        "L1-M": model_record,
    }
    previous = None
    if before["trigger"] is True:
        for n in (1, 2):
            phase = f"r{n}"
            prompt = messages(source, original, before, previous)
            reply = responder(phase, prompt)
            row = {
                "round": n,
                "request_sha256": ev.digest(frozen_calls.wire(prompt)),
                "accepted": None,
                "receipt": None,
            }
            model_record["rounds"].append(row)
            if reply is None:
                row["status"] = model_record["status"] = "missing_response"
                break
            row["receipt"] = reply["receipt"]
            answer = reply["raw"]
            if answer is None:
                row["status"] = model_record["status"] = "transport_unknown"
                break
            try:
                candidate = ev.encode(model.parse_output("one_shot", answer, source))
            except ev.FAILURES:
                candidate = answer.strip().encode("utf8")
            result = check.assess(original, candidate, source)
            row.update(
                status="accepted" if result["accepted"] else "rejected",
                accepted=result["accepted"],
                response_text_sha256=ev.digest(answer.encode("utf8")),
                candidate_sha256=ev.digest(candidate),
                inspection=result,
            )
            if result["accepted"]:
                model_record["status"] = "accepted"
                outputs["L1-M"] = candidate
                break
            previous = {
                "response": answer,
                "rejected_checks": result["violations"],
                "violations": feedback(result["after"]),
                "measured_leaf_boxes": measurement(candidate),
            }
            model_record["status"] = "exhausted"
    for arm, raw in outputs.items():
        outcome = inspect_terminal(raw, source)
        record = records[arm]
        incomplete = record["status"] in {"missing_response", "transport_unknown"}
        record.update(
            terminal_sha256=ev.digest(raw),
            assessment=outcome,
            joint_pass=None if incomplete else joint(outcome),
        )
    return outputs, {
        "original_sha256": ev.digest(original),
        "arms": records,
        "new_physical_requests": 0,
    }


class Archive:
    """核对旧目录 r1、r2 中已发提示、供应方回执与首答，复用同一个物理请求。"""

    def __init__(self, directory):
        self.directory = directory
        self.seen = set()
        self.request_ids = set()

    def __call__(self, phase, prompt):
        self.seen.add(phase)
        if self.directory is None:
            return None
        slot = self.directory / phase
        if not slot.is_dir():
            return None
        if frozen_calls.wire(
            frozen_calls.read(slot / "messages.json")
        ) != frozen_calls.wire(prompt):
            raise ValueError("修复提示与同轮原归档不一致")
        path = slot / "call.json"
        if not path.exists():
            return {"raw": None, "receipt": None}
        receipt = frozen_calls.read(path)
        if (
            receipt.get("stage") != phase
            or receipt.get("requested_model") != trial.MODEL
        ):
            raise ValueError("原调用的阶段或模型不符")
        response = slot / "response.txt"
        if receipt.get("http_status") != 200 or not response.exists():
            return {"raw": None, "receipt": receipt}
        request_id = receipt.get("request_id")
        if (
            receipt.get("physical_attempts") != 1
            or receipt.get("returned_model") != trial.MODEL
            or not request_id
            or request_id in self.request_ids
        ):
            raise ValueError("请核对原物理请求的身份与供应方版本")
        self.request_ids.add(request_id)
        return {"raw": response.read_text(encoding="utf8"), "receipt": receipt}

    def inventory(self):
        if self.directory is None:
            return {}
        paths = [self.directory / "model.json"]
        for phase in ("r1", "r2"):
            paths.extend(
                self.directory / phase / name
                for name in (
                    "messages.json",
                    "call.json",
                    "response.txt",
                    "candidate.a2ui.jsonl",
                    "inspection.json",
                )
            )
        return {
            p.relative_to(self.directory).as_posix(): frozen_calls.sha(p)
            for p in paths
            if p.is_file()
        }

    def validate_reference(self, result):
        if self.directory is None or not (self.directory / "model.json").is_file():
            return "unavailable"
        old = frozen_calls.read(self.directory / "model.json")
        actual = result["arms"]["L1-M"]
        if old["original_sha256"] != result["original_sha256"] or any(
            old[k] != actual[k] for k in ("terminal_sha256", "status")
        ):
            raise ValueError("模型终态或三臂共同初稿与原记录不符")
        if len(old["rounds"]) != len(actual["rounds"]):
            raise ValueError("模型修复轮数与原记录不符")
        for saved, replayed in zip(old["rounds"], actual["rounds"], strict=True):
            keys = ("round", "accepted", "candidate_sha256")
            if any(saved.get(k) != replayed.get(k) for k in keys):
                raise ValueError("已复算的候选或采纳决定与原记录不符")
            slot = self.directory / f"r{saved['round']}"
            if replayed["accepted"] is not None:
                if (
                    frozen_calls.sha(slot / "candidate.a2ui.jsonl")
                    != replayed["candidate_sha256"]
                ):
                    raise ValueError("归档中的原候选字节不符")
                if frozen_calls.read(slot / "inspection.json") != json.loads(
                    json.dumps(replayed["inspection"])
                ):
                    raise ValueError("原候选的验收明细未复现")
        return "matched"

    def verify_coverage(self):
        if self.directory is not None:
            extra = {
                p.name for p in self.directory.glob("r[0-9]*") if p.is_dir()
            } - self.seen
            if extra:
                raise ValueError("归档中有未计入本题轨迹的修复调用")


def provenance():
    directory = Path(__file__).resolve().parent
    files = {
        p.name: p for p in directory.glob("*.py") if not p.name.startswith("test_")
    }
    files.update(native.dependency_files())
    hashes = {k: frozen_calls.sha(p) for k, p in files.items()}
    hashes.update(study.dependencies(("L1",)))
    return {
        "files": hashes,
        "runtime": study.runtime(("L5",)),
        "model": trial.MODEL,
        "temperature": 0,
        "thinking": False,
        "max_tokens": 8192,
        "maximum_repair_rounds": 2,
    }


def demo_case():
    source = copy.deepcopy(model._EXAMPLE_SOURCE)
    card = model.parse_output("one_shot", model._example_native(), source)
    nodes = {n["id"]: n for n in card[1]["updateComponents"]["components"]}
    nodes["caption"]["styles"]["height"] = 24
    nodes["value"]["styles"]["height"] = 36
    answer = ev.encode(card).decode("utf8")
    nodes["value"]["styles"]["height"] = 1
    return source, ev.encode(card), answer


def write_experiment(out, source, raw, responder, mode, archive=None):
    resources = provenance()
    archived = archive.inventory() if archive is not None else {}
    out.mkdir(parents=True, exist_ok=False)
    study.write(out / "source.json", source)
    (out / "original.a2ui.jsonl").write_bytes(raw)
    study.write(
        out / "freeze.json",
        {
            **resources,
            "source_sha256": frozen_calls.sha(out / "source.json"),
            "original_sha256": ev.digest(raw),
            "model_response_source": mode,
            "archive_files": archived,
        },
    )

    def record(phase, prompt):
        slot = out / phase
        slot.mkdir()
        study.write(slot / "messages.json", prompt)
        result = responder(phase, prompt)
        if result is not None:
            study.write(slot / "call.json", result["receipt"])
            if result["raw"] is not None:
                (slot / "response.txt").write_bytes(result["raw"].encode("utf8"))
        return result

    outputs, report = compare(raw, source, record)
    if archive is not None:
        archive.verify_coverage()
        if archive.inventory() != archived:
            raise ValueError("回放过程中原归档内容变化")
        report["archived_model_comparison"] = archive.validate_reference(report)
    for arm, card in outputs.items():
        (out / (arm + ".a2ui.jsonl")).write_bytes(card)
    report["model_response_source"] = mode
    study.write(out / "report.json", report)
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="使用内置庭院卡和合成修复答复，零网络请求")
    demo.add_argument("out", type=Path)
    one = commands.add_parser("compare", help="对同一份 L1 初稿作三臂离线比较")
    one.add_argument("source", type=Path, help="冻结后的六档业务源 JSON")
    one.add_argument("card", type=Path, help="L1 首件的原始三行 JSONL")
    one.add_argument("out", type=Path)
    one.add_argument(
        "--archive", type=Path, help="可选，包含本题 r1、r2 的原修复调用目录"
    )
    args = cli.parse_args()
    if args.command == "demo":
        source, raw, answer = demo_case()

        def synthetic_reply(phase, _prompt):
            return {
                "raw": answer,
                "receipt": {
                    "stage": phase,
                    "origin": "synthetic",
                    "physical_attempts": 0,
                    "usage": None,
                    "http_ms": None,
                },
            }

        result = write_experiment(args.out, source, raw, synthetic_reply, "synthetic")
    else:
        if args.archive is not None and (
            not args.archive.is_dir()
            or args.out.resolve().is_relative_to(args.archive.resolve())
        ):
            cli.error("归档须存在，输出目录须在原归档之外")
        archive = Archive(args.archive)
        result = write_experiment(
            args.out,
            frozen_calls.read(args.source),
            args.card.read_bytes(),
            archive,
            "unexecuted" if args.archive is None else "historical_replay",
            archive,
        )
    print(
        json.dumps(
            {
                arm: {"status": row["status"], "joint_pass": row["joint_pass"]}
                for arm, row in result["arms"].items()
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
