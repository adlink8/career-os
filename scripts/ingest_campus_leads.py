"""Ingest newly discovered campus jobs and update company campus URLs.

Single source of truth: data/career_jobs.sqlite.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("D:/ADLINK/Myproject/career-os")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_dedupe_key(company: str, title: str, city: str) -> str:
    raw = f"{company.strip().lower()}|{title.strip().lower()}|{city.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def ingest_findings(data: dict) -> dict:
    conn = get_db()
    now = utc_now()
    portals_updated = 0
    leads_added = 0
    jobs_added = 0

    # 1. Update company portals if live_url is provided and differs
    for p in data.get("portals", []):
        raw_cname = (p.get("company") or p.get("company_name") or "").strip()
        live_url = (p.get("live_url") or p.get("current_url") or p.get("resolved_url") or "").strip()
        status = str(p.get("status", "")).upper()
        
        # Clean company name
        cname = raw_cname.split("(")[0].split("（")[0].strip()
        if not cname:
            cname = raw_cname

        if cname and live_url and (live_url.startswith("http://") or live_url.startswith("https://")):
            row = conn.execute(
                "SELECT id, campus_url, name FROM companies WHERE name=? OR alias=? OR name LIKE ? OR alias LIKE ?",
                (cname, cname, f"%{cname[:4]}%", f"%{cname[:4]}%"),
            ).fetchone()
            if row:
                old_url = row[1] or ""
                matched_id = row[0]
                matched_name = row[2]
                if old_url != live_url:
                    conn.execute(
                        "UPDATE companies SET campus_url=? WHERE id=?",
                        (live_url, matched_id),
                    )
                    portals_updated += 1
                    print(f"[PORTAL UPDATED] {matched_name}: {old_url} -> {live_url}")
            else:
                print(f"[PORTAL SKIPPED / NOT IN COMPANIES TABLE] {cname} -> {live_url}")

    # 2. Ingest jobs
    for j in data.get("jobs", []):
        raw_cname = (j.get("company_name") or j.get("company") or "").strip()
        cname = raw_cname.split("(")[0].split("（")[0].strip()
        if not cname:
            cname = raw_cname

        title = j.get("job_title", "").strip()
        
        loc_val = j.get("city") or j.get("locations") or "长三角/待定"
        if isinstance(loc_val, list):
            city = "/".join(loc_val).strip()
        else:
            city = str(loc_val).strip()

        category = (j.get("category") or j.get("job_category") or "技术研发").strip()
        rec_type = j.get("recruitment_type", "2027届校招/实习").strip()
        salary = j.get("salary", "面议").strip()
        apply_url = (j.get("apply_url") or j.get("url") or "").strip()
        
        resp_raw = j.get("responsibilities") or j.get("description") or j.get("description_summary") or ""
        if isinstance(resp_raw, list):
            resp = "\n".join(str(x) for x in resp_raw).strip()
        else:
            resp = str(resp_raw).strip()

        reqs_raw = j.get("requirements") or j.get("tech_stack") or ""
        if isinstance(reqs_raw, list):
            reqs = ", ".join(str(x) for x in reqs_raw).strip()
        else:
            reqs = str(reqs_raw).strip()

        ts_raw = j.get("tech_stack")
        if ts_raw:
            ts_str = ", ".join(ts_raw) if isinstance(ts_raw, list) else str(ts_raw)
            if ts_str not in reqs:
                reqs = f"技术栈: {ts_str}\n{reqs}".strip()


        grad_range = j.get("graduation_range", "2026-2027届").strip()
        edu_req = j.get("education_requirement", "本科及以上").strip()

        if not cname or not title:
            continue

        dkey = make_dedupe_key(cname, title, city)

        # Check platform_recruitment_leads
        lead_exists = conn.execute(
            "SELECT id FROM platform_recruitment_leads WHERE dedupe_key=? OR (company_name=? AND job_title=?)",
            (dkey, cname, title),
        ).fetchone()

        if not lead_exists:
            conn.execute(
                """
                INSERT INTO platform_recruitment_leads (
                    platform, company_name, job_title, job_category, city,
                    recruitment_type, graduation_range, source_url, apply_url,
                    status, evidence_confidence, evidence_text, checked_at,
                    notes, dedupe_key, responsibilities, requirements,
                    education_requirement, jd_source_url, created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    '在招', '高', ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """,
                (
                    "官网校招",
                    cname,
                    title,
                    category,
                    city,
                    rec_type,
                    grad_range,
                    apply_url,
                    apply_url,
                    f"2026/2027校招在招岗位，抓取自官方校招门户：{apply_url}",
                    now,
                    j.get("notes", "由校招链接探索子Agent自动抓取"),
                    dkey,
                    resp,
                    reqs,
                    edu_req,
                    apply_url,
                ),
            )
            leads_added += 1
            print(f"[NEW LEAD ADDED] {cname} - {title} ({city})")

        # Check jobs table
        job_exists = conn.execute(
            "SELECT id FROM jobs WHERE (company_name LIKE ? OR company_name=?) AND job_title=?",
            (f"%{cname[:4]}%", cname, title),
        ).fetchone()

        if not job_exists:
            comp_row = conn.execute(
                "SELECT id, name FROM companies WHERE name=? OR alias=? OR name LIKE ? OR alias LIKE ?",
                (cname, cname, f"%{cname[:4]}%", f"%{cname[:4]}%"),
            ).fetchone()
            comp_id = comp_row[0] if comp_row else None
            actual_cname = comp_row[1] if comp_row else cname

            conn.execute(
                """
                INSERT INTO jobs (
                    company_id, company_name, job_title, category, city,
                    salary_text, education_req, english_req, match_level,
                    responsibilities, requirements, application_url, status,
                    priority, source_plugin, source_job_id, updated_at
                ) VALUES (
                    ?, ?, ?, '校园招聘', ?,
                    ?, ?, '', '待评估',
                    ?, ?, ?, '待投递',
                    3, 'campus-crawler-agent', ?, CURRENT_TIMESTAMP
                )
                """,
                (
                    comp_id,
                    actual_cname,
                    title,
                    city,
                    salary,
                    edu_req,
                    resp,
                    reqs,
                    apply_url,
                    dkey[:16],
                ),
            )
            jobs_added += 1
            print(f"[NEW TARGET JOB RECORDED] {actual_cname} - {title} ({city})")

    conn.commit()
    conn.close()

    return {
        "portals_updated": portals_updated,
        "leads_added": leads_added,
        "jobs_added": jobs_added,
    }



if __name__ == "__main__":
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            data = json.load(f)
        res = ingest_findings(data)
        print("Ingestion summary:", res)
    else:
        print("Usage: python scratch/ingest_campus_leads.py <json_path>")
