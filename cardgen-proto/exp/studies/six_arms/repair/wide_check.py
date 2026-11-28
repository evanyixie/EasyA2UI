"""对相同原卡的不同补救使用同一把尺，允许重组容器，保持所有已选叶与动作归属。"""

from . import evidence


def contract(messages):
    packet = messages[1]["updateComponents"]
    tree = evidence.native.fidelity.graph(packet)
    leaves, actions, paint = [], {}, {}

    def walk(node):
        key, component, style = node["id"], node["component"], node["styles"]
        kind = component["component"]
        colors = {
            name: style[name]
            for name in evidence.native.fidelity.THEME
            if name in style
        }
        if colors:
            paint[key] = colors
        child_ids = []
        for child in node["children"]:
            child_ids.extend(walk(child))
        if kind in ("Text", "Button"):
            field = "content" if kind == "Text" else "label"
            leaves.append(
                [
                    key,
                    kind,
                    field,
                    component[field],
                    {
                        k: style[k]
                        for k in ("fontSize", "fontWeight", "lineHeight")
                        if k in style
                    },
                ]
            )
            child_ids = [key]
        if component.get("onClick"):
            actions[key] = [component["onClick"], child_ids]
        return child_ids

    walk(tree)
    size_style = tree["styles"]
    return {
        "leaves_in_order": leaves,
        "actions_and_descendants": actions,
        "node_colors": paint,
        "canvas_and_shell": [
            tree["id"],
            {k: size_style.get(k) for k in ("width", "height", "borderRadius", "clip")},
        ],
        "create_surface": messages[0],
        "surface_id": packet["surfaceId"],
        "first_frame": messages[2],
    }


def assess(original, candidate, source):
    before = evidence.inspect_card(original, source)
    after = evidence.inspect_card(candidate, source)
    reasons = []
    preservation = {}
    for section in ("protocol", "source", "geometry"):
        if after[section]["pass"] is not True:
            reasons.append(section)
    action_samples = after["source"].get("action_parameter_samples", [])
    if any(
        row["state"] != "matched" or not row["exact_handler_allowed"]
        for row in action_samples
    ):
        reasons.append("action_parameter_source")
    try:
        one = contract(evidence.native.parse(original))
        two = contract(evidence.native.parse(candidate))
        preservation = {
            k: evidence.signature(v) == evidence.signature(two[k])
            for k, v in one.items()
        }
        for key, match in preservation.items():
            if not match:
                reasons.append(key)
    except evidence.FAILURES as exc:
        reasons.append("protected_content_unknown: " + str(exc)[:240])
    local = evidence.compare_candidate(original, candidate, source)
    return {
        "accepted": not reasons,
        "after": after,
        "before": before,
        "preservation": preservation,
        "violations": reasons,
        "local_rule_pass": local["accepted"],
    }
