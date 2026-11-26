"""按事先登记的可表达条款评估内容首选，无可判条款记为未知。"""

def evaluate(choice, reference):
    facts, actions = set(choice["fact_ids"]), set(choice["action_ids"])
    required = [c for c in reference["clauses"] if c["kind"].startswith("required_")]
    misses = []
    totals = {"required_fact": 0, "required_action": 0}
    hits = totals.copy()
    for clause in required:
        kind = clause["kind"]
        totals[kind] += 1
        ids = actions if kind == "required_action" else facts
        if ids.intersection(clause["alternatives"]):
            hits[kind] += 1
        else:
            misses.append({"id": clause["id"], "evidence": clause["evidence"], "kind": kind})
    explicitly_excluded = sorted((facts | actions).intersection(reference["excluded"]))
    return {
        "totals": totals,
        "hits": hits,
        "misses": misses,
        "all_required": not misses if required else None,
        "excluded_selected": explicitly_excluded,
        "selected_facts": len(facts),
        "selected_actions": len(actions),
        "selected_without_sample": sorted(
            facts.intersection(reference["sample_missing_candidate_ids"])
        ),
    }


def summarize(rows, method):
    available = [row[method] for row in rows if row[method]["status"] == "ok"]
    judged = [r["evaluation"] for r in available]
    return {
        "case_count": len(rows),
        "valid": len(available),
        "all_required_cases": sum(x["all_required"] is True for x in judged),
        "unknown_cases": len(rows) - len(judged) + sum(x["all_required"] is None for x in judged),
        "required_total_all_inputs": {
            k: sum(r["select_all"]["evaluation"]["totals"][k] for r in rows)
            for k in ("required_fact", "required_action")
        },
        "hits_on_valid_choices": {
            k: sum(e["hits"][k] for e in judged) for k in ("required_fact", "required_action")
        },
        "selected_facts_on_valid_choices": sum(e["selected_facts"] for e in judged),
        "selected_actions_on_valid_choices": sum(e["selected_actions"] for e in judged),
        "known_excluded_items_selected": sum(len(e["excluded_selected"]) for e in judged),
    }
