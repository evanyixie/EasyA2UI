"""Layout contract tests independent of third-party font distribution."""

import pytest
from reference_text_measure import CapacityError, TextMeasure


@pytest.fixture
def measure(monkeypatch):
    class Face:
        def getlength(self, text):
            # A kerned pair occupies 14 pixels; each standalone letter occupies 8.
            return 8 * len(text) - 2 * text.count("AV")

    monkeypatch.setattr(TextMeasure, "_font", lambda self, size, bold: Face())
    return object.__new__(TextMeasure)


def test_wraps_shaped_runs_at_the_inclusive_width_boundary(measure):
    line = measure.text("AV", 7.5, 12, max_lines=1, line_height=1.3)
    assert (line.height, line.lines, line.font_size, line.line_height) == (
        18,
        1,
        12,
        1.3,
    )
    assert measure.text("AV", 7.49, 12, max_lines=2).lines == 2
    with pytest.raises(CapacityError, match="需要 2 行"):
        measure.text("AV", 7.49, 12, max_lines=1)


def test_blank_lines_and_unfit_glyphs(measure):
    assert measure.text("", 6, 12, max_lines=1).lines == 1
    assert measure.text("\nA\n", 6, 12, max_lines=3).lines == 3
    with pytest.raises(CapacityError, match="可用宽度不足"):
        measure.text("", 4, 12, max_lines=1)
    with pytest.raises(CapacityError, match="单个字形"):
        measure.text("A", 5.99, 12, max_lines=1)
