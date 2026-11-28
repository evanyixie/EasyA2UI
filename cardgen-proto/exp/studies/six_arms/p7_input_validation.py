"""Check sealed P7 original ballots and adjudications before issuing business forms.

Run as a custodian with the frozen business.py, the signed lock and its SHA-256.
Optional --prepare NEW_PRIVATE_DIRECTORY issues forms after successful checks.
Only aggregate counts are returned.
"""

import argparse
import hashlib
import json
import runpy
import sys
from pathlib import Path

# The original dataset tool is also directly executable from its own directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dataset"))
from human_review import checked_p7_answer, checked_submission

COLLECTOR_SHA = "d700908c8239cc8e860121f92b1d8cc6b3e6af51e3246c2aafa1a425186277e6"
FORM_SHA = "31d630ef090349c4ebf19ec7e0d9219b3db0a9c1ba5e83dc1e949ce74f2efda0"


def _preflight(collector, lock_path, lock_sha):
    # The frozen collector verifies roles, times, questionnaire versions, source
    # hashes and the exact set of disagreements. Retain its independent checks.
    cases, _ = collector["load_lock"](lock_path, lock_sha)
    read_verified = collector["verified"]
    parse = collector["parse"]
    lock = parse(read_verified(lock_path, lock_sha))
    original_count = 0
    for role in collector["ROLES"]:
        ref = lock["returns"][role]
        ballot = parse(read_verified(lock_path.parent / ref["file"], ref["sha256"]))
        _, validated = checked_submission(collector["P7"], role, ballot)
        original_count += len(validated)
    for task, resolution in lock["disagreements"].items():
        checked_p7_answer(resolution["decision"], cases[task])
    return {
        "tasks": len(cases),
        "original_selections": original_count,
        "adjudications": len(lock["disagreements"]),
    }


def validate(collector_path, lock_path, lock_sha, *, prepare=None):
    if hashlib.sha256(collector_path.read_bytes()).hexdigest() != COLLECTOR_SHA:
        raise ValueError("Frozen business collector digest mismatch")
    collector = runpy.run_path(str(collector_path))
    result = _preflight(collector, lock_path, lock_sha)
    if prepare is not None:
        collector["verified"](collector_path.with_name("form.html"), FORM_SHA)
        collector["prepare"](lock_path, lock_sha, prepare)
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("collector", type=Path)
    cli.add_argument("lock", type=Path)
    cli.add_argument("lock_sha256")
    cli.add_argument("--prepare", type=Path, metavar="NEW_PRIVATE_DIRECTORY")
    args = cli.parse_args()
    print(
        json.dumps(
            validate(args.collector, args.lock, args.lock_sha256, prepare=args.prepare)
        )
    )
