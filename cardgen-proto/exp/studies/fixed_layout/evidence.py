"""核验冻结席位、首件字节、原生取图回执及裁区像素。"""

import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops

ARMS = ("model_model", "program_program")
SIZES = {"2x2": [150, 150], "2x4": [300, 150]}
SAMPLE_SALT = "report219-native-primary-frame-sample-20261125/"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def verified(path, expected):
    data = Path(path).read_bytes()
    require(digest(data) == expected, f"摘要不符 {Path(path).name}")
    return data


def read(path):
    return json.loads(path.read_bytes())


def atomic(path, value, *, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf8", dir=path.parent, delete=False
    ) as stream:
        tmp = Path(stream.name)
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    if exclusive:
        try:
            os.link(tmp, path)
        finally:
            tmp.unlink()
    else:
        os.replace(tmp, path)


def safe_name(value):
    require(
        isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value),
        "编号不合法",
    )
    return value


def protect_seal(root, destination):
    root, destination = root.resolve(), destination.resolve()
    protected = (
        "results",
        "shared_inputs",
        "anonymous",
        "freeze.json",
        "blind_map.json",
        "seal.json",
        "writer.lock",
        "status.json",
    )
    require(
        root != destination
        and all(not destination.is_relative_to(root / n) for n in protected),
        "输出位置与冻结批次证据重叠",
    )


def select_pairs(tasks, n):
    require(type(n) is int and 1 <= n <= len(tasks), "抽取题数超出冻结分母")
    ranked = sorted(tasks, key=lambda task: digest((SAMPLE_SALT + task).encode()))
    return set(ranked[:n])


def verify_capture(row, seat, directory, host):
    require(
        row["task_id"] == seat["task_id"] and row["arm"] == seat["arm"],
        "首图对应席位不同",
    )
    expected = seat["artifact_sha256"]
    require(
        expected == row["input_return_sha256"] == row["input_sha256"], "装载字节不符"
    )
    verified(directory / "received-input.jsonl", expected)
    verified(Path(seat["artifact_path"]), expected)
    require(
        row["serial"] == host["serial"]
        and row["bundle"] == host["bundle"]
        and row["rom"] == host["rom"]
        and row["rom"],
        "设备宿主不符",
    )
    term, front = row["terminal"], row["foreground"]
    fields = front["window"].split()
    require(
        len(fields) >= 4
        and fields[0] == host["window_name"]
        and fields[3] == front["windowId"]
        and fields[2] == front["bundle_pid"],
        "前台窗口不符",
    )
    require(
        row["status"] == "captured"
        and term["state"] in ("READY", "READY_WITH_WARNINGS"),
        "缺本次终态",
    )
    require(
        row["run_id"] == term["runId"] and term["sample"] == row["run_id"] + ".json",
        "回执装载编号不符",
    )
    require(
        SIZES[seat["size"]] == row["vp"] == [term["widthVp"], term["heightVp"]],
        "画布不符",
    )
    require(
        datetime.fromisoformat(row["started"])
        <= datetime.fromisoformat(row["captured_utc"]),
        "时间边界不符",
    )
    full = directory / "screen.jpeg"
    photo = directory / "card.png"
    require(
        Path(row["full"].replace("\\", "/")).name == full.name
        and Path(row["screenshot"].replace("\\", "/")).name == photo.name,
        "图片目录不符",
    )
    verified(full, row["full_sha256"])
    verified(photo, row["screenshot_sha256"])
    x, y, w, h = [term["cropPx"][k] for k in ("left", "top", "width", "height")]
    with Image.open(full) as screen, Image.open(photo) as card:
        require(
            screen.size == tuple(row["screen_px"]) and card.size == (w, h),
            "裁图尺寸不符",
        )
        require(
            0 <= x < x + w <= screen.width and 0 <= y < y + h <= screen.height,
            "裁图越界",
        )
        actual = screen.convert("RGB").crop((x, y, x + w, y + h))
        require(
            ImageChops.difference(actual, card.convert("RGB")).getbbox() is None,
            "原图像素不匹配",
        )


def snapshot(seats, selected, out, host):
    rows = []
    for seat in seats:
        row = dict(seat)
        row["sample_selected"] = row["task_id"] in selected
        row["native_visual_judgment"] = None
        row["independent_business_judgment"] = None
        row["live_update_verified"] = None
        row["action_execution_verified"] = None
        place = out / "captures" / row["task_id"] / row["arm"]
        receipt = place / "capture_receipt.json"
        if not row["artifact_sha256"]:
            state = "no_first_artifact"
        elif not row["sample_selected"]:
            state = "outside_capture_sample"
        elif receipt.exists():
            proof = read(receipt)
            require(
                proof["input_sha256"] == row["artifact_sha256"]
                and (proof["task_id"], proof["arm"]) == (row["task_id"], row["arm"]),
                "旧回执与首件不符",
            )
            corrected = place / "offline_verification.json"
            if corrected.exists():
                note = read(corrected)
                require(
                    proof["status"] == "device_failed"
                    and note["original_receipt_sha256"] == digest(receipt.read_bytes()),
                    "复核未对应原回执",
                )
                verify_capture({**proof, "status": "captured"}, row, place, host)
                row["original_capture_note"] = proof["error"]
            if proof["status"] == "captured" or corrected.exists():
                verify_capture({**proof, "status": "captured"}, row, place, host)
                row.update(
                    capture_receipt=str(receipt),
                    card_png=str(place / "card.png"),
                    screenshot_sha256=proof["screenshot_sha256"],
                    terminal=proof["terminal"]["state"],
                )
                state = "captured_first_frame"
            else:
                require(proof["status"] == "device_failed", "捕获状态未知")
                row["error"] = proof["error"]
                state = "device_failed"
        elif place.exists():
            state = "interrupted_capture"
        else:
            state = "awaiting_capture"
        row["capture_status"] = state
        rows.append(row)
    return rows


def coverage(rows):
    tasks = {r["task_id"] for r in rows}
    require(
        len(rows) == len(tasks) * 2
        and {(r["task_id"], r["arm"]) for r in rows}
        == {(t, arm) for t in tasks for arm in ARMS},
        "分母缺席或重复",
    )
    return {
        "assigned_cases": len(tasks),
        "assigned_seats": len(rows),
        "selected_cases": len({r["task_id"] for r in rows if r["sample_selected"]}),
        "by_arm": {
            arm: {
                "assigned": len(tasks),
                "generation": dict(
                    Counter(r["generation_status"] for r in rows if r["arm"] == arm)
                ),
                "capture": dict(
                    Counter(r["capture_status"] for r in rows if r["arm"] == arm)
                ),
                "independently_rated_here": 0,
            }
            for arm in ARMS
        },
        "primary_complete_success_rate": None,
        "primary_paired_difference": None,
        "scope": "登记首轮产物与真机首帧覆盖。独立视觉、业务、动作执行和原地刷新均待相应证据。",
    }


def sealed_seats(root, count=None):
    seal_bytes = (root / "seal.json").read_bytes()
    seal = json.loads(seal_bytes)
    if "evidence_sha256" in seal:
        files = {
            p.relative_to(root).as_posix(): p
            for sub in ("results", "shared_inputs", "anonymous")
            for p in (root / sub).rglob("*")
            if p.is_file()
        }
        require(set(files) == set(seal["evidence_sha256"]), "封存文件清单不一致")
        for rel, path in files.items():
            verified(path, seal["evidence_sha256"][rel])
    freeze = json.loads(verified(root / "freeze.json", seal["freeze_sha256"]))
    mapping = json.loads(verified(root / "blind_map.json", freeze["blind_map_sha256"]))
    if count is None:
        count = len(freeze["queue"])
    require(count > 0 and seal["receipts_count"] == 2 * count, "批次首轮分母不符")
    manifest = json.loads(
        verified(root / "anonymous/manifest.json", seal["anonymous_manifest_sha256"])
    )
    index = {}
    for item in manifest:
        blind = safe_name(item["anonymous_id"])
        require(blind not in index, "匿名清单重复")
        index[blind] = item
    aliases = {"A": ARMS[0], "B": ARMS[1]}
    require(freeze["arms"] == aliases, "首轮实验条件不符")
    queue = freeze["queue"]
    tasks = [safe_name(case["task_id"]) for case in queue]
    require(len(tasks) == len(set(tasks)) == count, "冻结队列数或唯一性不符")
    arm_hashes = seal["arm_receipt_sha256"]
    expected_files = {
        f"results/{task}/{arm}/receipt.json" for task in tasks for arm in ARMS
    }
    require(set(arm_hashes) == expected_files, "已封存回执路径与冻结队列不一致")
    seats = []
    used = set()
    for case in queue:
        task = case["task_id"]
        require(case["execute"] in ("AB", "BA"), "正式队列未登记两个首轮条件")
        for alias in case["execute"]:
            arm = aliases[alias]
            rel = f"results/{task}/{arm}/receipt.json"
            rec = json.loads(verified(root / rel, arm_hashes[rel]))
            require(
                rec.get("task_id") == task
                and rec.get("cell") == arm
                and rec.get("first_pass") is True
                and rec.get("anonymous_id") == mapping[task][arm]
                and rec.get("source_row_sha256") == case["input_line_sha256"],
                "首轮回执与冻结题不符",
            )
            row = {
                "task_id": task,
                "arm": arm,
                "generation_status": rec["status"],
                "size": None,
                "artifact_sha256": None,
                "artifact_path": None,
                "execution_receipt_sha256": arm_hashes[rel],
            }
            shared_sha = rec.get("shared_sha256")
            if shared_sha:
                shared = json.loads(
                    verified(root / "shared_inputs" / (task + ".json"), shared_sha)
                )
                size = shared["size"]
                require(
                    shared["task_id"] == task
                    and size in SIZES
                    and [shared["canvas"]["width"], shared["canvas"]["height"]]
                    == SIZES[size],
                    "合同版面不符",
                )
                row["size"] = size
            if rec["status"] == "artifact_ready":
                require(row["size"], "首件缺少合同尺寸")
                blind = safe_name(rec["anonymous_id"])
                require(
                    blind in index and blind not in used, "正式首件缺少唯一匿名副本"
                )
                artifact_hash = rec["artifact_sha256"]
                location = root / Path(rel).parent / "card.a2ui.jsonl"
                verified(location, artifact_hash)
                ref = index[blind]
                canonical = root / "anonymous" / blind / "card.a2ui.jsonl"
                rel_card = Path(ref["relative_card_path"])
                require(
                    not rel_card.is_absolute()
                    and (
                        root / rel_card == canonical
                        or root / "anonymous" / rel_card == canonical
                    ),
                    "匿名副本路径不符",
                )
                require(ref["sha256"] == artifact_hash, "匿名清单与首件摘要不符")
                verified(canonical, artifact_hash)
                used.add(blind)
                row.update(artifact_sha256=artifact_hash, artifact_path=str(location))
            else:
                require(not rec.get("artifact_sha256"), "未生成终态带有首件摘要")
            seats.append(row)
    require(set(index) == used, "匿名清单与首件席位覆盖不同")
    return seats, digest(seal_bytes)


def supplement_rows(rows, out, host):
    result = []
    for original in rows:
        row = dict(original)
        row["initial_capture_status"] = original["capture_status"]
        row["additional_capture_attempts"] = 0
        folder = out / "additional" / row["task_id"] / row["arm"]
        for attempt in sorted(folder.glob("attempt-*")):
            row["additional_capture_attempts"] += 1
            require(
                original["capture_status"] in ("device_failed", "interrupted_capture"),
                "只有已尝试而无有效图片的首件可追加取图",
            )
            if not (attempt / "capture_receipt.json").exists():
                continue
            proof = read(attempt / "capture_receipt.json")
            require(
                proof["input_sha256"] == row["artifact_sha256"]
                and proof["task_id"] == row["task_id"]
                and proof["arm"] == row["arm"],
                "补充取图未绑定同一首件",
            )
            if proof["status"] == "captured":
                require(
                    row["capture_status"] != "captured_first_frame",
                    "已取得有效补图后又提交另一张",
                )
                verify_capture(proof, row, attempt, host)
                row.update(
                    capture_status="captured_first_frame",
                    capture_receipt=str(attempt / "capture_receipt.json"),
                    card_png=str(attempt / "card.png"),
                    screenshot_sha256=proof["screenshot_sha256"],
                    terminal=proof["terminal"]["state"],
                    capture_origin="additional_same_artifact",
                )
            else:
                require(proof["status"] == "device_failed", "补充取图状态未知")
        result.append(row)
    return result
