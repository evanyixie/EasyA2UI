import re
import subprocess
import zipfile

import build
import pytest


def test_blind_material_stays_out_of_release(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    study = tmp_path / build.STUDIES
    study.mkdir(parents=True)
    source = study / "method.py"
    source.write_text("pass\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "--", source.relative_to(tmp_path)], check=True)
    (study / "private-review.html").write_text("private", encoding="utf-8")
    (study / "blind-map.json").write_text("{}", encoding="utf-8")
    for name in (
        "paper/data/heldout/answer.json",
        "paper/out/tables/feedback.json",
        (build.STUDIES / "unsealed/score.private.json").as_posix(),
    ):
        private = tmp_path / name
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_text("private", encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp_path), "add", "--", name], check=True)
    monkeypatch.setattr(build, "REPO", tmp_path)
    assert [p for p, _ in build.collect()] == [source]


def test_check_and_build_require_registered_report_links(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    monkeypatch.setattr(build, "REPO", tmp_path)
    archive = tmp_path / "old.zip"
    monkeypatch.setattr(build, "OUT", archive)
    archive.write_bytes(b"previous release")
    study = build.STUDIES / "six_arms"
    for name in (*build.PUBLIC_FILES, study / "study.py", study / "fixtures/synthetic.json"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
    method = study / "audit.py"
    (tmp_path / build.REPORTS[1]).write_text(
        f"[复算](../../{method.as_posix()})\n", encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(tmp_path), "add", "--", "paper", str(study)], check=True)
    (tmp_path / method).write_text("pass\n", encoding="utf-8")
    assert build.main(["--check"]) == 1
    with pytest.raises(ValueError, match="audit.py"):
        build.build()
    assert archive.read_bytes() == b"previous release"
    subprocess.run(["git", "-C", str(tmp_path), "add", "--", str(method)], check=True)
    assert build.main(["--check"]) == 0
    with zipfile.ZipFile(build.build(anonymous=True)) as packed:
        assert packed.testzip() is None
        assert method.as_posix() in packed.namelist()
        assert all(name in packed.namelist() for name in build.PUBLIC_FILES)
        readme = packed.read("README.md").decode("utf-8")
        assert readme.startswith("# 卡片生成六档实验\n")
        assert set(re.findall(r"\]\(([^)]+)\)", readme)) == {*build.TABLES, *build.REPORTS, *build.FIGURES}
