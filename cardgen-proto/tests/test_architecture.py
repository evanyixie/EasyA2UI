"""架构检查：产品区与实验区的边界，靠测试而不是靠自觉。

三条硬规则（论文 §19 严谨性约束的代码落实）：
1. `src/` 不许 import `exp`——产品路径必须能整目录剥离实验区后继续工作；
2. 模型调用只允许出现在 `src/M1_extract.py`——四档共用同一个通道，代价指标才同源可比；
3. 四档拼的是同一份提示词共享片段——公平性要求"同一份约束清单与示例素材"。

运行：python tests/test_architecture.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from exp.conditions import (CONDITIONS, MAIN_CONDITIONS, ONE_SHOT,  # noqa: E402
                            REPAIR_CONDITIONS, STEPS, model_calls)

SRC = ROOT / "src"
EXP = ROOT / "exp"
PROMPTS = ROOT / "prompts"

IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", re.M)
NET_RE = re.compile(r"\b(?:urllib\.request|urllib\.error|http\.client|requests|httpx|aiohttp)\b")


def _py_files(directory: Path):
    return sorted(p for p in directory.rglob("*.py") if "__pycache__" not in p.parts)


def test_src_does_not_import_exp():
    """产品区不许反向依赖实验区：删掉 exp/ 后 src/ 必须照常工作。"""
    bad = []
    for p in _py_files(SRC):
        text = p.read_text(encoding="utf-8")
        for mod in IMPORT_RE.findall(text):
            if mod == "exp" or mod.startswith("exp."):
                bad.append(f"{p.relative_to(ROOT)} -> {mod}")
    assert not bad, "src/ 出现了对 exp/ 的依赖：\n" + "\n".join(bad)


def test_model_channel_is_single_point():
    """所有网络调用只允许在 src/M1_extract.py：四档共用一个通道，token/时延才可比。"""
    bad = []
    for p in _py_files(SRC):
        if p.name == "M1_extract.py":
            continue
        text = p.read_text(encoding="utf-8")
        if NET_RE.search(text):
            bad.append(str(p.relative_to(ROOT)))
    assert not bad, "网络调用出现在 src/M1_extract.py 之外：\n" + "\n".join(bad)


def test_tests_do_not_import_exp():
    """回归测试属于产品区：删掉实验区后必须照旧全绿。

    例外只有本文件——它是检查，必须能读到条件表。这个例外要写在这里，
    否则将来有人加了"测试引用 exp"的写法，剥离演练会静默失效。
    """
    bad = []
    for p in _py_files(ROOT / "tests"):
        if p.name == "test_architecture.py":
            continue
        text = p.read_text(encoding="utf-8")
        for mod in IMPORT_RE.findall(text):
            if mod == "exp" or mod.startswith("exp."):
                bad.append(f"{p.name} -> {mod}")
    assert not bad, "tests/ 出现了对 exp/ 的依赖（删实验区后会崩）：\n" + "\n".join(bad)


def test_shared_prompt_fragments_exist():
    """四档共享的提示词片段必须存在且非空（公平性第 1、2 条）。"""
    for name in ("_constraints.md", "_fewshot.md"):
        p = PROMPTS / name
        assert p.exists(), f"缺少共享片段 {name}"
        assert p.read_text(encoding="utf-8").strip(), f"共享片段 {name} 是空的"


def test_conditions_are_a_matrix_not_four_programs():
    """每档要么四步齐全，要么整行 one_shot（不分解）：不许半拆半合。"""
    assert set(CONDITIONS) == {"L1", "L2", "L3", "L4", "L5", "L5b", "L6"}
    assert set(MAIN_CONDITIONS) == {"L1", "L2", "L3", "L4", "L5", "L6"}
    for name, spec in CONDITIONS.items():
        values = [spec.get(s) for s in STEPS]
        if all(v == ONE_SHOT for v in values):
            continue
        assert not any(v == ONE_SHOT for v in values), f"{name} 混用 one_shot 与分步实现"
        for step in STEPS:
            assert step in spec, f"{name} 缺少 {step} 步骤"


def test_l1_is_one_shot():
    """L1 只调一次模型、一次出整卡：整档标 one_shot，不许拆成四步假装分步。"""
    assert all(CONDITIONS["L1"].get(s) == ONE_SHOT for s in STEPS)


def test_l6_is_the_product_path():
    """L6 必须直接指向产品路径的实现，而不是 exp/ 里另写一份。"""
    l6 = CONDITIONS["L6"]
    assert l6["structure"] == "program_route"
    assert l6["geometry"] == "program_solve_plan"
    assert l6["theme"] == "program_theme"
    assert l6["emit"] == "program_jsonl"


def test_ladder_hands_over_one_stage_at_a_time():
    """从 L3 到 L6，程序接手的阶段个数逐个加一：每档只多移交一个阶段。"""
    order = ["L2", "L3", "L4", "L5", "L6"]
    counts = [sum(1 for st in STEPS if str(CONDITIONS[c][st]).startswith("program_")) for c in order]
    assert counts == [0, 1, 2, 3, 4], counts


def test_two_ends_cost_one_call():
    """两端都是 1 次调用：L1 一次全包，L6 只有内容归模型；L2 最多（5 次）。"""
    assert model_calls("L1") == 1
    assert model_calls("L6") == 1
    assert model_calls("L2") == 5


def test_l5b_only_changes_structure():
    """L5b 与 L5 只差结构实现：内容实现与调用次数都一样，不许顺手换别的。"""
    a, b = CONDITIONS["L5"], CONDITIONS["L5b"]
    assert a["content"] == b["content"] == "model_extract"
    assert a["structure"] == "model_free" and b["structure"] == "model_pick"
    assert model_calls("L5") == model_calls("L5b") == 2
    for st in ("geometry", "theme", "emit"):
        assert a[st] == b[st], f"L5b 不应改 {st}"


def test_repair_arms_share_the_same_base():
    """补救三组必须建立在同一个位置上（全包），否则比的是两件事。"""
    bases = {v["base"] for v in REPAIR_CONDITIONS.values() if v["base"] == "L1"}
    assert bases == {"L1"}
    for name in ("L1-NR", "L1", "L1-M"):
        assert name in REPAIR_CONDITIONS


# ---------------------------------------------------------------------------
# 命名与论文对应（论文 §19.7、设计正本 §13.1）
#
# 这两条是"长期原则"的落地：原则只写在文档里会漂，写成断言才会在改名时立刻报错。
# ---------------------------------------------------------------------------

# src/ 里不属任何单一环节的基础设施文件（不带环节号）
INFRA_FILES = {
    "__init__.py", "pipeline.py", "validate.py", "measure.py",
    "text_metrics.py", "content_forms.py", "sample_values.py",
    "pipeline_options.py", "paths.py",
}

# 已废止的名字：出现即说明改名没同步干净
DEPRECATED = [
    "registry/", "fixtures/", "exp/prompts", "batch_queries.json",
    "step1_structure_plan",
    "src.llm", "src.normalize", "src.skeletons", "src.slot_assign",
    "src.component_select", "src.capacity", "src.assemble", "src.theme",
    "src.compiler", "src.forms", "src.metrics",
]


def test_src_filenames_follow_the_paper_convention():
    """src/ 的文件名必须能对上论文的环节号：M1_ / P1_~P7_，或明确的基础设施。"""
    bad = []
    for p in sorted(SRC.glob("*.py")):
        name = p.name
        if name in INFRA_FILES:
            continue
        if re.match(r"^(M1_|P[1-7]_)", name):
            continue
        bad.append(name)
    assert not bad, (
        "src/ 出现既不带环节号、也不在基础设施白名单里的文件：\n  "
        + "\n  ".join(bad)
        + "\n（环节相关的文件加 M1_/P1_~P7_ 前缀；确属基础设施的，登记到 INFRA_FILES）"
    )


def test_no_deprecated_names_in_code():
    """全库代码（含注释）不许再出现已废止的名字：改名必须同步三处。"""
    hits = []
    for p in _py_files(ROOT):
        if p.name == "test_architecture.py" or "runs" in p.parts:
            continue
        text = p.read_text(encoding="utf-8")
        for name in DEPRECATED:
            if name in text:
                hits.append(f"{p.relative_to(ROOT)}: {name}")
    assert not hits, "代码里残留已废止的名字（改名未同步）：\n  " + "\n  ".join(hits)


if __name__ == "__main__":
    test_src_does_not_import_exp()
    print("OK  产品区不依赖实验区")
    test_model_channel_is_single_point()
    print("OK  模型调用只有一处")
    test_tests_do_not_import_exp()
    print("OK  测试不依赖实验区")
    test_shared_prompt_fragments_exist()
    print("OK  共享提示词片段存在")
    test_conditions_are_a_matrix_not_four_programs()
    print("OK  六档是同一张表的六行")
    test_l6_is_the_product_path()
    print("OK  L6 指向产品路径")
    test_ladder_hands_over_one_stage_at_a_time()
    print("OK  每档只多移交一个阶段")
    test_two_ends_cost_one_call()
    print("OK  两端各 1 次调用")
    test_l5b_only_changes_structure()
    print("OK  L5b 只改结构")
    test_repair_arms_share_the_same_base()
    print("OK  补救三组同一位置")
    test_l1_is_one_shot()
    print("OK  L1 整档不分解")
    test_src_filenames_follow_the_paper_convention()
    print("OK  src 文件名带环节号")
    test_no_deprecated_names_in_code()
    print("OK  无废止名字残留")
    print("\n== 架构检查 通过 ==")
