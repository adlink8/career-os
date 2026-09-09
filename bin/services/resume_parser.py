#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Career OS — Resume & Document Parser Service (简历与文档解析公共服务层)
支持 PDF (PyMuPDF)、Markdown、TXT 提取，并结构化切分意向、技能栏与项目正文。
"""

import os
import re
import sqlite3
from typing import Dict, List

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

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

try:
    from .job_service import JobService
except (ImportError, ValueError):
    try:
        from services.job_service import JobService
    except ImportError:
        JobService = None

def extract_jd_from_db(job_id: int, db_path: str = "data/career_jobs.sqlite") -> Dict[str, str]:
    """Retrieve job details from Career OS sqlite database via JobService."""
    if JobService is not None:
        conn = None
        if db_path != "data/career_jobs.sqlite" and os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
        try:
            job = JobService.get_job(job_id, conn=conn)
            if not job:
                raise ValueError(f"数据库中未找到 ID 为 {job_id} 的岗位")
            return {
                "company": job["company_name"],
                "title": job["job_title"],
                "city": job["city"],
                "responsibilities": job["responsibilities"],
                "requirements": job["requirements"],
                "category": job["category"],
                "full_text": job["full_text"],
            }
        finally:
            if conn:
                conn.close()
    else:
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

def parse_resume_sections(text: str) -> Dict[str, str]:
    """
    Parse resume text into structured components:
      - intent: target job title declaration
      - skills: technical skills block
      - projects: full project experiences text
      - flagship_title: title of the 1st project
      - flagship_text: description of the 1st project
      - char_count: clean character count without whitespaces
    """
    intent_m = re.search(r'(?:求职意向|意向岗位|应聘岗位|求职意向岗位)[：:]\s*([^\n\r]+)', text)
    intent = intent_m.group(1).strip() if intent_m else ""
    if not intent:
        lines = [l.strip() for l in text[:400].split("\n") if l.strip()]
        for l in lines[1:5]:
            if any(k in l for k in ["工程师", "开发", "运维", "专员", "助理", "支持", "经理"]):
                intent = l
                break

    skills_m = re.search(
        r'(?:主要技能|专业技能|核心技能|个人技能|IT技能)([\s\S]*?)(?:专业荣誉|个人概述|核心工程项目经历|项目经历|项目经验|工作经历|教育背景|$)',
        text
    )
    skills = skills_m.group(1).strip() if skills_m else ""

    projects_m = re.search(
        r'(?:核心工程项目经历|项目经历|项目经验|工作经历|工程实战)([\s\S]*?)(?=\n(?:教育背景|专业荣誉|校园经历|资格证书)\b|$)',
        text,
    )
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

    clean_chars = len(re.sub(r'\s+', '', text))

    return {
        "intent": intent,
        "skills": skills,
        "projects": projects,
        "flagship_title": flagship_title,
        "flagship_text": flagship_text,
        "char_count": clean_chars
    }
