"""Experiment-only adapter. Memoize exactly one shaping method within one search."""
from copy import copy
from functools import cache


class CardMeasurements:
    def __init__(self, stages):
        self.stages = stages
        original = stages._measure()
        self.measure = copy(original)
        self.fonts = {}

        def card_font(size, bold):
            key = size, bold
            if key not in self.fonts:
                font = original._font(size, bold)
                self.fonts[key] = FontWidths(font)
            return self.fonts[key]

        self.measure._font = card_font

    def _measure(self):
        return self.measure

    def __getattr__(self, name):
        return getattr(self.stages, name)

    def close(self):
        self.fonts.clear()
        del self.measure._font


class FontWidths:
    def __init__(self, font):
        self.getlength = cache(font.getlength)


class ScopedSearch:
    def __init__(self, scoped_module):
        self.scoped = scoped_module

    def try_geometry(self, content, base, stages):
        measurements = CardMeasurements(stages)
        try:
            return self.scoped.try_geometry(content, base, measurements)
        finally:
            measurements.close()
