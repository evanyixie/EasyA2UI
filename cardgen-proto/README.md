# cardgen-proto — 封闭域 AI 卡片生成原型

> 验证目标：**在线链路仅 1 个模型调用（M1）时，封闭域路线是否稳定可靠。**
> 架构文档：`docs/AI卡片生成架构方案-v3.md`（本仓库按其实现，与代码保持一致；本项目只维护这一份）。
> UX 规范：`ux-spec/UX-SPEC.md`（规范正文 + 实现对齐清单 + 增量区，唯一维护处）。
> 核心：模型只做语义决策（领域/对象分组/字段取舍 + 枚举短摘抄），程序负责一切确定性工作（骨架路由/region 装配/角色规格/宽度预算/协议发射）。

## 快速开始

```bash
python tools/debug_pipeline.py "我想随时看看手机和耳机盒还剩多少电"   # 单次生成：逐环节 trace
python tests/run_cases.py         # 批量用例 + 指标报告（含协议合规断言）
python tools/diff_gold.py         # 与金标做元素级比对（按差异卡数聚类）
python tools/gen_card_compare.py  # 金标 vs 本次产物并排渲染成 runs/viz/card_compare.html
python tests/test_capacity.py     # 容量适配专项 16 项断言
python tests/test_gold_queries.py # 真实数据集冒烟（49 条真实 query，零异常零协议违规）
python tests/test_paths.py        # 资源路径守卫（前缀只允许在 src/paths.py 出现）
python tests/test_forms.py        # 排法表守卫（表与 src/forms.py 必须一一对应）
python tests/test_routing_stability.py  # 路由稳定性（显示字段不得改变骨架）
python tools/snapshot_pipeline.py save /tmp/s.json   # 输出快照（重构后 diff 必须为 0）
python tools/check_layout.py      # 布局体检：真实排版后测越界/裁切（--gold 校准）
```

> 原型没有常驻服务：流水线唯一入口是 `src.pipeline.generate()`，命令行验证走 `tools/debug_pipeline.py`。将来要包 HTTP 或前端时再加，不提前背维护成本。

真实数据集与基准（输入输出对来自 CreateMyCard 的人工校验数据）：

```bash
python tools/gold_dataset.py        # 构建 fixtures/batch_queries.json + fixtures/gold_pairs.json
python tools/gold_dataset.py check  # 金标结构核验（49 张卡 ↔ 本项目骨架，有漂移则非零退出）
python tools/batch_generate.py      # 用真实模型跑真实 query 批量生成（产物 runs/batch/）
python tools/extract_skeletons_from_cards.py 0 pairs|regions|tree|summary   # 卡片 DSL 区划聚类探索
```

逐环节调试（本目录下执行）：

```bash
python tools/debug_pipeline.py "query"  # trace 落盘 runs/debug/debug_output.json
                                  # 裸三行 JSONL 落盘 runs/debug/debug_full_a2ui.jsonl（可直接复制渲染）
```

## 目录结构

```
cardgen-proto/
├── src/          流水线七段 + 度量 + 校验（产品代码，零第三方依赖）
├── registry/     注册表：枚举 / 骨架 / 主题 / 角色 / 素材 / 排法 / 降档梯级
├── prompts/      M1 提示词
├── resources/    媒体素材（127 svg + 27 png，白名单 72 个可被选中）
├── tests/        九套测试（语义 / 容量 / 金标 / 路径 / 排法 / 路由 / 选项 / 校验 / 度量）
├── tools/        开发工具（批量生成 / 调试 / 比对 / 快照 / 可视化 / 度量 / 出表）
├── fixtures/     固定输入与基准：cases / gold_pairs / content_oracle / batch 清单
├── data/         金标原始数据（49 对，98 文件）+ MANIFEST.sha256
├── docs/         本项目文档（设计正本）
├── refs/         外部依据：A2UI 协议 / Basic Catalog / 鸿蒙 Form 规范
├── ux-spec/      界面规范 + 规范附带的 few-shot 样例
├── config/       本地配置（含密钥，不入库）
├── runs/         一切产物：batch / stability / viz / debug / acceptance
└── logs/         只放日志：generate.jsonl / llm_calls.jsonl
```

四条规矩：

1. **目录名必须说明内容。** 固定输入进 `fixtures/`，产物进 `runs/`，日志进 `logs/`——互不越界。
2. **`logs/` 只放日志。** 调试产物（完整结果、裸 JSONL）属于产物，进 `runs/debug/`。
3. **路径前缀只允许出现在 `src/paths.py`。** 其他文件出现 `resources/base/media` 即违规，由 `tests/test_paths.py` 守。
4. **跑一次能重建的东西不入库**（批量卡、图表、对比页、稳定性报告）。

## 流程

```
query → M1 结构规划【模型】→ P1 归一化 → P2 骨架路由 → P3 region 装配
      → P4 角色规格 → P5 拼装IR(宽度预算审计) → P6 主题装配 → P7 发射器(原生 A2UI 三行 JSONL)
```

- 输出：`{ ir, a2ui(调试视图), full-a2ui(原生三行 JSONL), meta }`；`debug=true` 多 `trace`。
- 渲染目标：鸿蒙 Form（`ohos.a2ui.extended.catalog.form`），组件白名单十种，Toggle 排除（开关落 Checkbox），Button 用 label+onClick。
- 封闭域资产：`registry/`（enums/skeletons 16 骨架 S1~S6/W1~W10/themes 主题目录/ladders 档位/components 角色/assets 素材白名单）+ `resources/base/media/` 素材库（**路径前缀只在 `src/paths.py` 定义**，registry 只登记文件名）。主题只在 P6 主题装配处理（选主题+着色），其余环节零主题知识。
- 验收产物：`runs/acceptance/acceptance_outputs.json`（对照 CreateMyCard few-shot V02/V04/V05 的三场景输出；生成它的 `verify_a2ui_render.py` 已移除，此文件成为孤儿证据）。

## 接真实模型

填 `config/llm.json`（OpenAI 兼容的 Chat Completions 端点均可）：

```json
{
  "base_url": "https://ark.cn-beijing.volces.com/api/v3",
  "api_key": "你的密钥",
  "model": "模型名",
  "temperature": 0.0,
  "timeout": 120,
  "connect_timeout": 10,
  "json_mode": true,
  "max_retries": 1
}
```

- **自动降级**：文件不存在、内容非法，或 `base_url`/`api_key`/`model` 任一为空 → 自动使用内置 MockLLM。
- `timeout` 是**读取超时**（强推理/带思考的模型建议 60~120）；`connect_timeout` 是连接超时（避免连不上还白等）。
- `json_mode=true` 带 `response_format: {"type":"json_object"}`；**调用失败重试时会自动关闭它**（不少端点卡在这个字段上）。
- `extra_payload`：**厂商私有参数透传**，会合并进请求体。典型用途是关闭思考模式——强推理模型的思维链动辄上万 token，会把生成时间拖到分钟级。实测（火山方舟 Coding 套餐）：
  - `deepseek-v4-flash`：`"extra_payload": {"thinking": {"type": "disabled"}}`（生效，reasoning_tokens=0，单次生成 4s 级）
  - `glm-5.3`：`thinking.type=disabled` 不支持（400）；只有 `"chat_template_kwargs": {"enable_thinking": false}` 部分有效（262s → 68s），建议换 deepseek
- 调试脚本会打印当前模型来源（`真实模型（config/llm.json）` / `MockLLM（配置缺失或值为空，已降级）`）。
- 密钥不要提交到仓库（已加入 `.gitignore`）。

### 日志（排障用）

- `logs/llm_calls.jsonl`：每一次模型调用（含重试）一行——耗时、错误类型、是否带 json_mode、prompt/响应长度；
- `logs/generate.jsonl`：每一次生成请求一行——query、模型、M1 是否失败、骨架/尺寸/主题、fallback_log、总耗时。

失败语义已区分：`M1 call fail` = 调用层失败（连接/超时/HTTP）；`M1 parse fail` = 输出解析失败。两种都走空计划兜底，任何情况仍产出合法卡片。

当前默认跑的是 MockLLM（规则模拟理想模型，五场景），零依赖、无需 API Key。
