"""Verify a sealed five-card alarm-navigation follow-up offline; publish aggregate counts only."""

import argparse
import json
import re
import sys
from datetime import datetime
from io import BytesIO
from itertools import pairwise
from pathlib import Path

from PIL import Image

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from six_arms import native_text_audit as native
from six_arms import paired_delivery_bounds as bounds
from six_arms.fixed_content_repeats import FORMAL_PLAN, canonical, check, digest
from six_arms.fixed_content_sampling import REQUEST_INDEX_SHA
from six_arms.native_font_observability import MANIFEST, MANIFEST_SHA256
from six_arms.technical_yield import read_lines

ARMS = ("L2", "L3", "L4", "L5", "L6")
DIR = "followup_evidence_20261128/alarm_tab_explicit_open_20261128"
TABLE = Path(__file__).resolve().parents[4] / "paper/out/tables/formal_alarm_tab.json"
QUEUE = "c59abaa95f4ed2d819a1418eb0d0fd64d87f436322d871300231f909c11cf44e"
DOSSIER = "fc753f995cb94ca22f7a989b7b330ebe029aab05bacecc9486996421fb877cbb"
PRIOR = "5febb1656fd86838b1bd2369cd2fec5bbee8627970a4338df913886d82e3fe62"
BATTERY = "9f4151fbb0048ff972b273750bf7ffab61289bc1558062f1db56151e1618d305"
FILES = (
    "action_probe.json",
    "tap-intent.private.json",
    "trace.private.json",
    "host_tree.json",
    "host-markers.private.log",
    "screen.jpeg",
    "card.png",
    "received-input.jsonl",
)
CLOCK = "com.huawei.hmos.clock"
TARGET = {
    "call": "clickToDeeplink",
    "args": {
        "bundleName": CLOCK,
        "abilityName": CLOCK + ".phone",
        "intentName": "Clock",
        "uri": "",
        "parameters": {"tabActive": "ALARM_CLOCK_TAB"},
    },
}


def crop_box(terminal):
    x = terminal["cropPx"]
    return (x["left"], x["top"], x["left"] + x["width"], x["top"] + x["height"])


def hit_center(raw_tree, target, crop):
    controls = native.control_index(json.loads(raw_tree), crop)
    matches = controls.get(target["id"], [])
    if len(matches) != 1:
        return None
    node = matches[0]
    if (
        node["type"] != "Button"
        or node["text"] != target["label"]
        or any(node.get(k) != "true" for k in ("visible", "clickable", "enabled"))
    ):
        return None
    for field in ("origBounds", "bounds"):
        box = native.box(node.get(field))
        if not box or not (
            crop[0] <= box[0] < box[2] <= crop[2]
            and crop[1] <= box[1] < box[3] <= crop[3]
        ):
            return None
    return [(box[0] + box[2]) // 2, (box[1] + box[3]) // 2]


def dispatch_evidence(lines, timing, target_id):
    """Only the host PID within the tap window may establish this ordered event pair."""
    clicked = False
    for line in lines:
        stamp = re.match(r"^\s*(\d{10})\.(\d{3})\s+(\d+)\s", line)
        check(
            stamp is not None and stamp[3] == timing["host_pid"],
            "Wrong host log process",
        )
        when = 1000 * int(stamp[1]) + int(stamp[2])
        check(
            timing["device_before_ms"] <= when <= timing["sample_end_ms"],
            "Host log outside tap window",
        )
        if line.rstrip().endswith(
            f"onClick triggered: componentId={target_id}, handlers=1"
        ):
            clicked = True
        if clicked and "local function is not registered: clickToDeeplink" in line:
            return True
    return False


def classify_focus(before, polls, host_pid):
    check(
        before["is_host"]
        and not before["is_clock"]
        and before["focus_pid"] == host_pid,
        "Host not established before tap",
    )
    stamps = [datetime.fromisoformat(p["utc"]) for p in polls]
    check(
        all(x < y for x, y in pairwise(stamps)),
        "Focus samples out of order",
    )
    if any(p["is_clock"] and not p["is_host"] for p in polls):
        return "clock_foreground"
    if len(polls) == 4 and all(
        p["is_host"]
        and not p["is_clock"]
        and p["focus_pid"] == host_pid
        and p["window_id"] == before["window_id"]
        for p in polls
    ):
        return "host_only"
    return "unknown"


def original_request(root, task, proof, request_index, originals_root):
    [indexed] = [
        r for r in read_lines(request_index, REQUEST_INDEX_SHA) if r["task_id"] == task
    ]
    path = (
        originals_root / indexed["source_file"]
        if originals_root
        else Path(indexed["source_local_path"])
    )
    check(
        indexed["source_file_sha256"] == proof["raw_request_sha256"],
        "Wrong original request",
    )
    original = json.loads(bounds.verified(path, indexed["source_file_sha256"]))
    packaged = json.loads(
        bounds.verified(
            root / "queue/package/requests" / (digest(task.encode()) + ".json"),
            proof["packaged_request_sha256"],
        )
    )
    query = packaged["originalQuery"] or packaged["userQuery"]
    check(
        packaged["_custody_original_envelope_sha256"] == proof["raw_request_sha256"]
        and original["content"]["userQuery"]
        == packaged["userQuery"]
        == original["userQuery"]
        and original["utterance"]["original"] == packaged["originalQuery"]
        and "打开闹钟应用" in query,
        "Explicit requested launch missing",
    )
    check(
        original["content"]["candidateEventCandidates"]
        == original["candidateEventCandidates"]
        == packaged["candidateEventCandidates"]
        and TARGET in [e.get("action") for e in packaged["candidateEventCandidates"]],
        "Registered target differs",
    )


def archived(root, first, final):
    sha = final["artifact_sha256"]
    p = final["provenance"]
    check(
        first["artifact_sha256"] == sha == final["original_artifact_sha256"]
        and first["input_sha256"] == final["input_sha256"]
        and all(
            first["provenance"][key] == p[key]
            for key in (
                "raw_request_sha256",
                "packaged_request_sha256",
                "registry_sha256",
                "capture",
                "outcome_sha256",
            )
        ),
        "Checkpoints do not share a signed artifact and capture",
    )
    raw = bounds.verified(root / p["artifact_ref"], sha)
    check(
        bounds.verified(root / first["provenance"]["artifact_ref"], sha) == raw,
        "First artifact changed",
    )
    controls = [
        n
        for line in raw.splitlines()
        for n in json.loads(line).get("updateComponents", {}).get("components", [])
        if n.get("onClick")
    ]
    # The tested card has one handler. A new competing action must never pass this replay.
    check(
        len(controls) == 1
        and controls[0].get("component") == "Button"
        and controls[0]["onClick"] == [TARGET],
        "Not the registered single-button source",
    )
    cap = p["capture"]
    receipt_path = root / cap["proof_ref"]
    rec = json.loads(bounds.verified(receipt_path, cap["proof_sha256"]))
    check(
        rec["input_sha256"] == rec["input_return_sha256"] == sha
        and rec["screenshot_sha256"] == cap["screenshot_sha256"],
        "Archive binding mismatch",
    )
    bounds.verified(receipt_path.parent / "received-input.jsonl", sha)
    png = bounds.verified(root / cap["screenshot_ref"], cap["screenshot_sha256"])
    return controls[0], rec, png, receipt_path.parent


def verify_tap(folder, case, archive, original):
    target, reference, png, source_folder = original
    obs = json.loads((folder / "action_probe.json").read_bytes())
    trace = json.loads((folder / "trace.private.json").read_bytes())
    intent = json.loads((folder / "tap-intent.private.json").read_bytes())
    check(
        all(
            obs[k] == case[k]
            for k in (
                "arm",
                "task",
                "sha256",
                "payload",
                "target_id",
                "target_label",
                "other_node_ids",
                "vp",
                "archive_png",
                "archive_tree",
                "capture_receipt",
                "request_sha256",
            )
        )
        and case["payload"] == TARGET
        and not case["other_node_ids"]
        and case["target_id"] == target["id"]
        and case["target_label"] == target["label"]
        and case["sha256"] == archive["artifact_sha256"]
        and archive["provenance"]["capture"]["proof_sha256"] == case["capture_receipt"]
        and case["request_sha256"] == archive["provenance"]["packaged_request_sha256"],
        "Tap/registration/archived source mismatch",
    )
    check(
        case["vp"]
        == reference["vp"]
        == [obs["terminal"]["widthVp"], obs["terminal"]["heightVp"]]
        and obs["terminal"]["runId"] == obs["run_id"]
        and obs["terminal"]["state"] in {"READY", "READY_WITH_WARNINGS"}
        and obs["input_return_sha256"] == case["sha256"]
        and obs["screenshot_sha256"] == case["archive_png"] == digest(png),
        "Host execution identity differs",
    )
    bounds.verified(folder / "received-input.jsonl", case["sha256"])
    bounds.verified(folder / "card.png", case["archive_png"])
    crop = crop_box(obs["terminal"])
    check(crop == crop_box(reference["terminal"]), "Canvas differs")
    with (
        Image.open(BytesIO(png)) as card,
        Image.open(
            BytesIO(bounds.verified(folder / "screen.jpeg", obs["full_sha256"]))
        ) as screen,
    ):
        check(
            card.size == (crop[2] - crop[0], crop[3] - crop[1])
            and screen.crop(crop).convert("RGB").tobytes()
            == card.convert("RGB").tobytes(),
            "Live crop differs from original",
        )
    original_center = hit_center(
        bounds.verified(source_folder / "native-layout.json", case["archive_tree"]),
        target,
        crop,
    )
    live_center = hit_center((folder / "host_tree.json").read_bytes(), target, crop)
    check(
        original_center == live_center == intent["coordinates"]
        and live_center is not None,
        "Tap does not hit the same eligible native control",
    )
    timing = trace["timing"]
    check(
        trace["source_probe_sha256"]
        == digest((folder / "action_probe.json").read_bytes())
        and all(intent[k] == timing[k] for k in intent)
        and timing["device_before_ms"]
        <= timing["device_after_ms"]
        <= timing["sample_end_ms"]
        and trace["intent"]
        and trace["tap_return_observed"]
        and obs["clicks"] == 1
        and obs["tap_return"].strip() == "No Error"
        and obs["foreground"]["bundle_pid"] == intent["host_pid"],
        "Click receipt differs",
    )
    lines = (
        bounds.verified(folder / "host-markers.private.log", trace["host_log_sha256"])
        .decode("utf8")
        .splitlines()
    )
    dispatch = dispatch_evidence(lines, timing, target["id"])
    focus = classify_focus(obs["before"], obs["observations"], intent["host_pid"])
    check(
        dispatch
        and trace["host_onclick_for_target"]
        and trace["host_unregistered_dispatch"]
        and focus == "host_only"
        and not obs["destination_observed"]
        and trace["result"] == "host_remained_at_four_polls",
        "Original navigation evidence differs",
    )
    return obs["run_id"], len(obs["observations"])


def audit(formal_root, *, request_index=None, originals_root=None, evaluator=None):
    root = Path(formal_root)
    folder = root / DIR
    queue = json.loads(bounds.verified(folder / "queue.private.json", QUEUE))
    bounds.verified(folder / "probe.py", queue["script_sha256"])
    cases = queue["cases"]
    check(
        tuple(q["arm"] for q in cases) == ARMS and len({q["task"] for q in cases}) == 1,
        "Wrong registered roster",
    )
    task = cases[0]["task"]
    hashes = [
        [digest((folder / q["arm"] / name).read_bytes()) for name in FILES]
        for q in cases
    ]
    check(digest(canonical(hashes)) == DOSSIER, "Sealed physical trace bundle differs")
    old_grid, grid_sha = bounds.GRIDS["original"]
    grid = {
        (r["arm"], r["checkpoint"]): r
        for r in read_lines(root / "followup_evidence_20261128" / old_grid, grid_sha)
        if r["task_id"] == task
    }
    original_request(
        root,
        task,
        grid["L2", "raw_first"]["provenance"],
        request_index
        or root.parent / "paper_source219_verification_20261126/requests.private.jsonl",
        originals_root,
    )
    bounds.verified(root / "live/plan.json", FORMAL_PLAN)
    assess = bounds.frozen_assess(evaluator)
    archived_trees = {
        (r["arm"], r["checkpoint"]): r["tree_sha256"]
        for r in read_lines(root / MANIFEST, MANIFEST_SHA256)
        if r["task"] == task
    }
    first, final = (grid["L1", p] for p in bounds.POINTS)
    target, rec, _, parent = archived(root, first, final)
    excluded = (
        hit_center(
            bounds.verified(
                parent / "native-layout.json",
                archived_trees["L1", "after_common_repair"],
            ),
            target,
            crop_box(rec["terminal"]),
        )
        is None
    )
    check(excluded, "Previously excluded sixth card became eligible")
    runs = set()
    n_polls = 0
    for q in cases:
        arm = q["arm"]
        first, final = (grid[arm, p] for p in bounds.POINTS)
        check(
            all(archived_trees[arm, p] == q["archive_tree"] for p in bounds.POINTS),
            "Archived tree differs",
        )
        check(
            all(assess(r)["primary"]["status"] == "unknown" for r in (first, final)),
            "Seat previously decided",
        )
        ident, polls = verify_tap(folder / arm, q, final, archived(root, first, final))
        check(ident not in runs, "Reused physical tap")
        runs.add(ident)
        n_polls += polls
    clock = json.loads(
        bounds.verified(
            root / "objective_quality_20261128/clock_query_link.private.json",
            bounds.CLOCK_INTENTS,
        )
    )
    battery = json.loads(
        bounds.verified(
            root / "failure_casebook_t16_20261128/private_index.json", BATTERY
        )
    )
    check(
        not any(r["task"] == task and r["scope"] == "explicit_open" for r in clock)
        and all(r["task"] != task for r in battery["missing_action"]["seats"]),
        "Overlaps prior explicit action study",
    )
    prior = json.loads(
        bounds.verified(
            root / "explicit_action_delivery_sensitivity_20261128/summary.private.json",
            PRIOR,
        )
    )
    [member] = [
        r
        for r in read_lines(root / "analysis/roster.jsonl", bounds.ROSTER)
        if r["task_id"] == task
    ]
    check(member["included_in_217_sensitivity"], "Unexpected sensitivity cohort")
    comparisons = {}
    for label, variants in prior["cohorts_and_checkpoints"].items():
        before = variants["explicit_clock_and_battery_access"]
        n = int(label.split("/")[0])
        after = before["known_fail"] + len(runs)
        new_bounds = {}
        for name in ("L5-L4", "L5-L6"):
            was = before["differences"][name]["unrestricted"]
            # In this previously unknown/unknown task, failure/failure contributes exactly zero.
            delta_old = bounds.interval("unknown", "unknown")
            new_bounds[name] = [v - d for v, d in zip(was, delta_old, strict=True)]
        pending = sum(x["unknown"] for x in before["arms"].values()) - len(runs)
        passed = sum(x["pass"] for x in before["arms"].values())
        check(after + pending + passed == n * 6, "Closed cohort accounting differs")
        comparisons[label] = {
            "known_fail": after,
            "unknown": pending,
            "known_pass": passed,
            "paired_net_bounds": new_bounds,
        }
    return {
        "schema": "formal_alarm_tab.v1",
        "source_sha256": {
            "queue": QUEUE,
            "physical_evidence_bundle": DOSSIER,
            "prior_action_sensitivity": PRIOR,
        },
        "distinct_tasks": 1,
        "assigned_arms": list(ARMS),
        "excluded_without_tap": 1,
        "physical_taps": len(runs),
        "matched_original_images": len(runs),
        "observed_target_onclick_then_unregistered_dispatch": len(runs),
        "post_tap_focus_samples": n_polls,
        "clock_foreground_at_samples": 0,
        "alarm_tab_observed": 0,
        "target": "The request specified opening Clock. Its handler additionally specified the alarm tab.",
        "scope": "Same registered host. No alarm contents or in-app screenshot were collected. "
        "Five physical taps cover both checkpoints. The original formal endpoint is unchanged.",
        "posthoc_explicit_action_sensitivity": comparisons,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_root", type=Path)
    parser.add_argument(
        "--request-index", type=Path, help="Relocated sealed original-request index"
    )
    parser.add_argument(
        "--originals-root", type=Path, help="Relocated original request checkout"
    )
    parser.add_argument("--evaluator", type=Path, help="Relocated frozen endpoint.py")
    parser.add_argument(
        "--output",
        type=Path,
        help="Write a new anonymous aggregate instead of checking the published table",
    )
    a = parser.parse_args()
    result = audit(
        a.formal_root,
        request_index=a.request_index,
        originals_root=a.originals_root,
        evaluator=a.evaluator,
    )
    if a.output:
        with a.output.open("x", encoding="utf8", newline="\n") as stream:
            stream.write(
                json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
            )
    else:
        check(result == json.loads(TABLE.read_bytes()), "Published table differs")
    print(
        f"Verified {result['physical_taps']} physical taps and {result['post_tap_focus_samples']} foreground samples"
    )


if __name__ == "__main__":
    main()
