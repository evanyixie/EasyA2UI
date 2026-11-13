"""逐环节调试：显示 M1 → P1 → ... → P7 每一步的完整输入/输出，并落盘。

这是原型唯一的命令行入口（没有常驻服务）：打印逐环节 trace，
并把完整结果与**裸 A2UI 三行**写进 runs/debug/，方便直接粘进渲染器。

用法（在 cardgen-proto/ 目录）：
    python tools/debug_pipeline.py                   # 用默认 query
    python tools/debug_pipeline.py "你的测试 query"   # 指定 query
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from src.pipeline import generate
from src.M1_extract import build_llm, config_ready, load_llm_config

DEFAULT_QUERY = "帮我做一个双11会员促销卡片，要有折扣信息和购买按钮"


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUERY
    llm = build_llm()
    mode = "真实模型（config/llm.json）" if config_ready(load_llm_config()) else "MockLLM（配置缺失或值为空，已降级）"
    print("query:", query)
    print("模型来源:", mode)
    result = generate(query, llm, debug=True)

    for t in result["trace"]:
        print("=" * 70)
        print(f"{t['step']}  [{'模型' if t['kind'] == '模型' else '程序'}]")
        print("-- 输入 --")
        print(json.dumps(t["input"], ensure_ascii=False, indent=2))
        print("-- 输出 --")
        print(json.dumps(t["output"], ensure_ascii=False, indent=2))

    print("=" * 70)
    print("兜底日志:", json.dumps(result["meta"]["fallback_log"], ensure_ascii=False) or "（无，零 fallback）")

    log_dir = ROOT / "runs" / "debug"
    log_dir.mkdir(parents=True, exist_ok=True)
    out = log_dir / "debug_output.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完整结果已写入: {out}")
    # full-a2ui 是字符串字段，嵌在 JSON 里会带 \" 转义；另存裸 JSONL 方便直接复制到渲染器
    raw = log_dir / "debug_full_a2ui.jsonl"
    raw.write_text(result["full-a2ui"] + "\n", encoding="utf-8")
    print(f"原生 A2UI 三行（可直接复制渲染）已写入: {raw}")


if __name__ == "__main__":
    main()
