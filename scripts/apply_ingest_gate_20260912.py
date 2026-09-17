"""把 CET-4 硬门槛、过细不像培养的待投岗标成门禁拦截，不删行。"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db
from bin.services.job_ingest_gate import ingest_gate_reasons

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")


def main() -> None:
    conn = get_db()
    rows = conn.execute(
        """
        SELECT j.id, j.job_title, j.responsibilities, j.requirements,
               j.recommendation_reason, j.english_req, j.recommendation_weight
        FROM jobs j
        JOIN companies c ON c.id = j.company_id
        WHERE COALESCE(j.status,'') IN ('待投递','待沟通内推')
          AND COALESCE(c.pool,'sme_startup') IN ('sme_startup','applied')
        """
    ).fetchall()
    n = 0
    for row in rows:
        jid, title, duty, req, reason, eng, weight = row
        reasons = ingest_gate_reasons(title or "", duty or "", req or "")
        if not reasons:
            continue
        tag = "；".join(reasons)
        new_reason = f"【门禁拦截】{tag}"
        if reason and "【门禁拦截】" not in (reason or ""):
            new_reason = f"{new_reason}。原：{reason}"
        new_eng = eng or ""
        if "CET" in tag or "四级" in tag:
            new_eng = "CET-4硬门槛（未持有）"
        conn.execute(
            """
            UPDATE jobs
            SET recommendation_weight = MIN(COALESCE(recommendation_weight, 99), 22),
                priority = 3,
                match_level = '待评估',
                english_req = ?,
                recommendation_reason = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (new_eng, new_reason, NOW, jid),
        )
        n += 1
        print(f"[GATE] {jid} {title} | {tag}")
    conn.commit()
    print(f"gated={n}")
    conn.close()


if __name__ == "__main__":
    main()
