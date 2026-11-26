"""仅以临时合成题自测，所有返回都在临时目录销毁。"""

import copy

import pytest

import human_review as review


def mock_stage(root, mode, roles):
    stage = root / "formal"
    admin = {"packets": {}, "package_file_sha256": {}}
    submissions = {}
    for i, role in enumerate(roles):
        ids = [f"blind{i}-{k}" for k in range(2)]
        cases = [
            {
                "id": bid,
                "request": {"userQuery": "显示测试姓名"},
                "choices": [["D1.1", "/x"]],
            }
            for bid in ids
        ]
        q = {"mode": mode, "layout_classes": ["L", "R", "无法判定"], "cases": cases}
        path = stage / role / "questions.json"
        review.save(path, q)
        admin["packets"][role] = {
            "version": "synthetic",
            "blind_to_task": dict(zip(ids, ["t0", "t1"], strict=True)),
        }
        admin["package_file_sha256"][f"{role}/questions.json"] = review.hashfile(path)
        if mode == "must":
            content = [
                {"state": "已判定", "must": ["D1.1"], "literal": [], "note": ""},
                {"state": "无必显项", "must": [], "literal": [], "note": "synthetic"},
            ]
        elif mode == "layout":
            content = [{"layout": "L"}, {"layout": "R"}]
        else:
            content = [
                {
                    "protocol": "符合",
                    "binding": "证据不足",
                    "content": "符合",
                    "note": "synthetic",
                },
                {
                    "protocol": "符合",
                    "binding": "不符合",
                    "content": "不符合",
                    "note": "synthetic",
                },
            ]
        submissions[role] = {
            "role": role,
            "version": "synthetic",
            "reviewer": f"synthetic-{i}",
            "independent": True,
            "submitted_at": "2000-01-01T00:00:00Z",
            "answers": dict(zip(ids, content, strict=True)),
        }
    review.save(stage / "admin.json", admin)
    return submissions


def test_paired_with_different_blind_ids(tmp_path, monkeypatch):
    roles = ["P7-all-A", "P7-double-B"]
    sub = mock_stage(tmp_path, "must", roles)
    for role, s in sub.items():
        review.save(tmp_path / "inbox" / (role + ".json"), s)
    score = review.score("formal", tmp_path / "inbox", tmp_path)["P7"]
    assert (
        score["paired_n"] == 2
        and score["exact_rate"] == 1
        and score["mean_card_jaccard"] == 1
    )
    s = sub[roles[1]]
    s["answers"]["blind1-1"] = {
        "state": "证据不足",
        "must": [],
        "literal": [],
        "note": "synthetic",
    }
    review.save(tmp_path / "inbox" / (roles[1] + ".json"), s)
    assert (
        review.score("formal", tmp_path / "inbox", tmp_path)["P7"]["unresolved_n"] == 1
    )
    s["reviewer"] = "synthetic-0"
    review.save(tmp_path / "inbox" / (roles[1] + ".json"), s)
    with pytest.raises(ValueError, match="同一人"):
        review.score("formal", tmp_path / "inbox", tmp_path)


def test_invalid_returns(tmp_path):
    r = "P7-all-A"
    s = mock_stage(tmp_path, "must", [r])[r]
    path = tmp_path / "formal"
    for change in [
        "wrong_hash",
        "missing",
        "foreign_quote",
        "extra",
        "wrong_mode",
        "blindness",
    ]:
        x = copy.deepcopy(s)
        if change == "wrong_hash":
            x["version"] = "old"
        if change == "missing":
            x["answers"].pop("blind0-0")
        if change == "extra":
            x["answers"]["fake"] = {}
        if change == "foreign_quote":
            x["answers"]["blind0-0"]["literal"] = ["伪事实"]
        if change == "wrong_mode":
            x["role"] = "P6-gold"
        if change == "blindness":
            x["independent"] = False
        with pytest.raises(ValueError):
            review.checked_submission(path, r, x)


def test_gold_partial_information(tmp_path, monkeypatch):
    r = "P6-gold"
    s = mock_stage(tmp_path, "gold", [r])[r]
    review.save(tmp_path / "inbox" / (r + ".json"), s)
    score = review.score("formal", tmp_path / "inbox", tmp_path)["P6_gold"]
    assert (score["defective_cards"], score["unresolved_cards"]) == (1, 1)
    assert score["rate_on_all_if_every_unknown_passes"] == 0.5
    assert score["rate_on_all_if_every_unknown_fails"] == 1


def test_agreement_coefficient(tmp_path, monkeypatch):
    assert review.kappa([]) is None and review.kappa([("L", "L")] * 3) is None
    assert review.kappa([("L", "R"), ("R", "L")]) == -1
    roles = ["P6-layout-A", "P6-layout-B"]
    subs = mock_stage(tmp_path, "layout", roles)
    for role, s in subs.items():
        review.save(tmp_path / "inbox" / (role + ".json"), s)
    assert (
        review.score("formal", tmp_path / "inbox", tmp_path)["P6_layout"]["kappa"] == 1
    )


def test_missing_returns_keep_unknown(tmp_path, monkeypatch):
    mock_stage(tmp_path, "must", ["P7-all-A", "P7-double-B"])
    info = review.score("formal", tmp_path / "empty", tmp_path)
    assert len(info["missing"]) == 2 and info["P7"] is None
