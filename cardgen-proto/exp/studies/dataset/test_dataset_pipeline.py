"""合成数据跨阶段验证。所有请求、评审包和派生文件都在临时目录内生成。"""

import copy
import json
import sys

import pytest

from dataset_tool import main, make_drafts
from freeze_candidates import select_candidates
from human_review import generate, score


def save(path, obj, *, lines=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        "".join(json.dumps(v, ensure_ascii=False) + "\n" for v in obj)
        if lines
        else json.dumps(obj, ensure_ascii=False)
    )
    path.write_text(data, encoding="utf8")
    return path


def test_cardspec_to_frozen_queue(tmp_path, monkeypatch):
    def invoke(stage, **kwargs):
        out = tmp_path / (stage + ".json")
        args = ["dataset_tool.py", stage, "--out", str(out)]
        for name, path in kwargs.items():
            args.extend(["--" + name.replace("_", "-"), str(path)])
        monkeypatch.setattr(sys, "argv", args)
        main()
        return json.loads(out.read_text("utf8")) if out.is_file() else out

    ident = save(tmp_path / "id", {"case_id": "SYNTH-A", "size": "2x2"})
    req = save(
        tmp_path / "req",
        {"content": {"size": "2x2", "userQuery": "显示样本读数并打开详情"}},
    )
    handler = {"call": "openSynthetic", "args": {"target": "object-a"}}
    surface = {"surfaceId": "s"}
    components = [
        {"id": "r", "component": "Column", "children": ["v", "a"]},
        {"id": "v", "component": "Text", "content": {"path": "/value"}},
        {"id": "a", "component": "Button", "label": "查看", "onClick": [handler]},
    ]
    msgs = [
        {"version": "v0.9", "createSurface": surface},
        {
            "version": "v0.9",
            "updateComponents": {**surface, "root": "r", "components": components},
        },
        {
            "version": "v0.9",
            "updateDataModel": {**surface, "path": "/", "value": {"value": 0}},
        },
    ]
    a2ui = save(tmp_path / "a2ui", msgs)
    compact_rows = [["r", "Synthetic", {}], ["/value", 0]]
    compact = save(tmp_path / "compact", compact_rows, lines=True)
    manifest = invoke(
        "freeze",
        root=tmp_path,
        files=save(tmp_path / "filelist", ["a2ui", "req", "compact"]),
    )
    assert all("sha256" in r for r in manifest["files"].values())
    assert len(manifest["tree_sha256"]) == 64
    inspected = invoke("inspect", request=req, a2ui=a2ui)
    assert all(c["status"] == "pass" for c in inspected["checks"])
    evidence = invoke("evidence", identity=ident, compact=compact, a2ui=a2ui)
    assert (
        evidence["A"] == 1 and evidence["texts"][0]["bindings"][0]["sample_value"] == 0
    )
    ann = {
        "case_id": "SYNTH-A",
        "items": [{"name": "合成数值", "n": 1, "text_ids": ["v"]}],
        "excluded": [],
        "A": 1,
        "D": 1,
    }
    info = invoke(
        "extract",
        evidence=tmp_path / "evidence.json",
        a2ui=a2ui,
        annotation=save(tmp_path / "annotation", ann),
    )
    assert info["actions"][0]["handlers"] == [handler]
    packet = {
        **info,
        "task_id": "SYNTH-TA",
        "original_request": {"userQuery": "样本读数"},
        "private_source_evidence": {"original_graphic_evidence": []},
        "private_original_compacts": [{"rows": compact_rows}],
    }
    review = {
        "case_id": "SYNTH-A",
        "status": "clear_ai",
        "entities": [{"id": "E", "name": "样本"}],
        "atoms": [
            {
                "parent": "fact_1",
                "entity": "E",
                "role": "primary",
                "take": {"path": "/value"},
            }
        ],
        "relations": [],
        "actions": [
            {
                "action_id": "action_1",
                "owners": ["E"],
                "scope": "entity",
                "interaction": "record_click",
            }
        ],
        "preferences": [],
        "issues": [],
        "review_note": "合成流程检查",
        "human_confirmed": False,
        "ready_for_experiment": False,
    }
    fixed = invoke(
        "semantics",
        packet=save(tmp_path / "packet", packet),
        review=save(tmp_path / "review", review),
    )
    assert fixed["binding_samples"] == {"/value": 0}
    assert fixed["actions"][0]["handlers"] == [handler]
    assert (
        fixed["entities"][0]["id"] == "E"
        and fixed["semantic_units"][0]["role"] == "primary"
    )
    assert fixed["ready_for_experiment"] is False
    queue = invoke(
        "queue",
        inputs=save(tmp_path / "frozen", [fixed], lines=True),
        family_map=save(
            tmp_path / "families",
            [{"task_id": fixed["task_id"], "family_id": "F"}],
            lines=True,
        ),
    )
    assert (
        json.loads((queue / "unfilled_decisions.jsonl").read_text("utf8"))["A"]
        == "missing"
    )
    assert json.loads((queue / "queue.json").read_text("utf8"))["n"] == 1


def test_candidate_freeze_preserves_load_and_quarantines_exposed_family():
    def candidate(tid, split, text, load, size="2x2"):
        return {
            "task_id": tid,
            "split": split,
            "original_request": {"userQuery": text, "size": size},
            "contract": {
                "task_id": tid,
                "D": load,
                "size": size,
                "constraints": {
                    "content_selection_locked": True,
                    "may_delete_content": False,
                },
            },
        }

    rows = [
        candidate("a", "report", "合成读数", 1),
        candidate("b", "report", "合成读数", 3),
        candidate("c", "report", "合成读数", 3),
        candidate("d", "extension", "历史输入", 6),
        candidate("e", "reserve", "另组", 7),
    ]
    journal, summary = select_candidates(
        rows, [{"task_ids": ["x", "d"], "exposure": ["保管人确认"]}], []
    )
    assert (
        summary["retained"] == 3
        and summary["quarantined"] == summary["exact_aliases"] == 1
    )
    by_id = {r["task_id"]: r for r in journal}
    assert (
        by_id["a"]["family_id"] == by_id["b"]["family_id"]
        and by_id["b"]["decision"] == "retained"
    )
    assert by_id["c"]["representative"] == "b"
    assert by_id["d"]["decision"] == "quarantine_exposed_family"
    assert "合成读数" not in json.dumps(summary, ensure_ascii=False)
    rows.append(copy.deepcopy(rows[0]))
    with pytest.raises(ValueError):
        select_candidates(rows, [], [])


def test_split_runs_all_seeds_retains_failures():
    records = [
        {
            "case_id": str(i),
            "size": "2x2",
            "D": 1,
            "A": 0,
            "source_hashes": {},
            "items": [
                {"count": 1, "sources": [{"type": "static_text", "content": str(i)}]}
            ],
            "supporting_text": [],
            "actions": [],
        }
        for i in range(4)
    ]
    inputs = [
        {
            "case_id": str(i),
            "input": {"userQuery": "合成" + str(i)},
            "pre_exposed": i < 2,
        }
        for i in range(4)
    ]
    trials = make_drafts(
        records, inputs, {"dev": 1, "report": 1, "extension": 1, "reserve": 1}
    )["trials"]
    assert len(trials) == 5 and all(
        t["allocation"] is None and t["error"] for t in trials
    )


def test_calibration_packets_and_empty_aggregate_only(tmp_path):
    pkg = tmp_path / "source"
    ids = [
        {"task_id": f"synthetic{i}", "size": "2x2" if i < 5 else "2x4"}
        for i in range(10)
    ]
    save(pkg / "dev/case_index.jsonl", ids, lines=True)
    save(
        pkg / "dev/layout_inputs.jsonl",
        [{**row, "test_only_secret": "hidden-answer"} for row in ids],
        lines=True,
    )
    save(
        pkg / "dev/requests_for_review.jsonl",
        [
            {
                "task_id": x["task_id"],
                "original_request": {
                    "userQuery": "模拟读数",
                    "candidateDataBindings": [],
                    "transport": "hidden-envelope",
                },
            }
            for x in ids
        ],
        lines=True,
    )
    private = tmp_path / "manager"
    generate("calibration", private, pkg)
    questions = []
    for role in ("P7-trial-A", "P7-trial-B"):
        source = (private / "calibration" / role / "questions.json").read_text("utf8")
        assert all(
            value not in source
            for value in ("hidden-answer", "hidden-envelope", "synthetic0")
        )
        questions.append({q["id"] for q in json.loads(source)["cases"]})
    assert questions[0].isdisjoint(questions[1])
    result = score("calibration", tmp_path / "empty", private)
    assert result["P7"] is None and len(result["missing"]) == 2


def test_private_outputs_cannot_enter_public_package(tmp_path):
    from audit_common import private_destination

    source = tmp_path / "inputs"
    source.mkdir()
    for candidate in (source, source / "review"):
        with pytest.raises(ValueError, match="必须分开"):
            generate("calibration", candidate, source)
    assert not (source / "review").exists()
    assert (
        private_destination(tmp_path / "formal", input_package=source)
        == tmp_path / "formal"
    )
    assert (
        private_destination(tmp_path / "private" / "receipt.json")
        == tmp_path / "private" / "receipt.json"
    )


def test_recognizes_only_the_published_git_repository(tmp_path, monkeypatch):
    import subprocess

    import audit_common

    git = tmp_path / "private-repository"
    subprocess.run(["git", "init", "--quiet", str(git)], check=True)
    subprocess.run(
        ["git", "-C", str(git), "remote", "add", "origin", "file:///private/example"],
        check=True,
    )
    code = git / "cardgen-proto/exp/studies/dataset/audit_common.py"
    code.parent.mkdir(parents=True)
    monkeypatch.setattr(audit_common, "__file__", str(code))
    target = git / "private-output" / "dispositions.jsonl"
    assert audit_common.private_destination(target) == target
    subprocess.run(
        [
            "git",
            "-C",
            str(git),
            "remote",
            "set-url",
            "origin",
            "git@github.com:evanyixie/EasyA2UI.git",
        ],
        check=True,
    )
    with pytest.raises(ValueError, match="发布仓库"):
        audit_common.private_destination(target)
