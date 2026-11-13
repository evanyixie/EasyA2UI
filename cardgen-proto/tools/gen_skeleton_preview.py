#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""骨架可视化生成器（调试工具，独立于流水线）。

读取 rules/skeletons.json + rules/themes.json，生成自包含的
viz/skeleton_preview.html：全部骨架（S1~S7 / W1~W10）的线框图阵列（vp×2 缩放），
支持 线框/主题 双模式切换、悬停查看节点样式、槽位虚线占位与拟真填充。

用法：python viz/gen_skeleton_preview.py   （产物用浏览器打开）
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "runs" / "viz" / "skeleton_preview.html"


def natural_key(sid: str):
    """S1..S4 / W1..W10 按数字自然排序（W10 排在 W2 后面）。"""
    m = re.match(r"([SW])(\d+)", sid)
    return (0 if m and m.group(1) == "S" else 1, int(m.group(2)) if m else 99)


def main():
    skels = json.loads((ROOT / "rules/skeletons.json").read_text(encoding="utf-8"))
    themes = json.loads((ROOT / "rules/themes.json").read_text(encoding="utf-8"))
    order = sorted(skels["skeletons"].keys(), key=natural_key)
    data = {"skeletons": skels["skeletons"], "themes": themes["themes"],
            "selection": themes.get("selection", {}), "order": order}
    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    print(f"已生成 {OUT}（共 {len(order)} 个骨架，浏览器打开即可）")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>cardgen-proto 骨架可视化</title>
<style>
  body { font-family: "Microsoft YaHei", sans-serif; margin: 16px; background: #f7f8fa; color: #333; }
  h1 { font-size: 20px; }
  .controls { margin: 12px 0 20px; display: flex; gap: 16px; align-items: center; }
  .controls label { font-size: 14px; }
  .grid { display: flex; flex-wrap: wrap; gap: 28px; }
  .card-wrap { background: #fff; border: 1px solid #e3e5e8; border-radius: 10px; padding: 14px; }
  .card-title { font-size: 15px; font-weight: 700; margin-bottom: 2px; }
  .card-desc { font-size: 12px; color: #777; margin-bottom: 10px; max-width: 640px; }
  .canvas { border: 2px solid #444; background: #fff; position: relative; }
  .meta { font-size: 12px; color: #555; margin-top: 8px; line-height: 1.7; }
  .meta code { background: #f0f2f5; padding: 1px 5px; border-radius: 4px; }
  .node { position: relative; box-sizing: border-box; display: flex; }
  body.wire .container { outline: 1px dashed #c3c3c3; outline-offset: -1px; }
  body.wire .slot-chip { display: block; }
  .slot-chip { display: none; position: absolute; top: 0; left: 0; z-index: 5;
               font-size: 10px; background: #fff8e1; color: #8a6d00;
               border: 1px solid #e0c96b; padding: 0 4px; border-radius: 0 0 4px 0; }
  .ph { box-sizing: border-box; display: flex; }
  .txt { white-space: nowrap; overflow: hidden; }
</style>
</head>
<body class="wire">
<h1>cardgen-proto 骨架可视化（14 骨架 · 线框图）</h1>
<div class="controls">
  <label><input type="radio" name="mode" value="wire" checked onchange="setMode('wire')"> 线框模式</label>
  <label><input type="radio" name="mode" value="theme" onchange="setMode('theme')"> 主题着色模式</label>
  <label>主题：
    <select id="themeSel" onchange="setMode(currentMode)">
      <option value="blue">blue（蓝）</option>
      <option value="purple">purple（紫）</option>
      <option value="warm">warm（暖）</option>
      <option value="dark">dark（深色）</option>
    </select>
  </label>
  <span style="font-size:12px;color:#888">缩放：vp × 2 ｜ 悬停任意框可查看节点 id 与样式</span>
</div>
<div class="grid" id="grid"></div>

<script>
const DATA = __DATA__;
const SCALE = 2;
const SKELETONS = DATA.skeletons;
const ORDER = DATA.order;
let currentMode = "wire";
let currentSize = "2x2";

const WIRE = { primary_text: "#555", meta_text: "#999", action_bg: "#e3e3e3",
               backboard: "#f2f2f2", rootBg: "#ffffff" };
const GRAD_DIR = { RightBottom: "to bottom right", LeftBottom: "to bottom left",
                   RightTop: "to top right", LeftTop: "to top left",
                   Right: "to right", Bottom: "to bottom" };

function colors() {
  if (currentMode === "theme") {
    const t = DATA.themes[document.getElementById("themeSel").value];
    return { primary_text: t.palette.roles.primary_text,
             meta_text: t.palette.roles.meta_text,
             action_bg: t.palette.roles.action_bg,
             backboard: t.palette.backboard["2x2"],
             gradient: t.palette.gradient,
             rootBg: null };
  }
  return WIRE;
}

function len(v) { return typeof v === "number" ? (v * SCALE) + "px"
    : v === "matchParent" ? "100%"   // ArkUI matchParent -> CSS 百分比（非法值会被浏览器忽略导致高度塌缩）
    : v; }

function padCss(p) {
  if (typeof p === "number") return (p * SCALE) + "px";
  if (p && typeof p === "object")
    return `${(p.top||0)*SCALE}px ${(p.right||0)*SCALE}px ${(p.bottom||0)*SCALE}px ${(p.left||0)*SCALE}px`;
  return null;
}

function align(v) {
  return { start: "flex-start", top: "flex-start", end: "flex-end", bottom: "flex-end", center: "center" }[v] || v;
}

function nodeCss(node) {
  const s = node.styles || {}, c = [], C = colors();
  if (s.width) c.push(`width:${len(s.width)}`);
  if (s.height) c.push(`height:${len(s.height)}`);
  const p = padCss(s.padding); if (p) c.push(`padding:${p}`);
  if (s.borderRadius) c.push(`border-radius:${s.borderRadius * SCALE}px`);
  if (s.clip) c.push("overflow:hidden");
  if (s.layoutWeight) { c.push(`flex-grow:${s.layoutWeight}`); c.push("flex-basis:0"); }
  if (s.flexShrink !== undefined) c.push(`flex-shrink:${s.flexShrink}`);
  if (s.itemMargin) c.push(`gap:${s.itemMargin * SCALE}px`);
  if (s.alignItems) c.push(`align-items:${align(s.alignItems)}`);
  if (s.justifyContent) c.push(`justify-content:${align(s.justifyContent)}`);
  if (s.linearGradient) {
    const g = s.linearGradient;
    c.push(`background:linear-gradient(${GRAD_DIR[g.direction] || "to bottom right"},` +
           g.colors.map(x => `${x[0]} ${(x[1]||0)*100}%`).join(",") + ")");
  }
  if (s.background === "gradient") {           // 语义 token：根渐变
    if (currentMode === "theme") {
      const g = C.gradient;
      c.push(`background:linear-gradient(${GRAD_DIR[g.direction] || "to bottom right"},` +
             g.colors.map(x => `${x[0]} ${(x[1]||0)*100}%`).join(",") + ")");
    }
  }
  if (s.backgroundColor === "backboard") {     // 语义 token：白背板
    c.push(`background-color:${currentMode === "theme" ? (C.backboard[currentSize] || C.backboard["2x2"]) : "#f1f1f1"}`);
  } else if (s.backgroundColor) {
    c.push(`background-color:${s.backgroundColor}`);
  }
  if (node.component === "Row" || node.component === "Column" || node.component === "List") {
    c.push("display:flex");
    c.push(`flex-direction:${node.component === "Row" ? "row" : "column"}`);
  }
  if (node.component === "Stack") { c.splice(0, 0, "display:grid"); c.push("place-content:center"); }
  return c.join(";");
}

function fs(fp) { return (fp * SCALE) + "px"; }

function txt(t, fp, weight, color) {
  return `<div class="txt" style="font-size:${fs(fp)};font-weight:${weight};color:${color}">${t}</div>`;
}

function iconBox(C) {
  return `<div class="ph" title="图标位 20×20" style="width:${20*SCALE}px;height:${20*SCALE}px;` +
         `border:1px dashed ${C === WIRE ? "#bbb" : C.primary_text};border-radius:4px;` +
         `align-self:center;justify-content:center;align-items:center;color:${C.meta_text};font-size:10px">图</div>`;
}

function capsule(label, C) {
  return `<div class="ph" style="flex:1;height:${36*SCALE}px;border-radius:${18*SCALE}px;` +
         `background:${C.action_bg};justify-content:center;align-items:center">` +
         txt(label, 14, 400, C.primary_text) + `</div>`;
}

function slotContent(slot) {
  const C = colors();
  const line = (t, fp, w, col) => txt(t, fp, w, col || C.primary_text);
  switch (true) {
    case slot === "header":
      return `<div class="ph" style="align-items:center;gap:${8*SCALE}px;width:100%">` +
             txt("标题", 12, 400, C.primary_text) + iconBox(C) + `</div>`;
    case slot === "content":
      return `<div class="ph" style="flex-direction:column;width:100%;gap:${2*SCALE}px">` +
             line("正文要点", 18, 700) + line("辅助信息 xxxxxxx", 14, 500) + `</div>`;
    case slot === "hero":
      return `<div class="ph" style="flex-direction:column;align-items:center;gap:${2*SCALE}px;width:100%">` +
             txt("8888", 30, 700, C.primary_text) + txt("单位", 12, 400, C.meta_text) + `</div>`;
    case slot === "action":
      return `<div class="ph" style="flex-direction:column;width:100%;gap:${6*SCALE}px">` +
             capsule("按钮", C) + `</div>`;
    case slot.startsWith("zone:"):
      return `<div class="ph" style="width:100%;align-items:center">` +
             `<div class="ph" style="flex-direction:column;flex:1;gap:${2*SCALE}px">` +
             line("对象名 888", 14, 700) + line("辅助信息 | xxxxxxx", 12, 400) + `</div>` +
             iconBox(C) + `</div>`;
    case slot.startsWith("aux:"):
      return `<div class="ph" style="flex-direction:column;width:100%;justify-content:center;gap:${2*SCALE}px">` +
             line("辅助信息", 14, 700) + line("xxxxxxx", 12, 400) + `</div>`;
    case slot.startsWith("action_zone:"):
      return `<div class="ph" style="width:100%;justify-content:center">` +
             txt("动作入口", 14, 500, C.primary_text) + `</div>`;
    case slot === "list":
      return `<div class="ph" style="flex-direction:column;width:100%;gap:${8*SCALE}px">` +
             [0,1,2].map(() => `<div class="ph" style="height:${28*SCALE}px;border-radius:${8*SCALE}px;` +
               `background:${currentMode === "theme" ? C.backboard : "#f0f0f0"};align-items:center;` +
               `padding:0 ${12*SCALE}px">` + txt("列表项 xxxxxxx", 12, 400, C.primary_text) + `</div>`).join("") +
             `</div>`;
    case slot === "text_flow":
      return `<div class="ph" style="flex-direction:column;width:100%;gap:${8*SCALE}px">` +
             line("正文 xxxxxxx", 14, 500) + line("正文 xxxxxxx", 14, 500) + line("正文 xxxxxxx", 12, 400, C.meta_text) + `</div>`;
    case slot === "triple":
      return `<div class="ph" style="width:100%;justify-content:space-evenly">` +
             [0,1,2].map(() => `<div class="ph" style="flex-direction:column;align-items:center;gap:${2*SCALE}px">` +
               txt("888", 20, 700) + txt("指标", 12, 400, C.meta_text) + `</div>`).join("") + `</div>`;
    case slot === "ring":
      return `<div class="ph" style="width:${92*SCALE}px;height:${92*SCALE}px;border:2px dashed ` +
             `${currentMode === "theme" ? C.primary_text : "#aaa"};border-radius:50%;` +
             `justify-content:center;align-items:center">` + txt("88%", 16, 700) + `</div>`;
    case slot === "progress":
      return `<div class="ph" style="width:100%;height:${8*SCALE}px;border-radius:${4*SCALE}px;` +
             `background:${currentMode === "theme" ? C.action_bg : "#e0e0e0"}"></div>`;
    default:
      return `<div class="ph" style="width:100%;justify-content:center">` +
             txt("xxxxxxx", 14, 400, C.meta_text) + `</div>`;
  }
}

function renderNode(node, depth) {
  const css = nodeCss(node);
  const isContainer = ["Row", "Column", "List", "Stack"].includes(node.component);
  const title = `${node.id} | ${node.component} | ${JSON.stringify(node.styles || {})}`;
  const chip = node.slot ? `<span class="slot-chip">slot: ${node.slot}${node.optional ? "（可选）" : ""}</span>` : "";
  const styleAttr = css ? ` style="${css}"` : "";
  const cls = "node " + (isContainer ? "container" : "ph");
  let inner = "";
  if (node.slot) {
    inner = slotContent(node.slot);
    if (!inner) inner = "";
  } else if (node.children) {
    inner = node.children.map(ch => renderNode(ch, depth + 1)).join("");
  }
  return `<div class="${cls}"${styleAttr} title="${title.replace(/"/g, "&quot;")}">${chip}${inner}</div>`;
}

function renderAll() {
  const grid = document.getElementById("grid");
  const parts = [];
  for (const sid of ORDER) {
    const sk = SKELETONS[sid];
    const sel = sk.select || {};
    const selTxt = [`对象 ${sel.objects ? sel.objects[0] + "~" + sel.objects[1] : "-"}`,
                    `动作 ${sel.actions ? sel.actions[0] + "~" + sel.actions[1] : "-"}`,
                    sel.features ? "特征: " + sel.features.join("/") : ""].filter(Boolean).join(" ｜ ");
    const slots = [];
    (function walk(n) { if (n.slot) slots.push(n.slot + (n.optional ? "(可选)" : "")); (n.children||[]).forEach(walk); })(sk.tree);
    const size = sk.size === "2x4" ? [600, 300] : [300, 300];
    currentSize = sk.size;
    parts.push(`<div class="card-wrap">
      <div class="card-title">${sid}</div>
      <div class="card-desc">${sk.desc || ""}</div>
      <div class="canvas" style="width:${size[0]}px;height:${size[1]}px">${renderNode(sk.tree, 0)}</div>
      <div class="meta">尺寸 <b>${sk.size}</b> ｜ 优先级 ${sk.priority || "-"}${sk.fallback ? " ｜ <b>兜底骨架</b>" : ""}<br>
        路由：${selTxt}<br>槽位：${slots.map(s => `<code>${s}</code>`).join(" ")}</div>
    </div>`);
  }
  grid.innerHTML = parts.join("");
}

function setMode(m) {
  currentMode = m;
  document.body.className = m === "wire" ? "wire" : "";
  renderAll();
}

renderAll();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
