#!/usr/bin/env python3
"""把 data/analysis/interview-drill-*.json 的面试拷打点导入 career_jobs.sqlite（v12）。

幂等：按 (project_key, feature, question) upsert。

用法：python scripts/import_interview_drill.py [--input data/analysis/interview-drill-2026-09.json]
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
    parser = argparse.ArgumentParser(description="导入面试拷打点进 Career OS 库")
    parser.add_argument(
        "--input",
        default=str(ROOT / "data" / "analysis" / "interview-drill-2026-09.json"),
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    conn = get_db()

    for proj in payload["projects"]:
        count = 0
        for feat in proj.get("features", []):
            for p in feat.get("points", []):
                conn.execute(
                    """
                    INSERT INTO interview_drill_points
                        (project_key, feature, phase, depth, question,
                         answer_points, my_thinking, evidence, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(project_key, feature, question) DO UPDATE SET
                        phase=excluded.phase, depth=excluded.depth,
                        answer_points=excluded.answer_points,
                        my_thinking=excluded.my_thinking,
                        evidence=excluded.evidence, updated_at=excluded.updated_at
                    """,
                    (
                        proj["project_key"],
                        feat["feature"],
                        feat.get("phase", ""),
                        p.get("depth", 1),
                        p["question"],
                        p.get("answer", ""),
                        p.get("my_thinking", ""),
                        p.get("evidence", ""),
                    ),
                )
                count += 1
        conn.commit()
        print(f"[ok] {proj['project_key']}: features={len(proj.get('features', []))} points={count}")

    total = conn.execute("SELECT COUNT(*) FROM interview_drill_points").fetchone()[0]
    print(f"汇总: drill_points={total}")
    conn.close()
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
