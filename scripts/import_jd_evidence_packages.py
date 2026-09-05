#!/usr/bin/env python3
"""把 data/analysis/jd-evidence-packages-*.json 的 JD 对位证据包导入 career_jobs.sqlite（v11）。

幂等：package 按 jd_key upsert；matches 按 (package_id, project_key, bullet_sort, layer) 重灌。

用法：python scripts/import_jd_evidence_packages.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="导入 JD 对位证据包进 Career OS 库")
    parser.add_argument(
        "--input",
        default=str(ROOT / "data" / "analysis" / "jd-evidence-packages-2026-09.json"),
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    conn = get_db()

    for pkg in payload["packages"]:
        conn.execute(
            """
            INSERT INTO jd_evidence_packages
                (jd_key, company_name, job_title, jd_source, focus_layers,
                 hook_strategy, gap_notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(jd_key) DO UPDATE SET
                company_name=excluded.company_name, job_title=excluded.job_title,
                jd_source=excluded.jd_source, focus_layers=excluded.focus_layers,
                hook_strategy=excluded.hook_strategy, gap_notes=excluded.gap_notes,
                updated_at=excluded.updated_at
            """,
            (
                pkg["jd_key"],
                pkg["company_name"],
                pkg["job_title"],
                pkg.get("jd_source", ""),
                json.dumps(pkg.get("focus_layers", []), ensure_ascii=False),
                pkg.get("hook_strategy", ""),
                pkg.get("gap_notes", ""),
            ),
        )
        conn.commit()
        package_id = conn.execute(
            "SELECT id FROM jd_evidence_packages WHERE jd_key = ?", (pkg["jd_key"],)
        ).fetchone()[0]

        conn.execute("DELETE FROM jd_evidence_matches WHERE package_id = ?", (package_id,))
        for m in pkg.get("matches", []):
            conn.execute(
                """
                INSERT INTO jd_evidence_matches
                    (package_id, project_key, bullet_sort, layer, match_role, rationale)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    package_id,
                    m["project_key"],
                    m["bullet_sort"],
                    m["layer"],
                    m.get("match_role", "support"),
                    m.get("rationale", ""),
                ),
            )
        conn.commit()
        print(f"[ok] {pkg['jd_key']}: matches={len(pkg.get('matches', []))} "
              f"layers={pkg.get('focus_layers')}")

    total_pkgs = conn.execute("SELECT COUNT(*) FROM jd_evidence_packages").fetchone()[0]
    total_matches = conn.execute("SELECT COUNT(*) FROM jd_evidence_matches").fetchone()[0]
    print(f"汇总: packages={total_pkgs}, matches={total_matches}")
    conn.close()
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
