"""Reconstruct the exploratory 12-case draw from frozen custodian inputs, offline.

Run with --formal-root FORMAL --request-index REQUESTS_JSONL --check SELECTION_JSON.
If the raw request archive has moved, add --originals-root DIR containing debug_tools/.
Prints only population sizes, aggregate strata and the sealed selection checksum.
"""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

SEED = "EasyA2UI/fixed-content/structure-repeat/v1"
SIZES = ("2x2", "2x4")
BANDS = ("low", "middle", "high")
SELECTION_SHA = "819a5f79679ca24caa62137b8c5c9a647c94319e367e0ed7a25ed50405baf444"
REQUEST_INDEX_SHA = "4c40977e54fff56bdea35b0179cc4adc2da5915bcb5950516f0610fb6686bf44"
ROSTER = "analysis/roster.jsonl"
PLAN = "live/plan.json"
ACCEPTED_CONTENT = "l56_focus_20261128/candidate_followup/selection.private.jsonl"
SOURCES = {
    ROSTER: "ffcecb4ce1cf0f0fb0ea9e3a43140c1b119420f619d335ad621bd2063e9a39c2",
    PLAN: "66a65da3c893fb2c0bd6ecd9feb8a09d669e95996e6692fffc635bdbe7c17d18",
    ACCEPTED_CONTENT: "5b9f57bd6fab3b3fbb0a776ec7887dbf54a4ca2090b40bd978e8408fced35147",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked_bytes(path, expected):
    data = path.read_bytes()
    require(
        digest(data) == expected, "A custodian input does not match its frozen hash"
    )
    return data


def index_unique(records, key):
    result = {}
    for row in records:
        require(row[key] not in result, "Duplicate record in source")
        result[row[key]] = row
    return result


def read_population(formal, request_index, originals_root):
    roster = index_unique(
        map(json.loads, checked_bytes(formal / ROSTER, SOURCES[ROSTER]).splitlines()),
        "task_id",
    )
    plan = json.loads(checked_bytes(formal / PLAN, SOURCES[PLAN]))
    assignments = index_unique(plan["assignment"]["cases"], "id")
    records = map(
        json.loads,
        checked_bytes(
            formal / ACCEPTED_CONTENT, SOURCES[ACCEPTED_CONTENT]
        ).splitlines(),
    )
    # Project just eligibility and accepted-content hash. No geometry, rendering or score is consulted.
    eligible = index_unique(
        ({"task": r["task"], "content_sha": r.get("content_sha")} for r in records),
        "task",
    )
    originals = index_unique(
        map(json.loads, checked_bytes(request_index, REQUEST_INDEX_SHA).splitlines()),
        "task_id",
    )
    require(
        len(roster) == 219
        and roster.keys() == assignments.keys() == eligible.keys() == originals.keys(),
        "Source populations disagree",
    )
    rows = []
    for task, entry in sorted(eligible.items()):
        content_sha = entry["content_sha"]
        if not content_sha:
            continue
        identity, assignment, original = (
            roster[task],
            assignments[task],
            originals[task],
        )
        request_sha = identity["raw_request_sha256"]
        require(
            request_sha == original["source_file_sha256"],
            "Original request identity mismatch",
        )
        source_path = (
            originals_root / original["source_file"]
            if originals_root is not None
            else Path(original["source_local_path"])
        )
        checked_bytes(source_path, request_sha)
        file_id = assignment["file_id"]
        require(file_id == digest(task.encode()), "Packaged file ID mismatch")
        request = json.loads(
            checked_bytes(
                formal / "queue/package/requests" / (file_id + ".json"),
                assignment["input_sha256"],
            )
        )
        require(
            request["_custody_original_envelope_sha256"] == request_sha,
            "Packaged request origin mismatch",
        )
        checked_bytes(
            formal / "queue/package/registry" / (file_id + ".json"),
            assignment["registry_sha256"],
        )
        folder = Path("live") / file_id / "L5"
        content_ref = folder / "calls/content/response.txt"
        raw = (formal / content_ref).read_bytes()
        content = json.loads(raw)
        require(digest(canonical(content)) == content_sha, "Accepted content mismatch")
        size = assignment["size"]
        require(content["size"] == size and size in SIZES, "Size mismatch")
        require(
            isinstance(content["items"], list) and isinstance(content["actions"], list),
            "Unknown content load",
        )
        n_items, n_actions = len(content["items"]), len(content["actions"])
        rank = digest((SEED + "\0draw\0" + request_sha).encode())
        rows.append(
            {
                "task": task,
                "qid": identity["source_case_id"],
                "family": identity["family"],
                "size": size,
                "file_id": file_id,
                "raw_request_sha256": request_sha,
                "input_sha256": assignment["input_sha256"],
                "registry_sha256": assignment["registry_sha256"],
                "content_sha256": content_sha,
                "content_response_sha256": digest(raw),
                "outcome_ref": (folder / "outcome.json").as_posix(),
                "content_response_ref": content_ref.as_posix(),
                "n_items": n_items,
                "n_actions": n_actions,
                "load": n_items + n_actions,
                "draw_rank_sha256": rank,
            }
        )
    require(
        len(rows) == len({r["raw_request_sha256"] for r in rows}) == 187,
        "Wrong eligible population",
    )
    return rows


def size_bands(rows, size):
    """Cut between distinct loads, minimizing the frozen pair of distances to tertiles."""
    bucket = defaultdict(list)
    for row in rows:
        if row["size"] == size:
            bucket[row["load"]].append(row)
    loads = sorted(bucket)
    n = sum(map(len, bucket.values()))
    best_score, best_groups = None, None
    for a, b in combinations(range(1, len(loads)), 2):
        groups = [
            [r for load in values for r in bucket[load]]
            for values in (loads[:a], loads[a:b], loads[b:])
        ]
        if any(len({r["family"] for r in group}) < 2 for group in groups):
            continue
        left, right = len(groups[0]), n - len(groups[2])
        d1, d2 = abs(3 * left - n), abs(3 * right - 2 * n)
        score = d1 + d2, max(d1, d2), left, right
        if best_score is None or score < best_score:
            best_score, best_groups = score, groups
    require(best_groups is not None, "No three eligible unsplit load bands for " + size)

    def rank(r):
        return r["draw_rank_sha256"], r["raw_request_sha256"], r["task"]

    return [
        (size, label, sorted(group, key=rank))
        for label, group in zip(BANDS, best_groups, strict=True)
    ]


def choose(cells, used=frozenset()):
    """First complete ranked assignment in fixed cell order; backtrack on family conflicts."""
    if not cells:
        return []
    _, band, ordered = cells[0]
    for left, right in combinations(range(len(ordered)), 2):
        pair = {ordered[left]["family"], ordered[right]["family"]}
        if len(pair) == 2 and not used.intersection(pair):
            rest = choose(cells[1:], used | pair)
            if rest is not None:
                return [
                    dict(ordered[i], load_band=band, within_cell_rank=i + 1)
                    for i in (left, right)
                ] + rest
    return None


def draw(rows):
    cells = [cell for size in SIZES for cell in size_bands(rows, size)]
    selected = choose(cells)
    require(
        selected is not None, "No complete assignment with globally distinct families"
    )
    strata = []
    for size, band, members in cells:
        counts = Counter(r["load"] for r in members)
        strata.append(
            {
                "size": size,
                "load_band": band,
                "min_load": min(counts),
                "max_load": max(counts),
                "population_tasks": len(members),
                "population_families": len({r["family"] for r in members}),
                "load_histogram": {
                    str(load): count for load, count in sorted(counts.items())
                },
            }
        )
    return selected, strata


def verify(formal, request_index, selection, originals_root=None):
    original = json.loads(checked_bytes(selection, SELECTION_SHA))
    rows = read_population(formal, request_index, originals_root)
    selected, strata = draw(rows)
    require(
        original["seed"] == SEED and original["source_sha256"] == SOURCES,
        "Wrong design",
    )
    require(
        original["projected_pool_sha256"] == digest(canonical(rows))
        and original["population"] == len(rows)
        and original["population_families"] == len({r["family"] for r in rows}),
        "Candidate pool mismatch",
    )
    require(
        original["strata"] == strata and original["cases"] == selected,
        "Draw differs from the sealed selection",
    )
    return {
        "population": len(rows),
        "selected": len(selected),
        "strata": strata,
        "selection_sha256": SELECTION_SHA,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--request-index", type=Path, required=True)
    parser.add_argument("--check", metavar="SEALED_SELECTION", type=Path, required=True)
    parser.add_argument("--originals-root", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            verify(
                args.formal_root, args.request_index, args.check, args.originals_root
            ),
            ensure_ascii=False,
        )
    )
