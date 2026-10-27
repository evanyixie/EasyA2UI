# -*- coding: utf-8 -*-
"""遍历高质量卡片的 A2UI DSL，抽取每张卡片的「骨架签名」并分组。

签名 = 根尺寸 + 容器拓扑（含关键几何）+ 叶子类型统计 + 数据根。
用法：
    python tools/extract_skeletons_from_cards.py [卡片目录]
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_DIR = Path(r"F:\playground\workbuddy\nextgenui")
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "gold"
CARDS_DIR = DATA / "生成卡片的DSL结果"

CONTAINERS = {"Column", "Row", "Stack", "List", "Grid", "Flex"}
BINDING = re.compile(r"\$\{/data/([A-Za-z0-9_]+)")


def load_messages(path: Path):
    """兼容两种形态：单行 JSON 数组 / 多行 JSONL。"""
    text = path.read_text(encoding="utf-8").strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        out = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out


def get_components(messages):
    for m in messages:
        if isinstance(m, dict) and "updateComponents" in m:
            uc = m["updateComponents"]
            comps = uc.get("components") or []
            return {c["id"]: c for c in comps}, uc.get("root", "root")
    return {}, "root"


def norm_id(cid: str) -> str:
    """把实例 id 归一成可比较的结构角色名。"""
    s = cid
    s = re.sub(r"^__layout__\w+?__(.*)$", r"L.\1", s)   # __layout__root__body -> L.body
    s = re.sub(r"[-_]\d+$", "", s)                       # title-1 -> title
    s = re.sub(r"\d+$", "", s)
    return s


def geometry(node) -> str:
    st = node.get("styles", {}) or {}
    w, h = st.get("width"), st.get("height")
    bits = []
    if isinstance(w, (int, float)) and isinstance(h, (int, float)):
        bits.append(f"{int(w)}x{int(h)}")
    elif isinstance(h, (int, float)):
        bits.append(f"h{int(h)}")
    elif isinstance(w, (int, float)):
        bits.append(f"w{int(w)}")
    pad = st.get("padding")
    if isinstance(pad, (int, float)) and pad:
        bits.append(f"p{int(pad)}")
    elif isinstance(pad, dict):
        bits.append("p*")
    im = node.get("itemMargin", st.get("itemMargin"))
    if isinstance(im, (int, float)) and im:
        bits.append(f"im{int(im)}")
    return ",".join(bits)


def walk(node, comps, depth=0, acc=None):
    """深度优先，产出容器拓扑串 + 形状串 + 叶子清单。"""
    if acc is None:
        acc = {"topo": [], "leaves": [], "shape": []}
    comp = node.get("component", "?")
    if comp in CONTAINERS:
        acc["topo"].append(f"{comp}({norm_id(node['id'])}{'|' + geometry(node) if geometry(node) else ''})")
        acc["shape"].append(f"{comp}[{geometry(node)}]" if geometry(node) else comp)
        for ch in node.get("children", []) or []:
            if ch in comps:
                walk(comps[ch], comps, depth + 1, acc)
    else:
        acc["leaves"].append(f"{comp}:{norm_id(node['id'])}")
    return acc


def analyze(path: Path) -> dict:
    messages = load_messages(path)
    comps, root_id = get_components(messages)
    root = comps.get(root_id) or (list(comps.values())[0] if comps else {})
    r = walk(root, comps)
    text = path.read_text(encoding="utf-8")
    domains = sorted(set(BINDING.findall(text)))
    st = root.get("styles", {}) or {}
    size = f"{st.get('width')}x{st.get('height')}"
    leaf_counter = Counter(x.split(":")[0] for x in r["leaves"])
    return {
        "file": path.name,
        "size": size,
        "topo": " > ".join(r["topo"]),
        "shape": " > ".join(r["shape"]),
        "leaves": dict(leaf_counter),
        "leaf_ids": r["leaves"],
        "domains": domains,
        "n_comp": len(comps),
    }


WRAPPER_IDS = {"L.body", "body_flow", "content_flow", "__genui_render_component__root", "genui_render_component_root"}
HEADER_IDS = {"header", "title_area"}


def region_view(root, comps) -> tuple:
    """归一区划视图：穿透 layout wrapper，返回 (header几何, 区划节点列表)。"""
    def descendants(node):
        out = []
        for cid in node.get("children", []) or []:
            n = comps.get(cid)
            if not n:
                continue
            if norm_id(cid) in WRAPPER_IDS:
                out.extend(descendants(n))
            else:
                out.append(n)
        return out

    header, regions = None, []
    for k in descendants(root):
        nid = norm_id(k["id"])
        if nid in HEADER_IDS:
            header = geometry(k) or "h?"
        else:
            regions.append(k)
    return header, regions


def region_sig(root, comps) -> tuple:
    header, regions = region_view(root, comps)
    return header, tuple(norm_id(r["id"]) for r in regions)


def print_regions():
    files = sorted(CARDS_DIR.glob("*.jsonl"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    print(f"{'文件':<12}{'header':<10}区划")
    for f in files:
        messages = load_messages(f)
        comps, root_id = get_components(messages)
        root = comps.get(root_id) or (list(comps.values())[0] if comps else {})
        header, regions = region_view(root, comps)
        seg = " + ".join(f"{norm_id(r['id'])}[{r.get('component')}]" for r in regions)
        print(f"{f.stem:<12}{str(header):<10}{seg}")


DATA_ROOT = DATA
ARTIFACT_DIR = DATA_ROOT / "生成卡片的中间环节的输入数据"


def _block(text: str, name: str) -> str:
    m = re.search(r"```" + name + r"\n(.*?)\n```", text, re.S)
    return m.group(1) if m else ""


def print_pairs():
    """把 userQuery / cardspec 与 DSL 的区划拓扑配对（路由规则的证据）。"""
    files = sorted(CARDS_DIR.glob("*.jsonl"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    print(f"{'文件':<12}{'查询':<58}{'区划拓扑'}")
    for f in files:
        art = ARTIFACT_DIR / f"{f.stem}_artifact.md"
        query, title = "", ""
        if art.exists():
            t = art.read_text(encoding="utf-8")
            m = re.search(r'"userQuery"\s*:\s*"(.*?)"', _block(t, "taskspec"), re.S)
            query = (m.group(1) if m else "").replace("\n", " ")
            m2 = re.search(r'"title"\s*:\s*"(.*?)"', _block(t, "cardspec"), re.S)
            title = m2.group(1) if m2 else ""
        messages = load_messages(f)
        comps, root_id = get_components(messages)
        root = comps.get(root_id) or (list(comps.values())[0] if comps else {})
        header, regions = region_view(root, comps)
        seg = "+".join(norm_id(r["id"]) for r in regions)
        q = (query[:54] + "..") if len(query) > 56 else query
        print(f"{f.stem:<12}{q:<58}[{title}] {seg}")


def print_tree(path: Path):
    """打印单张卡片的组件树（嵌套缩进），用于人工判读区划结构。"""
    messages = load_messages(path)
    comps, root_id = get_components(messages)
    root = comps.get(root_id) or (list(comps.values())[0] if comps else {})

    def rec(node, depth=0):
        st = node.get("styles", {}) or {}
        g = geometry(node)
        leaf = node.get("component") not in CONTAINERS
        extra = ""
        if leaf:
            c = node.get("content") or node.get("src") or node.get("label") or ""
            extra = f"  «{str(c)[:34]}»"
        print(f"{'  ' * depth}{norm_id(node['id'])} [{node.get('component')}]{(' ' + g) if g else ''}{extra}")
        for ch in node.get("children", []) or []:
            if ch in comps:
                rec(comps[ch], depth + 1)
    rec(root)


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    mode = sys.argv[2] if len(sys.argv) > 2 else ""
    files = sorted(CARDS_DIR.glob("*.jsonl"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    if mode == "regions":
        print_regions()
        return
    if mode == "pairs":
        print_pairs()
        return
    if mode == "tree":
        wanted = sys.argv[3:] or [f.name for f in files[:3]]
        for name in wanted:
            p = CARDS_DIR / name
            print("=" * 90)
            print(f"### {name}")
            print("=" * 90)
            print_tree(p)
            print()
        return
    summary_only = mode == "summary"
    if limit:
        files = files[:limit]
    print(f"卡片目录：{CARDS_DIR}\n共 {len(files)} 个文件\n")
    rows = []
    for f in files:
        try:
            rows.append(analyze(f))
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {f.name}: {type(e).__name__}: {e}")
    print("=" * 100)
    for row in rows:
        if summary_only:
            continue
        print(f"[{row['file']:>9}] {row['size']:>9} | {row['n_comp']:>3} 组件 | 数据根={row['domains']}")
        print(f"            拓扑: {row['topo']}")
        print(f"            叶子: {row['leaves']}")
    print("=" * 100)
    groups = defaultdict(list)
    for row in rows:
        groups[(row["size"], row["topo"])].append(row["file"])
    print(f"\n按「尺寸 + 容器拓扑」分组：共 {len(groups)} 组")
    for (size, topo), fs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f"\n--- {len(fs)} 张 | {size}")
        print(f"    {topo}")
        print(f"    文件: {', '.join(fs)}")

    # 第二层分组：纯形状（容器类型 + 几何，忽略 id 命名）——骨架形状本体
    print("\n" + "=" * 100)
    print("按「骨架形状」分组（容器类型 + 几何；忽略 id 命名，两代命名归一）")
    sig_groups = defaultdict(list)
    for row in rows:
        sig_groups[row["shape"]].append(row["file"])
    print(f"共 {len(sig_groups)} 种形状\n")
    for shape, fs in sorted(sig_groups.items(), key=lambda kv: -len(kv[1])):
        print(f"--- {len(fs)} 张 | {shape}")
        print(f"    文件: {', '.join(fs)}\n")


if __name__ == "__main__":
    main()
