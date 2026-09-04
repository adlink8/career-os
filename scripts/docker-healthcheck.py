"""Small, read-only container health check for the Career OS SQLite runtime."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def main() -> int:
    path = Path(os.environ.get("CAREER_OS_DB_PATH", "/app/data/career_jobs.sqlite"))
    if not path.exists():
        print(f"database missing: {path}")
        return 1
    try:
        with sqlite3.connect(path) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"jobs", "mock_questions", "mock_exam_records", "mock_interview_reports"}
            missing = required - tables
            if missing:
                print(f"database schema incomplete: {sorted(missing)}")
                return 1
            conn.execute("SELECT 1").fetchone()
    except sqlite3.Error as exc:
        print(f"database check failed: {type(exc).__name__}")
        return 1
    print("career-os database healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
