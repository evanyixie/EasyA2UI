"""仅用合成像素、回执与评分测试证据校对、盲化及未知分母。"""

import json
import re

import pytest
from PIL import Image

import blind_review
import evidence
import ratings


def test_capture_and_blind_packet(tmp_path):
    native = tmp_path / "native"
    tid = "synthetic-private-source"
    arm = evidence.ARMS[0]
    place = native / "captures" / tid / arm
    place.mkdir(parents=True)
    card = tmp_path / "source.jsonl"
    card.write_bytes(b"synthetic artifact")
    (place / "received-input.jsonl").write_bytes(card.read_bytes())
    full, photo = place / "screen.jpeg", place / "card.png"
    Image.new("RGB", (40, 36), (0, 32, 8)).save(full)
    with Image.open(full) as screen:
        screen.crop((10, 4, 30, 24)).save(photo)
    h = evidence.sha(card)
    seat = {
        "task_id": tid,
        "arm": arm,
        "generation_status": "artifact_ready",
        "size": "2x2",
        "artifact_sha256": h,
        "artifact_path": str(card),
    }
    missing = {
        **seat,
        "arm": evidence.ARMS[1],
        "generation_status": "geometry_rejected",
        "artifact_sha256": None,
    }
    host = {
        "bundle": "test.bundle",
        "serial": "synthetic",
        "rom": "test",
        "window_name": "testWindow",
    }
    proof = {
        **{k: host[k] for k in ("bundle", "serial", "rom")},
        "task_id": tid,
        "arm": arm,
        "input_return_sha256": h,
        "input_sha256": h,
        "status": "captured",
        "run_id": "demo",
        "terminal": {
            "runId": "demo",
            "sample": "demo.json",
            "state": "READY_WITH_WARNINGS",
            "widthVp": 150,
            "heightVp": 150,
            "cropPx": {"left": 10, "top": 4, "width": 20, "height": 20},
        },
        "foreground": {
            "window": "testWindow x 42 7",
            "windowId": "7",
            "bundle_pid": "42",
        },
        "screen_px": [40, 36],
        "vp": [150, 150],
        "full": str(full),
        "screenshot": str(photo),
        "started": "2020-01-01T00:00:00Z",
        "captured_utc": "2020-01-01T00:00:01Z",
        "screenshot_sha256": evidence.sha(photo),
        "full_sha256": evidence.sha(full),
    }
    evidence.atomic(place / "capture_receipt.json", proof)
    rows = evidence.snapshot([seat, missing], {tid}, native, host)
    package = tmp_path / "review"
    blind_review.build(rows, {}, "synthetic-seal", package)
    bookpath = package / "管理/book.json"
    book = evidence.read(bookpath)
    sides = []
    files = []
    for idx, (pid, mapping) in enumerate(book["packets"].items()):
        page = (package / "评审" / mapping["file"]).read_text(encoding="utf8")
        assert all(s not in page for s in (tid, *evidence.ARMS, str(tmp_path)))
        packet = json.loads(
            re.search(
                r'<script id="packet" type="application/json">(.*?)</script>', page
            )[1]
        )
        case = packet["items"][0]
        (shown,) = tuple(o["label"] for o in case["options"] if o["image"])
        sides.append(shown)
        export = {
            "reviewer": f"synthetic-{idx}",
            "independent": True,
            "schema": book["schema"],
            "packet_id": pid,
            "items": [
                {
                    "code": case["code"],
                    "preference": None,
                    "options": [
                        {
                            "label": s,
                            "scores": dict.fromkeys(
                                ratings.DIMENSIONS, "pass" if s == shown else None
                            ),
                            "overall": "pass" if s == shown else None,
                            "note": "",
                        }
                        for s in "AB"
                    ],
                }
            ],
        }
        path = tmp_path / f"simulated-{idx}.json"
        evidence.atomic(path, export)
        files.append(path)
    assert set(sides) == {"A", "B"}
    report = blind_review.evaluate(bookpath, files, tmp_path / "score.json")
    assert report["binary_agreement"]["jointly_binary"] == 1
    assert report["binary_agreement"]["other_seats"] == 1
    assert report["primary_complete_success_rate"] is None
    book = evidence.read(bookpath)
    first_packet = next(iter(book["packets"].values()))
    local_map = next(iter(first_packet["items"].values()))["map"]
    local_map["A"], local_map["B"] = local_map["B"], local_map["A"]
    evidence.atomic(bookpath, book)
    with pytest.raises(ValueError, match="镜像"):
        blind_review.evaluate(bookpath, files, tmp_path / "incorrect.json")
    with pytest.raises(ValueError, match="评审者"):
        blind_review.evaluate(bookpath, files, package / "评审/leak.json")
    Image.new("RGB", (20, 20), "white").save(photo)
    evidence.atomic(
        place / "capture_receipt.json",
        {**proof, "screenshot_sha256": evidence.sha(photo)},
    )
    with pytest.raises(ValueError, match="原图像素"):
        evidence.snapshot([seat, missing], {tid}, native, host)


def test_device_capture_protocol_without_hardware(tmp_path, monkeypatch):
    from io import BytesIO
    from pathlib import Path

    import capture

    source = tmp_path / "sealed.jsonl"
    source.write_bytes(b"synthetic test bytes")
    seat = {
        "task_id": "synthetic-source",
        "arm": evidence.ARMS[0],
        "size": "2x2",
        "generation_status": "artifact_ready",
        "artifact_path": str(source),
        "artifact_sha256": evidence.sha(source),
    }
    other = {
        **seat,
        "arm": evidence.ARMS[1],
        "artifact_path": None,
        "artifact_sha256": None,
        "generation_status": "geometry_rejected",
    }
    hostinfo = {
        "serial": "fake",
        "bundle": "synthetic.bundle",
        "window_name": "syntheticWindow",
        "rom": "synthetic",
    }

    class FakeHost:
        genui_src = None
        bundle = hostinfo["bundle"]
        fail_first = True

        def info(self):
            return hostinfo

        def focused(self):
            return {
                "windowId": "4",
                "bundle_pid": "123",
                "window": "syntheticWindow x 123 4",
            }

        def command(self, *args):
            if args[:2] == ("file", "send"):
                self.payload = Path(args[-2]).read_bytes()
            elif args[:3] == ("file", "recv", "-b"):
                Path(args[-1]).write_bytes(self.payload)
            elif args[:3] == ("shell", "aa", "start"):
                self.run_id = args[args.index("runId") + 1]
            elif args[:2] == ("shell", "hilog"):
                terminal = {
                    "runId": self.run_id,
                    "sample": self.run_id + ".json",
                    "state": "READY_WITH_WARNINGS",
                    "widthVp": 150,
                    "heightVp": 150,
                    "cropPx": {"left": 0, "top": 0, "width": 40, "height": 40},
                }
                return "A2UI_RUN " + json.dumps(terminal)
            elif args[:2] == ("shell", "snapshot_display") and self.fail_first:
                self.fail_first = False
                raise RuntimeError("simulated display interruption")
            elif args[:2] == ("file", "recv"):
                image = Image.new("RGB", (40, 40), "white")
                image.paste("black", (8, 8, 23, 23))
                stream = BytesIO()
                image.save(stream, "JPEG")
                Path(args[-1]).write_bytes(stream.getvalue())
            return ""

    monkeypatch.setattr(
        capture.e, "sealed_seats", lambda root: ([seat, other], "synthetic")
    )
    monkeypatch.setattr(capture.time, "sleep", lambda seconds: None)
    host = FakeHost()
    where = tmp_path / "native"
    where.mkdir()
    first = capture.collect(tmp_path, where, host, None, None)
    assert first["first"]["by_arm"][seat["arm"]]["capture"] == {"device_failed": 1}
    result = capture.collect(tmp_path, where, host, None, "synthetic retry")
    assert result["first"] == first["first"]
    assert result["including_additional"]["by_arm"][seat["arm"]]["capture"] == {
        "captured_first_frame": 1
    }
