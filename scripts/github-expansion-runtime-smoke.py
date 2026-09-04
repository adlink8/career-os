"""Run the expanded objective and personality banks through real runtimes.

The test uses a temporary copy of the active database and therefore leaves
the user's actual assessment history untouched.
"""

from __future__ import annotations

import builtins
import contextlib
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = ROOT / "data" / "career_jobs.sqlite"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="career-os-github-runtime-") as tmp:
        db_path = Path(tmp) / "career_jobs.sqlite"
        shutil.copy2(SOURCE_DB, db_path)
        previous = os.environ.get("CAREER_OS_DB_PATH")
        os.environ["CAREER_OS_DB_PATH"] = str(db_path)
        try:
            from bin.career_os_store import get_db
            from bin.mock_oa_sandbox import _job_question_tracks, run_choice_quiz, select_choice_questions
            from bin.mock_interview_agent import run_mock_interview
            from bin.personality_assessment import DEFAULT_ASSESSMENT_KIND, FULL_ASSESSMENT_KIND, run_personality_assessment
            from bin.question_bank_adapter import QuestionBankAdapter

            # The import itself is repeated to cover source-key idempotency in
            # the same database that the runtime will consume.
            adapter = QuestionBankAdapter()
            for path, plugin in (
                (ROOT / "data" / "question-bank.github-exam-questions-aptitude.json", "github-exam-questions-aptitude"),
                (ROOT / "data" / "personality-bank.github-bigfive-web-ipip-neo-120.json", "github-bigfive-web-ipip-neo-120"),
            ):
                adapter.load(path, source_plugin=plugin, apply=True)
                adapter.load(path, source_plugin=plugin, apply=True)

            conn = get_db()
            tracks = _job_question_tracks(conn, 1)
            params = [f"%{track}%" for track in tracks]
            where = " OR ".join("company_tags LIKE ?" for _ in tracks)
            choice_rows = conn.execute(
                f"SELECT id, correct_answer, category FROM mock_questions WHERE question_type='choice' AND ({where}) ORDER BY id",
                params,
            ).fetchall()
            expanded_choice_count = conn.execute(
                "SELECT count(*) FROM mock_questions WHERE source_plugin='github-exam-questions-aptitude' AND question_type='choice'"
            ).fetchone()[0]
            personality_quick_count = conn.execute(
                "SELECT count(*) FROM mock_questions WHERE question_type='personality' AND assessment_kind=?",
                (DEFAULT_ASSESSMENT_KIND,),
            ).fetchone()[0]
            personality_full_count = conn.execute(
                "SELECT count(*) FROM mock_questions WHERE question_type='personality' AND assessment_kind=?",
                (FULL_ASSESSMENT_KIND,),
            ).fetchone()[0]
            conn.close()

            selected_rows = select_choice_questions(choice_rows, limit=30, seed=20260903)
            assert len(selected_rows) == 30, len(selected_rows)
            assert [row[0] for row in selected_rows] == [row[0] for row in select_choice_questions(choice_rows, limit=30, seed=20260903)]
            answers = [str(row[1]) for row in selected_rows]
            with patch.object(builtins, "input", side_effect=answers), contextlib.redirect_stdout(io.StringIO()):
                assert run_choice_quiz(job_id=1, limit=30, duration_minutes=30, seed=20260903), "choice runtime failed"
            conn = get_db()
            report = conn.execute(
                "SELECT score, total_score, pass_rate, details_json FROM mock_exam_records WHERE exam_type='choice' AND job_id=1 ORDER BY id DESC LIMIT 1"
            ).fetchone()
            conn.close()
            assert expanded_choice_count == 175, expanded_choice_count
            assert report and tuple(report[:3]) == (30 * 20, 30 * 20, 100.0), report
            details = json.loads(report[3])
            assert details["question_count"] == 30 and details["pool_question_count"] == len(choice_rows), details
            print(f"PASS objective runtime: job 1 selected 30/{len(choice_rows)} targeted questions at 100% (includes {expanded_choice_count} imported aptitude rows)")

            with contextlib.redirect_stdout(io.StringIO()):
                assert run_personality_assessment(job_id=1, responses=["3"] * personality_quick_count), "quick personality runtime failed"
                assert run_personality_assessment(job_id=1, assessment_kind=FULL_ASSESSMENT_KIND, responses=["3"] * personality_full_count), "full personality runtime failed"
            conn = get_db()
            personality_reports = conn.execute(
                "SELECT details_json, score, total_score FROM mock_exam_records WHERE exam_type='personality' AND job_id=1 ORDER BY id DESC"
            ).fetchall()
            conn.close()
            assert len(personality_reports) == 2, personality_reports
            kinds = {json.loads(row[0])["assessment_kind"]: row for row in personality_reports}
            assert set(kinds) == {DEFAULT_ASSESSMENT_KIND, FULL_ASSESSMENT_KIND}, kinds
            assert all(row[2] == 100 for row in kinds.values()), kinds
            print(f"PASS personality runtime: quick {personality_quick_count} + full {personality_full_count} questions scored and persisted in temporary DB")

            # Job 17 is an IoT/embedded JD.  Verify that the new open-ended
            # embedded source is actually selected by the JD-aware interview
            # runtime, rather than merely existing in SQLite.
            conn = get_db()
            company_id = conn.execute("SELECT company_id FROM jobs WHERE id=17").fetchone()[0]
            conn.close()
            answer = "我会先复现并缩小范围，再用日志、示波器或测试用例验证假设，最后补充回滚和回归方案。"
            with patch.object(builtins, "input", side_effect=[answer] * 12), contextlib.redirect_stdout(io.StringIO()):
                assert run_mock_interview(str(company_id), job_id=17), "interview runtime failed"
            conn = get_db()
            transcript = conn.execute(
                "SELECT qa_transcript_json FROM mock_interview_reports WHERE job_id=17 ORDER BY id DESC LIMIT 1"
            ).fetchone()[0]
            conn.close()
            context = json.loads(transcript).get("context", {})
            selected = context.get("selected_questions", [])
            assert any(item.get("source_plugin") == "github-embedded-interview-prep" for item in selected), selected
            print("PASS interview runtime: IoT JD 17 selected the new embedded GitHub source")
            print("PASS expanded runtime uses temporary DB only")
            return 0
        finally:
            if previous is None:
                os.environ.pop("CAREER_OS_DB_PATH", None)
            else:
                os.environ["CAREER_OS_DB_PATH"] = previous


if __name__ == "__main__":
    raise SystemExit(main())
