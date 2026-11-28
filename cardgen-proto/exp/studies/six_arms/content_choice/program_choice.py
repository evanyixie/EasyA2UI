"""程序内容选择对照，版本 lexical-choice-v1。

直接接受 harness_v2.trial.source_for 的返回值。事实 ID 使用原始 JSON Pointer，
动作 ID 使用原始动作 ID。所有登记字段均可选择，包括缺值、空值和非标量值。
输出只含字段和动作。实现使用 Python 标准库，运行时不访问文件或网络。

检索比较查询与路径各级名称、标量样值、来源自带标签/描述、动作能力名或调用名。中文按
相邻双字拆词，拉丁标识支持驼峰和下划线，数字使用完整词项。按本组内逆文档频率求和，
分数同则按输入顺序。保留全部命中项，不因为尺寸删除已点名项。事实组无命中时用
标题和描述重试，再按原顺序取小卡前两项或宽卡前四项。动作仅凭查询命中保留；
仅有通用操作词且无命中时取首个登记动作。简单否定分句先排除匹配项。

本对照没有业务词表、翻译、实体推理、视觉容量测量或金标。跨语言字段名、同义词、
复杂否定和动作归属可能判断错误；原序保底是先验。此实现是新基线，原六臂的
program_route 接收已确定的内容，仓库 semantic-program-v1 的内容由模型选择。
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from math import log1p

VERSION = "lexical-choice-v1"
_HAN = r"[\u3400-\u9fff]"
_NEGATION = re.compile(
    r"不要|不需要|无需|不用|隐藏|排除|不(?:显示|展示|包含|包括|列出|提供)|"
    r"\b(?:exclude|omit|hide|without|do not (?:show|include|display))\b",
    re.IGNORECASE,
)
_ACTION_CUE = re.compile(
    r"按钮|点击|点按|操作入口|\b(?:button|tap|click)\b", re.IGNORECASE
)
_DIRECTIVE_TERMS = frozenset(
    [
        "显示",
        "展示",
        "包含",
        "包括",
        "提供",
        "按钮",
        "入口",
        "show",
        "display",
        "include",
        "with",
        "and",
        "the",
        "a",
        "an",
        "to",
        "of",
        "button",
        "click",
        "tap",
    ]
)


def _terms(text):
    if isinstance(text, (int, float, bool)):
        text = str(text)
    if not isinstance(text, str):
        return set()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text).casefold()
    result = set(re.findall(r"[a-z]+[0-9]*", text))
    result.update(
        re.findall(r"(?<![a-z0-9.])[+-]?[0-9]+(?:\.[0-9]+)?(?![a-z0-9.])", text)
    )
    for run in re.findall(_HAN + "+", text):
        if len(run) == 1:
            result.add(run)
        else:
            result.update(run[i : i + 2] for i in range(len(run) - 1))
    return result - _DIRECTIVE_TERMS


def _split_query(query):
    positive, excluded = [], []
    for clause in re.split(r"[,，;；。!！？?\n]|(?<![0-9])\.|\.(?![0-9])", query):
        parts = _NEGATION.split(clause, maxsplit=1)
        positive.append(parts[0])
        if len(parts) == 2:
            excluded.append(
                re.sub(r"^\s*(?:显示|展示|包含|包括|列出|提供)", "", parts[1])
            )
    return " ".join(positive), " ".join(excluded)


def _scalar(data, path):
    if not isinstance(path, str) or not path.startswith("/"):
        return None
    for key in path[1:].split("/"):
        key = key.replace("~1", "/").replace("~0", "~")
        if isinstance(data, dict) and key in data:
            data = data[key]
        elif isinstance(data, list) and key.isdecimal() and int(key) < len(data):
            data = data[int(key)]
        else:
            return None
    return data if isinstance(data, (str, int, float, bool)) else None


@dataclass(frozen=True)
class _Candidate:
    identifier: str
    terms: frozenset[str]


def _label_terms(value):
    if isinstance(value, dict):
        return (
            _terms(value.get("label"))
            | _terms(value.get("description"))
            | _terms(value.get("name"))
        )
    return _terms(value)


def _field_terms(source):
    """只索引共同输入中随路径明确登记的标签和说明。"""
    result = {}

    def collect(row, root=""):
        for key in (
            "field_descriptions",
            "field_labels",
            "fieldDescriptions",
            "fieldLabels",
        ):
            mapping = row.get(key)
            if not isinstance(mapping, dict):
                continue
            for pointer, metadata in mapping.items():
                if not isinstance(pointer, str):
                    continue
                path = (
                    pointer
                    if pointer.startswith(root + "/")
                    else root + "/" + pointer.lstrip("/")
                )
                result.setdefault(path, set()).update(_label_terms(metadata))

    collect(source)
    request = source.get("request", {})
    collect(request)
    for binding in request.get("candidateDataBindings", []):
        collect(binding, binding["writeResultTo"].rstrip("/"))
    return result


def _candidates(source):
    facts, actions = [], []
    field_terms = _field_terms(source)
    for path in source["candidate_paths"]:
        words = _terms(_scalar(source["sample_data"], path)) | field_terms.get(
            path, set()
        )
        for part in path.split("/"):
            if not part.isdecimal():
                words.update(_terms(part.replace("~1", "/").replace("~0", "~")))
        facts.append(_Candidate(path, frozenset(words)))
    raw_actions = {
        f"a{index}": item
        for index, item in enumerate(
            source.get("request", {}).get("candidateEventCandidates", []), 1
        )
    }
    for action in source["candidate_actions"]:
        handler = action.get("handler")
        words = (
            _label_terms(action)
            | _terms(action.get("capabilityId"))
            | _label_terms(handler)
        )
        if isinstance(handler, dict):
            words.update(_label_terms(handler.get("call")))
        words.update(_label_terms(raw_actions.get(action["id"])))
        actions.append(_Candidate(action["id"], frozenset(words)))
    return facts, actions


def _rank(candidates, terms):
    frequency = Counter(word for candidate in candidates for word in candidate.terms)
    scores = []
    for candidate in candidates:
        shared = candidate.terms & terms
        if shared:
            score = sum(
                log1p(len(candidates) / frequency[word]) for word in sorted(shared)
            )
            scores.append((score, candidate.identifier))
    scores.sort(key=lambda pair: -pair[0])
    return [identifier for score, identifier in scores]


def choose_content(source: dict) -> dict:
    """按同一份 source 选内容，返回有序且来自登记候选的 fact_ids 和 action_ids。"""
    fallback_limit = {"2x2": 2, "2x4": 4}[source["size"]]
    facts, actions = _candidates(source)
    query = source["query"]
    positive, excluded = _split_query(query)
    excluded_words = _terms(excluded)
    facts = [candidate for candidate in facts if not candidate.terms & excluded_words]
    actions = [
        candidate for candidate in actions if not candidate.terms & excluded_words
    ]
    query_words = _terms(positive)
    fact_ids = _rank(facts, query_words)
    if not fact_ids:
        context = _terms(source.get("title")) | _terms(source.get("description"))
        fact_ids = _rank(facts, context)
    if not fact_ids:
        fact_ids = [candidate.identifier for candidate in facts[:fallback_limit]]
    action_ids = _rank(actions, query_words)
    if not action_ids and actions and _ACTION_CUE.search(positive):
        action_ids = [actions[0].identifier]
    return {"fact_ids": fact_ids, "action_ids": action_ids}
