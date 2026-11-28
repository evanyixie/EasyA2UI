"""组装六档研究的公开复现包。使用 --check 预检，--anonymous 生成匿名版标题。"""

from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "复现包.zip"
STUDIES = Path("cardgen-proto/exp/studies")
CODE_DIRS = ("cardgen-proto/src", "cardgen-proto/rules", "cardgen-proto/exp", "cardgen-proto/tests")
REPORTS = (
    "paper/方案/论文实验方案.md",
    "paper/方案/正式实验结果与进度.md",
    "paper/方案/补强L6与L5的同内容布局对照.md",
)
TABLES = (
    "paper/out/tables/six_arm_evidence_20261128.json",
    "paper/out/tables/six_arm_robustness_20261128.json",
    "paper/out/tables/enhanced_l6_vs_l5_fixed_content.json",
    "paper/out/tables/six_arm_failure_modes_20261128.json",
    "paper/out/tables/six_arm_cost_frontier.json",
    "paper/out/tables/enhanced_l6_layout_distributions.json",
    "paper/out/tables/enhanced_layout_native_observation.json",
    "paper/out/tables/six_arm_button_visibility.json",
    "paper/out/tables/layout_preference_calibration.json",
    "paper/out/tables/protocol_mutation_coverage.json",
    "paper/out/tables/matched_structure_repeats.json",
    "paper/out/tables/fixed_content_repeats.json",
    "paper/out/tables/enhanced_repeat_bridge.json",
    "paper/out/tables/standard_repeat_bridge.json",
    "paper/out/tables/matched_content_repeats.json",
    "paper/out/tables/layout_content_draws.json",
    "paper/out/tables/augmented_content_draws.json",
    "paper/out/tables/native_repeated_facts.json",
    "paper/out/tables/six_arm_cache_token_cost.json",
    "paper/out/tables/paired_resource_differences.json",
    "paper/out/tables/layout_order_sensitivity.json",
    "paper/out/tables/endpoint_stability_scores_dev.json",
    "paper/out/tables/formal_web_geometry.json",
    "paper/out/tables/formal_reference_cost.json",
    "paper/out/tables/formal_reference_cost_diagnostics.json",
    "paper/out/tables/formal_numeric_fidelity.json",
    "paper/out/tables/formal_font_size.json",
    "paper/out/tables/fixed_tree_density.json",
    "paper/out/tables/formal_repair_b5.json",
    "paper/out/tables/formal_repeated_values.json",
    "paper/out/tables/formal_stage_timing.json",
    "paper/out/tables/structure_input_audit.json",
    "paper/out/tables/model_repair_vs_layout_strategies.json",
    "paper/out/tables/formal_alarm_tab.json",
    "paper/out/tables/formal_content_only_structure_bridge.json",
    "paper/out/tables/repair_call_limits.json",
    "paper/out/tables/repair_content_yield.json",
    "paper/out/tables/formal_arm_content_yield.json",
    "paper/out/tables/wide_menu_outcomes.json",
    "paper/out/tables/fixed_geometry_content.json",
    "paper/out/tables/formal_p7_candidates.json",
    "paper/out/tables/formal_delivery_replay.json",
    "paper/out/tables/formal_selected_bindings.json",
)
FIGURES = ("paper/out/figures/six_arm_cost_frontier.png",)
PUBLIC_FILES = (*REPORTS, *TABLES, *FIGURES, "paper/data/dev/pointer.json")
STUDY_ASSETS = {
    STUDIES / ".gitattributes",
    STUDIES / "dataset/form.html",
    STUDIES / "fixed_layout/review.html",
    STUDIES / "genui71/external-demo.patch",
    STUDIES / "six_arms/fixtures/synthetic.json",
}
EXCLUDE_DIRS = {"__pycache__", "runs", "logs", "out", ".cache", ".slidep", "专利材料"}
EXCLUDE_FILES = {"llm.json", ".gitkeep"}


def study_release_files(repo: Path, paths: tuple[str, ...] = (STUDIES.as_posix(),)) -> set[Path]:
    """列出指定范围已登记的文件，默认仅查询实验程序目录。"""
    if not any((repo / path).exists() for path in paths):
        return set()
    raw = subprocess.check_output(
        ["git", "-C", str(repo), "ls-files", "-z", "--", *paths]
    )
    return {repo / item.decode("utf-8") for item in raw.split(b"\0") if item}


def collect() -> list[tuple[Path, str]]:
    """只遍历 Git 登记的代码和明确公开的文件，保留正文链接使用的仓库路径。"""
    pairs = []
    for path in sorted(study_release_files(REPO, (*CODE_DIRS, *PUBLIC_FILES))):
        relative = path.relative_to(REPO)
        name = relative.as_posix()
        if name not in PUBLIC_FILES:
            if not any(name.startswith(root + "/") for root in CODE_DIRS):
                continue
            if path.name in EXCLUDE_FILES or EXCLUDE_DIRS.intersection(relative.parts):
                continue
            if relative.is_relative_to(STUDIES) and path.suffix != ".py" and relative not in STUDY_ASSETS:
                continue
        if path.is_file() and path.resolve() == path:
            pairs.append((path, name))
    return pairs


def missing_material(pairs: list[tuple[Path, str]]) -> list[str]:
    names = {name for _, name in pairs}
    required = {
        *PUBLIC_FILES,
        "cardgen-proto/exp/studies/six_arms/study.py",
        "cardgen-proto/exp/studies/six_arms/fixtures/synthetic.json",
    }
    missing = required - names
    directories = {p.as_posix() for name in names for p in Path(name).parents}
    # 先检查允许公开的正文所指向的本地文件。引用只用于预检，不能扩大收录范围。
    for report in REPORTS:
        if report not in names:
            continue
        content = (REPO / report).read_text(encoding="utf-8")
        prose = re.sub(r"^```.*?^```[^\n]*", "", content, flags=re.MULTILINE | re.DOTALL)
        for link in re.findall(r"\[[^\]\n]+\]\(([^)\s]+)\)", prose):
            target = link.partition("#")[0]
            if target and "://" not in target:
                destination = posixpath.normpath(posixpath.join(posixpath.dirname(report), target))
                if destination not in names and destination not in directories:
                    missing.add(destination)
    return sorted(missing)


def _readme(anonymous: bool) -> str:
    title = "卡片生成六档实验" if anonymous else "EasyA2UI 卡片生成六档实验"
    return f"""# {title}

正式实验以 219 题比较 L1–L6，共 1,314 个席位。补强 L6 的布局对照使用其中可固定内容的 187 题，单独报告。

- [论文实验设计]({REPORTS[0]})
- [六档正式结果与证据范围]({REPORTS[1]}) · [机读汇总]({TABLES[0]}) · [稳健性汇总]({TABLES[1]})
- [补强 L6 与 L5 的同内容布局对照]({REPORTS[2]}) · [机读汇总]({TABLES[2]}) · [复算通过数与耗时所用的分布]({TABLES[5]})
- [补强 L6 新增通过的十题与原 L5 的真机对照]({TABLES[6]})
- [正式六档 219 题的按钮尾部省略与同题比较]({TABLES[7]})
- [固定内容实验的参考几何、字号与人工偏好]({TABLES[8]})
- [T03 三行协议校验器的逐项注错与合法对照]({TABLES[9]})
- [正式批相同布局消息的历史重复]({TABLES[10]}) · [固定内容后每题十次的布局稳定性]({TABLES[11]})
- [补强 L6 在同一批十二题上的重复结果]({TABLES[12]}) · [两档统一字号后的同题比较]({TABLES[13]})
- [相同内容提示的选择一致性]({TABLES[14]}) · [四组内容下的原程序]({TABLES[15]}) · [两种字号下的补强程序]({TABLES[16]})
- [A6 同一动态数值是否跨控件重复显示]({TABLES[17]})
- [六档缓存命中、未命中与输出用量]({TABLES[18]}) · [同题耗时与输入、输出 token 的配对差和区间]({TABLES[19]})
- [同一内容下改变候选顺序的结果]({TABLES[20]}) · [两道开发题各六档十次的端到端稳定性]({TABLES[21]})
- [正式首件与终件的浏览器文字越界、卡内截断及同题差值]({TABLES[22]})
- [覆盖参考值的卡数及每张合格卡的 token 用量]({TABLES[23]}) · [纯内容覆盖、框内截断与单边通过原因]({TABLES[24]})
- [六档正文数值出处、参考值覆盖与修复前后配对]({TABLES[25]})
- [六档声明字号、同一字段配对与设备取证范围]({TABLES[26]})
- [固定布局树，分别改变字号和留白的四格结果]({TABLES[27]})
- [正式 B5 修复轮次、候选新增违规及同初稿请求预算]({TABLES[28]})
- [A6 首帧正文的参考值重复与完整数值复核]({TABLES[29]})
- [各档逐阶段计时、调用回执与相邻档的同题时间差]({TABLES[30]})
- [L5 与原 L6 在结构阶段能读取的信息]({TABLES[31]})
- [同一批 219 题上 L1-M、L5 与 L6 的通过和成本]({TABLES[32]})
- [带参闹钟入口的五份同机实点证据]({TABLES[33]})
- [固定待排版内容和几何程序后，分别复算两种布局树的结果]({TABLES[34]})
- [相同模型请求上限下的整卡修复与分阶段生成]({TABLES[35]})
- [同题比较五种策略的技术通过、参考内容覆盖与数值出处]({TABLES[36]})
- [六档首件、终件的技术与参考内容联合通过数]({TABLES[37]})
- [宽卡同菜单首选、标准字号通过数及决策耗时]({TABLES[38]})
- [固定内容与布局树后，模型与程序几何的参考内容、可行性与耗时]({TABLES[39]})
- [P7 正式勾选清单与六档模型输入核对]({TABLES[40]})
- [预注册完整交付终点、未知分项及五组配对界限]({TABLES[41]})
- [模型已选动态字段在卡片原件和真机首帧中的保留情况]({TABLES[42]})
- [各档终止原因及 L5/L6 同题交叉表]({TABLES[3]})
- [同题成本与两种通过率]({TABLES[4]}) · [六档对比图]({FIGURES[0]})

## 用公开材料离线演练

使用 Python 3.11 或更新版本，在解压目录依次执行以下命令。`demo-batch` 和 `demo-replay` 须为新目录。这条演练使用一份合成请求和内置模型回复，仅需标准库。

```sh
python cardgen-proto/exp/studies/six_arms/study.py freeze cardgen-proto/exp/studies/six_arms/fixtures/synthetic.json demo-batch --arms L1 L2 L3 L4
python cardgen-proto/exp/studies/six_arms/study.py fixture demo-batch
python cardgen-proto/exp/studies/six_arms/study.py replay demo-batch demo-replay
```

预期匹配 4 个席位，新增物理请求 0 次。逐席结果见 `demo-replay/replay.json`。上述机读表给出正式观测和补充分析的汇总值。

安装 Pillow 后，可以用本机字体运行补强 L6 的小卡与宽卡合成示例。程序核对两个实体的事实绑定和动作，列出两种字号策略的判定与成件摘要。演练自行识别常见字体，也可用 `--regular` 和 `--bold` 指定字体文件。

```sh
python cardgen-proto/exp/studies/six_arms/portable_layout_smoke.py
```

T03 的 90 次注错和 10 个合法对照均可用公开材料复算。在解压目录执行下列命令，程序将逐项校对返回码、伴随码及异常类型。

```sh
python cardgen-proto/exp/studies/six_arms/protocol_mutations.py --check
```

## 正式结果的复核条件

保管方逐题复算需要冻结输入、对应版本的执行器、历史模型回包、原件与回执。视觉与交互结论另需对应的设备和评审证据。这些逐题材料由保管方隔离保存。

复核参考值覆盖与单位交付成本时，在上述正式批保管目录旁保留原注册的答案库和来源清单。运行 `python cardgen-proto/exp/studies/six_arms/formal_reference_cost.py <正式批保管目录>` 校验主表，加 `--diagnostics` 校验分项表。两次均使用历史原件与已封存的浏览器测量，无需模型服务或设备。

同一保管目录下运行 `python cardgen-proto/exp/studies/six_arms/formal_numeric_fidelity.py <正式批保管目录>` 可复核数值出处表。程序校验历史匹配器、输入和原件摘要，重算每席的参考值覆盖，并核对已发表的覆盖计数摘要。

运行 `python cardgen-proto/exp/studies/six_arms/formal_font_size.py <正式批保管目录>` 可复核 C-05 的两条字号线、同一字段的字号差异，以及归档设备控件树能否提供实际字号。输出仅含汇总。

运行 `python cardgen-proto/exp/studies/six_arms/formal_repeated_values.py <正式批保管目录>` 可复核 A6。程序按冻结的参考卡取值，用历史匹配器统计六档首件与终件，再检查重复出现在同一个还是多个正文控件中。

运行 `python cardgen-proto/exp/studies/six_arms/formal_stage_timing.py <正式批保管目录>` 可从归档执行记录与请求回执复算 B1/B2。每个阶段分别列出实际进入和提前终止的题数，网络请求耗时已计入相应的模型阶段。

运行 `python cardgen-proto/exp/studies/six_arms/structure_input_audit.py <正式批保管目录>` 可核对 187 份固定内容的哈希、已发送的结构提示、引用清单以及模型和程序树中的按钮位置。

运行 `python cardgen-proto/exp/studies/six_arms/repair_strategy_comparison.py <正式批保管目录>` 可复算同一批 219 题的 L1-M、L5、L6 技术通过与请求用量。复算包括原始生成和已执行的修复请求。

运行 `python cardgen-proto/exp/studies/six_arms/alarm_tab_evidence.py <正式批保管目录>` 可离线核对五份带参数的闹钟动作回执和追加后的完整交付界限。

运行 `python cardgen-proto/exp/studies/fixed_layout/formal_content_only_structure_bridge.py <11月25日固定内容实验保管目录>` 可用同一套冻结的几何程序复算模型和规则各自选择的结构，核对通过数、配对差值及可复用原件的字节。

运行 `python cardgen-proto/exp/studies/six_arms/repair_call_limits.py <六档正式批保管目录>` 可复算全部 219 题在两种调用上限下的技术结果、实际登记调用数和用量。

运行 `python cardgen-proto/exp/studies/six_arms/repair_content_yield.py <六档正式批保管目录> <保管库根目录>` 可从原始请求、参考卡和各策略的真实终件逐题核对内容，复算同时满足三项检查的数量和对应 token 用量。
运行 `python cardgen-proto/exp/studies/six_arms/formal_arm_content_yield.py <六档正式批保管目录> <保管库根目录>` 可复算六档首件、共同修复终件和 L5 对 L4 的同题差值。
运行 `python cardgen-proto/exp/studies/six_arms/fixed_geometry_content.py <六档正式批保管目录> <保管库根目录>` 可从同一批 L4 布局树重建程序几何产物，核对模型原件与程序首终件，复算参考内容、同题差值和原运行成本。异机复现须配置登记的常规与粗体字体，可用随包的 `reference_text_measure.py`。

运行 `python cardgen-proto/exp/studies/six_arms/formal_p7_candidates.py <六档正式批保管目录> <保管库根目录>` 可核对实际交接的勾选项、动作参数和留存的首请求。正式业务制卷前，保管方可用同目录的 `p7_input_validation.py --help` 查看原票及仲裁的原文证据预检入口。

运行 `python cardgen-proto/exp/studies/six_arms/preregistered/replay.py <六档正式批保管目录>` 可用冻结的判分与配对程序复算原批次的完整交付分项和五组相邻比较。公开包内的三个原程序保留冻结时的文件摘要。运行 `python -m pytest cardgen-proto/exp/studies/six_arms/preregistered` 可用合成证据独立验证判据。

运行 `python cardgen-proto/exp/studies/six_arms/formal_selected_bindings.py <六档正式批保管目录>` 可从 L2–L6 的模型内容回执追踪已接受的字段，核对卡片原件及真机首帧中的对应控件。相同非空字段集合的配对统计保留单边或双边缺件的题。

宽卡同菜单的待排版内容和首选回执保存在保管侧。使用登记的 HarmonyOS 字体、Pillow 12.3.0 和 FreeType 2.14.3，在 `cardgen-proto/exp/studies/six_arms/` 下运行 `wide_menu_outcomes.py <宽卡保管目录> --cohort-sha <题单摘要> --program-sha <程序首选摘要> --model-sha <模型首选摘要>` 即可离线复算。三个摘要见[宽卡汇总]({TABLES[38]})的 `evidence_sha256`。原始选择流程由 `wide_menu_selection.py` 冻结候选，Windows 上的 `menu_model_runner.py` 留存每次实际请求。复算已有成绩无需再次调用模型。

保管方运行 `python cardgen-proto/exp/studies/six_arms/fixed_tree_density.py <正式批保管目录>` 可重放 12 题共 120 份已生成的布局树，核对字号与留白的四格结果。需要登记的常规和粗体字库及测量器；支持通过既有的 `SIX_ARMS_FONT_REGULAR`、`SIX_ARMS_FONT_BOLD`、`SIX_ARMS_MEASURE_PY` 指向等摘要的文件。

同样的测量环境可运行 `python cardgen-proto/exp/studies/six_arms/formal_repair_b5.py <正式批保管目录>`。复算需要六档的原件、终件、逐轮候选和独立修复实验的归档回包。程序核对证据摘要，使用原字号与测量器，分别计数候选产生的几何违规和真正提交到终件的违规。

A2 文字越界复测入口为 `cardgen-proto/exp/studies/six_arms/formal_web_geometry.py <正式批保管目录>`。Windows 上使用本机 Edge，实测依赖 websockets 17.0.1。完整 Git 检出可直接读取固定版本的排版代码。单独使用发布包时，把 `EASY_A2UI_RENDERER_SOURCE` 指向历史提交 `7680f7a7` 的 `cardgen-proto/tools/gen_card_compare.py`，保留源文件字节，程序会核验 SHA-256。

演练全部六档时，将 `SIX_ARMS_MEASURE_PY` 设为本包 `cardgen-proto/exp/studies/six_arms/reference_text_measure.py` 的绝对路径，并用 `SIX_ARMS_FONT_REGULAR` 和 `SIX_ARMS_FONT_BOLD` 指定两款字体。去掉第一条命令中的 `--arms L1 L2 L3 L4`，三条命令另用新的批次与回放目录。使用原参考字体的独立发布包已复现六个合成席位，六个匹配，新增物理请求零次。与正式批逐字节比对还需匹配冻结字体和 Pillow、FreeType 版本。运行回归测试另需 pytest。另行实发模型请求需要 httpx、获授权的 API 密钥和联网环境。论文中的首次调用耗时来自历史实测。
"""


def build(anonymous: bool = False) -> Path:
    pairs = collect()
    missing = missing_material(pairs)
    if missing:
        raise ValueError("缺少已登记的发布材料或正文引用：" + "、".join(missing))
    with tempfile.TemporaryDirectory(dir=OUT.parent) as tmp:
        archive = Path(tmp) / "release.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for source, name in pairs:
                zf.write(source, name)
            zf.writestr("README.md", _readme(anonymous))
        archive.replace(OUT)
    return OUT


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anonymous", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        pairs = collect()
        print(f"发布清单共 {len(pairs) + 1} 个文件（含 README）")
        missing = missing_material(pairs)
        if missing:
            print("缺少已登记的发布材料或正文引用：" + "、".join(missing))
            return 1
        return 0
    try:
        out = build(args.anonymous)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"已生成 {out}（{out.stat().st_size // 1024} KB）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
