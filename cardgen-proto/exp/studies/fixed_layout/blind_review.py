"""制作匿名镜像离线评审页，回收两位评审的独立原判。"""

import argparse
import base64
import io
import json
import random
import secrets
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

import evidence as n
import ratings

SCHEMA = "fixed-layout-report219-first-frame-v1"


def serialize(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def assignments(rows, rng):
    """按画布和有图情况平衡 A/B；同题第二位评审镜像顺序。"""
    strata = defaultdict(lambda: defaultdict(list))
    for row in rows:
        visible = sum(bool(slot["image_sha256"]) for slot in row["arms"].values())
        strata[row["size"]][visible].append(row["task"])
    first = {}
    total = 0
    for size in sorted(strata):
        within_size = 0
        for visible in sorted(strata[size]):
            members = sorted(strata[size][visible])
            rng.shuffle(members)
            lead = 1 if (within_size or total) < 0 else -1
            if within_size == total == 0:
                lead = rng.choice((-1, 1))
            for index, task in enumerate(members):
                side = lead if index % 2 == 0 else -lead
                first[task] = side == 1
                within_size += side
                total += side
    return first


def fact_prompt(contract):
    if contract is None:
        return "该题缺少共同可展示合同。"
    entities = {e["id"]: e["name"] for e in contract["entities"]}
    lines = ["固定首帧内容"]
    for unit in contract["units"]:
        who = entities.get(unit.get("entity"), "")
        lines.append(
            f"• {who + '　' if who else ''}{unit['sample_text']}〔{unit['role']}〕"
        )
    if contract["actions"]:
        labels = {
            "whole_card": "整卡",
            "record_click": "记录",
            "independent_entry": "独立入口",
        }
        lines.append("动作入口与归属")
        for action in contract["actions"]:
            owners = "、".join(entities.get(s, s) for s in action["owners"])
            lines.append(
                "• "
                + "　".join(
                    str(v)
                    for v in [
                        labels.get(action["interaction"], action["interaction"]),
                        action.get("caption"),
                        owners,
                    ]
                    if v
                )
            )
    for pref in contract.get("user_preferences", []):
        if pref.get("quote"):
            lines.append("呈现偏好　" + str(pref["quote"]))
    return "\n".join(lines)


def blind_image(row):
    if row["capture_status"] != "captured_first_frame":
        return None
    raw = n.verified(Path(row["card_png"]), row["screenshot_sha256"])
    with Image.open(io.BytesIO(raw)) as card, io.BytesIO() as clean:
        # 只将相同 RGB 像素送入评审页面，移除所有文件元数据。
        card.convert("RGB").save(clean, format="PNG")
        return "data:image/png;base64," + base64.b64encode(clean.getvalue()).decode()


def build(rows, contracts, seal, out):
    n.require(not out.exists(), "盲包目录已存在")
    total = n.coverage(rows)
    first = n.coverage(
        [
            {
                **r,
                "capture_status": r.get("initial_capture_status", r["capture_status"]),
            }
            for r in rows
        ]
    )
    seed = secrets.randbits(128)
    rng = random.Random(seed)
    by = {}
    for row in rows:
        by.setdefault(row["task_id"], {})[row["arm"]] = row
    selected = [
        t for t, pair in by.items() if all(r["sample_selected"] for r in pair.values())
    ]
    n.require(len(selected) == total["selected_cases"], "同题两个席位必须成对抽取")
    for task in selected:
        n.require(
            not any(
                r["capture_status"] == "awaiting_capture" for r in by[task].values()
            ),
            "已入选首件仍有待取图记录；先完成采集",
        )
    order = assignments(
        [
            {
                "task": t,
                "size": next(iter(by[t].values()))["size"] or "unknown",
                "arms": {
                    a: {"image_sha256": r.get("screenshot_sha256")}
                    for a, r in by[t].items()
                },
            }
            for t in selected
        ],
        rng,
    )
    public = Path(__file__).with_name("review.html").read_text(encoding="utf8")
    book = {
        "schema": SCHEMA,
        "seal_sha256": seal,
        "coverage": total,
        "initial_capture_coverage": first,
        "seed": str(seed),
        "assigned": sorted(by),
        "packets": {},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        staged = Path(tmp) / "package"
        (staged / "评审").mkdir(parents=True)
        for i, name in enumerate(("评审甲.html", "评审乙.html")):
            tasks = sorted(selected)
            rng.shuffle(tasks)
            packet = {"schema": SCHEMA, "packet_id": secrets.token_hex(12), "items": []}
            key = {}
            for task in tasks:
                code = secrets.token_hex(12)
                n.require(code not in key, "随机盲号冲突")
                arms = n.ARMS if order[task] != bool(i) else n.ARMS[::-1]
                mapping = dict(zip("AB", arms, strict=True))
                slot = by[task]
                key[code] = {
                    "task": task,
                    "map": mapping,
                    "images": {
                        k: slot[v].get("screenshot_sha256") for k, v in mapping.items()
                    },
                    "artifacts": {
                        k: slot[v]["artifact_sha256"] for k, v in mapping.items()
                    },
                }
                packet["items"].append(
                    {
                        "code": code,
                        "query": fact_prompt(contracts.get(task)),
                        "title": "",
                        "description": "",
                        "size": next(iter(slot.values()))["size"] or "",
                        "options": [
                            {"label": k, "image": blind_image(slot[v])}
                            for k, v in mapping.items()
                        ],
                    }
                )
            payload = serialize(packet).replace("<", "\\u003c")
            html = public.replace("__PACKET__", payload).encode()
            (staged / "评审" / name).write_bytes(html)
            book["packets"][packet["packet_id"]] = {
                "file": name,
                "sha256": n.digest(html),
                "items": key,
            }
        n.atomic(staged / "管理" / "book.json", book)
        staged.rename(out)
    return total


def validate_book(book):
    assigned = set(book["assigned"])
    n.require(
        len(assigned) == len(book["assigned"]) == book["coverage"]["assigned_cases"],
        "盲册题号与原分母不符",
    )
    books, codes = [], set()
    for packet in book["packets"].values():
        tasks = {}
        for code, row in packet["items"].items():
            task = row["task"]
            mapping = row["map"]
            n.require(
                task in assigned
                and task not in tasks
                and code not in codes
                and set(mapping) == set("AB")
                and set(mapping.values()) == set(n.ARMS),
                "盲册出现重复题号、盲号或方法映射错误",
            )
            codes.add(code)
            by_arm = {
                arm: (row["images"][label], row["artifacts"][label])
                for label, arm in mapping.items()
            }
            n.require(
                all(not photo or artifact for photo, artifact in by_arm.values()),
                "盲册中的图缺首件",
            )
            tasks[task] = (mapping["A"], by_arm)
        n.require(len(tasks) == book["coverage"]["selected_cases"], "盲册抽题分母不符")
        books.append(tasks)
    first, second = books
    n.require(
        first.keys() == second.keys()
        and all(
            first[t][0] != second[t][0] and first[t][1] == second[t][1] for t in first
        ),
        "两份盲册的首件、图片与镜像映射不一致",
    )


def evaluate(book_path, exports, output):
    n.require(
        not output.resolve().is_relative_to(
            (book_path.parent.parent / "评审").resolve()
        ),
        "解盲输出不能写入评审者的目录",
    )
    book = n.read(book_path)
    n.require(
        book["schema"] == SCHEMA and len(exports) == len(book["packets"]) == 2,
        "需对应的两份盲评原件",
    )
    n.require(not output.exists(), "评审汇总已存在")
    validate_book(book)
    names, votes, refs, preferences = {}, {}, {}, {}
    for path in exports:
        export, digest = ratings.read(path)
        pid = export["packet_id"]
        person = export.get("reviewer", "").strip()
        n.require(
            pid in book["packets"]
            and pid not in votes
            and person
            and person.casefold() not in names.values()
            and export.get("independent") is True
            and export["schema"] == SCHEMA,
            "身份、独立声明或包号不符",
        )
        names[pid] = person.casefold()
        refs[pid] = {"reviewer": person, "export_sha256": digest}
        record = book["packets"][pid]
        n.verified(book_path.parent.parent / "评审" / record["file"], record["sha256"])
        # 开发解码器按公开标签解析逐维判定和偏好。包的实际规模、臂名及正式来源在此核验。
        _, result = ratings.decode({**export, "schema": ratings.SCHEMA}, {pid: record})
        votes[pid] = {
            (t, arm): v
            for t, entry in result.items()
            for arm, v in entry["arms"].items()
        }
        preferences[pid] = {t: r["decoded_preference"] for t, r in result.items()}
    left, right = votes
    n.require(votes[left].keys() == votes[right].keys(), "两名评审没有评同一组首件")
    rows, pairs = [], []
    for task in book["assigned"]:
        for arm in n.ARMS:
            seat = (task, arm)
            raw = {pid: decisions.get(seat) for pid, decisions in votes.items()}
            a, b = [r.get("effective_overall") if r else None for r in raw.values()]
            pairs.append((a, b))
            agreement = a if a == b and a in ("pass", "fail") else None
            rows.append(
                {
                    "task_id": task,
                    "arm": arm,
                    "raw_judgments": raw,
                    "both_raters_agree": agreement,
                    "needs_adjudication": a != b and a is not None and b is not None,
                }
            )
    n.require(len(rows) == book["coverage"]["assigned_seats"], "总分母不一致")
    report = {
        "schema": SCHEMA,
        "source_book_sha256": n.sha(book_path),
        "seal_sha256": book["seal_sha256"],
        "submissions": refs,
        "coverage": book["coverage"],
        "binary_agreement": ratings.agreement(pairs, left, right),
        "raw_preferences": preferences,
        "agreement_counts": dict(
            Counter(r["both_raters_agree"] or "unknown" for r in rows)
        ),
        "primary_complete_success_rate": None,
        "rows": rows,
    }
    n.atomic(output, report, exclusive=True)
    return {
        k: report[k]
        for k in (
            "agreement_counts",
            "binary_agreement",
            "primary_complete_success_rate",
        )
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="command", required=True)
    p = sub.add_parser("pack")
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--native-dir",
        type=Path,
        help="含 plan.json、host.json、captures/ 及可选 additional/ 的授权本地取证目录",
    )
    g.add_argument(
        "--missing-captures",
        action="store_true",
        help="没有真机取证时保留全分母，生成空图盲卷",
    )
    p.add_argument("--window-name", help="设备回执中预先核准的前台窗口名")
    p = sub.add_parser("score")
    p.add_argument("--book", type=Path, required=True)
    p.add_argument("--rating", nargs=2, type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = cli.parse_args()
    if args.command == "score":
        summary = evaluate(args.book, args.rating, args.out)
    else:
        n.protect_seal(args.root, args.out)
        seats, seal = n.sealed_seats(args.root)
        tasks = {r["task_id"] for r in seats}
        if args.native_dir:
            plan = n.read(args.native_dir / "plan.json")
            selected = set(plan["selected"])
            n.require(
                plan["seal_sha256"] == seal
                and selected == n.select_pairs(tasks, len(selected)),
                "采集计划与封存席位不一致",
            )
            n.require(args.window_name, "需给出预先核准的宿主窗口名")
            host = n.read(args.native_dir / "host.json")
            n.require(
                host.get("window_name", args.window_name) == args.window_name,
                "窗口名与取证宿主冻结值不同",
            )
            host = {**host, "window_name": args.window_name}
            rows = n.supplement_rows(
                n.snapshot(seats, selected, args.native_dir, host),
                args.native_dir,
                host,
            )
        else:
            rows = [
                {
                    **r,
                    "sample_selected": True,
                    "capture_status": "missing_capture_evidence"
                    if r["artifact_sha256"]
                    else "no_first_artifact",
                }
                for r in seats
            ]
        contracts = {
            r["task_id"]: n.read(args.root / "shared_inputs" / (r["task_id"] + ".json"))
            for r in rows
            if r["size"] and r["sample_selected"]
        }
        summary = build(rows, contracts, seal, args.out)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
