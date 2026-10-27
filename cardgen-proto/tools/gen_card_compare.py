#!/usr/bin/env python3
"""把「金标 vs 本次批跑」逐卡并排渲染成自包含 HTML，用于肉眼验收。

用法：
    python viz/gen_card_compare.py                # 取最新一次 runs
    python viz/gen_card_compare.py 20261019_143144
输出：
    viz/card_compare.html（双击即开，图标内联、无外部依赖）

设计要点（都是为了"看到的就是协议里写的"）：
  - 严格按 A2UI 组件的 styles 落 CSS：width/height/padding/itemMargin(→gap)/
    layoutWeight(→flex)/alignItems/justifyContent/linearGradient/borderRadius/clip
  - 数据绑定 {{ ${/data/...} }} 就地解析成真实样本值（金标靠它显示内容）
  - Image 内联 SVG 并把 fill 改写为 currentColor，按 fillColor 着色 →
    两端图标颜色、尺寸可直接对比
  - 每张卡 2 倍缩放（150→300），左金标、右本次；顶部可切「只看不一致」
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # cardgen-proto
DATA = ROOT / "data" / "gold"                           # 随仓库分发
DSL_DIR = DATA / "生成卡片的DSL结果"
sys.path.insert(0, str(ROOT))
from src.paths import MEDIA_DIR as MEDIA  # noqa: E402  资源路径唯一事实源
RUNS = ROOT / "runs" / "batch"
GOLD_PAIRS = ROOT / "fixtures" / "gold_pairs.json"
OUT = ROOT / "runs" / "viz" / "card_compare.html"

SCALE = 2
CONTAINERS = {"Column", "Row", "Stack", "List", "Grid"}
ALIGN = {"start": "flex-start", "end": "flex-end", "top": "flex-start",
         "bottom": "flex-end", "center": "center", "stretch": "stretch"}
JUSTIFY = {"start": "flex-start", "end": "flex-end", "center": "center",
           "spaceBetween": "space-between", "spaceAround": "space-around",
           "spaceEvenly": "space-evenly"}
DIR = {"RightBottom": "135deg", "BottomRight": "135deg", "RightTop": "45deg",
       "TopRight": "45deg", "Right": "90deg", "Left": "270deg",
       "Bottom": "180deg", "Top": "0deg"}

_svg_cache: dict = {}


# ---------------------------------------------------------------- 数据解析
def load_msgs(path: Path) -> list:
    raw = path.read_text(encoding="utf-8").strip()
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, list) else [obj]
    except json.JSONDecodeError:
        return [json.loads(x) for x in raw.splitlines() if x.strip()]


def to_tree(msgs: list):
    """返回 (comps_by_id, root_id, data_root)。"""
    comps, data = {}, {}
    for m in msgs:
        if "updateComponents" in m:
            for c in m["updateComponents"].get("components", []):
                comps[c["id"]] = c
        if "updateDataModel" in m:
            u = m["updateDataModel"]
            path = u.get("path") or "/"
            val = u.get("value")
            if path.strip("/") in ("", "/"):
                data = val if isinstance(val, dict) else {"value": val}
            else:
                data = {path.strip("/").split("/")[0]: val}
    root = None
    ids = set(comps)
    referenced = {k for c in comps.values() for k in (c.get("children") or [])}
    for cid in comps:
        if cid not in referenced:
            root = cid
            break
    if root is None and comps:
        root = next(iter(comps))
    return comps, root, data


def walk_path(root, p):
    cur = root
    for seg in [x for x in p.strip("/").split("/") if x]:
        if isinstance(cur, dict):
            cur = cur.get(seg)
        elif isinstance(cur, list):
            try:
                cur = cur[int(seg)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cur


def fmt_val(v):
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if v is None:
        return "—"
    return str(v)


BIND = re.compile(r"\$\{\s*([^}]+?)\s*\}")


def resolve(text, data):
    """把 {{ ${/data/...} }} / 拼接 / 三元 解析成显示文本。"""
    if not isinstance(text, str) or "${" not in text:
        return text
    def rep(m):
        return fmt_val(walk_path(data, m.group(1)))
    out = BIND.sub(rep, text)
    out = out.replace("{{", "").replace("}}", "").strip()
    # 三元：cond ? a : b（解析后条件只剩字面量）
    if "?" in out and ":" in out:
        cond, _, rest = out.partition("?")
        a, _, b = rest.partition(":")
        cond = cond.strip().strip("'\"")
        out = (b if cond in ("", "false", "False", "0", "否", "null", "None") else a).strip()
    out = out.replace(" + ", "").replace("+", "") if " + " in out else out
    return out.strip().strip("'\"").strip()


# ---------------------------------------------------------------- 样式转换
ARG = re.compile(r"^#([0-9A-Fa-f]{8})$")


def argb(c):
    """协议里的颜色是 ArkUI 的 #AARRGGBB（alpha 在前），CSS 的 8 位是 #RRGGBBAA，
    直接照搬会把 alpha 当蓝通道 → 文字/底色全部错乱。这里统一转成 rgba()。"""
    if not isinstance(c, str):
        return c
    m = ARG.match(c.strip())
    if not m:
        return c
    h = m.group(1)
    a, r, g, b = h[0:2], h[2:4], h[4:6], h[6:8]
    alpha = round(int(a, 16) / 255, 3)
    return f"rgba({int(r,16)},{int(g,16)},{int(b,16)},{alpha})"


def px(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return f"{v:g}px"
    return None


def size_css(v, prop):
    if v is None:
        return None
    if isinstance(v, str):
        if v == "matchParent":
            return "100%"
        if v == "wrapContent":
            return "auto"
        if v.endswith("%"):          # 百分比尺寸原样透传（如 116.666667%）
            return v
        return None
    return px(v)


def padding_css(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return f"{v:g}px"
    if isinstance(v, dict):
        return " ".join(f"{v.get(k, 0):g}px" for k in ("top", "right", "bottom", "left"))
    return None


def css_of(c: dict, parent: str):
    st = c.get("styles") or {}
    out = []
    w, h = size_css(st.get("width"), "width"), size_css(st.get("height"), "height")
    if w:
        out.append(f"width:{w}")
    if h:
        out.append(f"height:{h}")
    lw = st.get("layoutWeight")
    if isinstance(lw, (int, float)):
        out.append(f"flex:{lw:g} 1 0px")
        if parent == "Row" and not w:
            out.append("min-width:0")
    if c.get("itemMargin") is not None:
        out.append(f"gap:{px(c['itemMargin'])}")
    elif st.get("itemMargin") is not None:
        out.append(f"gap:{px(st['itemMargin'])}")
    pad = padding_css(st.get("padding"))
    if pad:
        out.append(f"padding:{pad}")
    if st.get("alignItems"):
        out.append(f"align-items:{ALIGN.get(st['alignItems'], st['alignItems'])}")
    if st.get("justifyContent"):
        out.append(f"justify-content:{JUSTIFY.get(st['justifyContent'], st['justifyContent'])}")
    if st.get("backgroundColor"):
        out.append(f"background:{argb(st['backgroundColor'])}")
    lg = st.get("linearGradient")
    if lg:
        stops = ", ".join(f"{argb(col)} {pos * 100:g}%" for col, pos in lg.get("colors", []))
        out.append(f"background:linear-gradient({DIR.get(lg.get('direction'), '135deg')}, {stops})")
    if st.get("borderRadius") is not None:
        out.append(f"border-radius:{px(st['borderRadius'])}")
    if st.get("clip"):
        out.append("overflow:hidden")
    if st.get("opacity") is not None:
        out.append(f"opacity:{st['opacity']}")
    if st.get("flexShrink") is not None:
        out.append(f"flex-shrink:{st['flexShrink']}")
    return ";".join(out)


def svg_inline(src: str, color: str | None):
    """把 resources/**/x.svg 内联，并把 fill 改成 currentColor 以支持着色。"""
    name = Path(src).name
    if name not in _svg_cache:
        p = MEDIA / name
        _svg_cache[name] = p.read_text(encoding="utf-8") if p.exists() else None
    s = _svg_cache[name]
    if s is None:
        box = "border:1px dashed #bbb;box-sizing:border-box"
        return f'<span style="display:block;width:100%;height:100%;{box}"></span>'
    s = re.sub(r'fill="(?!none|currentColor)[^"]*"', 'fill="currentColor"', s)
    s = re.sub(r"fill='(?!none|currentColor)[^']*'", "fill='currentColor'", s)
    s = re.sub(r"<(svg[^>]*)>", r"<\1 style='width:100%;height:100%;display:block'>", s, count=1)
    col = f"color:{color};" if color else ""
    return f'<span style="display:block;width:100%;height:100%;{col}">{s}</span>'


# ---------------------------------------------------------------- 组件发射
def emit(cid: str, comps: dict, data, parent: str, depth=0) -> str:
    c = comps.get(cid)
    if not c or depth > 30:
        return ""
    comp = c.get("component", "Column")
    st = c.get("styles") or {}
    css = css_of(c, parent)

    if comp in CONTAINERS:
        kids = [emit(k, comps, data, comp, depth + 1) for k in (c.get("children") or [])]
        kids = [k for k in kids if k]
        if comp == "Stack":
            ac = st.get("alignContent") or "center"
            ai, ji = {"center": ("center", "center"),
                      "bottom": ("end", "center"),
                      "bottomEnd": ("end", "end"),
                      "bottomStart": ("end", "start"),
                      "topStart": ("start", "start"),
                      "topEnd": ("start", "end"),
                      "top": ("start", "center")}.get(ac, ("center", "center"))
            css += ";display:grid;grid-template:1fr/1fr"
            # 每个子节点必须显式占同一格（grid-area:1/1）才会真正叠在一起；
            # 只写 grid-template 会让后续子节点落到隐式行、被裁掉（叠层只剩最上面一层）。
            cells = "".join(
                f'<div style="grid-area:1/1;display:grid;min-width:0;min-height:0;'
                f'align-items:{ai};justify-items:{ji}">{k}</div>'
                for k in kids)
            return f'<div style="{css}" data-cid="{cid}">{cells}</div>'
        disp = {"Column": "column", "Row": "row", "List": "column",
                "Grid": "grid"}[comp]
        if comp == "Grid":
            css += f";display:grid;grid-template-columns:1fr 1fr;grid-auto-rows:1fr"
            return f'<div style="{css}" data-cid="{cid}">{"".join(kids)}</div>'
        css += f";display:flex;flex-direction:{disp}"
        if comp == "Row":
            css += ";min-width:0"
        return f'<div style="{css}" data-cid="{cid}">{"".join(kids)}</div>'

    if comp == "Text":
        txt = resolve(c.get("content", ""), data)
        fs = st.get("fontSize", 14)
        fw = st.get("fontWeight", 400)
        lh = st.get("lineHeight") or 1.25
        extra = f"font-size:{fs:g}px;font-weight:{fw};line-height:{lh}"
        if st.get("fontColor"):
            extra += f";color:{argb(st['fontColor'])}"
        if st.get("textAlign"):
            extra += f";text-align:{st['textAlign']}"
        if st.get("maxLines") == 1:
            extra += ";white-space:nowrap;overflow:hidden;text-overflow:ellipsis"
        elif st.get("maxLines"):
            extra += (f";display:-webkit-box;-webkit-line-clamp:{st['maxLines']};"
                      f"-webkit-box-orient:vertical;overflow:hidden")
        if st.get("height"):
            extra += ";display:flex;align-items:center"
        if st.get("width") and st.get("width") != "wrapContent":
            extra += ";box-sizing:border-box"
        return f'<div style="{css};{extra}" data-cid="{cid}" data-text="1">{html_escape(txt)}</div>'

    if comp == "Image":
        color = argb(st.get("fillColor"))
        return (f'<div style="{css}" data-cid="{cid}">'
                f'{svg_inline(c.get("src", ""), color)}</div>')

    if comp == "Button":
        label = c.get("label") or resolve(c.get("content", ""), data)
        extra = (f";display:flex;align-items:center;justify-content:center;"
                 f"font-size:{st.get('fontSize', 14):g}px;font-weight:{st.get('fontWeight', 500)}")
        if st.get("fontColor"):
            extra += f";color:{argb(st['fontColor'])}"
        return f'<div style="{css}{extra}">{html_escape(label)}</div>'

    if comp == "Checkbox":
        on = st.get("selected") or c.get("select") or False
        box = "✓" if on else ""
        return (f'<div style="{css};display:flex;align-items:center;gap:6px">'
                f'<span style="width:14px;height:14px;border:1px solid #888;'
                f'border-radius:3px;font-size:11px;line-height:14px;text-align:center">{box}</span>'
                f'<span style="font-size:12px">{html_escape(c.get("label", ""))}</span></div>')

    if comp == "Divider":
        return f'<div style="{css}"></div>'

    if comp == "Progress":
        size = st.get("width") or st.get("height") or 52
        w = size if isinstance(size, (int, float)) else 52
        sw = st.get("strokeWidth") or 6
        try:
            frac = max(0.0, min(1.0, float(c.get("value", 0)) / float(c.get("total") or 100)))
        except (TypeError, ValueError):
            frac = 0.0
        r = (w - sw) / 2
        circ = 2 * 3.14159265 * r
        col = argb(st.get("color") or "#FF1F4799")
        track = argb(st.get("backgroundColor") or "#331F4799")
        # 轨道色由 <circle stroke> 承担，div 本身不能有底色（否则圆外出现方块）
        return (f'<div style="width:{w}px;height:{w}px">'
                f'<svg viewBox="0 0 {w} {w}" style="width:100%;height:100%">'
                f'<circle cx="{w/2}" cy="{w/2}" r="{r}" fill="none" stroke="{track}" stroke-width="{sw}"/>'
                f'<circle cx="{w/2}" cy="{w/2}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}"'
                f' stroke-linecap="round" stroke-dasharray="{circ*frac:.2f} {circ:.2f}"'
                f' transform="rotate(-90 {w/2} {w/2})"/></svg></div>')

    if comp == "Text":
        txt = resolve(c.get("content", ""), data)
        fs = st.get("fontSize", 14)
        fw = st.get("fontWeight", 400)
        lh = st.get("lineHeight") or 1.25
        extra = f"font-size:{fs:g}px;font-weight:{fw};line-height:{lh}"
        if st.get("fontColor"):
            extra += f";color:{argb(st['fontColor'])}"
        if st.get("textAlign"):
            extra += f";text-align:{st['textAlign']}"
        if st.get("maxLines") == 1:
            extra += ";white-space:nowrap;overflow:hidden;text-overflow:ellipsis"
        elif st.get("maxLines"):
            extra += (f";display:-webkit-box;-webkit-line-clamp:{st['maxLines']};"
                      f"-webkit-box-orient:vertical;overflow:hidden")
        if st.get("height"):
            extra += ";display:flex;align-items:center"
        if st.get("width") and st.get("width") != "wrapContent":
            extra += ";box-sizing:border-box"
        return f'<div style="{css};{extra}" data-cid="{cid}" data-text="1">{html_escape(txt)}</div>'

    if comp == "Image":
        color = argb(st.get("fillColor"))
        return (f'<div style="{css}" data-cid="{cid}">'
                f'{svg_inline(c.get("src", ""), color)}</div>')

    if comp == "Button":
        label = c.get("label") or resolve(c.get("content", ""), data)
        extra = (f";display:flex;align-items:center;justify-content:center;"
                 f"font-size:{st.get('fontSize', 14):g}px;font-weight:{st.get('fontWeight', 500)}")
        if st.get("fontColor"):
            extra += f";color:{argb(st['fontColor'])}"
        return f'<div style="{css}{extra}">{html_escape(label)}</div>'

    if comp == "Checkbox":
        on = st.get("selected") or c.get("select") or False
        box = "✓" if on else ""
        return (f'<div style="{css};display:flex;align-items:center;gap:6px">'
                f'<span style="width:14px;height:14px;border:1px solid #888;'
                f'border-radius:3px;font-size:11px;line-height:14px;text-align:center">{box}</span>'
                f'<span style="font-size:12px">{html_escape(c.get("label", ""))}</span></div>')

    if comp == "Divider":
        return f'<div style="{css}"></div>'

    if comp == "Progress":
        size = st.get("width") or st.get("height") or 52
        w = size if isinstance(size, (int, float)) else 52
        ring = w * 0.9
        rgb = argb(st.get("color") or "#FF8C4B1C")
        # 轨道色由 <circle stroke> 承担，div 本身不能有底色（否则圆外出现方块）
        return (f'<div style="width:{w}px;height:{w}px">'
                f'<svg viewBox="0 0 {w} {w}" style="width:100%;height:100%">'
                f'<circle cx="{w/2}" cy="{w/2}" r="{ring/2}" fill="none" stroke="rgba(0,0,0,0.08)" stroke-width="4"/>'
                f'<circle cx="{w/2}" cy="{w/2}" r="{ring/2}" fill="none" stroke="{rgb}" stroke-width="4" '
                f'stroke-dasharray="{3.1416*ring*0.7:g} {3.1416*ring:g}" transform="rotate(-90 {w/2} {w/2})"/>'
                f'</svg></div>')

    kids = [emit(k, comps, data, comp, depth + 1) for k in (c.get("children") or [])]
    return f'<div style="{css}">{"".join(k for k in kids if k)}</div>'


def html_escape(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------------------------------------------------------------- 页面组装
def card_html(path: Path) -> tuple:
    comps, root, data = to_tree(load_msgs(path))
    if not comps or root is None:
        return '<div class="err">无法解析</div>', (150, 150)
    st = comps[root].get("styles") or {}
    w = st.get("width") if isinstance(st.get("width"), (int, float)) else 150
    h = st.get("height") if isinstance(st.get("height"), (int, float)) else 150
    body = emit(root, comps, data, "")
    return body, (w, h)


def frame(body: str, w, h) -> str:
    return (f'<div class="frame" style="width:{w*SCALE}px;height:{h*SCALE}px">'
            f'<div class="canvas" style="width:{w}px;height:{h}px;'
            f'transform:scale({SCALE});transform-origin:top left">{body}</div></div>')


def main():
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(RUNS.iterdir())[-1]
    if not run.is_absolute():
        run = RUNS / run.name
    idx = json.loads((run / "index.json").read_text(encoding="utf-8"))
    gold = {p["tag"]: p for p in json.loads(GOLD_PAIRS.read_text(encoding="utf-8"))["pairs"]}

    rows, n_skel, n_size, n_clean = [], 0, 0, 0
    for e in idx["files"]:
        tag = e["tag"]
        g = gold.get(tag, {})
        gskel = (g.get("gold") or {}).get("skeleton", "?")
        skel_ok = gskel == e.get("skeleton")
        size_ok = g.get("size") == e.get("size")
        clean = skel_ok and not e.get("fallback_log")
        n_skel += skel_ok
        n_size += size_ok
        n_clean += clean
        try:
            gbody, (gw, gh) = card_html(DSL_DIR / f"q{int(tag[1:])}.jsonl")
        except Exception as ex:                                    # 金标缺失也不炸
            gbody, (gw, gh) = f'<div class="err">{ex}</div>', (150, 150)
        obody, (ow, oh) = card_html(run / e["file"])
        badge = "ok" if clean else ("diff" if not skel_ok else "fb")
        fb = "；".join(e.get("fallback_log") or []) or "无"
        rows.append(f"""
<section class="case {badge}">
  <header>
    <b>{tag}</b>
    <span class="q">{html_escape(e.get('query',''))}</span>
    <span class="meta">{'骨架一致' if skel_ok else f'骨架 {gskel} → {e.get("skeleton")}'} ·
      {e.get('size')} · {e.get('theme','')} · fallback: {html_escape(fb)[:60]}</span>
  </header>
  <div class="pair">
    <figure><figcaption>金标 {gskel}</figcaption>{frame(gbody, gw, gh)}</figure>
    <figure><figcaption>本次 {e.get('skeleton')}</figcaption>{frame(obody, ow, oh)}</figure>
  </div>
</section>""")

    total = idx["files"]
    page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>卡片对比 · {run.name}</title>
<style>
:root{{--ink:#1d1d1f;--dim:#6b7280;--line:#e5e7eb;--bg:#f6f7f9;
  --ok:#0a7c4a;--warn:#b45309;--bad:#b42318}}
*{{box-sizing:border-box}}
body{{margin:0;padding:24px;background:var(--bg);color:var(--ink);
  font:14px/1.5 "HarmonyOS Sans","PingFang SC","Microsoft YaHei",system-ui,sans-serif}}
h1{{font-size:19px;margin:0 0 4px}}
.sub{{color:var(--dim);margin-bottom:14px}}
.stats{{display:flex;gap:22px;margin-bottom:14px;font-size:13px}}
.stats b{{font-size:20px;font-weight:700}}
.bar{{position:sticky;top:0;z-index:9;background:var(--bg);padding:10px 0 12px;
  display:flex;gap:8px;align-items:center;border-bottom:1px solid var(--line)}}
button{{border:1px solid var(--line);background:#fff;border-radius:8px;padding:6px 12px;
  font-size:13px;cursor:pointer}}
button.on{{background:var(--ink);color:#fff;border-color:var(--ink)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(700px,1fr));gap:16px;margin-top:16px}}
.case{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px 16px}}
.case header{{display:flex;flex-direction:column;gap:2px;margin-bottom:10px}}
.case header b{{font-size:14px}}
.q{{font-size:13px;color:#374151}}
.meta{{font-size:12px;color:var(--dim)}}
.case.ok .meta{{color:var(--ok)}}
.case.diff .meta{{color:var(--bad)}}
.case.fb .meta{{color:var(--warn)}}
.pair{{display:flex;gap:26px}}
figure{{margin:0}}
figcaption{{font-size:11px;color:var(--dim);margin-bottom:6px}}
.frame{{background:#fff;border-radius:20px;box-shadow:0 2px 10px #0000001a}}
.canvas{{background:#fff;border-radius:20px;overflow:hidden}}
.err{{color:var(--bad);font-size:12px;padding:10px}}
body.only-diff .case.ok{{display:none}}
</style></head><body>
<h1>金标 vs 本次产物 · {run.name}</h1>
<div class="sub">左＝人工校验的真实产物（金标），右＝本次真实模型跑出的结果。均为 {SCALE}× 缩放。
批跑模式：{idx.get('mode')} ｜ 完成于 {idx.get('finished_at')}</div>
<div class="stats">
  <span>骨架一致 <b>{n_skel}/{len(total)}</b></span>
  <span>尺寸一致 <b>{n_size}/{len(total)}</b></span>
  <span>完全一致（骨架+零 fallback）<b>{n_clean}/{len(total)}</b></span>
</div>
<div class="bar">
  <button id="all" class="on">全部 {len(total)}</button>
  <button id="diff">只看不一致 {len(total)-n_skel}</button>
  <span class="meta">卡片按 scale({SCALE}) 渲染；虚线框＝该图标文件缺失</span>
</div>
<div class="grid">{''.join(rows)}</div>
<script>
const a=document.getElementById('all'), d=document.getElementById('diff');
a.onclick=()=>{{document.body.classList.remove('only-diff');a.classList.add('on');d.classList.remove('on')}};
d.onclick=()=>{{document.body.classList.add('only-diff');d.classList.add('on');a.classList.remove('on')}};
</script></body></html>"""
    OUT.write_text(page, encoding="utf-8")
    print(f"✅ {OUT}")
    print(f"   骨架一致 {n_skel}/{len(total)} ｜ 尺寸一致 {n_size}/{len(total)} ｜ 完全一致 {n_clean}/{len(total)}")


if __name__ == "__main__":
    main()
