"""离线汇总固定排版首帧的宿主警告。历史采集需提供 --window-name。"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import evidence as e

# 宿主截短 schemaWarning 时，先读取保留下来的头部，再逐个读取完整对象。
PREFIX = re.compile(
    r'\s*\{\s*"type"\s*:\s*"schemaWarning"\s*,\s*"warningCount"\s*:\s*(0|[1-9]\d*)'
    r'\s*,\s*"warnings"\s*:\s*\[\s*'
)
KNOWN = {
    (
        "Text",
        "Property content contains an invalid expression reference",
    ): "Text.content_invalid_expression_reference",
    (
        "Row",
        "Property styles.alignItems has invalid value 'start' and has been reset to default",
    ): "Row.styles.alignItems_start_reset_to_default",
}


def packet(message):
    """返回消息形式、可信声明数、完整对象和下一对象的残片；未知数量用 None 表示。"""
    if not isinstance(message, str) or not message.startswith("2001:"):
        return "unsupported", None, [], ""
    payload = message.removeprefix("2001:").strip()
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError as exc:
        header = PREFIX.match(payload)
        if not header or (
            exc.pos != len(payload) and not exc.msg.startswith("Unterminated string")
        ):
            return "unreadable", None, [], ""
        declared = int(header[1])
        offset = header.end()
        items = []
        while offset < len(payload):
            try:
                item, offset = json.JSONDecoder().raw_decode(payload, offset)
            except json.JSONDecodeError:
                break
            if not isinstance(item, dict) or len(items) >= declared:
                return "unreadable", None, [], ""
            items.append(item)
            separator = re.match(r"\s*,\s*", payload[offset:])
            if not separator:
                break
            offset += separator.end()
        return "truncated", declared, items, payload[offset:]
    if not isinstance(obj, dict) or obj.get("type") != "schemaWarning":
        return "unsupported", None, [], ""
    declared, items = obj.get("warningCount"), obj.get("warnings")
    if (
        type(declared) is not int
        or not isinstance(items, list)
        or declared != len(items)
        or not all(isinstance(item, dict) for item in items)
    ):
        return "unreadable", None, [], ""
    return "complete", declared, items, ""


def category(item):
    if (
        item.get("code") == "ERROR_CODE_INVALID_VALUE"
        and item.get("itemType") == "component"
    ):
        name, message = item.get("itemName"), item.get("message")
        if isinstance(name, str) and isinstance(message, str):
            return KNOWN.get((name, message), "other")
    return "other"


def terminal_from_log(receipt_path):
    rec_bytes = receipt_path.read_bytes()
    rec = json.loads(rec_bytes)
    log = (receipt_path.parent / "runner.log").read_bytes()
    terms = []
    for line in log.decode("utf8").splitlines():
        if "A2UI_RUN " in line:
            event = json.loads(line.split("A2UI_RUN ", 1)[1])
            if event.get("runId") == rec["run_id"] and event.get("state") in {
                "READY",
                "READY_WITH_WARNINGS",
                "FAILED",
            }:
                terms.append(event)
    e.require(terms == [rec["terminal"]], "未找到与原回执完全一致的唯一同次终态")
    return terms[0], e.digest(rec_bytes) + e.digest(log)


def summarize(rows):
    coverage = e.coverage(rows)
    states, forms, details, unreadable_payloads = Counter(), Counter(), Counter(), 0
    tail_codes, tail_properties = Counter(), Counter()
    by_arm = {arm: Counter() for arm in e.ARMS}
    hashes = []
    known_total = 0
    for row in rows:
        if row["capture_status"] != "captured_first_frame":
            continue
        terminal, fingerprint = terminal_from_log(Path(row["capture_receipt"]))
        hashes.append(fingerprint)
        state = terminal["state"]
        e.require(state in {"READY", "READY_WITH_WARNINGS"}, "有效首帧的宿主终态异常")
        states[state] += 1
        warnings = terminal.get("warnings", [])
        if not isinstance(warnings, list) or (
            state == "READY_WITH_WARNINGS" and not warnings
        ):
            unreadable_payloads += 1
            continue
        for message in warnings:
            form, count, items, tail = packet(message)
            forms[form] += 1
            if count is None:
                unreadable_payloads += 1
                continue
            known_total += count
            for item in items:
                label = category(item)
                details[label] += 1
                by_arm[row["arm"]][label] += 1
            if tail.startswith("{"):
                code = re.match(r'\{\s*"code"\s*:\s*"(ERROR_CODE_INVALID_VALUE)"', tail)
                prop = re.search(
                    r'"message"\s*:\s*"Property (content|styles\.alignItems) ', tail
                )
                tail_codes[code[1] if code else "other_or_unknown"] += 1
                tail_properties[prop[1] if prop else "other_or_unknown"] += 1
    return {
        "assigned_cases": coverage["assigned_cases"],
        "assigned_seats": coverage["assigned_seats"],
        "capture_status_by_arm": {
            arm: v["capture"] for arm, v in coverage["by_arm"].items()
        },
        "verified_terminal_images": dict(states),
        "same_run_log_matches": len(hashes),
        "warning_message_forms": dict(forms),
        "messages_or_lists_with_unknown_count": unreadable_payloads,
        "host_declared_entries_in_readable_headers": known_total,
        "host_declared_entries_on_verified_images": known_total
        if hashes and not unreadable_payloads
        else None,
        "complete_warning_objects": sum(details.values()),
        "declared_entries_without_complete_details": known_total
        - sum(details.values()),
        "complete_details": dict(details),
        "complete_details_by_arm": {arm: dict(v) for arm, v in by_arm.items()},
        "truncated_next_codes": dict(tail_codes),
        "truncated_next_properties": dict(tail_properties),
        "receipt_and_log_hash_set_sha256": e.digest("\n".join(sorted(hashes)).encode()),
    }


def from_archive(root, native, window_name=None):
    seats, seal = e.sealed_seats(root)
    plan = e.read(native / "plan.json")
    selected = set(plan["selected"])
    tasks = {r["task_id"] for r in seats}
    e.require(
        plan["seal_sha256"] == seal
        and selected == e.select_pairs(tasks, len(selected)),
        "取图计划与封存批次不符",
    )
    host = e.read(native / "host.json")
    approved = host.get("window_name") or window_name
    e.require(
        approved and (window_name is None or window_name == approved),
        "缺少已登记的宿主窗口名，或窗口名不符",
    )
    host["window_name"] = approved
    rows = e.supplement_rows(e.snapshot(seats, selected, native, host), native, host)
    return {**summarize(rows), "seal_sha256": seal}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument(
        "--root", required=True, type=Path, help="已封存的固定排版首轮批次目录"
    )
    cli.add_argument(
        "--native-dir",
        required=True,
        type=Path,
        help="包含采样计划、宿主、首图及补采回执的目录",
    )
    cli.add_argument(
        "--window-name", help="旧版 host.json 未保存窗口名时，传入采集时核准的值"
    )
    cli.add_argument("--out", type=Path, help="写入新的无映射汇总文件；默认打印 JSON")
    args = cli.parse_args()
    result = from_archive(args.root, args.native_dir, args.window_name)
    if args.out:
        e.protect_seal(args.root, args.out)
        e.atomic(args.out, result, exclusive=True)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
