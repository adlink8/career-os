"""岗位来源统一适配器。

接收 CareerDesk/CareerSail/career-ops 等工具的 JSON/CSV 导出。默认只预览，
必须显式 ``apply=True`` 才写入本地岗位库；适配器永远不登录、不自动投递。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

try:
    from career_os_store import get_db
except ModuleNotFoundError:
    from bin.career_os_store import get_db


class JobSourceAdapter:
    capability = "job_source"

    def __init__(self, manifest=None):
        self.manifest = manifest

    def provide(self, capability: str):
        return self if capability == self.capability else None

    def load(self, source: str | Path, *, source_plugin: str = "external", apply: bool = False) -> dict[str, int]:
        path = Path(source)
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        else:
            raw = json.loads(path.read_text(encoding="utf-8"))
            rows = raw.get("jobs", raw) if isinstance(raw, dict) else raw
        if not isinstance(rows, list):
            raise ValueError("岗位导出必须是数组，或包含 jobs 数组的 JSON 对象")

        normalized = [self._normalize(item, idx) for idx, item in enumerate(rows, 1)]
        if not apply:
            return {"preview": len(normalized), "companies": len({x["company_name"] for x in normalized}), "inserted": 0, "updated": 0}

        conn = get_db()
        inserted = updated = 0
        for item in normalized:
            company = conn.execute("SELECT id FROM companies WHERE name = ?", (item["company_name"],)).fetchone()
            if company:
                company_id = company[0]
                conn.execute(
                    "UPDATE companies SET website=COALESCE(NULLIF(?, ''), website), campus_url=COALESCE(NULLIF(?, ''), campus_url) WHERE id=?",
                    (item["website"], item["campus_url"], company_id),
                )
            else:
                cur = conn.execute(
                    "INSERT INTO companies (name, alias, city, website, campus_url) VALUES (?, ?, ?, ?, ?)",
                    (item["company_name"], item["company_name"], item["city"], item["website"], item["campus_url"]),
                )
                company_id = cur.lastrowid
            existing = conn.execute(
                "SELECT id FROM jobs WHERE source_plugin = ? AND source_job_id = ?",
                (source_plugin, item["source_job_id"]),
            ).fetchone()
            values = (
                company_id, item["company_name"], item["job_title"], item["category"], item["city"], item["salary_text"],
                item["education_req"], item["english_req"], item["match_level"], item["responsibilities"], item["requirements"],
                item["matching_analysis"], item["application_url"], source_plugin, item["source_job_id"],
            )
            if existing:
                conn.execute(
                    """
                    UPDATE jobs SET company_id=?, company_name=?, job_title=?, category=?, city=?, salary_text=?,
                        education_req=?, english_req=?, match_level=?, responsibilities=?, requirements=?, matching_analysis=?,
                        application_url=? WHERE id=?
                    """,
                    (*values[:-2], existing[0]),
                )
                updated += 1
            else:
                conn.execute(
                    """
                    INSERT INTO jobs
                        (company_id, company_name, job_title, category, city, salary_text, education_req, english_req,
                         match_level, responsibilities, requirements, matching_analysis, application_url, status, source_plugin, source_job_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '待投递', ?, ?)
                    """,
                    values,
                )
                inserted += 1
        conn.commit()
        conn.close()
        return {"preview": len(normalized), "companies": len({x["company_name"] for x in normalized}), "inserted": inserted, "updated": updated}

    @staticmethod
    def _normalize(raw: dict[str, Any], index: int) -> dict[str, str]:
        if not isinstance(raw, dict):
            raise ValueError(f"第 {index} 条岗位不是对象")
        company = str(raw.get("company_name", raw.get("company", ""))).strip()
        title = str(raw.get("job_title", raw.get("title", raw.get("position", "")))).strip()
        if not company or not title:
            raise ValueError(f"第 {index} 条缺少 company_name/job_title")
        return {
            "source_job_id": str(raw.get("source_job_id", raw.get("id", index))),
            "company_name": company,
            "job_title": title,
            "category": str(raw.get("category", "校招")),
            "city": str(raw.get("city", "")),
            "salary_text": str(raw.get("salary_text", raw.get("salary", ""))),
            "education_req": str(raw.get("education_req", raw.get("education", ""))),
            "english_req": str(raw.get("english_req", raw.get("english", ""))),
            "match_level": str(raw.get("match_level", "待评估")),
            "responsibilities": str(raw.get("responsibilities", "")),
            "requirements": str(raw.get("requirements", "")),
            "matching_analysis": str(raw.get("matching_analysis", raw.get("analysis", ""))),
            "application_url": str(raw.get("application_url", raw.get("url", ""))),
            "website": str(raw.get("website", "")),
            "campus_url": str(raw.get("campus_url", "")),
        }


def create_plugin(manifest=None):
    return JobSourceAdapter(manifest=manifest)

