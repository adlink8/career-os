"""Validate GitHub-sourced open interview question snapshots.

These snapshots intentionally use ``question_type=interview`` rather than
inventing MCQ distractors. The runtime interview adapter is responsible for
consuming this schema; the existing OA adapter should not import these files
as choice questions.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin import career_os_store, question_bank_adapter


FILES = (
    ROOT / "data" / "question-bank.github-seringhong-embedded-interview.json",
    ROOT / "data" / "question-bank.github-ather-rag-interview.json",
    ROOT / "data" / "question-bank.github-embedded-interview-prep.json",
)

PLUGINS = {
    FILES[0].name: "github-seringhong-embedded-interview",
    FILES[1].name: "github-ather-rag-interview",
    FILES[2].name: "github-embedded-interview-prep",
}


def main() -> int:
    seen: set[tuple[str, str]] = set()
    total = 0
    by_category: dict[str, int] = {}
    for path in FILES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        source = payload.get("source", {})
        assert source.get("repository", "").startswith("https://github.com/")
        assert source.get("license") == "MIT"
        assert source.get("license_evidence", "").startswith("https://github.com/")
        assert payload.get("schema") == "interview_questions-v1"
        questions = payload.get("questions")
        assert isinstance(questions, list) and questions
        for index, question in enumerate(questions, 1):
            assert question.get("question_type") == "interview", (path, index)
            assert question.get("assessment_kind") == "technical-interview", (path, index)
            for key in ("source_question_id", "source_text", "source_file", "source_module", "title", "explanation", "category", "company_tags"):
                assert str(question.get(key, "")).strip(), (path, index, key)
            key = (source["repository"], question["source_question_id"])
            assert key not in seen, key
            seen.add(key)
            total += 1
            category = question["category"]
            by_category[category] = by_category.get(category, 0) + 1
    print(f"PASS specialized interview snapshots: {total} questions")
    for category, count in sorted(by_category.items()):
        print(f"  {category}: {count}")
    print("PASS unique source IDs, MIT evidence, trace fields and explanations")

    # Exercise the same adapter used by the runtime, but never touch the
    # project's real database.  A second load proves source-based idempotency.
    with tempfile.TemporaryDirectory(prefix="career-os-specialized-smoke-") as tmp:
        db_path = Path(tmp) / "smoke.sqlite"
        seed = sqlite3.connect(db_path)
        seed.executescript(
            """
            CREATE TABLE mock_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT, difficulty TEXT, company_tags TEXT,
                question_type TEXT, title TEXT, options_json TEXT,
                correct_answer TEXT, test_cases_json TEXT, starter_code TEXT,
                explanation TEXT
            );
            CREATE TABLE mock_exam_records (id INTEGER PRIMARY KEY AUTOINCREMENT);
            CREATE TABLE mock_interview_reports (id INTEGER PRIMARY KEY AUTOINCREMENT);
            CREATE TABLE jobs (id INTEGER PRIMARY KEY AUTOINCREMENT);
            """
        )
        seed.commit()
        seed.close()

        def open_smoke_db():
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            career_os_store.migrate(conn)
            return conn

        original_get_db = question_bank_adapter.get_db
        question_bank_adapter.get_db = open_smoke_db
        try:
            adapter = question_bank_adapter.QuestionBankAdapter()
            first = sum(
                adapter.load(path, source_plugin=PLUGINS[path.name], apply=True)
                for path in FILES
            )
            second = sum(
                adapter.load(path, source_plugin=PLUGINS[path.name], apply=True)
                for path in FILES
            )
            check = open_smoke_db()
            rows = check.execute("SELECT COUNT(*) FROM mock_questions").fetchone()[0]
            interview_rows = check.execute(
                "SELECT COUNT(*) FROM mock_questions WHERE question_type='interview'"
            ).fetchone()[0]
            distinct_sources = check.execute(
                "SELECT COUNT(*) FROM (SELECT DISTINCT source_plugin, source_question_id FROM mock_questions)"
            ).fetchone()[0]
            check.close()
            assert first == total and second == total
            assert rows == total and interview_rows == total and distinct_sources == total
        finally:
            question_bank_adapter.get_db = original_get_db
    print(f"PASS adapter imports interview type and remains idempotent ({total} rows, {total} unique source keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
