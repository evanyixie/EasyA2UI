"""Offline Blink proxy for the historical check_layout Text border and horizontal-clip metrics."""

import argparse
import ast
import base64
import ctypes
import hashlib
import html
import json
import logging
import math
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from six_arms import emit_fidelity
from six_arms.harness_v2 import program_stages

ROOT = Path(__file__).resolve().parents[4]
RENDERER_BLOB = "701ddca87d15fab4f1e97972cd3951283b12fa28"
RENDERER_SHA256 = "820db2c95f988e02e12ef7ebb24bd0d9b0d65ecad4bfd6a947d192ff3142c956"
EDGE = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
SIZES = {"2x2": (150, 150), "2x4": (300, 150)}
METRICS = (
    "overflow_nodes",
    "above4_nodes",
    "overflow_max_px",
    "overflow_sum_px",
    "clipped_text_nodes",
    "edge_clip_nodes",
)
# The fixed emitter uses declaration strings directly in HTML attributes. Only these
# enumerated/numeric layout properties and generated IDs reach it; paint is irrelevant here.
NUMERIC = {
    "layoutWeight",
    "borderRadius",
    "opacity",
    "flexShrink",
    "fontSize",
    "lineHeight",
    "itemMargin",
}
CHOICES = {
    "alignItems": {"start", "end", "top", "bottom", "center", "stretch"},
    "justifyContent": {
        "start",
        "end",
        "center",
        "spaceBetween",
        "spaceAround",
        "spaceEvenly",
    },
    "textAlign": {"start", "end", "left", "right", "center", "justify"},
}
PAINT = {"fontColor", "backgroundColor", "linearGradient"}
SAFE_FUNCTIONS = {
    "load_msgs",
    "to_tree",
    "walk_path",
    "fmt_val",
    "resolve",
    "argb",
    "px",
    "size_css",
    "padding_css",
    "css_of",
    "emit",
    "html_escape",
    "card_html",
}
SAFE_CONSTANTS = {"CONTAINERS", "ALIGN", "JUSTIFY", "DIR", "ARG", "BIND"}


class Unsupported(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise Unsupported(reason)


@lru_cache(maxsize=4)
def legacy(source=None):
    if source is not None:
        raw = Path(source).read_bytes()
    else:
        raw = subprocess.run(
            ["git", "cat-file", "blob", RENDERER_BLOB],
            cwd=ROOT,
            env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_ALLOW_PROTOCOL": ""},
            check=True,
            capture_output=True,
        ).stdout
    if hashlib.sha256(raw).hexdigest() != RENDERER_SHA256:
        raise ValueError("Historical renderer source fingerprint mismatch")
    body = [
        n
        for n in ast.parse(raw).body
        if (isinstance(n, ast.FunctionDef) and n.name in SAFE_FUNCTIONS)
        or (
            isinstance(n, ast.Assign)
            and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id in SAFE_CONSTANTS
        )
    ]
    namespace = {"json": json, "Path": Path, "re": re}
    # Only trusted source from the pinned blob is compiled. Its imports, SVG reader,
    # filesystem paths, comparison UI and its main entry never enter the namespace.
    exec(  # noqa: S102
        compile(ast.Module(body=body, type_ignores=[]), "<frozen-renderer>", "exec"),
        namespace,
    )
    return namespace


def renderer_source(value):
    return str(Path(value).resolve()) if value else None


def number(v):
    return type(v) in (int, float) and 0 <= v <= 100_000 and math.isfinite(v)


def styles(original):
    safe = {}
    for k, v in original.items():
        if k in PAINT:
            continue
        if k in NUMERIC:
            ok = number(v)
        elif k in {"width", "height"}:
            ok = number(v) or (
                isinstance(v, str)
                and (
                    v in {"matchParent", "wrapContent"}
                    or re.fullmatch(r"[0-9]{1,4}(?:\.[0-9]{1,10})?%", v)
                )
            )
        elif k == "fontWeight":
            ok = number(v) or (
                isinstance(v, str) and v in {"normal", "bold", "lighter", "bolder"}
            )
        elif k == "maxLines":
            ok = type(v) is int and 1 <= v <= 1000
        elif k == "padding":
            ok = number(v) or (
                isinstance(v, dict)
                and set(v) <= {"top", "right", "bottom", "left"}
                and all(number(x) for x in v.values())
            )
        elif k in CHOICES:
            ok = isinstance(v, str) and v in CHOICES[k]
        elif k == "clip":
            ok = type(v) is bool
        else:
            raise Unsupported("unsupported_geometry_style")
        need(ok, "invalid_geometry_style")
        safe[k] = v
    return safe


class InMemoryCard:
    def __init__(self, messages):
        self.raw = json.dumps(messages, ensure_ascii=False, allow_nan=False)

    def read_text(self, encoding):
        return self.raw


def resolve_value(value, data):
    tokens = emit_fidelity.tokens(value)
    need(
        tokens is not emit_fidelity.UNKNOWN
        and not (
            isinstance(value, str)
            and "${" in value
            and not value.strip().startswith("{{")
        ),
        "unsupported_binding_expression",
    )
    try:
        return "".join(
            s if k == "text" else program_stages._sample(data, s) for k, s in tokens
        )
    except program_stages.StageError:
        raise Unsupported("unresolved_binding_value") from None


def prepare(card, template, audit=None):
    raw = card["a2ui"]
    need(isinstance(raw, (str, bytes)) and len(raw) <= 2_000_000, "invalid_input")
    lines = raw.splitlines()
    need(len(lines) == 3, "invalid_envelope")
    messages = [json.loads(line) for line in lines]
    creation, graph, model = (
        m[field]
        for m, field in zip(
            messages,
            ("createSurface", "updateComponents", "updateDataModel"),
            strict=True,
        )
    )
    need(
        creation["surfaceId"] == graph["surfaceId"] == model["surfaceId"]
        and model["path"] == "/",
        "unsupported_surface_or_data_root",
    )
    tree = emit_fidelity.graph(graph)
    nodes = graph["components"]
    if audit is not None:
        audit["expected_text_nodes"] = sum(n["component"] == "Text" for n in nodes)
    need(len(nodes) <= 2000, "node_limit")
    pending = [(tree, 0)]
    while pending:
        node, depth = pending.pop()
        need(depth <= 30, "historical_renderer_depth_limit")
        pending.extend((child, depth + 1) for child in node["children"])
    ids = {n["id"]: f"g{idx}" for idx, n in enumerate(nodes)}
    root = tree["component"]["styles"]
    need(
        card["size"] in SIZES
        and all(
            number(root.get(k)) and 0 < root[k] <= 4096 for k in ("width", "height")
        ),
        "unresolved_root_canvas",
    )
    canvas = (root["width"], root["height"])
    if audit is not None:
        audit.update(
            root_width_px=canvas[0],
            root_height_px=canvas[1],
            caller_canvas_differs=canvas != SIZES[card["size"]],
        )
    data = model["value"]
    projected, labels, expected = [], {}, {}
    bridge = direct = expr = 0
    for i, n in enumerate(nodes):
        kind = n["component"]
        need(kind in {"Text", "Button", "Row", "Column"}, "unsupported_component")
        allowed = {"id", "component", "styles"}
        allowed.update(
            {"children", "itemMargin"}
            if kind in {"Row", "Column"}
            else {"content", "children"}
            if kind == "Text"
            else {"label", "onClick", "children"}
        )
        need(set(n) <= allowed, "unsupported_component_property")
        identity = ids[n["id"]]
        p = {"id": identity, "component": kind, "styles": styles(n.get("styles", {}))}
        if kind in {"Column", "Row"}:
            p["children"] = [ids[c] for c in n.get("children", [])]
            if "itemMargin" in n:
                need(number(n["itemMargin"]), "invalid_geometry_style")
                p["itemMargin"] = n["itemMargin"]
        else:
            need(not n.get("children"), "leaf_has_children")
            attr = "content" if kind == "Text" else "label"
            need(attr in n, "missing_text_or_label")
            value = n[attr]
            text = resolve_value(value, data)
            old = template["resolve"](value, data) if kind == "Text" else value
            is_binding = isinstance(value, dict) or (
                isinstance(value, str) and value.strip().startswith("{{")
            )
            bridge += int(is_binding and old != text)
            direct += isinstance(value, dict)
            expr += is_binding and not isinstance(value, dict)
            labels[str(i)] = text
            p[attr] = f"GEOMETRYTEXT{i}END"
            if kind == "Text":
                expected[identity] = text
        projected.append(p)
    graph = {"components": projected, "root": ids[tree["id"]]}
    body, actual = template["card_html"](
        InMemoryCard(
            [
                {"updateComponents": graph},
                {"updateDataModel": {"path": "/", "value": {}}},
            ]
        )
    )
    need(actual == canvas, "renderer_canvas_mismatch")
    # One substitution pass; user text never goes through expression or HTML parsing
    # as markup. Original identifiers, actions and user-supplied style strings stay out.
    body, n_replaced = re.subn(
        r"(?<=>)GEOMETRYTEXT(\d+)END(?=</div>)",
        lambda m: html.escape(labels[m[1]], quote=True),
        body,
    )
    need(n_replaced == len(labels), "historical_renderer_omitted_leaf")
    attrs = {
        "root_width_px": canvas[0],
        "root_height_px": canvas[1],
        "caller_canvas_differs": canvas != SIZES[card["size"]],
        "expected_text_nodes": len(expected),
        "binding_mode": "lossless_binding_bridge"
        if bridge
        else "historical_text_equal",
        "bridged_leaf_count": bridge,
        "direct_binding_leaves": direct,
        "expression_leaves": expr,
    }
    return body, expected, attrs


# Matches the original four single-sided Math.round tests. Width overflow uses the
# historical integer scrollWidth-clientWidth. No synthetic vertical glyph metric.
JS = """
const results=Array.from(document.querySelectorAll('.card'), card=>{
 const cr=card.getBoundingClientRect();
 return Array.from(card.querySelectorAll('[data-text="1"]'),el=>{
  const r=el.getBoundingClientRect(), d=[r.bottom-cr.bottom,r.right-cr.right,cr.top-r.top,cr.left-r.left];
  return [el.dataset.cid,el.textContent,d.map(x=>x>0.6 ? Math.round(x):0),el.scrollWidth-el.clientWidth];
 });
});
const record={cards:results,userAgent:navigator.userAgent,devicePixelRatio:window.devicePixelRatio};
const bytes=new TextEncoder().encode(JSON.stringify(record));let binary='';
for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.slice(i,i+8192));
document.getElementById('report').textContent=btoa(binary);
"""


def document(prepared):
    nonce = secrets.token_hex(16)
    css = "*{box-sizing:border-box}body{margin:0;padding:20px;background:#fff}.card{display:inline-block;vertical-align:top;margin:0 20px 20px 0}"
    cards = "".join(
        f'<div class="card" style="width:{a["root_width_px"]}px;height:{a["root_height_px"]}px;position:relative">{b}</div>'
        for b, _, a in prepared
    )
    csp = f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-src 'none'; object-src 'none'; connect-src 'none'"
    return (
        f'<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="{csp}">'
        f'<style>{css}</style></head><body>{cards}<pre id="report"></pre><script nonce="{nonce}">{JS}</script></body></html>'
    )


@lru_cache(maxsize=4)
def browser_version(executable):
    if os.name != "nt":
        return subprocess.check_output(
            [executable, "--version"], text=True, timeout=10
        ).strip()
    # Read the PE version resource; unlike launching the GUI with --version, this
    # does not create a browser session. ProductVersion DWORDs follow FileVersion.
    ver = ctypes.windll.version
    length = ver.GetFileVersionInfoSizeW(str(executable), None)
    buf = ctypes.create_string_buffer(length)
    pointer = ctypes.c_void_p()
    n = ctypes.c_uint()
    if (
        not length
        or not ver.GetFileVersionInfoW(str(executable), 0, length, buf)
        or not ver.VerQueryValueW(buf, "\\", ctypes.byref(pointer), ctypes.byref(n))
    ):
        raise RuntimeError("Browser version unavailable")
    words = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint32))
    return ".".join(str(x) for w in (words[4], words[5]) for x in (w >> 16, w & 65535))


def read_geometry(encoded, runtime):
    record = json.loads(base64.b64decode(encoded, validate=True))
    if record["devicePixelRatio"] != 1:
        raise RuntimeError(
            "Unexpected device scale factor for the Blink CSS measurement"
        )
    if runtime is not None:
        runtime["pageUserAgent"] = record["userAgent"]
        runtime["devicePixelRatio"] = record["devicePixelRatio"]
    return record["cards"]


@contextmanager
def scratch_directory(scratch):
    parent = Path(
        scratch or os.environ.get("EASY_A2UI_WEB_SCRATCH") or tempfile.gettempdir()
    ).resolve(strict=True)
    base = Path(tempfile.mkdtemp(prefix="easy-web-geometry-", dir=parent)).resolve(
        strict=True
    )
    if base.parent != parent:
        raise RuntimeError("Unexpected browser scratch location")
    try:
        yield base
    finally:
        # The isolated page can be removed independently of transient Chromium
        # cache locks. All cleanup is limited to this single newly created directory.
        page = base / "geometry.html"
        for delay in (0, 0.05, 0.1, 0.2, 0.4, 0.8):
            if delay:
                time.sleep(delay)
            try:
                page.unlink(missing_ok=True)
                shutil.rmtree(base)
                break
            except FileNotFoundError:
                if not base.exists():
                    break
            except OSError:
                pass
        else:
            logging.getLogger(__name__).warning(
                "Browser scratch cleanup deferred in the configured scratch directory"
            )


def browse(prepared, edge, *, scratch=None, runtime=None):
    with scratch_directory(scratch) as base:
        page = base / "geometry.html"
        page.write_text(document(prepared), encoding="utf-8")
        if edge.name.casefold() in {"msedge.exe", "new_msedge.exe"}:
            # Windows Edge did not write --dump-dom to stdout on this host.
            # Read the same trusted report element from the same local page.
            from six_arms.web_geometry_edge import read_report

            value = read_report(page, base / "edge-cdp-profile", edge, runtime=runtime)
            return read_geometry(value, runtime)
        run = subprocess.run(
            [
                str(edge),
                "--headless=new",
                "--disable-gpu",
                "--disable-background-networking",
                "--disable-sync",
                "--disable-extensions",
                "--disable-component-update",
                "--no-first-run",
                "--no-default-browser-check",
                "--no-pings",
                "--host-resolver-rules=MAP * ~NOTFOUND",
                "--proxy-server=127.0.0.1:9",
                "--force-device-scale-factor=1",
                f"--user-data-dir={base / 'profile'}",
                "--virtual-time-budget=3000",
                "--dump-dom",
                page.as_uri(),
            ],
            capture_output=True,
            timeout=60,
            check=True,
        )
        m = re.search(rb'<pre id="report">([A-Za-z0-9+/=]+)</pre>', run.stdout)
        if not m:
            raise RuntimeError("Local browser did not produce a geometry return")
        return read_geometry(m[1], runtime)


def score(expected, observed):
    seen = set()
    totals = dict.fromkeys(METRICS, 0)
    for node, text, d, cut in observed:
        need(
            node not in seen and node in expected and expected[node] == text,
            "rendered_text_identity_mismatch",
        )
        seen.add(node)
        totals["overflow_nodes"] += any(d)
        totals["above4_nodes"] += max(d) > 4
        totals["overflow_max_px"] = max(totals["overflow_max_px"], *d)
        totals["overflow_sum_px"] += sum(d)
        totals["clipped_text_nodes"] += cut > 4
        totals["edge_clip_nodes"] += 1 < cut <= 4
    need(seen == set(expected), "missing_rendered_text_nodes")
    return totals


def measure_cards(
    cards, *, edge=None, renderer_source=None, batch_size=32, scratch=None
):
    """Input: key, three-line a2ui bytes/text and caller size. Returns rows in input order."""
    if not 1 <= batch_size <= 64:
        raise ValueError("batch_size must be in 1..64")
    if len({c["key"] for c in cards}) != len(cards):
        raise ValueError("Card keys must be unique")
    source = renderer_source or os.environ.get("EASY_A2UI_RENDERER_SOURCE")
    emitter = legacy(str(Path(source).resolve()) if source else None)
    edge = Path(edge or EDGE).resolve()
    version = browser_version(str(edge))
    rows = []
    for start in range(0, len(cards), batch_size):
        prepared, indices = [], []
        for card in cards[start : start + batch_size]:
            row = {
                "key": card["key"],
                "state": "unassessed",
                "renderer_blob": RENDERER_BLOB,
                "browser_version": version,
                "browser_runtime": None,
                "expected_text_nodes": None,
                "measured_text_nodes": 0,
                **dict.fromkeys(METRICS),
            }
            rows.append(row)
            try:
                result = prepare(card, emitter, row)
                row.update(result[2])
                prepared.append(result)
                indices.append(len(rows) - 1)
            except Unsupported as exc:
                row["reason"] = str(exc)
            except (KeyError, ValueError, TypeError, RecursionError, UnicodeError):
                row["reason"] = "invalid_or_unsupported_artifact"
        if not prepared:
            continue
        runtime = {}
        observations = browse(prepared, edge, scratch=scratch, runtime=runtime)
        if len(observations) != len(prepared):
            raise RuntimeError("Browser returned an incomplete card batch")
        for idx, (_, expected, _), observed in zip(
            indices, prepared, observations, strict=True
        ):
            row = rows[idx]
            row["browser_runtime"] = runtime
            row["measured_text_nodes"] = len(observed)
            try:
                row.update(score(expected, observed))
                row["state"] = "measured"
            except Unsupported as exc:
                row["reason"] = str(exc)
    return rows


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--renderer-source", type=Path)
    cli.add_argument("--edge", type=Path, default=EDGE)
    args = cli.parse_args()
    legacy(
        renderer_source(
            args.renderer_source or os.environ.get("EASY_A2UI_RENDERER_SOURCE")
        )
    )
    print(
        json.dumps(
            {
                "renderer_blob": RENDERER_BLOB,
                "renderer_sha256": RENDERER_SHA256,
                "browser_version": browser_version(str(args.edge.resolve())),
            }
        )
    )
