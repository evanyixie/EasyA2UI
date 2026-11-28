"""从封存首试回执汇总本机耗时和服务端用量。只输出聚合。"""

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ARMS = ("model_model", "program_program")
STAGES = ("structure", "geometry")
TOKEN_FIELDS = (
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "prompt_cache_hit_tokens",
    "prompt_cache_miss_tokens",
)


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def quantile(values, probability):
    ordered = sorted(values)
    rank = probability * (len(ordered) - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (rank - lo)


def describe(values, eligible=None):
    values = list(values)
    eligible = len(values) if eligible is None else eligible
    known = [v for v in values if v is not None]
    check(
        len(values) <= eligible and all(math.isfinite(v) and v >= 0 for v in known),
        "耗时或分母无效",
    )
    return {
        "denominator": eligible,
        "not_executed": eligible - len(values),
        "executed": len(values),
        "missing": len(values) - len(known),
        "known": len(known),
        "p50_ms": round(quantile(known, 0.5), 3) if known else None,
        "p95_ms": round(quantile(known, 0.95), 3) if known else None,
        "sum_known_ms": round(sum(known), 3) if known else None,
    }


def arm_interval(r, mode="historical_live"):
    if any(r[p] and r[p].get("replayed_from_persisted_call") for p in STAGES):
        return None
    if not r.get("started_utc") or not r.get("ended_utc"):
        return None
    start, end = (datetime.fromisoformat(r[k]) for k in ("started_utc", "ended_utc"))
    if mode != "historical_live" and any(
        r[p]
        and r[p].get("started_utc")
        and datetime.fromisoformat(r[p]["started_utc"]) < start
        for p in STAGES
    ):
        # 恢复后的席位起点可能晚于已保存阶段的起点，整段区间无法从该席位的两个读数重建。
        return None
    return (end - start).total_seconds() * 1000 if end >= start else None


def model_calls(records):
    return [call for r in records for call in r["call_records"]]


def usage(calls):
    counts = {}
    for field in TOKEN_FIELDS:
        known = [
            value
            for c in calls
            if c.get("usage") is not None
            and type(value := c["usage"].get(field)) is int
        ]
        counts[field] = {
            "observed_calls": len(known),
            "missing_calls": len(calls) - len(known),
            "known_sum": sum(known) if known or not calls else None,
        }
    return counts


def http_group(calls):
    counts = Counter(
        "无HTTP状态" if c["http_status"] is None else str(c["http_status"])
        for c in calls
    )
    return {
        "call_records": len(calls),
        "physical_attempts_known": sum(
            c["physical_attempts"]
            for c in calls
            if c.get("physical_attempts") is not None
        ),
        "physical_attempt_count_missing": sum(
            c.get("physical_attempts") is None for c in calls
        ),
        "http_status_counts": counts,
        "client_request_ms": describe(c["http_ms"] for c in calls),
        "tokens": usage(calls),
    }


def arm_summary(records, owner, mode):
    number = len(records)
    result = {
        "cases": number,
        "raw_artifact_count": sum(r["status"] == "artifact_ready" for r in records),
        "terminal_status_counts": Counter(r["status"] for r in records),
        "arm_host_interval_ms": describe(arm_interval(r, mode) for r in records),
        "stage_wall_ms": {
            phase: describe((r[phase]["wall_ms"] for r in records if r[phase]), number)
            for phase in STAGES
        },
    }
    result["stage_wall_ms"]["emit"] = describe(
        (
            r["emit_wall_ms"]
            for r in records
            if r["geometry"] and r["geometry"]["status"] == "accepted"
        ),
        number,
    )
    # 两阶段均实际执行且都有读数才纳入相加；不将未到达几何的题记为0。
    both_stages = [r for r in records if all(r[p] for p in STAGES)]
    result["structure_plus_geometry_wall_ms"] = describe(
        (
            sum(r[p]["wall_ms"] for p in STAGES)
            if all(r[p]["wall_ms"] is not None for p in STAGES)
            else None
            for r in both_stages
        ),
        number,
    )
    if owner == "model_model":
        calls = model_calls(records)
        if mode == "offline_replay":
            result["http"] = None
            result["offline_stage_records"] = len(calls)
            result["physical_model_requests"] = 0
            return result
        result["http"] = {
            "all_calls": http_group(calls),
            "by_stage": {
                p: http_group([c for c in calls if c["stage"] == p]) for p in STAGES
            },
            "sum_of_attempted_calls_per_case_ms": describe(
                (
                    sum(c["http_ms"] for c in r["call_records"])
                    if all(c["http_ms"] is not None for c in r["call_records"])
                    else None
                    for r in records
                    if r["call_records"]
                ),
                number,
            ),
        }
    else:
        check(not model_calls(records), "程序侧出现模型调用")
        result["model_calls"] = 0
        result["model_tokens"] = 0
    return result


def take_sources(root):
    seal = read(root / "seal.json")
    check(sha(root / "freeze.json") == seal["freeze_sha256"], "批次冻结摘要不符")
    lock = read(root / "freeze.json")
    mode = lock.get("mode", "historical_live")
    check(mode in {"historical_live", "live", "offline_replay"}, "无法解释本批执行模式")
    queue = lock["queue"]
    task_ids = [q["task_id"] for q in queue]
    check(
        all(
            isinstance(t, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", t)
            for t in task_ids
        )
        and len(set(task_ids)) == len(queue) > 0,
        "队列题号无效或重复",
    )
    expected = {
        f"results/{task}/{arm}/receipt.json" for task in task_ids for arm in ARMS
    }
    check(
        seal["receipts_count"] == 2 * len(queue)
        and set(seal["arm_receipt_sha256"]) == expected
        and lock["arms"] == dict(zip("AB", ARMS, strict=True)),
        "席位分母或归属不符",
    )
    evidence = seal.get("evidence_sha256")
    if mode == "historical_live":
        hashes = [
            v
            for k, v in lock["dependencies"].items()
            if k.replace(chr(92), "/").split("/")[-1] == "execute.py"
        ]
        check(hashes == [sha(root / "execute.py")], "原计时实现摘要不符")
    else:
        check(
            isinstance(evidence, dict)
            and lock["dependencies"]["fixed_layout/run.py"]
            == sha(Path(__file__).with_name("run.py")),
            "公开版执行器或封存索引不符",
        )

    def verified_file(path):
        h = sha(path)
        if evidence is not None:
            check(
                evidence.get(path.relative_to(root).as_posix()) == h, "计时证据摘要不符"
            )
        return h

    cases, input_receipts, referenced_calls = [], [], set()
    extras = hashlib.sha256()
    for q in queue:
        case = root / "results" / q["task_id"]
        input_file = case / "input_receipt.json"
        src = read(input_file)
        extras.update(bytes.fromhex(verified_file(input_file)))
        check(src["source_row_sha256"] == q["input_line_sha256"], "来源不符")
        input_receipts.append(src)
        pair = {}
        for arm in ARMS:
            p = case / arm / "receipt.json"
            check(
                sha(p) == seal["arm_receipt_sha256"][p.relative_to(root).as_posix()],
                "席位摘要不符",
            )
            r = read(p)
            check(
                r["task_id"] == q["task_id"] and r["cell"] == arm and r["first_pass"],
                "席位归属不符",
            )
            check(
                r["shared_sha256"] == src.get("shared_sha256")
                and r["reference_sha256"] == src.get("reference_sha256")
                and r["source_row_sha256"] == src["source_row_sha256"],
                "同源校验失败",
            )
            r["call_records"] = []
            for stage in STAGES:
                item = r[stage]
                if not item or not item.get("request_dir"):
                    continue
                call_dir = p.parent / "calls" / stage
                path_parts = item["request_dir"].replace(chr(92), "/").split("/")
                if mode == "historical_live":
                    check(
                        path_parts[-5:]
                        == ["results", q["task_id"], arm, "calls", stage],
                        "原调用归属不符",
                    )
                else:
                    check(path_parts == ["calls", stage], "调用位置与回执不符")
                call_file = call_dir / "call.json"
                check(call_file not in referenced_calls, "同一真实请求被重复引用")
                referenced_calls.add(call_file)
                extras.update(bytes.fromhex(verified_file(call_file)))
                call = read(call_file)
                check(
                    call["stage"] == stage
                    and all(
                        call[k] == item[k]
                        for k in ("prompt_sha256", "http_status", "http_ms")
                    ),
                    "阶段内HTTP记录不符",
                )
                if mode == "offline_replay":
                    check(
                        call.get("source") == "offline_fixture_or_replay"
                        and call["physical_attempts"] == 0
                        and call["http_status"] is None
                        and call["http_ms"] is None
                        and call.get("usage") is None,
                        "离线回放回执带有真实请求或用量",
                    )
                elif call["http_status"] == 200:
                    body = call_dir / "response.body"
                    if body.is_file():
                        check(
                            verified_file(body)
                            == (
                                call.get("envelope_sha256")
                                or call.get("expected_body_sha256")
                            ),
                            "原始服务信封摘要不符",
                        )
                        if (
                            mode == "historical_live"
                            or call.get("state") == "response_recorded"
                            or call.get("usage") is not None
                        ):
                            check(
                                read(body).get("usage") == call.get("usage"),
                                "服务用量与原始信封不符",
                            )
                    else:
                        check(
                            mode == "live"
                            and not call.get("envelope_sha256")
                            and call.get("usage") is None
                            and item["status"] == "transport_unknown",
                            "收到200但缺原始信封证据",
                        )
                r["call_records"].append(call)
            pair[arm] = r
        if src["status"] == "accepted":
            cases.append(pair)
        else:
            check(
                all(not r["call_records"] for r in pair.values()),
                "共同准备失败的席位出现调用",
            )
    check(
        referenced_calls == set((root / "results").glob("*/*/calls/*/call.json")),
        "存在游离调用",
    )
    return cases, input_receipts, seal, extras.hexdigest(), mode


def build(root):
    admitted, inputs, seal, source_digest, mode = take_sources(root)
    paired = [
        p for p in admitted if all(p[arm]["status"] == "artifact_ready" for arm in ARMS)
    ]
    cohorts = {
        "common_admitted_all_attempts": {
            a: arm_summary([p[a] for p in admitted], a, mode) for a in ARMS
        },
        "own_raw_artifacts": {
            a: arm_summary(
                [p[a] for p in admitted if p[a]["status"] == "artifact_ready"], a, mode
            )
            for a in ARMS
        },
        "paired_raw_artifacts": {
            a: arm_summary([p[a] for p in paired], a, mode) for a in ARMS
        },
    }
    shared = {}
    for group, rows in (
        ("all", inputs),
        ("admitted", [r for r in inputs if r["status"] == "accepted"]),
        ("common_rejected", [r for r in inputs if r["status"] != "accepted"]),
    ):
        shared[group] = {
            "cases": len(rows),
            "adapter_ms": describe(r.get("adapter_wall_ms") for r in rows),
            "reference_table_ms": describe(
                (
                    r.get("reference_wall_ms")
                    for r in rows
                    if r["status"] != "adapter_rejected"
                ),
                len(rows),
            ),
        }
    return {
        "study": "固定内容首试的本机耗时及资源汇总",
        "mode": mode,
        "units": "毫秒，token 为官网 usage 字段",
        "denominators": {
            "all": len(inputs),
            "shared_admitted": len(admitted),
            "both_raw_artifacts": len(paired),
            "all_arm_slots": seal["receipts_count"],
        },
        "source": {
            "freeze_sha256": seal["freeze_sha256"],
            "seal_sha256": sha(root / "seal.json"),
            "summarizer_sha256": sha(Path(__file__)),
            "prep_and_call_receipt_digests_in_queue_order_sha256": source_digest,
        },
        "definitions": {
            "arm_host_interval_ms": (
                "同一席位直接记录的 UTC 开始、结束两次读数之差。始于共同投影及参考表准备完毕，"
                "止于写最终席位回执之前，成功时已校验、写卡及写匿名副本。含阶段间文件操作、"
                "本机程序执行或真实 HTTP。该计时不含上游选择、处理队列、服务退避、共同准备、"
                "真机部署/首帧、人审；不能视为用户端到端延迟或端侧性能。"
            ),
            "resumed": "公开版中重用旧调用、或已有阶段始于本次席位开始前，席位总区间留空。",
            "stage_wall_ms": (
                "结构及几何使用 perf_counter 包含各自决策与校验。模型侧包含提示准备、真实 HTTP、"
                "响应解析与请求记录写盘；不含最终阶段产物及阶段回执写盘。程序侧调用同一个冻结程序。"
                "共同发射包含发射、协议校验、写卡与匿名副本。"
            ),
            "structure_plus_geometry_wall_ms": "同题两阶段均有计时才相加，发射及阶段间落盘另计。",
            "http": (
                "自客户端 POST 至响应返回或抛错的 perf_counter 墙钟。"
                "HTTP 已包含在结构/几何及席位时间中，不能再相加。"
                "分别统计单次调用和单题多次调用的耗时。"
            ),
            "offline_replay": "回放模式只汇总本机回放墙钟，http 为 null；回放阶段条数和本次实际模型请求数分开统计。",
            "shared": "输入适配、参考宽度表分别计时，每题共同执行一次，未把两臂重复计费/计时。",
            "cohorts": (
                "all_attempts 含共同准入后的全部尝试，失败可在早期退出。"
                "own_raw_artifacts 只按本臂生成首件，样本不同。"
                "paired_raw_artifacts 是双方均生成首件的同题配对。"
                "首件表示协议产物生成，不代表独立验收。各组嵌套，不应累加。"
            ),
            "quantiles": "对已知值排序，采用位置 (n−1)p 的线性插值。未知与未执行分别计数。",
            "usage": "仅已报告 token 可汇总。未回用量的请求及各字段缺项分别计数，不按零估算。",
            "unavailable": (
                "没有可归于本批的官方结算金额、实际CPU/GPU占用或内存峰值、服务端推理耗时、"
                "用户端到端延迟及设备首帧生产性能。"
            ),
            "sources": (
                "席位时间与阶段回执由全量 seal 逐份绑定。独立回读准备和调用台账，检查与席位"
                "的来源、阶段、HTTP时间一致性；对200响应从原始信封复核 usage。"
            ),
        },
        "common_preparation": shared,
        "cohorts": cohorts,
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument(
        "--root", required=True, type=Path, help="已封存的固定内容首试目录"
    )
    cli.add_argument("--out", required=True, type=Path, help="新的匿名汇总 JSON 文件")
    args = cli.parse_args()
    root, target = args.root.resolve(), args.out.resolve()
    check(not target.is_relative_to(root), "请将汇总写到封存目录外")
    check(not target.exists(), "汇总文件已存在")
    result = build(root)
    data = (
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as output:
        output.write(data)
    print("首试耗时和用量聚合复核完成")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError):
        sys.exit("未写入汇总。请核对封存清单、回执、运行版本和新的输出路径。")
