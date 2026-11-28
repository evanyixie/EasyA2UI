from pathlib import Path

import pytest
from reference_fact_sources import (
    MissingReference,
    digest,
    keyed,
    select_reference,
    summary,
)


def fixture(root, variant):
    folder = root / "report" / variant
    folder.mkdir(parents=True)
    hashes = {}
    for name in ("a2ui.jsonl", "compact.jsonl"):
        p = folder / name
        raw = (variant + name + "\r\n").encode()
        p.write_bytes(raw)
        hashes[p.relative_to(root).as_posix()] = digest(raw)
    return hashes


def test_uses_lexical_p6_primary_and_never_substitutes_another_reference(tmp_path):
    hashes = fixture(tmp_path, "r2") | fixture(tmp_path, "r1")
    record = {
        "collection": "report",
        "references": [{"reference_id": x, "path": x} for x in ("r2", "r1")],
    }
    ref = select_reference(tmp_path, hashes, record, True, False)
    assert ref.reference_id == "r1" and ref.reconstructed_input and not ref.simulated
    assert digest(ref.a2ui_bytes()) == ref.a2ui_sha256
    assert digest(ref.compact_bytes()) == ref.compact_sha256
    ref.compact_path.unlink()
    missing = select_reference(tmp_path, hashes, record, True, False)
    assert missing == MissingReference("missing_compact.jsonl")
    assert summary({"t": missing})["unavailable"] == {"missing_compact.jsonl": 1}


def test_checks_exact_bytes_again_after_loading(tmp_path):
    hashes = fixture(tmp_path, "p")
    record = {
        "collection": "report",
        "references": [{"reference_id": "first", "path": "p"}],
    }
    ref = select_reference(tmp_path, hashes, record, False, True)
    assert summary({"t": ref})["simulated_tasks_with_reference"] == 1
    ref.a2ui_path.write_bytes(ref.a2ui_bytes().replace(b"\r\n", b"\n"))
    with pytest.raises(ValueError, match="hash differs"):
        ref.a2ui_bytes()
    with pytest.raises(ValueError, match="hash differs"):
        select_reference(tmp_path, hashes, record, False, True)


def test_wrong_collection_and_duplicate_task_rejected(tmp_path):
    ref = {
        "collection": "report",
        "references": [{"reference_id": "r1", "path": str(Path("..") / "reserve")}],
    }
    with pytest.raises(ValueError, match="escapes collection"):
        select_reference(tmp_path, {}, ref, False, False)
    with pytest.raises(ValueError, match="Duplicate"):
        keyed(b'{"task":"x"}\n{"task":"x"}\n', "task")
