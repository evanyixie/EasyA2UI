"""Replay a one- or two-request repair budget on the same archived initial cards."""

import json
from collections import Counter

from six_arms.fixed_content_repeats import check
from six_arms.paired_delivery_bounds import verified

RQ2_PAIRED = "bf341baa5135848d0df1fdf86c69c670307f88608febf98b5b87d65bf0126f72"
RQ2_RECEIPT = "1352508f1fb9a3b3793bbbaa7b1b08349e8911876ec4df5909f142d3d1effc7a"


def load_comparisons(batch):
    root = batch / "rq2_followup_20261127/verification"
    receipt = json.loads(verified(root / "receipt.json", RQ2_RECEIPT))
    check(receipt["paired_sha256"] == RQ2_PAIRED, "Unmatched repair-pair roster")
    rows = json.loads(verified(root / "paired219.private.json", RQ2_PAIRED))
    check(len(rows) == len({r["id"] for r in rows}) == 219, "Invalid assignment")
    return rows


def replay(rows):
    eligible = [r for r in rows if r["model_eligibility"] == "awaiting_first_repair"]
    for r in eligible:
        rounds = r["model_rounds"]
        check(
            r["first_common"] is False and type(r["program_common"]) is bool,
            "Expected a failed initial and an assessed program repair",
        )
        check(
            [x["round"] for x in rounds] in ([1], [1, 2]), "Missing or duplicate round"
        )
        check(
            all(x["common_pass"] is False for x in rounds[:-1]),
            "Attempt after stopping",
        )
        check(
            rounds[-1]["common_pass"] is r["model_common"], "Terminal decision mismatch"
        )
        check(
            len(rounds) == 2 or rounds[-1]["common_pass"] is not False, "Missing retry"
        )
        for x in rounds:
            decision = x["common_pass"]
            check(decision is None or type(decision) is bool, "Invalid repair verdict")
            check(
                (decision is None) == (x["candidate_sha256"] is None),
                "Missing candidate evidence",
            )
            tokens = x["added_tokens"]
            check(
                tokens is None or (type(tokens) is int and tokens >= 0),
                "Invalid token receipt",
            )

    def policy(program_first, budget):
        counts = Counter()
        phases = [Counter() for _ in range(budget)]
        for r in eligible:
            passed = program_first and r["program_common"]
            if passed:
                counts["program_rescued"] += 1
            else:
                for step, x in enumerate(r["model_rounds"][:budget]):
                    current = phases[step]
                    current["request_intents"] += 1
                    passed = x["common_pass"]
                    if passed is not None:
                        current["candidate_received"] += 1
                    if passed is True:
                        current["rescued"] += 1
                    if x["added_tokens"] is not None and passed is not None:
                        current["metered_responses"] += 1
                        current["metered_tokens"] += x["added_tokens"]
            counts[
                "undetermined" if passed is None else "pass" if passed else "fail"
            ] += 1
        keys = (
            "request_intents",
            "candidate_received",
            "rescued",
            "metered_responses",
            "metered_tokens",
        )
        return {
            "eligible": len(eligible),
            "pass": counts["pass"],
            "fail": counts["fail"],
            "undetermined": counts["undetermined"],
            "program_rescued": counts["program_rescued"],
            "rounds": [{k: p[k] for k in keys} for p in phases],
            "total": {k: sum(p[k] for p in phases) for k in keys},
        }

    return {
        "assigned": len(rows),
        "eligibility_counts": dict(
            sorted(Counter(r["model_eligibility"] for r in rows).items())
        ),
        "program_only": policy(True, 0),
        **{
            f"{prefix}_budget_{n}": policy(program, n)
            for prefix, program in (("model", False), ("program_first", True))
            for n in (1, 2)
        },
        "scope": "Previously observed repair requests from the same original card. A program-first policy retains a successful program output; all other model requests start from the original card. Unknown replies remain undetermined. Tokens are the incremental metered model repair tokens, excluding the original generation.",
    }
