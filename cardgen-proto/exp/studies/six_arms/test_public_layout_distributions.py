import json
import math
from pathlib import Path
from statistics import median

import pytest
from public_layout_distributions import bin_times, get_quantiles, summarize, verify


@pytest.mark.parametrize("n", [1, 2, 3, 12, 95, 96, 124, 187])
def test_rank_blocks_preserve_paired_quantiles(n):
    values = [((i * 1753) % 1229) / 7 for i in range(n)]
    public = get_quantiles(bin_times(values))
    assert public["n"] == n
    assert public["median"] == pytest.approx(median(values), abs=1e-6)
    assert public["p95"] == pytest.approx(
        sorted(values)[math.ceil(0.95 * n) - 1], abs=1e-6
    )


def test_sealed_public_table_and_historical_stages():
    tables = Path(__file__).resolve().parents[4] / "paper/out/tables"
    source = json.loads((tables / "enhanced_l6_layout_distributions.json").read_bytes())
    reference = json.loads(
        (tables / "enhanced_l6_vs_l5_fixed_content.json").read_bytes()
    )
    assert set(source) == {"schema", "cell_order", "quality", "latency_rank_blocks"}
    for scopes in source["quality"].values():
        pooled = scopes["all187"]
        assert set(pooled) == {"counts", "families_by_size_and_net"}
        assert len(pooled["counts"]) == 4
        assert all(len(group) == 3 for group in pooled["families_by_size_and_net"])
    for measures in source["latency_rank_blocks"].values():
        assert all(len(blocks) < 10 for blocks in measures.values())
    result = summarize(source)
    verify(result, reference)
    observations = result["quality"]
    assert [
        (
            observations[stage]["all187"]["only_l5"],
            observations[stage]["all187"]["only_l6"],
        )
        for stage in ("original", "after_wide", "legacy_compatible")
    ] == [(35, 1), (30, 2), (26, 2)]
    observed = result["timing_ms"]["strict/all187/assigned"]
    assert round(observed["program_ms"]["median"], 2) == 14.44
    assert round(observed["program_ms"]["p95"], 2) == 65.12
    observations["strict_model_native_order"]["all187"]["only_l6"] -= 1
    with pytest.raises(ValueError, match="Paired counts disagree"):
        verify(result, reference)
