"""从授权的原始冻结合同和封存首件复算静态合同、参考几何与配对次要指标。"""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import median

import artifact_checks as checks
from evidence import ARMS, atomic, protect_seal, read, require, sealed_seats, sha
from paired_analysis import analyze
from run import sources

ENDPOINTS = ("first_artifact", "delivered_with_strict_reference_geometry")


def classify(arm, endpoint):
    status = arm["generation_status"]
    if status == "artifact_ready":
        require(arm["artifact_sha256"] is not None, "缺产物摘要")
        if endpoint == "first_artifact":
            return "pass"
        return {"verified": "pass", "mismatch": "fail", "unresolved": "missing"}[
            arm["reference_geometry"]["status"]
        ]
    if (
        status.endswith(("_transport_unknown", "_implementation_unknown"))
        or status == "unexecuted_or_unsealed"
    ):
        return "missing"
    if status in {
        "common_adapter_rejected",
        "common_reference_rejected",
        "structure_rejected",
        "geometry_rejected",
        "emit_rejected",
    }:
        return "fail"
    raise ValueError("未登记的判定输入")


def timing(values):
    known = [n for n in values if n is not None]
    return {
        "applicable": len(values),
        "known": len(known),
        "missing": len(values) - len(known),
        "sum_ms": sum(known) if known else None,
        "median_ms": median(known) if known else None,
    }


def audit(root, inputs, order, roster, out):
    protect_seal(root, out)
    cases, queue, families, hashes = sources(inputs, order, roster)
    seats, seal = sealed_seats(root, len(queue))
    lock = read(root / "freeze.json")
    require(
        hashes["input_sha256"] == lock["input_sha256"]
        and hashes["order_sha256"] == lock["order_sha256"]
        and queue == lock["queue"],
        "输入或执行顺序与封存版本不符",
    )
    roster_hash = lock.get("roster_sha256")
    if roster_hash is None:
        roster_hash = next(
            (
                h
                for k, h in lock["dependencies"].items()
                if k.replace("\\", "/").endswith("/roster.jsonl")
            ),
            None,
        )
    require(hashes["roster_sha256"] == roster_hash, "冻结题组映射不符")
    current = checks.runtime.dependencies()
    historical = "mode" not in lock
    if historical:
        original = {
            Path(k.replace("\\", "/")).name: v for k, v in lock["dependencies"].items()
        }
        names = {
            "measure.py": "measure.py",
            "space_allocation.py": "space_allocation.py",
            "data_model.py": "data_model.py",
            "Easy/validate.py": "validate.py",
            "Easy/conditions.py": "conditions.py",
            "regular.ttf": "HarmonyOS_Sans_SC_Regular.ttf",
            "bold.ttf": "HarmonyOS_Sans_SC_Bold.ttf",
        }
        require(
            all(current[k] == original[v] for k, v in names.items()),
            "复算历史首件需使用冻结研究模块、Easy 校验与参考字体",
        )
    else:
        require(
            all(lock["dependencies"].get(k) == v for k, v in current.items()),
            "复算运行依赖漂移",
        )
    out.mkdir(parents=True, exist_ok=False)
    counts = {a: {} for a in ARMS}
    phases = {a: {} for a in ARMS}
    projected_time, reference_time = [], []
    changes = Counter()
    votes = {metric: [] for metric in ENDPOINTS}
    supported = set()
    for assignment in queue:
        tid = assignment["task_id"]
        row, line = cases[tid]
        home = root / "results" / tid
        common, shared = checks.check_pair_input(
            row, line, home, root / "shared_inputs" / (tid + ".json")
        )
        preparation = read(home / "input_receipt.json")
        projected_time.append(preparation.get("adapter_wall_ms"))
        if common["status"] != "adapter_rejected":
            reference_time.append(preparation.get("reference_wall_ms"))
        if common["status"] == "accepted":
            supported.add(tid)
        arms = {}
        for arm in ARMS:
            result = checks.check_slot(row, arm, home, common, shared, True, root)
            arms[arm] = result
            for key, decision in checks.record_summary(result).items():
                counts[arm].setdefault(key, Counter())[decision] += 1
            rec = read(home / arm / "receipt.json")
            for stage in ("structure", "geometry"):
                sr = rec.get(stage)
                if sr:
                    phases[arm].setdefault(stage + "_wall", []).append(sr["wall_ms"])
                    if sr.get("request_dir"):
                        phases[arm].setdefault(stage + "_http", []).append(
                            sr.get("http_ms")
                        )
            if rec.get("geometry") and rec["geometry"]["status"] == "accepted":
                phases[arm].setdefault("emit_wall", []).append(rec.get("emit_wall_ms"))
        times = [datetime.fromisoformat(arms[a]["started_utc"]) for a in ARMS]
        actual = "AB" if times[0] < times[1] else "BA" if times[0] > times[1] else "tie"
        changes[assignment["execute"] + "→" + actual] += 1
        atomic(out / "cases" / (tid + ".json"), {"input": common, "arms": arms})
        for metric in ENDPOINTS:
            a, b = (classify(arms[arm], metric) for arm in ARMS)
            decision = {
                "task_id": tid,
                "A": a,
                "B": b,
                "pre_admission": "admitted" if tid in supported else "shared_blocked",
            }
            if tid not in supported:
                decision["admission_reason"] = "冻结共同准备拒绝"
            if "missing" in (a, b):
                decision["missing_reason"] = "传输或实现状态未知、未执行或无有效判定"
            votes[metric].append(decision)
    stats = {}
    for name, group in (
        ("full", families),
        (
            "common_preparation_accepted",
            [f for f in families if f["task_id"] in supported],
        ),
    ):
        ids = {f["task_id"] for f in group}
        stats[name] = {
            "n": len(group),
            "families": len({f["family_id"] for f in group}),
            "endpoints": {},
        }
        for metric, rows in votes.items():
            chosen = [v for v in rows if v["task_id"] in ids]
            if not chosen:
                stats[name]["endpoints"][metric] = None
                continue
            res = analyze(group, chosen)
            for key in "AB":
                res[key + "_verified_delivery"] = sum(v[key] == "pass" for v in chosen)
                res[key + "_missing"] = sum(v[key] == "missing" for v in chosen)
            res["documented_delivery_rate_difference_B_minus_A"] = (
                res["B_verified_delivery"] - res["A_verified_delivery"]
            ) / len(group)
            stats[name]["endpoints"][metric] = res
    atomic(out / "votes.json", votes)
    report = {
        "seal_sha256": seal,
        "assigned_seats": len(seats),
        "mode": lock.get("mode", "historical_first_run"),
        "technical": counts,
        "execution_order": changes,
        "paired": stats,
        "independent_business_visual_pass": None,
        "timing": {
            "shared_adapter": timing(projected_time),
            "shared_reference": timing(reference_time),
            "arms": {
                arm: {key: timing(values) for key, values in grouped.items()}
                for arm, grouped in phases.items()
            },
            "unit": "ms",
            "scope": "参考机器墙钟与服务往返；离线回放不提供真实服务时延。",
        },
        "audit_code_sha256": {
            p.name: sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))
        },
        "case_file_sha256": {
            p.name: sha(p) for p in sorted((out / "cases").glob("*.json"))
        },
        "votes_sha256": sha(out / "votes.json"),
    }
    atomic(out / "summary.json", report)
    return report


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "input", "order", "roster", "out"):
        cli.add_argument("--" + name, type=Path, required=True)
    args = cli.parse_args()
    summary = audit(args.root, args.input, args.order, args.roster, args.out)
    print(
        json.dumps(
            {
                "assigned_seats": summary["assigned_seats"],
                "seal_sha256": summary["seal_sha256"],
            }
        )
    )
