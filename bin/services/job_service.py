#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Career OS — Job & Pipeline Repository Service (岗位与招聘管线公共服务层)
封装 SQLite 查询、岗位检索、投递状态跃迁与管线统计，消除跨模块 SQL 冗余。
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from career_os_store import add_timeline_event, get_db
except ModuleNotFoundError:
    from bin.career_os_store import add_timeline_event, get_db


class JobService:
    """统一岗位与招聘管线服务层"""

    @staticmethod
    def get_db_connection() -> sqlite3.Connection:
        """获取项目统一管理的 SQLite 数据库连接"""
        return get_db()

    @classmethod
    def get_job(cls, job_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
        """
        获取单个岗位的完整实体字典。
        包含 ATS、面试 Agent、项目候选匹配等所需的所有标准化字段。
        """
        close_needed = False
        if conn is None:
            conn = cls.get_db_connection()
            close_needed = True
        try:
            row = conn.execute(
                """
                SELECT id, company_id, company_name, job_title, category, city, salary_text,
                       education_req, english_req, match_level, responsibilities, requirements,
                       matching_analysis, application_url, status, priority, updated_at
                FROM jobs WHERE id = ?
                """,
                (int(job_id),),
            ).fetchone()
            if not row:
                return None

            title = row[3] or ""
            resp = row[10] or ""
            req = row[11] or ""
            full_text = f"{title}\n{resp}\n{req}".strip()

            return {
                "id": row[0],
                "company_id": row[1],
                "company_name": row[2],
                "company": row[2],  # alias
                "job_title": title,
                "title": title,      # alias
                "category": row[4] or "",
                "city": row[5] or "",
                "salary_text": row[6] or "",
                "education_req": row[7] or "",
                "english_req": row[8] or "",
                "match_level": row[9] or "",
                "responsibilities": resp,
                "requirements": req,
                "matching_analysis": row[12] or "",
                "application_url": row[13] or "",
                "status": row[14] or "",
                "priority": row[15],
                "updated_at": row[16] or "",
                "full_text": full_text,
            }
        finally:
            if close_needed:
                conn.close()

    @classmethod
    def get_job_detail(cls, job_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
        """获取岗位详细信息（联合 companies 表企业主数据）"""
        close_needed = False
        if conn is None:
            conn = cls.get_db_connection()
            close_needed = True
        try:
            row = conn.execute(
                """
                SELECT j.id, j.company_name, j.job_title, j.category, j.city, j.salary_text, j.education_req, 
                       j.english_req, j.match_level, j.responsibilities, j.requirements, j.matching_analysis, 
                       j.application_url, j.status, c.website, c.campus_url, c.welfare_summary
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                WHERE j.id = ?
                """,
                (int(job_id),),
            ).fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "company_name": row[1] or "",
                "job_title": row[2] or "",
                "category": row[3] or "",
                "city": row[4] or "",
                "salary_text": row[5] or "",
                "education_req": row[6] or "",
                "english_req": row[7] or "",
                "match_level": row[8] or "",
                "responsibilities": row[9] or "",
                "requirements": row[10] or "",
                "matching_analysis": row[11] or "",
                "application_url": row[12] or "",
                "status": row[13] or "",
                "website": row[14] or "",
                "campus_url": row[15] or "",
                "welfare_summary": row[16] or "",
            }
        finally:
            if close_needed:
                conn.close()

    @classmethod
    def list_jobs(cls, conn: Optional[sqlite3.Connection] = None) -> List[Tuple[Any, ...]]:
        """按优先级升序检索所有岗位概览清单"""
        close_needed = False
        if conn is None:
            conn = cls.get_db_connection()
            close_needed = True
        try:
            return conn.execute(
                """
                SELECT j.id, j.company_name, j.job_title, j.category, j.city, j.salary_text, j.match_level, j.status
                FROM jobs j
                ORDER BY j.priority ASC, j.id ASC
                """
            ).fetchall()
        finally:
            if close_needed:
                conn.close()

    @classmethod
    def get_all_jobs(cls, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
        """获取所有岗位的完整字典列表，供评估画像及大盘分析使用"""
        close_needed = False
        if conn is None:
            conn = cls.get_db_connection()
            close_needed = True
        try:
            rows = conn.execute(
                """
                SELECT id, company_id, company_name, job_title, category, city, salary_text,
                       education_req, english_req, match_level, responsibilities, requirements,
                       matching_analysis, application_url, status, priority, updated_at
                FROM jobs ORDER BY priority ASC, id ASC
                """
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "company_id": r[1],
                    "company_name": r[2],
                    "company": r[2],
                    "job_title": r[3],
                    "title": r[3],
                    "category": r[4] or "",
                    "city": r[5] or "",
                    "salary_text": r[6] or "",
                    "education_req": r[7] or "",
                    "english_req": r[8] or "",
                    "match_level": r[9] or "",
                    "responsibilities": r[10] or "",
                    "requirements": r[11] or "",
                    "matching_analysis": r[12] or "",
                    "application_url": r[13] or "",
                    "status": r[14] or "",
                    "priority": r[15],
                    "updated_at": r[16] or "",
                    "full_text": f"{r[3] or ''}\n{r[10] or ''}\n{r[11] or ''}".strip(),
                }
                for r in rows
            ]
        finally:
            if close_needed:
                conn.close()

    @classmethod
    def get_pipeline_summary(cls, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        """获取求职全流程管线统计与处于活跃状态（非待投递）的岗位列表"""
        close_needed = False
        if conn is None:
            conn = cls.get_db_connection()
            close_needed = True
        try:
            status_counts = dict(
                conn.execute(
                    """
                    SELECT j.status, COUNT(j.id)
                    FROM jobs j
                    GROUP BY j.status
                    """
                ).fetchall()
            )
            active_rows = conn.execute(
                """
                SELECT j.id, j.company_name, j.job_title, j.city, j.salary_text, j.status
                FROM jobs j
                WHERE j.status != '待投递'
                ORDER BY j.updated_at DESC
                """
            ).fetchall()
            return {
                "counts": status_counts,
                "active_jobs": active_rows,
            }
        finally:
            if close_needed:
                conn.close()

    @classmethod
    def transition_job_status(
        cls,
        job_id: int,
        new_status: str,
        *,
        resume_path: Optional[str] = None,
        notes: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> bool:
        """
        跃迁岗位状态并自动写入审计时间线（Timeline Event）。
        保证状态更新与事件插入的事务原子性。
        """
        close_needed = False
        if conn is None:
            conn = cls.get_db_connection()
            close_needed = True
        try:
            job = conn.execute(
                "SELECT company_name, job_title FROM jobs WHERE id = ?", (int(job_id),)
            ).fetchone()
            if not job:
                return False

            conn.execute(
                "UPDATE jobs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_status, int(job_id)),
            )

            if not notes:
                if resume_path:
                    notes = f"通过 Career OS CLI 标记 (附简历: {os.path.basename(resume_path)})"
                else:
                    notes = f"通过 Career OS 标记状态为【{new_status}】"

            add_timeline_event(
                conn,
                job_id=int(job_id),
                company_name=job[0],
                job_title=job[1],
                event_type=new_status,
                notes=notes,
            )
            conn.commit()
            return True
        finally:
            if close_needed:
                conn.close()

    @classmethod
    def get_company_interview_guides(
        cls, target: Union[int, str], conn: Optional[sqlite3.Connection] = None
    ) -> List[Tuple[Any, ...]]:
        """按企业 ID 或名称/别名模糊查找面试真题与考官指南"""
        close_needed = False
        if conn is None:
            conn = cls.get_db_connection()
            close_needed = True
        try:
            if str(target).isdigit():
                return conn.execute(
                    """
                    SELECT c.id, c.name, g.recruitment_process, g.resume_criteria, g.interview_rounds, 
                           g.typical_questions, g.score_weights, g.avoid_pitfalls, g.authentic_sources
                    FROM companies c
                    LEFT JOIN company_interview_guides g ON c.id = g.company_id
                    WHERE c.id = ?
                    """,
                    (int(target),),
                ).fetchall()
            else:
                return conn.execute(
                    """
                    SELECT c.id, c.name, g.recruitment_process, g.resume_criteria, g.interview_rounds, 
                           g.typical_questions, g.score_weights, g.avoid_pitfalls, g.authentic_sources
                    FROM companies c
                    LEFT JOIN company_interview_guides g ON c.id = g.company_id
                    WHERE c.name LIKE ? OR c.alias LIKE ?
                    """,
                    (f"%{target}%", f"%{target}%"),
                ).fetchall()
        finally:
            if close_needed:
                conn.close()

    @classmethod
    def get_global_stats(cls, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        """获取全景资产数据统计"""
        close_needed = False
        if conn is None:
            conn = cls.get_db_connection()
            close_needed = True
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM companies")
            total_companies = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM jobs")
            total_jobs = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM company_interview_guides")
            total_guides = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM mock_questions")
            total_questions = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM mock_questions WHERE question_type = 'personality'")
            personality_questions = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM mock_questions WHERE question_type = 'personality' AND source_plugin LIKE 'github-%'")
            github_questions = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM mock_questions WHERE question_type = 'personality' AND assessment_kind = 'career-personality-v1'")
            quick_personality_questions = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM mock_questions WHERE question_type = 'personality' AND assessment_kind = 'career-personality-ipip-neo-120'")
            full_personality_questions = c.fetchone()[0]
            source_counts = c.execute(
                "SELECT COALESCE(NULLIF(source_plugin, ''), 'legacy/未标注') AS source, COUNT(*) FROM mock_questions GROUP BY source ORDER BY COUNT(*) DESC, source"
            ).fetchall()
            return {
                "total_companies": total_companies,
                "total_jobs": total_jobs,
                "total_guides": total_guides,
                "total_questions": total_questions,
                "personality_questions": personality_questions,
                "github_questions": github_questions,
                "quick_personality_questions": quick_personality_questions,
                "full_personality_questions": full_personality_questions,
                "source_counts": source_counts,
            }
        finally:
            if close_needed:
                conn.close()
