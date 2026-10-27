# fixtures/ — 固定输入与基准

测试与工具共用的**输入**和**判定基准**。都是入库文件，不要手工改（改就失去可比性）。

| 文件 | 是什么 | 谁生成 | 谁消费 |
|---|---|---|---|
| `cases.json` | 9 条回归用例（含 `expect_skeleton` 断言） | 手写 | `tests/run_cases.py`、`tools/snapshot_pipeline.py` |
| `batch_queries.json` | 49 条真实 userQuery（来自人工校验数据） | `tools/gold_dataset.py` | `test_gold_queries`、`test_routing_stability`、`batch_generate`、`run_condition`、`resample_stability` |
| `batch_queries.legacy_model_invented.json` | 早期 49 条模型自编 query（**已废**，仅存档对照） | 历史 | 无（不要再用） |
| `gold_pairs.json` | 49 对金标数据集：输入 + 金标结构 + 数据模型叶子（169 叶） | `tools/gold_dataset.py` | `test_gold_queries`、`gold_dataset compare` |
| `content_oracle.json` | 每卡"应有事实集"（49 卡 128 条），内容覆盖的判定基准 | `tools/build_content_oracle.py` | `tools/measure_content.py` |

两条口径：

1. **基准必须独立于被测系统。** `content_oracle.json` 从**金标终产物**抽，不从流水线的 plan 抽——L1 没有 plan，用了就不可比。
2. **派生品丢了就重建**（`gold_dataset build` / `build_content_oracle`），所以它们入库是为了省时间，不是因为不可重建；`batch_queries.json` 例外——工具已不再从参考项目抽取，丢了无法重建，**必须入库**。
