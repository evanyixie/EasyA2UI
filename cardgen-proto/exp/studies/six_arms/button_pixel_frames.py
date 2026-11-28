"""Extract original RGB button frames from a frozen JSONL seat manifest.

Usage: python -m six_arms.button_pixel_frames MANIFEST NEW_DIRECTORY [--key-file PATH]
Each row identifies task, arm and checkpoint. Supply source and artifact_sha256
for a generated A2UI JSONL, receipt and receipt_sha256 for an actual capture,
and tree_sha256 for a sealed native-layout.json. Omit unavailable pairs.
Paths may be relative to the manifest. Each receipt sits beside card.png,
screen.jpeg, received-input.jsonl and the native tree. Only blind/crops is
intended for readers. The private directory contains the key and the two
ledgers accepted by button_pixel_census. Requires Pillow.
"""

import argparse
import hashlib
import hmac
import json
import re
import secrets
import struct
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image

from . import native_text_audit as native
from .native_capture_check import area, intersection

ELLIPSIS = re.compile(r"…|⋯|\.{3}|．{3}")


def locate(controls, crop):
    if len(controls) != 1:
        return "ambiguous_id" if controls else "button_absent", None
    node = controls[0]
    if node.get("type") != "Button":
        return "wrong_type", None
    if node.get("visible") != "true":
        return "hidden", None
    original, visible = (native.box(node.get(k)) for k in ("origBounds", "bounds"))
    if not original or not visible or not area(original) or not area(visible):
        return "invalid_bounds", None
    if original != visible or intersection(original, crop) != original:
        return "outside_or_clipped", None
    return "cropped", visible


def pixels(card, box, crop):
    left, top, right, bottom = box
    tile = card.crop((left - crop[0], top - crop[1], right - crop[0], bottom - crop[1]))
    digest = hashlib.sha256(struct.pack(">II", *tile.size) + tile.tobytes()).hexdigest()
    return digest, tile


def capture(row, base):
    file = base / row["receipt"]
    rec = json.loads(native.checked(file, row["receipt_sha256"]))
    native.require(
        rec["status"] == "captured"
        and (rec["task"], rec["arm"]) == (row["task"], row["arm"]),
        "Wrong capture",
    )
    sha = row["artifact_sha256"]
    native.require(
        rec["input_return_sha256"] == rec["input_sha256"] == sha,
        "Wrong returned artifact",
    )
    native.checked(file.parent / "received-input.jsonl", sha)
    terminal = rec["terminal"]
    native.require(terminal["runId"] == rec["run_id"], "Wrong host run")
    native.require(
        tuple(rec["vp"]) == (terminal["widthVp"], terminal["heightVp"]),
        "Wrong viewport",
    )
    c = terminal["cropPx"]
    crop = c["left"], c["top"], c["left"] + c["width"], c["top"] + c["height"]
    with Image.open(
        BytesIO(native.checked(file.parent / "card.png", rec["screenshot_sha256"]))
    ) as png:
        native.require(
            png.format == "PNG" and png.size == (c["width"], c["height"]),
            "Wrong crop PNG",
        )
        card = png.convert("RGB")
    with Image.open(
        BytesIO(native.checked(file.parent / "screen.jpeg", rec["full_sha256"]))
    ) as full:
        native.require(
            intersection(crop, (0, 0, *full.size)) == crop and area(crop) > 0,
            "Invalid crop",
        )
        native.require(
            full.crop(crop).convert("RGB").tobytes() == card.tobytes(),
            "Screenshot replay mismatch",
        )
    digest = row.get("tree_sha256")
    if rec.get("tree_sha256"):
        native.require(
            not digest or rec["tree_sha256"] == digest, "Conflicting tree hashes"
        )
        digest = rec["tree_sha256"]
    if not digest:
        return card, crop, {}, "missing_tree"
    tree = json.loads(native.checked(file.parent / "native-layout.json", digest))
    index = native.control_index(tree, crop)
    roots = index.get("a2ui_capture_root", [])
    if (
        len(roots) != 1
        or roots[0].get("visible") != "true"
        or native.box(roots[0].get("origBounds")) != crop
    ):
        return card, crop, {}, "root_unverified"
    return card, crop, index, None


def extract(row, base, key, image_dir, aliases):
    seat = {k: row[k] for k in ("task", "arm", "checkpoint")}
    seat["artifact_sha256"] = row.get("artifact_sha256")
    native.require(
        bool(row.get("source")) == bool(seat["artifact_sha256"]),
        "Unpaired source and hash",
    )
    native.require(
        bool(row.get("receipt")) == bool(row.get("receipt_sha256")),
        "Unpaired receipt and hash",
    )
    if not row.get("source"):
        native.require(not row.get("receipt"), "Capture without source")
        return {**seat, "seat_state": "no_source", "source_button_count": None}, []
    source = native.checked(base / row["source"], seat["artifact_sha256"])
    updates = [
        m["updateComponents"]
        for line in source.splitlines()
        if line.strip()
        if "updateComponents" in (m := json.loads(line))
    ]
    native.require(len(updates) == 1, "Expected one component update")
    components = updates[0]["components"]
    native.require(
        len({c["id"] for c in components}) == len(components), "Duplicate component"
    )
    buttons = [c for c in components if c["component"] == "Button"]
    if row.get("receipt"):
        card, crop, index, reason = capture(row, base)
    else:
        card, crop, index, reason = None, None, {}, "no_capture"
    records = []
    for button in buttons:
        label = button["label"]
        controls = index.get(button["id"], [])
        state, rect = (reason, None) if reason else locate(controls, crop)
        node = controls[0] if len(controls) == 1 else {}
        text = node.get("text")
        record = {
            **seat,
            "button_id": button["id"],
            "state": state,
            "source_label": label,
            "source_label_ellipsis": bool(ELLIPSIS.search(label))
            if isinstance(label, str)
            else None,
            "native_text": text,
            "native_text_ellipsis": bool(ELLIPSIS.search(text))
            if isinstance(text, str)
            else None,
            "original_rect": native.box(node.get("origBounds")),
            "visible_rect": native.box(node.get("bounds")),
            "crop_rect": crop,
            "rgb_sha256": None,
            "blind_id": None,
        }
        if rect:
            digest, tile = pixels(card, rect, crop)
            alias = hmac.new(key, bytes.fromhex(digest), "sha256").hexdigest()[:16]
            if alias in aliases:
                native.require(aliases[alias] == digest, "Blind identifier collision")
            else:
                aliases[alias] = digest
                # Construct a fresh image so embedded source PNG metadata cannot travel with the pixels.
                Image.frombytes("RGB", tile.size, tile.tobytes()).save(
                    image_dir / (alias + ".png")
                )
            record.update(rgb_sha256=digest, blind_id=alias)
        records.append(record)
    return {
        **seat,
        "seat_state": "captured" if row.get("receipt") else "source_without_capture",
        "source_button_count": len(buttons),
    }, records


def run(manifest, output, key):
    native.require(
        len(key) == 32 and not output.exists(),
        "Expected a 32-byte key and new output directory",
    )
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch:
        stage = Path(scratch) / "package"
        images, private = stage / "blind/crops", stage / "private"
        images.mkdir(parents=True)
        private.mkdir()
        (private / "key.bin").write_bytes(key)
        seats, buttons = (
            private / "seats.private.jsonl",
            private / "buttons.private.jsonl",
        )
        seen, aliases = set(), {}
        with (
            manifest.open(encoding="utf8") as source,
            seats.open("x", encoding="utf8") as s,
            buttons.open("x", encoding="utf8") as b,
        ):
            for line in source:
                if not line.strip():
                    continue
                row = json.loads(line)
                ident = row["task"], row["arm"], row["checkpoint"]
                native.require(ident not in seen, "Duplicate seat")
                seen.add(ident)
                seat, records = extract(row, manifest.parent, key, images, aliases)
                s.write(json.dumps(seat, ensure_ascii=False) + "\n")
                b.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
        stage.rename(output)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("manifest", type=Path)
    cli.add_argument("new_directory", type=Path)
    cli.add_argument(
        "--key-file", type=Path, help="reuse a private 32-byte randomization key"
    )
    args = cli.parse_args()
    run(
        args.manifest,
        args.new_directory,
        args.key_file.read_bytes() if args.key_file else secrets.token_bytes(32),
    )


if __name__ == "__main__":
    main()
