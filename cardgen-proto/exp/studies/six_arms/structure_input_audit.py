"""Verify what L5 and the original L6 could read in the fixed-content comparison."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from six_arms.enhanced_repeat_bridge import PINS
from six_arms.fixed_content_repeats import FORMAL_PLAN, canonical, check, digest
from six_arms.formal_reference_cost import ROOT, encode
from six_arms.harness_v2 import model_stages, program_stages, trial
from six_arms.matched_structure_repeats import archived
from six_arms.paired_delivery_bounds import verified

TABLE = ROOT / "paper/out/tables/structure_input_audit.json"


def nested_button(tree):
    def visit(node, depth):
        if node["kind"] == "button":
            return depth > 1
        return any(visit(child, depth + 1) for child in node.get("children", []))

    return visit(tree["root"], 0)


def compare(body, source, content, model_tree):
    check(
        set(body) == {"source", "content", "required_leaf_refs"}, "Prompt shape changed"
    )
    check(body["source"] == source and body["content"] == content, "Input mismatch")
    refs = [{"kind": "text", "ref": "title"}]
    for field, kind in (("items", "text"), ("actions", "button")):
        refs.extend({"kind": kind, "ref": item["id"]} for item in content[field])
    check(refs == body["required_leaf_refs"], "Leaf manifest differs from selection")
    tree = program_stages.program_route(content)
    # The published parser rejects a changed, omitted or duplicated reference in either tree.
    for candidate in (model_tree, tree):
        model_stages.parse_output("structure", json.dumps(candidate), source, content)
    paths = {r["path"] for r in content["items"] if "path" in r}
    actions = {r["id"] for r in content["actions"]}
    extra_paths = set(source["candidate_paths"]) - paths
    extra_actions = {a["id"] for a in source["candidate_actions"]} - actions
    return {
        "paired": 1,
        "nonempty_query_in_model_prompt": int(bool(source["query"])),
        "model_prompt_has_unselected_path": int(bool(extra_paths)),
        "model_prompt_has_unselected_action": int(bool(extra_actions)),
        "model_prompt_has_either_extra": int(bool(extra_paths or extra_actions)),
        "selected_action_cards": int(bool(actions)),
        "actions_with_entity_in_selection": sum(
            "entity" in a for a in content["actions"]
        ),
        "model_has_nested_button": int(nested_button(model_tree)),
        "original_program_has_nested_button": int(nested_button(tree)),
    }


def audit(root):
    plan = json.loads(verified(root / "live/plan.json", FORMAL_PLAN))
    cases = {c["id"]: c for c in plan["assignment"]["cases"]}
    pairs = json.loads(
        verified(
            root / "same_content_l56_followup/paired187.private.json", PINS["paired187"]
        )
    )
    check(
        len({r["task"] for r in pairs}) == len(pairs) == 187 and len(cases) == 219,
        "Invalid roster",
    )
    counts = Counter()
    for row in pairs:
        task = row["task"]
        case = cases[task]
        fid = case["file_id"]
        check(fid == digest(task.encode()), "Task directory mismatch")
        package = root / "queue/package"
        request = json.loads(
            verified(package / "requests" / (fid + ".json"), case["input_sha256"])
        )
        registry = json.loads(
            verified(package / "registry" / (fid + ".json"), case["registry_sha256"])
        )
        source = trial.source_for(request, registry["data_model"])
        folder = root / "live" / fid / "L5"
        record = json.loads((folder / "outcome.json").read_bytes())
        execution = record["execution"]
        check(
            record["task"] == task
            and record["arm"] == "L5"
            and record["plan_sha256"] == FORMAL_PLAN
            and digest(canonical(execution)) == record["execution_sha256"]
            and digest(canonical(source)) == execution["source_canonical_sha256"],
            "Foreign outcome",
        )
        steps = {s["stage"]: s for s in execution["stages"]}
        content = steps["content"]["product"]
        check(
            digest(canonical(content)) == row["content_sha256"],
            "Content differs from paired study",
        )
        reply = archived(folder / "calls/structure", steps["structure"])
        user = json.loads(reply.prompt)[-1]
        prefix = "本次输入："
        check(
            user["role"] == "user" and user["content"].startswith(prefix),
            "Missing structure input",
        )
        body = json.loads(user["content"][len(prefix) :])
        tree = model_stages.parse_output(
            "structure", reply.wire.decode(), source, content
        )
        check(tree == reply.product, "Archived structure failed to reproduce")
        counts.update(compare(body, source, content, tree))
    return {
        "formal_plan_sha256": FORMAL_PLAN,
        "paired_content_receipt_sha256": PINS["paired187"],
        "counts": dict(sorted(counts.items())),
        "scope": "Original L5 versus the original L6 router given the same accepted L5 content. "
        "Nested means a button below a non-root container. These counts establish which inputs were "
        "available and which references survived, not whether a model used the extra context or a "
        "particular grouping was appropriate.",
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("formal_root", type=Path)
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    result = audit(args.formal_root)
    if args.output:
        with args.output.open("xb") as stream:
            stream.write(encode(result))
    else:
        check(
            result == json.loads(TABLE.read_bytes()),
            "Published structure input audit differs",
        )
    print("Verified", result["counts"]["paired"], "paired structure inputs")
