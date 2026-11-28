import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def web(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import web_geometry_browser

    return web_geometry_browser


@pytest.fixture
def renderer(web):
    try:
        return web.legacy(
            web.renderer_source(os.environ.get("EASY_A2UI_RENDERER_SOURCE"))
        )
    except subprocess.CalledProcessError:
        pytest.skip("Provide the pinned renderer source for history-free releases")


def card(key, nodes, *, width=150, size="2x2", data=None):
    root = {
        "id": "root",
        "component": "Column",
        "styles": {"width": width, "height": 150},
        "children": [n["id"] for n in nodes],
    }
    messages = [
        {"createSurface": {"surfaceId": "synthetic"}},
        {
            "updateComponents": {
                "surfaceId": "synthetic",
                "root": "root",
                "components": [root, *nodes],
            }
        },
        {
            "updateDataModel": {
                "surfaceId": "synthetic",
                "path": "/",
                "value": {} if data is None else data,
            }
        },
    ]
    return {
        "key": key,
        "size": size,
        "a2ui": "\n".join(json.dumps(m) for m in messages),
    }


def leaf(value, w=150, kind="Text"):
    return {
        "id": "synthetic-leaf",
        "component": kind,
        "styles": {
            "width": w,
            "height": 24,
            "fontSize": 12,
            "lineHeight": 1.3,
            "maxLines": 1,
        },
        "content" if kind == "Text" else "label": value,
    }


def test_pinned_source_and_no_optional_resource_or_file_loader(web, renderer, tmp_path):
    assert not (
        {"main", "MEDIA", "svg_inline", "sys", "subprocess", "frame"} & renderer.keys()
    )
    p = tmp_path / "historical.py"
    p.write_bytes(b"changed source")
    with pytest.raises(ValueError, match="fingerprint"):
        web.legacy(str(p))


def test_exact_expression_resolver_and_safe_projections(web, renderer):
    value = '&<上车>" ${/data/literal} GEOMETRYTEXT1END'
    n = leaf({"path": "/x"})
    n["id"] = 'untrusted"identifier'
    n["styles"]["backgroundColor"] = "ignored decorative metadata"
    result = web.prepare(card("s", [n], data={"x": value}), renderer)
    body, texts, attrs = result
    assert (
        list(texts.values()) == [value]
        and "lossless_binding_bridge" == attrs["binding_mode"]
    )
    assert (
        "&amp;&lt;上车&gt;&quot;" in body
        and "untrusted" not in body
        and "decorative metadata" not in body
    )
    doc = web.document([result])
    assert (
        "default-src 'none'" in doc
        and "base-uri 'none'" in doc
        and "connect-src 'none'" in doc
    )
    assert doc.count("<script ") == 1 and "unsafe-eval" not in doc
    expr = "{{ '今天 ' + ${/items/0} + ' 台' }}"
    _, texts, attrs = web.prepare(
        card("x", [leaf(expr)], data={"items": [3]}), renderer
    )
    assert list(texts.values()) == ["今天 3 台"] and attrs["expression_leaves"] == 1
    _, texts, attrs = web.prepare(card("x", [leaf("不变")]), renderer)
    assert attrs["binding_mode"] == "historical_text_equal"


@pytest.mark.parametrize(
    "n,reason",
    [
        (leaf({"path": "/missing"}), "unresolved_binding_value"),
        (leaf("{{ upper(${/x}) }}"), "unsupported_binding_expression"),
        ({**leaf("x"), "component": "Image"}, "unsupported_component"),
        ({**leaf("x"), "styles": {"padding": "unexpected"}}, "invalid_geometry_style"),
        (
            {**leaf("x"), "styles": {"position": "absolute"}},
            "unsupported_geometry_style",
        ),
    ],
)
def test_unassessed_inputs_never_become_zero_overflow(web, renderer, n, reason):
    with pytest.raises(web.Unsupported, match=reason):
        web.prepare(card("x", [n]), renderer)


def test_count_once_per_leaf_that_exceeds_four_on_at_least_one_side(web):
    rows = [
        ["a", "p", [2, 5, 0, 7], 5],
        ["b", "q", [0, 4, 0, 0], 4],
        ["c", "r", [0, 0, 0, 0], 1],
    ]
    totals = web.score({"a": "p", "b": "q", "c": "r"}, rows)
    assert totals == {
        "overflow_nodes": 2,
        "above4_nodes": 1,
        "overflow_max_px": 7,
        "overflow_sum_px": 18,
        "clipped_text_nodes": 1,
        "edge_clip_nodes": 1,
    }
    with pytest.raises(web.Unsupported, match="missing_rendered"):
        web.score({"a": "p"}, [])
    with pytest.raises(web.Unsupported, match="identity_mismatch"):
        web.score({"a": "p"}, [["a", "different", [0] * 4, 0]])


def test_locked_profile_does_not_discard_measurement_or_page_privacy(
    web, tmp_path, monkeypatch, caplog
):
    attempts = []

    def denied(path):
        attempts.append(path)
        raise PermissionError("synthetic lock")

    monkeypatch.setattr(web.shutil, "rmtree", denied)
    monkeypatch.setattr(web.time, "sleep", lambda _: None)
    with web.scratch_directory(tmp_path) as directory:
        (directory / "geometry.html").write_text("synthetic page")
        measurement = 5
    assert measurement == 5 and not (directory / "geometry.html").exists()
    assert len(attempts) == 6 and all(p.parent == tmp_path for p in attempts)
    assert "cleanup deferred" in caplog.text


def test_local_blink_integration_synthetic_only(web, renderer, tmp_path, monkeypatch):
    win_chrome = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
    exe = os.environ.get("EASY_A2UI_TEST_BROWSER") or (
        str(win_chrome) if win_chrome.is_file() else shutil.which("chromium")
    )
    if not exe:
        pytest.skip("No local Blink test browser")
    monkeypatch.setenv("EASY_A2UI_WEB_SCRATCH", str(tmp_path / "unused-fallback"))
    cases = [
        card(
            str(w), [leaf({"path": "/x"}, w)], size="2x4", data={"x": "3&<４>\u202f个"}
        )
        for w in (149, 154, 155)
    ]
    cases.extend(
        [
            card("buttons", [leaf("打开", 90, "Button")]),
            card("unsupported", [leaf({"path": "/unavailable"})]),
            card("horizontal", [leaf("MMMMMMMMMMMM", 8)]),
        ]
    )
    results = web.measure_cards(cases, edge=exe, batch_size=4, scratch=tmp_path)
    assert [(r["overflow_max_px"], r["above4_nodes"]) for r in results[:3]] == [
        (0, 0),
        (4, 0),
        (5, 1),
    ]
    assert all(
        r["caller_canvas_differs"]
        and r["expected_text_nodes"] == r["measured_text_nodes"] == 1
        for r in results[:3]
    )
    assert (
        results[3]["state"] == "measured"
        and results[3]["expected_text_nodes"] == results[3]["measured_text_nodes"] == 0
    )
    assert (
        results[4]["state"] == "unassessed"
        and results[4]["overflow_nodes"] is None
        and results[4]["expected_text_nodes"] == 1
    )
    assert results[5]["clipped_text_nodes"] == 1 and results[5]["edge_clip_nodes"] == 0
    assert not list(tmp_path.glob("*/geometry.html"))
