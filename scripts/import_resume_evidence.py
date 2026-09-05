#!/usr/bin/env python3
"""把 data/analysis/resume-evidence-*.json 的挖掘证据导入 career_jobs.sqlite（v10 简历证据域）。

幂等：项目按 project_key upsert；bullet/QA 按 (project_id, sort_order) 重灌；
里程碑按项目重灌；数字按 (project_id, number_display) upsert。

用法：python scripts/import_resume_evidence.py [--input data/analysis/resume-evidence-2026-09.json]
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
    parser = argparse.ArgumentParser(description="导入简历证据进 Career OS 库")
    parser.add_argument(
        "--input",
        default=str(ROOT / "data" / "analysis" / "resume-evidence-2026-09.json"),
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    conn = get_db()

    for proj in payload["projects"]:
        cur = conn.execute(
            """
            INSERT INTO resume_evidence_projects
                (project_key, display_name, repo_url, positioning, started_on, ended_on,
                 scale_summary, source_report, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(project_key) DO UPDATE SET
                display_name=excluded.display_name, repo_url=excluded.repo_url,
                positioning=excluded.positioning, started_on=excluded.started_on,
                ended_on=excluded.ended_on, scale_summary=excluded.scale_summary,
                source_report=excluded.source_report, updated_at=excluded.updated_at
            """,
            (
                proj["project_key"],
                proj["display_name"],
                proj.get("repo_url", ""),
                proj.get("positioning", ""),
                proj.get("started_on", ""),
                proj.get("ended_on", ""),
                proj.get("scale_summary", ""),
                Path(args.input).name,
            ),
        )
        conn.commit()
        project_id = conn.execute(
            "SELECT id FROM resume_evidence_projects WHERE project_key = ?",
            (proj["project_key"],),
        ).fetchone()[0]

        for b in proj.get("bullets", []):
            conn.execute(
                """
                INSERT INTO resume_evidence_bullets
                    (project_id, sort_order, bullet_text, hook_type, what_it_is,
                     why_this_choice, pitfall_detail, evidence_chain, evidence_status,
                     is_public_verifiable, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(project_id, sort_order) DO UPDATE SET
                    bullet_text=excluded.bullet_text, hook_type=excluded.hook_type,
                    what_it_is=excluded.what_it_is, why_this_choice=excluded.why_this_choice,
                    pitfall_detail=excluded.pitfall_detail, evidence_chain=excluded.evidence_chain,
                    evidence_status=excluded.evidence_status,
                    is_public_verifiable=excluded.is_public_verifiable,
                    notes=excluded.notes, updated_at=excluded.updated_at
                """,
                (
                    project_id,
                    b["sort_order"],
                    b["bullet_text"],
                    b.get("hook_type", ""),
                    b.get("what_it_is", ""),
                    b.get("why_this_choice", ""),
                    b.get("pitfall_detail", ""),
                    b.get("evidence_chain", ""),
                    b.get("evidence_status", "unsupported"),
                    b.get("is_public_verifiable", 0),
                    proj.get("anti_ai_notes", "")[:0] or b.get("notes", ""),
                ),
            )

        # 里程碑按 (project_id, milestone_date) upsert：增量载荷只加/改，不清既有记录
        for m in proj.get("milestones", []):
            conn.execute(
                "DELETE FROM resume_evidence_milestones "
                "WHERE project_id = ? AND milestone_date = ?",
                (project_id, m["milestone_date"]),
            )
            conn.execute(
                """
                INSERT INTO resume_evidence_milestones
                    (project_id, milestone_date, description, session_evidence, commit_evidence)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    m["milestone_date"],
                    m["description"],
                    m.get("session_evidence", ""),
                    m.get("commit_evidence", ""),
                ),
            )

        for n in proj.get("numbers", []):
            conn.execute(
                """
                INSERT INTO resume_evidence_numbers
                    (project_id, number_display, description, verification_method,
                     is_public, usable_on_resume)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, number_display) DO UPDATE SET
                    description=excluded.description,
                    verification_method=excluded.verification_method,
                    is_public=excluded.is_public, usable_on_resume=excluded.usable_on_resume
                """,
                (
                    project_id,
                    n["number_display"],
                    n.get("description", ""),
                    n.get("verification_method", ""),
                    n.get("is_public", 0),
                    n.get("usable_on_resume", 1),
                ),
            )

        for q in proj.get("interview_qa", []):
            conn.execute(
                """
                INSERT INTO resume_evidence_interview_qa
                    (project_id, sort_order, question, answer_points, related_bullet_sort)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project_id, sort_order) DO UPDATE SET
                    question=excluded.question, answer_points=excluded.answer_points,
                    related_bullet_sort=excluded.related_bullet_sort
                """,
                (
                    project_id,
                    q["sort_order"],
                    q["question"],
                    q.get("answer_points", ""),
                    q.get("related_bullet_sort"),
                ),
            )

        conn.commit()
        print(f"[ok] {proj['project_key']}: bullets={len(proj.get('bullets', []))} "
              f"milestones={len(proj.get('milestones', []))} "
              f"numbers={len(proj.get('numbers', []))} qa={len(proj.get('interview_qa', []))}")

    total = {
        t: conn.execute(f"SELECT COUNT(*) FROM resume_evidence_{t}").fetchone()[0]
        for t in ("projects", "bullets", "milestones", "numbers", "interview_qa")
    }
    print("汇总:", total)
    conn.close()
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
