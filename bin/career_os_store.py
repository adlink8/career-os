"""Career OS 的本地存储与幂等迁移。

所有运行时脚本都通过本模块解析项目根目录，避免把数据库路径写死在某一台机器上。
迁移只新增表/列，不删除或改写既有求职数据。
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("CAREER_OS_DB_PATH", ROOT / "data" / "career_jobs.sqlite"))
SCHEMA_VERSION = 7

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _add_column(conn: sqlite3.Connection, table: str, name: str, definition: str) -> None:
    if name not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def migrate(conn: sqlite3.Connection) -> None:
    """Apply the local assessment/interview persistence contract once."""

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS career_os_schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )

    # Existing databases already contain the two report tables.  These columns
    # make attempts traceable to a job, provider and rubric without breaking old rows.
    for name, definition in (
        ("job_id", "INTEGER"),
        ("provider", "TEXT"),
        ("rubric_version", "TEXT"),
        ("started_at", "TEXT"),
        ("completed_at", "TEXT"),
    ):
        _add_column(conn, "mock_exam_records", name, definition)
    for name, definition in (
        ("job_id", "INTEGER"),
        ("provider", "TEXT"),
        ("rubric_version", "TEXT"),
        ("started_at", "TEXT"),
        ("completed_at", "TEXT"),
    ):
        _add_column(conn, "mock_interview_reports", name, definition)
    _add_column(conn, "mock_questions", "source_plugin", "TEXT")
    _add_column(conn, "mock_questions", "source_question_id", "TEXT")
    _add_column(conn, "mock_questions", "assessment_kind", "TEXT NOT NULL DEFAULT 'general'")
    _add_column(conn, "mock_questions", "dimension", "TEXT")
    _add_column(conn, "mock_questions", "reverse_scored", "INTEGER NOT NULL DEFAULT 0")
    _add_column(conn, "mock_questions", "scale_min", "INTEGER NOT NULL DEFAULT 1")
    _add_column(conn, "mock_questions", "scale_max", "INTEGER NOT NULL DEFAULT 5")
    _add_column(conn, "jobs", "source_plugin", "TEXT")
    _add_column(conn, "jobs", "source_job_id", "TEXT")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mock_exam_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_record_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_answer TEXT,
            correct INTEGER NOT NULL DEFAULT 0,
            response_ms INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exam_record_id) REFERENCES mock_exam_records(id),
            FOREIGN KEY (question_id) REFERENCES mock_questions(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS interview_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            turn_no TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            score_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES mock_interview_reports(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mock_exam_answers_record ON mock_exam_answers(exam_record_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_interview_turns_report ON interview_turns(report_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mock_questions_assessment "
        "ON mock_questions(question_type, assessment_kind)"
    )

    # Target opportunities are deliberately separate from ``jobs``.  The
    # latter represents imported/confirmed JDs and real application tracking;
    # this table stores a source-backed prospecting pool that still requires
    # a second-pass vacancy check before it becomes a real application.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            city TEXT NOT NULL,
            company_type TEXT NOT NULL,
            target_title TEXT NOT NULL,
            category TEXT NOT NULL,
            source_file TEXT NOT NULL,
            source_company_id TEXT NOT NULL,
            source_rank INTEGER NOT NULL,
            total_score REAL,
            entry_friendliness REAL,
            registration_capital TEXT,
            establishment_date TEXT,
            reg_status TEXT,
            verification_status TEXT NOT NULL DEFAULT '待核实',
            application_status TEXT NOT NULL DEFAULT '待准备',
            application_url TEXT,
            notes TEXT NOT NULL DEFAULT '',
            dedupe_key TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_targets_company "
        "ON job_targets(company_name)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_targets_city "
        "ON job_targets(city)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_targets_verification "
        "ON job_targets(verification_status, application_status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_targets_source "
        "ON job_targets(source_file, source_company_id)"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_target_recruitment_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id INTEGER NOT NULL UNIQUE,
            checked_at TEXT NOT NULL,
            search_engine TEXT NOT NULL,
            query TEXT NOT NULL,
            search_url TEXT NOT NULL,
            autumn_status TEXT NOT NULL,
            internship_status TEXT NOT NULL,
            confidence TEXT NOT NULL,
            result_count INTEGER NOT NULL DEFAULT 0,
            autumn_evidence_url TEXT,
            autumn_evidence_title TEXT,
            autumn_evidence_snippet TEXT,
            autumn_evidence_date TEXT,
            internship_evidence_url TEXT,
            internship_evidence_title TEXT,
            internship_evidence_snippet TEXT,
            internship_evidence_date TEXT,
            notes TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (target_id) REFERENCES job_targets(id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_target_checks_autumn "
        "ON job_target_recruitment_checks(autumn_status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_target_checks_internship "
        "ON job_target_recruitment_checks(internship_status)"
    )

    # Public recruitment posts are kept at their own grain.  A platform post
    # is evidence for a concrete opening (and may contain a referral code),
    # while ``job_targets`` is only a company prospecting pool.  Keeping the
    # two tables separate prevents an unverified target from being mistaken
    # for a live vacancy and preserves the original source text/URL.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS platform_recruitment_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            company_name TEXT NOT NULL,
            job_title TEXT NOT NULL,
            job_category TEXT NOT NULL,
            city TEXT NOT NULL,
            recruitment_type TEXT NOT NULL,
            graduation_range TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL,
            apply_url TEXT NOT NULL DEFAULT '',
            referral_code TEXT NOT NULL DEFAULT '',
            posted_at TEXT NOT NULL DEFAULT '',
            deadline TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT '需复核',
            evidence_confidence TEXT NOT NULL DEFAULT '中',
            evidence_text TEXT NOT NULL,
            checked_at TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            dedupe_key TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Structured JD fields are kept beside the public lead record.  Empty
    # values are intentional when the source post does not disclose a hard
    # requirement; they must not be filled with inferred gates.
    for name, definition in (
        ("jd_summary", "TEXT NOT NULL DEFAULT ''"),
        ("responsibilities", "TEXT NOT NULL DEFAULT ''"),
        ("requirements", "TEXT NOT NULL DEFAULT ''"),
        ("education_requirement", "TEXT NOT NULL DEFAULT ''"),
        ("major_requirement", "TEXT NOT NULL DEFAULT ''"),
        ("skill_requirement", "TEXT NOT NULL DEFAULT ''"),
        ("experience_requirement", "TEXT NOT NULL DEFAULT ''"),
        ("jd_source_url", "TEXT NOT NULL DEFAULT ''"),
        ("jd_evidence_confidence", "TEXT NOT NULL DEFAULT '中'"),
    ):
        _add_column(conn, "platform_recruitment_leads", name, definition)
    for column in (
        "platform",
        "company_name",
        "city",
        "recruitment_type",
        "status",
        "referral_code",
        "dedupe_key",
    ):
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_platform_leads_{column} "
            f"ON platform_recruitment_leads({column})"
        )

    # Resume files remain outside SQLite.  These tables store the logical
    # version, content fingerprint and application linkage so a filename can
    # change without breaking historical submissions.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_key TEXT NOT NULL UNIQUE,
            role_slug TEXT NOT NULL DEFAULT '',
            target_company_slug TEXT NOT NULL DEFAULT '',
            target_job_slug TEXT NOT NULL DEFAULT '',
            version_label TEXT NOT NULL DEFAULT 'v1.0',
            state TEXT NOT NULL DEFAULT 'draft',
            source_relative_path TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            parent_version_id INTEGER,
            FOREIGN KEY (parent_version_id) REFERENCES resume_versions(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_version_id INTEGER,
            file_state TEXT NOT NULL DEFAULT 'draft',
            format TEXT NOT NULL,
            canonical_filename TEXT NOT NULL,
            sha256 TEXT NOT NULL UNIQUE,
            size_bytes INTEGER NOT NULL,
            first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            missing_at TEXT,
            notes TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (resume_version_id) REFERENCES resume_versions(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_artifact_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artifact_id INTEGER NOT NULL,
            relative_path TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            is_current INTEGER NOT NULL DEFAULT 1,
            first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            missing_at TEXT,
            FOREIGN KEY (artifact_id) REFERENCES resume_artifacts(id),
            UNIQUE (relative_path, artifact_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            resume_version_id INTEGER,
            submitted_artifact_id INTEGER,
            submitted_at TEXT,
            channel TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT '待投递',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id),
            FOREIGN KEY (resume_version_id) REFERENCES resume_versions(id),
            FOREIGN KEY (submitted_artifact_id) REFERENCES resume_artifacts(id)
        )
        """
    )
    _add_column(conn, "application_timeline", "application_id", "INTEGER")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_resume_versions_role "
        "ON resume_versions(role_slug, state)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_resume_artifacts_version "
        "ON resume_artifacts(resume_version_id, file_state)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_resume_artifact_locations_artifact "
        "ON resume_artifact_locations(artifact_id, is_current)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_applications_job "
        "ON applications(job_id, status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_applications_resume "
        "ON applications(resume_version_id, submitted_artifact_id)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_applications_job_artifact "
        "ON applications(job_id, submitted_artifact_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_application_timeline_application "
        "ON application_timeline(application_id, event_date)"
    )

    conn.execute(
        "INSERT OR IGNORE INTO career_os_schema_migrations(version, applied_at) VALUES (?, ?)",
        (SCHEMA_VERSION, _utc_now()),
    )
    conn.commit()


def get_db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"数据库文件不存在: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    migrate(conn)
    return conn


def add_timeline_event(
    conn: sqlite3.Connection,
    *,
    application_id: int | None = None,
    job_id: int | None,
    company_name: str,
    job_title: str,
    event_type: str,
    notes: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO application_timeline
            (application_id, job_id, company_name, job_title, event_date, event_type, notes)
        VALUES (?, ?, ?, ?, DATE('now'), ?, ?)
        """,
        (application_id, job_id, company_name, job_title, event_type, notes),
    )
