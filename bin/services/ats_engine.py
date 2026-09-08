#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Career OS — Core ATS Scoring Engine (核心打分算法引擎层)
纯业务逻辑与五维打分评估引擎，完全解耦于展示层与命令行。
"""

import re
from typing import Dict, List, Tuple, Set

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

class ATSScorer:
    """
    Core 5-dimensional ATS Scoring Engine (Project-First & Strict Gate):
      1. Knockout & Intent: Max 5 pts (Strict Rule 316 single intent gate)
      2. In-Project Keyword Grounding: Max 30 pts (Skills-only gets 25% discount + Warning)
      3. Project Experience & Flagship Alignment: Max 40 pts (Project text TF-IDF + Flagship relevance)
      4. STAR Quantification & Engineering Evidence: Max 15 pts (Metrics + Battle Scars)
      5. Parsability & A4 Density: Max 10 pts
      Total: 100 pts
    """

    def __init__(self, jd_info: Dict[str, str], resume_text: str):
        self.jd = jd_info
        self.resume_text = resume_text
        self.sections = self._parse_sections(resume_text)
        self.first_third_text = resume_text[:max(400, len(resume_text) // 3)]

    def _parse_sections(self, text: str) -> Dict[str, str]:
        intent_m = re.search(r'(?:求职意向|意向岗位|应聘岗位|求职意向岗位)[：:]\s*([^\n\r]+)', text)
        intent = intent_m.group(1).strip() if intent_m else ""
        if not intent:
            lines = [l.strip() for l in text[:400].split("\n") if l.strip()]
            for l in lines[1:5]:
                if any(k in l for k in ["工程师", "开发", "运维", "专员", "助理", "支持", "经理"]):
                    intent = l
                    break

        skills_m = re.search(r'(?:主要技能|专业技能|核心技能|个人技能|IT技能)([\s\S]*?)(?:专业荣誉|个人概述|核心工程项目经历|项目经历|项目经验|工作经历|教育背景|$)', text)
        skills = skills_m.group(1).strip() if skills_m else ""

        projects_m = re.search(r'(?:核心工程项目经历|项目经历|项目经验|工作经历|工程实战)([\s\S]*)', text)
        projects = projects_m.group(1).strip() if projects_m else ""
        if not projects:
            projects = text[len(text)//3:]

        flagship_title = ""
        flagship_text = ""
        proj_split = re.split(r'\n(?=(?:[1-9]\.|\b[1-9]、|【项目[一二三四1-2-3-4]】))', projects)
        if proj_split:
            flagship_text = proj_split[0].strip()
            first_line = [l.strip() for l in flagship_text.split("\n") if l.strip()]
            flagship_title = first_line[0] if first_line else ""

        return {
            "intent": intent,
            "skills": skills,
            "projects": projects,
            "flagship_title": flagship_title,
            "flagship_text": flagship_text
        }

    def evaluate_knockout(self) -> Tuple[int, List[str], List[str]]:
        """Dimension 1: Knockout Criteria & Intent (Max 5 pts)."""
        score = 5
        warnings = []
        critical_errors = []
        intent = self.sections["intent"]

        # Check for composite intent (Rule 316)
        if any(sep in intent for sep in ["与", "/", "及", "、", "兼", "和"]):
            score = 0
            critical_errors.append(f"【致命违规·Rule 316】求职意向使用了复合兼顾词: '{intent}'！ATS/HR秒筛为海投摇摆，直接一票否决(0分)。")
        elif not intent:
            score = 0
            warnings.append("未明确检测到'求职意向'独立声明模块。")
        else:
            jd_title_clean = re.sub(r'（.*?）|\(.*?\)|届|校招|202\d|J\d+', '', self.jd["title"]).strip()
            clean_tokens = [t for t in re.split(r'[\s\-_—]+', jd_title_clean) if len(t) >= 2]
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
            return 25, {"grounded": [], "skill_only": [], "missing": []}, ["JD中未识别出强硬技术词，使用通用技术栈匹配。"]

        grounded = set()
        skill_only = set()
        missing = set()
        first_screen_hits = set()

        projects_text = self.sections["projects"]
        skills_text = self.sections["skills"]

        for kw in jd_keywords:
            in_projects = match_keyword_in_text(kw, projects_text)
            in_skills = match_keyword_in_text(kw, skills_text)
            in_first_screen = match_keyword_in_text(kw, self.first_third_text)

            if in_first_screen:
                first_screen_hits.add(kw)

            if in_projects:
                grounded.add(kw)
            elif in_skills:
                skill_only.add(kw)
            elif match_keyword_in_text(kw, self.resume_text):
                grounded.add(kw)
            else:
                missing.add(kw)

        # Grounded gets 1.0, skill_only gets 0.25
        effective_points = len(grounded) * 1.0 + len(skill_only) * 0.25
        base_ratio = effective_points / len(jd_keywords)
        base_score = base_ratio * 22

        first_screen_ratio = len(first_screen_hits) / len(jd_keywords)
        first_screen_score = first_screen_ratio * 8

        total_score = min(30, round(base_score + first_screen_score))
        suggestions = []

        if skill_only:
            suggestions.append(f"⚠️ 【口头吹水警示】关键词 {sorted(list(skill_only))} 仅在技能栏罗列，项目经历中 0 次实际落地！面试官将视为空头支票，必须在项目正文中补充动作与指标！")
        if missing:
            suggestions.append(f"❌ 【致命缺词】{sorted(list(missing))} 完全未在简历中出现，ATS 算法大幅扣分！")

        kw_breakdown = {
            "grounded": sorted(list(grounded)),
            "skill_only": sorted(list(skill_only)),
            "missing": sorted(list(missing))
        }
        return total_score, kw_breakdown, suggestions

    def evaluate_project_alignment(self) -> Tuple[int, float, int, List[str]]:
        """Dimension 3: Project Experience & Flagship Alignment (Max 40 pts)."""
        notes = []
        projects_text = self.sections["projects"]
        if not projects_text:
            return 10, 0.05, 5, ["未提取到有效项目经历模块，扣除大部分项目分。"]

        # 1. Project Text TF-IDF Cosine Similarity (25 pts)
        if TfidfVectorizer is None or cosine_similarity is None:
            sim = 0.20
            sim_score = 18
        else:
            try:
                corpus = [self.jd["full_text"], projects_text]
                vectorizer = TfidfVectorizer(tokenizer=hybrid_tokenizer, lowercase=True, token_pattern=None)
                tfidf = vectorizer.fit_transform(corpus)
                sim = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
            except Exception:
                sim = 0.15

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

        # 2. Flagship Project Direct Alignment (15 pts)
        flagship_score = 15
        f_title = self.sections["flagship_title"].lower()
        f_text = self.sections["flagship_text"].lower()
        jd_title_lower = self.jd["title"].lower()
        jd_full = self.jd["full_text"].lower()

        # Prioritize job title for track classification
        if any(k in jd_title_lower for k in ["数据", "etl", "数仓", "爬虫"]):
            is_data_job, is_ai_job = True, False
        elif any(k in jd_title_lower for k in ["ai", "大模型", "算法", "智能体", "agent"]):
            is_data_job, is_ai_job = False, True
        else:
            is_data_job = any(k in jd_full for k in ["数据开发", "etl", "数仓", "血缘分析", "数据清洗"])
            is_ai_job = any(k in jd_full for k in ["大模型应用", "智能体组件", "模型微调", "llm", "rag"])

        if is_ai_job:
            f_is_ai = any(k in f_title or k in f_text for k in ["rag", "大模型", "agent", "llm", "fastapi", "ai native", "向量"])
            if not f_is_ai:
                flagship_score = 5
                notes.append("【第一项目错位】目标为AI开发岗位，但第一项目非大模型/AI系统，严重影响面试官初筛第一印象！")
            else:
                flagship_score = 15
        elif is_data_job:
            f_is_data = any(k in f_title or k in f_text for k in ["数据", "sql", "清洗", "血缘", "etl", "sqlite", "数仓"])
            if not f_is_data:
                flagship_score = 5
                notes.append("【第一项目错位】目标为数据开发岗位，但第一项目非数据处理系统，建议将数据血缘/清洗项目置顶！")
            else:
                flagship_score = 15

        total_proj_score = min(40, sim_score + flagship_score)
        return total_proj_score, round(sim, 4), flagship_score, notes

    def evaluate_star_and_evidence(self) -> Tuple[int, List[str]]:
        """Dimension 4: STAR Quantification & Engineering Evidence (Max 15 pts)."""
        score = 0
        notes = []
        proj_text = self.sections["projects"]

        # 1. Metrics Quantification (8 pts)
        metric_patterns = [
            r'\d+\.?\d*%', r'\d+\s*(?:ms|毫秒|s|秒|分钟|min)', r'降低\s*\d+', r'缩短\s*\d+',
            r'压降\s*\d+', r'提升\s*\d+', r'\d+\s*倍', r'\d+\s*条', r'\d+\s*类', r'0\.00%'
        ]
        metric_hits = sum(len(re.findall(p, proj_text)) for p in metric_patterns)
        if metric_hits >= 5:
            score += 8
        elif metric_hits >= 2:
            score += 5
        else:
            score += 2
            notes.append("项目经历缺乏明确的量化对比指标（如耗时压降%、处理时延ms、吞吐量提升倍数）。")

        # 2. Battle Scars & Engineering Keywords (7 pts)
        battle_words = [
            "索引", "重连", "指数退避", "心跳", "超时", "回滚", "熔断", "快照", "血缘",
            "抓包", "排障", "防篡改", "缓存", "增量", "切片", "时序对齐", "门禁", "E2E", "单测"
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
        char_count = len(re.sub(r'\s+', '', self.resume_text))
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
                    "suggestions": kw_sugg
                },
                "project_alignment": {
                    "score": proj_score,
                    "max": 40,
                    "cosine_sim": proj_sim,
                    "flagship_score": f_score,
                    "notes": proj_notes
                },
                "star_and_evidence": {"score": star_score, "max": 15, "notes": star_notes},
                "parsability": {"score": p_score, "max": 10, "notes": p_notes}
            }
        }

# Alias
ATSEngine = ATSScorer
