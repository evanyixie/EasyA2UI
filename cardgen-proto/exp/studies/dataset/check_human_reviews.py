"""校验 P6 网页导出的两份真人布局记录；不读取金标或推导必显项。"""

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

UNKNOWN_LAYOUTS = frozenset({"不属于14类", "无法判定", "尺寸信息不足"})
SHA256 = re.compile(r"[0-9a-f]{64}")
TARGET_COUNT = 50


@dataclass(frozen=True)
class Context:
    manifest: str
    inputs: dict[str, str]
    layouts: frozenset[str]


@dataclass
class CheckedDocument:
    errors: list[dict] = field(default_factory=list)
    answers: dict[str, dict] = field(default_factory=dict)
    reviewer: str | None = None


def sha_valid(value):
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def context_from_inputs(samples, records, manifest, catalogue):
    """以冻结样本清单、输入哈希和14类目录为依据，不读取产物内容。"""
    if not isinstance(manifest, dict) or not sha_valid(manifest.get("tree_sha256")):
        raise ValueError("expected manifest must contain a valid tree_sha256")
    if not isinstance(samples, list) or not isinstance(records, list):
        raise TypeError("expected samples and input records must be arrays")
    if not isinstance(catalogue, dict):
        raise TypeError("layout catalogue must be an object")
    labels = catalogue.get("catalogue")
    if not isinstance(labels, (list, dict)) or len(labels) != 14:
        raise ValueError("expected exactly fourteen named layout classes")
    if not all(isinstance(label, str) and label.strip() for label in labels):
        raise ValueError("layout names must be nonempty strings")
    names = frozenset(labels)
    if len(names) != 14 or names & UNKNOWN_LAYOUTS:
        raise ValueError("layout catalogue contains duplicate or reserved names")
    by_id = {}
    for record in records:
        if not isinstance(record, dict):
            raise TypeError("input record must be an object")
        identity = record.get("case_id")
        input_sha = record.get("input_sha256")
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("input case_id must be a nonempty string")
        if identity in by_id or not sha_valid(input_sha):
            raise ValueError("input case ID repeated or SHA256 invalid")
        by_id[identity] = input_sha
    selected = {}
    for sample in samples:
        if not isinstance(sample, dict):
            raise TypeError("expected sample must be an object")
        identity = sample.get("case_id")
        if not isinstance(identity, str):
            raise TypeError("sample case_id must be a string")
        if identity not in by_id or identity in selected:
            raise ValueError("sample case ID unknown or repeated")
        selected[identity] = by_id[identity]
    if len(selected) != TARGET_COUNT:
        raise ValueError("expected exactly fifty distinct selected cases")
    return Context(manifest["tree_sha256"], selected, names | UNKNOWN_LAYOUTS)


def check_document(document, mode, context):
    result = CheckedDocument()
    if not isinstance(document, dict):
        result.errors.append({"code": "DOCUMENT_NOT_OBJECT", "mode": mode})
        return result
    for key, expected in (
        ("version", "human-review-v1"),
        ("mode", mode),
        ("manifest", context.manifest),
    ):
        if document.get(key) != expected:
            result.errors.append(
                {"code": "DOCUMENT_FIELD_MISMATCH", "mode": mode, "field": key}
            )
    answers = document.get("answers")
    if not isinstance(answers, list):
        result.errors.append({"code": "ANSWERS_NOT_LIST", "mode": mode})
        return result
    if len(answers) != TARGET_COUNT:
        result.errors.append(
            {
                "code": "ANSWER_COUNT_MISMATCH",
                "mode": mode,
                "actual": len(answers),
            }
        )
    reviewers = set()
    for answer in answers:
        if not isinstance(answer, dict):
            result.errors.append({"code": "ANSWER_NOT_OBJECT", "mode": mode})
            continue
        identity = answer.get("case_id")
        if not isinstance(identity, str) or identity not in context.inputs:
            result.errors.append({"code": "CASE_ID_NOT_EXPECTED", "mode": mode})
            continue
        if identity in result.answers:
            result.errors.append(
                {"code": "DUPLICATE_CASE_ID", "mode": mode, "case_id": identity}
            )
            continue
        result.answers[identity] = answer
        for key, expected in (
            ("input_sha256", context.inputs[identity]),
            ("audit_mode", mode),
            ("manifest", context.manifest),
        ):
            if answer.get(key) != expected:
                result.errors.append(
                    {
                        "code": "ANSWER_FIELD_MISMATCH",
                        "mode": mode,
                        "case_id": identity,
                        "field": key,
                    }
                )
        reviewer = answer.get("reviewer")
        if not isinstance(reviewer, str) or not reviewer.strip():
            result.errors.append(
                {"code": "REVIEWER_MISSING", "mode": mode, "case_id": identity}
            )
        else:
            reviewers.add(reviewer.strip())
        layout = answer.get("human_layout")
        if not isinstance(layout, str) or layout not in context.layouts:
            result.errors.append(
                {
                    "code": "LAYOUT_UNFILLED_OR_UNKNOWN",
                    "mode": mode,
                    "case_id": identity,
                }
            )
    if set(result.answers) != set(context.inputs):
        result.errors.append({"code": "CASE_SET_MISMATCH", "mode": mode})
    if len(reviewers) == 1:
        result.reviewer = next(iter(reviewers))
    else:
        result.errors.append({"code": "REVIEWER_NOT_SINGLE", "mode": mode})
    return result


def cohens_kappa(left, right):
    """未知类也计入列联表；退化情形不伪造κ=1。"""
    if len(left) != len(right) or not left:
        raise ValueError("kappa requires nonempty paired labels of equal length")
    count = len(left)
    left_counts = Counter(left)
    right_counts = Counter(right)
    labels = sorted(set(left_counts) | set(right_counts))
    agreement = sum(a == b for a, b in zip(left, right, strict=True))
    observed = Fraction(agreement, count)
    expected = Fraction(
        sum(left_counts[label] * right_counts[label] for label in labels), count * count
    )
    coefficient = None if expected == 1 else (observed - expected) / (1 - expected)
    confusion = Counter(zip(left, right, strict=True))
    pairs = []
    for (a, b), frequency in sorted(confusion.items()):
        pairs.append({"a": a, "b": b, "count": frequency})
    return {
        "n": count,
        "observed_agreement": float(observed),
        "expected_agreement": float(expected),
        "kappa": None if coefficient is None else float(coefficient),
        "undefined_reason": "EXPECTED_AGREEMENT_EQUALS_ONE"
        if coefficient is None
        else None,
        "threshold": 0.9,
        "threshold_pass": coefficient is not None and coefficient >= Fraction(9, 10),
        "included_labels": labels,
        "confusion_pairs": pairs,
    }


def check_reviews(left, right, context):
    first = check_document(left, "p6-layout-a", context)
    second = check_document(right, "p6-layout-b", context)
    errors = [*first.errors, *second.errors]
    if first.reviewer is not None and first.reviewer == second.reviewer:
        errors.append({"code": "SAME_REVIEWER"})
    agreement = None
    if not errors:
        identities = sorted(context.inputs)
        labels_a = [first.answers[identity]["human_layout"] for identity in identities]
        labels_b = [second.answers[identity]["human_layout"] for identity in identities]
        agreement = cohens_kappa(labels_a, labels_b)
    passed = agreement is not None and agreement["threshold_pass"]
    return {
        "status": "INVALID_REVIEW_DOCUMENTS" if errors else "VALID_REVIEW_DOCUMENTS",
        "errors": errors,
        "manifest": context.manifest,
        "expected_count": TARGET_COUNT,
        "documents_valid": not errors,
        "reviewer_a": first.reviewer,
        "reviewer_b": second.reviewer,
        "agreement": agreement,
        "layout_agreement_pass": passed,
        "p4_accuracy": {"status": "PENDING_INDEPENDENT_ADJUDICATION", "value": None},
        "p6_complete": False,
        "human_answers_generated": False,
        "identity_and_independence": "Signatures checked only; real identity and "
        "independent work require human confirmation.",
        "limits": "No gold labels, majority vote or required-item answers were inferred. "
        "Valid documents do not complete P6 gold review, P7 or P8.",
    }


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text("utf-8-sig"), object_pairs_hook=unique_object)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "review-a",
        "review-b",
        "expected-samples",
        "records",
        "manifest",
        "catalogue",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    records = []
    for line in args.records.read_text("utf-8-sig").splitlines():
        if line.strip():
            records.append(json.loads(line, object_pairs_hook=unique_object))
    context = context_from_inputs(
        read_json(args.expected_samples),
        records,
        read_json(args.manifest),
        read_json(args.catalogue),
    )
    result = check_reviews(read_json(args.review_a), read_json(args.review_b), context)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf8") as stream:
        public = {
            key: result[key]
            for key in (
                "status",
                "documents_valid",
                "expected_count",
                "agreement",
                "layout_agreement_pass",
                "p4_accuracy",
                "p6_complete",
            )
        }
        public["error_counts"] = dict(
            Counter(error["code"] for error in result["errors"])
        )
        stream.write(json.dumps(public, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "layout_agreement_pass": result["layout_agreement_pass"],
                "p6_complete": False,
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["layout_agreement_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
