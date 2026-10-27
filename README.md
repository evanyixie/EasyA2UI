# EasyA2UI

封闭域 AI 卡片生成：一句中文需求 → 一张可直接渲染的鸿蒙 A2UI Form 卡片（三行 JSONL）。

**核心主张**：模型只做语义抽取（领域 / 对象分组 / 字段取舍），几何与结构全部交给确定性程序。
因为排版依赖一个模型拿不到的量——**这段字在 150vp 的格子里放得下多少**，只有真正排一遍才知道。

## 结构

```
nextgenui/
├── cardgen-proto/    原型：流水线 / 注册表 / 提示词 / 测试 / 设计文档 / 金标数据
└── paper/            论文：实验设计 / 实验结果 / 参考资料
```

两者平行，不互相嵌套：论文依赖原型的某次 commit，但原型不依赖论文，且论文在双盲期需要匿名。

## 跑起来

零第三方依赖，Python 3.10+。

```bash
cd cardgen-proto
python tools/debug_pipeline.py "我想随时看看手机和耳机盒还剩多少电"   # 单次生成 + 逐环节 trace
python tests/run_cases.py                                          # 9 条回归用例
```

没有常驻服务——流水线入口是 `src.pipeline.generate()`，命令行用 `tools/debug_pipeline.py`。

## 现状

- **原型**：49 对人工校验金标数据；九套测试；协议违规 0、越界 0；单次生成只有 **1 个模型调用**
- **论文**：实验设计完成（对照四档 + 补救三组），六处统计口径已冻结，待跑批

## 读哪里

| 想知道 | 看这里 |
|---|---|
| 系统怎么设计、每步为什么这么分 | `cardgen-proto/docs/AI卡片生成架构方案-v3.md` |
| 怎么跑、目录规矩、各文件是什么 | `cardgen-proto/README.md` |
| 界面规范与 few-shot | `cardgen-proto/ux-spec/UX-SPEC.md` |
| 实验怎么设计、指标怎么算、还有什么没做 | `paper/方案/论文实验方案.md` |
| 论文与代码的边界 | `paper/README.md` |

## 三条纪律

1. **同一样东西只存在一处。** 副本必然分叉（曾经分叉过 6 个版本）。
2. **跑一次能重建的都不入库。** 产物进 `runs/`、日志进 `logs/`、本地密钥进 `config/llm.json`，三者都被忽略。
3. **金标数据只有一份**，在 `cardgen-proto/data/gold/`；论文侧只记 `commit + MANIFEST.sha256` 两个指针，不复制。
