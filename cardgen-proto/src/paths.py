"""资源路径的唯一事实源（Single Source of Truth）。

约定：
  - 协议发给端侧的 `src` 形如 `resources/base/media/xxx.svg`（相对 cardgen-proto 根）；
  - **这个前缀只允许出现在本文件**。rules 里的资产只登记**文件名**，
    代码一律通过 `media_src()` / `media_path()` 取路径。

以后要挪目录（或改成 CDN / 打包路径），只改下面两行常量 + 移动文件即可，
不需要再动 rules、emitter、渲染器或测试。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# —— 路径常量（改这里就是改全部）——
RESOURCE_ROOT = "resources"
MEDIA_SUBDIR = "base/media"
MEDIA_PREFIX = f"{RESOURCE_ROOT}/{MEDIA_SUBDIR}"

MEDIA_DIR = ROOT / RESOURCE_ROOT / MEDIA_SUBDIR


def bare_name(src_or_name: str) -> str:
    """把 `resources/xx/yy.svg` 或 `yy.svg` 统一成文件名（兼容历史数据）。"""
    return Path(str(src_or_name)).name


def media_src(name: str) -> str:
    """文件名 → 协议 src。传入路径也安全（自动剥成文件名）。"""
    return f"{MEDIA_PREFIX}/{bare_name(name)}"


def media_path(name: str) -> Path:
    """文件名 → 磁盘路径（兼容历史前缀）。"""
    return MEDIA_DIR / bare_name(name)
