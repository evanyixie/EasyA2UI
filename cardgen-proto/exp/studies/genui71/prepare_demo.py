"""在新目录还原用于语义分工对比的外部演示实现。"""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

BASE = "9d46268a4f06e2996fef1b7644659b11a3a3eae7"
HERE = Path(__file__).resolve().parent


def materialize(source: Path, output: Path) -> None:
    source, output = source.resolve(strict=True), output.resolve()
    if output.exists():
        raise FileExistsError(f"输出目录已存在：{output}")
    subprocess.run(["git", "-C", str(source), "cat-file", "-e", f"{BASE}^{{commit}}"], check=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch:
        checkout = Path(scratch) / "demo"
        subprocess.run(
            ["git", "clone", "--no-hardlinks", "--no-checkout", "--", str(source), str(checkout)],
            check=True,
        )
        git = ["git", "-C", str(checkout)]
        subprocess.run([*git, "checkout", "--detach", BASE], check=True)
        patch = ["--unidiff-zero", str(HERE / "external-demo.patch")]
        subprocess.run([*git, "apply", "--check", "--index", *patch], check=True)
        subprocess.run([*git, "apply", *patch], check=True)
        for directory in ("src", "tests"):
            for path in sorted((HERE / directory).rglob("*.py")):
                target = checkout / path.relative_to(HERE)
                if target.exists():
                    raise FileExistsError(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        checkout.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="已获取指定提交的 GenUI-AL 仓库")
    parser.add_argument("--output", required=True, type=Path, help="新的实验目录")
    args = parser.parse_args()
    materialize(args.source, args.output)
