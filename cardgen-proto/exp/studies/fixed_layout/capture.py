"""用 HDC 在已安装的兼容 A2UIRunner 宿主中捕获封存的同字节首件。"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

import evidence as e
from evidence import sha
from run import single_writer


def utc():
    return datetime.now(UTC).isoformat()


class Device:
    def __init__(self, args):
        self.hdc = shutil.which(args.hdc)
        e.require(self.hdc, "未找到 HDC")
        self.serial = args.serial
        self.bundle = args.bundle
        self.window_name = args.window_name
        self.genui_src = (
            Path(os.environ["GENUI_ROOT"]) / "src" if os.getenv("GENUI_ROOT") else None
        )

    def command(self, *args):
        proc = subprocess.run(
            [self.hdc, "-t", self.serial, *map(str, args)],
            capture_output=True,
            check=False,
            timeout=25,
        )
        text = (proc.stdout + proc.stderr).decode("utf-8", "replace")
        if proc.returncode or "[Fail]" in text or "error code:" in text.lower():
            raise RuntimeError(text[:250])
        return text

    def focused(self):
        lines = self.command(
            "shell", "hidumper", "-s", "WindowManagerService", "-a", "-a"
        )
        match = re.search(r"^Focus window: (\d+)", lines, re.MULTILINE)
        e.require(match, "未取得焦点窗口")
        wid = match.group(1)
        pids = self.command("shell", "pidof", self.bundle).split()
        for line in lines.splitlines():
            fields = line.split()
            if (
                len(fields) >= 4
                and fields[0] == self.window_name
                and fields[2] in pids
                and fields[3] == wid
            ):
                return {
                    "windowId": wid,
                    "window": line.strip(),
                    "bundle_pid": fields[2],
                }
        raise ValueError("焦点不属于指定的宿主窗口或进程")

    def info(self):
        rom = self.command(
            "shell", "param", "get", "const.product.software.version"
        ).strip()
        dump = self.command("shell", "bm", "dump", "-n", self.bundle)
        versions = sorted(
            {
                tuple(i)
                for i in re.findall(
                    r'"(versionCode|versionName)"\s*:\s*("[^"]+"|\d+)', dump
                )
            }
        )
        e.require(rom and self.bundle in dump and versions, "无法核实 ROM 或宿主版本")
        return {
            "serial": self.serial,
            "bundle": self.bundle,
            "rom": rom,
            "versions": [list(v) for v in versions],
            "window_name": self.window_name,
        }


def capture(host, source, size, dest, record):
    hdc = host.command
    bundle = host.bundle
    tag = str(uuid.uuid4())
    filename = tag + ".json"
    sandbox = "data/storage/el2/base/files/a2ui/" + filename
    remote = "/data/local/tmp/fixed-layout-" + tag + ".jpeg"
    checkbytes = dest / "received-input.jsonl"
    start = utc()
    try:
        hdc("shell", "-b", bundle, "mkdir", "-p", "data/storage/el2/base/files/a2ui")
        hdc("file", "send", "-b", bundle, source, sandbox)
        hdc("file", "recv", "-b", bundle, sandbox, checkbytes)
        if sha(checkbytes) != sha(source):
            raise ValueError("推送前后字节不同")
        hdc(
            "shell",
            "aa",
            "start",
            "-a",
            "EntryAbility",
            "-b",
            bundle,
            "-m",
            "entry",
            "--ps",
            "runId",
            tag,
            "--ps",
            "sampleFile",
            filename,
            "--pi",
            "width",
            size[0],
            "--pi",
            "height",
            size[1],
        )
        terminal = None
        lines = ""
        until = time.monotonic() + 16
        while time.monotonic() < until:
            lines = hdc(
                "shell", "hilog", "-x", "-T", "A2UIRunner", "-e", tag, "-v", "wrap"
            )
            events = [
                json.loads(s) for s in re.findall(r"A2UI_RUN\s+(\{[^\n]+\})", lines)
            ]
            for e in events:
                if e.get("runId") == tag and e.get("state") in (
                    "READY",
                    "READY_WITH_WARNINGS",
                    "FAILED",
                ):
                    terminal = e
            if terminal:
                break
            time.sleep(0.35)
        (dest / "runner.log").write_text(lines, encoding="utf8")
        if not terminal or terminal["state"] == "FAILED":
            raise ValueError(f"无本次可截图的终态：{terminal}")
        crop = terminal["cropPx"]
        if [terminal["widthVp"], terminal["heightVp"]] != size:
            raise ValueError("终态尺寸与原始请求不一致")
        time.sleep(1)
        before = host.focused()
        hdc("shell", "snapshot_display", "-f", remote)
        when = utc()
        hdc("file", "recv", remote, dest / "screen.jpeg")
        after = host.focused()
        if before != after:
            raise ValueError("截图前后窗口变化")
        x, y, w, h = [crop[k] for k in ("left", "top", "width", "height")]
        with Image.open(dest / "screen.jpeg") as pic:
            fullsize = pic.size
            if (
                min(x, y) < 0
                or x + w > pic.width
                or y + h > pic.height
                or abs(w / h - size[0] / size[1]) > 0.015
            ):
                raise ValueError("原生裁框越界或比例不符")
            card = pic.crop((x, y, x + w, y + h)).convert("RGB")
            if max(c[1] - c[0] for c in card.getextrema()) < 40:
                raise ValueError("裁框缺少可见内容")
            card.save(dest / "card.png")
        record.update(
            status="captured",
            run_id=tag,
            started=start,
            captured_utc=when,
            foreground=before,
            terminal=terminal,
            screen_px=fullsize,
            full=str(dest / "screen.jpeg"),
            screenshot=str(dest / "card.png"),
            full_sha256=sha(dest / "screen.jpeg"),
            screenshot_sha256=sha(dest / "card.png"),
            input_return_sha256=sha(checkbytes),
        )
        if host.genui_src is not None:
            try:
                sys.path.insert(0, str(host.genui_src))
                from genui_device.native_audit import dump_layout

                dump_layout(host.hdc, host.serial, dest, bundle=bundle)
            except (
                ValueError,
                OSError,
                RuntimeError,
                ImportError,
                subprocess.SubprocessError,
            ) as exc:
                record["tree_error"] = str(exc)
            finally:
                sys.path.pop(0)
        else:
            record["tree_error"] = "未指定宿主树取证模块"
    finally:
        for args in [
            ("shell", "-b", bundle, "rm", "-f", sandbox),
            ("shell", "rm", "-f", remote),
        ]:
            try:
                hdc(*args)
            except (OSError, RuntimeError, subprocess.SubprocessError):
                continue


def collect(root, out, device, n, reason):
    seats, seal = e.sealed_seats(root)
    tasks = {r["task_id"] for r in seats}
    selected = e.select_pairs(tasks, n if n is not None else len(tasks))
    script = Path(__file__)
    info = device.info()
    plan = {
        "seal_sha256": seal,
        "selected": sorted(selected),
        "salt": e.SAMPLE_SALT,
        "script_sha256": sha(script),
        "verification_sha256": sha(Path(e.__file__)),
    }
    if (out / "plan.json").exists():
        e.require(e.read(out / "plan.json") == plan, "取图实现、范围或批次改变")
        e.require(e.read(out / "host.json") == info, "取图设备与冻结宿主不同")
    else:
        e.require(
            not any(p.name != "writer.lock" for p in out.iterdir()), "新采集目录需为空"
        )
        e.atomic(out / "host.json", info)
        e.atomic(out / "plan.json", plan)

    def snapshot():
        return e.supplement_rows(e.snapshot(seats, selected, out, info), out, info)

    rows = snapshot()
    if reason:
        e.require(
            not any(r["capture_status"] == "awaiting_capture" for r in rows),
            "补采前需完成初次取图",
        )
        pending = [
            r
            for r in rows
            if r["capture_status"] in ("interrupted_capture", "device_failed")
        ]
    else:
        pending = [r for r in rows if r["capture_status"] == "awaiting_capture"]
    for r in pending:
        attempt = r["additional_capture_attempts"] + 1
        if reason:
            place = (
                out / "additional" / r["task_id"] / r["arm"] / f"attempt-{attempt:03d}"
            )
        else:
            place = out / "captures" / r["task_id"] / r["arm"]
        place.mkdir(parents=True, exist_ok=False)
        proof = {
            "task_id": r["task_id"],
            "arm": r["arm"],
            "input_sha256": r["artifact_sha256"],
            "source": r["artifact_path"],
            "vp": e.SIZES[r["size"]],
            "clicks_executed": 0,
            "serial": info["serial"],
            "rom": info["rom"],
            "bundle": info["bundle"],
            "seal_sha256": seal,
            "physical_capture_attempt": 1 + attempt if reason else 1,
            "selection_reason": reason,
        }
        try:
            e.verified(Path(proof["source"]), proof["input_sha256"])
            capture(device, Path(proof["source"]), proof["vp"], place, proof)
            e.verify_capture(proof, r, place, info)
        except (
            OSError,
            ValueError,
            RuntimeError,
            AssertionError,
            KeyError,
            IndexError,
            TypeError,
            subprocess.SubprocessError,
        ) as exc:
            proof.update(status="device_failed", error=repr(exc))
        e.atomic(place / "capture_receipt.json", proof)
        if proof["status"] == "device_failed":
            break
    rows = snapshot()
    first = [{**r, "capture_status": r["initial_capture_status"]} for r in rows]
    result = {"first": e.coverage(first), "including_additional": e.coverage(rows)}
    e.atomic(out / "coverage.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--window-name", required=True)
    parser.add_argument("--hdc", default="hdc")
    parser.add_argument(
        "--sample-pairs", type=int, help="初次计划时冻结成对抽取，默认全题"
    )
    parser.add_argument(
        "--additional-reason", help="初次已全部尝试后，只补采有记录的缺图席位"
    )
    args = parser.parse_args()
    e.require(
        re.fullmatch(r"[A-Za-z0-9:._-]+", args.serial)
        and re.fullmatch(r"[A-Za-z0-9._]+", args.bundle),
        "设备或包名格式无效",
    )
    e.require(
        args.additional_reason is None or args.additional_reason.strip(), "补采需要原因"
    )
    lock = Path(tempfile.gettempdir()) / (
        "fixed-layout-device-" + e.digest(args.serial.encode())
    )
    lock.mkdir(exist_ok=True)
    e.protect_seal(args.root, args.out)
    args.out.mkdir(parents=True, exist_ok=True)
    with single_writer(lock), single_writer(args.out):
        summary = collect(
            args.root, args.out, Device(args), args.sample_pairs, args.additional_reason
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
