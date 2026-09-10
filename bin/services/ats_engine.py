#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Career OS — Core ATS Scoring Engine (核心打分算法引擎层)
纯业务逻辑与五维打分评估引擎，完全解耦于展示层与命令行。
"""

import re
from typing import Dict, List, Tuple

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    TfidfVectorizer = None
    cosine_similarity = None

try:
    from .tech_lexicon import match_keyword_in_text, extract_keywords_from_jd, hybrid_tokenizer
    from .resume_parser import parse_resume_sections
except (ImportError, ValueError):
    from services.tech_lexicon import match_keyword_in_text, extract_keywords_from_jd, hybrid_tokenizer
    from services.resume_parser import parse_resume_sections

# 双岗位标题连接符：只打「两个职位」而不是方向说明里的「与/和」
_ROLE_TOKEN = r"(?:工程师|开发|运维|专员|助理|支持|经理|实习|SRE|DevOps|FAE)"
_COMPOSITE_INTENT_RE = re.compile(
    _ROLE_TOKEN + r".{0,16}(?:[/／、兼|]|&)\s*.{0,16}" + _ROLE_TOKEN,
    re.IGNORECASE,
)
_COMPOSITE_AND_RE = re.compile(
    _ROLE_TOKEN + r".{0,10}(?:与|及).{0,10}" + _ROLE_TOKEN,
    re.IGNORECASE,
)

_JOB_FAMILY_TITLE = (
    ("data", ("数据", "etl", "数仓", "爬虫")),
    ("ai", ("ai", "大模型", "算法", "智能体", "agent")),
    ("ops", ("运维", "devops", "sre")),
    ("iot", ("物联网", "iot", "嵌入式", "固件", "硬件")),
    ("support", ("技术支持", "fae", "售后", "实施")),
)
_JOB_FAMILY_BODY = (
    ("data", ("数据开发", "etl", "数仓", "血缘分析", "数据清洗")),
    ("ai", ("大模型应用", "智能体组件", "模型微调", "llm", "rag")),
    ("ops", ("linux", "kubernetes", "docker", "ci/cd", "prometheus")),
    ("iot", ("mqtt", "esp32", "单片机", "嵌入式", "工业物联网")),
    ("support", ("现场交付", "客户支持", "工单", "售前售后")),
)
_FAMILY_FLAGSHIP = {
    "ai": (["rag", "大模型", "agent", "llm", "fastapi", "ai native", "向量"], "AI开发"),
    "data": (["数据", "sql", "清洗", "血缘", "etl", "sqlite", "数仓"], "数据开发"),
    "ops": (["运维", "linux", "docker", "nginx", "监控", "容器", "ci", "k8s", "kubernetes"], "运维/DevOps"),
    "iot": (["iot", "mqtt", "嵌入式", "esp32", "网关", "固件", "传感器", "单片机"], "物联网/嵌入式"),
    "support": (["排障", "交付", "支持", "联调", "现场", "工单"], "技术支持"),
}


def is_dual_role_title(title: str) -> bool:
    """True when a job title names two roles with slash/顿号, e.g. 运维 / 开发."""
    if not title:
        return False
    stripped = re.sub(r"（.*?）|\(.*?\)", "", title)
    return bool(_COMPOSITE_INTENT_RE.search(stripped))


def is_composite_intent(intent: str) -> bool:
    """True only when the intent line names two job roles, not a tech-direction note."""
    if not intent:
        return False
    stripped = re.sub(r"（.*?）|\(.*?\)", "", intent)
    return bool(_COMPOSITE_INTENT_RE.search(stripped) or _COMPOSITE_AND_RE.search(stripped))


class ATSScorer:
    """
    Core 5-dimensional ATS Scoring Engine (Project-First & Strict Gate):
      1. Knockout & Intent: Max 5 pts (dual-role intent veto)
      2. In-Project Keyword Grounding: Max 30 pts (Skills-only gets 25% discount + Warning)
      3. Project Experience & Flagship Alignment: Max 40 pts (Project text TF-IDF + Flagship relevance)
      4. STAR Quantification & Engineering Evidence: Max 15 pts (Metrics + Battle Scars)
      5. Parsability & A4 Density: Max 10 pts
      Total: 100 pts
    """

    def __init__(self, jd_info: Dict[str, str], resume_text: str):
        self.jd = jd_info
        self.resume_text = resume_text
        self.sections = parse_resume_sections(resume_text)
        self.first_third_text = resume_text[: max(400, len(resume_text) // 3)]

    def evaluate_knockout(self) -> Tuple[int, List[str], List[str]]:
        """Dimension 1: Knockout Criteria & Intent (Max 5 pts)."""
        score = 5
        warnings = []
        critical_errors = []
        intent = self.sections["intent"]

        if is_composite_intent(intent):
            score = 0
            critical_errors.append(
                f"【致命违规·Rule 316】求职意向写成了多个岗位: '{intent}'。"
                "只否决双职位标题（如「运维工程师 / 开发工程师」），方向说明里的「与」不在此列。"
            )
        elif not intent:
            score = 0
            warnings.append("未明确检测到'求职意向'独立声明模块。")
        else:
            jd_title_clean = re.sub(r"（.*?）|\(.*?\)|届|校招|202\d|J\d+", "", self.jd["title"]).strip()
            clean_tokens = [t for t in re.split(r"[\s\-_—]+", jd_title_clean) if len(t) >= 2]
            matched_title = any(t.lower() in intent.lower() for t in clean_tokens) if clean_tokens else False

            if not matched_title and jd_title_clean.lower() not in intent.lower():
                score -= 2
                warnings.append(f"求职意向 '{intent}' 与目标岗位 '{self.jd['title']}' 存在字面偏差，建议精准对齐。")

        if "2027" in self.jd["title"] or "2027" in self.jd.get("full_text", ""):
            if "2027" not in self.resume_text:
                score = max(0, score - 1)
                warnings.append("目标JD标明2027届校招，简历中未明确标注'2027届'或'2027-06毕业'。")

        return max(0, score), warnings, critical_errors

    def evaluate_keywords_grounding(self) -> Tuple[int, Dict, List[str]]:
        """Dimension 2: In-Project Keyword Grounding (Max 30 pts)."""
        jd_keywords = extract_keywords_from_jd(self.jd["full_text"])
        if not jd_keywords:
            return 0, {"grounded": [], "skill_only": [], "missing": []}, [
                "JD 未命中技术词典，关键词维记 0 分（不再白送 25 分）。请改用带明确技术栈的 JD，或扩充词典。"
            ]

        grounded = set()
        skill_only = set()
        missing = set()
        elsewhere = set()
        first_screen_hits = set()

        projects_text = self.sections["projects"]
        skills_text = self.sections["skills"]

        for kw in jd_keywords:
            in_projects = match_keyword_in_text(kw, projects_text)
            in_skills = match_keyword_in_text(kw, skills_text)
            in_first_screen = in_projects and match_keyword_in_text(kw, self.first_third_text)

            if in_first_screen:
                first_screen_hits.add(kw)

            if in_projects:
                grounded.add(kw)
            elif in_skills:
                skill_only.add(kw)
            elif match_keyword_in_text(kw, self.resume_text):
                elsewhere.add(kw)
                missing.add(kw)
            else:
                missing.add(kw)

        effective_points = len(grounded) * 1.0 + len(skill_only) * 0.25
        base_ratio = effective_points / len(jd_keywords)
        base_score = base_ratio * 22

        first_screen_ratio = len(first_screen_hits) / len(jd_keywords)
        first_screen_score = first_screen_ratio * 8

        total_score = min(30, round(base_score + first_screen_score))
        suggestions = []

        if skill_only:
            suggestions.append(
                f"⚠️ 【口头吹水警示】关键词 {sorted(list(skill_only))} 仅在技能栏罗列，项目经历中 0 次实际落地！"
            )
        if elsewhere:
            suggestions.append(
                f"⚠️ 【非项目正文】{sorted(list(elsewhere))} 只出现在教育/概述等位置，不计入落地分。"
            )
        if missing:
            suggestions.append(f"❌ 【致命缺词】{sorted(list(missing))} 未在项目正文出现，ATS 算法大幅扣分！")

        kw_breakdown = {
            "grounded": sorted(list(grounded)),
            "skill_only": sorted(list(skill_only)),
            "missing": sorted(list(missing)),
            "elsewhere": sorted(list(elsewhere)),
        }
        return total_score, kw_breakdown, suggestions

    def _job_family(self) -> str:
        title = (self.jd.get("title") or "").lower()
        full = (self.jd.get("full_text") or "").lower()
        for family, keys in _JOB_FAMILY_TITLE:
            if any(k in title for k in keys):
                return family
        for family, keys in _JOB_FAMILY_BODY:
            if any(k in full for k in keys):
                return family
        return "other"

    def evaluate_project_alignment(self) -> Tuple[int, float, int, List[str]]:
        """Dimension 3: Project Experience & Flagship Alignment (Max 40 pts)."""
        notes = []
        projects_text = self.sections["projects"]
        if not projects_text:
            return 10, 0.05, 5, ["未提取到有效项目经历模块，扣除大部分项目分。"]

        if TfidfVectorizer is None or cosine_similarity is None:
            sim = 0.20
            sim_score = 18
            notes.append(
                "⚠️ 【引擎降级】scikit-learn 未安装，项目语义相似度采用固定中位分 18/25，"
                "该维度分数不可信！请执行: pip install scikit-learn"
            )
        else:
            try:
                corpus = [self.jd["full_text"], projects_text]
                vectorizer = TfidfVectorizer(tokenizer=hybrid_tokenizer, lowercase=True, token_pattern=None)
                tfidf = vectorizer.fit_transform(corpus)
                sim = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
            except Exception as exc:
                sim = 0.15
                notes.append(f"⚠️ 【引擎降级】TF-IDF 计算失败，项目语义分不可信: {str(exc)[:120]}")

            if sim >= 0.26:
                sim_score = 25
            elif sim >= 0.18:
                sim_score = 20
            elif sim >= 0.12:
                sim_score = 15
            elif sim >= 0.07:
                sim_score = 10
            else:
                sim_score = 5

        flagship_score = 15
        f_title = self.sections["flagship_title"].lower()
        f_text = self.sections["flagship_text"].lower()
        family = self._job_family()
        spec = _FAMILY_FLAGSHIP.get(family)
        if spec:
            keys, label = spec
            if not any(k in f_title or k in f_text for k in keys):
                flagship_score = 5
                notes.append(
                    f"【第一项目错位】目标为{label}岗位，但第一项目未覆盖该赛道关键词，建议把对口项目置顶。"
                )

        total_proj_score = min(40, sim_score + flagship_score)
        return total_proj_score, round(sim, 4), flagship_score, notes

    def evaluate_star_and_evidence(self) -> Tuple[int, List[str]]:
        """Dimension 4: STAR Quantification & Engineering Evidence (Max 15 pts)."""
        score = 0
        notes = []
        proj_text = self.sections["projects"]

        metric_patterns = [
            r"\d+\.?\d*%", r"\d+\s*(?:ms|毫秒|s|秒|分钟|min)", r"降低\s*\d+", r"缩短\s*\d+",
            r"压降\s*\d+", r"提升\s*\d+", r"\d+\s*倍", r"\d+\s*条", r"\d+\s*类", r"0\.00%",
        ]
        metric_hits = sum(len(re.findall(p, proj_text)) for p in metric_patterns)
        if metric_hits >= 5:
            score += 8
        elif metric_hits >= 2:
            score += 5
        else:
            score += 2
            notes.append("项目经历缺乏明确的量化对比指标（如耗时压降%、处理时延ms、吞吐量提升倍数）。")

        battle_words = [
            "索引", "重连", "指数退避", "心跳", "超时", "回滚", "熔断", "快照", "血缘",
            "抓包", "排障", "防篡改", "缓存", "增量", "切片", "时序对齐", "门禁", "E2E", "单测",
        ]
        scars_found = [w for w in battle_words if w in proj_text]
        if len(scars_found) >= 5:
            score += 7
        elif len(scars_found) >= 2:
            score += 4
        else:
            score += 1
            notes.append("项目经历缺乏一线工程攻坚关键词（如重试、防篡改、血缘、回滚、索引调优等）。")

        return score, notes

    def evaluate_parsability(self) -> Tuple[int, List[str]]:
        """Dimension 5: Parsability & Structure (Max 10 pts)."""
        score = 10
        notes = []
        char_count = len(re.sub(r"\s+", "", self.resume_text))
        if char_count < 400:
            score -= 4
            notes.append(f"有效字符偏少 ({char_count}字)，信息密度不足。")
        elif char_count > 1900:
            score -= 2
            notes.append(f"字符偏多 ({char_count}字)，存在物理单页溢出或行距过密风险。")

        essential = ["教育", "技能", "项目"]
        for sec in essential:
            if sec not in self.resume_text:
                score -= 2
                notes.append(f"未检测到明显的'{sec}'模块。")

        return max(0, score), notes

    def run_full_diagnosis(self) -> Dict:
        """Run all evaluations and produce full report."""
        k_score, k_warn, k_crit = self.evaluate_knockout()
        kw_score, kw_breakdown, kw_sugg = self.evaluate_keywords_grounding()
        proj_score, proj_sim, f_score, proj_notes = self.evaluate_project_alignment()
        star_score, star_notes = self.evaluate_star_and_evidence()
        p_score, p_notes = self.evaluate_parsability()

        total_score = k_score + kw_score + proj_score + star_score + p_score

        if k_crit:
            verdict = "FAIL_KNOCKOUT"
            status_text = "🔴 强制拦截 (FAIL - 触发硬门槛否决)"
        elif total_score >= 85:
            verdict = "PASS"
            status_text = "🟢 极度安全，准许投递 (PASS)"
        elif total_score >= 70:
            verdict = "WARN"
            status_text = "🟡 中度风险，建议项目深度对位优化 (WARN)"
        else:
            verdict = "FAIL"
            status_text = "🔴 高危风险，低分拦截 (FAIL)"

        return {
            "total_score": total_score,
            "verdict": verdict,
            "status_text": status_text,
            "sub_scores": {
                "knockout": {"score": k_score, "max": 5, "warnings": k_warn, "critical": k_crit},
                "keywords_grounding": {
                    "score": kw_score,
                    "max": 30,
                    "grounded": kw_breakdown["grounded"],
                    "skill_only": kw_breakdown["skill_only"],
                    "missing": kw_breakdown["missing"],
                    "elsewhere": kw_breakdown.get("elsewhere", []),
                    "suggestions": kw_sugg,
                },
                "project_alignment": {
                    "score": proj_score,
                    "max": 40,
                    "cosine_sim": proj_sim,
                    "flagship_score": f_score,
                    "notes": proj_notes,
                },
                "star_and_evidence": {"score": star_score, "max": 15, "notes": star_notes},
                "parsability": {"score": p_score, "max": 10, "notes": p_notes},
            },
        }


ATSEngine = ATSScorer
