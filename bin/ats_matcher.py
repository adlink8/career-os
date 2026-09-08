#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Career OS — ATS Preflight Matcher CLI (校招ATS投前模拟打分机器人)
模块化分层架构门面：
- 技术词典与NLP服务: bin/services/tech_lexicon.py
- 简历与文本解析服务: bin/services/resume_parser.py
- 核心五维评分引擎: bin/services/ats_engine.py
- 诊断报告渲染展示: bin/services/ats_reporter.py
"""

import os
import sys
import json
import argparse

# 确保在任何目录下运行都能找到 bin 及 services
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 从公共服务层统一导入
try:
    from services.tech_lexicon import (
        TECH_DICTIONARY,
        ALL_TECH_KEYWORDS,
        match_keyword_in_text,
        extract_keywords_from_jd,
        hybrid_tokenizer,
    )
    from services.resume_parser import (
        extract_text_from_file,
        extract_jd_from_db,
        parse_resume_sections,
    )
    from services.ats_engine import (
        ATSEngine,
        ATSScorer,
    )
    from services.ats_reporter import (
        render_terminal_report,
        render_json_report,
        print_report,
    )
except ImportError:
    from bin.services.tech_lexicon import (
        TECH_DICTIONARY,
        ALL_TECH_KEYWORDS,
        match_keyword_in_text,
        extract_keywords_from_jd,
        hybrid_tokenizer,
    )
    from bin.services.resume_parser import (
        extract_text_from_file,
        extract_jd_from_db,
        parse_resume_sections,
    )
    from bin.services.ats_engine import (
        ATSEngine,
        ATSScorer,
    )
    from bin.services.ats_reporter import (
        render_terminal_report,
        render_json_report,
        print_report,
    )


def main():
    parser = argparse.ArgumentParser(description="Career OS ATS Preflight Matcher")
    parser.add_argument("--resume", required=True, help="Path to resume file (.pdf, .md, .txt)")
    parser.add_argument("--job-id", type=int, help="Job ID from data/career_jobs.sqlite")
    parser.add_argument("--jd-file", help="Path to JD text file")
    parser.add_argument("--jd-text", help="Raw JD text string")
    parser.add_argument("--jd-title", default="自定义目标岗位", help="Job title if using jd-file or jd-text")
    parser.add_argument("--min-score", type=int, default=70, help="Minimum passing score (default 70)")
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

    scorer = ATSEngine(jd_info, resume_text)
    results = scorer.run_full_diagnosis()

    if args.json:
        print(render_json_report(results))
    else:
        render_terminal_report(results, jd_info.get("title", args.jd_title), args.resume)

    if results["verdict"] == "FAIL_KNOCKOUT" or results["total_score"] < args.min_score:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
