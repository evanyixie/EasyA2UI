"""组装复现包：一条命令，从仓库挑子集打成压缩包。

原则：**复现包不是第二份代码**。它每次从当前仓库组装，因此永远不会和主线漂移。

用法：
    python paper/release/build.py                  # 生成 paper/release/复现包.zip
    python paper/release/build.py --anonymous      # 双盲版：去掉专利材料与署名
    python paper/release/build.py --check          # 只检查要打包的文件是否齐全

包里有什么：
    cardgen_proto/src/          产品路径（第四个方案本体）
    cardgen_proto/rules/     封闭域资产
    cardgen_proto/data/gold/    49 条金标
    cardgen_proto/exp/          实验区（三个方案的实现、跑批、度量）
    cardgen_proto/tests/        回归测试
    paper/data/                 闭卷题、标注、人评清单
    paper/方案/                 实验设计
    README.md                   三条命令：跑一条 / 跑主表 / 出统计（构建时生成）

不打包：runs/、out/、专利材料、config/llm.json（含密钥）、日志。
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "复现包.zip"

# (源相对路径, 包内路径)
INCLUDE = [
    ("cardgen-proto/src", "cardgen_proto/src"),
    ("cardgen-proto/rules", "cardgen_proto/rules"),
    ("cardgen-proto/data/gold", "cardgen_proto/data/gold"),
    ("cardgen-proto/exp", "cardgen_proto/exp"),
    ("cardgen-proto/tests", "cardgen_proto/tests"),
    ("paper/data", "paper/data"),
    ("paper/方案", "paper/方案"),
]

EXCLUDE_DIRS = {"__pycache__", "runs", "logs", ".cache", ".slidep", "专利材料"}
EXCLUDE_FILES = {"llm.json", ".gitkeep"}
STUDIES = Path("cardgen-proto/exp/studies")


def study_release_files(repo: Path) -> set[Path]:
    """实验目录也能生成盲卷和原件；发布包只读取 Git 登记的文件。"""
    if not (repo / STUDIES).is_dir():
        return set()
    raw = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z", "--", STUDIES.as_posix()])
    return {repo / name.decode("utf-8") for name in raw.split(b"\0") if name}


def collect() -> list[tuple[Path, str]]:
    pairs: list[tuple[Path, str]] = []
    published = study_release_files(REPO)
    for src_rel, dst_rel in INCLUDE:
        src = REPO / src_rel
        if not src.exists():
            continue
        if src.is_file():
            pairs.append((src, dst_rel))
            continue
        for p in sorted(src.rglob("*")):
            if p.is_dir() or any(part in EXCLUDE_DIRS for part in p.parts):
                continue
            if p.name in EXCLUDE_FILES:
                continue
            if p.is_relative_to(REPO / STUDIES) and (p not in published or p.is_symlink()):
                continue
            pairs.append((p, str(Path(dst_rel) / p.relative_to(src))))
    return pairs


def build(anonymous: bool = False) -> Path:
    pairs = collect()
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "release"
        for src, dst in pairs:
            target = stage / dst
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
        _write_readme(stage, anonymous)
        if OUT.exists():
            OUT.unlink()
        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(stage.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(stage))
    return OUT


def _write_readme(stage: Path, anonymous: bool) -> None:
    note = "（双盲评审版，作者与单位信息已移除）" if anonymous else ""
    text = f"""# 复现包 {note}

## 环境
只依赖 Python 3.10+ 标准库，无需安装第三方包。

## 三条命令
1. 跑一条（看效果）：
   `python -m exp.runners.run_condition --condition L4 --query "看下手机和耳机的电量"`
2. 跑主表（四档 × 49 条）：
   `python -m exp.runners.run_condition --all`
3. 出统计（表 1 / 表 2 / 表 3）：
   `python exp.metrics.build_metrics_report`

## 条件与配置的对应
见 `cardgen_proto/exp/conditions.py`（这张表同时是论文附录的映射表）。

## 已知限制
- 未训练任何模型；模型调用走 `cardgen_proto/src/M1_extract.py` 的统一通道；
- 开发集（49 条）与程序规则同源，属开卷；独立验证看 `paper/data/heldout/`。
"""
    (stage / "README.md").write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anonymous", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    pairs = collect()
    if args.check:
        missing = [s for s, _ in INCLUDE if not (REPO / s).exists()]
        print(f"待打包文件 {len(pairs)} 个")
        if missing:
            print("缺少：" + "、".join(missing))
            return 1
        return 0

    out = build(args.anonymous)
    print(f"已生成 {out}（{len(pairs)} 个文件，{out.stat().st_size // 1024} KB）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
