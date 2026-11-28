from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import fixed_tree_density
    from six_arms.harness_v2 import program_stages

    class CapacityError(ValueError):
        pass

    class Oracle:
        def text(self, value, width, sz, **kwargs):
            if value == "NEVER":
                raise CapacityError("Synthetic overflow")
            return SimpleNamespace(height=sz, lines=1)

    monkeypatch.setattr(program_stages, "_measure", lambda: Oracle())
    monkeypatch.setattr(
        program_stages,
        "_module",
        lambda *args: SimpleNamespace(CapacityError=CapacityError),
    )
    return fixed_tree_density, program_stages


def example(height, value="value"):
    content = {
        "size": {"width": 150, "height": height},
        "title": "",
        "items": [{"id": "v", "role": "primary", "text": value}],
        "actions": [],
    }
    tree = {"root": {"kind": "column", "children": [{"kind": "text", "ref": "v"}]}}
    return tree, content


@pytest.mark.parametrize(
    "height,expected", [(50, "1111"), (38, "0111"), (35, "0001"), (20, "0000")]
)
def test_independent_switches_and_original_first_fit(study, height, expected):
    mod, program = study
    tree, content = example(height)
    font = program._font_style
    got = {c: mod.one_recipe(program, c)(tree, content) for c in mod.CELLS}
    assert "".join(str(int(obj is not None)) for obj in got.values()) == expected
    for cell, obj in got.items():
        if obj is None:
            continue
        style = obj["root"]["style"]
        assert (style["itemMargin"], style["padding"]) == (
            (4, 10) if cell[1] == "S" else (2, 8)
        )
        assert obj["root"]["children"][0]["style"]["fontSize"] == (
            20 if cell[0] == "S" else 16
        )
        assert mod.frame_issue(obj["root"]) is None
    if expected == "0000":
        with pytest.raises(program.StageError, match="reference_capacity"):
            program.program_geometry(tree, content)
    else:
        assert (got["SS"] or got["CC"]) == program.program_geometry(tree, content)
    assert program._font_style is font and "style" not in tree["root"]


def test_only_capacity_rejection_is_a_nonfit(study):
    mod, program = study
    tree, content = example(150, "NEVER")
    for c in mod.CELLS:
        trial = mod.one_recipe(program, c)
        assert trial(tree, content) is None
        with pytest.raises(
            program.StageError, match="omitted_references|invalid_reference"
        ):
            trial({"root": {"kind": "text", "ref": "undeclared"}}, content)


def test_conditional_gains_interaction_and_task_weighting(study):
    mod, _ = study
    rows = [
        {"task": "a", "fits": dict(zip(mod.CELLS, [False, True, True, True]))}
        for _ in range(2)
    ]
    rows += [{"task": "b", "fits": dict.fromkeys(mod.CELLS, True)}]
    result = mod.aggregate(rows)
    assert result["draw_fit_pattern_counts"] == {"0111": 2, "1111": 1}
    assert result["cells"]["SS"] == {"fit": 1, "equal_task_weight_rate": 0.5}
    assert result["conditional_differences"]["compact_font_at_standard_spacing"] == {
        "gained_draws": 2,
        "lost_draws": 0,
        "tied_draws": 1,
        "equal_task_weight_difference": 0.5,
        "higher_tasks": 1,
        "lower_tasks": 0,
        "tied_tasks": 1,
    }
    assert (
        result["conditional_differences"]["compact_font_at_compact_spacing"][
            "gained_draws"
        ]
        == 0
    )
    assert result["interaction_equal_task_weight"] == -0.5
