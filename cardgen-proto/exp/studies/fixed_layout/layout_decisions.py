"""固定内容研究的模型角色、实际提示、参考宽度表与响应解析。"""

import json

import common_native as common
from common_native import require
from runtime import program

COMMON = (
    "在同一画布内安排已经确定的全部可见内容。内容单元与动作已经由调用者冻结。\n"
    "同一记录的身份、值和单位放在一起，主次按实体理解。"
    "不得改写文字、增删叶、重排有顺序的记录、拆开一条多值表达式。实体名只用于理解。\n"
    "根是row或column。容器kind、children；"
    "叶只有kind(text或button)、ref。"
    "unit中的for_unit是身份对应的值，显示身份在该值之前。"
    "record_click要有仅含该对象全部文字叶的独立容器，"
    "按钮只对应独立动作。whole_card自动挂根。\n"
    "普通根内边距12、圆角20、内容从起点排。宽高vp，"
    "标题12fp，主值21fp，其他文字14fp，按钮14fp、高36vp、左右预留12vp、圆角18。"
    "间距可选2、4、6、8vp。根尺寸由canvas给出。禁止缩字或改变尺寸。\n"
    "给出的reference是同一参考字体的完整整数宽度表。"
    "每项width_ranges中 [最小宽,最大宽,所需行数,自然高度] 均含两端；"
    "没列出的宽度容不下。小数列宽可保守按向下取整查。当前只允许四种原语，"
    "结构合法情况下可选择任一组合。只输出一个合法JSON对象。"
)


def measurements(shared):
    inside = shared["canvas"]["width"] - 24
    oracle = program._measure()
    result = {}
    for u in shared["units"]:
        size, weight, line_height, max_lines = common.font(u)
        button = u["kind"] == "button"
        ranges = []
        for width in range(1, inside + 1):
            try:
                m = oracle.text(
                    u["sample_text"],
                    width - 24 * button,
                    size,
                    max_lines=max_lines,
                    bold=weight >= 600,
                    line_height=line_height,
                )
                if button and m.height > 36:
                    continue
            except ValueError:
                continue
            result_at_width = [m.lines, 36 if button else m.height]
            if ranges and ranges[-1][1] == width - 1 and ranges[-1][2:] == result_at_width:
                ranges[-1][1] = width
            else:
                ranges.append([width, width, *result_at_width])
        result[u["id"]] = {
            "font": size,
            "single_line_width": program._natural_width(u["sample_text"], size, weight)
            + 24 * button,
            "width_ranges": ranges,
        }
    return result


def prompt(stage, shared, reference, tree=None):
    visible_keys = ("id", "kind", "role", "entity", "sample_text", "for_unit", "paths")
    view = {k: shared[k] for k in ("canvas", "entities", "relations", "user_preferences")}
    view["visible"] = [{k: u[k] for k in visible_keys if k in u} for u in shared["units"]]
    view["actions"] = [
        {k: a[k] for k in ("action_id", "interaction", "owners")} for a in shared["actions"]
    ]
    view["reference"] = reference
    if stage == "structure":
        spec = (
            "选择结构，所有可见ID各用一次。禁止style、坐标、宽高。"
            '输出示例 {"root":{"kind":"column","children":[{"kind":"text","ref":"x"},'
            '{"kind":"button","ref":"go"}]}}。'
            "示例ID仅作格式说明，请使用本题真实ID。"
        )
    else:
        view["tree"] = tree
        view["positions"] = [
            {"at": p, "kind": n["kind"], **({"ref": n["ref"]} if "ref" in n else {})}
            for p, n in common.walk(tree["root"])
        ]
        spec = (
            '为既定树给出所有节点的几何。返回 {"boxes":[...]}。每个位置必须提交数字宽w、高h；'
            "容器另填gap，叶另填整数lines。不得改变结构，字号和样式将由统一配方填写。根的w和h与canvas完全相同。"
            "row中子宽之和加间距不得超过可用宽度，column中子高之和加间距不得超过可用高度；仅根四边各扣12。"
            "单节点容器仍填已登记gap。标题、按钮都1行，主值最多2行。例："
            '{"boxes":[{"at":"0","w":150,"h":150,"gap":4},{"at":"0.0","w":126,"h":30,"lines":1},{"at":"0.1","w":126,"h":36,"lines":1}]}。'
            "根下 children[0] 的编号0.0，继续向内逐层追加索引。"
        )
    return [
        {"role": "system", "content": COMMON + "\n" + spec},
        {
            "role": "user",
            "content": json.dumps(view, ensure_ascii=False, separators=(",", ":")),
        },
    ]


def parse(raw):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            require(k not in result, "JSON键重复")
            result[k] = v
        return result

    return json.loads(
        raw,
        object_pairs_hook=unique,
        parse_constant=lambda x: require(False, "非有限数字"),
    )
