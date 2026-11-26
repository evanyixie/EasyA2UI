"""冻结本地可复验的实现和队列；只读受管理的元信息，不复制任何参考卡或模型配置。"""

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
        newline="\n",
    )


def lock_folder(staging, destination):
    if destination.exists():

        def files(folder):
            return {
                p.relative_to(folder): sha(p.read_bytes())
                for p in folder.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts
            }

        if files(destination) != files(staging):
            raise ValueError(f"已冻结的目录内容不同，须另建版本: {destination}")
        return
    staging.rename(destination)


def row_file(path, rows):
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in rows
        ),
        encoding="utf8",
        newline="\n",
    )


def make_queue(input_path, mapping, destination):
    raw_input = input_path.read_bytes()
    rows = [(json.loads(line), line) for line in raw_input.splitlines()]
    if not rows or len({r["task_id"] for r, _ in rows}) != len(rows):
        raise ValueError("空队列或重复编号")
    if set(mapping) != {r["task_id"] for r, _ in rows} or not all(
        isinstance(value, str) and value for value in mapping.values()
    ):
        raise ValueError("队列与冻结家族登记不匹配")
    assigned = {}
    for size in sorted({r["size"] for r, _ in rows}):
        ids = [r["task_id"] for r, _ in rows if r["size"] == size]
        ids.sort(key=lambda k: sha(("genui-paper-arms-20261124:" + k).encode()))
        for idx, tid in enumerate(ids):
            assigned[tid] = "AB" if idx % 2 == 0 else "BA"
    ordered = sorted(
        rows,
        key=lambda item: sha(
            ("genui-paper-sequence-20261124:" + item[0]["task_id"]).encode()
        ),
    )
    roster, schedule, missing = [], [], []
    for n, (item, raw) in enumerate(ordered, 1):
        tid = item["task_id"]
        fam = mapping[tid]
        roster.append({"task_id": tid, "family_id": fam})
        schedule.append(
            {
                "n": n,
                "task_id": tid,
                "input_line_sha256": sha(raw),
                "execute": assigned[tid],
            }
        )
        missing.append(
            {
                "task_id": tid,
                "A": "missing",
                "B": "missing",
                "missing_reason": "未执行/未验收的空模板；须按实际记录回填。",
            }
        )
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        staged = Path(tmp) / "queue"
        staged.mkdir()
        row_file(staged / "roster.jsonl", roster)
        row_file(staged / "order.jsonl", schedule)
        row_file(staged / "unfilled_decisions.jsonl", missing)
        dump(
            staged / "queue.json",
            {
                "input_sha256": sha(raw_input),
                "n": len(schedule),
                "families": len({r["family_id"] for r in roster}),
                "order_counts": dict(Counter(r["execute"] for r in schedule)),
                "repeat_primary": 1,
                "arm_order_not_visual_blinding": (
                    "运行顺序不揭示盲评的左右位置，后者由独立管理员另行随机。"
                ),
            },
        )
        lock_folder(staged, destination)
    print(destination, len(schedule))
