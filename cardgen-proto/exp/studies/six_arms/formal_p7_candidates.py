"""Audit P7 question packages against frozen requests and first-stage model inputs."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from six_arms.fixed_content_repeats import FORMAL_PLAN, check, digest
from six_arms.harness_v2 import model_stages, trial
from six_arms.paired_delivery_bounds import verified

ROLES = {"P7-all-A": 219, "P7-double-B": 20}
ADMIN = {
    "original": "9c021641706a91f8035f48ebe44296f9a0c3606870c783198932f1944f322810",
    "revised": "f2b9b567f68ae569e1826465eb5acc94615ec472d62c721260ff4280f5cf3077",
}
HANDOFF = {
    "P7-all-A": "85b1d45325b2497348c60b174b44bc325c2ce51ffc823ae784033a823053231b",
    "P7-double-B": "c658edb3d47a425528b78566018f334dc5183f3b0877f13e98c099b5a79a34f7",
}
FILES = ("questions.json", "开始审核.html")
TABLE = (
    Path(__file__).resolve().parents[4] / "paper/out/tables/formal_p7_candidates.json"
)


def embedded(html):
    text = html.decode("utf-8-sig")
    marker = "const p="
    check(text.count(marker) == 1, "Ambiguous embedded packet")
    packet, end = json.JSONDecoder().raw_decode(text, text.index(marker) + len(marker))
    check(text[end:].startswith(";"), "Invalid end of question data")
    return packet


def load_packet(folder, admin, role, archive=None):
    parts = {
        name: verified(
            folder / role / name, admin["package_file_sha256"][f"{role}/{name}"]
        )
        for name in FILES
    }
    if archive:
        from io import BytesIO

        with ZipFile(BytesIO(verified(archive, HANDOFF[role]))) as z:
            check(sorted(z.namelist()) == sorted(FILES), "Unexpected handoff members")
            check(
                all(z.read(n) == data for n, data in parts.items()),
                "Handoff differs from study package",
            )
    packet = json.loads(parts[FILES[0]])
    key = admin["packets"][role]
    check(embedded(parts[FILES[1]]) == packet, "HTML differs from question JSON")
    check(
        packet["role"] == role
        and packet["version"] == key["version"]
        and packet["mode"] == "must",
        "Wrong questionnaire",
    )
    mapping = key["blind_to_task"]
    rows = {mapping[c["id"]]: c for c in packet["cases"]}
    check(
        len(rows) == len(mapping) == len(packet["cases"]) == ROLES[role]
        and {c["id"] for c in rows.values()} == set(mapping),
        "Incomplete or duplicated question map",
    )
    return rows, {n: digest(data) for n, data in parts.items()}


def compare_question(case, source):
    raw = source["request"]
    display = case["request"]
    choices = case["choices"]
    ids = [key for key, _ in choices]
    check(len(set(ids)) == len(ids), "Duplicate checkbox identity")
    check(
        all(
            isinstance(val, str) and val and key.startswith(("D", "F", "A"))
            for key, val in choices
        ),
        "Unknown choice type",
    )
    facts = [v for k, v in choices if not k.startswith("A")]
    actions = [(k, v) for k, v in choices if k.startswith("A")]
    expected = source["candidate_paths"]
    expected_actions = [
        (a["id"].upper(), a["capabilityId"]) for a in source["candidate_actions"]
    ]
    missing = set(expected) - set(facts)
    extra = set(facts) - set(expected)
    same = not missing and not extra
    return {
        "tasks": 1,
        "field_choices": len(facts),
        "action_choices": len(actions),
        "missing_fields": len(missing),
        "extra_fields": len(extra),
        "duplicate_field_choices": len(facts) - len(set(facts)),
        "duplicate_registered_fields_in_flat_list": len(expected) - len(set(expected)),
        "tasks_with_same_field_set": int(same),
        "tasks_with_same_field_sequence": int(facts == expected),
        "tasks_same_field_set_different_order": int(same and facts != expected),
        "tasks_same_action_id_and_capability_multiset": int(
            Counter(actions) == Counter(expected_actions)
        ),
        "tasks_same_action_id_and_capability_order": int(actions == expected_actions),
        "tasks_same_full_ordered_action_definitions": int(
            display.get("candidateEventCandidates", [])
            == raw.get("candidateEventCandidates", [])
        ),
        "tasks_same_original_query_user_query_and_size": int(
            all(
                display.get(k) == raw.get(k)
                for k in ("originalQuery", "userQuery", "size")
            )
        ),
        "tasks_same_expandable_binding_definitions": int(
            display.get("candidateDataBindings", [])
            == raw.get("candidateDataBindings", [])
        ),
        "tasks_with_added_fields_shown_after_an_action": int(
            any(
                k.startswith("F")
                for k in ids[
                    next(
                        (i for i, k in enumerate(ids) if k.startswith("A")), len(ids)
                    ) :
                ]
            )
        ),
    }


def public_stats(rows, sources):
    counts = Counter()
    for task, case in rows.items():
        counts.update(compare_question(case, sources[task]))
    return dict(counts)


def overlap(large, small):
    check(small.keys() <= large.keys(), "Overlap outside formal A")
    return {
        "tasks": len(small),
        "same_checkbox_ids_values_and_order": sum(
            c["choices"] == large[t]["choices"] for t, c in small.items()
        ),
        "same_request_details": sum(
            c["request"] == large[t]["request"] for t, c in small.items()
        ),
    }


def archived_inputs(batch):
    plan = json.loads(verified(batch / "live/plan.json", FORMAL_PLAN))
    sources = {}
    seen_intents, provider_ids = set(), set()
    summary = {arm: Counter() for arm in (f"L{i}" for i in range(1, 7))}
    common_users = 0
    for c in plan["assignment"]["cases"]:
        name = c["file_id"] + ".json"
        req = json.loads(
            verified(batch / "queue/package/requests" / name, c["input_sha256"])
        )
        registry = json.loads(
            verified(batch / "queue/package/registry" / name, c["registry_sha256"])
        )
        source = trial.source_for(req, registry["data_model"])
        tid = c["id"]
        check(tid not in sources, "Duplicate formal task")
        sources[tid] = source
        user_texts = set()
        for arm, counts in summary.items():
            phase = "one_shot" if arm == "L1" else "content"
            folder = batch / "live" / c["file_id"] / arm / "calls" / phase
            seal = json.loads((folder / "seal.json").read_bytes())
            intent = json.loads((folder / "intent.json").read_bytes())
            check(
                seal["stage"] == intent["stage"] == phase
                and seal["local_request_id"] == intent["local_request_id"]
                and intent["local_request_id"] not in seen_intents,
                "Request identity mismatch",
            )
            seen_intents.add(intent["local_request_id"])
            check(
                intent["messages_sha256"] == seal["messages_sha256"],
                "Input seal differs",
            )
            messages = json.loads(
                verified(folder / "messages.json", seal["messages_sha256"])
            )
            call = json.loads(verified(folder / "call.json", seal["receipt_sha256"]))
            check(
                call["stage"] == phase
                and messages == model_stages.build_messages(phase, source),
                "Frozen input or stage differs",
            )
            user_texts.add(messages[1]["content"])
            counts["verified_request_messages"] += 1
            counts["status_200"] += call.get("http_status") == 200
            counts["no_http_status"] += call.get("http_status") is None
            counts["other_http_status"] += call.get("http_status") not in (200, None)
            if call.get("request_id"):
                check(
                    call["request_id"] not in provider_ids,
                    "Repeated provider request ID",
                )
                provider_ids.add(call["request_id"])
                counts["provider_id_present"] += 1
        common_users += len(user_texts) == 1
    check(len(sources) == 219, "Wrong formal allocation")
    return sources, {
        "by_arm": summary,
        "same_user_message_across_all_six_arms_tasks": common_users,
    }


def audit(batch, vault):
    sources, sent = archived_inputs(batch)
    paths = {
        "original": vault / "paper_independent_review_v1/formal",
        "revised": batch / "review/P7正式/formal",
    }
    result = {
        "formal_plan_sha256": FORMAL_PLAN,
        "model_inputs": sent,
        "packet_revisions": {},
    }
    versions = {}
    for revision, folder in paths.items():
        admin = json.loads(verified(folder / "admin.json", ADMIN[revision]))
        versions[revision] = {}
        entry = {"admin_sha256": ADMIN[revision], "roles": {}}
        for role in ROLES:
            archive = (
                batch / "review_handoff_20261127/packets/input" / (role + ".zip")
                if revision == "revised"
                else None
            )
            cases, hashes = load_packet(folder, admin, role, archive)
            check(cases.keys() <= sources.keys(), "Unknown task in question set")
            versions[revision][role] = cases
            entry["roles"][role] = {
                "counts": public_stats(cases, sources),
                "file_sha256": hashes,
                "handoff_zip_sha256": HANDOFF[role] if archive else None,
            }
        entry["within_revision_overlap"] = overlap(
            *[versions[revision][role] for role in ROLES]
        )
        result["packet_revisions"][revision] = entry
    changes = {}
    for role in ROLES:
        old, new = (versions[k][role] for k in ("original", "revised"))
        check(old.keys() == new.keys(), "Revised roster differs")
        additions = Counter()
        for tid, c in old.items():
            replacement = new[tid]
            check(
                c["id"] == replacement["id"] and c["request"] == replacement["request"],
                "Revised original context or blind ID changed",
            )
            prior = c["choices"]
            check(
                replacement["choices"][: len(prior)] == prior,
                "Original checkbox moved or replaced",
            )
            extra = replacement["choices"][len(prior) :]
            check(
                all(k.startswith("F") for k, _ in extra), "Unexpected added candidate"
            )
            additions[len(extra)] += 1
        changes[role] = {
            "added_field_count_to_task_count": dict(sorted(additions.items()))
        }
    result["question_revision"] = changes
    result["scope"] = (
        "L1 is a direct end-product request. L2–L6 have a distinct content request. "
        "The verified first-stage messages show the registered fields, samples and action definitions supplied; "
        "transport without a provider acknowledgement does not establish provider receipt. No model replies or human answers are read. "
        "Checkbox action labels name the capability. Full handler arguments are in the expandable request. "
        "Handoff archives establish the prepared version, not distribution or human completion."
    )
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("batch", type=Path)
    p.add_argument("vault", type=Path)
    p.add_argument(
        "--output",
        type=Path,
        help="Create a new anonymous JSON table; otherwise verify the committed table",
    )
    a = p.parse_args()
    summary = audit(a.batch, a.vault)
    if a.output:
        with a.output.open("x", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
    else:
        check(
            json.loads(TABLE.read_bytes()) == json.loads(json.dumps(summary)),
            "Published aggregate differs",
        )
