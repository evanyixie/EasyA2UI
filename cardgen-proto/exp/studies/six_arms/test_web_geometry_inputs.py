from dataclasses import replace

import pytest
from web_geometry_inputs import GeometryInput, artifact_path, digest


def test_reads_crlf_bytes_and_rejects_cross_checkpoint_substitution(tmp_path):
    folder = tmp_path / "arm"
    folder.mkdir()
    raw = b"{}\r\n{}\r\n"
    sha = digest(raw)
    path = folder / "first_native.a2ui.jsonl"
    path.write_bytes(raw)
    obs = {
        "artifact_sha256": sha,
        "provenance": {"artifact_ref": "arm/first_native.a2ui.jsonl"},
    }
    run = {"first_native": {"sha256": sha, "text": raw.decode()}}
    assert artifact_path(tmp_path, folder, "first_native", obs, run) == path
    obs["provenance"]["artifact_ref"] = "arm/final_native.a2ui.jsonl"
    with pytest.raises(ValueError, match="different artifacts"):
        artifact_path(tmp_path, folder, "first_native", obs, run)
    obs["provenance"]["artifact_ref"] = "arm/first_native.a2ui.jsonl"
    path.write_bytes(raw.replace(b"\r\n", b"\n"))
    with pytest.raises(ValueError, match="hash mismatch"):
        artifact_path(tmp_path, folder, "first_native", obs, run)


def test_absence_explicit_and_stale_file_rejected(tmp_path):
    obs = {"artifact_sha256": None, "provenance": {"artifact_ref": None}}
    run = {"final_native": None}
    assert artifact_path(tmp_path, tmp_path, "final_native", obs, run) is None
    (tmp_path / "final_native.a2ui.jsonl").write_bytes(b"")
    with pytest.raises(ValueError, match="absence evidence"):
        artifact_path(tmp_path, tmp_path, "final_native", obs, run)


def test_reuse_by_canvas_and_bytes_only(tmp_path):
    item = GeometryInput(
        "task",
        "family",
        "L3",
        "raw_first",
        "2x2",
        "hash",
        tmp_path / "a",
        "artifact_checks_rejected",
    )
    same = replace(
        item, task="other", checkpoint="after_common_repair", path=tmp_path / "b"
    )
    wide = replace(item, size="2x4")
    absent = replace(item, path=None, artifact_sha256=None)
    assert item.cache_key == same.cache_key != wide.cache_key
    assert item.viewport == (150, 150) and wide.viewport == (300, 150)
    assert absent.cache_key is None
