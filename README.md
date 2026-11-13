# EasyA2UI

封闭域 AI 卡片生成：一句中文需求 → 一张可直接渲染的鸿蒙 A2UI Form 卡片（三行 JSONL）。
模型只做语义抽取（唯一一次调用），结构与几何交给确定性程序。

## 三份正本（其余文档都是这三份的衍生，迭代期一律不另建）

| 内容 | 文件 |
|---|---|
| 系统怎么设计：M1 + P1~P7、规则库、目录与命名 | `cardgen-proto/docs/AI卡片生成架构方案-v3.md` |
| 实验怎么设计：四档阶梯、指标、口径、工程结构 | `paper/方案/论文实验方案.md` |
| 界面规范：字号间距档位、few-shot 样张 | `cardgen-proto/ux-spec/UX-SPEC.md` |

## 跑起来

```bash
cd cardgen-proto
python tools/debug_pipeline.py "我想随时看看手机和耳机盒还剩多少电"   # 单次生成 + 逐环节 trace
python tests/run_cases.py                                          # 9 条回归用例
python tests/test_architecture.py                                  # 产品区 / 实验区边界检查
python tools/batch_generate.py                                     # 批量跑 49 条真实 query
```

零第三方依赖（Python 3.10+）。不配模型也能跑，自动降级 MockLLM；接真实模型时填 `config/llm.json`（写法见设计正本 §13.2）。

## 约定

- **只留正本，不留副本**：同一件事只写在一个地方；目录说明、使用手册这类文档等发布前再补。
- **产物不入库**：`runs/`、`logs/`、`paper/out/`、`config/llm.json`。
- **金标只有一份**：`cardgen-proto/data/gold/`，论文只记 `commit + MANIFEST.sha256` 两个指针。
