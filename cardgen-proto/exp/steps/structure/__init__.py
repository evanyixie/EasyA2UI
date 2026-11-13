"""structure 阶段：语义计划 → 组件树骨架。

- `model_free`     模型自由写树（L2~L5）              状态：待落地
- `model_pick`     模型从 16 个骨架里挑一个（L5b）     状态：待落地（程序校验并采用该 id）
- `program_route`  程序按规则路由（L6）               状态：已有 `src/P2_skeleton_route.py`

不放：字号与几何（归 geometry）；主题（归 theme）。
"""
