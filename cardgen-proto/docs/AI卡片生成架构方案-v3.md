# AI 卡片生成架构方案 v3

> 本文档是封闭域 AI 卡片生成系统的**定稿方案**，也是原型/生产代码实现的唯一依据。
> v3 基于 v2 修订：**对标生产级项目 CreateMyCard 完成"协议对齐 + 资产移植"两阶段整改**——骨架升级为带精确几何的固定布局模板（S1~S4/W1~W10；v3.7 起为 S1~S6/W1~W10）、组件升级为带视觉规格与色彩角色的角色体系、新增主题目录与设计档位、程序直接组装**原生 A2UI v0.9 三行 JSONL**、M1 契约扩展（domain/size/theme/objects/keep）。v3.1 将主题处理独立为 P6 主题装配（整条流水线唯一主题环节），原发射器顺延为 P7（零色板知识）。全文以当前 cardgen-proto 代码实际实现为准。
> 核心理念自 v2 起不变：**确定的东西全部封装，规则化的东西全部交给程序，模型只负责无法规则化的语义理解——且输出压缩到枚举值 + 短摘抄，不输出任何实现层概念。**

---

## 1. 背景与问题

业务通过 AI 生成卡片，让模型直接生成最终产物时效果不稳定：样式幻觉、结构不可控、输出不可测试。本业务的真正优势在于**封闭域**：卡片的显示样式和布局是有限的、可枚举的。

v3 起增加第二重对标：生产级项目 CreateMyCard（小艺 App AI 卡片）验证了"固定布局骨架 + 受控组件规格 + 主题色板 + 校验兜底"的工程可行性。本方案吸收其全部规范资产（UX 规范、Form 协议方言、设计档位、色板），但保留并强化自己的结构性优势——**CreateMyCard 靠 prompt 硬规则约束模型输出布局，本方案把同样的知识全部下沉为程序规则表，模型输出空间进一步压缩**。

三个关键收益（继承 v2）：

- **消除样式幻觉**：模型永远不输出几何/样式/组件编号，只输出"决策结果"（枚举 + 短摘抄 + 对象分组），幻觉面趋近于零。
- **可测试、可回放**：每步输出都是结构化小数据，可断言、可回归。
- **UI 质量天花板由程序保证**：模型选错会被程序兜住（路由决策表/角色规则表/宽度预算/兜底骨架），不会"生成坏卡片"。

## 2. 架构原则

| # | 原则 | 含义 |
|---|---|---|
| 1 | **模型输出空间最小化** | 模型只输出枚举值 + 短摘抄（content_hint ≤30 字、label_hint ≤10 字）+ 业务对象分组 + 领域枚举；不碰组件编号、骨架编号、几何、样式、绑定路径 |
| 2 | **程序负责确定性，模型负责不确定性** | 能枚举、有唯一正确答案的 → 程序；语义判断（领域、对象分组、字段取舍、信息项拆解）→ 模型 |
| 3 | **业务对象先于字段数量** | 同一业务对象的名称/数值/状态只算一个对象（objects 分组），是骨架路由的第一判据；字段数、组件数不增加对象数 |
| 4 | **骨架即发射模板** | 16 个固定骨架（2×2 S1~S6 / 2×4 W1~W10；S5/S6 由真实卡片数据反哺）带精确几何（region 尺寸/padding/间距），P6 按树模板直接发射原生组件，无中间转换器 |
| 5 | **规范资产全部代码化** | UX 规范的字号/间距/圆角档位、三套色板、白背板、压力宽度预算口径全部落 registry JSON，越档即审计错误 |
| 6 | **IR 单点事实源** | 数据只朝一个方向流动：IR → A2UI。意图（M1 原始 domain/intent）贯穿写入 IR 做残差连接 |
| 7 | **协议合规是发射器的责任** | Form catalog 组件白名单（十组件，Toggle 排除）、事件协议（onClick 单 handler）、三行消息结构由 P6 统一保证，模型与中间环节无感知 |

## 3. 在线流程

### 3.1 流程图

```
query
  │
  ▼
┌────────────────────────────────────────────────────────────┐
│ M1 结构规划【模型】                                          │
│   职责：理解 query，输出纯语义结构计划                         │
│   输出：domain + size + theme? + objects + 信息项/动作项      │
│         （含 keep 取舍标记）+ relations + groups              │
└──────────────────────┬─────────────────────────────────────┘
                       ▼
┌────────────────────────────────────────────────────────────┐
│ P1 归一化【程序】                                            │
│   枚举对齐（domain/theme/size/keep）/ 同义词 / ref 重排 /     │
│   入关截断(30/10) / objects 校验 / 悬空边清洗 / fallback_log  │
└──────────────────────┬─────────────────────────────────────┘
                       ▼
┌────────────────────────────────────────────────────────────┐
│ P2 骨架路由【程序】                                          │
│   特征派生 → 尺寸决策（最小尺寸原则）→ 路由决策表              │
│   （对象数第一判据）→ 主题选择 → 兜底骨架                      │
└──────────────────────┬─────────────────────────────────────┘
                       ▼
┌────────────────────────────────────────────────────────────┐
│ P3 region 装配【程序】                                       │
│   对象 → zone 背板；字段 → 信息行；动作 → 所属 region；        │
│   密度上限校验；覆盖率校验                                     │
└──────────────────────┬─────────────────────────────────────┘
                       ▼
┌────────────────────────────────────────────────────────────┐
│ P4 角色规格选择【程序】                                       │
│   语义类型 + 特征 → 角色（header_title/hero_value/status_lead │
│   /meta_note/capsule_action…）→ 视觉规格 + color_role         │
└──────────────────────┬─────────────────────────────────────┘
                       ▼
┌────────────────────────────────────────────────────────────┐
│ P5 拼装 IR【程序】                                           │
│   文案填充 / 语义实例 ID / 绑定路径 / 意图贯穿校验 /           │
│   压力宽度预算审计（hero 降档序列 + 语义截断）                  │
└──────────────────────┬─────────────────────────────────────┘
                       ▼
┌────────────────────────────────────────────────────────────┐
│ P6 主题装配【程序】                                          │
│   整条流水线唯一处理主题的环节：按主题目录选主题                │
│   （M1偏好 > domain映射 > 默认）/ 解析色板写 ir.palette /      │
│   涂装骨架树与条目（背景/文字色/动作色）/（挂载点）对比度校验    │
└──────────────────────┬─────────────────────────────────────┘
                       ▼
┌────────────────────────────────────────────────────────────┐
│ P7 发射器【程序】                                            │
│   骨架 tree 前序展平（root 第一位、父先子后）/ 零色板知识，     │
│   只读已着色 IR / zone 两行规则 / 协议合规保证                 │
│   → 原生 A2UI 三行 JSONL                                     │
└──────────────────────┬─────────────────────────────────────┘
                       ▼
        输出 { ir, a2ui(调试视图), full-a2ui(三行 JSONL), meta }
```

### 3.2 各环节职责一览

| 节点 | 归属 | 一句话职责 |
|---|---|---|
| M1 | 模型 | 想清楚这张卡是什么领域、有几个业务对象、要说什么、哪些字段可删 |
| P1 | 程序 | 把模型的"方言"翻译成程序世界的"官方语言"（枚举/ref/截断/清洗） |
| P2 | 程序 | 尺寸决策 + 从 16 个固定骨架中路由出唯一骨架 + 选主题色板 |
| P3 | 程序 | 把对象/字段/动作装进骨架的 region 槽位（管"放哪、放几个"） |
| P4 | 程序 | 为每个条目选角色与视觉规格（管"长什么样、什么颜色角色"） |
| P5 | 程序 | 拼完整 IR + 压力宽度预算审计（管"装不装得下"） |
| P6 | 程序 | 主题装配：选主题 + 涂颜色/背景（整条流水线唯一主题环节） |
| P7 | 程序 | 骨架树模板 + 着色后 IR → 原生 A2UI 三行 JSONL（管"协议合规"） |

### 3.3 输出契约

服务对每个 query 返回四段（`debug=true` 时多一个 `trace`）：

```json
{
  "ir":        { "surface_id", "size", "domain", "intent", "theme",
                 "entries": [{ref, kind, type, copy, instance_id, role, spec,
                              binding, keep, slot}],
                 "objects", "fills", "relations", "groups", "skeleton_id",
                 "fallback_log" },
  "a2ui":      { "调试视图：instance_id + role + copy + binding 汇总" },
  "full-a2ui": "原生 A2UI v0.9 协议三行 JSONL（createSurface + updateComponents
                + updateDataModel），组件数组前序发射（root 第一位、父先子后）",
  "meta":      { "query", "fallback_log" },
  "trace":     [ {"step": "M1", "kind": "模型", "input": ..., "output": ...}, ... ]
}
```

调试入口：`python tools/debug_pipeline.py "query"`（在 `cardgen-proto/` 下执行，逐环节 trace 落盘 `logs/debug_output.json`，另落盘**裸三行** `logs/debug_full_a2ui.jsonl` 可直接复制渲染）；HTTP `POST /generate {"query": "...", "debug": true}`。

## 4. M1 结构规划：模型契约

### 4.1 输出 JSON 结构（示例：双业务电量卡）

```json
{
  "domain": "battery",
  "size": "auto",
  "theme": null,
  "info_items": [
    {"ref": 1, "type": "stat",    "content_hint": "68%",   "keep": "must"},
    {"ref": 2, "type": "subtitle","content_hint": "未充电", "keep": "should"},
    {"ref": 3, "type": "stat",    "content_hint": "47%",   "keep": "must"},
    {"ref": 4, "type": "subtitle","content_hint": "充电中", "keep": "should"}
  ],
  "actions": [],
  "objects": [
    {"name_hint": "手机",   "fields": [1, 2]},
    {"name_hint": "耳机盒", "fields": [3, 4]}
  ],
  "relations": [],
  "groups": []
}
```

### 4.2 字段规范

| 字段 | 类型 | 约束 |
|---|---|---|
| `domain` | 枚举 | 业务领域（weather/battery/earphone/calendar/exercise/sleep/countdown/notice/promotion/unknown 等 15 值），决定主题色板与素材语义 |
| `size` | 枚举 | `2x2 \| 2x4 \| auto`；用户显式指定尺寸时填写，否则 auto（程序按最小尺寸原则决策） |
| `theme` | 枚举/空 | 可选覆盖（blue/purple/warm），仅用户明确指定配色时输出 |
| `info_items[].keep` | 枚举 | `must`（回答核心问题/用户明确要求）\| `should`（可删支撑信息）——字段取舍标记 |
| `objects[]` | 数组 | `{name_hint ≤12字, fields: [info_item 的 ref]}`；业务对象分组，同对象多字段归一组；两个独立对象必须分别声明 |
| `content_hint` | 字符串 | 原文摘取 ≤30 字；`label_hint` ≤10 字（入关防呆口径，真实容量归 P5 宽度预算） |
| `relations/groups` | — | 沿用 v2 七种关系边/五种组；**groups 自 v3 起降级为语义参考**，region 装配以 objects/fills 为准 |

**两条铁律**（继承 v2）：`ref` 用序号不做命名；禁止出现任何实现层概念（组件/骨架编号、几何、样式）。

### 4.3 M1 兜底策略

模型输出不是合法 JSON 时，程序不重试，直接采用空计划（domain=unknown、空对象列表等）走完全流程，`M1 parse fail: <原因>` 记入 `fallback_log`。任何输入都产出合法的四段输出。

## 5. 关系词表与组类型

继承 v2：七种带类型的关系边（binds/part_of/peer/order_before/primary_of/secondary/exclusive_with）与五种语义组（section/list/unit/action_bar/aside）定义不变，词表宁小勿大，按 fallback_log 收敛。

**v3 变化**：region 装配的执行依据从 groups 迁移到 **objects（业务对象）**；groups 保留用于语义参考与未来演进。关系边中 `binds`（动作属于哪个对象）用于 P3 把动作绑定到对象所在背板。

## 6. 封闭域资产（registry/，v3 六件套）

程序环节依赖的全部确定性资产，以 JSON 配置 + 媒体资源形式存放：

| 文件 | 内容 | 来源 |
|---|---|---|
| `enums.json` | 全部枚举（intent/domain/size/theme/info_type/action_type/relation_type/group_type/keep）+ 同义词表 | v2 扩展 |
| `skeletons.json` | **16 个固定骨架**：select 路由键（objects/actions 区间 + features）+ tree 发射模板（region 几何、slot 槽位、styles）| CreateMyCard UX-SPEC |
| `themes.json` | **主题目录**：多主题条目（蓝/紫/暖浅色 + 中性深色），每条目 = desc + select 选择规则（domains 映射 / user_only）+ palette（渐变 / 色彩角色 / 白背板按尺寸两档）+ selection 优先级链 | UX-SPEC 第 3 节、PROMPT 第十二节、OHOS 色彩 token 值表 |
| `ladders.json` | 字号档（12/14/16/18/20/24/30/32/38）、间距档（2/4/6/8/10/12/14/16）、圆角档（卡 20/背板 12-16/胶囊 18）、hero 降档序列（38/30/24/20）、压力宽度预算口径 | UX-SPEC 第 2 节 |
| `components.json` | **11 个组件角色**（视觉规格 + color_role）+ select_rules 语义→角色规则表 | Form 协议 + UX-SPEC |
| `assets.json` | 72 项素材白名单（src/description/dyeable）+ 图标规格（20×20/contain） | CreateMyCard 素材库 |

另有 `copy_templates.json`（文案模板）与 `resources/base/media/`（154 个端侧素材文件，复制自 CreateMyCard；**路径前缀只在 `src/paths.py` 定义**，registry 只登记文件名，挪目录只改一处常量）。

### 6.1 骨架（skeletons.json）

每个骨架条目：`size`（适用尺寸）、`select`（路由键：objects/actions 数量区间 + features 特征）、`priority`（同命中取高）、`tree`（发射模板）。tree 节点字段：

- 容器节点：`component`（Row/Column/Stack）+ `styles`（精确几何，`background: "gradient"` 或 `"backboard"` 由主题层解析）；
- 槽位节点：`slot`（`header`/`content`/`hero`/`action`/`zone:N`/`aux:N`/`action_zone:N`/`list`/`text_flow`/`triple`）+ `optional`（空槽省略）。

16 骨架速览（v3.7 起：S1~S6 / W1~W10）：

| 骨架 | 尺寸 | 适用 | 关键几何 |
|---|---|---|---|
| S1-single-info | 2×2 | 单信息/倒计时（hero + ≤2 信息 + 无动作） | 居中组（**不套 CardHeader**，标题并入组内） |
| S2-info-pair-action | 2×2 | 标题+内容+底部动作（**兜底**） | CardHeader 20vp + content layoutWeight:1 + action 36vp |
| S3-info-dual-action | 2×2 | 单对象双动作 | 38vp 信息组（固定内高，容量引擎管辖）+ 两张 36vp 胶囊（间距 8，以真实数据为准） |
| S4-stacked-zones | 2×2 | 恰好 2 个业务对象 | padding 8 + 两个 134×63 白背板 |
| S5-primary-support | 2×2 | 无动作 + 信息 ≥3（主区 + 辅区，数据 M1） | CardHeader 20 + primary/ support 各 layoutWeight:1 |
| S6-primary-bottom-action | 2×2 | 单**图标入口**动作（数据 M2） | CardHeader 20 + primary layoutWeight:1 + 底部行 40（辅信息列 78 / 圆钮 40×40） |
| W1-focus-aux | 2×4 | 左主焦点 + 双辅助（**2×4 兜底**） | 左 136 + 右两个 130×59 背板 |
| W2-text-flow | 2×4 | 文字叙事（无动作纯文本） | 最多三组文字单元 |
| W3-ring-detail | 2×4 | 环形主指标（progress 特征，休眠） | 可选标题 20 + 主环 92/stroke 8 + 说明列 134 |
| W4-metric-triple | 2×4 | 三个同级指标 | 可选标题 20 + 三列 88/96/88 + Divider 1×64（主题动作底色） |
| W5-progress-detail | 2×4 | 线性进度+双明细（休眠） | 可选标题 20 + 进度区 45 + 276×8 进度条 + 两个 134×45 明细板 |
| W6-agenda-cta | 2×4 | 焦点+双动作背板 | 左 136 + 右两个 130×59 动作板 |
| W7-list-rows | 2×4 | 三项列表 | 行 276×28、gap 8、圆角 8 |
| W8-quad-cells | 2×4 | 4 个对象 | padding 8 + 2×2 网格 138×63 |
| W9-dual-backboards | 2×4 | 2 个等权对象 | 两个 138×134 大板（板内 114×110） |
| W10-triple-backboards | 2×4 | 3 个对象 | 左 138×134 + 右两块 138×63 |

### 6.2 组件角色（components.json）

角色 = 语义类型到视觉规格的映射。当前 13 角色：

| 角色 | A2UI 组件 | 规格 | 用途 |
|---|---|---|---|
| header_title | Text | 12/400、高 20、primary_text | 卡片标题（CardHeader 形态） |
| hero_value | Text | 降档序列 38/30/24/20、700 | 大数字主焦点 |
| hero_context | Text | 12/400、secondary_text | hero 上下文（主区第二项：单位/状态） |
| status_lead | Text | 18/700、高 24 | 突出状态/副标题 |
| support_line | Text | 14/500、高 20 | 支撑信息行 |
| zone_value_line | Text | 14/700 | 小背板第一行（对象名+主值） |
| zone_aux_line | Text | 12/400 | 小背板第二行 / 主区辅区行 |
| meta_note | Text | 12/400、meta_text（60%） | 弱化注释/来源 |
| list_row | Text | 12/400、高 28 | 列表条目行 |
| capsule_action | Button | 高 36、圆角 18、14fp、action_bg 底 | 胶囊按钮（图文入口） |
| icon_action | Stack | 40×40、圆角 20、图标 20×20 居中、action_bg 底 | 圆形图标入口（S6 bottom_action；图标槽未启用时用 ≤2 字短标签占位） |
| check_action | Checkbox | label+select | 开关形态（Form 协议无 Toggle） |
| compact_value | Text | 20/700（下限 16） | 三列指标/并列比较 |

select_rules 顺序匹配（命中即停）：`actions:true + toggle → check_action`；`actions:true → capsule_action`；`title → header_title`；`短(≤8字) discount/price/stat → hero_value`；`discount/price/stat/deadline → status_lead`；`subtitle → support_line`；`member_tag/source → meta_note`；空条件兜底 `support_line`。**槽位感知优先**（P4，先于语义规则）：`triple:* → compact_value`；`bottom_action → icon_action`；`primary → 首项 hero_value/status_lead，其余 hero_context`；`support`/`bottom_info → zone_aux_line`；`zone:*`/`aux:*` → 首项 zone_value_line、其余 zone_aux_line。

### 6.3 内容区排法表（content_forms.json）

**要解决的问题**：同一个内容槽位可能有多种排法。以 `content` 为例——一条电量百分比要画成"环 + 标签列"，两条带标签的条目要画成"标签在左、数值在右"，三条以上放不下时容量引擎还会给出"换轴/合并"。这些判断以前写成 `compiler._fill_children` 里的一串 `if/else`，**优先级等于书写顺序**，加第四种排法时没人说得清该插在哪。

**定义**：排法（form）= **槽位内部怎么排**。它既不是骨架（骨架 = 大分区：顶部标题 / 中部内容 / 底部动作），也不是角色（角色 = 单个条目的字号尺寸）。三者界限：

| 变化类型 | 归到哪 | 例子 |
|---|---|---|
| 大分区（容器拓扑 + 方向）变了 | 骨架 `skeletons.json` | 环占满整卡、没有 header/action |
| 槽位内部排布变了 | 排法 `content_forms.json` | 环 + 标签列 / 标签值行 / 一条一段 |
| 单个条目的字号尺寸变了 | 角色 `components.json` | 主值 30/700 还是 18/700 |

**适用范围（重要）**：只有"多种排法会抢同一个槽"的槽位才进表，即 `content` / `primary` / `support` / `bottom_info`。

| 槽位 | 今天的决定方式 | 是否进表 | 原因 |
|---|---|---|---|
| `content` / `primary` / `support` / `bottom_info` | 多个 `if` 分支竞争 | **进表** | 存在真正的"选哪个" |
| `header` / `action` / `action_zone` / `bottom_action` | 条目类型 → 组件，一对一 | 不进 | 表里只会有一行，等于把 switch 搬进 JSON |
| `zone:*` / `aux:*`（背板） | `layout_variants.json` 的候选序列（stack→row→merged→丢弃→截断） | 不进 | 那是**试算**不是**选择**，写进表会让表变成编程语言 |

**表结构**（`registry/content_forms.json`）

```json
{"order": 1, "id": "ring_stat",
 "when": {"slots": ["content"], "exact_types": {"percent": 1}, "max_items": 2, "all_present": true},
 "spec": {"ring": 52, "strokeWidth": 6, "icon": 20, "rowHeight": 52, "iconGap": 8, "lineGap": 2,
          "label": {"fontSize": 14, "fontWeight": 700, "height": 18, "colorRole": "primary_text"},
          "value": {"fontSize": 12, "fontWeight": 400, "height": 16, "colorRole": "secondary_text"},
          "colorRole": "primary_text", "trackRole": "action_bg", "iconRole": "meta_text"}}
```

- `order`：从小到大依次判断，取**第一个**满足的；
- `when`：只允许使用白名单键（`slots` / `has_layout_rows` / `all_present` / `exact_types` / `min_items` / `max_items` / `all_have_label` / `no_promoted_hero`），拼错键会被 `tests/test_forms.py` 抓住（否则会静默变成"永远命中"）；
- `spec`：这种排法的几何与配色角色。**改外观只改这里**，不动代码；
- 最后一条必须是**无条件兜底**（`when: {}`），保证任何槽位都有排法可走。

**与容量引擎的关系**：容量降级仍是算法，留在 `layout_variants.json` 与 `assemble` 里；表里用 `{"order": 0, "id": "capacity_rows", "when": {"has_layout_rows": true}}` 把"容量已给出逐行决策"原样表达成一行数据。**顺序从此写在数据里，不再取决于代码先后**。

**新增一种排法的步骤（四步，缺一不可）**
1. 表里加一条 `order` / `when` /（可选）`spec`；
2. `src/forms.py` 写同名函数 `def _your_form(em, slot, f, layout) -> list[组件]`；
3. 在 `EMITTERS` 里登记一行；
4. 跑 `python tests/test_forms.py`（表与实现必须一一对应）与 `python tools/snapshot_pipeline.py`（重构类改动要求输出 diff = 0）。

**准入条件**（防止"每张卡造一种排法"）：金标里至少 2 张、能被条目属性稳定判断、能说明"放不下时交给容量引擎"。三条缺一不注册。

**验证方式**：`tools/snapshot_pipeline.py` 用确定性桩模型跑 62 条（10 用例 + 49 条真实 query + 3 条排法探针）并逐条比对 `full-a2ui`，要求**一字不差**；探针里必须至少各有一条命中的环形、标签值行、容量换轴卡。

## 7. P1~P7 程序模块设计

### 7.0 职责划分：五层与三类

这一小节是 §7.1~§7.7 的总图，回答两个问题：每一步在决定什么？哪些步骤在论文里可以归为一类？

判断只有一条：**这一步的数字，是模板常量、查表结果，还是真实测量算出来的？**

#### 五层（实现视角）

| 层 | 步骤 | 决定什么 | 数字来源 | 交给模型的后果 |
|---|---|---|---|---|
| 语义 | M1 + P1 | 有哪些条目、各是什么类型、分属哪些业务对象、什么领域 | 无数字 | 本来就是模型在做 |
| 结构 | P2 + P3 | 用哪个骨架、每条进哪个槽、每槽几条 | **常量**（骨架里写死的 3 / 1 / 2 / 3） | 可以交，且是唯一有意义的边界 |
| 样式规格 | P4 | 每条挂哪个角色（字号档、字重、行高、颜色角色、组件类型） | **查表**（13 角色 × 批准档位 12/14/16/18/20/24/30/32/38） | 交出去无收益：模型没有信息优势，只会记错表 |
| 几何 | P5 | 这档字号在剩余宽度里放不放得下、换行、截断、降档、hero 提不提 | **真实测量** | **不可交**：可用宽度只有排一遍才知道 |
| 外观与输出 | P6 + P7 | 角色 → 色值、树 → 三行 JSONL | 查表 + 序列化 | 交出去无收益：零决策或纯格式 |

**一句话**：整条流水线只有 P5 一格需要真实测量。这就是"几何必须由程序求解"的严格表述——不是因为模型不够聪明，而是因为这一格的正确性依赖一个模型拿不到的量。

#### 三类（论文视角）

| 类 | 包含 | 能否交给模型 | 在论文里的角色 |
|---|---|---|---|
| **可交决策** | P2 + P3（结构） | 能，且值得讨论 | 实验自变量：结构权归谁、结构自由度多大 |
| **查表类** | P4（规格）、P6（外观）、P7（序列化） | 能，但无收益（结果只会相同或更差） | **固定给程序**，不做实验，作为各条件的共同部分 |
| **不可交** | P5（几何） | 不能（无测量信息） | 所有方案共有的程序部分，恒定 |

三类之外还有一个特例：**P1**。它同时装了两件事，论文里必须能分开：

| 别名 | 具体动作 | 是否改内容集合 |
|---|---|---|
| **翻译** | 同义词映射、ref 重排、类型名对齐 | 否 |
| **修复** | 丢非法条目、info/action 去重、stat→percent、悬空引用清洗、未归属字段并入首对象 | **是** |

做"无保障"对照时必须能单独关掉后半部分；否则 P1 会替所有方案吸收抖动，对照组不成立。

### 7.0.1 运行选项与校验器（实验才用，生产默认全开）

三个布尔选项，只影响"模型输出不合法时程序怎么处置"，不影响正常路径的产物：

| 选项 | 管什么 | 关掉之后 |
|---|---|---|
| `repair_plan` | **入口修正**：info/action 去重、stat→percent、悬空关系清洗、未归属字段并入首对象 | 这四条不执行，模型的分组与类型错误原样流下去 |
| `repair_card` | **出口修正**：按校验结果缩字号、截断、降档、换组件 | 违规卡原样输出 |
| `placeholder_card` | 解析失败时输出"暂无可展示的内容"占位卡 | 返回 `meta.failed = True` 且 `ir = None` |

实现：`src/pipeline_options.py`（`PipelineOptions` + `load_options()`），环境变量前缀 `CARDGEN_`；也可以由 `generate(..., options=...)` 显式传入——测试与批跑用这条，避免污染进程环境。

**校验器不是开关，是库函数。** `src/validate.py` 的 `validate_a2ui()` 返回结构化违规（`code / where / detail / severity`），出口修正与评测共用同一份规则（原先这 55 行住在 `tests/run_cases.py` 里，统计脚本够不着）。理由很简单：校验是尺子，关掉就量不出"没修的时候有多少违规"，而"有多少违规"正是"修复救了多少"的唯一证据。

**纪律**：默认值必须等于生产行为（三项全开）。`snapshot_pipeline` 65 条在默认值下必须一字不差——这是"加开关没改行为"的硬证据。

### 7.0.2 度量工具链（评测用，不在产品路径上）

一次生成 = 一行记录（`src/measure.py`），几何与内容两把尺子事后再回填。这样"换个口径重算指标"不用重跑模型。

| 环节 | 工具 | 吃什么 | 产出 |
|---|---|---|---|
| 记录 | `src/measure.py` | `generate()` 结果 | 一行固定字段：协议违规 / 分阶段耗时 / token / 骨架 / 指纹 / 卡面文字 |
| 跑批 | `tools/run_condition.py` | 条件名（L4 / L4-NR） | `records.jsonl` + `cards/<tag>.jsonl` |
| 内容 | `tools/build_content_oracle.py` → `tools/measure_content.py` | 金标 DSL → 基准；记录 + 基准 | 覆盖（漏）/ 保真（编）/ 重复 |
| 几何 | `tools/measure_geometry.py` | 记录 + 原始产物 | 越界卡数、裁切卡数、最小字号、低于 12fp 节点数 |
| 稳定性 | `tools/resample_stability.py` | query × N 次重采样 | 字段全一致率、产物逐字一致率 |
| 出表 | `tools/build_metrics_report.py` | 各条件的 `records.jsonl` | Markdown 汇总表（论文表 1/表 3 原料） |

**基准必须独立于被测系统**：内容对错的基准来自金标抽出的事实集（`fixtures/content_oracle.json`，49 张卡 128 条），不是被测系统自己的 plan——L1 根本没有 plan，用它当基准就不可比。

**快慢分开**：协议校验在流水线内（微秒级，修复要用它拿清单）；几何测量在流水线外（每张几百毫秒，要起渲染器）；内容与稳定性也在外。

#### 记录长什么样

一次生成落一行，字段固定（`src/measure.py:build_record`）。**先定字段再写代码**——字段定不下来的指标，说明它还没有判据。

| 字段 | 含义 | 来源 |
|---|---|---|
| `tag` / `condition` | 卡片编号 / 实验条件 | 跑批脚本传入 |
| `failed` | 生成是否失败（关掉兜底后才会出现） | `meta.failed` |
| `clean` | 无违规且未失败 → 协议干净 | `violations` 为空 |
| `violation_codes` | 按 code 计数的违规（"哪类错最多"靠它） | `validate.py` |
| `skeleton` / `size` / `domain` / `theme` | 结构决策的结果 | `ir` |
| `fallback_count` | 兜底日志条数 | `meta.fallback_log` |
| `timing` | 模型 / 装配 / 校验 / 总时长（ms） | `perf_counter` |
| `cost` | 调用次数、重试次数、in/out token | `llm.stats_delta` |
| `options` | 三项运行选项的实际取值（回放实验用） | `pipeline_options` |
| `fingerprint` | 产物指纹（surfaceId 已归一） | `measure.fingerprint` |
| `static` | 最小字号 / 低于 12fp 与 10fp 节点数（C-05 两条线）/ 组件数 / 文字条数 | `measure.static_metrics` |
| `card_text` | 卡面全部文字，内容指标只吃它 | `measure.extract_text` |
| `layout` | 几何测量**回填**：越界（含单节点最大像素，供 C-04 合格判定）、裁切、最小字号、两条字号线 | `measure_geometry` |
| `content` | 内容测量**回填**：覆盖（A4a 全量 + A4b 必显）、保真（空数据卡置 `empty_data`，C-03）、重复 | `measure_content` |

> 生成失败的卡（C-01）在 `build_record` 里记一条 `generate.failed` 违规，`content` 由 `measure_content` 强制为"覆盖 0 / 保真不计入"。六条口径的完整规定见论文文档 §15；本表只记代码落点。

#### 一条链跑完

```bash
python tools/run_condition.py L4 --out runs/L4        # 生成 + 落记录与产物
python tools/measure_content.py runs/L4/records.jsonl # 原地回填 content
python tools/measure_geometry.py runs/L4              # 原地回填 layout
python tools/build_metrics_report.py runs/L4 runs/L4-NR --out runs/report.md
```

`--mock` 可离线跑通链路，但它只是关键词桩，**指标数值没有意义**，只用来验证工具本身。

#### 三个口径细节（决定指标可不可信）

1. **双向包含**：基准是 `68`、卡面写 `68%` → 算命中（单位是卡面加的，不是编造）；
2. **数字边界**：`168` 里不能把 `68` 算成命中，否则覆盖虚高；
3. **复合值拆分**：金标写 `25℃ / 32℃` 时拆成两条事实，否则"只显示其中一个"会被算成整体命中；
4. **tag 归一化**：批次 tag 是 `q01`、基准键是 `q1`，查不到就静默变成空基准（这条踩过一次）。

### 7.1 P1 归一化（normalize）

继承 v2 全部规则（枚举对齐→同义词→丢弃、ref 重排、入关截断 30/10、悬空边清洗、fallback_log 贯穿），v3 新增：

1. **domain/theme/size/keep 归一化**：domain 不合法回退 `unknown`；theme 非法丢弃；size 非法回退 `auto`；keep 非法回退 `must`。
2. **intent 派生**：M1 未显式给 intent 时由 domain 派生（promotion/notice 等可直接映射，其余 info_card）。
3. **objects 校验**：fields 引用重映射、空对象丢弃；有显式对象时未覆盖字段并入第一个对象（记 log）；无显式对象时隐式单对象兜底（规范默认行为，**不记 fallback**）。
4. **groups 不再做覆盖兜底**（装配以 objects 为准）。

### 7.2 P2 骨架路由（skeletons）

**特征派生**（`derive_features`，全部确定性规则）：

| 特征 | 判定 |
|---|---|
| n_objects | len(objects)，至少 1 |
| hero | 存在 discount/price/stat 且 hint ≤8 字 |
| list | 非标题信息 ≥3 条且类型 ≤2 种 |
| triple_stats | 恰好 3 条同类型非标题信息 |
| text | 无 hero 且全部为文本类信息 |
| progress | 恒 false（原型无数值+total 语义，W3/W5 休眠） |
| icon_action | 存在 action 且 `type == "icon_button"`（图标入口；S2/S6 的唯一结构分界，见 §8.5 与 UX-SPEC §11.3） |

**尺寸决策**（`decide_size`）：用户显式指定优先（`2x2`/`2x4`），否则一律 `2x2`。**对象数不放大画布**——金标 52/52 全 2×2，其中含跨 3 个数据源的卡；内容装不下走 P5 容量降级，不升尺寸。

**路由决策表**（条件按序命中即停）：

```text
2x2:  objects≥2 → S4 ｜ actions≥2 → S3 ｜ 单动作∧icon_action → S6
      ｜ 无动作∧info≥3 → S5 ｜ hero∧无动作∧info≤2 → S1 ｜ else → S2（兜底）
2x4:  objects≥4 → W8 ｜ objects=3 → W10 ｜ objects=2 → W9 ｜ actions≥2 → W6
      ｜ triple_stats → W4 ｜ list → W7 ｜ progress → W3 ｜ text∧无动作 → W2
      ｜ else → W1（兜底）
```

超限适配（对象数截断、动作数不符）记 fallback_log。

> 主题选择不在本步骤。它由 P6 执行（§7.6），此处只声明：P2 不读 theme、不因主题改变骨架。

### 7.3 P3 region 装配（slot_assign）

把对象/条目/动作填进骨架 tree 的槽位。fills 结构 `{slot_id: {info: [refs], action: [refs]}}`：

- **zone:N 槽**（多对象骨架）：对象 N 的字段填入（≤3 项，超出记 log 丢弃）；动作绑定到该背板**容器 onClick**（非子组件，S4/W8/W10 语义）；`binds` 关系决定动作归属对象。
- **单对象骨架**：header ← title 条目；hero ← hero 条目；content/text_flow/list/triple ← 其余信息（≤3 项）；aux:N ← 后续对象或剩余信息（每槽 ≤2 项）；action ← 最多 2 个；action_zone:N（W6）← 每板 1 个动作。
- **覆盖率校验**：未安置条目按 keep 处理——must 记 `coverage check failed`，should 记 dropped。

### 7.4 P4 角色规格选择（component_select）

按 6.2 的 select_rules 顺序匹配，为每个条目产出 role；视觉规格（spec）在 P5 审计后定稿（hero 的最终 fontSize 由宽度预算决定）。

### 7.5 P5 拼装 IR + 宽度预算审计（assemble）

拼装规则（继承 v2）：文案填充（copy_templates→hint 兜底）、语义实例 ID（`title-r1`/`cta-primary-r4`）、绑定路径 `/data/items/{ref}`、意图贯穿校验、surface_id 程序生成。

**容量口径 v3 升级：字数 copy_spec → 压力宽度预算**：

```text
est_width(text, fontSize) = Σ (中文 1em ｜ 字母数字 0.65em ｜ 其他 0.85em) × fontSize
槽位宽度 = 骨架 tree 中该槽位容器宽 − 左右 padding（P5 从 tree 自动提取）

审计链：
  hero_value  → 降档序列 38/30/24/20，每档按 est×1.2 ≤ 槽宽 校验；
                全档不通过 → 20fp 语义截断并记 log（终局）
  普通文字    → est×1.0 > 槽宽 → 标点/CJK 边界语义截断 + "…"，记 log
  胶囊按钮    → est×1.2 > 槽宽 → 语义截断（2×2 文案上限 6 字由入关口径保护）
```

静态文案宽度已知故不加余量（1.0 倍）；1.2 倍余量仅用于 hero 降档与胶囊压力口径。数据类文字的运行时长度仍归渲染层兜底（§8）。

### 7.6 P6 主题装配（theme）

整条流水线**唯一处理主题的环节**（M1 仅传递用户颜色偏好这一语义事实）。输入 P5 的 IR，按主题目录执行：

1. **选主题**：priority 链 = M1 用户偏好 > 目录内 domain 映射 > 默认 blue；`user_only` 条目（深色）不可被 domain 映射命中；
2. **解析色板**：把选中主题的渐变/色彩角色/白背板（按尺寸两档）解析为具体值，写入 `ir["palette"]`；
3. **涂装骨架树**：tree 上的语义背景（`background: "gradient"` / `backgroundColor: "backboard"`）替换为具体样式，解析后的树写入 `ir["tree"]`；
4. **涂装条目**：entry spec 的 `color_role/bg_role/ink_role` 替换为具体色值（角色体系来自 P4，本步骤只做"角色名 → 色值"）；
5. **挂载点**：对比度校验（着色后执行，当前未实现）。

**边界纪律（步骤契约）**：只写颜色、背景、透明度、图像；禁止改宽高、间距、圆角、结构、行数、内容。

### 7.7 P7 发射器（compiler）

输入着色后 IR（`ir["tree"]` + `ir["palette"]` + 具体色值的 spec），**零色板知识**，两阶段发射：

1. **`_build`（递归建树）**：槽位节点按 fills 填充子组件；zone 槽按**小内容蒙版两行规则**合成（第一行 `14fp/700 对象名+主值`，第二行 `12fp/400`，多项用 `" | "` 连接，字色取自 palette）；zone 动作绑背板容器 `onClick`；空槽位整体省略（协议禁止空容器）。
2. **`_flatten`（前序展平）**：**root 第一位、父先子后**——与 CreateMyCard 正式产物发射顺序一致，兼容顺序处理 children 引用的渲染端。

**协议合规保证**（发射器统一负责）：

| 规则 | 发射结果 |
|---|---|
| 消息结构 | 三行 JSONL：createSurface（catalogId `ohos.a2ui.extended.catalog.form`）+ updateComponents + updateDataModel |
| 组件白名单 | 仅 Form 十组件 Text/Image/Divider/Progress/Button/Checkbox/Row/Column/List/Stack |
| root shell | width/height `matchParent`、borderRadius 20、clip: true、主题渐变背景 |
| 样式承载 | 全部收进组件 `styles` 嵌套对象；语义字段（content/label）扁平 |
| 事件 | `onClick: [{call, args}]` EventHandler 数组，恰好 1 个 handler；无 Button.action |
| 开关 | Checkbox（label + select），不发射 Form 排除的 Toggle |
| 首帧数据 | updateDataModel：`path=/data`、`value.items.{ref}` = 条目 copy（占位首帧） |

`a2ui` 简化格式保留为调试视图（role + copy + binding 汇总），不再是交付产物。


**排法分派**：发射器只保留三类专用分支——背板（`zone:`/`aux:`，走 `_zone_children` + 容量候选）、标题区（标题 + 20×20 图标）、动作区（胶囊/圆钮/开关）。其余内容类槽位（`content`/`primary`/`support`/`bottom_info`）**统一交给 `src/forms.py` 查表分派**，实现见 §6.3。新增内容排法不得再往 `_fill_children` 加 `if`。

## 8. 容量适配机制：候选表与首个可行解

槽位放不下内容时（如 S3 header_area 126×40 要放 38fp 的值 + 状态行），流水线不做回溯搜索，而是**前向枚举 + 首个可行解**：候选由 P4 以有序数据表输出，容量引擎（P5 调用）逐候选做**宽度 + 高度双预算**验收，第一个通过者定稿，链尾截断兜底必过。看似"试了不行再换一个"，实现上没有任何状态撤销——只是一层有界 `for` 循环。

### 8.1 候选的边界纪律

**候选只允许改变"区划之内"的排布，永远不允许改变区划本身。**

- 区划（谁在哪块区域、区域多大）= 骨架职责 → P2 路由决定，适配过程不碰；
- 区划内排布（几条、横排纵排、什么字号、合不合并）= 容量适配职责 → 本章的候选空间。

这条纪律同时决定了骨架策略：**只要一种新形态没有改变区划，它就应该是一条候选，而不是一个新骨架**（见 §8.5）。

### 8.2 原子变换算子

所有候选都是这 7 个算子的组合（按"保真度代价"从低到高）：

| # | 算子 | 语义 | 合法性前置条件（guard） | 规范依据 |
|---|---|---|---|---|
| T1 | 保原形 | 结构、字号都不动 | 总是合法 | — |
| T2 | 降档 | 字号/字重沿梯级下降（连续） | 目标档位在规范允许区（如主数字 38→30→24→20） | UX-SPEC §5.2 主数字降档序列 |
| T3 | 换轴 | 同一组内容 纵排 ↔ 横排 | 横排时各行宽度之和 ≤ 槽内宽；纵排时行高之和 ≤ 槽内高；**值-单位组永不换轴**（单位不得换行） | UX-SPEC §5.2「同一 Row 不同字号文字底部对齐」 |
| T4 | 合并 | 多条 → 一条 Text，用规范分隔符（` · ` 或 ` \| `） | ① 条目 ≤2；② 每条都短（合并后满足宽预算）；③ 语义不冲突（值与状态可合，值与另一指标不可合） | 「天气与日程…二者固定合并成一个单行 Text（如 29° · 多云）」 |
| T5 | 拆分 | 一条 → 两条（值/单位分离） | 拆出的两条同行不同字号；拆后总高仍超限则不采用 | 「数字与单位拆成两个 Text 时仍属于同一行」 |
| T6 | 省略 | 按 keep 优先级丢弃条目 | 仅当存在 `keep=should`；**must 不可省略**；动作只降形态不删除 | 「仍超出再删除低优先级可选字段」 |
| T7 | 截断 | 语义截断，带 `…` | 总是合法（链尾兜底） | §7.5 语义截断 |

**禁止算子**（避免走偏）：改变槽位数/尺寸（区划级）、换骨架（区划级，靠路由前置条件收紧解决）、单位换行、把值 Text 拉到整行宽再把单位挤到另一端（规范明文禁止）。

### 8.3 候选生成策略（四步）

```
输入：槽位（几何 width×height、形态 kind）、条目[]（role/copy/keep/语义关系）

第 1 步 · 行组划分
  值 × 单位 → 必同行；值 × 状态 → 可同行可断行（两种都生成）；
  同级指标 → 各自成组；标题 → 独立组；图标 × 文字 → 可同行可去图标
第 2 步 · 结构候选（行组数 × 轴）
  for n_rows in [N, N-1, …, 1]（递减；合并需过 T4 guard）
      for axis in [纵排, 横排]（T3 guard 过滤）→ 生成候选
第 3 步 · 字号梯级（候选内部，连续计算）
  主条目沿梯级内插最大可容纳字号；次要条目取固定档（12/400 等）
第 4 步 · 偏好排序（数据表，离线定义，金标校准）
  T1 < T2 < T3 < T4 < T6 < T7（保真度）；同代价内保层级（纵排）优先于保字号（横排）
```

### 8.4 场景模式库（12 个模式）

| 模式 | 内容形态 | 候选序列（按偏好） | 备注 |
|---|---|---|---|
| M1 值+状态 | 68% + 充电中（单行区 126×40） | 纵排 20/12 高 47 ✗ → **横排单行 24/12 高 34 ✓** → 横排大字 38/12 行高 53 ✗ → 合并 `68% · 充电中` → 纵排+截断 | 高度是硬瓶颈 → 优先换轴保字号 |
| M2 值+单位 | 68 + % | 同行不同字号（底部对齐 + 单位字底补偿 `min(8, ceil(Δ/4))`）→ 降档 → 合并格式化字符串 → 截断 | **无换轴候选**（单位永不换行） |
| M3 同级多指标 | 3 条指标 | 三列等宽 → 纵向"标签—值"对齐行 → 2+1 → 丢 should → 截断 | 列/行数由条目数派生 |
| M4 小背板两行 | 对象名+主值 / 次要状态（134×63、138×63、130×59） | Column 两行 → 次要项 ` \| ` 合并进第一行 → 只留第一行（should）→ 截断 | 固定高度硬盒，**不生成换轴候选** |
| M5 标题区 | 标题 + 图标 | 文字 98 + gap8 + 图标 20 → 去图标文字占满 126 → 降档 + 截断 | 候选空间由规范直接给出 |
| M6 列表行 | 3 条日程（时间+标题） | 每行 Row[时间/标题] → 行内合并单 Text → 减行（should）→ 行内截断 | — |
| M7 图文胶囊 | 图标 20 + 文字 14 | Row[图标, gap8, 文字] → 去图标纯文字 → 文字 14→12 → 截断 | 规范先例：无素材时保留纯文字 |
| M8 W1 焦点区 | 上下文 + 主焦点 + 支撑 | 三层纵排居中 → 合并上下文与主焦点 → 支撑降 12fp → 丢支撑 | 「value-led 最多三层」 |
| M9 动作区 | 2 个动作 | 纵排两胶囊 → 文字 14→12 + 去图标 → 次动作降纯文字链接 → 截断 | **动作不可丢**（T6 只降形态） |
| M10 W4 列内 | 值 + 标签（列高 84） | 纵排居中 20/12 → 统一降档 18 → 列内合并 `80分` → 截断 | — |
| M11 时间日期 | 日期/星期/时间/标题 | 日期区独立小行（126×16）→ 并入标题行 → 日期与星期二选一（默认保星期） | 取舍规则驱动，需读语义 guard |
| M12 倒计时特例 | 标题 + 纯数字 + 单位「天」 | 三 Text 纵排居中（数字可 38）→ 降档 → 合并标题 → 截断 | S1 / W9 特例 |

### 8.5 骨架影响结论：容量候选不新增骨架（真实数据另行反哺）

**第一层结论（容量维度，不变）**：

1. **区划 vs 区划内**：12 个模式的候选全部发生在区划内部（槽内换轴/合并/降档），不改变区划——骨架的定义就是区划，候选再多也不构成新骨架；
2. **规范禁止叠加布局**：「整卡由标题区、内容区、按钮区组合；各区域遵循所选骨架，不额外叠加另一套布局」——槽内换轴是区域内部的合法排布；
3. **骨架已被金标验证覆盖**：规范原文「骨架说明空间结构，完整卡覆盖当前 15 个 few-shot；两者不能混为 15 种骨架」；
4. **区划级需求靠路由前置条件解决**：W1 要求「一个主要信息 + **两组**辅助信息」，只有一组时是不该选 W1（收紧 P2 路由），而非新造骨架。

**何时才该新增骨架（四条判据，需同时满足）**：① 出现现有骨架无法表达的新区划拓扑；② 现有骨架无一能通过收紧路由条件承担；③ 有对应区域规格（不得自造数字）；④ 金标或真实需求中**重复出现**。容量 12 模式无一命中——容量维度不新增。

**第二层结论（v3.7：真实卡片数据反哺）**：对用户提供的 52 张高质量卡片 DSL（`生成卡片的DSL结果/`，全 2×2）做区划签名聚类，按判据逐条核对后**新增 2 个、证伪 1 个**：

| 区划签名 | 张数 | 结论 | 说明 |
|---|---|---|---|
| `body[primary, bottom]`（主区 + 底部复合行：辅信息列 78 + 40×40 圆钮） | 13 | **新增 S6** | 与 S2（`content + action`）区划不同：动作不是独立整行胶囊，而是与辅信息同处一条 40 高的底行；判据 ①②③④ 全中 |
| `body[primary, support]`（主区 + 辅区纵排，无动作） | 9 | **新增 S5** | S1 要求 hero∧无动作∧info≤2，S2 是无动作时的"内容区"语义，均无法表达"两块等权纵分"；判据 ①②③④ 全中 |
| `body[left, right]`（疑似左右双栏） | 0 | **不采纳** | 复核发现该容器实为 **Column**（区域名才叫 left/right），全量扫描 52 张**不存在任何左右并列容器**（唯一的等宽 Row 是 S6 的底行 78+40）→ 判据 ④ 不成立，S7 从资产中移除 |
| `body[tomorrow, dayafter]` / `body[chengdu, shanghai]`（上下两块 63 高） | 各 1 | 折入 S4 | 与 S4 同为"上下双业务 134×63"，只是缺白背板背景（稀疏亚型），不构成新骨架 |
| `body[content, action]` / `body[content]` | 9 / 6 | 折入 S2 | 与既有 S2 一致（无动作时 action 槽空置省略） |
| `body[content, cta, cta]`（双 CTA） | 3 | 折入 S3 | 与既有 S3 一致；v3.8 按金标把信息组内高定为 38、双胶囊间距定为 8（规范正本写 6，以数据为准） |

**S2/S6 的判据说明（重要）**：两类卡片的**语义完全等价**（单业务 + 一个"点一下去某处"的入口），差异只在入口的**呈现形态**——S2 是可点区域更大的图文胶囊（`Row h36` + 图标 + 文字），S6 是 40×40 圆形图标钮（`Stack` 套图标，无文字）。数据中两种形态由生成器随机选择，**无法从 query 语义推导**（同为"点一下查看天气详情"的 q1 走 S2、q25 走 S6）。因此方案把该差异显式提升为 M1 的 `action_type` 枚举（`primary_button` = 带文字标签 / `icon_button` = 图标入口），由模型在理解 query 后声明——这是唯一能同时忠实还原两类卡片、又不让程序瞎猜的分界方式。

### 8.6 资产与接口（实现）

**三份资产**

| 资产 | 内容 |
|---|---|
| `registry/layout_variants.json` | 槽位形态判据（`board_slot_prefixes: ["zone:","aux:"]`、`single_line_max_h: 46`）、每形态的有序候选序列、guards、字号梯级、间距与分隔符 |
| `registry/components.json` | 角色规格新增 **`min_size` 下限**（hero_value 20 = 主数字降档序列终点，其余 12）——决定"继续缩字号"与"换结构"的分界线 |
| `registry/skeletons.json` | 槽位几何即容量来源（`_slot_boxes` 提取内宽/内高/标注）；槽位节点可选带 `kind` 显式标注（board / flow / single_line）——**几何与命名都无法区分时以标注为准**（如 W4 三列 88 宽与 W9 大板 138 宽、W6 焦点区 136 宽易混） |
| `registry/components.json`（新增角色） | `compact_value`：三列指标/并列比较的紧凑数值（20/700，下限 16）——triple 列不用 hero（38）也不用 zone 行角色（14） |

**两个模块**

| 模块 | 职责 |
|---|---|
| `src/metrics.py` | 文字度量公共基础：`est_width`（压力宽度）、`est_height`（1.4 × 字号 × 行数）、`semantic_truncate`——独立成模块以避免 assemble 与 capacity 循环依赖 |
| `src/capacity.py` | 容量引擎：`slot_kind()` 判形态（board 按槽位命名优先，其余按几何），`adapt_slot()` 实现候选枚举 + 双预算验收 + 首个可行解，返回布局决策 |

**流水线接口**

1. **P4 槽位感知**：`select_roles(entries, slot_of)` —— 按槽位形态定角色：board 类（zone:/aux:）走 zone 行角色（首项 `zone_value_line`、其余 `zone_aux_line`）；triple 列走 `compact_value`（紧凑数字）；hero 角色只出现在普通内容区（修复"小背板里出现 38fp 主数字"与"三列里出现 hero"两个根因）；
2. **P5 分流**：固定几何槽位（内高为数值）交 `capacity.adapt_slot()`；弹性槽位（内高 auto）沿用宽度预算（hero 降档 + 语义截断）；结果写入 `ir["slot_layouts"]`，并回写条目字号（`fonts`）与截断文案（`truncated`）；
3. **P7 按布局发射**：`structure = stack`（每行一项）/ `row`（同行包裹小 Row、底部对齐）/ `merged`（合成单 Text）；小背板按行组合成行文本（首行 700 + 对象名前缀，次行 400 + ` \| ` 连接），并对对象名前缀后的整行做宽度兜底截断；
4. **日志口径**：选择轨迹留在 `ir["slot_layouts"]`（可追溯）；仅**降级选择**（`truncate` 链尾兜底 / 丢弃条目）写 `fallback_log`——供候选表收敛闭环。

**业务背板的动作链路**（v3.6 补齐）：① **P1 去重**——同一入口既被 M1 声明为 info 又被声明为 action 时保留动作、丢弃重复信息条目（避免同一事实在卡面出现两次，并把"入口"当成信息渲染成纯文本）；② **P3 语义绑定**——动作按「字段绑定 > 文案与业务名互相包含 > 文案与字段提示互相包含 > 顺序填空板」匹配所属业务背板，每板恰好 1 个 handler（原先未匹配就集中到 zone:0，导致入口挂错板、第二个入口丢失）；③ **P7 入口板**——小背板（≤63 高）绑定动作时按"整块点击入口板"渲染：第一行入口名（动作文案）、第二行支撑信息（规范：W8/W10 右小板动作直接绑定背板）；对象名前缀在条目文案已含业务名时不再重复。

**已知边界**：`merged` 候选在现有模式中通常被 `stack`/`row` 支配（三者共享同一字号下限，而 row 可逐条独立降档），保留为 guard 兜底；语义强制合并对（如规范例"29° · 多云"）属内容层规则，列入演进项。容量引擎的**槽位形态判定顺序**：骨架显式 `kind` → 槽位命名前缀（zone:/aux:）→ 几何派生（内高 ≤ 46 单行区 / 内宽 ≤ 150 小背板 / 其余弹性）。

## 9. 卡片文字的来源与容量责任边界

继承 v2 三分法（数据类/query 自带/创作类）与责任边界：静态文案由生成链路兜底（P5 宽度预算），数据类文字长度兜底归渲染层。v3 变化：容量口径从"组件自声明字数"升级为"压力宽度预算"（§7.5），与 UX 规范的排版口径统一。

## 10. UX 规范对齐要点

规范正文与"规范 → 实现位置"对齐清单统一维护在 `cardgen-proto/ux-spec/UX-SPEC.md`（§1~§9 正文 + §10 对齐清单），本项目只维护这一份，此处不再重复。

## 11. 验证指标与通过标准

### 10.1 测试用例（fixtures/cases.json）

| # | query | 期望 |
|---|---|---|
| 1-6 | 促销/到期/通知/优惠/任意/空 | 意图正确、**骨架路由正确**、零 fallback、协议合规、不抛异常 |
| 7 | 长标题促销卡（容量专项） | 标题落 header_title 角色、宽度预算内、无硬截断 |
| 8 | 耳机 + 图标入口（"打开收藏的歌单"） | 路由 **S6**（icon_button）、零 fallback、协议合规 |
| 9 | 深圳天气和温度 | 路由 **S5**（无动作 + info≥3）、零 fallback、协议合规 |

用例 8/9 是 v3.7 新增骨架的常驻回归锚点：把 `expect_skeleton` 写进 cases.json，路由回归一旦发生立即报警（此前 S6 条件过松，促销类卡片被误路由到 S6 并触发容量降级，即由该断言暴露）。

### 10.2 验收场景（runs/acceptance/acceptance_outputs.json）

对照 CreateMyCard few-shot 金标的三个场景，产物为原生三行 JSONL，可直接粘贴渲染端目测：

| 场景 | 期望骨架/主题 | 对照金标 |
|---|---|---|
| 耳机状态 + 蓝牙设置按钮 | S2 / blue | 2x2-V02 |
| 深圳天气稀疏卡 | S2 / blue | 2x2-V04 |
| 手机+耳机盒双业务 | S4 / blue | 2x2-V05 |

### 10.3 通过标准（当前实测状态）

- 意图正确 8/8、骨架正确 8/8、零 fallback 8/8、A2UI 协议合规 8/8（协议断言：三行消息/组件白名单/无 Button.action/onClick 单 handler/root shell/updateDataModel）；
- 容量专项 16/16（`python tests/test_capacity.py`）；三验收场景零 fallback 且官方 a2ui_core MessageProcessor 解析闭合（v3.7 起加入 S6/S5 两条 query）；
- MockLLM 下零 fallback 是管线正确性的硬性自检；真实模型下 fallback 触发是安全网在工作（继承 v2 认知）。

### 10.4 验证方式

- `python tests/run_cases.py`：9 用例回归（8 主用例 + 1 容量用例）；
- `python tests/test_capacity.py`：容量适配专项 16 项断言；
- ~~`verify_a2ui_render.py`~~：**已移除**（依赖外部 `a2ui` 包，未随仓库分发，跑不起来）。协议合规改由 `src/validate.py` 的 15 条规则覆盖；官方 MessageProcessor 解析只作 2026-10-16 的一次性旁证，见 v3.5 变更记录；
- `python tests/test_gold_queries.py`：真实 query 数据集冒烟（49 条，断言零异常零协议违规；语义词数不断言——MockLLM 是桩模型）；
- `python tools/gold_dataset.py`：从人工校验输入输出对构建数据集（`fixtures/batch_queries.json` + `fixtures/gold_pairs.json`）；`check` 子命令做金标结构核验；
- `python tools/extract_skeletons_from_cards.py [--] pairs|regions|tree|summary`：卡片 DSL 区划聚类探索（`gold_dataset.py` 复用其解析函数）；
- `python tools/debug_pipeline.py "query"`：逐环节 trace + 裸 JSONL 落盘（`logs/`）。

## 12. 演进路线（原型均不含）

继承 v2 全部演进项（澄清反问、骨架模型补位、组件风格模型选择、创作文案、预览评审闭环、约束解码、RAG few-shot、蒸馏小模型），v3 新增/调整：

| 能力 | 说明 | 启用时机 |
|---|---|---|
| 图标槽启用 | CardHeader 右上/按钮区/环中心/S4 分区主视觉，按 assets.json 白名单选素材 | 视觉完善阶段 |
| Hero 安全盒 | 106×58 居中安全盒 + 压力样本降档的完整结构 | S2 数值亚型精细化 |
| W3/W5/W6/W8/W10 激活 | progress 特征与多对象 2×4 场景的端到端验证 | 输入侧支持能力候选后 |
| TaskSpec 式输入 | query + 数据/事件/素材候选（对齐 CreateMyCard 输入契约） | 接真实数据链路 |
| CardSpec 产出 | dataBindings 运行时刷新契约 + 真实 updateDataModel | 端侧数据链路 |
| P7 校验器 | 协议/绑定/单位/对比度规则子集（参照 CreateMyCard 校验器体系） | 质量对齐阶段 |
| 字段取舍深化 | 密度超限时的程序化删减顺序（drop→装饰→should→图标→隐式入口） | 真实模型接入后 |

## 13. 工程结构

```
cardgen-proto/
├── README.md
├── docs/
│   └── AI卡片生成架构方案-v3.md      # 本文档
├── prompts/
│   └── step1_structure_plan.md      # M1 提示词（domain/objects/keep 契约）
├── registry/                        # 封闭域资产六件套 + 文案模板
│   ├── enums.json                   # 枚举 + 同义词
│   ├── skeletons.json               # 16 骨架（select 路由键 + tree 发射模板）
│   ├── themes.json                  # 三套色板 + domain 映射 + 色彩角色
│   ├── ladders.json                 # 字号/间距/圆角档 + hero 降档 + 宽度预算口径
│   ├── components.json              # 11 角色（视觉规格 + color_role）+ select_rules
│   ├── assets.json                  # 72 项素材白名单
│   └── copy_templates.json
├── resources/
│   └── media/                       # 端侧素材（154 文件，来自 CreateMyCard）
├── src/                             # 程序环节
│   ├── llm.py                       # LLMClient + HttpLLM(占位) + MockLLM(五场景规则)
│   ├── normalize.py                 # P1 归一化（含 domain/objects/keep）
│   ├── skeletons.py                 # P2 骨架路由（特征派生+尺寸决策+决策表）
│   ├── slot_assign.py               # P3 region 装配
│   ├── component_select.py          # P4 角色规格选择
│   ├── assemble.py                  # P5 拼装 IR（压力宽度预算审计）
│   ├── sample_values.py             # 样本值推断（泛化提示 -> 真实样值，封闭域关键词映射）
│   ├── metrics.py                   # 文字度量（压力宽度 / 行高 / 语义截断，公共基础）
│   ├── capacity.py                   # 容量引擎（前向枚举 + 首个可行解，v3 §8）
│   ├── theme.py                     # P6 主题装配（选主题 + 着色，唯一主题环节）
│   ├── compiler.py                  # P7 发射器（原生三行 JSONL，零色板知识）
│   └── pipeline.py                  # 固定 workflow 编排
├── fixtures/                        # 固定输入与基准（入库）
│   ├── cases.json                   # 9 条回归用例
│   ├── gold_pairs.json              # 49 对金标数据集（派生品）
│   ├── content_oracle.json          # 应有事实集（评测基准）
│   └── batch_queries.json           # 49 条真实 userQuery
├── data/                            金标原始数据（49 对，98 文件）+ MANIFEST.sha256
├── refs/                            外部依据（A2UI 协议 / Basic Catalog / 鸿蒙 Form）
├── runs/                            一切产物（batch / stability / viz / debug / acceptance）
├── logs/                            运行日志
├── tests/run_cases.py               # 批量验证 + 协议断言
├── tests/test_capacity.py           # 容量适配专项断言
├── tests/test_gold_queries.py       # 真实数据集冒烟（换数据集后的安全网）
├── tools/gen_assets_registry.py     # 素材清单生成脚本
├── tools/extract_skeletons_from_cards.py  # 卡片 DSL 区划聚类（探索视图）
└── tools/gold_dataset.py            # 输入输出对 → 数据集 + 基准核验
```

**运行方式**（零第三方依赖，Python 3）：

```bash
python tools/debug_pipeline.py "query"  # 单次生成：逐环节 trace + 裸 JSONL（落 runs/debug/）
python tests/run_cases.py         # 9 用例回归
```

### 12.1 接真实模型（config/llm.json）

填 `config/llm.json` 的 `base_url` / `api_key` / `model` 即可切换到真实模型（OpenAI 兼容 Chat Completions 端点）：

```json
{
  "base_url": "https://ark.cn-beijing.volces.com/api/v3",
  "api_key": "你的密钥",
  "model": "模型名",
  "temperature": 0.0,
  "timeout": 30,
  "json_mode": true
}
```

规则：

- **降级策略**：文件缺失、内容非法，或三项必填任一为空 → `build_llm()` 自动返回 MockLLM，任何环境都能跑通；
- `timeout` 为读取超时（强推理模型建议 60~120），`connect_timeout` 为连接超时，两者分离；
- `json_mode=true` 带 `response_format: {"type":"json_object"}`；调用失败重试时自动关闭该字段（`max_retries` 控制重试次数）；
- `extra_payload`（对象）：厂商私有参数透传，合并进请求体。典型用途是关闭思考模式——强推理模型的思维链动辄上万 token（实测 glm-5.3 一个结构规划请求推理 15174 tokens、耗时 262s），会把生成时间拖到分钟级。各模型参数形态不同，需实测：deepseek 系用 `{"thinking": {"type": "disabled"}}`，glm 系该参数 400、仅 `chat_template_kwargs` 部分有效；M1 属枚举级选择任务，建议优先选非思考/快模型；
- 模型输出经 `extract_json()` 解析（剥代码围栏、取首个 JSON 对象）；
- **失败语义区分**：`M1 call fail`（调用层：连接失败/读超时/HTTP 错误，可重试）与 `M1 parse fail`（输出解析失败）；两者都走空计划兜底，任何情况仍产出合法卡片；
- **可观测性**：`logs/llm_calls.jsonl`（每次调用/重试：耗时、错误类型、json_mode、长度）与 `logs/generate.jsonl`（每次请求：query、模型、M1 失败原因、骨架/尺寸/主题、fallback_log、总耗时）；
- 回归测试（`tests/run_cases.py`）固定使用 MockLLM 以保证确定性，真实模型用于联调与指标统计。

## 14. 关键认知备忘

1. **A2UI 是发射器的输出语言，不是模型的思考语言**——v3 把这条推到极致：连中间 DSL 都没有了，程序直接从骨架树模板发射原生协议。
2. **模型输出的"扩展"仍是枚举级**：domain/objects/keep 看似比 v2 多，但全部是"从封闭集合里做选择"，幻觉面没有扩大。
3. **对象数是骨架路由的第一判据**——业务对象先于字段数量；两个独立对象强制 S4/W9，与 CreateMyCard 的四分法/W 路由一致。
4. **容量即几何**：字数口径已被压力宽度预算取代；槽位宽度从骨架 tree 自动提取，规格与实现永不脱节。
5. **发射顺序即兼容性**：root 第一位、父先子后的前序展平，是顺序处理渲染端的兼容前提（官方 map 式解析器则顺序无关）。
6. **协议合规集中在 P6 一处**：组件白名单、事件协议、消息结构、root shell 全部由发射器保证，上游环节零感知。
7. **fallback_log 仍是规则收敛的原料**；MockLLM 下零 fallback 仍是管线正确性的硬性自检。

---

**文档版本：v3.1**（2026-10-15，P6 主题装配独立成步；以下变更记录含 v3 历史）

v3 变更清单（相对 v2）：

1. **骨架体系重写**：2 个抽象槽位骨架 → 14 个带精确几何的固定布局骨架（tree 发射模板 + 路由决策表），路由判据从 intent+条目数改为 size+业务对象数+特征（§6.1/§7.2）；
2. **组件体系重写**：8 个抽象组件 + 字数 copy_spec → 11 个角色（视觉规格 + color_role）+ 压力宽度预算（中文 1em/字母数字 0.65em，hero 降档序列）（§6.2/§7.5）；
3. **主题资产新增**：三套渐变色板 + domain 映射 + 白背板两档 + 设计档位（字号/间距/圆角）代码化（§6 themes/ladders）；
4. **M1 契约扩展**：新增 domain/size/theme/objects/keep，输出仍为枚举级选择（§4）；
5. **P6 重写为原生发射器**：删除"简化格式→方言转换"中间层，树模板直接发射 A2UI v0.9 三行 JSONL；协议对齐 5 处违规修复（Toggle→Checkbox、Button onClick、root shell、styles 嵌套、补 updateDataModel）（§7.6）；
6. **UX 规范对齐清单**（§9）与验收场景机制（§10）新增；
7. **素材资产引入**：resources/base/media 素材库 + assets.json 白名单（槽位接入为演进项）；
8. 输出契约调整：`full-a2ui` 升级为三行原生协议；`a2ui` 降级为调试视图；CardSpec 不做（演进项）。

---

## 15. 待办清单（实验期暂缓）

以下三件事已经论证过，但会改快照或改 49 条的行为，为不干扰论文实验而推迟。每一条都写到"改哪个文件的哪一处、怎么算改完"，避免以后重推一遍。

---

### T1 主题不交给模型

**为什么**

配色是整条链上唯一一个"两种核验都没有"的决策：

- **没有文本可溯**：文本里不存在"蓝色"这条信息，模型给 blue 或 purple 都能自圆其说；
- **没有下游可证伪**：任何色板都结构合法，不溢出、不丢字段，错了看不出来。

对比一下：骨架选错会被容量打回（装不下就丢条目），领域判错会让图标和标题一起错。只有主题错了，下游每一步照常运行。这条静默失败通道不该留在契约里。

**现状（四处）**

| 位置 | 现状 |
|---|---|
| `prompts/step1_structure_plan.md` 第 8 行 | 契约写着 `theme: 可选覆盖（blue / purple / warm），仅用户明确指定配色时输出` |
| 同文件规则 4 后半段 | "其余情况 theme 留空，由程序按 domain 选" |
| `src/normalize.py:56-58` | 只检查 `theme not in ENUMS["theme"]`，合法就放行，**不核对用户到底说没说** |
| `src/theme.py:21 select_theme()` | 三级优先：`m1_user_preference` > `domain_map` > `default(blue)`；前两级在 M1 给了合法值时都会被触发 |

**怎么改（四步）**

1. **删契约**：移除第 8 行的 `theme` 字段说明；规则 4 保留"判断业务领域"，删掉"用户明确要求配色时输出 theme"整段。
2. **删归一化分支**：`normalize.py` 里 `theme` 变量的读取、非法校验、`theme dropped (invalid)` 日志一并移除；返回的 plan 不再含 `theme` 键（下游 `plan.get("theme")` 自然得到 None）。
3. **降优先级**：`registry/themes.json` 的 `selection.priority` 从 `["m1_user_preference","domain_map","default"]` 改为 `["domain_map","default"]`；`theme.py::select_theme()` 删掉第一级分支，签名里的 `m1_theme` 参数也去掉（不留没用的入口）。
4. **补字面抽取（可选，产品需要才做）**：新增 `src/color_request.py`，关键词命中才返回主题 id：深色/暗色/夜间 → `dark`；蓝 → `blue`；紫 → `purple`；暖 → `warm`。**硬约束：命中的词必须出现在 query 原文里**，否则返回 None——这是该模块唯一的可核验条件。

**改完怎么验收**

- 跑 49 条真实 query，M1 原始输出里 grep 不到 `"theme"`；
- 主题分布仍是 blue / warm / purple 三色（这一轮实测 M1 从未给过非常规主题，所以分布应当不变）；
- `snapshot_pipeline` 65 条：**第 4 步不做时应完全无差异**；做了第 4 步则只有"用户明说配色"的探针会变。

**风险**

不做第 4 步，`dark` 不可达（只能靠用户设置）。可接受：生产上主题应来自用户设置，而不是从一句话里猜。

---

### T2 P4 拆两半（暂不做）

**为什么会有这个想法**

13 个角色里，**8 个只看条目类型**（`header_title` / `hero_value` / `status_lead` / `support_line` / `meta_note` / `list_row` / `capsule_action` / `check_action`），**5 个要看落在哪个槽**（`hero_context` = primary 非首条、`zone_value_line` / `zone_aux_line`、`compact_value` = `triple:` 槽、`icon_action` = `bottom_action` 槽）。所以 P4 被 P3 锁住，只能排在装配之后。

**拆法（如果将来要拆）**

```python
# P4a：P1 之后即可执行，只看条目类型
def select_content_roles(entries) -> dict:        # {ref: role}，产出 8 个类型驱动角色

# P4b：P3 之后执行，只做槽位覆盖
def apply_slot_overrides(roles, slot_of) -> dict  # 改 5 个槽位驱动角色
```

**什么时候才值得拆（命中任一即可）**

1. M1 直接输出 `content_role`（让模型判断"这条是不是主值"），此时 P4a 必须独立早跑；
2. 出现第二处消费者需要在 P3 之前读角色（比如文案改写、可访问性检查）；
3. P6/P7 要做"只改颜色、不改角色"的局部重生成。

**验收**：纯重构，`snapshot_pipeline` 65 条必须 diff = 0。

**现在不做的理由**：三个条件一个都没命中。拆完只是多一个中间产物、多一次 dict 拷贝，行为一模一样。

---

### T3 出口修复器

**现状**

- `repair_card` 选项已在 `src/pipeline_options.py` 就位（默认 True），但**没有任何代码读它**——修复动作本身还没写；
- `src/validate.py` 已能给出结构化违规（`code` / `where` / `detail`），修复器所需的"眼睛"已经有了；
- 原型（对应论文 L4）在 49 条上违规恒为 0，所以原型不需要它；它只服务论文的 L1 组（模型全包的 baseline）。

**要做什么**

新增 `src/repair.py`：

```python
def repair_a2ui(text, surface_id, size, max_rounds=2) -> (text, repair_log)
```

动作集与违规 code 的对应：

| 动作 | 针对的问题 | 做法 |
|---|---|---|
| 缩字号 | 真实排版后越界（由 `check_layout` 量出，**不在 validate 的产物里**） | 按 `ladders.json` 的批准档位降一档，不越档 |
| 截断 | 同上 | 设 `maxLines`，超出用省略号 |
| 降档 / 换角色 | 同上 | 主值 30→24→20；仍放不下换 `status_lead` |
| 换组件 | `component.not_allowed` | 白名单外的组件映射到最近的合法组件（Table→List 等） |
| 补壳 | `root.canvas` / `root.shell` | 按尺寸补显式画布、圆角、clip |
| 清引用 | `tree.dangling_child` | 删掉指向不存在 id 的子引用 |

**三条约束（缺一条就不能进论文）**

1. **只改几何与协议，不改语义**：不许删条目、不许改文案。若某动作必须删内容，要记进 `repair_log` 并单独统计——这正是"修补靠删内容消溢出"要暴露的行为。
2. **每轮修完重新校验**：二次违规单独记 `introduced_by_repair`。论文里必须报告"修复引入的新违规数"，否则等于自证清白。
3. **`repair_log` 可解释**：每条写清 `code / where / 动作 / 改前值 / 改后值`，出表时按动作分组统计。

**验收**

- L1 组 49 条：违规率下降，且 `introduced_by_repair` 单独成列；
- 修复触发率 = 有违规的生成占比（论文 §4 的指标）；
- 在原型 L4 上跑：触发率必须为 0，产物与不修时逐字一致（这条同时守住"修复器不影响正常路径"）。

**风险**：修复器可能越修越糟。所以第 2 条约束是硬性的，论文里也必须如实给出"修复引入的新违规"与"修复后反而更差的卡数"。

---

## v3.1 变更记录（2026-10-15：主题装配独立成步）

1. **新增 P6 主题装配**（`src/theme.py`）：整条流水线唯一处理主题的环节——按主题目录选主题（M1 偏好 > domain 映射 > 默认）、解析色板写 `ir["palette"]`、涂装骨架树与条目、挂载对比度校验位；边界纪律：只碰颜色/背景/透明度/图像，不碰布局与内容；
2. **原 P6 顺延为 P7 发射器**：去色板化（不再读取 themes.json），只读着色后 IR（`ir["tree"]`/`ir["palette"]`/具体色值 spec），职责收窄为结构展开 + 协议合规；
3. **`registry/themes.json` 升级为主题目录**：多主题条目（蓝/紫/暖浅色 + 新增中性深色），每条目自带 select 选择规则，加主题 = 加 JSON 条目零代码；
4. **主题参与度收敛**：M1 仅传递用户颜色偏好（语义事实）；P1 保留 theme 枚举校验（海关职责，与 size/intent 同构）；P2/P3/P5 与 P7 零主题知识（P4 仅输出色彩语义角色名，不查色板）；
5. **等价性验证**：重构前后 5 条代表 query（S1/S2/S3/S4/W9）的 full-a2ui 逐字段一致，产物零变化；7 条回归用例全绿。

---

## v3.2 变更记录（2026-10-15：骨架几何对齐 UX-SPEC 校准）

逐骨架对照 UX-SPEC（画布 150×150 / 300×150、安全区、padding、区域规格）全量校验，修正 4 处偏差：

1. **S1**：移除 CardHeader 槽——规范明确 S1"不套 CardHeader"，标题并入居中组（`focus_group` 槽）；P3 相应支持"无 header 槽时标题进 hero 组"；
2. **W3 / W5**：补充规范中的可选标题槽（276×20，`optional`），W3 主区改为"标题 + 主区行（环 92 + 说明列 134）"结构（有标题时主区 103 高）；
3. **W4**：由单一 triple 槽展开为规范结构——可选标题 + 三列 88/96/88 + 两条 Divider 1×64（金标 2x4-V05 佐证：Divider 为主题动作底色 20%，经 P6 divider 语义 token 涂装）；列高 84 对齐金标（值+标签两行预算）；P3 槽位分配支持 `triple:0/1/2` 每列 1 条；
4. **P7 发射器**：支持无子树的叶子组件节点（如 Divider）不再被"空槽省略"逻辑丢弃。

其余 10 个骨架（S2/S3/S4/W1/W2/W6/W7/W8/W9/W10）几何逐项验算与规范一致，无需修改。**骨架数量结论：UX-SPEC 的骨架集合就是 14 个（S1~S4 + W1~W10），规范原文明确"完整卡 15 个 few-shot 不能混为 15 种骨架"，不存在第 15 个骨架；few-shot 中其余差异均为骨架内的内容亚型**（S2 hero 安全盒 106×58、S2 会议时间线日期区 126×16、S2 环形亚型 48×48、S2 对称并列焦点组、S2 标签值列表、W1 var-a 双辅助、icon-round 30 圆形动作、W9 无动作倒计时特例），属 P4 角色规格与发射器内容变体的演进项，不是新骨架。

验证：7 条回归全绿；S1/W4 定向冒烟通过（S1 标题进居中组、W4 标题+三列+双 Divider 零 fallback 且协议合规）；a2ui_core 三场景解析通过。

---

## v3.3 变更记录（2026-10-15：样本值与 zone 行宽度预算）

1. **新增样本值推断**（`src/sample_values.py`）：数据类条目（stat/subtitle/price/discount/deadline/source）的泛化提示（"温度""天气"）按封闭域关键词白名单替换为真实样值（"26°""晴""68%""92千卡"…，对齐 CreateMyCard 的 dataModelSchema.sampleValue 概念）；hint 已含数字（如"26°C"）不替换；替换发生在 P5 文案生成前，文案模板前缀保留，组件 Text 与 updateDataModel 首帧自动同步；更具体的关键词优先（"最高"→31°、"最低"→22° 区分于当前温度 26°）；
2. **zone 行合成补宽度预算**（P7 `_zone_children`）：业务背板两行文字是发射时才合成的（对象名+主值 / 次要信息合并），此前不受 P5 条目级审计约束；现按背板内宽（板宽 − 2×padding）截断，超出带 `…`，内宽从骨架树节点样式实时计算；
3. 截断口径现状：P5 条目级（含 hero 降档）+ P7 zone 合成级两道预算，所有 Text 发射路径均受宽度约束，超宽必带 `…` 截断。

验证：7 条回归全绿；真实模型冒烟（天气卡 Text=26°/晴/31°、updateDataModel 含 22° 最低温；S4 电量卡 zone 行"手机 68%/充电中"）；zone 超长合成行正确截断；a2ui_core 三场景解析通过。

---

## v3.4 变更记录（2026-10-15：按钮规格修正 + 画布尺寸声明 + 尺寸决策强化）

1. **按钮宽度固定**：`capsule_action` 规格补 `width: matchParent`——按钮宽度恒等于所在容器内容区（S2 全宽 126 / S3 双按钮各 126 / W9 板内 114），与金标一致（金标 W9 按钮 width=114），不随文字长短变化，左右与卡片边界等距居中；
2. **按钮文字色修复**：P6 的 `ink_role` 此前被映射到无效键 `ink`（STYLE_KEYS 不含），Button 的 `fontColor` 从未发射、渲染端落默认色；修正为 `ink_role -> fontColor`，实测输出 `#FF1F4799`（主文字色，与金标一致）；背景仍为主题色 20%（`#331F4799`）；
3. **画布尺寸显式声明**：root styles 由 `matchParent` 改为显式 vp 数值（2×2 → 150×150，2×4 → 300×150）——此前 DSL 无任何尺寸信息，渲染端无法区分画布，2×4 产物全部被按正方形渲染（批量验证中 W10/W1 内容错乱的直接根因）；设备端 Form 若需铺满卡片槽位，由端侧按 size 改写回 matchParent（CardSpec 属阶段三范围）；
4. **P2 尺寸决策强化**：业务对象 ≥3 时强制升 2×4（2×2 最多承载 2 对象，硬约束），不再被 M1 的显式 2×2 压制；三对象落入 S4 的"截断对象"fallback 由此消除；
5. **M1 尺寸判断规则**：提示词新增第 6 条——对象数与尺寸的映射（3/4 对象→2x4；2 对象→2x4；单业务含列表/进度→2x4；单业务字段≤3→2x2；同对象字段不得拆对象）；
6. **样本值补充**：剩余天数→"3天"、待办列举（第N件事）→真实事项（提交周报/健身1小时/读书30分钟）。

验证：7 条回归全绿（root 尺寸断言同步升级）；按钮样式实测 width=matchParent + fontColor=#FF1F4799 + bg=#331F4799；三条真实模型 query 的 root 尺寸与骨架 size 全部一致；a2ui_core 三场景解析通过。

**已知项**：单业务三指标卡（睡眠得分类）的真实模型 size 判断与金标偶有分歧（金标 2x4 W1，模型按"单对象3字段"规则出 2x2 S2）——规范明确"few-shot 不表示固定路由"，属模型语义判断噪声；画布声明修复后渲染不再错乱，路由分歧留待指标组语义建模（演进项）。

---

## v3.5 变更记录（2026-10-15：容量适配机制并入方案 + 落地实现）

1. **新增 §8 容量适配机制**（前向枚举 + 首个可行解）：候选边界纪律、7 个原子变换算子（含 guard 与规范依据）、四步候选生成策略、12 个场景模式库（M1~M12）、骨架影响结论与新增骨架四条判据、资产与接口定义；原 §8~§13 顺延为 §9~§14（独立设计文档已并入本章后删除，全项目只维护本文档）；
2. **代码落地**（详见 §8.6）：新增 `registry/layout_variants.json`（候选表）、`src/metrics.py`（度量公共基础）、`src/capacity.py`（容量引擎）；`registry/components.json` 角色补 `min_size` 下限；P4 槽位感知（board 槽位不用 hero 角色）、P5 容量分流（固定槽位交引擎、弹性槽位走宽度预算）、P7 按 `slot_layouts` 发射（stack / 行包裹 / 合并）与背板行组合成；新增 `tests/test_capacity.py`（16 项断言）；
3. **验证**：容量专项 16/16、7 条回归全绿、官方 a2ui_core 三场景解析通过；S3 案例（68% + 充电中 + 双动作）从"38fp 主值与状态行重叠"变为"横排单行、hero 收敛至 24fp"；小背板行字号回到金标 14/700 + 12/400。

---

## v3.6 变更记录（2026-10-15：入口动作链路修复）

批跑产物 `04_fs2x2-2x2-V03` 渲染后两个入口按钮消失，逐环节排查确认为**三处既有缺口被模型计划差异暴露**（非容量引擎回归）：

1. **P1 归一化去重**：M1 把同一入口同时声明为 info 与 action（文案相同，如"每日歌单"）——重复保留会让入口被当信息渲染成纯文本，并多出一个孤立条目。现保留动作、丢弃重复 info 并记 log；
2. **P3 动作→背板语义绑定**：原逻辑按 `bind_to` 字段匹配，匹配不上就把第一个动作塞给 zone:0、其余丢弃 → 入口挂错背板、第二个入口彻底丢失。现按四级优先级匹配（字段 > 文案与业务名互含 > 文案与字段提示互含 > 顺序填空板），每板恰好 1 个 handler；
3. **P7 入口板渲染**：小背板（≤63 高）绑定动作时按"整块点击入口板"渲染（第一行入口名、第二行支撑信息）；对象名前缀在文案已含业务名时不重复（消除"每日歌单 …"式截断）。

**验证**：该条 case 回到金标形态（S3：68%/充电中 横排单行 + 两个 Button，零 fallback）；W10 三业务场景下两个入口分别绑定到各自的业务背板（zone:1/zone:2）且整块可点击；7 条回归与容量专项 16/16 全绿；全量批跑 49/49 成功、协议与尺寸 49/49、**fallback 15 → 10**。

---

## v3.7 变更记录（2026-10-16：真实卡片数据反哺骨架）

**输入**：用户提供的 52 张高质量卡片 DSL（`data/gold/生成卡片的DSL结果/*.jsonl`，全部 2×2，单行 JSON 数组形态）+ 53 份带 `userQuery` 标注的中间产物（`生成卡片的中间环节的输入数据/*_artifact.md`，含 taskspec / cardspec / genui 三段）。新增工具 `tools/extract_skeletons_from_cards.py` 支持 `pairs`（query↔区划拓扑配对，路由规则证据）、`regions`、`tree`、`summary` 四种视图。

1. **新增骨架 2 个**（判据逐条核对见 §8.5 第二层结论）：
   - `S5-primary-support`（数据 M1，9 张）：`header + primary(lw1) + support(lw1)`，无动作；
   - `S6-primary-bottom-action`（数据 M2，13 张）：`header + primary(lw1) + bottom_row(40){bottom_info 78 + bottom_action 40×40}`。
2. **证伪并移除 1 个**：`S7-dual-columns` 曾按区域名（left/right、tomorrow/dayafter、chengdu/shanghai）判为"左右双栏"，复核容器方向后确认前两代命名下的 `left/right` 父容器实为 **Column**，全量扫描 52 张**不存在任何左右并列容器**（唯一等宽 Row 是 S6 底行 78+40）→ 判据 ④ 不成立，从 `skeletons.json` 移除，装配/角色侧的 left/right 分支一并删除。
3. **新增 `action_type: icon_button`**（M1 枚举 + P1 同义词 + P2 特征 `icon_action`）：S2/S6 的**语义完全等价**，唯一差异是入口形态（图文胶囊 vs 40×40 圆钮），数据中由生成器随机选择、无法从 query 推导（q1 与 q25 同为"点一下查看天气详情"，分别走 S2 / S6）。把该差异提升为模型可声明的动作类型，是唯一既能忠实还原两类卡片、又不让程序瞎猜的方案；M1 提示词第 6 条 + 一条 few-shot 给出判定口径（有明确文字动作 → `primary_button`；"点一下去某处"的快捷跳转 → `icon_button`）。
4. **新增角色 `icon_action`**（`components.json`，Stack 40×40 / 圆角 20 / 图标 20×20 居中 / action_bg 底）；P7 增设该角色的发射分支（含 `<id>-glyph` 子节点，图标槽未启用期间以 ≤2 字短标签占位）；角色总数 12 → 13。
5. **P4 槽位感知扩展**：`primary` 首项 hero_value/status_lead、其余 hero_context；`support`/`bottom_info` → zone_aux_line；`bottom_action` → icon_action（原 11 角色表述同步更正在 §6.2）。
6. **P3 主区容量收紧**：`primary` 由"主值 + 单位/状态最多 2 条"改为**只放 1 条主值**——数据中主区恒为单一主值（剩下信息属辅区/底行），避免第二项挤占辅区。
7. **S3 信息组恢复固定内高**：S3 的 `content` 由 `layoutWeight:1` 改回显式 `height:40`（v3.8 按金标精修为 38）。**原因**：内高转 auto 后该槽位被判为 flow、脱离容量引擎，S3 的"68% + 充电中"换轴与超长文本截断两条机制失去载体（`test_capacity` T3/T7 直接报错）。固定内高后两者恢复，且与数据的 40vp 信息组语义一致。
8. **S6 底行辅信息列显式内高 40**：与数据 `L.bottom[Row h40]` 对齐，使该窄列同样受容量引擎管辖（宽度 78 的紧约束下自动走 stack/merged/truncate 链）。
9. **测试基线重建**：`examples/cases.json` 全量补 `expect_skeleton`，新增主用例 8（图标入口 → S6）/ 9（天气主辅 → S5）；`tests/run_cases.py` 增加"骨架正确率"指标。**该断言即为本次回归的报警器**——S6 初版路由条件（单动作 ∧ hero ∧ info≥3）过松，把促销类卡片（"立即购买"文字按钮）误路由进 S6 并触发容量降级，指针为 4/6 零 fallback。
10. **验收脚本扩容**：`verify_a2ui_render.py` 加入 S6/S5 两条 query，5 条 query 全部通过官方 a2ui_core MessageProcessor（surface 建立 + 组件树引用闭合）。
11. **文档**：UX-SPEC 增量区 §11.1（骨架补充表 + S5/S6 区域规格）、§11.2（icons/ 目录落地）、§11.3（动作形态、M7 信息组、数据侧新样式键）、§12 变更记录；本方案 §6.1/§6.2/§7.2/§8.5/§11 同步。

**验证**：主用例 8/8（意图 / 骨架 / 零 fallback / 协议全绿）、容量专项 16/16、官方 a2ui_core 5/5 解析闭合、全量 49 条 MockLLM 扫描协议 49/49 且 fallback 20 → 19（骨架分布由 S2×34 变为 S2×21 + S5×11 + S6×2）。

**已知边界**：① `capacity: header [single_line] -> truncate` 是长标题（>12 字）的既有降级路径，非本次引入，随标题长度出现；② `row`（换轴）候选目前仅由 S3 的 40vp 信息组承载——数据对齐后其余信息槽要么是弹性区、要么是 78/110 宽的小背板，机制保留待新骨架接入；③ 图标入口的**真实图标槽未启用**，`icon_action` 暂以短标签占位，属 §4 图标槽演进项。

---

## v3.8 变更记录（2026-10-16：真实输入输出对 → 数据集与基准）

**输入**：`生成卡片的中间环节的输入数据/qN_artifact.md`（52 份，每份 = 一次完整流水线记录，10 个代码块）+ `生成卡片的DSL结果/qN.jsonl`（最终产物）。二者是**人工校验过的真实输入输出对**（qN 一一对应）。

1. **配对关系核实（重要事实）**：`artifact.genui` 与 `qN.jsonl` **内容等价**，唯一差异是 root 的 `width/height`——前者为 `matchParent`，后者已被解析为 **显式 150×150**。即 `.jsonl` = 端侧解析后的终态，`genui` = 解析前。这印证了 v3.4"画布尺寸显式声明"与真实产物的终态一致（设备端解析步骤在我们的方案里由端侧承担）。
2. **新增 `tools/gold_dataset.py`**（构建 + 核验两个模式）：
   - 产出 `examples/batch/batch_queries.json`（**52 条真实 userQuery**，`source=artifact:CreateMyCard`，带 `size` 金标；该文件早期版本是模型自编 query，已归档为 `batch_queries.legacy_model_invented.json`）；
   - 产出 `examples/gold_pairs.json`（数据集：query / 尺寸 / 标题 / 描述 / 数据能力 / 事件 / **数据模型 169 个叶的路径·类型·sampleValue·说明** / 金标结构轮廓）；
   - `check` 模式做**金标结构核验**：把每张卡的纯结构事实映射到本项目骨架，并对照关键几何。
3. **金标骨架分布（本项目骨架对真实数据的覆盖度）**：S2×21、S6×13、S5×10、S3×3、S4×2——**49/49 全部可归属现有 16 骨架，零未归类**（`check` 通过）。这是"骨架集合够不够用"的量化答案。
4. **由金标修正的代码/资产**：
   - S3：信息组内高 40 → **38**、双胶囊总高 78 → **80**、胶囊间距 6 → **8**（真实数据 q44/q46/q48；规范正本 §6 写"间距 6"，以数据为准，差异已在 UX-SPEC §11.3 留痕）；
   - `src/sample_values.py`：关键词表的取值**全部换成本数据集的真实 sampleValue**（气温 29°、天气 多云、电量 68%、步数 6200、距离 4.60 公里、睡眠 7小时1分、得分 82分、倒计时 30天、日程 项目例会/会议室/14:00、耳机 示例耳机…），并新增 40+ 条封闭域词条；同时明确**与金标的约定差异**（金标把数值与单位分开，本项目暂无独立单位角色，故表中给可显示文本，待单位角色落地后改两段式）。
5. **换数据集的安全网（防"裸奔"）**：`tests/run_cases.py`（8 主用例，MockLLM 确定性回归）与 `tests/test_capacity.py`（16 项）**未改**，仍是语义/容量回归基线；新增 `tests/test_gold_queries.py` 断言"52 条真实 query × MockLLM 零异常、零协议违规、数据集自洽"（**不断言语义词数**——MockLLM 是封闭域桩模型，对真实 query 语义必然不匹配，24 条 fallback 均来自桩模型造出的 12 字长标题被 header 截断，属预期）。
6. **数据中可抽取但本期未用的内容（已记入数据集，留给后续）**：`request.content` 的完整上游入参（bundleName/deviceInfo/session/utterance/title/description/candidateAssetIds）、`generationPlan` 的候选绑定、`meta.createdAt`（可用于排序/时间线）、`designcompactdsl`（其缩略 DSL——**属该工程技术方案，本项目不参考**）。另注意：**金标的 header 文案绑定的是数据字段**（如 `/data/weather/location/districtName`），而非 `cardspec.title`；本项目 header 文案来自 query 抽取，属已知差异。

**验证**：`run_cases` 8/8（意图/骨架/零 fallback/协议）、`test_capacity` 16/16、`test_gold_queries` 6/6、`gold_dataset check` 49/49 结构一致、官方 a2ui_core 5/5 解析闭合。

---

## v3.9 变更记录（2026-10-16：首轮实机渲染核对驱动的修正）

**输入**：用户手工渲染 v3.8 那批 52 张真实 query 产物，与金标逐张比对，提出三条具体问题（q1 底部按钮、q9/q10 分区文字对齐、q20 最严重）。**结论：三条全部是"我们违反了自己的规范/金标"，规范原文完全支持用户判断**——§8 验收清单「小背板文字左对齐、图标在右并垂直居中」、§8「文本左对齐，图标占独立右槽」、§5.3「S2 单按钮 x12 / y102 / width126 / height36」、§2「默认文本靠左」。

1. **小背板文字左对齐（q9/q10）**：S4/W1-aux/W5-aux/W8/W10 右板此前声明 `alignItems: center`（文字水平居中），与规范 §8 及金标（q10/q34 的 `alignItems: start` + `justifyContent: center`）都不符 → 13 处槽位统一改为**左对齐 + 整组垂直居中**。
2. **底部按钮（q1）**：核对后确认**胶囊逻辑本身是对的**（`width: matchParent` + 动作区 126，实测 q32 正确）；q1 的真实根因是**路由**——它被 M1 声明成 `icon_button`，走 S6 渲染成 40×40 圆钮并靠左。修法：M1 提示词规则 6 改为**默认 `primary_button`**，只有用户明确要"图标/圆钮快捷入口"才用 icon_button（依据：用户期望 + 金标 S2 21 : S6 13）。同时 S6 的底行补 `justifyContent: spaceBetween`（辅信息左 / 圆钮右，同金标 q3）。
3. **标签值行（q20，问题最大）**：金标 **34/52 张**的内容区是「一行一个对象：左标签、右数值」，我们此前渲染成"一条目一行纯文本"，叠加 q20 的样本值 bug（下条）与路由放大，才出现"卡片内嵌套一个几乎同大的区域、只有一行字、下面空白"。修法：新增 P7 `_label_value_rows`（`Row(h18, spaceBetween){对象名 12/400 meta色, 值 12/400 primary色 + textAlign=end + layoutWeight=1}`，整列沉底，同金标 q20 的 `justifyContent=end`）+ P2 特征 `label_value_list`（多对象 × 单值）+ `examples/cases.json` #10 常驻断言。
4. **样本值 bug（q20 显示"手机 30天"）**：`src/sample_values.py` 依赖"更具体的词排在前面"的隐式约定，`剩余` 排在 `剩余电` 之前 → "剩余电量" 被映射成"30天"。**改为最长关键词匹配（顺序无关）**，此类 bug 不再可能出现；并新增 `tests/test_gold_queries.py` 的"真实字段名 → 预期值"断言（9 条）。
5. **路由去对象数化**：2×2 路由改为**形态优先**——S4 要求「恰好两个同构多字段对象且无动作」，`n_obj≥2 → S4` 与 `n_obj≥3 → 强制 2×4` 全部取消（金标 52/52 全 2×2，S4 仅 2 张）。此前 11 张被劫持成 S4、3 张被放大到 2×4（q48 双动作卡也被劫持）。
6. **hero 阈值改宽度口径**：新增共享常量 `HERO_MAX_CHARS = 4`（38fp 下 126 宽最多约 3 个中文字），`component_select` / `skeletons` / `assemble` 三处统一；并在**文案生成之后**复核（样本值会让文案变长："天气预警"→"大风蓝色预警"）→ hero 降档后仍被截断的 7 张卡清零。
7. **覆盖率高噪声修正**：无标题区骨架（S3/S4）不再把标题记为"未安置失败"（金标这几类卡本身没有标题）；"必保条目超槽位容量"改为降级措辞（金标 q49 问 4 个值也只展示 3 行）。

**验证（改造前后对比，同一批 52 条真实 query × 真实模型）**：

| 指标 | 改造前 | 改造后 |
|---|---|---|
| 骨架与金标一致 | 21/52 | **30~31/52** |
| 尺寸与金标一致 | 49/52 | **52/52** |
| 骨架+尺寸一致且零 fallback | 16/52 | **25~27/52** |
| 带 fallback 的卡 | 16 | **7~9** |

> 改造后为同一份代码连跑两次的区间：端点 temperature=0 但仍非完全确定（模型侧的措辞/切分偶有波动，骨架归属随之 ±1）。比较改动效果时用区间下界。
| 回归（run_cases / test_capacity / test_gold_queries） | 8-16-6 | **9/9 主用例 + 标签值行 1/1 / 16/16 / 7/7** |

**剩余已知分歧（未修，待裁决）**：① `S6 → S2` 9 张 —— 入口形态是**语义等价的形态二选一**，数据侧由生成器随机选择（同为"点一下查看详情"的 q1 走 S2、q3 走 S6），当前默认偏 S2（符合用户对 q1 的期望），如需更像金标需反向调；② `S2 ↔ S5`（6 张）无动作卡的单内容区 vs 主辅二分，同样是形态二选一，缺可靠判据；③ `S5 → S1/S4`（4 张）来自 M1 对"业务对象"的切分方式；④ 3 张必保条目超内容区容量（金标同样只展示前 N 条，属降级）。

---

## v3.10 变更记录（2026-10-16：逐卡元素级比对循环，6 轮）

**方法**：把 q1~q52 的真实 query 逐条发给真实模型跑完整流水线，再用新工具 `tools/diff_gold.py` 与金标做**元素级**比对（画布/padding/itemMargin、容器构成、字号字重多重集、对齐多重集、固定高度、可点组件形态、标签行数、图标数、进度环数），差异**聚类后按卡数排序**逐项追根因、改代码/骨架/资产/规范，再重跑验证。共 6 轮。

| 指标（同批 52 张真实 query） | 起点（v3.9） | 终点（v3.10） |
|---|---|---|
| 骨架与金标一致 | 21/52 | **约 32/52** |
| 尺寸与金标一致 | 49/52 | **52/52** |
| 骨架+尺寸+零 fallback | 16/52 | **约 29/52** |
| 带 fallback 的卡 | 16 | **5** |
| 图标缺失（n_image 差异卡数） | 48 | **6** |
| 可点组件形态差异（clicks） | 26 | **12** |

**修正清单（6 轮）**：① 主值两档制（数值 30/700 / 文本 18/700，降档序列截到 30，定档在文案替换之后，唯一数值候选才提升）；② 图标槽接入（新资产 `registry/icons.json`：域→标题图标、动作关键词→动作图标）；③ 胶囊改回金标 `Row+onClick` 形态（装得下 20×20 图标）；④ 小背板 16/700 + 左右 padding（内宽 110/内高 63）；⑤ 标签与值分离（label 来自 M1 字段名，行渲染条目驱动，单条目/主值不做行）；⑥ M1 契约强化（逐字段成条、写字段名不写值）；⑦ S1 条件收紧（防丢项）；⑧ S5/S6 加 body 包装层（root 6 + body 8）；⑨ S2 内容区顶部对齐、标题区 spaceBetween；⑩ 新增 `tools/diff_gold.py` 与 `examples/batch/gold_vs_run.md`（对比表）+ `examples/batch/runs/` 逐卡产物。

**判定为"声明密度差异、不追"的一类**：`n_container`（金标多 1~2 层无样式 wrapper）、`heights`（金标给每个 Text/行都显式声明高度）、`textalign`（金标显式写 start）。这三类不影响渲染结果，只反映两侧生成器的风格差异。

**剩余已知分歧（未修）**：① `S2↔S6`（约 12 张）与 `S2↔S5`（约 6 张）——**语义等价的形态二选一**，数据侧由生成器随机选择，无可靠判据（当前的默认值偏向用户期望的一侧）；② 进度环（q19/q32，2 张）：金标是 `Stack 52×52 > [Progress 52×52, Image 20]`，我们尚无 Progress（M1 的 progress 特征恒 false）；③ 小背板第二行/标签行字号：金标用 10fp，规范 §2 明文禁止 → 保留 12。

---

## v3.11 变更记录（2026-10-19：环形主值 / 可视化验收工具）

1. **新增可视化验收工具 `viz/gen_card_compare.py`**：把金标与本次批跑**逐卡并排**渲染成自包含 HTML（`viz/card_compare.html`，2× 缩放、图标内联着色、可切换"只看不一致"）。它按 A2UI 的 `styles` 忠实落 CSS（width/height/padding/itemMargin→gap/layoutWeight→flex/alignItems/justifyContent/linearGradient/borderRadius/clip），并把 `{{ ${/data/...} }}` 解析成真实样本值。**这是"肉眼验收"的固定入口**，此前只能整块复制 JSONL 到外部渲染器。用它反查出两处渲染口径问题并修正：① 协议色值是 ArkUI 的 **#AARRGGBB**（alpha 在前），直接当 CSS 八位色会把 alpha 当蓝通道 → 文字/底色全错；② `Stack` 叠层必须让所有子节点 `grid-area:1/1` 同格覆盖，否则后续子节点落到隐式行被裁掉。
2. **环形主值（金标 q19/q32）**：内容区改为 `Row(h52, im8, 居中){ Stack(52×52){Progress(ring, strokeWidth 6), Image(20)}, Column(h52){标签 14/700, 值, 状态} }`。**属槽内形态、不新增骨架**（区划仍是 header+content+action = S2）。触发条件严格：`content` 槽恰有 1 个 `percent` 条目且条目总数 ≤2，避免误伤多对象清单。
3. **`percent` 类型由 P1 确定性判定**：模型对"电量"时而给 `stat` 时而给 `percent`（同一句 query 两次结果不同），因此不依赖模型枚举——`stat` 且字段名含「电量/百分比/完成度/使用率/占比/进度/充满/剩余电」即纠正为 `percent`（`normalize.PERCENT_KW`）。同时 `percent` 纳入 `DATA_TYPES`（否则样本值替换不生效，环里会显示字段名而不是数值）。
4. **验证**（同批 52 条真实 query × 真实模型，`runs/20261019_144403`）：骨架一致 **32/52**、尺寸一致 **52/52**、骨架+尺寸+零 fallback **28/52**、带 fallback **7**、协议违规 **0**；回归 `run_cases` 9/9（含骨架/标签值行）、`test_capacity` 16/16、`test_gold_queries` 7/7、金标结构核验 52/52；环形产物均通过 `check_full_a2ui`。

**遗留（下一轮靶点，全部来自肉眼验收）**：① **M1 抽取质量**是当前最大瓶颈——q06 把首个事件的标题与时间重复抽取（标题=产品立项会、内容又是 14:00/客户交流会/14:00）；q04 多抽了"预警等级/预警发布时间"两行且值被截断成"大风蓝色预…"；q05 把"温度范围"这个标签丢了只留数值。这些都属抽取契约而非布局。② `S2↔S6`/`S2↔S5` 形态二选一（语义等价，数据随机，不猜）。③ 环形的**默认值**仍是不启用（与数据分布一致），要更像金标需另定策略。

---

## v3.12 变更记录（2026-10-19：进度环参数化 + 内容区排法表化）

**背景**：进度环此前把判断条件和 8 个几何数字都写死在 `compiler._ring_row` 里；而 `_fill_children` 里"容量行 / 环 / 标签值行 / 一条一段"四个分支靠书写顺序决定优先级。要加第五种排法时说不清该插在哪，也不知道会不会抢走别的卡。

1. **方案1 参数化**：新增资产 `registry/content_forms.json`，环的 `ring/strokeWidth/icon/rowHeight/iconGap/lineGap`、标签与数值的字号行高、以及三个配色角色全部写进 `spec`。改外观只改 JSON。
2. **方案2 排法表化**：内容类槽位（`content`/`primary`/`support`/`bottom_info`）改为**按 `order` 查表分派**，取第一个满足 `when` 的排法；拼装实现搬进 `src/forms.py`（`_capacity_rows` / `_ring_stat` / `_label_rows` / `_plain_items`）。`_fill_children` 收缩为一行 `forms.emit(...)`。
3. **边界（刻意不扩大范围）**：`header`/`action`/`action_zone`/`bottom_action` 是"条目类型 → 组件"的一对一映射，不进表；`zone:`/`aux:` 背板的"放不下怎么缩"是试算，继续走 `layout_variants.json`。**表只解决"选哪种排法"，不解决"放不下怎么算"**——后者写进表就会退化成自造 DSL。
4. **优先级显式化**：`capacity_rows` 用 `order: 0` + `when: {has_layout_rows: true}` 表达"容量引擎已给出逐行决策"，把原来的代码书写顺序搬成数据里的一行；行为不变，但以后调顺序只改数字。
5. **防回退**：`tests/test_forms.py` 五项守卫（表↔实现一一对应、最后一条必须无条件兜底、`when` 键必须在白名单内、`order` 唯一递增、环的几何确实来自 `spec` 且改 JSON 立即生效）。

**验证**：新增 `tools/snapshot_pipeline.py`（确定性桩模型跑 65 条 = 10 用例 + 52 条真实 query + 3 条排法探针，逐条比对 `full-a2ui`）。**方案1 与方案2 各自 diff = 0**（首次比对全红，原因是 `surfaceId` 每次随机，已加入归一化）。回归：`run_cases` 9/9、`test_capacity` 16/16、`test_gold_queries` 7/7、`test_paths` 9/9、`test_forms` 8/8。真实模型批跑 52/52 成功、协议 0 违规、q19/q32 仍出环（骨架一致 30/52，与上一轮 32/52 的差异全部落在已知的 `S2↔S6`/`S2↔S5`/`S5↔S4` 语义等价类，属模型抽样波动，非本次改动引入）。

---

## v3.13 变更记录（2026-10-19：实机核对三处问题 + 布局体检工具）

用户手工核对本轮产物，指出三处：q03 期望圆钮、q12 图标跑到左上角、q13 内容溢出卡片，并追问"对比工具为什么没发现"。逐条结论：

1. **q03（不是 bug，是随机形态）**：S6 + `icon_button` 我们支持且渲染正确。但金标里 **q01（S2，胶囊）与 q25（S6，圆钮）同为"城市天气 + 点一下查看天气详情"**，q28/q42 也分属两态——同一业务域、同一动作措辞，两种形态并存，**没有可推导的判据**。当前默认 `primary_button` 是按用户对 q01 的反馈定的；M1 仍可在用户说"圆钮/图标入口"时声明 `icon_button`。若要统一风格，应做成产品级配置项（`action_style: capsule|icon`），而不是让程序猜。
2. **q12（真 bug，已修）**：不是图标位置错，而是 M1 没抽出标题 → 标题区只剩一个子节点 → `spaceBetween` 把唯一子节点排到最左。修法：标题区只有图标时 `justifyContent: end`。
3. **q13（真 bug，已修）**：content 槽 3 条都有标签，本应走「标签值行」（3×18 + 间距 4 = 58 = 可用高度），但**主值提升**把 80% 提成 30fp 大字，既放不下、又因 `no_promoted_hero` 挡掉行布局，退回「一条一段」→ 24+24+36+4 = 88 > 58，把底部按钮顶出卡外 10px。修法：**主值提升仅在该槽体条目 ≤2 时生效**。
4. **配套修宽度截断**：标签值行（标签优先、值按剩余宽度语义截断、≤4px 容差）、环内标签、标题区，都改为按可用宽度预截断，不再依赖 CSS 省略号在边界硬裁。
5. **工具升级 `tools/check_layout.py`**：此前 `diff_gold.py` 比的是**声明**（字号/对齐多重集/组件构成），抓不到"声明没问题但排出来溢出"。新工具把卡片真正排版后测量每个文字框的 `getBoundingClientRect` 与 `scrollWidth`，直接回答越界与裁切；用金标校准（金标 0 越界）。另在对比页渲染器上加 `data-cid` 便于定位。

**结果（同一批 52 条真实 query）**：越界 **4 → 0**、明显裁切（>4px）**13 → 0**、边缘裁切（2~4px）**4 处**（金标同类 2 处）。骨架一致 31/52、尺寸 52/52、骨架+尺寸+零 fallback 27/52、fallback 7、协议 0 违规。回归 9/9 + 16/16 + 7/7 + 路径 9/9 + 排法表 8/8 + 金标核验 52/52。

**未修（下一轮靶点）**：M1 抽出的标题常是整句（q03「下一场日程是18天后上午十点的产品发布会」→ 截断成「下一场日程是1…」），而金标标题是对象名（「产品发布会」）。这是抽取契约问题（提示词要求标题 ≤8 字、取对象名），会同时改善 q03/q06 等多张卡的观感。

---

## v3.14 变更记录（2026-10-19：标题兜底）

**问题**：q11/q47 只有右上角图标、没有标题。用户指出"一般情况下卡片左上角都有标题，右上角有图标时更是必须有标题"，且这是共性问题。

**根因**：我们的标题只来自 M1 抽取的 `title` 条目；金标的标题来自数据绑定，永远存在。M1 漏抽（query 里明明写着"电池温度卡片"）时标题区就只剩图标，`spaceBetween` 又把唯一子节点排到最左（q12 曾因此让图标跑到左上角）。

**修法**：`src/slot_assign.py` 新增 `_ensure_title`，在**骨架路由之后**执行——有标题区但没有 title 条目时，用第一个业务对象名补（`电池`），否则按业务域给中性名（天气/电量/耳机/日程/会议/倒计时/健康/提醒/优惠）。

**关键坑**：首版放在 P1 归一化里，补标题改变了"信息条数"（title 计入 `n_info`），2 条内容的卡变成 3 条 → 路由改判 S5，**q32 的环卡因此丢掉环**。快照比对立刻暴露（4 张卡骨架变了）。挪到 P3 后骨架零变化，只剩"新增一个标题节点"。

**验证（单点，不跑全量）**：q11/q47 补出「电池」、`justifyContent: spaceBetween`（标题左、图标右）、布局体检无问题；q32 骨架与环保持不变。确定性快照 65 条中 6 条变化，逐条确认差异仅为新增标题节点。回归 `run_cases` 9/9、`test_capacity` 16/16。

---

## v3.15 变更记录（2026-10-19：修"显示字段参与路由"这一类隐患）

**触发**：用户追问"你那次把标题兜底放在 P1 导致改判骨架，是基本错误，这类错误还有吗？"

**审计方法（可复用）**：对 54 条计划做**对照实验**——先取 P1 输出的规范化计划，再人为"去掉标题条目并清理 objects 里的悬挂引用"，重算 `select_skeleton`，比较前后骨架。

**审计结论（修复前）**：
1. **9/54 条**会因"标题有无"改变骨架 —— 标题被计入 `n_info`；
2. **4 条**会因 `stat→percent` 转换改变 `hero`（percent 不在 `HERO_TYPES`），从而掉进 S1（居中单焦点）并**丢掉环**；
3. 第三处接近踩坑但被挡住了：`slot_assign` 会把标题放进 S1 的 hero 组，但合成标题只在"有 header 槽"时才补，S1 无 header，故不受影响。

**修法**：
- `n_info` 改为**只数非标题条目**（标题是显示字段，可缺可补，不该影响布局决策）；
- `HERO_TYPES` 显式注释"不含 percent"的原因（环画在 S2 content 槽，percent 当 hero 会让单百分比卡进 S1 并丢环）；
- 新增 `tests/test_routing_stability.py`：4 项断言把这条不变量钉死（标题有无不改变骨架、percent 不属于 HERO_TYPES、纯百分比计划不算 hero、单百分比卡不进 S1）。

**结果**：审计从 9 条变为 **0 条**；确定性快照 65 条无变化（因为桩模型计划总带标题、且此前标题在路由后才补）；真实模型 52 条：骨架一致 **31 → 29/52**、尺寸 52/52、完全一致 26/52、fallback 6、布局体检 0 越界 0 明显裁切。

**代价（需知悉）**：金标骨架一致掉了 2 张，集中在"金标 S5、我们 S2"的 3 张。原因是**金标自身不一致**——同样是"标题 + 2 条内容"的卡，金标既有 S5（q11）也有 S2（q32 环卡）。纯计数规则无法同时命中两者；本轮选择保住"路由不受显示字段影响"和"环卡不丢环"，牺牲 2 张指标。若更看重指标，可回退 `n_info` 但需接受上述隐患。

---

## v3.16 变更记录（2026-10-19：以「明显问题」为判据，修值错误）

**触发**：用户指出 **「金标也不一定是完美，需要持续迭代。关键看有没有明显的问题。」** 这句话纠正了评审标尺——此前我按"与金标的元素级差异"排优先级，容易在无关紧要的个位数差异上耗时间，却漏掉"卡面显示了错的值"这类真问题。

### 1. 新增判据：明显问题三级（已写入 UX-SPEC §11.4）

| 级别 | 内容 | 处置 |
|---|---|---|
| **一级：明显问题** | 信息错误（值错/同卡重复值）、内容越界或被裁、用户点名要的字段整条丢失、卡片空白只剩孤立标签、有标题区却缺标题 | **必须修**，与金标是否也这样无关 |
| 二级：风格差异 | 字号/间距差 1~2 档、形态二选一（胶囊 vs 圆钮、S2/S5/S6）、金标自身违规（10fp、轻微越界） | 不修，除非用户要求 |
| 三级：指标 | 骨架一致率、尺寸一致率、元素级差异卡数 | **只作趋势参考，不得为它牺牲一级** |

判定顺序固定为：`check_layout.py`（布局）→ 值正确性 → `mustKeep` 覆盖 → 最后才看金标一致率。

### 2. 按此判据查出的真问题（全部与金标无关，纯看卡面就能判定）

| 现象 | 根因 | 修法 |
|---|---|---|
| **q20 两个 68%**（手机与耳机仓同值） | M1 把两个对象的同类字段抽成同一 hint（都叫"剩余电量"）→ 标签重复 → 样本值按同一标签推断，值跟着重复 | `assemble._compose_label`：同卡标签重复时用「对象名 + 字段核心词」（`手机电量`/`耳机仓电量`/`耳机连接`，与金标一致）；仅在重复时生效 |
| **q24「会议发起人」→「项目例会」**（应为李四）、`是否重要日程`→项目例会 | `infer_sample` 的包含匹配过宽："会议发起人"含"会议"、"是否重要日程"含"日程"，被活动名抢走 | ① 匹配收紧为「整词 > 前缀/后缀 > 中间包含（且重合度 > 50%）」；② 复合字段名整词入表（`会议发起人`/`是否重要日程`/`提前提醒时间`/`预警类型`/`预警等级`/`预警发布时间`/`睡眠质量`/`白天补觉`/`左耳机电量`…） |
| **q36「睡眠质量」→「7小时1分」**（应为良好） | 同上，"睡眠质量"被前缀"睡眠"（时长）抢走 | 同上 |
| **q04 两行都是「大风蓝色预警」** | 预警"类型"与"等级"两个字段共用一个整词样本值 | 拆成 `预警类型→大风`、`预警等级→蓝色` |
| **q09 左右耳都是 68%**（金标 76%/78%） | "左耳机电量"被后缀"电量"(68%) 抢走 | 补整词 `左耳机电量→76%`、`右耳机电量→78%` |
| **q06「开始时间」不显示值** | `_compose_label` 拼接超长时退化为对象名（"产品立项会开始时间" 9 字 > 7 → 返回 "产品立项会"），推断拿对象名查表失败 | `infer_sample(hint_name) or infer_sample(e["hint"])`：去重标签失败时回退原字段名 |

### 3. 验证

- 单点（用户要求的方式，不跑全量）：q04/q06/q09/q20/q24/q36 逐张生成 + `check_layout` 量该卡 → 全部「体检 OK」，卡面文字逐条核对通过（q24 变为 李四/是/15分钟；q36 变为 良好/0分；q20 变为 68%/80%）。
- 确定性快照 65 条：**完全一致**（这批改动只影响真实模型抽到那些复合字段名的卡，桩模型路径零变化）。
- 回归：`run_cases` 9/9、`test_capacity` 16/16、`test_gold_queries` 7/7、`test_forms`/`test_paths`/`test_routing_stability` 全绿。
- 全量 52 条：**布局 0 越界、0 明显裁切**、3 处 2~4px 边缘裁切（金标同类 2 处）。

### 4. 这一轮刻意没做的

- **没有为了提升骨架一致率而放宽任何规则**。金标自身不一致（同类卡 S2/S5/S6 混用、同一句话两种入口形态），追平它没有意义。
- **没有改 M1 提示词**（q06 的"会议标题"、q29 的标题取成对象名属抽取质量，等值错误清完后再评估是否需要提示词微调）。
- **没有把"用户问 4 个字段、卡面只显示 3 个"当 bug**：2×2 的 content 区物理上只放得下 3 行标签值（54vp / 18vp），金标 q47 同样只显示 2 行。这是容量上限，按优先级丢弃是正确降级——但"丢了最前面的"或"明明有空位却丢"仍属一级问题。

## v3.17 变更记录（2026-10-26：职责划分补总图 §7.0）

### 1. 新增 §7.0 职责划分：五层与三类

给 §7.1~§7.7 补一张总图，解决此前讨论中反复出现的三类混淆：

- **五层（实现视角）**：语义（M1+P1）→ 结构（P2+P3）→ 样式规格（P4）→ 几何（P5）→ 外观与输出（P6+P7）。判据是"这一步的数字来自模板常量、查表，还是真实测量"。**只有 P5 一格含真实测量**。
- **三类（论文视角）**：可交决策（P2+P3 结构）、查表类（P4/P6/P7，交出去无收益）、不可交（P5 几何）。据此确定论文实验只讨论结构权，其余固定给程序。
- **P1 拆两半**：翻译（同义词/ref 重排）不改内容集合；修复（丢条目/去重/stat→percent/悬空引用）改内容集合。做"无保障"对照必须能单独关掉后半部分。

### 2. 修正两处文档与实现不一致

- §7.2 原写"仅 objects ≥3 时升 2×4"与实现不符（该规则已于 2026-10-16 取消）：改为"用户显式指定优先，否则一律 2×2，对象数不放大画布"。
- §7.2 原写"主题选择：M1 显式 theme > domain 映射 > 默认 blue"，把 P6 的职责写进了 P2。已改为指向 §7.6，并声明"P2 不读 theme、不因主题改变骨架"。

### 3. 未改动的部分

代码零改动。本轮只补叙述与更正文档，`snapshot_pipeline` 快照不受影响。

### 4. 论文实验方案另立文件

五档阶梯（L1~L5）属论文实验，不属于原型实现路径，已分离到 `../../paper/方案/论文实验方案.md`。

## v3.18 变更记录（2026-10-26：运行选项 + 校验器进主干）

### 1. 新增 `src/pipeline_options.py`

三个布尔选项（`repair_plan` / `repair_card` / `placeholder_card`），默认全开，环境变量前缀 `CARDGEN_`；也可由 `generate(..., options=...)` 显式传入。`PipelineOptions` 冻结，避免流水线中途被改。

### 2. P1 的四条“改内容”规则改为可关

去重、stat→percent、悬空关系清洗、未归属字段并入首对象——受 `repair_plan` 控制。**非法枚举回退与非法类型丢弃不动**：那是解析（数据不可解释，程序必须拒绝），不是修正。

### 3. 空计划兜底改为可关

`placeholder_card=False` 时返回 `meta.failed = True`、`ir = None`，不再塞占位卡。实验模式下失败必须暴露。

### 4. 校验器迁入 `src/validate.py`

原 `tests/run_cases.py:check_full_a2ui` 的 55 行规则改为 `validate_a2ui()`，输出结构化违规（`code / where / detail / severity`），`run_cases` 只保留一层字符串适配。出口修正与评测从此共用同一份规则。流水线末尾调用，违规写入 `meta.violations` 与请求日志。

### 5. 验证

- 新增 `tests/test_pipeline_options.py`（9 项：四条修正的开关行为、兜底开关、meta 透出、环境变量容错）
- 新增 `tests/test_validate.py`（12 项：每个用例只破坏一处，断言恰好报出那类 code）
- 回归：`run_cases` 9/9、`test_capacity` 16/16、`test_gold_queries` 7/7、`test_forms` / `test_paths` / `test_routing_stability` 全绿
- 快照：改动前后各跑 65 条，`diff` **完全一致**（默认值下行为未变）

### 6. 恢复被误删的 `examples/cases.json`

该文件在 `dd76ff6 add docs` 里被删除，导致 `run_cases` 一直报 FileNotFoundError（9 用例基线名存实亡）。已按 `HEAD^` 还原，9/9 复跑通过。

### 7. §15 待办清单

T1 主题不交给模型（实验后执行）、T2 P4 拆两半（暂不做）、T3 出口修复器（原型不做）。每条都写明了为什么要做、现状在哪几个文件、改法、验收标准与风险。

## v3.19 变更记录（2026-10-26：度量层落地）

### 1. 模型客户端开始记成本（`src/llm.py`）

`LLMClient` 增加四项统计：`calls`（成功调用次数）、`attempts`（含重试的请求次数）、`usage`（in/out token）、`usage_missing`。端点不返回 usage 时**不估算**，如实记 None——编出来的 token 数会让成本对比失去意义。`stats_delta()` 取两次快照的差，得到"一次生成用了多少"。

### 2. 流水线开始记分阶段耗时与成本（`src/pipeline.py`）

`meta.timing` = 模型 / 装配 / 校验 / 总时长，四项分别计时；`meta.cost` = 本次调用的次数与 token。写进 `meta` 与 `logs/generate.jsonl`。耗时用 `perf_counter`，`duration_ms` 保留以兼容旧日志。

### 3. 新增 `src/measure.py`：一行一条记录

`build_record()` 把一次生成拍成固定字段（协议违规 / 计时 / 成本 / 骨架 / 指纹 / 卡面文字 / 静态指标），`fingerprint()` 先抹平随机 surfaceId 再取哈希，用于"重采样是否逐字相同"。

### 4. 新增五个实验工具（`tools/`）

`build_content_oracle.py`（金标 → 应有事实集，52 卡 135 条）、`measure_content.py`（覆盖/保真/重复）、`measure_geometry.py`（批量渲染测越界与裁切）、`resample_stability.py`（重采样算字段全一致率）、`build_metrics_report.py`（条件 × 指标汇总表），以及串联用的 `run_condition.py`。

### 5. 内容指标的三个口径细节

- **双向包含**：基准是 `68`、卡面写 `68%`，算命中（单位是卡面加的，不是编的）；
- **数字边界**：`168` 里不能把 `68` 算成命中；
- **复合值拆分**：金标写 `25℃ / 32℃` 时拆成两条事实，否则"只显示了其中一个"会被算成命中。

### 6. 验证

- 新增 `tests/test_measure.py`（10 项：指纹归一化、记录字段、覆盖/保真/重复/边界）；
- 九套测试全绿：`run_cases` 9/9、`test_capacity` 16/16、`test_gold_queries` 7/7、`test_forms` / `test_paths` / `test_routing_stability` / `test_pipeline_options` / `test_validate` / `test_measure`；
- 快照：`snapshot_pipeline` 65 条与 v3.18 逐字一致（度量层不改产物）。

## v3.20 变更记录（2026-10-26：移除融球 / 结构性主题）

### 1. 为什么移除

融球是实际项目的特殊视觉效果，实现方式（Stack 多层包裹 + 百分比球槽 + 玻璃层）不具备通用性，原型与论文都不需要体现它。它的存在还给分类带来误导：它是"会改组件树的结构变体"，却被登记在配色表里。

### 2. 代码

- `registry/enums.json`：theme 枚举 9 → 4（blue / purple / warm / dark）
- `registry/themes.json`：删除 5 套融球主题、顶层 `structural` 几何规格、各主题的 `structural` 标记
- `src/theme.py`：删除 structural 分支与 tokens 透传
- `src/compiler.py`：删除 `_wrap_structural` 与 `THEMES` / `STRUCTURAL` 常量
- `prompts/step1_structure_plan.md`：删除 5 个融球 id 的映射规则

### 3. 金标与数据集

- 下线 3 张融球卡（q28 / q36 / q37，artifact 与 jsonl 成对删除）：52 → **49 张**
- 重建 `examples/batch/batch_queries.json`、`examples/gold_pairs.json`、`examples/content_oracle.json`（128 条事实）
- `tools/gold_dataset.py`、`tools/extract_skeletons_from_cards.py` 删除融球判定分支

### 4. 文档与规范

- `ux-spec/UX-SPEC.md`：删 §3「融球」整节、§11.3 第 6/11/34/35 条、§12 相关记录；**规则编号不重排**，删除处留空号（避免破坏既有引用），变更记在 §12 v0.13
- `ux-spec/FEWSHOT_2x2.md` / `FEWSHOT_2x4.md`：删除融球说明段与示例里的 `design` 字段
- 本文 §6 / §7.6 / §8.5 / §12 / §15 同步

### 5. 验证

- 九套测试全绿：`run_cases` 9/9、`test_capacity` 16/16、`test_gold_queries` 7/7、`test_forms` / `test_paths` / `test_routing_stability` / `test_pipeline_options` / `test_validate` / `test_measure`
- `gold_dataset check`：**49/49 结构一致**
- 确定性快照：65 → **62 条**，差异只有 q28/q36/q37 三条消失，其余 62 条逐字未变

## v3.21 变更记录（2026-10-27：六处口径冻结，度量层落地）

### 1. 动机

口径不冻结，前后跑出的数不可比——相当于量身高不先定脱不脱鞋。此前六处"怎么算"没有明文规定，本次按论文文档 §15（口径记录 v1）统一，代码只留一个实现。

### 2. 六条口径与落点

| 编号 | 规定 | 代码落点 |
|---|---|---|
| C-01 | 失败卡 = 不合格（记 `generate.failed`；覆盖 0；保真不计入） | `src/measure.py:build_record`、`tools/measure_content.py:main` |
| C-02 | 覆盖拆 A4a（全量）/ A4b（must 必显子集，未标注 = 未量） | `tools/measure_content.py:check`（`coverage_must`） |
| C-03 | 空数据卡保真不计入，单独计数 | `tools/measure_content.py:check`（`empty_data`） |
| C-04 | 合格卡 = 协议合规 ∧ 覆盖 ≥80% ∧ 单节点越界 ≤4px（60/100 两档敏感性） | `tools/build_metrics_report.py:_qualified` |
| C-05 | 字号两条线：12fp（规范）/ 10fp（金标实测） | `src/measure.py:static_metrics`、`tools/measure_geometry.py:_min_font` |
| C-06 | 重采样 = 全一致率 + 措辞不同算不一致（严格下界） | `tools/resample_stability.py`（实现本就如此） |

### 3. 验证

- 新增 5 项单测：`test_static_two_font_lines` / `test_failed_record_counts_as_violation` / `test_coverage_must_requires_annotation` / `test_empty_data_card_flag`（原有 10 项全保留）
- 九套测试全绿；`snapshot_pipeline` 62 条与 v3.20 逐字一致（口径只改度量层，不改产物）
- Mock 全链路（run_condition → measure_content → measure_geometry → build_metrics_report）跑通，新字段全部落位：A4b 显示"未量"、空数据卡计数、合格@60/80/100、两条字号线

## v3.22 变更记录（2026-10-27：清理根目录与失效脚本）

### 1. 删除（用户确认，共约 38MB）

`cardgen-proto.zip`（10-15 旧快照）、`CreateMyCard-main.zip` + `_CreateMyCard_extract/`（同源参考项目）、`ppt/`（一次性答辩材料）、`kimi网页版的讨论记录.txt`（9-22 讨论记录）、`debug_output.json` / `debug_full_a2ui.jsonl`（调试产物，可重生成）。

**删除前抢救**：`鸿蒙桌面卡片A2UI协议完整规范.md`（76K，唯一未复制进原型的依据文档）→ `cardgen-proto/docs/external/`。其余有用内容（UX 规范、few-shot、154 个素材）此前已在 `ux-spec/` 与 `resources/base/media/`。

### 2. 三个根目录脚本的处置

| 脚本 | 判定 | 处置 |
|---|---|---|
| `client_demo.py` | 唯一覆盖 HTTP 链路的功能，非过时 | → `examples/client_demo.py` |
| `debug_pipeline.py` | 与 `service.server --cli --debug` 打印部分重复，但多"落盘 + 裸 JSONL" | → `tools/debug_pipeline.py`，落盘改到 `logs/`（已被 .gitignore 忽略） |
| `verify_a2ui_render.py` | **跑不起来**：依赖外部 `a2ui` 包（未安装、未随仓库分发） | **删除**；协议合规由 `src/validate.py` 的 15 条规则承担 |

诚实记录一处操作失误：删除命令把三个脚本连原件带副本一起删了，`debug_pipeline.py` 按原文逐字重建、`client_demo.py` 按功能重建（示例 query 列表为复原而非原文），重建后均已实测可跑。

### 3. 验证

- `tools/debug_pipeline.py` 实测跑通（真实模型），trace 与两份落盘文件均正常
- `examples/client_demo.py` 通过语法检查（需服务在跑才能端到端）
- 九套测试与 62 条快照不受影响（脚本与文档改动不触及流水线）

## v3.23 变更记录（2026-10-27：工作区结构重整）

### 1. 工作区改成"原型 / 论文"平行两兄弟

```
nextgenui/
├── cardgen-proto/     ← 原型（可独立交付）
├── paper/             ← 论文（双盲期私有）
├── 真实的高质量卡片数据/
└── README.md
```

论文不放进原型内部，理由：可公开性不同、依赖单向（靠 commit hash 绑定）、生命周期不同。详见根目录 `README.md`。

### 2. 文档归位（同一样东西只留一处）

| 文件 | 原位置 | 现位置 |
|---|---|---|
| 设计正本 | 工作区根目录 | `docs/AI卡片生成架构方案-v3.md` |
| 论文实验方案 | 工作区根目录 | `../paper/方案/论文实验方案.md` |
| A2UI 官方协议 + Basic Catalog | 工作区根目录 | `docs/external/` |

`docs/` 里那份停在 v3.16 的旧副本已被正本覆盖。**没有归档它**：它是同一文档的旧快照（严格子集），不含独有内容，留着只会在两个同名文件之间制造误读。

### 3. 原型内：产物统一进 runs/

原本产物散在 `examples/batch/runs/`（13M / 1796 文件）与 `runs/`（稳定性）两处，`examples/` 名义是"示例"却装着生成物。

- 物理迁移：`examples/batch/runs/*`、`batch_outputs.md`、`batch_report.json`、`gold_vs_run.md` → `runs/batch/`
- 代码跟随：`batch_generate.py`（新增 `RUNS_DIR`，输入仍读 `examples/batch`）、`check_layout.py`、`gold_dataset.py`、`viz/gen_card_compare.py`
- `.gitignore`：`examples/batch/runs/` 等四条合并为一条 `runs/`
- 删除 `resp1.json`（8 天前的散落调试响应，已在忽略清单里）

### 4. README 写清三条规矩

`examples/` 只放输入与基准；路径前缀只允许出现在 `src/paths.py`；跑一次能重建的不入库。目录树同步。

### 5. 验证

九套测试 9/9；62 条快照与改动前逐字一致（结构重整不触及流水线）。

## v3.24 变更记录（2026-10-27：目录名与内容对齐）

起因：用户指出 `logs/` 里放着产物、`examples/` 里放着不相关的东西。按"目录名必须说明内容"重新审视每个目录。

### 1. 四处拆分

| 目录 | 原来装了什么 | 现在 |
|---|---|---|
| `examples/` | 3 个基准 json + 2 个批次清单 + 1 个 demo 脚本 + 1 个生成物 | **只放可运行示例**（`client_demo.py` + README）；数据 → `fixtures/`；生成物 → `runs/acceptance/` |
| `fixtures/`（新） | — | 固定输入与基准：`cases` / `gold_pairs` / `content_oracle` / `batch_queries` |
| `viz/` | 2 个生成脚本 + 1 个产物 html | 脚本 → `tools/`；产物 → `runs/viz/`；目录删除 |
| `docs/external/` | A2UI 协议 / Basic Catalog / 鸿蒙 Form 规范 | → `refs/`（外部依据不是本项目文档） |
| `logs/` | 2 个日志 + 2 个调试产物 | **只放日志**；调试产物 → `runs/debug/` |

### 2. 代码跟随（18 处引用）

`src/sample_values.py`、`tests/`（3 个）、`tools/`（10 个）、两个可视化脚本；另修一处脆弱判断：`diff_gold` 原来靠 `args[0].startswith("examples")` 区分"路径 or 最新一次"，改为看 `Path(args[0]).exists()`——目录改名就失效的代码本来就不该存在。

### 3. `.gitignore`

四条零散规则（`examples/batch/runs/`、两个 md/json、`viz/*.html`、`examples/acceptance_outputs.json`）合并为一条 `runs/`。

### 4. 新增两份 README

`fixtures/README.md` 说明每个文件是什么、谁生成、谁消费；`examples/README.md` 说明这个目录只放可运行示例。

### 5. 验证

九套测试 9/9；62 条快照与改名前后逐字一致。


## v3.25 变更记录（2026-10-27：金标数据入库，原型自包含）

### 1. 数据迁入

`真实的高质量卡片数据/`（工作区根目录）→ `data/gold/`：98 文件 / 1.1 MB，原样搬、不改内容。三个已下线卡（q28/q36/q37）本就不在。

同时生成 `data/MANIFEST.sha256`（98 行），用于判定"这批结果对应哪一版数据"。校验命令：`cd data && sha256sum -c MANIFEST.sha256`。

### 2. 六处路径常量

`build_content_oracle` / `check_layout` / `diff_gold` / `extract_skeletons_from_cards` / `gold_dataset` / `gen_card_compare`——全部从 `ROOT.parent / "真实的高质量..."` 改为 `ROOT / "data" / "gold"`。原型从此可独立 clone 跑通（测试 / 重建基准 / 金标比对都不再依赖上级目录）。

### 3. 顺手修两个真 bug

- `build_content_oracle`：删掉 `PROJ` 后，末尾 `OUT.relative_to(PROJ)` 抛 `NameError`——生成成功但最后一行崩，改为 `relative_to(ROOT)`。
- `diff_gold`：旧批跑（52 张）里含 q28/q36/q37，金标已下线导致 `FileNotFoundError`。改为金标缺失即跳过并打印"跳过 N 张"，不再崩。

### 4. 数据只有一份

论文侧不复制，靠 `commit hash + MANIFEST 哈希` 两个指针。规则写进根 `README.md`、`paper/README.md`、`data/README.md`。

### 5. 验证

九套测试 9/9；62 条快照逐字一致；`gold_dataset check` 49/49 通过；`build_content_oracle` 重建后 `fixtures/content_oracle.json` 哈希不变（1485754e…）；`diff_gold` 正常输出并跳过 3 张下线卡。

## v3.26 变更记录（2026-10-27：删除服务层，只留核心）

### 1. 为什么删

原型是"验证路线是否成立"，不是交付一个可部署服务。`service/server.py` 只是 `generate()` 外面套的一层 `http.server`：单线程、无鉴权、无 CORS、绑 `0.0.0.0`、无访问日志、HTTP/1.0 每次关连接。这些限制逐条都是"演示够用、生产不够"，而它带来的维护成本（多一个入口要同步文档、多一份 `--cli` 与调试脚本重复）是持续的。

**判断依据**：它唯一的职责是"常驻 + 端口"，而这恰好是 `tools/` 里任何脚本都不做的事。留着它就等于让项目背一个自己都不打算维护的接口层。将来要包 HTTP 或前端，再加不迟。

### 2. 删了什么

| 删除项 | 原作用 |
|---|---|
| `service/server.py` + `__init__.py` | HTTP(:8000) `POST /generate`、`--cli` 单次生成 |
| `start.bat` / `start.sh` | 一键启动服务 |
| `examples/client_demo.py` + `examples/README.md` | 演示怎么调 HTTP 接口（服务没了它无从演示） |
| `examples/` 目录 | 唯一的文件是上面两个，目录随之取消 |

### 3. 入口收敛

原来有三个入口做同一件事（`service.server --cli`、`tools/debug_pipeline.py`、`examples/client_demo.py` 走 HTTP），现在只剩一个：

```bash
python tools/debug_pipeline.py "query"    # 逐环节 trace + 落盘 runs/debug/
```

流水线的库入口仍是 `src.pipeline.generate()`，九套测试一直走的就是它，未受影响。

### 4. 文档同步

`README.md` 快速开始与目录树、本文目录树与运行方式、`tools/debug_pipeline.py` 的说明、`ux-spec/UX-SPEC.md` 里 `examples/gold_pairs.json` 的失效路径。

### 5. 验证

九套测试 9/9；62 条快照逐字一致；`tools/debug_pipeline.py` 实测跑通（trace + 两份落盘文件正常）。"在线链路仅 1 次模型调用"这一验证目标不变——它由 `generate()` 内部的调用次数保证，与是否包 HTTP 无关。
