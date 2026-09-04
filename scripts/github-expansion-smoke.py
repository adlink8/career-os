"""Validate newly added GitHub snapshots and source-based idempotency."""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin import career_os_store, question_bank_adapter


FILES = (
    (ROOT / "data" / "question-bank.github-exam-questions-aptitude.json", "github-exam-questions-aptitude", 175, "choice"),
    (ROOT / "data" / "personality-bank.github-bigfive-web-ipip-neo-120.json", "github-bigfive-web-ipip-neo-120", 120, "personality"),
)


def main() -> int:
    total = 0
    for path, plugin, expected, qtype in FILES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        source = payload.get("source", {})
        questions = payload.get("questions")
        assert source.get("repository", "").startswith("https://github.com/"), path
        assert source.get("license") == "MIT", path
        assert source.get("license_evidence", "").startswith("https://github.com/"), path
        assert isinstance(questions, list) and len(questions) == expected, (path, len(questions or []))
        ids = set()
        for index, question in enumerate(questions, 1):
            assert question.get("question_type") == qtype, (path, index)
            assert question.get("source_question_id") not in ids, (path, index)
            ids.add(question["source_question_id"])
            for key in ("title", "explanation", "source_text", "source_file", "source_module"):
                assert str(question.get(key, "")).strip(), (path, index, key)
            if qtype == "choice":
                assert len(question.get("options", [])) >= 2
                assert question.get("answer") in {"A", "B", "C", "D"}
            else:
                assert len(question.get("options", [])) == 5
                assert question.get("dimension") in {"开放性", "尽责性", "外向性", "宜人性", "情绪反应性"}
                assert question.get("assessment_kind") == "career-personality-ipip-neo-120"
        print(f"PASS {path.name}: {expected} {qtype} questions; unique IDs and MIT evidence")
        total += expected

    # Copy the active DB, import twice, and prove the source key is idempotent.
    with tempfile.TemporaryDirectory(prefix="career-os-github-expansion-") as tmp:
        db_path = Path(tmp) / "career_jobs.sqlite"
        shutil.copy2(ROOT / "data" / "career_jobs.sqlite", db_path)

        def open_db():
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            career_os_store.migrate(conn)
            return conn

        original = question_bank_adapter.get_db
        question_bank_adapter.get_db = open_db
        try:
            adapter = question_bank_adapter.QuestionBankAdapter()
            first = sum(adapter.load(path, source_plugin=plugin, apply=True) for path, plugin, _expected, _type in FILES)
            second = sum(adapter.load(path, source_plugin=plugin, apply=True) for path, plugin, _expected, _type in FILES)
            conn = open_db()
            rows = conn.execute(
                "SELECT source_plugin, question_type, COUNT(*) FROM mock_questions WHERE source_plugin IN (?, ?) GROUP BY source_plugin, question_type",
                (FILES[0][1], FILES[1][1]),
            ).fetchall()
            conn.close()
        finally:
            question_bank_adapter.get_db = original
        assert first == total and second == total, (first, second, total)
        assert sum(int(row[2]) for row in rows) == total, rows
        print(f"PASS adapter idempotency: {total} rows on first and second import; no duplicate source keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
