"""六档实验条件 = 五个阶段逐级从模型移交给程序。

这里是论文里"六档条件表"在代码中的**唯一事实源**。方案不是实体，阶段才是；
六个方案只是同一张表的六行。

数据流（五个阶段，接口契约见论文 §17.2）：

    用户这句话 + 数据
        │ content   产出：语义计划（要哪几条信息、什么类型、哪个对象）
        ▼
    语义计划
        │ structure 产出：组件树骨架（有哪几块、谁装谁；无字号坐标）
        ▼
    组件树（骨架）
        │ geometry  产出：带字号/换行/截断/丢弃决定的树
        ▼
    带几何的树
        │ theme     产出：同一棵树 + 每个节点的色值（选主题 + 着色）
        ▼
    带色值的树
        │ emit      产出：三行 JSONL（A2UI）
        ▼
    卡片产物

两档形态：

- **分阶段档**（L2~L6、L5b）：五个阶段各有实现，按顺序调，上一步的产物是下一步的输入；
- **不分解档**（L1）：整行标 `one_shot`——模型一次生成直接出终产物，没有中间表示可拆。
  这不是偷懒，是"全包"的本质：给它编一组中间表示、每段调一次模型，那已经是另一档了（就是 L2）。

阶梯的排法（论文 §2）：从末端往前逐个移交，程序做后缀、模型做前缀。
每一档相对上一档只把一个阶段从模型移交给程序（L5b 例外：它只改结构这个阶段内部的实现）。
"""

from __future__ import annotations

# 整档不分解的标记：这一档没有阶段划分，一次生成直接出终产物
ONE_SHOT = "one_shot"

CONDITIONS = {
    # L1：一次生成，五段合一
    "L1": {"content": ONE_SHOT, "structure": ONE_SHOT, "geometry": ONE_SHOT,
           "theme": ONE_SHOT, "emit": ONE_SHOT},

    # L2：五段全模型（5 次调用）
    "L2": {"content": "model_extract", "structure": "model_free",
           "geometry": "model_solve", "theme": "model_theme", "emit": "model_emit"},

    # L3：发射归程序（4 次调用）
    "L3": {"content": "model_extract", "structure": "model_free",
           "geometry": "model_solve", "theme": "model_theme", "emit": "program_jsonl"},

    # L4：主题归程序（3 次调用）
    "L4": {"content": "model_extract", "structure": "model_free",
           "geometry": "model_solve", "theme": "program_theme", "emit": "program_jsonl"},

    # L5：几何归程序（2 次调用）
    "L5": {"content": "model_extract", "structure": "model_free",
           "geometry": "program_solve_plan", "theme": "program_theme", "emit": "program_jsonl"},

    # L5b：与 L5 只差结构内部的实现（自由写 → 从 16 个骨架里挑），补充实验，不进主表
    "L5b": {"content": "model_extract", "structure": "model_pick",
            "geometry": "program_solve_plan", "theme": "program_theme", "emit": "program_jsonl"},

    # L6：仅内容归模型（1 次调用）＝本发明原型
    "L6": {"content": "model_extract", "structure": "program_route",
           "geometry": "program_solve_plan", "theme": "program_theme", "emit": "program_jsonl"},
}

# 主表里的六档（L5b 是补充实验，单独报一行）
MAIN_CONDITIONS = ("L1", "L2", "L3", "L4", "L5", "L6")
SUPPLEMENT = ("L5b",)

# 论文正文用的中文名（顺序固定，别改）
LABELS = {
    "L1": "一次全包",
    "L2": "五段全模型",
    "L3": "发射归程序",
    "L4": "主题归程序",
    "L5": "几何归程序",
    "L5b": "结构改为从 16 选（补充）",
    "L6": "仅内容归模型（本发明原型）",
}

# 补救对照（RQ2）：同一个位置（全包）上给三次机会
REPAIR_CONDITIONS = {
    "L1-NR": {"base": "L1", "repair": "none", "desc": "裸生成，只有解析"},
    "L1": {"base": "L1", "repair": "program", "desc": "程序修复（主阶梯里那一档）"},
    "L1-M": {"base": "L1", "repair": "model", "max_rounds": 2, "desc": "模型修复，≤2 轮"},
    # 可选：补救增益随位置递减
    "L5-NR": {"base": "L5", "repair": "none"},
    "L6-NR": {"base": "L6", "repair": "none"},
}

STEPS = ("content", "structure", "geometry", "theme", "emit")


def is_one_shot(cond: str) -> bool:
    """这一档是不是"整档不分解"（五个格子都是 one_shot）。"""
    spec = CONDITIONS[cond]
    return all(spec.get(s) == ONE_SHOT for s in STEPS)


def model_calls(cond: str) -> int:
    """这一档需要几次模型调用（用于等预算分析与成本表）。"""
    if is_one_shot(cond):
        return 1
    return sum(1 for s in STEPS if str(CONDITIONS[cond].get(s, "")).startswith("model_"))


def appendix_table() -> str:
    """生成论文附录"条件 → 配置"映射表（markdown）。

    这张表不要手写：手写会与实际跑批不一致。论文正文只讲条件，
    附录用这张表回答"复现时环境怎么设"。
    """
    head = "| 条件 | 内容 | 结构 | 几何 | 主题 | 发射 | 调用 | 说明 |\n|---|---|---|---|---|---|---|---|\n"
    rows = []
    for name, spec in CONDITIONS.items():
        note = LABELS[name]
        if is_one_shot(name):
            rows.append(f"| {name} | — | — | — | — | — | 1 | {note} |")
            continue
        cells = [spec[s] for s in STEPS]
        rows.append(f"| {name} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {cells[4]} "
                    f"| {model_calls(name)} | {note} |")
    return head + "\n".join(rows) + "\n"


if __name__ == "__main__":
    print(appendix_table())
    print("主表：", "、".join(MAIN_CONDITIONS))
    print("补充：", "、".join(SUPPLEMENT))
