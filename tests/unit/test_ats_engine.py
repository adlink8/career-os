import pytest

from services.ats_engine import ATSScorer, is_composite_intent

pytestmark = pytest.mark.unit

OPS_RESUME = """测一填
求职意向：运维工程师（Linux与容器方向）
专业技能
Linux Docker Python
核心工程项目经历
1. 线上服务运维
负责 Linux Docker Nginx 监控与排障，延迟降低 30ms，超时回滚熔断索引门禁。
教育背景 常州大学 2027届
"""

AI_FIRST_RESUME = """求职意向：运维工程师
教育背景 学习过 Kubernetes 课程
专业技能
Python
核心工程项目经历
1. RAG 检索平台
基于 FastAPI 与向量检索做问答，提升 2 倍召回。
"""

EDU_AFTER_PROJECTS = """求职意向：运维工程师
专业技能
Python
核心工程项目经历
1. RAG 检索平台
基于 FastAPI 与向量检索做问答，提升 2 倍召回。
教育背景 学习过 Kubernetes 课程
"""


def test_composite_intent_rules():
    assert not is_composite_intent("运维工程师（Linux与容器方向）")
    assert not is_composite_intent("运维工程师")
    assert is_composite_intent("技术支持工程师 / 运维工程师 / DevOps 实习生")


def test_direction_note_does_not_knockout():
    r = ATSScorer(
        {"title": "运维工程师", "full_text": "Linux Docker 运维 Nginx Git"},
        OPS_RESUME,
    ).run_full_diagnosis()
    assert r["verdict"] != "FAIL_KNOCKOUT"
    assert r["sub_scores"]["knockout"]["score"] > 0


def test_education_k8s_not_grounded():
    jd = {"title": "运维工程师", "full_text": "Kubernetes Linux Docker"}
    r2 = ATSScorer(jd, AI_FIRST_RESUME).run_full_diagnosis()
    grounded = r2["sub_scores"]["keywords_grounding"]["grounded"]
    missing = r2["sub_scores"]["keywords_grounding"]["missing"]
    assert "Kubernetes" not in grounded
    assert "Kubernetes" in missing

    r2b = ATSScorer(jd, EDU_AFTER_PROJECTS).run_full_diagnosis()
    assert "Kubernetes" not in r2b["sub_scores"]["keywords_grounding"]["grounded"]


def test_non_tech_jd_keyword_score_zero():
    r = ATSScorer(
        {"title": "行政专员", "full_text": "负责办公用品采购与会议安排"},
        OPS_RESUME,
    ).run_full_diagnosis()
    assert r["sub_scores"]["keywords_grounding"]["score"] == 0
