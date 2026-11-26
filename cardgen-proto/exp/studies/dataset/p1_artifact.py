"""P1 结构准入。未知绑定与物理可见性保留为未量。"""

from audit_common import FORM_COMPONENTS, bindings, graph_evidence, messages, pointer


def leaf_values(value):
    if isinstance(value, dict):
        return [leaf for child in value.values() for leaf in leaf_values(child)]
    if isinstance(value, list):
        return [leaf for child in value for leaf in leaf_values(child)]
    return [value] if value is not None and value != "" else []


def check(code, status, **evidence):
    return {"code": code, "status": status, "evidence": evidence}


def artifact_check(path, size):
    checks, details, normalized = [], {}, None
    if path is None:
        return (
            [check("P1_C1_MESSAGES", "fail", reason="MISSING_ARTIFACT")],
            details,
            None,
        )
    try:
        normalized = messages(path)
        expected = ("createSurface", "updateComponents", "updateDataModel")
        envelopes = {
            key: [msg[key] for msg in normalized if key in msg] for key in expected
        }
        if any(len(envelopes[key]) != 1 for key in expected) or len(normalized) != 3:
            raise ValueError("expected exactly one of each of the three messages")
        create, update, data = (envelopes[key][0] for key in expected)
        if not all(isinstance(value, dict) for value in (create, update, data)):
            raise ValueError("message body is not an object")
        surfaces = [body.get("surfaceId") for body in (create, update, data)]
        if (
            not isinstance(surfaces[0], str)
            or not surfaces[0]
            or len(set(surfaces)) != 1
        ):
            raise ValueError("surface IDs missing or inconsistent")
        if any(msg.get("version") != "v0.9" for msg in normalized):
            raise ValueError("unsupported protocol version")
        checks.append(check("P1_C1_MESSAGES", "pass", surface_id=surfaces[0]))
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        return [check("P1_C1_MESSAGES", "fail", reason=str(exc))], details, None
    components = update.get("components", [])
    if not isinstance(components, list):
        checks.append(check("P1_C2_COMPONENTS", "fail", reason="components not a list"))
        return checks, details, normalized
    observed = sorted(
        {str(item.get("component")) for item in components if isinstance(item, dict)}
    )
    unknown = sorted(set(observed) - FORM_COMPONENTS)
    checks.append(
        check(
            "P1_C2_COMPONENTS",
            "fail" if unknown else "pass",
            observed=observed,
            unsupported=unknown,
            whitelist_source="Easy060fcf0/src/validate.py:FORM_ALLOWED(10)",
        )
    )
    details["component_types"] = observed
    try:
        evidence = graph_evidence(update)
        checks.append(
            check(
                "P1_C5_TEXT_LOCATABLE",
                "pass",
                **evidence,
                scope="structural paths only, not measured pixel geometry",
            )
        )
        details.update(evidence)
    except (ValueError, KeyError, TypeError, RecursionError) as exc:
        checks.append(check("P1_C5_TEXT_LOCATABLE", "fail", reason=str(exc)))
    references = list(bindings(components))
    unresolved = []
    if data.get("path") not in ("/", ""):
        checks.append(
            check(
                "P1_C3_BINDINGS",
                "unknown",
                reason="NON_ROOT_DATA_UPDATE",
                references=len(references),
            )
        )
    else:
        model = data.get("value")
        for location, ref in references:
            try:
                pointer(model, ref)
            except (ValueError, TypeError) as exc:
                unresolved.append(
                    {"location": location, "path": ref, "reason": str(exc)}
                )
        checks.append(
            check(
                "P1_C3_BINDINGS",
                "fail" if unresolved else "pass",
                references=len(references),
                unresolved=unresolved,
                scope="source path resolution, not arbitrary expression execution",
            )
        )
    values = leaf_values(data.get("value"))
    checks.append(
        check(
            "P1_C6_NONEMPTY",
            "pass" if len(components) >= 3 and values else "fail",
            components=len(components),
            data_leaf_count=len(values),
            scope="paper dataset eligibility; not a general static-card validity rule",
        )
    )
    details["binding_count"] = len(references)
    details["wrappers"] = [
        item.get("id")
        for item in components
        if isinstance(item, dict)
        and item.get("id")
        in {"__post_theme_foreground", "__genui_render_component__root"}
    ]
    details["theme_present"] = any(
        isinstance(item, dict)
        and any(
            key in item.get("styles", {})
            for key in ("linearGradient", "backgroundColor")
        )
        for item in components
    )
    root_node = next(
        (
            item
            for item in components
            if isinstance(item, dict) and item.get("id") == update.get("root")
        ),
        {},
    )
    styles = root_node.get("styles", {})
    width, height = styles.get("width"), styles.get("height")
    details["host_size_vp"] = (
        {"width": width, "height": height}
        if all(type(value) in (int, float) and value > 0 for value in (width, height))
        else None
    )
    details["physical_geometry_status"] = "not_measured"
    details["logical_size"] = size
    return checks, details, normalized
