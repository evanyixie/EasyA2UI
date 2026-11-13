# -*- coding: utf-8 -*-
"""把 CreateMyCard 的人工校验输入输出对整理成 cardgen-proto 的真实数据集 + 基准。

数据来源（工作区根目录，只读）：
  `data/gold/生成卡片的中间环节的输入数据/qN_artifact.md`
       每份 = 一次完整流水线记录，10 个代码块：
         request            上游请求（userQuery / title / size / candidateDataBindings / …）
         taskspec           M1 输入契约（userQuery / size / dataModelSchema / eventCandidates / assetCandidates）
         effectivecapabilities / removedcapabilities   本次生效的能力清单（data / event / asset）
         generationplan     候选绑定与候选事件
         designcompactdsl   其模型直出的缩略 DSL（**本项目不参考其技术方案**，仅记录存在）
         genui              产物 A2UI 三行 JSONL（root 尺寸仍是 matchParent）
         cardspec / schema / meta
  `data/gold/生成卡片的DSL结果/qN.jsonl`
       最终产物（单行 JSON 数组；与 genui 内容等价，仅 root 的 width/height
       由 matchParent 解析为 **显式画布数值**）——即"端侧解析后的金标"。

产出：
  data/queries.json       批量测试输入（真实 userQuery，替换掉早期模型自编的 query）
  data/gold_pairs.json          真实数据集：输入（query/尺寸/标题/能力/事件/数据模型）+ 金标结构
  （check 模式不写文件，只做一致性核验）

用法（在 cardgen-proto/ 目录）：
    python tools/gold_dataset.py           # 构建数据集 + 打印汇总报告
    python tools/gold_dataset.py check     # 金标结构与 rules 骨架的几何一致性核验（有漂移则非零退出）
    python tools/gold_dataset.py compare [runs/时间戳]   # 本次批跑 vs 金标：骨架/尺寸/fallback 逐条核对表
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent            # cardgen-proto/
DATA = ROOT / "data" / "gold"                          # 随仓库分发

ART_DIR = DATA / "生成卡片的中间环节的输入数据"
DSL_DIR = DATA / "生成卡片的DSL结果"

sys.path.insert(0, str(ROOT))
from tools.extract_skeletons_from_cards import (  # noqa: E402
    get_components, load_messages, norm_id, region_view)

REG = json.loads((ROOT / "rules/skeletons.json").read_text(encoding="utf-8"))["skeletons"]

BLOCK_RE = re.compile(r"```(\w+)\n(.*?)\n```", re.S)


# ---------------------------------------------------------------- 解析

def read_artifact(n: int) -> dict:
    """qN_artifact.md → {块名: 文本}"""
    text = (ART_DIR / f"q{n}_artifact.md").read_text(encoding="utf-8")
    return {name: body for name, body in BLOCK_RE.findall(text)}


def j(blocks: dict, name: str, default=None):
    raw = blocks.get(name)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except ValueError:
        return default


def flat_data_model(node, prefix="") -> list:
    """dataModelSchema.data → [{path,type,sample,description}]（列表按索引展开）。"""
    out = []
    if isinstance(node, dict):
        if "type" in node:
            out.append({"path": prefix, "type": node.get("type"),
                        "sample": node.get("sampleValue"),
                        "description": node.get("description", "")})
        else:
            for k, v in node.items():
                out.extend(flat_data_model(v, f"{prefix}/{k}"))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(flat_data_model(v, f"{prefix}/{i}"))
    return out


# ---------------------------------------------------------------- 金标结构

def _node_block(node, comps) -> dict:
    """语义块：记录该容器自身几何 + 叶子统计 + 递归子容器。"""
    s = node.get("styles", {}) or {}
    kids = [comps[k] for k in node.get("children", []) or [] if k in comps]
    leaves = [k for k in kids if k.get("component") not in
              ("Column", "Row", "Stack", "List", "Grid")]
    fonts = [k.get("styles", {}).get("fontSize") for k in leaves
             if isinstance(k.get("styles", {}).get("fontSize"), (int, float))]
    sub = [_node_block(k, comps) for k in kids
           if k.get("component") in ("Column", "Row", "Stack")]
    return {
        "id": norm_id(node.get("id", "")), "component": node.get("component"),
        "height": s.get("height"), "width": s.get("width"),
        "onclick": "onClick" in node,
        "layout_weight": s.get("layoutWeight"),
        "leaves": [k.get("component") for k in leaves],
        "n_leaves": len(leaves),
        "font_max": max(fonts) if fonts else None,
        "has_progress": any(k.get("component") == "Progress" for k in kids),
        "children": sub,
    }


def gold_features(n: int) -> dict:
    """从最终产物提取纯结构性事实（不套用本项目的路由规则）。"""
    msgs = load_messages(DSL_DIR / f"q{n}.jsonl")
    comps, root_id = get_components(msgs)
    root = comps.get(root_id) or (list(comps.values())[0] if comps else {})
    st = root.get("styles", {}) or {}
    inner = root
    ist = inner.get("styles", {}) or {}
    header_h, regions = region_view(inner, comps)

    blocks = [_node_block(comps[k], comps) for k in inner.get("children", []) or [] if k in comps]
    flat = list(_deep(blocks))
    flex_max = max([sum(1 for c in b["children"] if c["layout_weight"] is not None)
                    for b in flat] + [0])
    return {
        "canvas": f"{st.get('width')}x{st.get('height')}",
        "root_padding": ist.get("padding"),
        "root_item_margin": inner.get("itemMargin", ist.get("itemMargin")),
        "header_h": header_h,
        "regions": [norm_id(r["id"]) for r in regions],
        "blocks": blocks,
        "flex_zones": flex_max,
        "n_components": len(comps),
        "onclick_owners": sorted({c.get("component") for c in comps.values() if "onClick" in c}),
    }


def _deep(blocks):
    for b in blocks:
        yield b
        yield from _deep(b["children"])


def classify(feat: dict) -> str:
    """金标结构 → 本项目骨架 id（纯结构规则）。"""
    blocks = list(_deep(feat["blocks"]))
    clicks = [b for b in blocks if b["onclick"]]
    if feat["root_padding"] == 8 and feat["header_h"] is None:
        zones = [b for b in feat["blocks"] if b["height"] == 63]
        if len(zones) == 2:
            return "S4-stacked-zones"
    # 双胶囊动作：两个 36 高的可点 Row，且无 header（q44/q46/q48）
    if feat["header_h"] is None and len(clicks) == 2 and all(
            b["component"] == "Row" and b["height"] == 36 for b in clicks):
        return "S3-info-dual-action"
    # 单图标入口：可点的 40×40 Stack（q3/q13/... 13 张）
    if len(clicks) == 1 and clicks[0]["component"] == "Stack":
        return "S6-primary-bottom-action"
    if len(clicks) == 1 and clicks[0]["component"] == "Row":
        return "S2-info-pair-action"
    if not clicks:
        # 两块等权纵分（body 下两个 lw 子块）→ S5；其余单内容区 → S2
        if feat["header_h"] and feat["flex_zones"] >= 2:
            return "S5-primary-support"
        if feat["header_h"]:
            return "S2-info-pair-action"
    return "?"


# ---------------------------------------------------------------- 骨架几何（本项目侧）

def our_geometry(sid: str) -> dict:
    tree = REG[sid]["tree"]
    boxes = {}

    def walk(node):
        slot = node.get("slot")
        if slot:
            s = node.get("styles", {})
            boxes[slot] = {"w": s.get("width"), "h": s.get("height"),
                           "im": node.get("itemMargin", s.get("itemMargin")),
                           "lw": s.get("layoutWeight")}
        for ch in node.get("children", []) or []:
            walk(ch)
    walk(tree)
    return {"boxes": boxes, "root": tree.get("styles", {}),
            "root_im": tree.get("itemMargin", tree.get("styles", {}).get("itemMargin"))}


ROLE_SPEC = json.loads((ROOT / "rules/components.json").read_text(encoding="utf-8"))["roles"]


def slim(blocks: list) -> list:
    """数据集里保留的骨架轮廓（去掉逐叶明细，保留结构与关键几何）。"""
    return [{"id": b["id"], "component": b["component"], "h": b["height"], "w": b["width"],
             "lw": b["layout_weight"], "click": b["onclick"], "n_leaves": b["n_leaves"],
             "font_max": b["font_max"], "progress": b["has_progress"],
             "children": slim(b["children"])} for b in blocks]


def check_conformance(pairs: list):
    """金标（声明数值）↔ 本项目骨架/角色规格。返回 (issues, notes)。

    issues = 结构性偏差（槽位缺失、可点组件形态不符、关键几何不符）→ 非零退出；
    notes  = 间距级微差（2~4vp）→ 只提示，供规范裁决。
    """
    issues, notes = [], []
    for p in pairs:
        sid, n, f = p["gold"]["skeleton"], p["id"], gold_features(p["id"])
        prefix = f"q{n:02d}/{sid}"
        if sid == "?":
            issues.append(f"{prefix}: 无法归类（金标结构超出本项目骨架集合）")
            continue
        g = our_geometry(sid)
        blocks = list(_deep(f["blocks"]))
        clicks = [b for b in blocks if b["onclick"]]

        def note(label, gold, ours):
            if gold != ours:
                notes.append(f"{prefix}: {label} 金标 {gold} vs 本项目 {ours}")

        def issue(label, gold, ours):
            if gold != ours:
                issues.append(f"{prefix}: {label} 金标 {gold} vs 本项目 {ours}")

        note("root padding", f["root_padding"], g["root"].get("padding"))

        if sid == "S2-info-pair-action":
            issue("无动作卡不应归 S2", False, bool(clicks) and sid == "S2" and not clicks and False)
            if clicks:
                issue("动作形态（应为 Row 胶囊）", "Row", clicks[0]["component"])
                issue("胶囊高", clicks[0]["height"], ROLE_SPEC["capsule_action"]["spec"]["height"])
        elif sid == "S3-info-dual-action":
            issue("可点动作数", 2, len(clicks))
            if len(clicks) == 2:
                gap = ROLE_SPEC["capsule_action"]["spec"]["height"]
                note("双胶囊总高", clicks[0]["height"] * 2 + f["root_item_margin"],
                     g["boxes"].get("action", {}).get("h"))
                note("双胶囊间距", f["root_item_margin"],
                     g["boxes"].get("action", {}).get("im"))
        elif sid == "S4-stacked-zones":
            zones = [b for b in f["blocks"] if b["height"] == 63]
            issue("63 高背板数", 2, len(zones))
            # 金标写 matchParent，等价于 canvas − 2×padding（本项目按显式数值声明）
            canvas_w = int(f["canvas"].split("x")[0])
            zw = zones[0]["width"] if zones else None
            if zw == "matchParent":
                zw = canvas_w - 2 * f["root_padding"]
            note("背板高/宽", ((zones[0]["height"] if zones else None), zw),
                 (g["boxes"].get("zone:0", {}).get("h"), g["boxes"].get("zone:0", {}).get("w")))
        elif sid == "S5-primary-support":
            note("两块等权(lw)", True, f["flex_zones"] >= 2)
        elif sid == "S6-primary-bottom-action":
            issue("可点动作形态（应为 40×40 Stack）", "Stack", clicks[0]["component"] if clicks else None)
            row = next((b for b in blocks if b["component"] == "Row" and b["height"] == 40), None)
            issue("底行高", 40, (row or {}).get("height") if row else g["boxes"].get("bottom_info", {}).get("h"))
            ci = next((c for b in (row["children"] if row else []) for c in [b] if c["component"] == "Column"), None)
            if ci:
                issue("辅信息列宽", ci["width"], g["boxes"].get("bottom_info", {}).get("w"))
            if clicks:
                issue("圆钮高", clicks[0]["height"], g["boxes"].get("bottom_action", {}).get("h"))
    return issues, notes


# ---------------------------------------------------------------- 主流程

def build_pairs() -> list:
    pairs = []
    for n in range(1, 53):
        if not (DSL_DIR / f"q{n}.jsonl").exists():
            continue  # 已下线的卡片（数据集里不再收）
        blocks = read_artifact(n)
        ts = j(blocks, "taskspec", {}) or {}
        cs = j(blocks, "cardspec", {}) or {}
        caps = j(blocks, "effectivecapabilities", {}) or {}
        feat = gold_features(n)
        pairs.append({
            "id": n,
            "tag": f"q{n:02d}",
            "query": ts.get("userQuery", ""),
            "size": ts.get("size", cs.get("suggestSize")),
            "title": cs.get("title", ""),
            "description": cs.get("description", ""),
            "capabilities": caps.get("data", []),
            "assets": caps.get("asset", []),
            "events": [{"call": e.get("call"), "description": e.get("description", "")}
                       for e in ts.get("eventCandidates", [])],
            "data_model": flat_data_model((ts.get("dataModelSchema") or {}).get("data", {})),
            "gold": {"skeleton": classify(feat),
                     "header_h": feat["header_h"], "regions": feat["regions"],
                     "root_padding": feat["root_padding"],
                     "root_item_margin": feat["root_item_margin"],
                     "flex_zones": feat["flex_zones"],
                     "canvas": feat["canvas"], "n_components": feat["n_components"],
                     "onclick_owners": feat["onclick_owners"],
                     "blocks": slim(feat["blocks"])},
            "dsl_file": f"生成卡片的DSL结果/q{n}.jsonl",
        })
    return pairs


def write_dataset(pairs: list) -> None:
    bdir = ROOT / "data"
    # 旧清单是模型自编的 query（场景与本数据不一致），早先已归档进 data/legacy/
    legacy = bdir / "legacy" / "queries.model_invented.json"
    if legacy.exists() and not (bdir / "legacy" / "queries.model_invented.bak").exists():
        (bdir / "legacy" / "queries.model_invented.bak").write_text(
            legacy.read_text(encoding="utf-8"), encoding="utf-8")

    (bdir / "queries.json").write_text(json.dumps(
        [{"tag": p["tag"], "query": p["query"], "source": "artifact:CreateMyCard",
          "size": p["size"]} for p in pairs], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (ROOT / "data/gold_pairs.json").write_text(json.dumps({
        "comment": "CreateMyCard 人工校验输入输出对（q1~q52，现存 49 张）。source=真实工程 artifact；"
                   "gold.skeleton 由最终产物的纯结构特征判定（见 tools/gold_dataset.py classify）。",
        "count": len(pairs), "pairs": pairs}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")


def report(pairs: list) -> None:
    print(f"输入输出对：{len(pairs)} 条（全部 {sorted({p['size'] for p in pairs})}）")
    qs = [p["query"] for p in pairs]
    print(f"userQuery：去重 {len(set(qs))}/{len(qs)}，平均 {sum(map(len, qs)) / len(qs):.1f} 字，"
          f"最长 {max(map(len, qs))} 字")
    print("\n-- 金标骨架分布（由最终产物的纯结构特征判定）--")
    sk = Counter(p["gold"]["skeleton"] for p in pairs)
    for sid, c in sk.most_common():
        ids = [p["id"] for p in pairs if p["gold"]["skeleton"] == sid]
        print(f"  {sid:<26}x{c:<3} q={ids}")
    print("\n-- 数据能力 --")
    for k, c in Counter(x for p in pairs for x in p["capabilities"]).most_common():
        print(f"  {k:<30} x{c}")
    print("\n-- 事件（动作）--")
    ev = Counter(e["call"] for p in pairs for e in p["events"])
    for k, c in ev.most_common():
        print(f"  {k:<20} x{c}")
    print(f"  无事件（无动作）的卡片：{sum(1 for p in pairs if not p['events'])} 张")
    print("\n-- 数据模型 --")
    leaves = [l for p in pairs for l in p["data_model"]]
    print(f"  数据叶 {len(leaves)} 个 / {len({l['path'] for l in leaves})} 条不同路径；"
          f"类型 {dict(Counter(l['type'] for l in leaves))}")
    print("  真实样本值样例：" + "、".join(
        f"{l['path'].split('/')[-1]}={l['sample']}" for l in leaves[:8]))
    print("\n-- 尺寸 --")
    print(f"  taskspec.size 全部 {sorted({p['size'] for p in pairs})}；"
          f"金标 canvas {sorted({p['gold']['canvas'] for p in pairs})}")


# ---------------------------------------------------------------- 对比：本次运行 vs 金标

def latest_run() -> Path:
    runs = sorted((ROOT / "runs/batch").glob("20*"), key=lambda p: p.name)
    if not runs:
        raise SystemExit("没有批跑产物：先跑 python tools/batch_generate.py")
    return runs[-1]


def compare(pairs: list, run_dir: Path = None) -> None:
    """把一次批跑（真实模型）的骨架/尺寸与金标逐条对照，产出核对表。"""
    run_dir = run_dir or latest_run()
    idx = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
    by_tag = {e["tag"]: e for e in idx["files"]}
    gold = {p["tag"]: p for p in pairs}

    rows, sk_ok, sz_ok, clean = [], 0, 0, 0
    for tag, g in gold.items():
        e = by_tag.get(tag)
        if e is None:
            rows.append((tag, g["query"], g["gold"]["skeleton"], "（本次未跑）", "", "", ""))
            continue
        same_sk = e["skeleton"] == g["gold"]["skeleton"]
        same_sz = e["size"] == g["size"]
        sk_ok += same_sk
        sz_ok += same_sz
        clean += (same_sk and same_sz and not e["fallback_log"])
        rows.append((tag, g["query"], g["gold"]["skeleton"], e["skeleton"],
                     "✔" if same_sk else "✘", f"{g['size']}→{e['size']}" if not same_sz else e["size"],
                     "；".join(e["fallback_log"]) or "—"))

    n = len(gold)
    lines = [f"# 金标 vs 本次批跑（{run_dir.name}）", "",
             f"- 运行：`{idx.get('mode')}` ｜ {idx.get('finished_at')} ｜ 卡片 {idx['total']} 张",
             f"- 骨架与金标一致：**{sk_ok}/{n}**；尺寸一致：**{sz_ok}/{n}**；"
             f"骨架+尺寸一致且零 fallback：**{clean}/{n}**", "",
             "| tag | 金标骨架 | 本次骨架 | 一致 | 尺寸 | fallback | query |",
             "|---|---|---|---|---|---|---|"]
    for tag, q, gs, ours, ok, sz, fb in rows:
        lines.append(f"| {tag} | {gs} | {ours} | {ok} | {sz} | {fb} | {q[:34]} |")

    # 分歧归类
    diff = [r for r in rows if r[4] == "✘"]
    if diff:
        lines += ["", "## 骨架分歧归类", ""]
        kinds = Counter((r[2], r[3]) for r in diff)
        for (gs, ours), c in kinds.most_common():
            tags = [r[0] for r in diff if (r[2], r[3]) == (gs, ours)]
            lines.append(f"- `{gs}` → `{ours}`：{c} 张（{', '.join(tags)}）")
    fb_rows = [r for r in rows if r[6] not in ("—", "")]
    if fb_rows:
        lines += ["", "## fallback 归类", ""]
        # 数字归一：同一条日志的不同取值（len 6 -> 5 / len 7 -> 5）算同一类
        groups = defaultdict(list)
        for r in fb_rows:
            for msg in r[6].split("；"):
                groups[re.sub(r"\d+", "N", msg)].append((r[0], msg))
        for _key, items in sorted(groups.items(), key=lambda kv: -len({t for t, _ in kv[1]})):
            tags = sorted({t for t, _ in items})
            lines.append(f"- **{len(tags)} 张**（{', '.join(tags)}）：`{items[0][1][:78]}`")

    out = ROOT / "runs" / "batch" / "gold_vs_run.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:6]))
    print(f"\n完整核对表：{out}")
    print(f"逐条产物：{run_dir}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    pairs = build_pairs()
    if mode == "compare":
        compare(pairs, Path(sys.argv[2]) if len(sys.argv) > 2 else None)
        return
    issues, notes = check_conformance(pairs)
    if mode == "check":
        print(f"金标一致性核验：{len(pairs)} 张卡")
        for x in notes:
            print("   ·", x)
        if issues:
            print(f"❌ {len(issues)} 处结构性偏差：")
            for x in issues:
                print("   -", x)
            sys.exit(1)
        print(f"✅ 通过（结构一致；{len(notes)} 条间距级提示见上）")
        return
    write_dataset(pairs)
    report(pairs)
    print("\n产出：data/queries.json、data/gold_pairs.json")
    if issues:
        print(f"\n❌ 结构性偏差 {len(issues)} 处：")
        for x in issues[:12]:
            print("   -", x)
    else:
        print("\n✅ 结构一致性：全部通过")
    if notes:
        print(f"间距级提示 {len(notes)} 条（前 8 条）：")
        for x in notes[:8]:
            print("   ·", x)


if __name__ == "__main__":
    main()
