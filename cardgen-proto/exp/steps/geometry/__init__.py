"""geometry 阶段：组件树 → 带字号/换行/截断/丢弃的树。

- `model_solve`         模型给每个文本节点定字号与截断（L2~L4）  状态：待落地
- `program_solve_plan`  程序按实测文本宽度求解（L5~L6）          状态：已有 `src/P5_capacity.py` + `src/P5_assemble.py`

不放：结构选择（归 structure）；配色（归 theme）。
"""
