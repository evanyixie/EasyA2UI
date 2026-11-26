"""从原始冻结合同独立核对共有投影与首件。"""

import json
import re
from collections import Counter, defaultdict

MISSING = object()


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def tokens(expr):
    if isinstance(expr, dict) and set(expr) == {"path"} and isinstance(expr["path"], str):
        return [("path", expr["path"])]
    if not isinstance(expr, str):
        return None
    if not expr.strip().startswith("{{"):
        return [("literal", expr)] if expr else []
    expr = expr.strip()
    if not expr.endswith("}}"):
        return None
    expr = expr[2:-2].strip()
    result = []
    while expr:
        m = re.match(r"(?:'([^'\\]*)'|\$\{(/[^}]*)\})", expr)
        if not m:
            return None
        result.append(("literal", m.group(1)) if m.group(1) is not None else ("path", m.group(2)))
        expr = expr[m.end() :].strip()
        if not expr:
            return result
        if not expr.startswith("+") or not expr[1:].strip():
            return None
        expr = expr[1:].strip()
    return None


def render(stream, values, symbolic=None):
    def value(k, v):
        if k == "literal":
            return v
        if symbolic == "*" or symbolic == v:
            return "\u2063" + v + "\u2064"
        x = values[v]
        return str(x).lower() if isinstance(x, bool) else str(x)

    return "".join(value(k, v) for k, v in stream)


def paths(stream):
    return [v for k, v in stream if k == "path"]


def facts(row):
    out = {}
    for group in row["content_groups"]:
        units = [(i, u) for i, u in enumerate(row["semantic_units"]) if u["parent"] == group["id"]]
        for ix, src in enumerate(group["selected_value_sources"], 1):
            stream = tokens(src["content"])
            ps = paths(stream) if stream is not None else []
            related = [
                (i, u)
                for i, u in units
                if (u["take"] == "all" and len(group["selected_value_sources"]) == 1)
                or (isinstance(u["take"], dict) and u["take"].get("path") in ps)
            ]
            out[f"{group['id']}_{ix}"] = {
                "source": src,
                "stream": stream,
                "paths": ps,
                "related": related,
                "entities": sorted({u["entity"] for _, u in related}),
            }
    return out


def covered_by_terms(text, terms):
    text = text.strip()
    terms = {term.strip() for term in terms if isinstance(term, str) and term.strip()}
    reachable = {0}
    for i in range(len(text)):
        if i not in reachable:
            continue
        if text[i].isspace():
            reachable.add(i + 1)
        reachable.update(i + len(term) for term in terms if text.startswith(term, i))
    return len(text) in reachable


class Review:
    def __init__(self):
        self.checks = []
        self.hr = {
            "actual_glyph_clipping": None,
            "independent_visual_hierarchy_and_ux": None,
            "business_acceptance": None,
            "actual_event_dispatch_and_destination": None,
            "device_dynamic_update": None,
            "native_font_measurement": None,
        }

    def put(self, dim, where, status, reason, **fields):
        self.checks.append(
            {
                "dimension": dim,
                "where": where,
                "status": status,
                "reason": reason,
                **fields,
            }
        )

    def is_(self, dim, where, ok, reason, **fields):
        self.put(dim, where, "verified" if ok else "mismatch", reason, **fields)

    def done(self):
        counts = Counter(c["status"] for c in self.checks)
        return {
            "static_status": "mismatch"
            if counts["mismatch"]
            else "unresolved"
            if counts["unknown"]
            else "verified",
            "counts": dict(counts),
            "checks": self.checks,
            "independent_evidence": self.hr,
            "complete_product_success": None,
        }


def check_expr(review, ref, fact, expr, row):
    expected, actual = fact["stream"], tokens(expr)
    if expected is None or actual is None:
        review.put("expression", ref, "unknown", "表达式超出经确认的单引号原生拼接或直接绑定")
        return None
    binding_order = paths(actual)
    review.is_(
        "ordered_binding_occurrences",
        ref,
        binding_order == fact["paths"],
        "逐叶绑定路径、顺序及次数",
        expected=fact["paths"],
        observed=binding_order,
    )
    sample = row["binding_samples"]
    if any(p not in sample for p in fact["paths"] + binding_order):
        review.put("selected_sample", ref, "mismatch", "合同所需或产物所用路径没有冻结样值")
        return actual
    base = render(expected, sample, "*")
    observed = render(actual, sample, "*")
    terms = [u.get(k, "") for _, u in fact["related"] for k in ("label", "unit")]
    terms.extend(
        s for s in row["supporting_text"] if s.strip() and any(s.strip() in t for t in terms)
    )
    left, sep, right = observed.partition(base) if base else ("", "", "")
    conserved = bool(sep) and covered_by_terms(left, terms) and covered_by_terms(right, terms)
    review.is_(
        "expression",
        ref,
        conserved,
        "同一 Text 内完整保持原表达式、内部分隔和静态文案，只允许合同中的附属文字",
        expected_symbolic=base,
        observed_symbolic=observed,
    )
    for p in sorted(set(fact["paths"])):
        # 仅替换抽象符号，未向运行的数据模型写入任何新样值。
        match = (
            binding_order == fact["paths"]
            and conserved
            and render(actual, sample, p) == left + render(expected, sample, p) + right
        )
        review.is_(
            "symbolic_path_change",
            ref,
            match,
            "单个原路径替换为符号后仍保持同一变化，不按首帧文本猜来源",
            path=p,
        )
    if not fact["paths"]:
        review.is_("static_text", ref, conserved, "原静态表达保留在预期叶")
    rendered = re.sub(r"\s+", "", render(actual, sample))
    for unit in {u["unit"].strip() for _, u in fact["related"] if u.get("unit")}:
        review.is_(
            "unit_once",
            ref,
            unit + unit not in rendered,
            "样值所带单位及表达式单位不能重复",
            unit=unit,
        )
    declared = [b["path"] for b in fact["source"].get("bindings", [])]
    review.is_(
        "frozen_source_bindings",
        ref,
        declared == fact["paths"]
        and all(
            b["path"] in sample and canonical(b["sample_value"]) == canonical(sample[b["path"]])
            for b in fact["source"].get("bindings", [])
        ),
        "原表达路径与冻结来源记录、样值一致",
    )
    return actual


def original_scope(row):
    selected = facts(row)
    owners = defaultdict(set)
    for ref, f in selected.items():
        for _, u in f["related"]:
            owners[u["entity"]].add(ref)
    return selected, owners


def check_projection(row, shared):
    rv = Review()
    fs, _ = original_scope(row)
    for key in (
        "size",
        "D",
        "A",
        "actions",
        "entities",
        "relations",
        "semantic_units",
        "supporting_text",
        "constraints",
        "binding_samples",
        "user_preferences",
        "numeric_semantics",
    ):
        rv.is_(
            "source_metadata",
            key,
            canonical(shared.get(key)) == canonical(row[key]),
            "直接比对冻结选择合同",
        )
    units = shared.get("units", [])
    by_id = {u["id"]: u for u in units}
    rv.is_("unit_identity", "all", len(by_id) == len(units), "单位 ID 唯一")
    used = Counter(i for f in fs.values() for i, _ in f["related"])
    rv.is_(
        "coverage_of_original_selection",
        "all",
        used == Counter(range(len(row["semantic_units"])))
        and sum(g["count"] for g in row["content_groups"]) == row["D"],
        "全部原选语义单元各映射到一份完整表达；D 独立于实际叶数",
    )
    streams = {}
    for ref, f in fs.items():
        u = by_id.get(ref)
        if not u:
            rv.put("source_unit", ref, "mismatch", "冻结来源缺少对应投影")
            continue
        if not f["related"]:
            rv.put("unit_mapping", ref, "unknown", "原 semantic_unit 无法唯一关联本来源")
        expected_refs = sorted(i for i, _ in f["related"])
        rv.is_(
            "unit_mapping",
            ref,
            u.get("source_refs") == expected_refs,
            "按原始父组和 take.path 检查关联索引",
        )
        rv.is_("entity", ref, f["entities"] == [u.get("entity")], "所属原实体")
        roles = {unit["role"] for _, unit in f["related"]}
        if len(roles) == 1:
            rv.is_("role", ref, u.get("role") in roles, "原角色原样保留")
        else:
            rv.put("role", ref, "unknown", "同一来源含多角色，需独立审核")
        rv.is_("unit_kind", ref, u.get("kind") == "text", "冻结的可见事实表达须作为 Text")
        actual = check_expr(rv, ref, f, u.get("expression"), row)
        if actual is not None:
            streams[ref] = actual
            rv.is_(
                "path_inventory",
                ref,
                u.get("paths") == paths(actual),
                "投影路径清单与可见表达相同",
            )
            if all(p in row["binding_samples"] for p in paths(actual)):
                rv.is_(
                    "projected_sample_text",
                    ref,
                    u.get("sample_text") == render(actual, row["binding_samples"]),
                    "冻结样值按实际表达展开，与用于布局的文字相同",
                )
    for u in units:
        if u["id"] not in streams:
            t = tokens(u.get("expression", u.get("sample_text")))
            if t is not None:
                streams[u["id"]] = t
    expected_buttons = {
        a["action_id"] for a in row["actions"] if a["interaction"] == "independent_entry"
    }
    rv.is_(
        "projected_button_set",
        "all",
        {u["id"] for u in units if u.get("kind") == "button"} == expected_buttons,
        "独立入口保留全部原按钮，整卡/记录点击不增造按钮",
    )
    companions = defaultdict(set)
    for u in units:
        linked = u.get("for_unit")
        if linked:
            rv.is_(
                "support_owner",
                u["id"],
                linked in fs and u.get("entity") in fs[linked]["entities"],
                "投影标签所指可见值与原业务实体一致",
            )
            if linked in fs and u.get("entity") in fs[linked]["entities"]:
                companions[linked].add(u["id"])
    check_support(rv, row, fs, streams, companions)
    return rv.done()


def check_support(rv, row, fs, streams, siblings):
    labels = {ref: [u.get("label", "").strip() for _, u in f["related"]] for ref, f in fs.items()}
    units = {ref: [u.get("unit", "").strip() for _, u in f["related"]] for ref, f in fs.items()}
    literal = {ref: [v for k, v in stream if k == "literal"] for ref, stream in streams.items()}
    captions = {a["action_id"]: a.get("caption") for a in row["actions"] if a.get("caption")}
    for i, x in enumerate(row["supporting_text"]):
        term = x.strip()
        if not term:
            continue
        hosts = {r for r in fs if term in units[r] or any(term in label for label in labels[r])}
        ac = {k for k, cap in captions.items() if cap == x}
        if ac:
            ok = any(ref in literal and [s.strip() for s in literal[ref]] == [term] for ref in ac)
            rv.is_(
                "support_action_caption",
                str(i),
                ok,
                "冻结动作文案可在正确按钮上读取",
                text=x,
            )
        elif len(hosts) == 1:
            ref = next(iter(hosts))
            adjacent = siblings.get(ref, set())
            separate = any(v.strip() == term for n in adjacent for v in literal.get(n, []))
            if term in units[ref]:
                st = streams.get(ref, [])
                last_path = max((j for j, (kind, _) in enumerate(st) if kind == "path"), default=-1)
                embedded = any(term in v for kind, v in st[last_path + 1 :] if kind == "literal")
            else:
                embedded = any(term in v for v in literal.get(ref, []))
            rv.is_(
                "localized_support",
                ref,
                embedded or separate,
                "标识或单位须附于正确的值或其专属子树",
                text=x,
            )
        else:
            present = any(len(st) == 1 and st[0] == ("literal", x) for st in streams.values())
            rv.is_(
                "standalone_support",
                str(i),
                present,
                "独立标题通过完整静态文字核对，子串不算",
                text=x,
            )


def unpack(messages):
    uc = messages[1]["updateComponents"]
    comps = uc["components"]
    nodes = {c["id"]: c for c in comps}
    if len(nodes) != len(comps):
        raise ValueError("重复组件 ID")
    seen, descendants, parent, order = set(), {}, {}, []

    def walk(id_, up=None):
        if id_ in seen or id_ not in nodes:
            raise ValueError("重复父节点、环或悬空节点")
        seen.add(id_)
        parent[id_] = up
        order.append(id_)
        out = {id_}
        for child in nodes[id_].get("children", []):
            out.update(walk(child, id_))
        descendants[id_] = out
        return out

    root = uc.get("root", "root")
    walk(root)
    if seen != set(nodes):
        raise ValueError("存在不可达组件")
    return nodes, descendants, parent, order, root


def get_value(obj, path):
    for part in path[1:].split("/"):
        k = part.replace("~1", "/").replace("~0", "~")
        if isinstance(obj, dict) and k in obj:
            obj = obj[k]
        elif isinstance(obj, list) and k.isdecimal() and int(k) < len(obj):
            obj = obj[int(k)]
        else:
            return MISSING
    return obj


def check_native(row, messages):
    rv = Review()
    fs, owners = original_scope(row)
    try:
        nodes, desc, parents, order, root = unpack(messages)
        data = messages[2]["updateDataModel"]
        sample = data["value"]
        if data["path"] != "/":
            for tok in reversed(data["path"].strip("/").split("/")):
                sample = {tok: sample}
    except (ValueError, KeyError, TypeError, IndexError, RecursionError):
        rv.put("native_tree", "root", "mismatch", "三行产物树或首帧无法重建")
        return rv.done()
    for p, v in row["binding_samples"].items():
        actual = get_value(sample, p)
        rv.is_(
            "emitted_sample",
            p,
            actual is not MISSING and canonical(actual) == canonical(v),
            "含事件参数所依赖路径在内，原生首帧与冻结值相同",
        )
    streams = {}
    for ref, f in fs.items():
        c = nodes.get(ref)
        if c is None or c.get("component") != "Text":
            rv.put(
                "source_leaf",
                ref,
                "mismatch",
                "原来源必须作为一个可到达的 Text 完整保留",
            )
            continue
        t = check_expr(rv, ref, f, c.get("content"), row)
        if t is not None:
            streams[ref] = t
    for cid, c in nodes.items():
        if c.get("component") in ("Text", "Button") and cid not in fs:
            st = tokens(c.get("content") if c["component"] == "Text" else c.get("label"))
            if st is None:
                rv.put("unregistered_text", cid, "unknown", "额外文字表达无法确认")
            else:
                streams[cid] = st
                authorized = list(row["supporting_text"]) + [
                    a["caption"] for a in row["actions"] if a.get("caption")
                ]
                rv.is_(
                    "extra_visible_leaf",
                    cid,
                    len(st) == 1 and st[0][0] == "literal" and st[0][1] in authorized,
                    "附加可见叶须来自冻结支撑文字或动作标题",
                )
    siblings = {}
    for ref in fs:
        parent = parents.get(ref)
        if parent and (desc[parent] & fs.keys()) == {ref}:
            siblings[ref] = desc[parent] - {ref}
        elif parent:
            ordered = nodes[parent].get("children", [])
            idx = ordered.index(ref)
            if idx > 0 and ordered[idx - 1].startswith("support_"):
                siblings[ref] = {ordered[idx - 1]}
    check_support(rv, row, fs, streams, siblings)
    check_entities_actions(rv, row, nodes, desc, order, root, fs, owners)
    check_presentation(rv, row, nodes, fs, owners)
    return rv.done()


def check_entities_actions(rv, row, nodes, desc, order, root, fs, owners):
    fact_ids = set(fs)
    fact_order = [cid for cid in order if cid in fact_ids]
    for ent, refs in owners.items():
        present = refs <= nodes.keys()
        if not present:
            rv.put("entity_evidence", ent, "mismatch", "此实体的冻结来源有缺失")
            continue
        exclusive = [cid for cid in order if (desc[cid] & fact_ids) == refs]
        indices = sorted(fact_order.index(r) for r in refs)
        if exclusive or (indices and indices[-1] - indices[0] + 1 == len(indices)):
            rv.put(
                "entity_evidence",
                ent,
                "verified",
                "原实体的来源出现在专属子树或连续阅读序列",
                exclusive_subtree=bool(exclusive),
            )
        else:
            rv.put(
                "entity_evidence",
                ent,
                "unknown",
                "同实体来源分散，需由原生视觉确认归属",
            )
    for rel in row["relations"]:
        src, target, typ = rel["from"], rel["to"], rel["type"]
        left, right = owners.get(src, set()), owners.get(target, set())
        if typ == "ordered" and left and right and (left | right) <= set(fact_order):
            rv.is_(
                "ordered_entities",
                src + "/" + target,
                max(map(fact_order.index, left)) < min(map(fact_order.index, right)),
                "冻结实体阅读顺序",
            )
        elif typ == "contains":
            rv.put(
                "semantic_relation",
                src + "/" + target,
                "unknown",
                "集合关系需结合原生记录组织判断",
            )
        elif typ in ("peer", "primary_support", "supports"):
            rv.put(
                "semantic_relation",
                src + "/" + target,
                "unknown",
                "相对层级、等权或主辅关系需原生视觉判断",
            )
    observed = [(cid, node["onClick"]) for cid, node in nodes.items() if "onClick" in node]
    matched = set()
    visual_leaves = {cid for cid, n in nodes.items() if n.get("component") in ("Text", "Button")}
    owned_leaves = {owner: set(ids) for owner, ids in owners.items()}
    for i, value in enumerate(row["supporting_text"], 1):
        sid = "support_" + str(i)
        if sid not in nodes:
            continue
        term = value.strip()
        refs = {
            r
            for r, f in fs.items()
            if term
            and any(term in u.get("label", "") or term == u.get("unit") for _, u in f["related"])
        }
        if len(refs) == 1:
            for ent in fs[next(iter(refs))]["entities"]:
                owned_leaves.setdefault(ent, set()).add(sid)
    for a in row["actions"]:
        if a["interaction"] == "independent_entry":
            for ent in a["owners"]:
                owned_leaves.setdefault(ent, set()).add(a["action_id"])
    for action in row["actions"]:
        aid, mode = action["action_id"], action["interaction"]
        actual = [
            cid
            for cid, handlers in observed
            if canonical(handlers) == canonical(action["handlers"])
        ]
        if mode == "whole_card":
            allowed = {root}
        elif mode == "record_click":
            members = set().union(*(owned_leaves.get(o, set()) for o in action["owners"]))
            allowed = {cid for cid in nodes if members and desc[cid] & visual_leaves == members}
        elif mode == "independent_entry":
            allowed = {aid} if nodes.get(aid, {}).get("component") == "Button" else set()
            rv.is_(
                "button_caption",
                aid,
                nodes.get(aid, {}).get("label") == action["caption"],
                "独立按钮可见原文",
            )
        else:
            rv.put("action_scope", aid, "unknown", "当前审查器未支持该动作拓扑")
            continue
        hits = [cid for cid in actual if cid in allowed and cid not in matched]
        rv.is_(
            "handler_and_hit_scope",
            aid,
            len(hits) == 1,
            "比较完整 handler/call/args、所属记录或根的点击范围",
            eligible_nodes=sorted(allowed),
            observed_on=actual,
        )
        if len(hits) == 1:
            matched.add(hits[0])
            if mode == "independent_entry" and len(row["entities"]) > 1:
                rv.put(
                    "button_visual_owner",
                    aid,
                    "unknown",
                    "按钮载荷和题定标题独立核对，视觉归属需人审",
                )
    rv.is_(
        "unrequested_handlers",
        "root",
        {cid for cid, _ in observed} == matched,
        "全部可达事件载荷均有冻结来源且只出现于一个正确节点",
    )


def check_presentation(rv, row, nodes, fs, owners):
    shell = nodes.get("root", {}).get("styles", {})
    expected_w = {"2x2": 150, "2x4": 300}.get(row["size"])
    rv.is_(
        "frozen_canvas_shell",
        "root",
        shell.get("width") == expected_w
        and shell.get("height") == 150
        and shell.get("padding") == 12
        and shell.get("borderRadius") == 20
        and shell.get("clip") is True,
        "调用者尺寸与共同登记的 12vp 内边距、20vp 圆角和裁切声明",
    )
    for pref in row["user_preferences"]:
        if pref["kind"] == "background":
            images = [
                n
                for n in nodes.values()
                if n.get("component") == "Image"
                or n.get("styles", {}).get("backgroundImage")
                or n.get("backgroundImage")
            ]
            rv.put(
                "explicit_background",
                pref["quote"],
                "unknown" if images else "mismatch",
                "有图像引用，需核实素材和真实加载"
                if images
                else "请求的图像背景缺相应资源，色板不能证明满足",
            )
        else:
            rv.put(
                "explicit_preference",
                pref["quote"],
                "unknown",
                "风格参考需原资产与人工独立比对",
            )
    if not row["user_preferences"]:
        rv.put("explicit_preference", "root", "not_applicable", "合同未指定偏好")
    for ent, refs in owners.items():
        scores = []
        for ref in refs:
            roles = {u["role"] for _, u in fs[ref]["related"]}
            size = nodes.get(ref, {}).get("styles", {}).get("fontSize")
            if type(size) in (int, float):
                scores.extend((role, size) for role in roles)
        main = [s for role, s in scores if role == "primary"]
        sub = [s for role, s in scores if role == "secondary"]
        if main and sub:
            rv.put(
                "declared_entity_hierarchy",
                ent,
                "verified" if min(main) >= max(sub) else "unknown",
                "同实体主值和次值的声明字号；视觉显著性仍需评审",
                primary=main,
                secondary=sub,
            )
    for cid, node in nodes.items():
        if node.get("component") in ("Text", "Button"):
            st = node.get("styles", {})
            if any(st.get(k) is False for k in ("visible",)) or st.get("visibility") in (
                "hidden",
                "none",
            ):
                rv.put("visible_declaration", cid, "mismatch", "必留文字或动作被显式隐藏")
            if type(st.get("fontSize")) in (int, float):
                rv.is_(
                    "declared_min_font",
                    cid,
                    st["fontSize"] >= 12,
                    "原生声明字号不低于 12fp",
                    fontSize=st["fontSize"],
                )
            else:
                rv.put(
                    "declared_min_font",
                    cid,
                    "unknown",
                    "需宿主默认规格或原生树核实字号",
                )
            if node["component"] == "Button":
                rv.is_(
                    "button_recipe",
                    cid,
                    st.get("fontSize") == 14
                    and st.get("height") == 36
                    and st.get("borderRadius") == 18,
                    "共同动作配方为 14fp、36vp 胶囊",
                )
            elif cid in fs and fs[cid]["related"]:
                roles = {u["role"] for _, u in fs[cid]["related"]}
                if len(roles) == 1:
                    size, weight = (21, 700) if roles == {"primary"} else (14, 400)
                    rv.is_(
                        "unit_typography",
                        cid,
                        (st.get("fontSize"), st.get("fontWeight")) == (size, weight),
                        "所选原角色对应共同的可读字号及字重",
                        expected=[size, weight],
                    )
            elif cid.startswith("support_"):
                value = node.get("content", "")
                claims = {
                    r
                    for r, f in fs.items()
                    if isinstance(value, str)
                    and value.strip()
                    and any(value.strip() in u.get("label", "") for _, u in f["related"])
                }
                if len(claims) == 1:
                    size = 14
                else:
                    size = 12
                rv.is_(
                    "support_typography",
                    cid,
                    st.get("fontSize") == size,
                    "冻结支撑标识按身份或独立标题核对",
                    expected=size,
                )
