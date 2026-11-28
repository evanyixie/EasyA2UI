"""Synthetic P7 original and adjudication examples. No participant files."""

import hashlib
import json

import pytest
from p7_input_validation import _preflight, checked_p7_answer, validate


@pytest.fixture
def case():
    return {
        "request": {
            "originalQuery": "显示周一的温度",
            "userQuery": "温度低于 5°C 时提醒",
            "title": "出门提醒",
            "description": "早上八点出门",
            "candidateEventCandidates": ["打开相机"],
        },
        "choices": [["D1", "/demo/temperature"], ["A1", "查看预报"]],
    }


def decision(**fields):
    return {"state": "已判定", "must": [], "literal": [], "note": "", **fields}


def test_verbatim_selection_preserves_all_four_sources_and_original_answer(case):
    items = ["周一", "5°C", "早上八点", "出门提醒"]
    answer = decision(must=["D1", "A1"], literal=items.copy(), note="意见另存")
    canonical = checked_p7_answer(answer, case)
    assert canonical == {
        "state": "已判定",
        "must": ["A1", "D1"],
        "literal": sorted(items),
    }
    assert answer["must"] == ["D1", "A1"] and answer["literal"] == items


@pytest.mark.parametrize(
    "fragments",
    [
        ["显示明天的天气"],
        ["周一", "周一"],
        ["查看预报"],  # Candidate label only.
        ["打开相机"],  # Candidate metadata only.
        ["我认为要展示"],
        ["5℃"],  # Similar typography, different source characters.
        ["温度\n温度"],  # Last and first words from different request fields.
        [" "],
        [None],
        "周一",
    ],
)
def test_invalid_literal_cannot_enter_business_packet_or_resolution(case, fragments):
    with pytest.raises(ValueError):
        checked_p7_answer(decision(literal=fragments, note="我认为要展示"), case)


@pytest.mark.parametrize("state", ["无必显项", "证据不足"])
def test_empty_and_unknown_keep_distinct_states_and_require_a_reason(case, state):
    assert checked_p7_answer(decision(state=state, note="合成的独立判断"), case) == {
        "state": state,
        "must": [],
        "literal": [],
    }
    with pytest.raises(ValueError):
        checked_p7_answer(decision(state=state), case)
    with pytest.raises(ValueError):
        checked_p7_answer(decision(state=state, must=["D1"], note="理由"), case)


@pytest.mark.parametrize("selected", [["X"], ["D1", "D1"], [None], []])
def test_candidate_selection_must_be_frozen_unique_and_consistent(case, selected):
    with pytest.raises(ValueError):
        checked_p7_answer(decision(must=selected), case)


def test_candidate_only_answer_is_valid_when_request_has_no_literal(case):
    assert checked_p7_answer(decision(must=["A1"]), case)["literal"] == []
    case["choices"].append(["A1", "另一候选"])
    with pytest.raises(ValueError, match="candidate"):
        checked_p7_answer(decision(must=["A1"]), case)


def save(path, value):
    raw = json.dumps(value, ensure_ascii=False).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("bad_source", [None, "original", "adjudication"])
def test_preflight_validates_both_originals_and_the_resolution(
    tmp_path, case, bad_source
):
    role_a, role_b = "P7-all-A", "P7-double-B"
    admin = {"package_file_sha256": {}, "packets": {}}
    returns = {}
    for role in (role_a, role_b):
        question = {"id": "q", **case}
        filename = role + "/questions.json"
        admin["package_file_sha256"][filename] = save(
            tmp_path / filename, {"cases": [question], "mode": "must"}
        )
        admin["packets"][role] = {"version": "v1", "blind_to_task": {"q": "task"}}
        literal = "查看预报" if role == role_b and bad_source == "original" else "周一"
        answer = (
            decision(must=["A1"]) if role == role_a else decision(literal=[literal])
        )
        name = role + ".json"
        returns[role] = {
            "file": name,
            "sha256": save(
                tmp_path / name,
                {
                    "role": role,
                    "version": "v1",
                    "reviewer": role,
                    "independent": True,
                    "submitted_at": "2020-01-01T00:00:00Z",
                    "answers": {"q": answer},
                },
            ),
        }
    save(tmp_path / "admin.json", admin)
    resolved = decision(
        literal=["周一", "周一"] if bad_source == "adjudication" else ["周一"]
    )
    lock_path = tmp_path / "lock.json"
    lock_sha = save(
        lock_path,
        {"returns": returns, "disagreements": {"task": {"decision": resolved}}},
    )

    def verified(path, sha):
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == sha
        return data

    collector = {
        "load_lock": lambda *_: ({"task": case}, {}),
        "parse": json.loads,
        "verified": verified,
        "ROLES": (role_a, role_b),
        "P7": tmp_path,
    }
    if bad_source:
        with pytest.raises(ValueError):
            _preflight(collector, lock_path, lock_sha)
    else:
        assert _preflight(collector, lock_path, lock_sha) == {
            "tasks": 1,
            "original_selections": 2,
            "adjudications": 1,
        }


def test_unrecognized_collector_is_never_loaded(tmp_path):
    path = tmp_path / "unexpected.py"
    path.write_text('raise RuntimeError("loaded")', encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        validate(path, tmp_path / "absent-lock", "0" * 64)
