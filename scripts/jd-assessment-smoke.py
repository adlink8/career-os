"""验证当前 jobs 表的 JD 测评映射覆盖。"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.jd_assessment_mapper import profiles_for_jobs, summarize_profiles


def main() -> int:
    conn = sqlite3.connect(ROOT / "data" / "career_jobs.sqlite")
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, company_name, job_title, category, responsibilities, requirements, english_req FROM jobs"
    ).fetchall()
    conn.close()
    profiles = profiles_for_jobs(rows)
    # 岗位库会随真实来源导入扩容；这里验证全量映射覆盖，而不是锁死旧基线数量。
    assert len(profiles) == len(rows), (len(profiles), len(rows))
    assert all(profile["question_families"] for profile in profiles)
    counts = summarize_profiles(profiles)
    required = {"software-testing-ops", "technical-support-fae", "iot-embedded", "data-analysis", "ai-rag"}
    assert required <= set(counts), counts
    print(f"JD assessment smoke: PASS ({len(profiles)} jobs; {counts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
