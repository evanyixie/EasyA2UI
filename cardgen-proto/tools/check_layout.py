"""布局体检：把卡片真正排版出来，测量每个文字框是否越界 / 被截断。

与 `diff_gold.py` 的区别：
  - diff_gold 比的是**声明**（字号多重集、对齐多重集、组件构成）→ 抓不到"声明没问题但排出来溢出"；
  - 本工具比的是**渲染结果**（getBoundingClientRect）→ 直接回答"有没有超出卡片、有没有被裁掉"。

用法：
    python tools/check_layout.py                 # 检查最新一次批跑
    python tools/check_layout.py 20261019_163255
    python tools/check_layout.py --gold          # 只检查金标（用于校准，金标应当基本无问题）
    python tools/check_layout.py --all           # 金标 + 本次产物都检查

依赖本机 Edge/Chrome 的无头模式（不引入 playwright）。
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "gold"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from gen_card_compare import card_html            # noqa: E402
from tools.extract_skeletons_from_cards import load_messages  # noqa: E402

RUNS = ROOT / "runs" / "batch"
DSL = DATA / "生成卡片的DSL结果"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

JS = """
const out = [];
document.querySelectorAll('.card').forEach(card => {
  const cr = card.getBoundingClientRect();
  card.querySelectorAll('[data-text="1"]').forEach(el => {
    const r = el.getBoundingClientRect();
    const over = [];
    if (r.bottom > cr.bottom + 0.6) over.push('下 ' + Math.round(r.bottom - cr.bottom));
    if (r.right  > cr.right  + 0.6) over.push('右 ' + Math.round(r.right - cr.right));
    if (r.top    < cr.top    - 0.6) over.push('上 ' + Math.round(cr.top - r.top));
    if (r.left   < cr.left   - 0.6) over.push('左 ' + Math.round(cr.left - r.left));
    if (over.length) out.push({tag: card.dataset.tag, cid: el.dataset.cid,
                               kind: 'overflow', detail: over.join(' / ')});
    const cut = el.scrollWidth - el.clientWidth;
    if (cut > 4)
      out.push({tag: card.dataset.tag, cid: el.dataset.cid, kind: 'clipped-text',
                detail: el.scrollWidth + '>' + el.clientWidth});
    else if (cut > 1)
      out.push({tag: card.dataset.tag, cid: el.dataset.cid, kind: 'edge-clip',
                detail: cut + 'px'});
  });
});
document.getElementById('report').textContent = JSON.stringify(out);
"""


def measure(cards: list) -> list:
    """cards = [(tag, html_body, w, h)]；返回问题列表。"""
    blocks = []
    for tag, body, w, h in cards:
        blocks.append(f'<div class="card" data-tag="{tag}" style="width:{w}px;height:{h}px;'
                      f'position:relative">{body}</div>')
    page = ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>*{box-sizing:border-box}"
            "body{margin:0;padding:20px;background:#fff}"
            ".card{display:inline-block;vertical-align:top;margin:0 20px 20px 0}</style></head><body>"
            + "".join(blocks) + f"<pre id='report'></pre><script>{JS}</script></body></html>")
    tmp = Path(tempfile.mkdtemp()) / "measure.html"
    tmp.write_text(page, encoding="utf-8")
    dom = subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--dump-dom",
                          "--virtual-time-budget=3000", tmp.as_uri()],
                         capture_output=True, text=True, encoding="utf-8", errors="ignore").stdout
    m = re.search(r"<pre id=\"report\">(.*?)</pre>", dom, re.S)
    if not m:
        raise RuntimeError("测量脚本没有产出报告（浏览器执行失败？）")
    return json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&"))


def cards_of_run(run: Path) -> list:
    idx = json.loads((run / "index.json").read_text(encoding="utf-8"))
    out = []
    for e in idx["files"]:
        body, (w, h) = card_html(run / e["file"])
        out.append((e["tag"], body, w, h))
    return out


def cards_of_gold() -> list:
    out = []
    for f in sorted(DSL.glob("q*.jsonl"), key=lambda p: int(re.sub(r"\D", "", p.stem))):
        body, (w, h) = card_html(f)
        out.append((f.stem, body, w, h))
    return out


def report(name: str, issues: list) -> None:
    over = [i for i in issues if i["kind"] == "overflow"]
    clip = [i for i in issues if i["kind"] == "clipped-text"]
    edge = [i for i in issues if i["kind"] == "edge-clip"]
    print(f"\n== {name} ==")
    print(f"超出卡片边界：{len(over)} 处 ｜ 明显裁切(>4px)：{len(clip)} 处 ｜ 边缘裁切(2~4px)：{len(edge)} 处")
    by_tag = {}
    for i in issues:
        by_tag.setdefault(i["tag"], []).append(i)
    for tag, items in sorted(by_tag.items()):
        kinds = ", ".join(f"{i['cid']}({i['kind']}:{i['detail']})" for i in items[:4])
        print(f"  - {tag}: {len(items)} 处 → {kinds}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_gold = "--gold" in sys.argv or "--all" in sys.argv
    do_run = "--gold" not in sys.argv

    if do_gold:
        g = measure(cards_of_gold())
        report("金标（校准用：这里若大量报错说明检查器口径有问题）", g)

    if do_run:
        run = RUNS / args[0] if args else sorted(RUNS.iterdir())[-1]
        issues = measure(cards_of_run(run))
        report(f"本次产物 {run.name}", issues)
        sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
