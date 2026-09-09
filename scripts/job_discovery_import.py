"""把视觉提取的岗位线索写入 platform_recruitment_leads 表。

输入：JSON 载荷（由 LLM 读截图后产出），结构：
{
  "channel": "guopin",
  "screenshot_path": "data/job_discovery/screenshots/...",
  "leads": [
    {"company_name": "...", "job_title": "...", "city": "...",
     "salary_text": "...", "job_category": "...", "source_url": "..."}
  ]
}

用法：
    python scripts/job_discovery_import.py --input data/job_discovery/extracts/xxx.json

幂等：dedupe_key = platform:md5(company|title|city)，冲突时跳过并计数。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from career_os_store import DB_PATH, get_db  # noqa: E402

INSERT_SQL = """
INSERT OR IGNORE INTO platform_recruitment_leads (
    platform, company_name, job_title, job_category, city, recruitment_type,
    graduation_range, source_url, apply_url, referral_code, posted_at, deadline,
    status, evidence_confidence, evidence_text, checked_at, notes, dedupe_key,
    salary_text, screenshot_path, capture_method, captured_at
) VALUES (
    :platform, :company_name, :job_title, :job_category, :city, :recruitment_type,
    :graduation_range, :source_url, :apply_url, :referral_code, :posted_at, :deadline,
    :status, :evidence_confidence, :evidence_text, :checked_at, :notes, :dedupe_key,
    :salary_text, :screenshot_path, 'screenshot_vision', :captured_at
)
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="视觉提取 JSON 载荷路径")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    platform = payload["channel"]
    shot = payload.get("screenshot_path", "")
    captured_at = payload.get("captured_at", "")

    con = get_db()
    inserted, skipped = 0, 0
    for lead in payload.get("leads", []):
        company = (lead.get("company_name") or "").strip()
        title = (lead.get("job_title") or "").strip()
        city = (lead.get("city") or "").strip()
        if not company or not title:
            skipped += 1
            continue
        digest = hashlib.md5(f"{company}|{title}|{city}".encode("utf-8")).hexdigest()
        row = {
            "platform": platform,
            "company_name": company,
            "job_title": title,
            "job_category": lead.get("job_category", ""),
            "city": city or "常州",
            "recruitment_type": lead.get("recruitment_type", "社会招聘"),
            "graduation_range": "",
            "source_url": lead.get("source_url", ""),
            "apply_url": "",
            "referral_code": "",
            "posted_at": lead.get("posted_at", ""),
            "deadline": "",
            "status": "需复核",
            "evidence_confidence": "中",
            "evidence_text": lead.get("evidence_text", f"截图提取：{shot}"),
            "checked_at": captured_at,
            "notes": lead.get("notes", ""),
            "dedupe_key": f"{platform}:{digest}",
            "salary_text": lead.get("salary_text", ""),
            "screenshot_path": shot,
            "captured_at": captured_at,
        }
        cur = con.execute(INSERT_SQL, row)
        if cur.rowcount == 1:
            inserted += 1
        else:
            # dedupe_key UNIQUE 冲突 = 已入库的重复线索
            skipped += 1
    con.commit()

    total = con.execute(
        "SELECT COUNT(*) FROM platform_recruitment_leads WHERE platform = ?", (platform,)
    ).fetchone()[0]
    con.close()
    print(f"[{platform}] 新增 {inserted} 条，跳过重复/无效 {skipped} 条；该渠道累计 {total} 条")
    print(f"库: {DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
