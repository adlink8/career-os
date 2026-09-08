#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Career OS — ATS Preflight Matcher & Scoring Engine (校招ATS投前模拟打分机器人)
深度复用 GitHub 明星开源项目：
- Beat-The-ATS (indiser): 关键词差距提取与首屏密度加权
- CV-Matcher (eristavi): 向量空间余弦相似度 (Cosine Similarity)
- Resume-Matcher (srbhr): 诊断看板、缺失词清单与排版解析友好度

专为国内校招 ATS (北森/Moka/大易) 及中英文混合语境深度适配。
"""

import sys
import os
import re
import json
import sqlite3
import argparse
from typing import Dict, List, Tuple, Set

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    TfidfVectorizer = None
    cosine_similarity = None

# Built-in Technical Lexicon for Campus ATS
TECH_DICTIONARY = {
    "ai_llm": [
        "RAG", "Agent", "FastAPI", "LangChain", "LlamaIndex", "Prompt", "大模型", "向量检索", 
        "Embedding", "PyTorch", "ONNX", "Transformer", "微调", "Fine-tuning", "NLP", "多模态",
        "Milvus", "Chroma", "Qdrant", "BM25", "LLM", "vLLM", "Ollama"
    ],
    "data_eng": [
        "SQL", "ETL", "Hive", "Spark", "Flink", "Kafka", "数据清洗", "数据仓库", "血缘分析",
        "数据治理", "MySQL", "PostgreSQL", "ClickHouse", "数据建模", "爬虫", "Scrapy", "反爬",
        "逆向", "Selenium", "Pandas", "NumPy", "数据湖", "Hadoop", "数仓", "数据分析"
    ],
    "devops_sys": [
        "Linux", "Docker", "Kubernetes", "K8s", "CI/CD", "Shell", "Bash", "Nginx", "Git",
        "TCP/IP", "Wireshark", "Prometheus", "Grafana", "自动化测试", "系统监控", "运维",
        "抓包", "路由交换", "网络协议", "负载均衡", "微服务", "Ansible", "DevOps", "排障"
    ],
    "iot_embed": [
        "ESP32", "MQTT", "Modbus", "单片机", "嵌入式", "传感器", "串口", "网关", "FreeRTOS",
        "STM32", "C语言", "C++", "上位机", "工业物联网", "物联网", "硬件调试", "局域网", "PLC",
        "树莓派", "RTOS", "边缘计算", "PyQt5", "CAN总线", "I2C", "SPI"
    ],
    "soft_eng": [
        "Java", "SpringBoot", "Python", "Go", "Golang", "Vue", "React", "RESTful", "API",
        "Redis", "消息队列", "面向对象", "设计模式", "单元测试", "GitFlow", "软件工程", "UML"
    ]
}

ALL_TECH_KEYWORDS = {}
for cat, words in TECH_DICTIONARY.items():
    for w in words:
        ALL_TECH_KEYWORDS[w.lower()] = w


def match_keyword_in_text(kw: str, text: str) -> bool:
    """Accurately match English words (with ASCII lookaround) or Chinese substrings in mixed text."""
    if re.search(r'[\u4e00-\u9fa5]', kw):
        return kw in text
    else:
        pattern = r'(?i)(?<![a-zA-Z0-9])' + re.escape(kw) + r'(?![a-zA-Z0-9])'
        return bool(re.search(pattern, text))


def extract_text_from_file(file_path: str) -> str:
    """Extract raw text from PDF, MD, or TXT file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件未找到: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        if fitz is None:
            raise RuntimeError("PyMuPDF (fitz) 未安装，无法解析 PDF。请运行 pip install pymupdf")
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        return text.strip()
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()


def extract_jd_from_db(job_id: int, db_path: str = "data/career_jobs.sqlite") -> Dict[str, str]:
    """Retrieve job details from Career OS sqlite database."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"数据库未找到: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT company_name, job_title, city, responsibilities, requirements, category
        FROM jobs WHERE id = ?
    """, (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise ValueError(f"数据库中未找到 ID 为 {job_id} 的岗位")
    return {
        "company": row[0],
        "title": row[1],
        "city": row[2],
        "responsibilities": row[3] or "",
        "requirements": row[4] or "",
        "category": row[5] or "",
        "full_text": f"{row[1]}\n{row[3]}\n{row[4]}"
    }


def extract_keywords_from_jd(jd_text: str) -> Set[str]:
    """Extract required tech keywords from JD using technical dictionary & lookaround."""
    found_keywords = set()
    for kw_lower, original_case in ALL_TECH_KEYWORDS.items():
        if match_keyword_in_text(kw_lower, jd_text):
            found_keywords.add(original_case)
    return found_keywords


def hybrid_tokenizer(text: str) -> List[str]:
    """Tokenize mixed Chinese and English text for TF-IDF without external segmenter."""
    tokens = re.findall(r'[a-zA-Z0-9+#]{2,}', text.lower())
    cn_chars = re.sub(r'[^\u4e00-\u9fa5]', '', text)
    for i in range(len(cn_chars) - 1):
        tokens.append(cn_chars[i:i+2])
        if i < len(cn_chars) - 2:
            tokens.append(cn_chars[i:i+3])
    return tokens


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


def print_report(res: Dict, jd_title: str, resume_path: str):
    """Print visually structured diagnostic report to terminal."""
    s = res["sub_scores"]
    print("\n" + "=" * 75)
    print(" 🎯 Career OS — ATS Preflight Matcher (校招投前模拟打分看板)")
    print("=" * 75)
    print(f"📌 拟投岗位 : {jd_title}")
    print(f"📄 审查简历 : {os.path.basename(resume_path)}")
    print(f"🏆 综合评分 : {res['total_score']} / 100 分")
    print(f"🚦 评审结论 : {res['status_text']}")
    print("-" * 75)
    print("📊 五维评分拆解 (Breakdown):")
    print(f"  1. 硬门槛与求职意向 (Knockout & Intent)     : {s['knockout']['score']:2d} / {s['knockout']['max']} 分")
    print(f"  2. 核心技术词正文落地 (In-Project Grounding) : {s['keywords_grounding']['score']:2d} / {s['keywords_grounding']['max']} 分")
    print(f"  3. 主力项目与JD对位深度 (Project Alignment)  : {s['project_alignment']['score']:2d} / {s['project_alignment']['max']} 分 (项目余弦值: {s['project_alignment']['cosine_sim']})")
    print(f"  4. 项目STAR量化与工程证据 (STAR Evidence)   : {s['star_and_evidence']['score']:2d} / {s['star_and_evidence']['max']} 分")
    print(f"  5. 格式结构与单页密度 (Parsability Score)   : {s['parsability']['score']:2d} / {s['parsability']['max']} 分")
    print("-" * 75)

    if s['knockout']['critical']:
        print("🚨 【一票否决致命告警】:")
        for c in s['knockout']['critical']:
            print(f"   ❌ {c}")
        print()

    if s['keywords_grounding']['suggestions']:
        for sug in s['keywords_grounding']['suggestions']:
            print(f"   {sug}")
        print()

    if s['project_alignment']['notes']:
        for n in s['project_alignment']['notes']:
            print(f"   • {n}")
        print()

    if s['knockout']['warnings'] or s['parsability']['notes']:
        print("⚠️ 【结构与格式警示】:")
        for w in s['knockout']['warnings']:
            print(f"   • {w}")
        for n in s['parsability']['notes']:
            print(f"   • {n}")
        print()

    print(f"✅ 项目正文落地核心词 ({len(s['keywords_grounding']['grounded'])}个):")
    print(f"   {', '.join(s['keywords_grounding']['grounded']) if s['keywords_grounding']['grounded'] else '无'}")
    print()

    if s['keywords_grounding']['skill_only']:
        print(f"⚠️ 仅在技能栏吹水·项目未落地词 ({len(s['keywords_grounding']['skill_only'])}个):")
        print(f"   👉 {', '.join(s['keywords_grounding']['skill_only'])}")
        print("   💡 警示: 面试官极易判定为只背过八股，必须在项目经历中补写该技术的实操动作！")
        print()

    if s['keywords_grounding']['missing']:
        print(f"❌ 全篇致命缺失词 Missing Keywords ({len(s['keywords_grounding']['missing'])}个):")
        print(f"   👉 {', '.join(s['keywords_grounding']['missing'])}")
    else:
        print("🎉 核心技术词完美覆盖！")

    print("=" * 75 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Career OS ATS Preflight Matcher")
    parser.add_argument("--resume", required=True, help="Path to resume file (.pdf, .md, .txt)")
    parser.add_argument("--job-id", type=int, help="Job ID from data/career_jobs.sqlite")
    parser.add_argument("--jd-file", help="Path to JD text file")
    parser.add_argument("--jd-text", help="Raw JD text string")
    parser.add_argument("--jd-title", default="自定义目标岗位", help="Job title if using jd-file or jd-text")
    parser.add_argument("--min-score", type=int, default=85, help="Minimum passing score (default 85)")
    parser.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()

    resume_text = extract_text_from_file(args.resume)

    if args.job_id:
        jd_info = extract_jd_from_db(args.job_id)
    elif args.jd_file:
        with open(args.jd_file, "r", encoding="utf-8", errors="ignore") as f:
            t = f.read()
        jd_info = {"title": args.jd_title, "full_text": t}
    elif args.jd_text:
        jd_info = {"title": args.jd_title, "full_text": args.jd_text}
    else:
        print("错误: 必须指定 --job-id、--jd-file 或 --jd-text 之一")
        sys.exit(2)

    scorer = ATSScorer(jd_info, resume_text)
    results = scorer.run_full_diagnosis()

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_report(results, jd_info.get("title", args.jd_title), args.resume)

    if results["verdict"] == "FAIL_KNOCKOUT" or results["total_score"] < args.min_score:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
