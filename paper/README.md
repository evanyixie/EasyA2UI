# paper/ — 论文资料

与 `../cardgen-proto/` **平行**，不是它的子目录。理由：可公开性不同（原型要交付，论文双盲期必须匿名）、依赖单向（论文用原型跑实验，原型不依赖论文）、生命周期不同（代码日更，论文长周期后冻结）。

两者靠 **commit hash 绑定**，不靠目录嵌套：论文里写清"实验基于 `cardgen-proto@<hash>`"，而不是把论文塞进代码仓库。

## 目录

```
paper/
├── 方案/          实验设计与口径记录（论文实验方案.md）
├── experiments/   实验编排与出表（import ../cardgen-proto/src）
├── data/          实验产物：records.jsonl、报表、图表
└── refs/          外部资料：同类论文笔记、协议摘录
```

## 现状（2026-10-27）

- `方案/论文实验方案.md` 已就位（§1~§15，含口径记录与待办总表）。
- `experiments/` 仍为空：实验编排脚本暂时留在 `cardgen-proto/tools/`（`run_condition` / `measure_*` / `build_metrics_report` / `resample_stability` / `build_content_oracle`），因为它们要 `import src`。迁移是下一步，需一并改 sys.path。
- `data/` 为空是正常的：它只装实验产物，输入数据在原型里。
- `refs/` 为空：8 篇对照论文的要点已在方案 §13，原文链接可直接点。

## 数据只有一份，靠指针引用

金标数据（98 文件 / 1.1 MB）在 `../cardgen-proto/data/gold/`，**论文侧不复制**。理由：两份必然分叉（设计文档已经分叉过一次），而输入数据属于被测系统——原型 clone 下来必须能跑。

论文侧要钉的是**两个指针**：

1. `cardgen-proto@<commit>` —— 用的是哪一版代码；
2. `data/MANIFEST.sha256` 的哈希 —— 用的是哪一版数据。

有了这两个，"这批结果对应哪一版"永远可判定，不需要冻结副本。`paper/data/` 只放**跑出来的东西**（records / 报表 / 图），不放输入。

第三种东西单独说：投稿时的**复现包**不是工作副本，是从原型打出来的发布物（数据 + 脚本 + 条件映射），一次性生成、带版本号。

## 边界（写论文时照着这条判）

| 东西 | 放哪 | 判据 |
|---|---|---|
| 金标原始数据 49 对 | `cardgen-proto/data` | 输入，原型要能独立跑 |
| 流水线、注册表、提示词、测试 | `cardgen-proto` | 产品能力，生产也要用 |
| 校验器 `validate.py`、度量 `measure.py` | `cardgen-proto/src` | 通用可观测性，不属于实验 |
| 条件编排、出表、重采样、oracle 生成 | `paper/experiments` | 只服务实验 |
| 论文正文、图表、实验结果 | `paper` | 只服务写作与投稿 |
