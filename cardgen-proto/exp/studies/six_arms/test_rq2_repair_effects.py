from pathlib import Path

import pytest


@pytest.fixture
def effects(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import rq2_repair_effects

    return rq2_repair_effects


def test_introduction_worsening_and_tolerance_are_different(effects):
    before = (
        {("a", "lines"): 1.0, ("b", "height"): 2.0, ("c", "height"): 2.0},
        {"a", "b", "c", "d"},
    )
    after = (
        {
            ("b", "height"): 2.05,
            ("c", "height"): 2.051,
            ("d", "width"): 4.0,
            ("new", "width"): 3.0,
        },
        {"a", "b", "c", "d", "new"},
    )
    stats = effects.geometry_effect(before, after)
    assert stats["introduced_occurrences"] == 2
    assert stats["introduced_on_new_ids"] == stats["introduced_on_preexisting_ids"] == 1
    assert stats["worsened_existing_occurrences"] == stats["with_either"] == 1


def test_unknown_scope_and_exact_original_retention(effects):
    assert effects.geometry_effect(None, None, identical=True) == {
        "not_numerically_comparable": 1,
        "unchanged_bytes_without_measurement": 1,
    }
    measured = ({}, {"root"})
    assert effects.geometry_effect(measured, measured)["with_either"] == 0
    effects.verify_selection(
        b"initial", [(1, False, b"bad"), (2, False, b"worse")], b"initial", False
    )
    effects.verify_selection(
        b"initial", [(1, False, b"bad"), (2, True, b"new")], b"new", True
    )
    effects.verify_selection(b"initial", [], None, None)


@pytest.mark.parametrize(
    ("rounds", "terminal", "status"),
    [
        ([(1, False, b"bad")], b"bad", False),
        ([], b"initial", None),
        ([], None, False),
        ([(1, True, b"new"), (2, False, b"new")], b"new", True),
        ([(1, True, b"new"), (2, True, b"new")], b"new", True),
    ],
)
def test_rejections_are_not_adopted_or_counted_as_known(
    effects, rounds, terminal, status
):
    with pytest.raises(ValueError):
        effects.verify_selection(b"initial", rounds, terminal, status)
