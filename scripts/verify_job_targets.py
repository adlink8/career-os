"""Independent database-level checks for the Jiangsu job target pool."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_FILE = ROOT / "data" / "job_target_verification.json"
EXPECTED_COUNT = 500


def normalise(value: object) -> str:
    return re.sub(r"\s+", "", "" if value is None else str(value)).casefold()


def duplicate_keys(rows: list[dict[str, object]], fields: tuple[str, ...]) -> list[dict[str, object]]:
    groups: dict[tuple[str, ...], list[int]] = {}
    for row in rows:
        key = tuple(normalise(row.get(field)) for field in fields)
        groups.setdefault(key, []).append(int(row["id"]))
    return [
        {"key": list(key), "ids": ids}
        for key, ids in groups.items()
        if len(ids) > 1
    ]


def run_checks() -> tuple[dict[str, object], int]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from bin.career_os_store import get_db

    conn = get_db()
    try:
        target_rows = [dict(row) for row in conn.execute("SELECT * FROM job_targets ORDER BY id")]
        existing_jobs = [
            dict(row)
            for row in conn.execute("SELECT id, company_name, city, job_title FROM jobs")
        ]
        recruitment_checks = [
            dict(row)
            for row in conn.execute(
                """
                SELECT c.target_id, c.autumn_status, c.internship_status,
                       c.autumn_evidence_url, c.internship_evidence_url
                FROM job_target_recruitment_checks c
                JOIN job_targets j ON j.id = c.target_id
                """
            )
        ]
        platform_leads = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM platform_recruitment_leads ORDER BY id"
            )
        ]
        schema_version = int(
            conn.execute("SELECT MAX(version) FROM career_os_schema_migrations").fetchone()[0]
        )
        jobs_count = int(conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])
        timeline_count = int(
            conn.execute("SELECT COUNT(*) FROM application_timeline").fetchone()[0]
        )
    finally:
        conn.close()

    status_counts = {
        "verification_status": dict(
            Counter(row["verification_status"] for row in target_rows)
        ),
        "application_status": dict(Counter(row["application_status"] for row in target_rows)),
    }
    logical_duplicates = duplicate_keys(
        target_rows, ("company_name", "city", "target_title")
    )
    source_duplicates = duplicate_keys(
        target_rows, ("source_company_id", "target_title")
    )
    existing_job_keys = {
        (
            normalise(row["company_name"]),
            normalise(row["city"]),
            normalise(row["job_title"]),
        )
        for row in existing_jobs
    }
    exact_overlaps = [
        {
            "target_id": row["id"],
            "company_name": row["company_name"],
            "city": row["city"],
            "target_title": row["target_title"],
        }
        for row in target_rows
        if (
            normalise(row["company_name"]),
            normalise(row["city"]),
            normalise(row["target_title"]),
        )
        in existing_job_keys
    ]

    checks = {
        "target_count_is_500": len(target_rows) == EXPECTED_COUNT,
        "dedupe_key_unique": len({row["dedupe_key"] for row in target_rows}) == len(target_rows),
        "logical_duplicate_free": not logical_duplicates,
        "source_id_title_duplicate_free": not source_duplicates,
        "no_exact_overlap_with_jobs": not exact_overlaps,
        "all_targets_pending_verification": all(
            row["verification_status"] == "待核实" for row in target_rows
        ),
        "none_marked_as_applied": all(
            row["application_status"] != "已投递" for row in target_rows
        ),
        "schema_version_at_least_3": schema_version >= 3,
        "recruitment_checks_cover_all_companies": len(recruitment_checks)
        == len({row["company_name"] for row in target_rows}),
        "recruitment_queries_no_failures": all(
            row["autumn_status"] != "查询失败" and row["internship_status"] != "查询失败"
            for row in recruitment_checks
        ),
        "recruitment_evidence_urls_present": all(
            (not row["autumn_status"].startswith("明确") or row["autumn_evidence_url"])
            and (not row["internship_status"].startswith("明确") or row["internship_evidence_url"])
            for row in recruitment_checks
        ),
        "platform_leads_have_unique_dedupe_keys": len(
            {row["dedupe_key"] for row in platform_leads}
        )
        == len(platform_leads),
        "platform_leads_have_source_and_evidence": all(
            row["source_url"].startswith(("https://", "http://"))
            and bool(row["evidence_text"])
            for row in platform_leads
        ),
        "platform_leads_have_structured_jd": all(
            bool(row.get("jd_summary"))
            and bool(row.get("responsibilities"))
            and bool(row.get("requirements"))
            and bool(row.get("education_requirement"))
            and bool(row.get("major_requirement"))
            and bool(row.get("skill_requirement"))
            and bool(row.get("experience_requirement"))
            and row.get("jd_source_url", "").startswith(("https://", "http://"))
            and row.get("jd_evidence_confidence") in {"高", "中", "低"}
            for row in platform_leads
        ),
        "platform_leads_are_jiangsu_city_scoped": all(
            any(token in row["city"] for token in ("南京", "苏州", "无锡", "常州", "扬州", "昆山"))
            for row in platform_leads
        ),
        "platform_referral_codes_are_explicitly_evidenced": all(
            (not row["referral_code"])
            or (row["referral_code"] in row["evidence_text"])
            for row in platform_leads
        ),
    }
    result = "PASS" if all(checks.values()) else "FAIL"
    report: dict[str, object] = {
        "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "result": result,
        "checks": checks,
        "target_count": len(target_rows),
        "distinct_companies": len({row["company_name"] for row in target_rows}),
        "distinct_cities": len({row["city"] for row in target_rows}),
        "status_counts": status_counts,
        "recruitment_check_count": len(recruitment_checks),
        "platform_lead_count": len(platform_leads),
        "platform_lead_platform_counts": dict(
            Counter(row["platform"] for row in platform_leads)
        ),
        "platform_lead_status_counts": dict(
            Counter(row["status"] for row in platform_leads)
        ),
        "platform_lead_recruitment_type_counts": dict(
            Counter(row["recruitment_type"] for row in platform_leads)
        ),
        "platform_lead_referral_code_count": sum(
            bool(row["referral_code"]) for row in platform_leads
        ),
        "platform_lead_unique_referral_code_count": len(
            {row["referral_code"] for row in platform_leads if row["referral_code"]}
        ),
        "platform_lead_jd_coverage_count": sum(
            bool(row.get("jd_summary"))
            and bool(row.get("responsibilities"))
            and bool(row.get("requirements"))
            for row in platform_leads
        ),
        "platform_lead_jd_confidence_counts": dict(
            Counter(row.get("jd_evidence_confidence", "未填") for row in platform_leads)
        ),
        "recruitment_autumn_status_counts": dict(
            Counter(row["autumn_status"] for row in recruitment_checks)
        ),
        "recruitment_internship_status_counts": dict(
            Counter(row["internship_status"] for row in recruitment_checks)
        ),
        "logical_duplicates": logical_duplicates,
        "source_id_duplicates": source_duplicates,
        "exact_existing_job_overlaps": exact_overlaps,
        "existing_jobs_count": jobs_count,
        "application_timeline_count": timeline_count,
        "schema_version": schema_version,
    }
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"result={result}")
    print(
        f"target_count={len(target_rows)} distinct_companies={report['distinct_companies']} "
        f"distinct_cities={report['distinct_cities']}"
    )
    print(
        f"duplicates: dedupe_key={len(target_rows) - len({row['dedupe_key'] for row in target_rows})} "
        f"logical={len(logical_duplicates)} source_id_title={len(source_duplicates)} "
        f"exact_job_overlap={len(exact_overlaps)}"
    )
    print(f"status_counts={json.dumps(status_counts, ensure_ascii=False, sort_keys=True)}")
    print(
        f"recruitment_checks={len(recruitment_checks)} "
        f"autumn={json.dumps(report['recruitment_autumn_status_counts'], ensure_ascii=False, sort_keys=True)} "
        f"internship={json.dumps(report['recruitment_internship_status_counts'], ensure_ascii=False, sort_keys=True)}"
    )
    print(
        f"platform_leads={len(platform_leads)} "
        f"platforms={json.dumps(report['platform_lead_platform_counts'], ensure_ascii=False, sort_keys=True)} "
        f"status={json.dumps(report['platform_lead_status_counts'], ensure_ascii=False, sort_keys=True)} "
        f"types={json.dumps(report['platform_lead_recruitment_type_counts'], ensure_ascii=False, sort_keys=True)} "
        f"referral_codes={report['platform_lead_referral_code_count']} "
        f"unique_referral_codes={report['platform_lead_unique_referral_code_count']}"
    )
    print(
        f"platform_jd_coverage={report['platform_lead_jd_coverage_count']} "
        f"jd_confidence={json.dumps(report['platform_lead_jd_confidence_counts'], ensure_ascii=False, sort_keys=True)}"
    )
    print(
        f"unchanged_boundary: jobs={jobs_count} application_timeline={timeline_count} "
        f"schema_version={schema_version}"
    )
    print(f"report={REPORT_FILE}")
    if result != "PASS":
        print(
            "failed_checks="
            + json.dumps(
                [name for name, passed in checks.items() if not passed], ensure_ascii=False
            )
        )
    return report, 0 if result == "PASS" else 1


if __name__ == "__main__":
    _, exit_code = run_checks()
    raise SystemExit(exit_code)
