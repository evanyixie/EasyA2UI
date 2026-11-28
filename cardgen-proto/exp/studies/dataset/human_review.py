"""离线人审包生成、独立回收及统计。管理映射永远不进入评审包。"""

import argparse
import datetime as dt
import hashlib
import hmac
import json
import secrets
import shutil
import tempfile
from collections import Counter
from pathlib import Path

from audit_common import private_destination

LOCAL = Path(__file__).resolve().parent
SEED = "genui-layout-review-v1-preoutcome"
STAGES = {"calibration", "formal"}
RATINGS = {"符合", "不符合", "证据不足"}
UNKNOWN = ["不属于14类", "无法判定", "尺寸信息不足"]


def unique_pairs(items):
    result = {}
    for k, v in items:
        if k in result:
            raise ValueError("JSON重复键")
        result[k] = v
    return result


def load(path):
    return json.loads(
        path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_pairs
    )


def jsonl(path):
    return [
        json.loads(x, object_pairs_hook=unique_pairs)
        for x in path.read_text(encoding="utf-8-sig").splitlines()
        if x
    ]


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )


def hashfile(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(obj):
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def ordered(ids, tag):
    return sorted(ids, key=lambda i: digest([SEED, tag, i]))


def keycode(secret, tag, tid):
    return hmac.new(secret, (tag + ":" + tid).encode(), hashlib.sha256).hexdigest()[:16]


def secret_key(root):
    key = root / "admin" / "blind_key.bin"
    key.parent.mkdir(parents=True, exist_ok=True)
    if not key.exists():
        with key.open("xb") as stream:
            stream.write(secrets.token_bytes(32))
    return key.read_bytes()


def source_fields(req):
    keep = (
        "originalQuery",
        "userQuery",
        "size",
        "candidateDataBindings",
        "candidateEventCandidates",
        "dataCapabilityIds",
        "dataCapabilityParams",
        "dataCapabilitySchemas",
        "eventCapabilityIds",
    )
    clean = {k: req[k] for k in keep if k in req}
    if not (clean.get("originalQuery") or clean.get("userQuery")):
        # 只有原请求提供标题/描述而无提问的情况，显式注明来源。
        for k in ("title", "description"):
            if k in req:
                clean[k] = req[k]
    return clean


def choices(req):
    opts = []
    for j, b in enumerate(req.get("candidateDataBindings", []) or []):
        for k, field in enumerate(b.get("candidateOutputFields", []) or []):
            path = b.get("writeResultTo", "").rstrip("/") + "/" + field.lstrip("/")
            opts.append([f"D{j + 1}.{k + 1}", path])
    for i, action in enumerate(req.get("candidateEventCandidates", []) or []):
        opts.append(
            [f"A{i + 1}", action.get("capabilityId") or "动作候选" + str(i + 1)]
        )
    return opts


def draw(stage, source, split, ids):
    reqs = {
        r["task_id"]: r["original_request"]
        for r in jsonl(source / split / "requests_for_review.jsonl")
    }
    sizes = {
        r["task_id"]: r["size"] for r in jsonl(source / split / "case_index.jsonl")
    }
    if not (set(reqs) == ids == set(sizes)):
        raise ValueError("冻结人审材料的完整性检查失败")
    if stage == "calibration":
        small = ordered([k for k in ids if sizes[k] == "2x2"], "trial-small")[:5]
        wide = ordered([k for k in ids if sizes[k] == "2x4"], "trial-wide")[:5]
        if not (len(set(small + wide)) == 10):
            raise ValueError("冻结人审材料的完整性检查失败")
        return reqs, {"P7-trial-A": small + wide, "P7-trial-B": small + wide}
    if not (len(ids) >= 50):
        raise ValueError("冻结人审材料的完整性检查失败")
    layout = ordered(ids, "P6-layout")[:50]
    return reqs, {
        "P7-all-A": sorted(ids),
        "P7-double-B": ordered(ids, "P7-double")[:20],
        "P6-layout-A": layout,
        "P6-layout-B": layout,
        "P6-gold": ordered(ids, "P6-gold")[:50],
    }


def generate(stage, root, source, owner=None, catalogue=None):
    root = root.resolve()
    private_destination(root / "admin" / "blind_key.bin", input_package=source)
    private_destination(root / stage, input_package=source)
    root.mkdir(parents=True, exist_ok=True)
    split = "dev" if stage == "calibration" else "report"
    source_sha = hashfile(source / split / "layout_inputs.jsonl")
    req_sha = hashfile(source / split / "requests_for_review.jsonl")
    ids = {row["task_id"] for row in jsonl(source / split / "case_index.jsonl")}
    reqs, work = draw(stage, source, split, ids)
    if stage == "formal":
        if owner is None or catalogue is None:
            raise ValueError("正式包需指定保管区与布局目录")
        refs = {x["task_id"]: x for x in jsonl(owner / "answer_index.jsonl")}
        reference_root = Path(load(owner / "source.json")["private_reference_root"])
        if not reference_root.is_absolute():
            reference_root = owner / reference_root
        ref_manifest = load(reference_root / "manifest.json")["outputs"]
    secret = secret_key(root)
    dest = root / stage
    if dest.exists():
        prev = load(dest / "admin.json")
        if (
            prev["layout_input_sha256"] != source_sha
            or prev["original_request_sha256"] != req_sha
        ):
            raise ValueError("输入已变化，另建新版本")
        for name, expected in prev["package_file_sha256"].items():
            if not (hashfile(dest / name) == expected):
                raise ValueError("冻结人审材料的完整性检查失败")
        return
    layouts = load(catalogue)["catalogue"] + UNKNOWN if stage == "formal" else []
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        staged = Path(tmp) / stage
        staged.mkdir()
        manager = {
            "stage": stage,
            "sampling_seed": SEED,
            "source_split": split,
            "layout_input_sha256": source_sha,
            "original_request_sha256": req_sha,
            "known_human_submissions_at_build": None,
            "packets": {},
        }
        for role, assignments in work.items():
            folder = staged / role
            folder.mkdir()
            blind_map = {keycode(secret, role, tid): tid for tid in assignments}
            if not (len(blind_map) == len(assignments)):
                raise ValueError("冻结人审材料的完整性检查失败")
            # 各人试卷采用互不相同的编号和顺序。
            cases = []
            for blind, tid in sorted(blind_map.items()):
                mode = (
                    "must"
                    if role.startswith("P7")
                    else ("gold" if role == "P6-gold" else "layout")
                )
                record = {"id": blind}
                req = source_fields(reqs[tid])
                if mode != "layout":
                    record["request"] = req
                if mode == "must":
                    record["choices"] = choices(req)
                else:
                    ref = refs[tid]
                    primary = min(ref["references"], key=lambda x: x["reference_id"])
                    source_folder = reference_root / ref["collection"] / primary["path"]
                    names = (
                        ("screenshot.png",)
                        if mode == "layout"
                        else ("screenshot.png", "compact.jsonl", "a2ui.jsonl")
                    )
                    for name in names:
                        src = (source_folder / name).resolve()
                        if not src.is_relative_to(reference_root.resolve()):
                            raise ValueError("参考文件越出冻结目录")
                        dst = folder / "items" / blind / name
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(src, dst)
                        if not (
                            hashfile(dst)
                            == ref_manifest[
                                src.relative_to(reference_root.resolve()).as_posix()
                            ]
                        ):
                            raise ValueError("冻结人审材料的完整性检查失败")
                    record["assets"] = [f"items/{blind}/{n}" for n in names]
                cases.append(record)
            packet = {
                "role": role,
                "mode": mode,
                "cases": cases,
                "layout_classes": layouts if mode == "layout" else [],
            }
            packet["version"] = digest([source_sha, req_sha, role, cases])
            save(folder / "questions.json", packet)
            template = (LOCAL / "form.html").read_text(encoding="utf8")
            payload = json.dumps(packet, ensure_ascii=False).replace("<", "\\u003c")
            (folder / "开始审核.html").write_text(
                template.replace("/*PACKET*/", payload), encoding="utf8"
            )
            manager["packets"][role] = {
                "version": packet["version"],
                "blind_to_task": blind_map,
            }
        manager["package_file_sha256"] = {
            p.relative_to(staged).as_posix(): hashfile(p)
            for p in sorted(staged.rglob("*"))
            if p.is_file()
        }
        save(staged / "admin.json", manager)
        staged.rename(dest)


P7_TEXT_FIELDS = ("originalQuery", "userQuery", "title", "description")


def checked_p7_answer(answer, case):
    """Return the comparable selection, preserving each quoted fragment verbatim."""
    if not isinstance(answer, dict) or not isinstance(case, dict):
        raise TypeError("A P7 answer and its frozen question are required")
    request = case.get("request")
    choices = case.get("choices")
    if not isinstance(request, dict) or not isinstance(choices, list):
        raise TypeError("Missing frozen request or candidate list")
    candidate_ids = set()
    for choice in choices:
        if (
            not isinstance(choice, (list, tuple))
            or len(choice) != 2
            or not isinstance(choice[0], str)
            or not choice[0]
            or choice[0] in candidate_ids
        ):
            raise ValueError("Invalid or ambiguous frozen candidate")
        candidate_ids.add(choice[0])

    must, literals = answer.get("must"), answer.get("literal")
    for items in (must, literals):
        if (
            not isinstance(items, list)
            or not all(isinstance(item, str) and item.strip() for item in items)
            or len(items) != len(set(items))
        ):
            raise ValueError("P7 selections must contain unique, nonblank strings")
    if not set(must) <= candidate_ids:
        raise ValueError("Unknown P7 candidate")
    # The form saves one fragment per line. A field boundary, a candidate label
    # or an annotator's explanation cannot supply the quoted request text.
    texts = [request[k] for k in P7_TEXT_FIELDS if isinstance(request.get(k), str)]
    for fragment in literals:
        if (
            "\n" in fragment
            or "\r" in fragment
            or not any(fragment in text for text in texts)
        ):
            raise ValueError("A P7 literal must quote one line of the request verbatim")

    state, note = answer.get("state"), answer.get("note", "")
    if (
        state not in ("已判定", "无必显项", "证据不足")
        or (state == "已判定") != bool(must or literals)
        or not isinstance(note, str)
        or (state != "已判定" and not note.strip())
    ):
        raise ValueError("Inconsistent P7 decision or missing explanation")
    return {"state": state, "must": sorted(must), "literal": sorted(literals)}


def checked_submission(stage_dir, role, obj):
    manager = load(stage_dir / "admin.json")
    questions_path = stage_dir / role / "questions.json"
    expected_sha = manager["package_file_sha256"][f"{role}/questions.json"]
    if hashfile(questions_path) != expected_sha:
        raise ValueError("题面文件与冻结清单不一致")
    q = load(questions_path)
    if (
        obj.get("role") != role
        or obj.get("version") != manager["packets"][role]["version"]
    ):
        raise ValueError("角色或冻结版本不符")
    if (
        not isinstance(obj.get("reviewer"), str)
        or not obj["reviewer"].strip()
        or obj.get("independent") is not True
    ):
        raise ValueError("缺独立评审身份或声明")
    try:
        stamped = dt.datetime.fromisoformat(obj["submitted_at"].replace("Z", "+00:00"))
        if not (stamped.tzinfo is not None):
            raise ValueError("冻结人审材料的完整性检查失败")
    except (ValueError, KeyError, TypeError, AssertionError):
        raise ValueError("缺带时区的提交时间") from None
    expected = {row["id"]: row for row in q["cases"]}
    answers = obj["answers"]
    if not isinstance(answers, dict) or set(answers) != set(expected):
        raise ValueError("未覆盖全包或含未知题")
    result = {}
    for blind, a in answers.items():
        ref = expected[blind]
        if not isinstance(a, dict):
            raise TypeError("答案结构有误")
        if q["mode"] == "must":
            checked_p7_answer(a, ref)
        elif q["mode"] == "layout":
            if a.get("layout") not in q["layout_classes"]:
                raise ValueError("缺合法布局判定")
            if a["layout"] in UNKNOWN and not a.get("note", "").strip():
                raise ValueError("需说明未知原因")
        else:
            if any(a.get(k) not in RATINGS for k in ("protocol", "content", "binding")):
                raise ValueError("金标三项未评完")
            if (
                any(a[k] != "符合" for k in ("protocol", "content", "binding"))
                and not a.get("note", "").strip()
            ):
                raise ValueError("缺错误/未知依据")
        result[manager["packets"][role]["blind_to_task"][blind]] = a
    return obj["reviewer"].strip().casefold(), result


def kappa(pairs):
    if not pairs:
        return None
    a, b = map(Counter, zip(*pairs, strict=True))
    n = len(pairs)
    agreed = sum(x == y for x, y in pairs)
    expected = sum(count * b[label] for label, count in a.items())
    return None if n * n == expected else (agreed * n - expected) / (n * n - expected)


def score(stage, inbox, root):
    folder = root / stage
    roles = load(folder / "admin.json")["packets"]
    result = {
        "stage": stage,
        "submitted": {},
        "missing": [],
        "P7": None,
        "P6_layout": None,
        "P6_gold": None,
    }
    all_results = {}
    for role in roles:
        path = inbox / (role + ".json")
        if not path.is_file():
            result["missing"].append(role)
            continue
        name, answers = checked_submission(folder, role, load(path))
        result["submitted"][role] = {
            "reviewed": len(answers),
        }
        all_results[role] = (name, answers)
    for mode, role_a, role_b in [
        ("must", "P7-trial-A", "P7-trial-B"),
        ("must", "P7-all-A", "P7-double-B"),
        ("layout", "P6-layout-A", "P6-layout-B"),
    ]:
        if role_a not in all_results or role_b not in all_results:
            continue
        name, a = all_results[role_a]
        other, b = all_results[role_b]
        if name == other:
            raise ValueError("不能同一人担任两个独立评审")
        overlap = sorted(set(a) & set(b))
        if mode == "layout":
            pairs = [(a[k]["layout"], b[k]["layout"]) for k in overlap]
            coef = kappa(pairs)
            result["P6_layout"] = {
                "n": len(pairs),
                "kappa": coef,
                "kappa_pass": None if coef is None else coef >= 0.9,
                "agreement_n": sum(x == y for x, y in pairs),
                "unknown_ratings": sum(x in UNKNOWN for pair in pairs for x in pair),
            }
        else:
            exact = 0
            usable = 0
            score_sum = 0
            for k in overlap:
                if "证据不足" in (a[k]["state"], b[k]["state"]):
                    continue
                sets = [
                    set(r["must"]) | {"原文:" + s for s in r["literal"]}
                    for r in (a[k], b[k])
                ]
                left, right = sets
                usable += 1
                exact += left == right
                score_sum += (
                    len(left & right) / len(left | right) if left | right else 1
                )
            result["P7"] = {
                "paired_n": len(overlap),
                "scorable_n": usable,
                "unresolved_n": len(overlap) - usable,
                "exact_n": exact,
                "exact_rate": exact / usable if usable else None,
                "mean_card_jaccard": score_sum / usable if usable else None,
            }
    if "P6-gold" in all_results:
        cards = all_results["P6-gold"][1]
        n = len(cards)
        bad = unk = 0
        for val in cards.values():
            hits = {val[k] for k in ("protocol", "content", "binding")}
            bad += int("不符合" in hits)
            unk += int("不符合" not in hits and "证据不足" in hits)
        result["P6_gold"] = {
            "n": n,
            "defective_cards": bad,
            "unresolved_cards": unk,
            "rate_on_all_if_every_unknown_passes": bad / n,
            "rate_on_all_if_every_unknown_fails": (bad + unk) / n,
            "disclose_above_2_percent": True
            if bad / n > 0.02
            else False
            if (bad + unk) / n <= 0.02
            else None,
        }
    return result


def main():
    px = argparse.ArgumentParser()
    px.add_argument("action", choices=["build", "check"])
    px.add_argument("stage", choices=sorted(STAGES))
    px.add_argument("--inbox", type=Path)
    px.add_argument("--out", type=Path)
    px.add_argument("--root", type=Path, required=True, help="私有评审工作目录")
    px.add_argument("--source", type=Path, help="冻结候选包")
    px.add_argument("--owner", type=Path, help="正式材料的保管目录")
    px.add_argument("--catalogue", type=Path, help="冻结的布局类别目录")
    a = px.parse_args()
    if a.action == "build":
        if a.source is None:
            px.error("build 需要 --source")
        generate(a.stage, a.root, a.source, a.owner, a.catalogue)
        return
    info = score(a.stage, a.inbox or a.root / "locked_returns" / a.stage, a.root)
    if a.out:
        if a.out.exists():
            raise FileExistsError("不能覆盖已收件结果")
        save(a.out, info)
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
