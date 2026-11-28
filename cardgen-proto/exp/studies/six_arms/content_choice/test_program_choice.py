"""程序臂的虚构单元测试；无需读取试验、样本、金标或历史模型结果。"""

from copy import deepcopy

from .program_choice import choose_content


def make_source(query, fields, actions=(), *, size="2x2"):
    return {
        "query": query,
        "size": size,
        "title": "",
        "description": "",
        "request": {},
        "candidate_paths": ["/pool/" + key for key in fields],
        "sample_data": {"pool": fields},
        "candidate_actions": list(actions),
    }


def test_literal_selection_and_action_negation():
    source = make_source(
        "显示展厅、场次，不要显示地址。点击收藏，隐藏导出。",
        {"场次": 3, "地址": "西岸", "展厅": "北厅"},
        [{"id": "a9", "label": "导出"}, {"id": "a8", "label": "收藏"}],
    )
    original = deepcopy(source)
    assert choose_content(source) == {
        "fact_ids": ["/pool/场次", "/pool/展厅"],
        "action_ids": ["a8"],
    }
    assert source == original


def test_english_camel_case_and_numeric_sample():
    source = make_source(
        "show refraction and 19.25, exclude slope",
        {"slope": 19.25, "windRefraction": 2, "distance": 19.25, "ref": 9},
    )
    assert choose_content(source)["fact_ids"] == [
        "/pool/windRefraction",
        "/pool/distance",
    ]


def test_uses_scalar_evidence_without_inventing_unregistered_paths():
    source = make_source("显示北厅", {})
    source["sample_data"] = {
        "a/b": [{"~": "北厅"}],
        "absent": None,
        "empty": " ",
        "外部": "北厅",
    }
    source["candidate_paths"] = ["/a~1b", "/a~1b/3", "/absent", "/empty", "/a~1b/0/~0"]
    assert choose_content(source) == {"fact_ids": ["/a~1b/0/~0"], "action_ids": []}


def test_registered_paths_available_independent_of_shape_and_first_frame():
    source = make_source(
        "show group, empty, missing and array",
        {"alpha": "x", "empty": "", "array": [1], "group": {"nested": "value"}},
    )
    source["candidate_paths"].append("/pool/missing")
    assert choose_content(source)["fact_ids"] == [
        "/pool/empty",
        "/pool/array",
        "/pool/group",
        "/pool/missing",
    ]


def test_field_descriptions_parent_paths_raw_action_labels_and_calls():
    source = make_source(
        "显示转速和层级，点击锁定、export",
        {},
        [
            {"id": "a1", "label": "控制器", "handler": {"call": "ApplyCurrent"}},
            {"id": "a2", "handler": {"call": "exportSnapshot"}},
            {"id": "a3", "label": "分享"},
        ],
    )
    source["candidate_paths"] = ["/obj/rate", "/层级/key", "/aux/none"]
    source["request"] = {
        "candidateDataBindings": [
            {
                "writeResultTo": "/obj",
                "fieldDescriptions": {"/rate": {"label": "当前转速"}},
            }
        ],
        "candidateEventCandidates": [{"description": "锁定"}, {}, {}],
    }
    assert choose_content(source) == {
        "fact_ids": ["/obj/rate", "/层级/key"],
        "action_ids": ["a1", "a2"],
    }


def test_specific_matches_survive_size_and_rarer_terms_rank_first():
    source = make_source(
        "show blue and azure",
        {"first": "blue", "second": "azure", "third": "blue", "fourth": "blue"},
    )
    assert choose_content(source)["fact_ids"] == [
        "/pool/second",
        "/pool/first",
        "/pool/third",
        "/pool/fourth",
    ]


def test_source_order_fallback_only_for_unmatched_facts():
    source = make_source(
        "快速浏览",
        {"alpha": 1, "beta": 2, "gamma": 3, "delta": 4, "epsilon": 5},
        [{"id": "a9", "label": "详情"}],
    )
    assert choose_content(source) == {
        "fact_ids": ["/pool/alpha", "/pool/beta"],
        "action_ids": [],
    }
    source["size"] = "2x4"
    assert choose_content(source)["fact_ids"] == [
        "/pool/alpha",
        "/pool/beta",
        "/pool/gamma",
        "/pool/delta",
    ]
    source["description"] = "汇总 gamma"
    source["query"] = "加个按钮"
    assert choose_content(source) == {"fact_ids": ["/pool/gamma"], "action_ids": ["a9"]}


def test_exclusion_suppresses_metadata_and_prior():
    source = make_source(
        "无需显示出处", {"出处": "北厅"}, [{"id": "a1", "label": "出处"}]
    )
    source["description"] = "出处"
    assert choose_content(source) == {"fact_ids": [], "action_ids": []}


def test_no_candidates_and_no_made_up_action():
    assert choose_content(make_source("点击按钮", {})) == {
        "fact_ids": [],
        "action_ids": [],
    }
