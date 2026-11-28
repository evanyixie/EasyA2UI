"""Pillow implementation of the experiment's reference text geometry in vp."""

from dataclasses import dataclass
from functools import lru_cache
from math import ceil
from pathlib import Path

from PIL import ImageFont


class CapacityError(ValueError):
    """The entire string cannot be drawn inside the requested width/line limit."""


@dataclass(frozen=True)
class TextMetrics:
    height: int
    lines: int
    font_size: float
    line_height: float


@lru_cache(maxsize=64)
def _load_font(path: Path, pixel_size: int):
    return ImageFont.truetype(str(path), pixel_size)


class TextMeasure:
    kind = "pillow_reference_not_native"

    def __init__(self, regular: Path, bold: Path | None = None):
        self.regular = Path(regular)
        self.bold = self.regular if bold is None else Path(bold)
        if not all(path.is_file() for path in (self.regular, self.bold)):
            raise ValueError("需要有效的参考字体文件")

    def _font(self, size: float, bold: bool):
        # The layout engine also uses this face for unwrapped natural widths.
        return _load_font(self.bold if bold else self.regular, round(4 * size))

    def text(self, value, width, font_size, *, max_lines, bold=False, line_height=1.35):
        if width <= 4:
            raise CapacityError("文字可用宽度不足")
        font = self._font(font_size, bold)
        pixel_limit = 4 * (width - 4)
        lines = 0
        # Explicit breaks, including a trailing break, start a new empty line.
        for paragraph in value.split("\n"):
            lines += 1
            run = ""
            for char in paragraph:
                if font.getlength(char) > pixel_limit:
                    raise CapacityError("单个字形无法完整容纳")
                candidate = run + char
                # Measure the shaped run as a whole to preserve kerning.
                if run and font.getlength(candidate) > pixel_limit:
                    lines += 1
                    run = char
                else:
                    run = candidate
        if lines > max_lines:
            raise CapacityError(f"完整文字需要 {lines} 行，组件最多允许 {max_lines} 行")
        return TextMetrics(
            ceil(font_size * line_height * lines + 2), lines, font_size, line_height
        )
