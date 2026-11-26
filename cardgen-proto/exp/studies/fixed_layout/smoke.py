"""完全离线的合成端到端自检。数据、模拟服务响应与空白盲卷只写入新目录。"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from evidence import atomic, digest, read, require, sealed_seats

HERE = Path(__file__).resolve().parent


def source(tid):
    return {
        "task_id": tid,
        "D": 1,
        "A": 0,
        "size": "2x2",
        "entities": [{"id": "item", "name": "Synthetic"}],
        "relations": [],
        "actions": [],
        "content_groups": [
            {
                "id": "reading",
                "count": 1,
                "selected_value_sources": [
                    {
                        "content": "{{ ${/demo/value} }}",
                        "bindings": [{"path": "/demo/value", "sample_value": "27"}],
                    }
                ],
            }
        ],
        "semantic_units": [
            {"parent": "reading", "entity": "item", "role": "primary", "take": "all"}
        ],
        "binding_samples": {"/demo/value": "27"},
        "numeric_semantics": [],
        "supporting_text": [],
        "user_preferences": [],
        "constraints": {
            "content_selection_locked": True,
            "may_delete_content": False,
            "may_add_data_facts": False,
            "may_reassign_actions": False,
        },
    }


def run_cli(script, *args):
    subprocess.run(
        [sys.executable, "-B", str(HERE / script), *map(str, args)],
        check=True,
        env=dict(os.environ, PYTHONUTF8="1"),
    )


def smoke(out):
    import layout_decisions as layout
    import shared_adapter
    from ratings import DIMENSIONS

    out.mkdir(parents=True, exist_ok=False)
    rows = [source("synth-both"), source("synth-missing"), source("synth-blocked")]
    rows[-1]["constraints"]["content_selection_locked"] = False
    order, roster = [], []
    lines = []
    for i, row in enumerate(rows):
        line = json.dumps(row, separators=(",", ":")).encode()
        lines.append(line)
        order.append(
            {
                "n": i + 1,
                "task_id": row["task_id"],
                "execute": "BA" if i % 2 else "AB",
                "input_line_sha256": digest(line),
            }
        )
        roster.append({"task_id": row["task_id"], "family_id": "one" if i == 0 else "two"})
    inputs = out / "inputs.jsonl"
    inputs.write_bytes(b"\n".join(lines) + b"\n")
    for name, data in (("order", order), ("roster", roster)):
        (out / (name + ".jsonl")).write_bytes(
            b"".join((json.dumps(v) + "\n").encode() for v in data)
        )
    case = rows[0]
    shared = shared_adapter.document(case)
    ref = layout.measurements(shared)
    tree = {"root": {"kind": "column", "children": [{"kind": "text", "ref": "reading_1"}]}}
    boxes = {
        "boxes": [
            {"at": "0", "w": 150, "h": 150, "gap": 4},
            {"at": "0.0", "w": 126, "h": 40, "lines": 1},
        ]
    }
    replay = out / "synthetic-envelopes"
    for phase, response in (("structure", tree), ("geometry", boxes)):
        where = replay / case["task_id"] / phase
        atomic(
            where / "messages.json",
            layout.prompt(phase, shared, ref, tree if phase == "geometry" else None),
        )
        atomic(
            where / "response.body",
            {
                "choices": [
                    {"message": {"content": json.dumps(response)}, "finish_reason": "stop"}
                ],
                "model": "synthetic-offline",
            },
        )
    root = out / "batch"
    src = ["--input", inputs, "--order", out / "order.jsonl", "--roster", out / "roster.jsonl"]
    batch_args = [*src, "--replay", replay, "--out", root]
    for mode in ("freeze", "run", "run"):
        run_cli("run.py", mode, *batch_args)
    run_cli("audit.py", *src, "--root", root, "--out", out / "audit")
    proof = read(out / "audit/summary.json")
    endpoint = proof["paired"]["full"]["endpoints"]["first_artifact"]
    require(
        len(sealed_seats(root)[0]) == 6
        and endpoint["A_verified_delivery"] == 1
        and endpoint["B_verified_delivery"] == 2
        and endpoint["A_missing"] == 1
        and endpoint["all_assigned_point_difference"] is None,
        "离线首件或未知状态不符",
    )
    for arm in ("model_model", "program_program"):
        require(
            proof["technical"][arm]["joint_automatic"].get("verified", 0) >= 1,
            "合成首件未通过静态合同、声明和参考几何",
        )
    require(read(root / "status.json")["physical_attempts_known"] == 0, "离线烟测不应发模型请求")
    blind = out / "empty-review"
    run_cli("blind_review.py", "pack", "--root", root, "--out", blind, "--missing-captures")
    book = read(blind / "管理/book.json")
    exports = []
    for i, (pid, p) in enumerate(book["packets"].items()):
        entry = {
            "schema": book["schema"],
            "reviewer": f"SYNTHETIC-{i}",
            "independent": True,
            "packet_id": pid,
            "items": [
                {
                    "code": c,
                    "options": [
                        {
                            "label": label,
                            "overall": None,
                            "note": "",
                            "scores": dict.fromkeys(DIMENSIONS),
                        }
                        for label in "AB"
                    ],
                    "preference": None,
                }
                for c in p["items"]
            ],
        }
        path = out / f"synthetic-empty-{i}.json"
        atomic(path, entry)
        exports.append(path)
    report = out / "synthetic-score.json"
    run_cli(
        "blind_review.py",
        "score",
        "--book",
        blind / "管理/book.json",
        "--rating",
        *exports,
        "--out",
        report,
    )
    require(read(report)["binary_agreement"]["jointly_binary"] == 0, "无图席位误计有效原判")
    print("离线核验完成：三题、六席、三个首件、一个缺响应、两份空图盲卷。")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--out", type=Path, help="保留合成证据的新目录；默认临时目录")
    args = cli.parse_args()
    if args.out:
        smoke(args.out)
    else:
        with tempfile.TemporaryDirectory() as temp:
            smoke(Path(temp) / "synthetic")
