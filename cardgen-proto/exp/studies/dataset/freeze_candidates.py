"""按照冻结原请求、固定内容和已登记的暴露关系选择候选。输入与逐条处置表仅供保管端使用。"""

import unicodedata
from collections import Counter, defaultdict

from audit_common import digest as sig

SPLITS = ("dev", "report", "extension", "reserve")


def word(text):
    return "".join(unicodedata.normalize("NFKC", text).casefold().split())


class Families:
    def __init__(self):
        self.parents = {}

    def root(self, t):
        q = self.parents.setdefault(t, t)
        if t != q:
            self.parents[t] = self.root(q)
        return self.parents[t]

    def join(self, group):
        members = sorted({self.root(t) for t in group})
        for t in members[1:]:
            self.parents[t] = members[0]


def select_candidates(rows, locks, prior_dev):
    """locks登记一组task_ids和该组的exposure理由，含历史亲缘和补题父项。"""
    union = Families()
    exposure = defaultdict(set)
    for lock in locks:
        members = lock["task_ids"]
        if not members or not isinstance(lock["exposure"], list):
            raise ValueError("缺少亲缘或暴露登记")
        union.join(members)
        for task in members:
            exposure[task].update(lock["exposure"])
    requests, contracts, wording = defaultdict(set), defaultdict(set), defaultdict(set)
    splits = {}

    def add_wording(task, size, request):
        for field in ("originalQuery", "userQuery"):
            if request.get(field) and (text := word(request[field])):
                wording[size, text].add(task)

    for row in rows:
        tid, split, fixed = row["task_id"], row["split"], row["contract"]
        if tid in splits or not tid or split not in SPLITS or fixed["task_id"] != tid:
            raise ValueError("任务登记重复或身份不一致")
        if (
            not fixed["constraints"]["content_selection_locked"]
            or fixed["constraints"]["may_delete_content"]
        ):
            raise ValueError("内容合同必须锁定")
        splits[tid] = split
        union.root(tid)
        req = row["original_request"]
        requests[sig(req)].add(tid)
        contracts[sig({k: v for k, v in fixed.items() if k != "task_id"})].add(tid)
        add_wording(tid, fixed["size"], req)
        if split == "dev":
            exposure[tid].add("parent_release_dev")
    if not splits:
        raise ValueError("候选集为空")
    for row in prior_dev:
        tid = row["task_id"]
        union.root(tid)
        exposure[tid].add("historical_dev_input")
        add_wording(tid, row["size"], row["original_request"])
    for groups in (requests, contracts, wording):
        for ids in groups.values():
            union.join(ids)
    family_members, flags = defaultdict(set), defaultdict(set)
    for tid in sorted(union.parents):
        family_members[union.root(tid)].add(tid)
    family_ids = {
        tid: "F-" + sig(sorted(members))[:20]
        for members in family_members.values()
        for tid in members
    }
    for tid, reasons in exposure.items():
        flags[family_ids[tid]].update(reasons)
    split_sets = defaultdict(set)
    for tid, split in splits.items():
        split_sets[family_ids[tid]].add(split)
    quarantine, duplicates = {}, {}
    for tid, split in splits.items():
        fam = family_ids[tid]
        if split != "dev" and flags[fam]:
            quarantine[tid] = "exposed_family"
        elif len(split_sets[fam] - {"dev"}) > 1:
            quarantine[tid] = "cross_closed_family_requires_review"
    for group in contracts.values():
        for split in SPLITS:
            remaining = sorted(
                t for t in group if t not in quarantine and splits[t] == split
            )
            for tid in remaining[1:]:
                duplicates[tid] = remaining[0]
    dispositions = []
    for tid, split in splits.items():
        decision = (
            "quarantine_" + quarantine[tid]
            if tid in quarantine
            else "exact_duplicate_alias"
            if tid in duplicates
            else "retained"
        )
        dispositions.append(
            {
                "task_id": tid,
                "source_split": split,
                "family_id": family_ids[tid],
                "decision": decision,
                "representative": duplicates.get(tid),
                "family_exposure": sorted(flags[family_ids[tid]]),
            }
        )
    retained = [row for row in dispositions if row["decision"] == "retained"]
    retained_splits = defaultdict(set)
    for row in retained:
        retained_splits[row["family_id"]].add(row["source_split"])
    if any(len(values) != 1 for values in retained_splits.values()):
        raise ValueError("保留的家族仍横跨集合")
    counts = Counter(row["source_split"] for row in retained)
    return dispositions, {
        "source_candidates": len(splits),
        "retained": len(retained),
        "quarantined": len(quarantine),
        "exact_aliases": len(duplicates),
        "counts_by_collection": {k: counts[k] for k in SPLITS},
        "strict_historical_blind_test": False,
        "independent_human_acceptance": None,
    }
