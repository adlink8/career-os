#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ATS 引擎契约冒烟：Rule 316、项目落地、空 JD 词、运维第一项目对位。"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))

from services.ats_engine import ATSScorer, is_composite_intent  # noqa: E402


def check(label: str, cond: bool) -> None:
    if not cond:
        raise AssertionError(label)
    print(f"[PASS] {label}")


OPS_RESUME = """李硕研
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


def main() -> int:
    check("方向说明含「与」不是复合意向", not is_composite_intent("运维工程师（Linux与容器方向）"))
    check(
        "斜杠多岗位是复合意向",
        is_composite_intent("技术支持工程师 / 运维工程师 / DevOps 实习生"),
    )
    check("单一岗位不是复合意向", not is_composite_intent("运维工程师"))

    r1 = ATSScorer({"title": "运维工程师", "full_text": "Linux Docker 运维 Nginx Git"}, OPS_RESUME).run_full_diagnosis()
    check("方向说明意向不熔断", r1["verdict"] != "FAIL_KNOCKOUT")
    check("方向说明意向 knockout>0", r1["sub_scores"]["knockout"]["score"] > 0)

    r2 = ATSScorer(
        {"title": "运维工程师", "full_text": "Kubernetes Linux Docker"},
        AI_FIRST_RESUME,
    ).run_full_diagnosis()
    check("教育栏在项目前时 Kubernetes 不算落地", "Kubernetes" not in r2["sub_scores"]["keywords_grounding"]["grounded"])
    check("教育栏 Kubernetes 记入缺词/elsewhere", "Kubernetes" in r2["sub_scores"]["keywords_grounding"]["missing"])

    r2b = ATSScorer(
        {"title": "运维工程师", "full_text": "Kubernetes Linux Docker"},
        EDU_AFTER_PROJECTS,
    ).run_full_diagnosis()
    check("教育栏在项目后时也不算落地", "Kubernetes" not in r2b["sub_scores"]["keywords_grounding"]["grounded"])

    r3 = ATSScorer({"title": "行政专员", "full_text": "负责办公用品采购与会议安排"}, OPS_RESUME).run_full_diagnosis()
    check("无技术词 JD 关键词维为 0", r3["sub_scores"]["keywords_grounding"]["score"] == 0)

    r4 = ATSScorer(
        {"title": "Linux运维工程师", "full_text": "Linux Docker Nginx 运维 排障 Git"},
        AI_FIRST_RESUME,
    ).run_full_diagnosis()
    check("运维岗第一项目不对口扣 flagship", r4["sub_scores"]["project_alignment"]["flagship_score"] == 5)

    r5 = ATSScorer(
        {"title": "运维工程师", "full_text": "Linux Docker"},
        OPS_RESUME.replace("运维工程师（Linux与容器方向）", "技术支持工程师 / 运维工程师 / DevOps 实习生"),
    ).run_full_diagnosis()
    check("多岗位斜杠意向熔断", r5["verdict"] == "FAIL_KNOCKOUT")
    print("[OK] ats-engine-smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
