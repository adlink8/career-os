"""职业性格测评的真实持久化冒烟测试（只使用临时数据库副本）。"""

from __future__ import annotations

import os
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = ROOT / "data" / "career_jobs.sqlite"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="career-os-personality-") as tmp:
        db_path = Path(tmp) / "career_jobs.sqlite"
        shutil.copy2(SOURCE_DB, db_path)
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM mock_exam_records")
        conn.execute("DELETE FROM mock_exam_answers")
        conn.execute("DELETE FROM application_timeline WHERE event_type='职业性格测评完成'")
        conn.commit()
        question_count = conn.execute(
            "SELECT count(*) FROM mock_questions WHERE question_type='personality' AND assessment_kind='career-personality-v1'"
        ).fetchone()[0]
        full_count = conn.execute(
            "SELECT count(*) FROM mock_questions WHERE question_type='personality' AND assessment_kind='career-personality-ipip-neo-120'"
        ).fetchone()[0]
        sample_job_id = str(conn.execute("SELECT min(id) FROM jobs").fetchone()[0])
        conn.close()
        assert question_count > 0 and full_count == 120, (question_count, full_count)
        env = os.environ.copy()
        env["CAREER_OS_DB_PATH"] = str(db_path)
        result = subprocess.run(
            [sys.executable, "bin/career_jobs_cli.py", "personality", sample_job_id],
            cwd=ROOT,
            env=env,
            input="5\n" * question_count,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            sys.stdout.buffer.write(result.stdout.encode("utf-8", errors="replace"))
            sys.stderr.buffer.write(result.stderr.encode("utf-8", errors="replace"))
            raise AssertionError("personality assessment subprocess failed")
        full_result = subprocess.run(
            [sys.executable, "bin/career_jobs_cli.py", "personality", sample_job_id, "--full"],
            cwd=ROOT,
            env=env,
            input="3\n" * full_count,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if full_result.returncode != 0:
            sys.stdout.buffer.write(full_result.stdout.encode("utf-8", errors="replace"))
            sys.stderr.buffer.write(full_result.stderr.encode("utf-8", errors="replace"))
            raise AssertionError("full personality assessment subprocess failed")
        conn = sqlite3.connect(db_path)
        reports = conn.execute(
            "SELECT details_json, provider, score, total_score FROM mock_exam_records WHERE exam_type='personality' ORDER BY id"
        ).fetchall()
        answer_count = conn.execute("SELECT count(*) FROM mock_exam_answers").fetchone()[0]
        timeline_count = conn.execute(
            "SELECT count(*) FROM application_timeline WHERE event_type='职业性格测评完成'"
        ).fetchone()[0]
        conn.close()
        assert len(reports) == 2, reports
        report_kinds = {json.loads(row[0])["assessment_kind"]: row for row in reports}
        assert set(report_kinds) == {"career-personality-v1", "career-personality-ipip-neo-120"}, report_kinds
        assert all(row[1] == "local-rubric" and row[3] == 100 for row in report_kinds.values()), report_kinds
        assert answer_count == question_count + full_count, (answer_count, question_count, full_count)
        assert timeline_count == 2, timeline_count
    print("Personality smoke: PASS (temporary DB only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
