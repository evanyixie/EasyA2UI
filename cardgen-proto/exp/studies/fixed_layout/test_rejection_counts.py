"""合成共同回执验证公开分类、非适配拒绝的分母及匿名输出。"""

import json
import sys
from types import SimpleNamespace

import pytest

import evidence
import rejection_counts as diagnostics


def adapter(row):
    exp = row["value"]
    if isinstance(exp, str):
        raise ValueError("不支持原始表达式")
    if exp is None:
        raise KeyError("synthetic-business-key")
    if exp is False:
        raise ValueError("synthetic-private-message")
    return exp


def sealed_fixture(root):
    rows = [
        ("first", "example", "adapter_rejected"),
        ("second", None, "adapter_rejected"),
        ("third", False, "adapter_rejected"),
        ("fourth", 1, "accepted"),
        ("fifth", 2, "reference_rejected"),
    ]
    queue, hashes, inputs, full = [], {}, [], {}
    for task, value, status in rows:
        line = json.dumps({"task_id": task, "value": value}).encode()
        inputs.append(line)
        digest = evidence.digest(line)
        queue.append({"task_id": task, "input_line_sha256": digest})
        common = {"source_row_sha256": digest, "status": status}
        if status == "adapter_rejected":
            with pytest.raises((KeyError, ValueError)) as err:
                adapter(json.loads(line))
            common.update(detail=str(err.value), error_type=type(err.value).__name__)
        elif status == "reference_rejected":
            common.update(detail="synthetic-reference-only", error_type="ValueError")
        receipt = f"results/{task}/input_receipt.json"
        evidence.atomic(root / receipt, common)
        full[receipt] = evidence.sha(root / receipt)
        for arm in evidence.ARMS:
            path = f"results/{task}/{arm}/receipt.json"
            evidence.atomic(
                root / path,
                {
                    "task_id": task,
                    "cell": arm,
                    "source_row_sha256": digest,
                    "first_pass": True,
                    "detail": common.get("detail"),
                    "status": "artifact_ready"
                    if status == "accepted"
                    else "common_" + status,
                },
            )
            hashes[path] = full[path] = evidence.sha(root / path)
    source = root / "source.jsonl"
    source.write_bytes(b"\n".join(inputs) + b"\n")
    evidence.atomic(
        root / "freeze.json",
        {
            "queue": queue,
            "input_sha256": evidence.sha(source),
            "denominator": len(queue),
            "arms": {"A": evidence.ARMS[0], "B": evidence.ARMS[1]},
        },
    )
    evidence.atomic(
        root / "seal.json",
        {
            "freeze_sha256": evidence.sha(root / "freeze.json"),
            "evidence_sha256": full,
            "arm_receipt_sha256": hashes,
            "receipts_count": len(hashes),
        },
    )
    return source


def test_public_counts_use_one_input_and_preserve_unknown(tmp_path, monkeypatch):
    monkeypatch.setitem(
        sys.modules, "shared_adapter", SimpleNamespace(document=adapter)
    )
    source = sealed_fixture(tmp_path)
    result = diagnostics.summarize(tmp_path, source)
    assert (
        result["assigned_inputs"] == 5 and result["sealed_arm_receipts_verified"] == 10
    )
    assert result["common_preparation"] == {
        "accepted": 1,
        "adapter_rejected": 3,
        "reference_rejected": 1,
    }
    assert result["unclassified_rejections"] == 1
    assert result["rejection_counts"] == {
        "冻结词法解释器未覆盖该字符串表达式": 1,
        "适配器取动态键或未覆盖字段时缺键": 1,
        diagnostics.UNCLASSIFIED: 1,
    }
    assert "synthetic-" not in json.dumps(result, ensure_ascii=False)
    (tmp_path / "results/first/input_receipt.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="摘要"):
        diagnostics.summarize(tmp_path, source)


def test_legacy_seal_rejects_changed_shared_error(tmp_path, monkeypatch):
    monkeypatch.setitem(
        sys.modules, "shared_adapter", SimpleNamespace(document=adapter)
    )
    source = sealed_fixture(tmp_path)
    seal = evidence.read(tmp_path / "seal.json")
    del seal["evidence_sha256"]
    evidence.atomic(tmp_path / "seal.json", seal)
    assert diagnostics.summarize(tmp_path, source)["adapter_rejections_reproduced"] == 3
    receipt = tmp_path / "results/second/input_receipt.json"
    changed = evidence.read(receipt)
    changed["detail"] = "other"
    evidence.atomic(receipt, changed)
    with pytest.raises(ValueError, match="首错"):
        diagnostics.summarize(tmp_path, source)


def test_distinguishes_semantic_and_syntactic_first_errors():
    exc = ValueError("原表达式跨实体或跨角色")
    assert (
        diagnostics.category(exc, {"owners": []})
        == "选定表达式无法按既定 take 规则关联到语义单元"
    )
    assert (
        diagnostics.category(
            exc,
            {
                "owners": [
                    (0, {"entity": "same", "role": "primary"}),
                    (1, {"entity": "same", "role": "context"}),
                ]
            },
        )
        == "一条不可拆的选定表达式跨角色"
    )
    assert (
        diagnostics.category(ValueError("未归属的首部文字超过一个"), {})
        == "现有投影将多段文字归为首部，而冻结表示只容许一个独立标题"
    )
    assert diagnostics.category(KeyError("path"), {}) == "适配器取既定字段 path 时缺键"
