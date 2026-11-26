import subprocess

import build


def test_blind_material_stays_out_of_release(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    study = tmp_path / build.STUDIES
    study.mkdir(parents=True)
    source = study / "method.py"
    source.write_text("pass\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "--", source.relative_to(tmp_path)], check=True)
    (study / "private-review.html").write_text("private", encoding="utf-8")
    (study / "blind-map.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(build, "REPO", tmp_path)
    assert [p for p, _ in build.collect()] == [source]
