"""按 profile.yml 动态定每家名额，写入 jobs.recommendation_rank（1..N 入选，0 未入选）。"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db
from bin.services.job_profile_quota import allocate_company_slots, load_profile
from bin.services.job_role_family import role_family

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")


def main() -> None:
    profile = load_profile()
    conn = get_db()
    rows = conn.execute(
        """
        SELECT j.id, j.company_id, c.alias, j.job_title, j.city, j.education_req,
               j.responsibilities, j.requirements, j.recommendation_weight,
               j.application_url
        FROM jobs j
        JOIN companies c ON c.id = j.company_id
        WHERE COALESCE(j.status,'') IN ('待投递','待沟通内推')
          AND COALESCE(c.pool,'sme_startup') IN ('sme_startup','applied')
        ORDER BY c.alias, j.id
        """
    ).fetchall()
    by_co = defaultdict(list)
    meta = {}
    for r in rows:
        job = {
            "id": r[0],
            "company_id": r[1],
            "alias": r[2],
            "job_title": r[3],
            "city": r[4],
            "education_req": r[5],
            "responsibilities": r[6],
            "requirements": r[7],
            "recommendation_weight": r[8],
            "application_url": r[9],
        }
        by_co[r[1]].append(job)
        meta[r[1]] = r[2]

    conn.execute(
        """
        UPDATE jobs SET recommendation_rank = 0, updated_at = ?
        WHERE id IN (
          SELECT j.id FROM jobs j JOIN companies c ON c.id=j.company_id
          WHERE COALESCE(j.status,'') IN ('待投递','待沟通内推')
            AND COALESCE(c.pool,'sme_startup') IN ('sme_startup','applied')
        )
        """,
        (NOW,),
    )

    total_pick = 0
    print("alias\tquota\tcandidates\trank\tw\tfit\tfamily\tcity\ttitle")
    for cid, jobs in sorted(by_co.items(), key=lambda kv: meta[kv[0]] or ""):
        picked = allocate_company_slots(jobs, profile)
        total_pick += len(picked)
        alias = meta[cid]
        if not picked:
            print(f"{alias}\t0\t{len(jobs)}\t-\t-\t-\t-\t(无匹配，名额0)")
            continue
        for item in picked:
            family = role_family(str(item.get("job_title") or ""))
            conn.execute(
                """
                UPDATE jobs
                SET recommendation_rank = ?, category = ?, updated_at = ?
                WHERE id = ?
                """,
                (item["recommendation_rank"], family, NOW, item["id"]),
            )
            print(
                f"{alias}\t{len(picked)}\t{len(jobs)}\t{item['recommendation_rank']}\t"
                f"{item.get('recommendation_weight')}\t{item.get('fit_score')}\t"
                f"{family}\t{item.get('city')}\t{item.get('job_title')}"
            )
    conn.commit()
    print("---")
    print(f"companies={len(by_co)} picked={total_pick}")
    conn.close()


if __name__ == "__main__":
    main()
