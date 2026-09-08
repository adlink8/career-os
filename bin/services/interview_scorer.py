#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Career OS — Mock Interview Answer Scorer Service (面试回答评估公共服务层)
四维 Rubric 离线打分与证据链判定，复用公共技术词典与 STAR 证据库。
"""

from __future__ import annotations

import re
from typing import Dict, Any, Union

try:
    from .tech_lexicon import (
        ALL_TECH_KEYWORDS,
        EVIDENCE_TERMS,
        STRUCTURE_TERMS,
        ENGINEERING_BATTLE_SCARS,
    )
except (ImportError, ValueError):
    from services.tech_lexicon import (
        ALL_TECH_KEYWORDS,
        EVIDENCE_TERMS,
        STRUCTURE_TERMS,
        ENGINEERING_BATTLE_SCARS,
    )

RUBRIC_VERSION = "interview-v1"


def score_answer(question: str, answer: str, *, follow_up: bool = False) -> Dict[str, Union[int, str, Any]]:
    """
    可解释的离线评分器，四维判定与 career-interview-master 保持一致。
    维度：technical (技术细节), expression (表达结构), project (项目证据), followup_score (追问与取舍).
    向下兼容 mock_interview_agent 以及 runtime-smoke 的所有契约字段。
    """
    text = answer.strip()
    length = len(text)

    # 1. 技术词与工程踩坑命中数
    tech_hits = 0
    text_lower = text.lower()
    for kw_lower in ALL_TECH_KEYWORDS:
        if len(kw_lower) >= 2 and kw_lower in text_lower:
            tech_hits += 1
    scars_hits = sum(1 for scar in ENGINEERING_BATTLE_SCARS if scar in text)
    total_tech_hits = tech_hits + scars_hits

    # 2. STAR 证据词与结构词命中
    evidence_hits = sum(1 for term in EVIDENCE_TERMS if term in text)
    structure_hits = sum(1 for term in STRUCTURE_TERMS if term in text)

    # 3. 四维得分计算
    technical = min(100, 35 + total_tech_hits * 6 + evidence_hits * 4 + (10 if length >= 80 else 0))
    expression = min(100, 35 + (15 if 45 <= length <= 500 else 5 if length else 0) + structure_hits * 7 + (8 if re.search(r"[。！？]", text) else 0))
    project = min(100, 30 + evidence_hits * 9 + (12 if "项目" in text or "系统" in text else 0) + (8 if length >= 100 else 0))
    followup_score = min(100, 30 + structure_hits * 10 + (15 if any(x in text for x in ("为什么", "取舍", "边界", "回滚", "监控", "对比")) else 0) + (10 if length >= 80 else 0))

    overall = round(technical * 0.4 + expression * 0.3 + project * 0.2 + followup_score * 0.1)
    weakest = min((technical, expression, project, followup_score))
    focus = "技术细节" if weakest == technical else "表达结构" if weakest == expression else "项目证据" if weakest == project else "追问与取舍"

    feedback_parts = []
    if total_tech_hits < 2:
        feedback_parts.append("技术术语偏少，建议多结合具体框架、协议或索引/监控等专业工程名词；")
    if evidence_hits < 2:
        feedback_parts.append("项目证据偏弱，建议增加真实业务场景、时延压降或稳定性百分比指标；")
    if structure_hits < 1:
        feedback_parts.append("表达缺少逻辑骨架，可采用‘首先-然后-取舍-结论’递进式结构；")

    feedback = "".join(feedback_parts) if feedback_parts else "回答结构完整，技术点与项目证据较扎实。"

    return {
        "technical": technical,
        "expression": expression,
        "project": project,
        "follow_up": followup_score,
        "overall": overall,
        "focus": focus,
        "weakest": focus,
        "provider": "local-rubric",
        "follow_up_turn": "yes" if follow_up else "no",
        "feedback": feedback,
        "rubric_version": RUBRIC_VERSION,
        "stats": {
            "length": length,
            "tech_hits": total_tech_hits,
            "evidence_hits": evidence_hits,
            "structure_hits": structure_hits,
        },
    }
