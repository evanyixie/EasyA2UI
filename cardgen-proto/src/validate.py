"""A2UI 产物校验：只判不修。

**它不是流水线的一个阶段，是一个纯函数库。** 有两个调用方：
  1. 出口修正（repair_card）先调它拿违规清单，再决定改什么；
  2. 评测与统计直接调它，量“没有修正时有多少违规”。
所以它不需要开关——尺子随时可用。

与 tests/run_cases.py 里原来的 check_full_a2ui 规则一一对应，只是改成结构化输出，
好让统计能按 code 分组（“哪一类违规最多”“关掉修复后多出哪些 code”）。
"""
import json
from dataclasses import dataclass

FORM_ALLOWED = {"Text", "Image", "Divider", "Progress", "Button",
                "Checkbox", "Row", "Column", "List", "Stack"}
CATALOG_ID = "ohos.a2ui.extended.catalog.form"


@dataclass(frozen=True)
class Violation:
    """一条违规。code 稳定，供统计分组；where 指出位置，供修复定位。"""

    code: str
    where: str
    detail: str
    severity: str = "error"

    def __str__(self) -> str:
        return f"{self.code} @ {self.where}: {self.detail}"


def validate_a2ui(text: str, surface_id: str, size: str = "2x2") -> list:
    """校验三行 JSONL 的结构合规性。返回违规列表，空 = 通过。"""
    out = []

    def add(code, where, detail, severity="error"):
        out.append(Violation(code=code, where=where, detail=detail, severity=severity))

    lines = [l for l in (text or "").splitlines() if l.strip()]
    if len(lines) != 3:
        add("jsonl.line_count", "text", f"jsonl 行数 {len(lines)} != 3")
        return out
    try:
        m1, m2, m3 = (json.loads(l) for l in lines)
    except Exception as e:  # noqa: BLE001
        add("jsonl.parse", "text", f"jsonl 解析失败: {e}")
        return out

    for idx, (msg, key) in enumerate(((m1, "createSurface"),
                                      (m2, "updateComponents"),
                                      (m3, "updateDataModel")), start=1):
        if set(msg) != {"version", key}:
            add(f"envelope.line{idx}", f"line{idx}",
                f"第{idx}行必须是 {key} 消息（且只有 version + {key} 两个键）")
        if msg.get("version") != "v0.9":
            add("envelope.version", f"line{idx}", "version 必须为 v0.9")

    cs = m1.get("createSurface", {})
    if cs.get("surfaceId") != surface_id:
        add("surface.create_surface", "line1", "createSurface.surfaceId 与 IR 不一致")
    if cs.get("catalogId") != CATALOG_ID:
        add("catalog.id", "line1", f"createSurface.catalogId 必须是 {CATALOG_ID}")

    uc = m2.get("updateComponents", {})
    if uc.get("surfaceId") != surface_id:
        add("surface.update_components", "line2", "updateComponents.surfaceId 与 IR 不一致")

    comps = uc.get("components", [])
    ids = [c.get("id") for c in comps]
    if ids.count("root") != 1:
        add("tree.root_count", "line2", f"必须恰好一个 id=root 的组件（实际 {ids.count('root')}）")
    idset = set(ids)
    for c in comps:
        cid = c.get("id", "?")
        for ch in c.get("children", []) or []:
            if ch not in idset:
                add("tree.dangling_child", cid, f"children 引用不存在的 id: {ch}")
        if c.get("component") not in FORM_ALLOWED:
            add("component.not_allowed", cid, f"组件 {c.get('component')} 不在 Form 白名单")
        if c.get("component") == "Button":
            if "action" in c:
                add("button.action_field", cid, "Button 禁止 action 字段")
            oc = c.get("onClick")
            if not isinstance(oc, list) or len(oc) != 1 or "call" not in oc[0]:
                add("button.on_click", cid, "Button 的 onClick 必须是恰好 1 个含 call 的 handler")

    root = next((c for c in comps if c.get("id") == "root"), {})
    rs = root.get("styles", {})
    width, height = (300, 150) if size == "2x4" else (150, 150)
    if (rs.get("width"), rs.get("height")) != (width, height):
        add("root.canvas", "root",
            f"root styles 必须 width/height = {width}x{height}（显式画布尺寸）")
    if rs.get("borderRadius") != 20 or rs.get("clip") is not True:
        add("root.shell", "root", "root styles 必须 borderRadius=20 且 clip=true")

    ud = m3.get("updateDataModel", {})
    if ud.get("surfaceId") != surface_id or not str(ud.get("path", "")).startswith("/"):
        add("data_model.path", "line3", "updateDataModel.surfaceId / path 不合法")
    if "value" not in ud:
        add("data_model.value", "line3", "updateDataModel 缺少首帧 value")

    return out


def count_by_code(violations) -> dict:
    """按 code 计数，供日志与实验统计（“哪一类违规最多”）。"""
    counts = {}
    for v in violations:
        counts[v.code] = counts.get(v.code, 0) + 1
    return counts
