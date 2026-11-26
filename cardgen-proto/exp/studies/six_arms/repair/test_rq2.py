"""同一虚构庭院初稿上的 RQ2 首轮、回退、缺回执与二轮反馈回归。"""

import json
import sys
from copy import deepcopy
from hashlib import sha256

import pytest

from harness_v2 import model_stages, program_stages
from repair import evidence, rq2


@pytest.fixture
def garden():
    try:
        program_stages.measurement_files()
    except RuntimeError:
        pytest.skip("需要外部参考测量引擎与两份字体")
    good = [json.loads(line) for line in model_stages._example_native().splitlines()]
    nodes = {n["id"]: n for n in good[1]["updateComponents"]["components"]}
    nodes["caption"]["styles"]["height"] = 24
    nodes["value"]["styles"]["height"] = 36
    original = deepcopy(good)
    value = next(
        n for n in original[1]["updateComponents"]["components"] if n["id"] == "value"
    )
    value["styles"]["height"] = 8
    return (
        evidence.encode(original),
        evidence.encode(good),
        deepcopy(model_stages._EXAMPLE_SOURCE),
    )


@pytest.mark.parametrize(
    ("sequence", "expected_status", "expected_acceptance"),
    [
        (("good",), "accepted", [True]),
        (("bad", "good"), "accepted", [False, True]),
        (("bad", "bad"), "exhausted", [False, False]),
        (("missing",), "missing_response", [None]),
    ],
)
def test_rq2_same_first_card_and_repair_rounds(
    garden, sequence, expected_status, expected_acceptance
):
    original, good, source = garden
    requests = []

    def respond(phase, prompt):
        context = json.loads(prompt[-1]["content"])
        assert context["original"] == original.decode("utf8")
        assert context["violations"]["geometry"]["pass"] is False
        if not requests:
            assert "previous_attempt" not in context
        else:
            assert context["previous_attempt"]["response"] == "{}"
            assert context["previous_attempt"]["rejected_checks"]
        requests.append(phase)
        reply = sequence[len(requests) - 1]
        if reply == "missing":
            return None
        return {
            "raw": good.decode("utf8") if reply == "good" else "{}",
            "receipt": {"origin": "synthetic", "physical_attempts": 0},
        }

    cards, report = rq2.compare(original, source, respond)
    assert set(cards) == {"L1-NR", "L1", "L1-M"}
    assert cards["L1-NR"] == original
    assert report["arms"]["L1-NR"]["joint_pass"] is False
    assert requests == [f"r{n}" for n in range(1, len(sequence) + 1)]
    model = report["arms"]["L1-M"]
    assert model["status"] == expected_status
    assert [r["accepted"] for r in model["rounds"]] == expected_acceptance
    expected = good if expected_status == "accepted" else original
    assert cards["L1-M"] == expected
    assert model["terminal_sha256"] == sha256(expected).hexdigest()
    assert model["joint_pass"] is (
        True
        if expected_status == "accepted"
        else None
        if expected_status == "missing_response"
        else False
    )


def test_cli_demo_and_unexecuted_comparison(garden, tmp_path, monkeypatch, capsys):
    demo = tmp_path / "demo"
    monkeypatch.setattr(sys, "argv", ["repair.rq2", "demo", str(demo)])
    rq2.main()
    assert json.loads(capsys.readouterr().out)["L1-M"]["status"] == "accepted"
    freeze = json.loads((demo / "freeze.json").read_bytes())
    first = (demo / "original.a2ui.jsonl").read_bytes()
    assert freeze["original_sha256"] == sha256(first).hexdigest()
    assert freeze["model_response_source"] == "synthetic"
    assert (demo / "L1-NR.a2ui.jsonl").read_bytes() == first
    assert json.loads((demo / "r1/call.json").read_bytes())["physical_attempts"] == 0

    second = tmp_path / "no-model"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "repair.rq2",
            "compare",
            str(demo / "source.json"),
            str(demo / "original.a2ui.jsonl"),
            str(second),
        ],
    )
    rq2.main()
    assert json.loads(capsys.readouterr().out)["L1-M"]["joint_pass"] is None
    report = json.loads((second / "report.json").read_bytes())
    assert report["model_response_source"] == "unexecuted"
    assert report["arms"]["L1-M"]["status"] == "missing_response"
    assert (second / "L1-M.a2ui.jsonl").read_bytes() == first
