"""抓取思必驰北森苏州校招岗位并幂等导入本地 jobs 表。

来源页面的岗位数据由前端接口动态加载，因此脚本同时保存一次原始接口快照，
并使用北森岗位 GUID 作为 ``source_job_id``，避免重复导入或覆盖无关岗位。
脚本不登录、不投递；默认只预览，传入 ``--apply`` 才写入数据库。
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import urllib.parse
import urllib.request
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db  # noqa: E402


SOURCE_URL = (
    "https://aispeech.zhiye.com/campus/jobs?LocId="
    "%5B%7B%22id%22%3A%223205%22%2C%22label%22%3A%22%E8%8B%8F%E5%B7%9E%E5%B8%82%22%7D%5D"
)
API_BASE = "https://aispeech.zhiye.com"
LIST_API = f"{API_BASE}/api/Jobad/GetJobAdPageList"
DETAIL_API = f"{API_BASE}/api/JobAd/GetJobAdInfo"
SOURCE_PLUGIN = "aispeech-zhiye-campus"
EXPECTED_COUNT = 35
LOCATION_ID = "3205"
BUSINESS_TYPE = "2"
DISPLAY_FIELDS = [
    "Category",
    "Kind",
    "LocId",
    "Org",
    "HeadCount",
    "Station",
    "EndTime",
    "PostDate",
    "Salary",
    "Degree",
    "YearsOfWorking",
    "WorkTime",
    "Insurance",
    "Welfare",
    "DetailAddress",
]


def _request(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None,
            referer: str = SOURCE_URL) -> dict[str, Any]:
    body = None
    headers = {
        "Accept": "application/json",
        "EagleEye-TraceID": str(uuid.uuid4()),
        "Referer": referer,
        "User-Agent": "CareerOS/1.0 (public recruitment import)",
    }
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8-sig")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"接口返回不是 JSON 对象: {url}")
    return parsed


def _portal_id() -> str:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"Accept": "text/html", "User-Agent": "CareerOS/1.0 (public recruitment import)"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8-sig")
    match = re.search(r"var BSGlobal = (\{.*?\});", html, flags=re.S)
    if not match:
        raise RuntimeError("来源页面没有找到 BSGlobal 配置，无法确定 portalId")
    config = json.loads(match.group(1))
    portal_id = config.get("PortalId")
    if not portal_id:
        raise RuntimeError("来源页面 BSGlobal 缺少 PortalId")
    return str(portal_id)


def fetch_jobs() -> tuple[str, list[dict[str, Any]]]:
    portal_id = _portal_id()
    payload = {
        "PageIndex": 0,
        "PageSize": 50,
        "KeyWords": "",
        "SpecialType": 0,
        "PortalId": portal_id,
        "DisplayFields": DISPLAY_FIELDS,
        "Category": [BUSINESS_TYPE],
        "LocId": [LOCATION_ID],
    }
    result = _request(LIST_API, method="POST", payload=payload)
    if result.get("Code") != 200:
        raise RuntimeError(f"岗位列表接口失败: {result}")
    jobs = result.get("Data")
    if not isinstance(jobs, list):
        raise RuntimeError("岗位列表接口缺少 Data 数组")
    count = int(result.get("Count") or 0)
    if count != len(jobs):
        raise RuntimeError(f"岗位列表分页不完整: Count={count}, Data={len(jobs)}")
    if count != EXPECTED_COUNT:
        raise RuntimeError(f"来源页面岗位数已变化，期望 {EXPECTED_COUNT}，实际 {count}；停止写库")

    # 列表已包含 Duty/Require；逐条详情请求用于确认详情路由和补齐显示字段。
    detail_ok = 0
    for job in jobs:
        source_id = job.get("Id")
        if not source_id:
            raise RuntimeError(f"岗位缺少北森 GUID: {job.get('JobAdName')}")
        query = urllib.parse.urlencode(
            {
                "jobAdId": source_id,
                "category": BUSINESS_TYPE,
                "displayFields": json.dumps(DISPLAY_FIELDS, ensure_ascii=False, separators=(",", ":")),
                "portalId": portal_id,
            }
        )
        try:
            detail = _request(f"{DETAIL_API}?{query}", referer=f"{API_BASE}/campus/detail?jobAdId={source_id}")
        except Exception:
            continue
        if detail.get("Code") == 200 and isinstance(detail.get("Data"), dict):
            job.update(detail["Data"])
            detail_ok += 1
    print(f"live source: count={count}, detail_verified={detail_ok}/{len(jobs)}, portal_id={portal_id}")
    return portal_id, jobs


def _snapshot_path() -> Path:
    return ROOT / "data" / f"aispeech_campus_jobs_{datetime.now().date().isoformat()}.json"


def save_snapshot(portal_id: str, jobs: list[dict[str, Any]], path: Path) -> None:
    snapshot = {
        "source_url": SOURCE_URL,
        "list_api": LIST_API,
        "portal_id": portal_id,
        "location_filter": {"id": LOCATION_ID, "label": "苏州市"},
        "business_type": BUSINESS_TYPE,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(jobs),
        "jobs": jobs,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _company_match(conn: sqlite3.Connection, api_name: str) -> sqlite3.Row | None:
    row = conn.execute("SELECT * FROM companies WHERE name = ?", (api_name,)).fetchone()
    if row:
        return row
    # 现有库已有“思必驰 (AISpeech)”别名，复用该公司记录而不制造重复公司。
    if "思必驰" in api_name or "AISpeech" in api_name:
        return conn.execute(
            "SELECT * FROM companies WHERE name LIKE '%思必驰%' OR alias LIKE '%AISpeech%' LIMIT 1"
        ).fetchone()
    return None


def _company_ids(conn: sqlite3.Connection, jobs: list[dict[str, Any]]) -> dict[str, int]:
    locations: dict[str, set[str]] = defaultdict(set)
    for job in jobs:
        name = str(job.get("Org") or "思必驰科技股份有限公司").strip()
        locations[name].update(str(x).strip() for x in (job.get("LocNames") or []) if str(x).strip())
    ids: dict[str, int] = {}
    for name, locs in locations.items():
        existing = _company_match(conn, name)
        city = " / ".join(sorted(locs))
        if existing:
            ids[name] = int(existing["id"])
            conn.execute(
                "UPDATE companies SET city=COALESCE(NULLIF(?, ''), city), "
                "campus_url=COALESCE(NULLIF(?, ''), campus_url) WHERE id=?",
                (city, SOURCE_URL, existing["id"]),
            )
            continue
        cur = conn.execute(
            "INSERT INTO companies (name, alias, city, campus_url) VALUES (?, ?, ?, ?)",
            (name, name, city, SOURCE_URL),
        )
        ids[name] = int(cur.lastrowid)
    return ids


def _job_values(job: dict[str, Any], company_id: int) -> tuple[Any, ...]:
    company_name = str(job.get("Org") or "思必驰科技股份有限公司").strip()
    title = str(job.get("JobAdName") or "").strip()
    source_id = str(job["Id"])
    locations = [str(x).strip() for x in (job.get("LocNames") or []) if str(x).strip()]
    city = " / ".join(locations) or "江苏省·苏州市"
    degree = str(job.get("Degree") or "原页未披露").strip()
    duty = str(job.get("Duty") or "原页未披露").strip()
    require = str(job.get("Require") or "原页未披露").strip()
    salary = str(job.get("Salary") or "面议").strip()
    metadata = (
        f"来源岗位ID: {job.get('JobAdId', '')}; 页面筛选: 苏州市(3205); "
        f"原页工作地点: {city}; 招聘人数: {job.get('HeadCount') or '原页未披露'}; "
        f"发布日期: {job.get('PostDate') or '原页未披露'}; 截止时间: {job.get('EndTime') or '原页未披露'}; "
        f"来源: {SOURCE_URL}"
    )
    application_url = f"{API_BASE}/campus/detail?jobAdId={urllib.parse.quote(source_id)}"
    return (
        company_id,
        company_name,
        title,
        str(job.get("Category") or "校园招聘"),
        city,
        salary,
        degree,
        "",
        "待评估",
        duty,
        require,
        metadata,
        application_url,
        SOURCE_PLUGIN,
        source_id,
    )


def apply_jobs(jobs: list[dict[str, Any]]) -> dict[str, int]:
    conn = get_db()
    company_ids = _company_ids(conn, jobs)
    inserted = updated = 0
    for job in jobs:
        company_name = str(job.get("Org") or "思必驰科技股份有限公司").strip()
        values = _job_values(job, company_ids[company_name])
        existing = conn.execute(
            "SELECT id FROM jobs WHERE source_plugin=? AND source_job_id=?",
            (SOURCE_PLUGIN, values[-1]),
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE jobs SET company_id=?, company_name=?, job_title=?, category=?, city=?, salary_text=?,
                   education_req=?, english_req=?, match_level=?, responsibilities=?, requirements=?,
                   matching_analysis=?, application_url=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (*values[:-2], existing[0]),
            )
            updated += 1
        else:
            conn.execute(
                """INSERT INTO jobs
                   (company_id, company_name, job_title, category, city, salary_text, education_req,
                    english_req, match_level, responsibilities, requirements, matching_analysis,
                    application_url, status, source_plugin, source_job_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '待投递', ?, ?)""",
                values,
            )
            inserted += 1
    conn.commit()
    conn.close()
    return {"inserted": inserted, "updated": updated, "companies": len(company_ids)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="将 35 条岗位写入本地数据库")
    parser.add_argument("--snapshot", type=Path, help="覆盖默认快照路径")
    args = parser.parse_args()

    portal_id, jobs = fetch_jobs()
    snapshot = args.snapshot or _snapshot_path()
    save_snapshot(portal_id, jobs, snapshot)
    print(f"snapshot: {snapshot}")
    print(f"preview: jobs={len(jobs)}, companies={len({j.get('Org') for j in jobs})}")
    if not args.apply:
        print("dry-run: database unchanged (use --apply to import)")
        return 0
    result = apply_jobs(jobs)
    print("apply:", json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
