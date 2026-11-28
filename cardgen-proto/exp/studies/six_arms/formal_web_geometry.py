"""Measure sealed first/final formal artifacts with the historical Blink text-box metric."""

import argparse
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from six_arms import web_geometry_browser as browser
from six_arms.web_geometry_inputs import load_inputs
from six_arms.web_geometry_stats import build_report

ROOT = Path(__file__).resolve().parents[4]
TABLE = ROOT / "paper/out/tables/formal_web_geometry.json"
PHASES = {"raw_first": "first", "after_common_repair": "final"}


def encode(value):
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def measure_inputs(seats, measure, batch_size=32):
    """Cache only identical artifact bytes at the same requested canvas size."""
    inputs = {}
    for seat in seats:
        if seat.path is not None:
            inputs.setdefault(seat.cache_key, seat.path)
    items = sorted(inputs.items())
    observations = {}
    for start in range(0, len(items), batch_size):
        cards = []
        for (size, digest), path in items[start : start + batch_size]:
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError(
                    "Artifact changed between custody check and measurement"
                )
            cards.append({"size": size, "key": f"{size}-{digest}", "a2ui": data})
        result = measure(cards)
        if [r["key"] for r in result] != [card["key"] for card in cards]:
            raise ValueError("Browser result missing, duplicated or out of order")
        for card, row in zip(cards, result, strict=True):
            observations[card["key"]] = row
    rows = []
    for seat in seats:
        record = {
            "task": seat.task,
            "family": seat.family,
            "arm": seat.arm,
            "phase": PHASES[seat.checkpoint],
            "status": "missing",
            "artifact_sha256": seat.artifact_sha256,
        }
        if seat.path is not None:
            key = f"{seat.size}-{seat.artifact_sha256}"
            obs = observations[key]
            record["observation_key"] = key
            if obs["state"] == "measured":
                if obs["expected_text_nodes"] != obs["measured_text_nodes"]:
                    raise ValueError(
                        "Partial text-node coverage in measured observation"
                    )
                record.update(
                    status="measured",
                    text_nodes=obs["measured_text_nodes"],
                    overflow_px=obs["overflow_sum_px"],
                    above4_nodes=obs["above4_nodes"],
                )
            elif obs["state"] == "unassessed":
                record["status"] = "unsupported"
            else:
                raise ValueError("Unrecognized browser observation status")
        rows.append(record)
    return rows, observations


def run(root, edge):
    seats = load_inputs(root)
    rows, observations = measure_inputs(
        seats,
        lambda cards: browser.measure_cards(cards, edge=edge, scratch=root),
    )
    private = {"seats": rows, "observations": observations}
    report = build_report(rows)
    report["unique_artifact_canvas_pairs"] = len(observations)
    report["private_observations_sha256"] = hashlib.sha256(encode(private)).hexdigest()
    report["unique_observation_states"] = dict(
        sorted(Counter(o["state"] for o in observations.values()).items())
    )
    report["environment"] = {
        "os": platform.system(),
        "os_version": platform.version(),
        "browser_executable": Path(edge or browser.EDGE).name,
        "browser_versions": sorted(
            {o["browser_version"] for o in observations.values()}
        ),
        "renderer_blobs": sorted({o["renderer_blob"] for o in observations.values()}),
        "runtime": [
            json.loads(record)
            for record in sorted(
                {
                    json.dumps(o["browser_runtime"], sort_keys=True)
                    for o in observations.values()
                    if o.get("browser_runtime") is not None
                }
            )
        ],
    }
    report["measurement_conditions"] = (
        "Offline post-hoc replay of emitted first and final artifacts. CSS text boxes, excluding "
        "button labels, are compared with the artifact root rectangle. The viewport declared by "
        "the request is cross-checked separately. One outward edge must exceed 0.6 CSS px before "
        "rounding, and a node is over threshold if any rounded edge exceeds four CSS px. "
        "Blink flex sizing and system fonts may differ from the phone."
    )
    for phase, groups in report["by_phase_arm"].items():
        for arm, group in groups.items():
            measured = [
                observations[r["observation_key"]]
                for r in rows
                if r["arm"] == arm and r["phase"] == phase and r["status"] == "measured"
            ]
            group["declared_canvas_differs_from_request"] = sum(
                o["caller_canvas_differs"] for o in measured
            )
            group["binding_modes"] = dict(
                sorted(Counter(o["binding_mode"] for o in measured).items())
            )
            group["cards_with_horizontal_text_clipping_above4"] = sum(
                o["clipped_text_nodes"] > 0 for o in measured
            )
        for name, comparison in report["paired"][phase].items():
            left, right = name.split("_minus_")
            lookup = {
                (r["task"], r["arm"]): observations[r["observation_key"]][
                    "clipped_text_nodes"
                ]
                > 0
                for r in rows
                if r["phase"] == phase and r["status"] == "measured" and r["text_nodes"]
            }
            pairs = [
                (x, lookup[t, right])
                for (t, a), x in lookup.items()
                if a == left and (t, right) in lookup
            ]
            comparison["horizontal_text_clipping_over4"] = {
                "left_only": pairs.count((True, False)),
                "right_only": pairs.count((False, True)),
                "both": pairs.count((True, True)),
                "neither": pairs.count((False, False)),
            }
            if len(pairs) != comparison["available_both"]:
                raise ValueError("Clipping and overflow pair denominators differ")
    return report, private


def write_once(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError("Existing result differs; choose a new output path")
        return
    with path.open("xb") as f:
        f.write(data)


def compare_browsers(current, previous):
    first, second = current["observations"], previous["observations"]
    if set(first) != set(second):
        raise ValueError("Browsers did not receive the same artifact/canvas pairs")
    # Browser build identifiers differ by design. Compare the full set of recorded
    # card counts and bounds, including the explicit absence of a measurement.
    fields = (
        "state",
        "reason",
        "expected_text_nodes",
        "measured_text_nodes",
        "root_width_px",
        "root_height_px",
        *browser.METRICS,
    )
    return {
        "same": sum(
            all(a.get(k) == second[key].get(k) for k in fields)
            for key, a in first.items()
        ),
        "assigned": len(first),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("formal_root", type=Path)
    p.add_argument(
        "--edge", type=Path, help="Optional path to the local Edge executable"
    )
    p.add_argument(
        "--output", type=Path, help="Write anonymous aggregates, default verifies"
    )
    p.add_argument(
        "--private-observations", type=Path, help="Optional custody-only output"
    )
    p.add_argument(
        "--compare-private-observations",
        type=Path,
        help="Optional independent browser replay covering the same artifacts",
    )
    args = p.parse_args()
    if (
        args.private_observations
        and not args.private_observations.resolve().is_relative_to(
            args.formal_root.resolve()
        )
    ):
        p.error("Write per-case measurements only under the formal custody directory")
    report, private = run(args.formal_root, args.edge)
    if args.compare_private_observations:
        print(
            "Cross-browser comparison:",
            compare_browsers(
                private, json.loads(args.compare_private_observations.read_bytes())
            ),
        )
    if args.private_observations:
        write_once(args.private_observations, encode(private))
    if args.output:
        write_once(args.output, encode(report))
    elif json.loads(TABLE.read_bytes()) != report:
        raise ValueError("Published A2 results differ from this browser replay")
    print(
        "Verified",
        report["unique_artifact_canvas_pairs"],
        "distinct artifact/canvas pairs",
    )
