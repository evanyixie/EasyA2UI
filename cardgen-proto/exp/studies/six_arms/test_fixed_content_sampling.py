from collections import Counter
from pathlib import Path

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import fixed_content_sampling

    return fixed_content_sampling


def case(size, load, i, family=None):
    name = f"{size}-{load}-{i}"
    return {
        "task": name,
        "size": size,
        "load": load,
        "family": family or name,
        "draw_rank_sha256": f"{i:02}",
        "raw_request_sha256": name,
    }


def test_two_per_size_and_band_with_ties_and_order_invariance(study):
    rows = [
        case(size, load, i)
        for size in study.SIZES
        for load, n in ((1, 2), (2, 4), (3, 4), (4, 2))
        for i in range(n)
    ]
    selected, strata = study.draw(rows)
    assert (selected, strata) == study.draw(list(reversed(rows)))
    assert Counter((r["size"], r["load_band"]) for r in selected) == {
        (size, band): 2 for size in study.SIZES for band in study.BANDS
    }
    for size in study.SIZES:
        sub = [cell for cell in strata if cell["size"] == size]
        # Splitting the ties would yield 4/4/4. All three integer boundary
        # pairs tie on distance, so the registered rule takes (2,6).
        assert [c["min_load"] for c in sub] == [1, 2, 3]
        assert [c["max_load"] for c in sub] == [1, 2, 4]
        assert [c["population_tasks"] for c in sub] == [2, 4, 6]


def test_backtracks_across_sizes_to_preserve_global_family_uniqueness(study):
    rows = [
        case(size, load, i)
        for size in study.SIZES
        for load in (1, 2, 3)
        for i in range(2)
    ]
    rows[0]["family"] = rows[6]["family"] = "only-available-in-later-cell"
    rows.append(case("2x2", 1, 2))
    selected, _ = study.draw(rows)
    assert len({r["family"] for r in selected}) == 12
    assert [r["within_cell_rank"] for r in selected[:2]] == [2, 3]
    assert selected[6]["family"] == "only-available-in-later-cell"


def test_no_feasible_draw_rejected(study):
    rows = [
        case(s, n, i, family=str(i))
        for s in study.SIZES
        for n in (1, 2, 3)
        for i in range(2)
    ]
    with pytest.raises(ValueError, match="globally distinct"):
        study.draw(rows)
    for row in rows:
        row["load"] = 1
    with pytest.raises(ValueError, match="unsplit load bands"):
        study.draw(rows)


def test_changed_private_source_rejected_before_parsing(study, tmp_path):
    f = tmp_path / "request.json"
    f.write_bytes(b'{"original":true}')
    expected = study.digest(f.read_bytes())
    f.write_bytes(b'{"original":false}')
    with pytest.raises(ValueError, match="frozen hash"):
        study.checked_bytes(f, expected)
