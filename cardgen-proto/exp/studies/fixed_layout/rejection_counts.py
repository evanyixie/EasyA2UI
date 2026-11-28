"""只读复算共同投影的首次拒绝原因。公开结果按题计数，两个方法共用一次投影。"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from evidence import (
    ARMS,
    atomic,
    digest,
    protect_seal,
    require,
    safe_name,
    sha,
    verified,
)

# 原分类表仅允许这些输入合同的静态字段名进入汇总。
STATIC_FIELDS = frozenset(
    """
path take unit role entity name count bindings sample_value content handlers caption owners id
label interaction from to type kind quote parent
""".split()
)
UNCLASSIFIED = "无法进一步归因"
DIAGNOSTIC_EXCEPTIONS = (
    ValueError,
    TypeError,
    IndexError,
    KeyError,
    AttributeError,
    ArithmeticError,
    RecursionError,
)


def category(exc, frame):
    """按旧封存复核的首错与 document 当时的局部语义关系分类。"""
    message = str(exc)
    if message == "原表达式跨实体或跨角色":
        owners = frame.get("owners", [])
        if not owners:
            return "选定表达式无法按既定 take 规则关联到语义单元"
        entities = len({unit["entity"] for _, unit in owners})
        roles = len({unit["role"] for _, unit in owners})
        if entities > 1 and roles > 1:
            return "一条不可拆的选定表达式同时跨实体及角色"
        return (
            "一条不可拆的选定表达式跨实体"
            if entities > 1
            else "一条不可拆的选定表达式跨角色"
        )
    if message == "独立入口缺标题或拥有多个实体":
        action = frame["a"]
        if not action["caption"] and len(action["owners"]) > 1:
            return "独立入口同时缺标题并含多个绑定实体"
        return "独立入口缺标题" if not action["caption"] else "独立入口含多个绑定实体"
    if message == "辅助文本有多个相同归属":
        return "同一辅助文字有多个可匹配的值或语义单位"
    if message == "不支持原始表达式":
        return {
            str: "冻结词法解释器未覆盖该字符串表达式",
            dict: "冻结词法解释器未覆盖该对象表达式",
        }.get(type(frame["exp"]), "冻结词法解释器未覆盖该输入类型")
    if message == "未归属的首部文字超过一个":
        return "现有投影将多段文字归为首部，而冻结表示只容许一个独立标题"
    if isinstance(exc, KeyError):
        key = exc.args[0] if exc.args else None
        if isinstance(key, str) and key in STATIC_FIELDS:
            # 源码行号随发布时的导入与格式变化，字段类别沿用原表。
            return f"适配器取既定字段 {key} 时缺键"
        return "适配器取动态键或未覆盖字段时缺键"
    return UNCLASSIFIED


def reproduce(document, row, receipt):
    try:
        document(row)
    except DIAGNOSTIC_EXCEPTIONS as exc:
        require(
            type(exc).__name__ == receipt["error_type"]
            and str(exc) == receipt["detail"],
            "当前首次拒绝的类型或明细与原回执不符",
        )
        tb = exc.__traceback__
        while tb is not None:
            if tb.tb_frame.f_code is document.__code__:
                return category(exc, tb.tb_frame.f_locals)
            tb = tb.tb_next
        raise ValueError("未能定位共同适配器的拒绝位置") from None
    raise ValueError("原先拒绝的输入被接受")


def summarize(batch, inputs):
    from shared_adapter import document

    seal_bytes = (batch / "seal.json").read_bytes()
    seal = json.loads(seal_bytes)
    lock = json.loads(verified(batch / "freeze.json", seal["freeze_sha256"]))
    expected_arms = {"A": ARMS[0], "B": ARMS[1]}
    require(lock["arms"] == expected_arms, "封存条件不符")
    adapter_sha = sha(Path(document.__code__.co_filename))
    pinned = lock.get("dependencies", {}).get("fixed_layout/shared_adapter.py")
    if pinned is not None:
        require(adapter_sha == pinned, "公开批次的共同适配器实现与冻结摘要不符")
    queue = lock["queue"]
    queued = {safe_name(case["task_id"]): case["input_line_sha256"] for case in queue}
    require(0 < len(queued) == len(queue) == lock["denominator"], "冻结题单分母不符")
    raw = verified(inputs, lock["input_sha256"])
    arm_hashes = seal["arm_receipt_sha256"]
    expected_paths = {
        f"results/{task}/{arm}/receipt.json" for task in queued for arm in ARMS
    }
    require(
        set(arm_hashes) == expected_paths
        and len(expected_paths) == seal["receipts_count"],
        "两臂封存回执清单与题单不符",
    )
    present = {
        p.relative_to(batch).as_posix()
        for p in (batch / "results").glob("*/*/receipt.json")
    }
    require(present == expected_paths, "发现未封存或缺失的首试回执")
    counts, statuses = Counter(), Counter()
    seen = set()
    for line in raw.splitlines():
        row = json.loads(line)
        task = safe_name(row["task_id"])
        require(
            task in queued and task not in seen and queued[task] == digest(line),
            "输入行与封存题单不符",
        )
        seen.add(task)
        relative = f"results/{task}/input_receipt.json"
        path = batch / relative
        common_bytes = (
            verified(path, seal["evidence_sha256"][relative])
            if "evidence_sha256" in seal
            else path.read_bytes()
        )
        common = json.loads(common_bytes)
        status = common["status"]
        require(
            common["source_row_sha256"] == queued[task]
            and status in {"accepted", "adapter_rejected", "reference_rejected"},
            "共同准备回执不符",
        )
        for arm in ARMS:
            rel = f"results/{task}/{arm}/receipt.json"
            seat = json.loads(verified(batch / rel, arm_hashes[rel]))
            require(
                seat["task_id"] == task
                and seat["cell"] == arm
                and seat["first_pass"] is True
                and seat["source_row_sha256"] == queued[task],
                "席位与共同来源不符",
            )
            if status == "accepted":
                require(
                    not seat["status"].startswith("common_"), "两臂与共同准备状态不符"
                )
            else:
                require(
                    seat["status"] == "common_" + status
                    and seat["detail"] == common["detail"],
                    "共同拒绝与封存席位的首错不符",
                )
        statuses[status] += 1
        if status == "adapter_rejected":
            counts[reproduce(document, row, common)] += 1
    require(
        seen == set(queued) and sum(counts.values()) == statuses["adapter_rejected"],
        "汇总与冻结分母不守恒",
    )
    return {
        "assigned_inputs": len(seen),
        "sealed_arm_receipts_verified": len(arm_hashes),
        "common_preparation": {
            s: statuses[s]
            for s in ("accepted", "adapter_rejected", "reference_rejected")
        },
        "adapter_rejections_reproduced": sum(counts.values()),
        "unclassified_rejections": counts[UNCLASSIFIED],
        "rejection_counts": dict(sorted(counts.items())),
        "seal_sha256": digest(seal_bytes),
        "classifier_sha256": sha(Path(__file__)),
        "replayed_adapter_sha256": adapter_sha,
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("batch", type=Path, help="有 seal.json 的固定内容首试批次")
    cli.add_argument("inputs", type=Path, help="冻结的逐行业务输入")
    cli.add_argument("--out", type=Path, help="可选的新聚合 JSON 路径，默认打印")
    args = cli.parse_args()
    try:
        if args.out:
            protect_seal(args.batch, args.out)
        result = summarize(args.batch, args.inputs)
        if args.out:
            atomic(args.out, result, exclusive=True)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, *DIAGNOSTIC_EXCEPTIONS) as exc:
        # 异常消息和业务行可能带有私有字段及题号，终端只报告错误类型。
        print(
            "复算失败，请核对研究依赖、封存文件与输入。错误类型为 "
            + type(exc).__name__,
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
