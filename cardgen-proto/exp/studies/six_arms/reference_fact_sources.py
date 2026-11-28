"""Locate the sealed primary reference for each formal request, without reading generated cards or ratings.

The frozen report roster and answer index determine membership. As in the P6
packet builder, choose the lexicographically first reference_id before opening
any asset. Never promote another variant if the chosen reference is missing.
"""

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from six_arms.fixed_content_repeats import FORMAL_PLAN, canonical, check, digest
from six_arms.paired_delivery_bounds import ROSTER

OWNER = "layout_comparison_paper_candidate_v1"
SOURCE = "layout_comparison_pr798_96390f9"
OWNER_MANIFEST = "653f901514550ec90127b66f6ffa2002f240d99b1f1ef6ab8531fd563bf8815a"
SOURCE_MANIFEST = "932821b33cc7b976b214d797841c23516e985e9e116752f802cf516dd74b4dc6"


def checked(path, sha):
    data = path.read_bytes()
    check(digest(data) == sha, "Sealed reference evidence hash differs")
    return data


@dataclass(frozen=True)
class Reference:
    reference_id: str
    a2ui_path: Path
    a2ui_sha256: str
    compact_path: Path
    compact_sha256: str
    reconstructed_input: bool
    simulated: bool

    def a2ui_bytes(self):
        return checked(self.a2ui_path, self.a2ui_sha256)

    def compact_bytes(self):
        return checked(self.compact_path, self.compact_sha256)


@dataclass(frozen=True)
class MissingReference:
    reason: str


def select_reference(root, manifest, record, reconstructed, simulated):
    choices = record["references"]
    if not choices:
        return MissingReference("no_registered_reference")
    ids = [r["reference_id"] for r in choices]
    check(
        all(isinstance(i, str) and i for i in ids) and len(set(ids)) == len(ids),
        "Ambiguous reference IDs",
    )
    primary = min(choices, key=lambda r: r["reference_id"])
    folder = (root / record["collection"] / primary["path"]).resolve()
    check(
        folder.is_relative_to((root / record["collection"]).resolve()),
        "Reference escapes collection",
    )
    files = []
    for name in ("a2ui.jsonl", "compact.jsonl"):
        path = (folder / name).resolve()
        check(path.parent == folder, "Reference file escapes its chosen directory")
        sha = manifest.get(path.relative_to(root).as_posix())
        if sha is None:
            return MissingReference("unregistered_" + name)
        if not path.is_file():
            return MissingReference("missing_" + name)
        checked(path, sha)
        files.extend((path, sha))
    return Reference(primary["reference_id"], *files, reconstructed, simulated)


def keyed(data, key, collection=None):
    rows = [json.loads(line) for line in data.splitlines()]
    if collection is not None:
        rows = [r for r in rows if r["collection"] == collection]
    index = {r[key]: r for r in rows}
    check(len(rows) == len(index), "Duplicate key in sealed index")
    return index


def load_references(batch, vault):
    """Return a private task -> Reference | MissingReference mapping. vault is the common custodian root."""
    batch, vault = Path(batch).resolve(), Path(vault).resolve()
    owner, root = vault / OWNER, vault / SOURCE
    owner_hashes = json.loads(checked(owner / "manifest.json", OWNER_MANIFEST))[
        "outputs"
    ]
    hashes = json.loads(checked(root / "manifest.json", SOURCE_MANIFEST))["outputs"]
    source = json.loads(checked(owner / "source.json", owner_hashes["source.json"]))
    check(
        PureWindowsPath(source["private_reference_root"]).name == SOURCE,
        "Unregistered reference release",
    )
    report = keyed(
        checked(owner / "answer_index.jsonl", owner_hashes["answer_index.jsonl"]),
        "task_id",
        "report",
    )
    originals = keyed(
        checked(root / "answer_index.jsonl", hashes["answer_index.jsonl"]),
        "task_id",
        "report",
    )
    families = keyed(
        checked(owner / "report_families.jsonl", owner_hashes["report_families.jsonl"]),
        "task_id",
    )
    roster = keyed(checked(batch / "analysis/roster.jsonl", ROSTER), "task_id")
    plan = json.loads(checked(batch / "live/plan.json", FORMAL_PLAN))
    cases = plan["assignment"]["cases"]
    check(
        len(cases) == len(roster) == 219
        and {c["id"] for c in cases}
        == report.keys()
        == families.keys()
        == roster.keys(),
        "Formal report roster mismatch",
    )
    result = {}
    for task, r in roster.items():
        check(
            r["family"] == families[task]["family_id"]
            and type(r["included_in_217_sensitivity"]) is bool,
            "Formal task family or reconstruction status mismatch",
        )
        check(
            report[task] == originals.get(task),
            "Candidate and source reference registrations disagree",
        )
        result[task] = select_reference(
            root,
            hashes,
            report[task],
            not r["included_in_217_sensitivity"],
            task in source["simulated_parents"],
        )
    return result


def summary(references):
    present = {task: r for task, r in references.items() if isinstance(r, Reference)}
    return {
        "formal_tasks": len(references),
        "verified_a2ui_and_compact": len(present),
        "reconstructed_inputs_with_reference": sum(
            r.reconstructed_input for r in present.values()
        ),
        "simulated_tasks_with_reference": sum(r.simulated for r in present.values()),
        "unavailable": dict(
            Counter(
                r.reason for r in references.values() if isinstance(r, MissingReference)
            )
        ),
        "mapping_sha256": digest(
            canonical(
                sorted(
                    (task, r.reference_id, r.a2ui_sha256, r.compact_sha256)
                    for task, r in present.items()
                )
            )
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-root", required=True, type=Path)
    parser.add_argument("--vault", required=True, type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            summary(load_references(args.formal_root, args.vault)), sort_keys=True
        )
    )
