"""Width candidates used by the common native repair's two-child row check."""

import math


def pair_allocations(width, gap):
    """Return positive 0.25vp allocations in the frozen 2–5-column search order."""
    quarters = round((width - gap) * 4)
    if quarters <= 0 or abs((width - gap) * 4 - quarters) > 1e-6:
        raise ValueError("同行预算必须能以0.25vp精确表示且大于间距")
    ratios = {span / slots for slots in range(2, 6) for span in range(1, slots)}
    pairs = []
    for ratio in sorted(ratios, key=lambda r: (abs(r - 0.5), r)):
        first = math.floor(quarters * ratio)
        pair = first / 4, (quarters - first) / 4
        if min(pair) > 4 and pair not in pairs:
            pairs.append(pair)
    return tuple(pairs)
