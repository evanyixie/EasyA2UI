# -*- coding: utf-8 -*-
"""批量生成测试：读本地测试输入清单，循环调用真实模型，
产出可依次渲染的 A2UI 产物文件与效果报告。

测试输入清单 `data/queries.json` 是本工具的唯一输入源，
不依赖任何外部项目。清单由 `tools/gold_dataset.py` 从真实人工校验数据
（CreateMyCard 的 q1~q52 输入输出对）生成，**不要再手工塞模型自编的 query**：
    [{"tag": "q01", "query": "帮我做个卡片，看杭州市西湖区现在是什么天气…",
      "source": "artifact:CreateMyCard", "size": "2x2"}]
（`size` 是金标尺寸，有则按它生成；缺失时回落 tag 前缀 `fs2x2-`/`fs2x4-`，再否则 auto）

用法（在 cardgen-proto/ 目录）：
    python tools/batch_generate.py                    # 全量批跑
    python tools/batch_generate.py --limit 10         # 只跑前 10 条
    python tools/batch_generate.py --tag-substr 2x4   # 只跑 tag 含 2x4 的

产物（runs/batch/）：
    queries.json         查询清单（tag + query + 来源），手工维护，批跑只读它
    batch_outputs.md     每条 query 的原生 A2UI 三行（代码块，可依次复制渲染）
    batch_report.json    汇总报告（骨架/尺寸/主题/fallback/耗时/错误）
    runs/<时间戳>/       本次执行的 DSL 目录：每个 query 一个 .jsonl 文件
                         （裸三行可直接复制渲染）+ index.json 清单；
                         失败的 query 落 .error.txt
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # cardgen-proto/
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from src.M1_extract import build_llm, config_ready, load_llm_config   # noqa: E402
from src.pipeline import generate                              # noqa: E402

BATCH_DIR = ROOT / "data"                  # 输入清单（入库）
RUNS_DIR = ROOT / "runs" / "batch"             # 产物（不入库）
QUERIES_FILE = BATCH_DIR / "queries.json"


def load_queries() -> list:
    """读本地测试输入清单。

    清单是本工具的唯一输入源——不再从 CreateMyCard 抽取，因此不依赖外部项目。
    增删测试输入直接编辑 data/queries.json。
    """
    if not QUERIES_FILE.exists():
        print(f"测试输入清单不存在：{QUERIES_FILE}\n"
              f"本工具已不再从外部项目抽取清单。请从版本库恢复该文件，或手工创建：\n"
              f"  [{{\"tag\": \"my-01\", \"query\": \"生成一张天气卡片\", \"source\": \"manual\"}}]",
              file=sys.stderr)
        sys.exit(1)
    return json.loads(QUERIES_FILE.read_text(encoding="utf-8"))


def _safe_name(tag: str) -> str:
    """tag 转文件名安全字符串（sys tag 含 / 等字符）。"""
    return re.sub(r'[\\/:*?"<>|]', "_", tag)


def run_batch(limit: int, tag_substr: str, delay: float) -> None:
    queries = load_queries()
    if tag_substr:
        queries = [q for q in queries if tag_substr in q["tag"]]
    if limit:
        queries = queries[:limit]

    run_dir = RUNS_DIR / time.strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    llm = build_llm()
    mode = "真实模型" if config_ready(load_llm_config()) else "MockLLM（降级）"
    print(f"模型来源: {mode} | 待跑 {len(queries)} 条 | 产物目录: {run_dir}\n")

    report, md_parts, ok = [], [], 0
    md_parts.append("# 批量 A2UI 生成产物\n\n"
                    "> 每个小节是一个独立卡片的完整三行 JSONL（createSurface + "
                    "updateComponents + updateDataModel），整块复制到渲染器即可。\n"
                    f"> 本次运行目录: `{run_dir.name}`\n")
    started = time.time()
    index = []
    for i, item in enumerate(queries, 1):
        tag, query = item["tag"], item["query"]
        t0 = time.time()
        entry = {"tag": tag, "query": query, "source": item["source"]}
        try:
            # 金标尺寸：优先读清单里的 size 字段（真实数据集自带），否则回落 tag 前缀（旧约定）
            gold_size = (item.get("size") or
                         ("2x2" if tag.startswith("fs2x2")
                          else "2x4" if tag.startswith("fs2x4") else None))
            r = generate(query, llm, size=gold_size)
            ir = r["ir"]
            lines = r["full-a2ui"].splitlines()
            entry.update({
                "status": "ok",
                "size": ir["size"], "skeleton": ir["skeleton_id"],
                "domain": ir["domain"], "theme": ir["theme"],
                "entries": len(ir["entries"]),
                "fallback_log": r["meta"]["fallback_log"],
                "m1_raw_head": r["trace"][0]["output"]["raw"][:300] if r.get("trace") else "",
                "duration_s": round(time.time() - t0, 1),
            })
            # 每个 query 的 DSL 单独落盘（裸三行，可直接复制渲染）
            dsl_name = f"{i:02d}_{_safe_name(tag)}.jsonl"
            (run_dir / dsl_name).write_text(r["full-a2ui"] + "\n", encoding="utf-8")
            entry["dsl_file"] = f"runs/{run_dir.name}/{dsl_name}"
            index.append({"file": dsl_name, "tag": tag, "query": query,
                          "skeleton": ir["skeleton_id"], "size": ir["size"],
                          "theme": ir["theme"],
                          "fallback_log": r["meta"]["fallback_log"]})
            md_parts.append(
                f"\n---\n\n## {i:02d}. {tag} ｜ {ir['skeleton_id']} ｜ {ir['size']} ｜ {ir['theme']}\n"
                f"**query**: {query} ｜ **文件**: `{dsl_name}`\n\n"
                f"```jsonl\n" + "\n".join(lines) + "\n```\n")
            ok += 1
            flag = "⚠️" if r["meta"]["fallback_log"] else "✅"
            print(f"[{i:02d}/{len(queries)}] {flag} {tag} {ir['skeleton_id']} "
                  f"{time.time()-t0:.1f}s fallback={r['meta']['fallback_log'] or '无'}")
        except Exception as e:
            err_name = f"{i:02d}_{_safe_name(tag)}.error.txt"
            (run_dir / err_name).write_text(f"query: {query}\n"
                                            f"{type(e).__name__}: {e}\n", encoding="utf-8")
            entry.update({"status": "error", "error": f"{type(e).__name__}: {str(e)[:200]}",
                          "error_file": f"runs/{run_dir.name}/{err_name}",
                          "duration_s": round(time.time() - t0, 1)})
            md_parts.append(f"\n---\n\n## {i:02d}. {tag} ｜ ❌ 生成失败\n"
                            f"**query**: {query}\n\n错误: {entry['error']}\n")
            print(f"[{i:02d}/{len(queries)}] ❌ {tag} {entry['error']}")
        report.append(entry)
        if delay:
            time.sleep(delay)

    (run_dir / "index.json").write_text(
        json.dumps({"mode": mode, "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total": len(report), "files": index}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    report_json = json.dumps({"mode": mode, "total": len(report), "ok": ok,
                              "error": len(report) - ok,
                              "total_minutes": round((time.time() - started) / 60, 1),
                              "run_dir": str(run_dir),
                              "results": report}, ensure_ascii=False, indent=2)
    outputs_md = "\n".join(md_parts)
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    # 汇总同时写进本次运行目录（留档）与 batch 根目录（始终为最新一次）
    (run_dir / "batch_report.json").write_text(report_json, encoding="utf-8")
    (run_dir / "batch_outputs.md").write_text(outputs_md, encoding="utf-8")
    (RUNS_DIR / "batch_report.json").write_text(report_json, encoding="utf-8")
    (RUNS_DIR / "batch_outputs.md").write_text(outputs_md, encoding="utf-8")
    n_fb = sum(1 for e in report if e.get("fallback_log"))
    print(f"\n完成：{ok}/{len(report)} 成功（其中 {n_fb} 条带 fallback）｜"
          f"本次 DSL 目录 {run_dir}｜"
          f"报告 {RUNS_DIR / 'batch_report.json'}｜产物 {RUNS_DIR / 'batch_outputs.md'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--tag-substr", default="")
    ap.add_argument("--delay", type=float, default=0.5)
    args = ap.parse_args()

    run_batch(args.limit, args.tag_substr, args.delay)


if __name__ == "__main__":
    main()
