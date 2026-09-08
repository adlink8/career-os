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
    """Core 4-dimensional ATS Scoring Engine."""

    def __init__(self, jd_info: Dict[str, str], resume_text: str):
        self.jd = jd_info
        self.resume_text = resume_text
        self.first_third_text = resume_text[:max(400, len(resume_text) // 3)]

    def evaluate_knockout(self) -> Tuple[int, List[str], List[str]]:
        """Dimension 1: Knockout Criteria & Intent (25 pts)."""
        score = 25
        warnings = []
        critical_errors = []

        # 1. Extract Target Job Intent from Resume
        intent_match = re.search(r'(?:求职意向|意向岗位|应聘岗位|求职意向岗位)[：:]\s*([^\n\r]+)', self.resume_text)
        intent = intent_match.group(1).strip() if intent_match else ""

        if not intent:
            lines = [l.strip() for l in self.resume_text[:400].split("\n") if l.strip()]
            for l in lines[1:5]:
                if any(k in l for k in ["工程师", "开发", "运维", "专员", "助理", "支持", "经理"]):
                    intent = l
                    break

        # Check for composite intent (Rule 316)
        if any(sep in intent for sep in ["与", "/", "及", "、", "兼", "和"]):
            score = 0
            critical_errors.append(f"【致命违规·Rule 316】求职意向使用了复合兼顾词: '{intent}'！ATS/HR秒筛为海投摇摆，直接一票否决(0分)。")
        elif not intent:
            score -= 15
            warnings.append("未明确检测到'求职意向'独立声明模块。")
        else:
            jd_title_clean = re.sub(r'（.*?）|\(.*?\)|届|校招|202\d|J\d+', '', self.jd["title"]).strip()
            clean_tokens = [t for t in re.split(r'[\s\-_—]+', jd_title_clean) if len(t) >= 2]
            matched_title = any(t.lower() in intent.lower() for t in clean_tokens) if clean_tokens else False

            if not matched_title and jd_title_clean.lower() not in intent.lower():
                score -= 10
                warnings.append(f"求职意向 '{intent}' 与目标岗位全称 '{self.jd['title']}' 存在字面偏差，建议100%对齐。")

        if "2027" in self.jd["title"] or "2027" in self.jd.get("full_text", ""):
            if "2027" not in self.resume_text:
                score -= 5
                warnings.append("目标JD标明2027届校招，简历中未明确标注'2027届'或'2027-06毕业'，易被毕业年份过滤器拦截。")

        return max(0, score), warnings, critical_errors

    def evaluate_keywords(self) -> Tuple[int, Set[str], Set[str], List[str]]:
        """Dimension 2: Keyword Coverage & Gap Analysis - Beat-The-ATS (35 pts)."""
        jd_keywords = extract_keywords_from_jd(self.jd["full_text"])
        if not jd_keywords:
            return 30, set(), set(), ["JD中未识别出强硬技术词，使用通用技术栈匹配。"]

        matched = set()
        missing = set()
        first_screen_matched = set()

        for kw in jd_keywords:
            if match_keyword_in_text(kw, self.resume_text):
                matched.add(kw)
                if match_keyword_in_text(kw, self.first_third_text):
                    first_screen_matched.add(kw)
            else:
                missing.add(kw)

        coverage = len(matched) / len(jd_keywords) if jd_keywords else 1.0
        base_score = coverage * 25
        first_screen_ratio = len(first_screen_matched) / len(jd_keywords) if jd_keywords else 1.0
        first_screen_score = first_screen_ratio * 10

        total_score = min(35, round(base_score + first_screen_score))
        suggestions = []
        if coverage < 0.65:
            suggestions.append(f"核心关键词覆盖率偏低 ({coverage*100:.1f}%)，需在专业技能栏补充关键缺词。")
        if first_screen_ratio < 0.40:
            suggestions.append(f"首屏加粗关键词较少 ({first_screen_ratio*100:.1f}%)，HR 5秒扫视易漏掉核心卖点。")

        return total_score, matched, missing, suggestions

    def evaluate_semantic(self) -> Tuple[int, float]:
        """Dimension 3: Semantic Alignment via TF-IDF & Cosine Similarity - CV-Matcher (25 pts)."""
        if TfidfVectorizer is None or cosine_similarity is None:
            return 20, 0.70

        try:
            corpus = [self.jd["full_text"], self.resume_text]
            vectorizer = TfidfVectorizer(
                tokenizer=hybrid_tokenizer,
                lowercase=True,
                token_pattern=None
            )
            tfidf_matrix = vectorizer.fit_transform(corpus)
            sim = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
        except Exception:
            sim = 0.20

        # Mapping for mixed-language TF-IDF
        if sim >= 0.28:
            score = 25
        elif sim >= 0.20:
            score = 22
        elif sim >= 0.14:
            score = 18
        elif sim >= 0.08:
            score = 12
        else:
            score = 6

        return score, sim

    def evaluate_parsability(self) -> Tuple[int, List[str]]:
        """Dimension 4: Parsability & Structure - Resume-Matcher (15 pts)."""
        score = 15
        notes = []

        char_count = len(re.sub(r'\s+', '', self.resume_text))
        if char_count < 400:
            score -= 6
            notes.append(f"有效字符偏少 ({char_count}字)，信息密度不足。")
        elif char_count > 1800:
            score -= 3
            notes.append(f"字符过多 ({char_count}字)，存在物理单页溢出或行间距过度压缩风险。")

        essential_sections = ["教育", "技能", "项目"]
        for sec in essential_sections:
            if sec not in self.resume_text:
                score -= 3
                notes.append(f"未检测到明显的'{sec}'模块标题。")

        return max(0, score), notes

    def run_full_diagnosis(self) -> Dict:
        """Run all evaluations and produce full report."""
        k_score, k_warn, k_crit = self.evaluate_knockout()
        w_score, matched_kw, missing_kw, w_sugg = self.evaluate_keywords()
        s_score, cos_sim = self.evaluate_semantic()
        p_score, p_notes = self.evaluate_parsability()

        total_score = k_score + w_score + s_score + p_score

        if k_crit:
            verdict = "FAIL_KNOCKOUT"
            status_text = "🔴 强制拦截 (FAIL - 触发硬门槛否决)"
        elif total_score >= 85:
            verdict = "PASS"
            status_text = "🟢 极度安全，准许投递 (PASS)"
        elif total_score >= 70:
            verdict = "WARN"
            status_text = "🟡 中度风险，建议补词优化 (WARN)"
        else:
            verdict = "FAIL"
            status_text = "🔴 高危风险，低分拦截 (FAIL)"

        return {
            "total_score": total_score,
            "verdict": verdict,
            "status_text": status_text,
            "sub_scores": {
                "knockout": {"score": k_score, "max": 25, "warnings": k_warn, "critical": k_crit},
                "keywords": {
                    "score": w_score, 
                    "max": 35, 
                    "matched": sorted(list(matched_kw)), 
                    "missing": sorted(list(missing_kw)),
                    "suggestions": w_sugg
                },
                "semantic": {"score": s_score, "max": 25, "cosine_sim": round(cos_sim, 4)},
                "parsability": {"score": p_score, "max": 15, "notes": p_notes}
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
    print("📊 四维评分拆解 (Breakdown):")
    print(f"  1. 硬门槛与求职意向 (Knockout Criteria) : {s['knockout']['score']:2d} / {s['knockout']['max']} 分")
    print(f"  2. 核心关键词覆盖率 (Beat-The-ATS Gap)  : {s['keywords']['score']:2d} / {s['keywords']['max']} 分")
    print(f"  3. 项目语义向量距离 (CV-Matcher Sim)   : {s['semantic']['score']:2d} / {s['semantic']['max']} 分 (余弦值: {s['semantic']['cosine_sim']})")
    print(f"  4. 格式结构与解析度 (Parsability Score): {s['parsability']['score']:2d} / {s['parsability']['max']} 分")
    print("-" * 75)

    if s['knockout']['critical']:
        print("🚨 【一票否决致命告警】:")
        for c in s['knockout']['critical']:
            print(f"   ❌ {c}")
        print()

    if s['knockout']['warnings'] or s['parsability']['notes']:
        print("⚠️ 【结构与格式警示】:")
        for w in s['knockout']['warnings']:
            print(f"   • {w}")
        for n in s['parsability']['notes']:
            print(f"   • {n}")
        print()

    print(f"✅ 已命中核心词 ({len(s['keywords']['matched'])}个):")
    print(f"   {', '.join(s['keywords']['matched']) if s['keywords']['matched'] else '无'}")
    print()

    if s['keywords']['missing']:
        print(f"❌ 致命缺失词 Missing Keywords ({len(s['keywords']['missing'])}个，ATS跑分扣分重灾区):")
        print(f"   👉 {', '.join(s['keywords']['missing'])}")
        print("   💡 优化建议: 请挑选 2~4 个你确实掌握的技术词，直接补充在简历左侧技能栏或项目第一句！")
    else:
        print("🎉 核心技术词完美全覆盖！")

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
