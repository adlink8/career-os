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
SCHEMA_VERSION = 20

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _add_column(conn: sqlite3.Connection, table: str, name: str, definition: str) -> None:
    if _table_exists(conn, table) and name not in _columns(conn, table):
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

    # v18: 项目分层契约 —— flagship（每份简历必选）/ normal（按 JD 择取）/ excluded（排雷，不上简历）
    _add_column(conn, "resume_evidence_projects", "priority", "TEXT NOT NULL DEFAULT 'normal'")

    # v19: 网申页实时快照（扩展捕获的 JobContext，ATS/会审的权威 JD 输入）
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_page_contexts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at TEXT NOT NULL,
            url TEXT NOT NULL,
            host TEXT,
            company TEXT,
            title TEXT NOT NULL DEFAULT '',
            jd_text TEXT NOT NULL DEFAULT '',
            hard_filters_json TEXT NOT NULL DEFAULT '{}',
            keywords_json TEXT NOT NULL DEFAULT '[]',
            form_schema_json TEXT NOT NULL DEFAULT '[]',
            raw_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_page_contexts_url ON job_page_contexts(url, captured_at)"
    )
    _add_column(conn, "job_page_contexts", "job_ad_id", "TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_page_contexts_job_ad ON job_page_contexts(job_ad_id)"
    )

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
        # v15: screenshot-based discovery (模拟真人浏览 + 截图 + 视觉提取).
        # salary_text 保留来源页原始写法（如 "8-12K·13薪"、"面议"），不做数值化。
        # screenshot_path 指向本次采集的页面截图（相对项目根），供溯源复核。
        # capture_method 区分采集链路：manual / screenshot_vision / script。
        ("salary_text", "TEXT NOT NULL DEFAULT ''"),
        ("screenshot_path", "TEXT NOT NULL DEFAULT ''"),
        ("capture_method", "TEXT NOT NULL DEFAULT 'manual'"),
        ("captured_at", "TEXT NOT NULL DEFAULT ''"),
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
    if _table_exists(conn, "application_timeline"):
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_application_timeline_application "
            "ON application_timeline(application_id, event_date)"
        )

    # JD 驱动的 GitHub 项目候选库。候选与简历提案分表，避免外部仓库
    # 在未核验许可证、贡献边界和个人证据前进入简历。
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS github_project_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            repo_full_name TEXT NOT NULL,
            repo_url TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT '',
            topics_json TEXT NOT NULL DEFAULT '[]',
            stars INTEGER NOT NULL DEFAULT 0,
            forks INTEGER NOT NULL DEFAULT 0,
            open_issues INTEGER NOT NULL DEFAULT 0,
            license_spdx TEXT NOT NULL DEFAULT '',
            license_status TEXT NOT NULL DEFAULT 'unknown',
            archived INTEGER NOT NULL DEFAULT 0,
            pushed_at TEXT NOT NULL DEFAULT '',
            repo_updated_at TEXT NOT NULL DEFAULT '',
            matched_terms_json TEXT NOT NULL DEFAULT '[]',
            relevance_score REAL NOT NULL DEFAULT 0,
            search_query TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'candidate',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id),
            UNIQUE (job_id, provider, repo_full_name)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_github_project_candidates_job "
        "ON github_project_candidates(job_id, status, relevance_score DESC)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_project_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            resume_key TEXT NOT NULL,
            resume_path TEXT NOT NULL,
            claim_level TEXT NOT NULL DEFAULT 'reference',
            evidence_text TEXT NOT NULL,
            proposal_markdown TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'confirmed',
            confirmed_at TEXT,
            applied_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES github_project_candidates(id),
            UNIQUE (candidate_id, resume_key)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_resume_project_proposals_status "
        "ON resume_project_proposals(status, resume_key)"
    )

    # v9 GitHub 数据域：本人账号的全量仓库、提交与档案快照。
    # 仓库以 full_name 幂等 upsert；提交以 (repo_full_name, sha) 幂等。
    # fork 仓库只存元数据与精确提交数，不逐条入库（避免外部项目噪声）。
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS github_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            login TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            bio TEXT NOT NULL DEFAULT '',
            company TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL DEFAULT '',
            public_repos INTEGER NOT NULL DEFAULT 0,
            followers INTEGER NOT NULL DEFAULT 0,
            total_authored_commits INTEGER,
            account_created_at TEXT NOT NULL DEFAULT '',
            fetched_at TEXT NOT NULL,
            raw_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS github_repositories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL DEFAULT '',
            owner TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            homepage TEXT NOT NULL DEFAULT '',
            html_url TEXT NOT NULL DEFAULT '',
            primary_language TEXT NOT NULL DEFAULT '',
            languages_json TEXT NOT NULL DEFAULT '{}',
            topics_json TEXT NOT NULL DEFAULT '[]',
            license_spdx TEXT NOT NULL DEFAULT '',
            default_branch TEXT NOT NULL DEFAULT '',
            stars INTEGER NOT NULL DEFAULT 0,
            forks INTEGER NOT NULL DEFAULT 0,
            open_issues INTEGER NOT NULL DEFAULT 0,
            size_kb INTEGER NOT NULL DEFAULT 0,
            is_private INTEGER NOT NULL DEFAULT 0,
            is_fork INTEGER NOT NULL DEFAULT 0,
            is_archived INTEGER NOT NULL DEFAULT 0,
            commit_count INTEGER,
            commits_imported INTEGER NOT NULL DEFAULT 0,
            repo_created_at TEXT NOT NULL DEFAULT '',
            repo_updated_at TEXT NOT NULL DEFAULT '',
            repo_pushed_at TEXT NOT NULL DEFAULT '',
            fetched_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_github_repositories_language "
        "ON github_repositories(primary_language, is_fork)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_github_repositories_pushed "
        "ON github_repositories(repo_pushed_at DESC)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS github_commits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_full_name TEXT NOT NULL,
            sha TEXT NOT NULL,
            author_login TEXT NOT NULL DEFAULT '',
            author_name TEXT NOT NULL DEFAULT '',
            author_email TEXT NOT NULL DEFAULT '',
            committed_at TEXT NOT NULL DEFAULT '',
            message TEXT NOT NULL DEFAULT '',
            additions INTEGER,
            deletions INTEGER,
            html_url TEXT NOT NULL DEFAULT '',
            fetched_at TEXT NOT NULL,
            UNIQUE (repo_full_name, sha),
            FOREIGN KEY (repo_full_name) REFERENCES github_repositories(full_name)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_github_commits_repo_date "
        "ON github_commits(repo_full_name, committed_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_github_commits_author "
        "ON github_commits(author_login, committed_at)"
    )

    # v10 简历证据域：会话/git 挖掘出的可上简历、可扛拷打的证据资产。
    # 粒度：项目 → bullet 候选（三层拷打答案+钩子类型）/ 里程碑 / 可验证数字 / 面试 QA。
    # bullet 以 (project_id, sort_order) 幂等重灌；数字以 (project_id, number_display) 幂等。
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_evidence_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_key TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            repo_url TEXT NOT NULL DEFAULT '',
            positioning TEXT NOT NULL DEFAULT '',
            started_on TEXT NOT NULL DEFAULT '',
            ended_on TEXT NOT NULL DEFAULT '',
            scale_summary TEXT NOT NULL DEFAULT '',
            source_report TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_evidence_bullets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            bullet_text TEXT NOT NULL,
            hook_type TEXT NOT NULL DEFAULT '',
            what_it_is TEXT NOT NULL DEFAULT '',
            why_this_choice TEXT NOT NULL DEFAULT '',
            pitfall_detail TEXT NOT NULL DEFAULT '',
            evidence_chain TEXT NOT NULL DEFAULT '',
            evidence_status TEXT NOT NULL DEFAULT 'unsupported',
            is_public_verifiable INTEGER NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES resume_evidence_projects(id),
            UNIQUE (project_id, sort_order)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_evidence_milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            milestone_date TEXT NOT NULL,
            description TEXT NOT NULL,
            session_evidence TEXT NOT NULL DEFAULT '',
            commit_evidence TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (project_id) REFERENCES resume_evidence_projects(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_evidence_numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            number_display TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            verification_method TEXT NOT NULL DEFAULT '',
            is_public INTEGER NOT NULL DEFAULT 0,
            usable_on_resume INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (project_id) REFERENCES resume_evidence_projects(id),
            UNIQUE (project_id, number_display)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_evidence_interview_qa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            question TEXT NOT NULL,
            answer_points TEXT NOT NULL,
            related_bullet_sort INTEGER,
            FOREIGN KEY (project_id) REFERENCES resume_evidence_projects(id),
            UNIQUE (project_id, sort_order)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_resume_evidence_bullets_project "
        "ON resume_evidence_bullets(project_id, sort_order)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_resume_evidence_bullets_status "
        "ON resume_evidence_bullets(evidence_status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_resume_evidence_numbers_project "
        "ON resume_evidence_numbers(project_id, usable_on_resume)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_resume_evidence_qa_project "
        "ON resume_evidence_interview_qa(project_id, sort_order)"
    )

    # v11 JD 对位证据域：按具体 JD 从简历证据域挖掘不同层面的组合包。
    # 层面（layer）：技术深挖 / 数据工程 / 质量测试 / 工程治理 / 运维部署 / AI 协作。
    # 一个 JD 一个 package；每条匹配记录指向 resume_evidence_bullets 的 (project_key, sort_order)。
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jd_evidence_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jd_key TEXT NOT NULL UNIQUE,
            company_name TEXT NOT NULL,
            job_title TEXT NOT NULL,
            jd_source TEXT NOT NULL DEFAULT '',
            focus_layers TEXT NOT NULL DEFAULT '[]',
            hook_strategy TEXT NOT NULL DEFAULT '',
            gap_notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jd_evidence_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER NOT NULL,
            project_key TEXT NOT NULL,
            bullet_sort INTEGER NOT NULL,
            layer TEXT NOT NULL,
            match_role TEXT NOT NULL DEFAULT 'support',
            rationale TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (package_id) REFERENCES jd_evidence_packages(id),
            UNIQUE (package_id, project_key, bullet_sort, layer)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_jd_evidence_packages_company "
        "ON jd_evidence_packages(company_name)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_jd_evidence_matches_package "
        "ON jd_evidence_matches(package_id, match_role)"
    )

    # v12 面试拷打域：按项目逐功能下钻的问答卡。
    # 每行 = 一个可能被提问的点：depth 1=是什么 2=为什么取舍 3=踩坑细节；
    # my_thinking 存项目主人当时的原始思考（会话概括），evidence 存 session/commit/ADR 溯源。
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS interview_drill_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_key TEXT NOT NULL,
            feature TEXT NOT NULL,
            phase TEXT NOT NULL DEFAULT '',
            depth INTEGER NOT NULL DEFAULT 1,
            question TEXT NOT NULL,
            answer_points TEXT NOT NULL DEFAULT '',
            my_thinking TEXT NOT NULL DEFAULT '',
            evidence TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (project_key, feature, question)
        )
        """
    )
    # v13 校招投递限制与岗位推荐权重域
    _add_column(conn, "companies", "max_campus_applications", "INTEGER")
    _add_column(conn, "companies", "campus_application_rules", "TEXT")
    _add_column(conn, "jobs", "recommendation_weight", "REAL")
    _add_column(conn, "jobs", "recommendation_rank", "INTEGER")
    _add_column(conn, "jobs", "recommendation_reason", "TEXT")
    if "company_id" in _columns(conn, "jobs"):
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_company_rank "
            "ON jobs(company_id, recommendation_rank)"
        )

    # v14 简历生成规则与硬红线契约库 (resume_generation_rules)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_generation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_category TEXT NOT NULL,
            rule_key TEXT NOT NULL UNIQUE,
            rule_title TEXT NOT NULL,
            rule_content TEXT NOT NULL,
            rationale TEXT NOT NULL DEFAULT '',
            priority INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_resume_rules_category "
        "ON resume_generation_rules(rule_category, is_active)"
    )

    rules_seed = [
        (
            "layout_intent",
            "no_target_location",
            "求职意向去目标地点",
            "求职意向严禁携带具体目标地点（如'常州武进区/新北区'），仅保留'岗位名称 + 2027届统招本科'。",
            "避免地域标签过早限定求职范围，提升简历泛化通用性",
            1,
        ),
        (
            "layout",
            "strict_1_page_a4_balanced",
            "严格A4物理单页且版面饱满",
            "PDF必须严格为1页，无任何跨页溢出；版面上下均衡饱满，严禁下半部大面积留白；行距与段距合理分布。",
            "校招纸质与电子简历物理单页规范，避免排版松散或溢出",
            1,
        ),
        (
            "layout",
            "sidebar_font_spacing_and_wrapping",
            "左侧栏字间距规整与优雅换行",
            "侧边栏宽度受限时使用左对齐和break-word，严禁在窄列使用justify导致汉字间隙被拉伸；长词组必须优雅换行，严禁单个字单独掉到下一行。",
            "确保中英文混排视觉美感与阅读体验",
            1,
        ),
        (
            "education",
            "education_bachelor_only",
            "教育背景仅限常州大学全日制本科",
            "教育背景必须且仅有：常州大学 | 计算机科学与技术 | 本科 | 2027年6月毕业。彻底清除专科、专升本、江苏信息职业技术学院等任何专科字样。删除大学英语四六级/英语文档表述，保留省级技能大赛（省级获奖）与软著。",
            "用户最高红线，杜绝任何历史冗余与无关信息干扰",
            1,
        ),
        (
            "skill",
            "ai_skill_first_no_prompt",
            "AI技能首位与彻底禁用Prompt",
            "主要技能第一条必须是AI技能：熟练使用 Codex、Claude Code、Gemini 等大模型工具；掌握 MCP 协议规范与 Skill 自动化应用，具备 RAG 知识检索与 Agent 工作流能力。全篇严禁出现 Prompt / Prompt 工程等词汇。技能项禁用精通/熟悉等分级标签。",
            "突显先进开发工具链与协议理解，杜绝空泛无意义的Prompt标签",
            1,
        ),
        (
            "project",
            "no_ai_whitewash_on_projects",
            "禁止给每个项目强扣AI帽子",
            "只有原本具备 RAG、向量切片和状态机代码的项目（pk-core、novel-mind）才说明 AI 能力；物联网通信、Wireshark抓包排障、Linux运维、技术博客和技能大赛绝不强加任何AI标签，展现扎实的工程本质。",
            "防止面试官认为项目全为AI虚构生成，还原候选人真实动手开发能力",
            1,
        ),
        (
            "anti_inflation",
            "no_hallucinated_percentages",
            "严禁编造无基线伪精确百分比",
            "严禁在简历中编造'84%提升至98.5%'、'误报率降至0.5%'、'降低62%'等无底层测试量测依据的伪精确数字。",
            "遵守简历审计红线，防止面试时被深挖量测工具导致当场证伪",
            1,
        ),
        (
            "anti_inflation",
            "no_inflated_magnitude_counts",
            "严禁堆砌几千几万的夸大数字",
            "校招简历严禁堆砌'15.8万处脏数据'、'1500+个测试用例'、'2800+行代码'等在面试官看来明显夸大、不真实的数字。重点放在业务痛点、具体做了什么模块、采用了什么机制以及带来哪些真实提升。",
            "消除夸大感与吹牛感，建立踏实、严谨的工程人设",
            1,
        ),
        (
            "project",
            "focus_what_done_and_lift",
            "务实说明做了什么与具体提升",
            "项目描述必须采用'业务痛点/背景 + 做了什么模块/技术手段 + 具体带来哪些实在提升'的叙事结构。例如：通过复合索引将查询延迟由 280ms 降低至 38ms；通过指数退避（1s至60s）解决瞬断重连网关堵塞；通过 Checksum 增量缓存缩短回归耗时；通过时间戳归一化消除多源数据时序错乱。",
            "以真实工程方案和实测改变量化价值，逻辑闭环",
            1,
        ),
        (
            "project",
            "no_fake_domain_wrapping",
            "严禁将项目虚假包装为不存在的车间MES",
            "不得将开源软件或个人数据项目强行包装成'制造车间生产工序/MES/WMS'。主数据治理岗对位多源数据清洗、SQL比对与数据库调优；智能制造岗以真实的物联网设备通信（MQTT/HTTP）、工业网关部署、Wireshark抓包排障、局域网组网为主干，辅以数据清洗与系统测试能力。",
            "坚守代码与事实一致性，确保面试现场可随时打开仓库对照演示",
            1,
        ),
        (
            "layout",
            "concise_section_titles",
            "模块标题简洁规范（个人概述就叫个人概述）",
            "主栏各模块标题使用标准简洁命名（如'个人概述'、'核心工程与数据治理项目经历'、'专业竞赛与工程实践'），个人概述模块标题直接使用'个人概述'，严禁随意添加'与专业定位'、'与制造数字化定位'等冗余后缀。",
            "保证简历模块标题严谨清晰，杜绝画蛇添足的自造标题",
            1,
        ),
        (
            "project",
            "min_four_bullets_per_project",
            "核心项目经历每项必须恰好四点",
            "核心工程项目经历每项必须恰好包含 4 个要点（bullet points），不多不少。四个要点按固定维度分配：(1) 架构/数据建模，(2) 核心技术实现/协议，(3) 性能优化/疑难排障，(4) 自动化测试/质量门禁或量化成果。严禁少于 4 点导致内容单薄，也严禁超过 4 点挤爆 A4 单页版面。",
            "用户明确要求：每个项目必须分四点。恰好四点既系统化展现工程深度与闭环能力，又与 A4 单页版面均衡约束（balanced_vertical_rhythm_no_crowding）严格兼容",
            1,
        ),
        (
            "project",
            "skill_project_echo",
            "技能点与项目必须互相呼应（严禁空中楼阁）",
            "简历技能区与项目经历必须双向呼应：(1) 技能区每一个技能点必须能对应到所选 3 个项目中至少一个的具体实现（佐证映射见 config/profile.yml skills.project_backing），无项目佐证的技能严禁上简历；(2) 每个项目 bullet 必须显式体现技能区列出的技能点（写出框架/协议/工具名），让面试官能从项目读到技能、从技能定位到项目；(3) 学习中技能只放 learning 区，严禁混入项目叙述冒充已掌握。",
            "用户明确要求：项目落实要体现出技能点，两者呼应，而不是空中楼阁。双向呼应既防技能区空泛无据，也防项目描述堆砌名词与技能区脱节",
            1,
        ),
        (
            "project",
            "exactly_three_projects_per_resume",
            "每份简历必须且只能展示三个项目",
            "每份简历项目经历模块必须且只能包含 3 个项目，不多不少。选材规则：NovelMind 与 pk-core（个人数据/知识智能系统）为库里 priority='flagship' 的重点项目，必须无条件入选占 2 席；第 3 席根据目标 JD 从 priority='normal' 项目池中择取对位最强的 1 个（如物联网岗位选 iot-skills-competition，全栈岗位选 pet-hospital-management-system）。严禁放 2 个或 4 个以上项目。",
            "用户明确要求：每份简历必须三个项目。3 项目 × 4 bullet = 12 个要点，恰好支撑 A4 单页饱满版面；双旗舰保底展示 AI 工程与数据治理深度，第三席按 JD 动态对位最大化 ATS 匹配",
            1,
        ),
        (
            "quantification",
            "quantified_engineering_metrics",
            "工程成果必须包含真实量化指标",
            "项目与经历描述必须具备真实、可信、有依据的量化指标支撑（如延迟从 280ms 压降至 38ms、缓存复用率 82%、回归耗时缩减 60%、14,031 条结论悬空率 0.00%、指数退避 1s~60s、20+ 篇深度技术长文等），严禁无量化的纯抽象叙述。",
            "量化指标能给面试官提供具体、可检验的工程价值证据，强化说服力与严谨度",
            1,
        ),
        (
            "layout",
            "balanced_vertical_rhythm_no_crowding",
            "版面垂直韵律均衡（严禁上半太挤、下半太空）",
            "A4 单页简历必须实现上下垂直韵律均衡分布。严禁将正文内容、字号与行距过度压缩堆叠在上半部而导致下半部大面积留白（底部留白严禁超过 25mm）；正文字号需维持在 9.8px~10.2px、行高 1.50~1.55、列表项间距 4.5px~5.5px，标题与模块间距舒展大方，左右侧栏与主栏高度协调，实现全页呼吸感与饱满度统一。",
            "避免因过度防跨页导致字体过小、行距过挤，给面试官造成压抑紧凑感，同时彻底杜绝页面下半部产生明显空洞与排版松垮",
            1,
        ),
    ]
    for cat, key, title, content, rat, pri in rules_seed:
        conn.execute(
            """
            INSERT INTO resume_generation_rules
                (rule_category, rule_key, rule_title, rule_content, rationale, priority, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(rule_key) DO UPDATE SET
                rule_category = excluded.rule_category,
                rule_title = excluded.rule_title,
                rule_content = excluded.rule_content,
                rationale = excluded.rationale,
                priority = excluded.priority,
                updated_at = CURRENT_TIMESTAMP
            """,
            (cat, key, title, content, rat, pri),
        )

    # v16 简历排版模板契约库 (resume_layout_templates)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_layout_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_key TEXT NOT NULL UNIQUE,
            template_name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            page_width_mm REAL NOT NULL DEFAULT 210.0,
            page_height_mm REAL NOT NULL DEFAULT 297.0,
            bottom_margin_min_mm REAL NOT NULL DEFAULT 18.0,
            bottom_margin_max_mm REAL NOT NULL DEFAULT 28.0,
            sidebar_width_mm REAL NOT NULL DEFAULT 65.0,
            main_width_mm REAL NOT NULL DEFAULT 145.0,
            photo_width_mm REAL NOT NULL DEFAULT 46.0,
            photo_height_mm REAL NOT NULL DEFAULT 60.0,
            css_content TEXT NOT NULL,
            layout_config_json TEXT NOT NULL DEFAULT '{}',
            is_default INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    v3_css = """@page {
  size: A4 portrait;
  margin: 0;
}
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}
html, body {
  width: 210mm;
  height: 297mm;
  margin: 0;
  padding: 0;
  background-color: #FFFFFF;
  -webkit-font-smoothing: antialiased;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, "Microsoft YaHei", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #334155;
  display: flex;
  overflow: hidden;
}
.sidebar {
  width: 65mm;
  height: 297mm;
  background-color: #3E4D5E;
  color: #FFFFFF;
  padding: 13mm 6.5mm 13mm 7.5mm;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.name {
  font-size: 28px;
  font-weight: bold;
  letter-spacing: 2px;
  color: #FFFFFF;
  margin-bottom: 5px;
}
.intent {
  font-size: 11.5px;
  color: #E2E8F0;
  margin-bottom: 12px;
  line-height: 1.45;
}
.photo-box {
  width: 100%;
  display: flex;
  justify-content: flex-start;
  margin-bottom: 12px;
}
.photo-img {
  width: 46mm;
  height: 60mm;
  object-fit: cover;
  border-radius: 2px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  background-color: #2D3748;
}
.side-sec-title {
  font-size: 12.2px;
  font-weight: bold;
  color: #FFFFFF;
  margin-top: 13px;
  margin-bottom: 6px;
  letter-spacing: 1px;
  padding-bottom: 2px;
  border-bottom: 1.5px solid rgba(255,255,255,0.35);
}
.side-item {
  font-size: 10px;
  line-height: 1.55;
  color: #F1F5F9;
  margin-bottom: 3.5px;
  word-break: normal;
  overflow-wrap: break-word;
  text-align: left;
}
.side-item b, .side-skill-item b {
  color: #FFFFFF;
  font-weight: 600;
}
.side-skill-item {
  font-size: 9.3px;
  line-height: 1.50;
  color: #F8FAFC;
  margin-bottom: 7.2px;
  word-break: normal;
  overflow-wrap: break-word;
  text-align: left;
}
.main {
  width: 145mm;
  height: 297mm;
  padding: 12mm 9.5mm 12mm 9.5mm;
  display: flex;
  flex-direction: column;
  background: #FFFFFF;
}
.sec-ribbon {
  background-color: #E2E8F0;
  color: #0F172A;
  font-size: 12.8px;
  font-weight: bold;
  padding: 4px 8.5px;
  margin-top: 10.5px;
  margin-bottom: 5.5px;
  border-left: 4px solid #3E4D5E;
  letter-spacing: 0.8px;
  display: flex;
  align-items: center;
}
.first-ribbon {
  margin-top: 0;
}
.bullet-item {
  font-size: 9.9px;
  line-height: 1.50;
  color: #334155;
  margin-bottom: 4.8px;
  text-align: left;
  padding-left: 11px;
  position: relative;
  word-break: normal;
  overflow-wrap: break-word;
}
.bullet-item::before {
  content: "▪";
  position: absolute;
  left: 1px;
  top: -0.5px;
  color: #3E4D5E;
  font-size: 10px;
}
.bullet-item b {
  color: #0F172A;
  font-weight: 600;
}
.proj-title-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 11.8px;
  font-weight: bold;
  color: #0F172A;
  margin-top: 9px;
  margin-bottom: 2.8px;
}
.proj-github {
  font-size: 9.1px;
  color: #2563EB;
  font-family: 'Consolas', monospace;
  font-weight: normal;
  text-decoration: none;
  white-space: nowrap;
  flex-shrink: 0;
}
.proj-duty {
  font-size: 9.3px;
  line-height: 1.42;
  color: #475569;
  margin-bottom: 4.6px;
  padding-left: 2px;
}"""

    v3_config = """{
  "name": "photo_two_column_balanced_v3",
  "description": "A4单页双栏经典照片版-垂直韵律均衡版(v3)，彻底杜绝上半太挤下半太空，底部留白严格控制在18mm~28mm",
  "page": {
    "width_mm": 210.0,
    "height_mm": 297.0,
    "bottom_margin_min_mm": 18.0,
    "bottom_margin_max_mm": 28.0
  },
  "fonts": {
    "body": "Microsoft YaHei",
    "latin": "Arial",
    "mono": "Consolas"
  },
  "colors": {
    "sidebar": "#3E4D5E",
    "sidebar_text": "#F1F5F9",
    "sidebar_muted": "#E2E8F0",
    "main_text": "#334155",
    "main_strong": "#0F172A",
    "ribbon": "#E2E8F0",
    "ribbon_text": "#0F172A",
    "ribbon_border": "#3E4D5E",
    "link": "#2563EB"
  },
  "metrics": {
    "sidebar_width_mm": 65.0,
    "main_width_mm": 145.0,
    "sidebar_padding": "13mm 6.5mm 13mm 7.5mm",
    "main_padding": "12mm 9.5mm 10mm 9.5mm",
    "name_px": 28,
    "intent_px": 11.5,
    "photo_width_mm": 46.0,
    "photo_height_mm": 60.0,
    "side_sec_title_px": 12.2,
    "side_item_px": 10.0,
    "side_item_line": 1.55,
    "side_skill_px": 9.3,
    "side_skill_line": 1.50,
    "side_skill_margin_bottom_px": 7.2,
    "ribbon_px": 12.8,
    "ribbon_padding": "4px 8.5px",
    "ribbon_margin_top_px": 10.5,
    "ribbon_margin_bottom_px": 5.5,
    "bullet_px": 9.9,
    "bullet_line": 1.50,
    "bullet_margin_bottom_px": 4.8,
    "bullet_padding_left_px": 11,
    "proj_title_px": 11.8,
    "proj_title_margin_top_px": 9.0,
    "proj_title_margin_bottom_px": 2.8,
    "proj_duty_px": 9.3,
    "proj_duty_line": 1.42,
    "proj_duty_margin_bottom_px": 4.6
  }
}"""

    conn.execute(
        """
        INSERT INTO resume_layout_templates
            (template_key, template_name, description, page_width_mm, page_height_mm,
             bottom_margin_min_mm, bottom_margin_max_mm, sidebar_width_mm, main_width_mm,
             photo_width_mm, photo_height_mm, css_content, layout_config_json, is_default, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(template_key) DO UPDATE SET
            template_name = excluded.template_name,
            description = excluded.description,
            page_width_mm = excluded.page_width_mm,
            page_height_mm = excluded.page_height_mm,
            bottom_margin_min_mm = excluded.bottom_margin_min_mm,
            bottom_margin_max_mm = excluded.bottom_margin_max_mm,
            sidebar_width_mm = excluded.sidebar_width_mm,
            main_width_mm = excluded.main_width_mm,
            photo_width_mm = excluded.photo_width_mm,
            photo_height_mm = excluded.photo_height_mm,
            css_content = excluded.css_content,
            layout_config_json = excluded.layout_config_json,
            is_default = excluded.is_default,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            "photo_two_column_balanced_v3",
            "经典双栏照片版-垂直韵律均衡版(v3)",
            "A4单页双栏经典照片版-垂直韵律均衡版(v3)，彻底杜绝上半太挤下半太空，底部留白严格控制在18mm~28mm",
            210.0,
            297.0,
            18.0,
            28.0,
            65.0,
            145.0,
            46.0,
            60.0,
            v3_css,
            v3_config,
            1,
        ),
    )

    # -------------------------------------------------------------------------
    # Schema v17: 注册第15条简历规则（根据JD动态裁剪物联网项目展示侧重点）
    # 及入库物联网技能大赛权威项目事实与双分支（Python上位机/Android移动端）证据库
    # -------------------------------------------------------------------------
    conn.execute(
        """
        INSERT INTO resume_generation_rules (
            rule_category, rule_key, rule_title, rule_content, rationale, priority, is_active, updated_at
        ) VALUES (
            'content_matching',
            'jd_tailored_project_emphasis',
            '根据JD岗位职责动态裁剪物联网项目展示侧重点',
            '在生成定制简历时，必须根据目标企业与JD的侧重点选择项目展现形态：(1) 工业上位机/软件/自动化岗位：突出Python (PyQt5) 上位机监控开发、Modbus协议与串口服务器通信；(2) 移动端/客户端/Android岗位：突出Android 原生应用开发 (Java)、多传感器数据采集与云平台API对接；(3) 数据开发/网络协议/爬虫岗位：突出Wireshark深度抓包、TCP/IP握手分析与网络通信排障；(4) 系统交付/运维岗位：突出局域网组网、消息网关部署与故障自动化自愈。严禁一刀切使用单一版本。',
            '竞赛知识库涵盖上位机、移动端、网络组网与云平台完整技术栈，且均为真实实操内容；针对性匹配JD能最大化契合面试官画像，提升简历通过率与专业技术可信度。',
            1,
            1,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT(rule_key) DO UPDATE SET
            rule_title = excluded.rule_title,
            rule_content = excluded.rule_content,
            rationale = excluded.rationale,
            updated_at = CURRENT_TIMESTAMP
        """
    )

    conn.execute(
        """
        INSERT INTO resume_evidence_projects (
            project_key, display_name, repo_url, positioning, started_on, ended_on, scale_summary, source_report, updated_at
        ) VALUES (
            'iot-skills-competition',
            '江苏省物联网技能大赛（网络规划与多设备协同联调）',
            'https://github.com/adlink8/iot-skills-competition',
            '江苏省职业技能大赛省级获奖成果：涵盖 Python (PyQt5) 上位机监控、Android 原生应用研发、局域网组网部署与 Wireshark 网络抓包排障；支持根据目标企业与JD职责动态切换展示侧重点（上位机工控/移动端开发/网络协议调试/系统服务交付）。',
            '2023-09-01',
            '2024-05-30',
            '2,609 个核心代码与解析文档，50 套实战工程源码；涵盖 PyQt5 上位机开发、Android Java 原生应用、Modbus 协议解析、新大陆云平台 API 对接、工业串口服务器 USR-TCP232 现场组网',
            'github.com/adlink8/iot-skills-competition',
            CURRENT_TIMESTAMP
        )
        ON CONFLICT(project_key) DO UPDATE SET
            display_name = excluded.display_name,
            repo_url = excluded.repo_url,
            positioning = excluded.positioning,
            scale_summary = excluded.scale_summary,
            updated_at = CURRENT_TIMESTAMP
        """
    )

    # v18: 旗舰项目标记 —— NovelMind 与 pk-core 为重点项目，每份简历必选
    conn.execute(
        """
        UPDATE resume_evidence_projects
        SET priority = 'flagship', updated_at = CURRENT_TIMESTAMP
        WHERE project_key IN ('novel-mind', 'personal-data-analysis-system')
        """
    )
    conn.execute(
        """
        UPDATE resume_evidence_projects
        SET priority = 'excluded', updated_at = CURRENT_TIMESTAMP
        WHERE project_key IN ('tracememo', 'xiaozhi-embedded-set', 'iot-devops-journey', 'awe')
        """
    )

    iot_proj_row = conn.execute("SELECT id FROM resume_evidence_projects WHERE project_key = 'iot-skills-competition'").fetchone()
    if iot_proj_row:
        iot_proj_id = iot_proj_row[0]
        bullets_data = [
            (iot_proj_id, 1, '工业上位机监控系统研发：使用 Python (PyQt5) 开发工业数据监控上位机；编写协议适配逻辑，实现底层 Modbus 二进制数据流与网络层标准 JSON 协议的双向转换与实时解析。', '机制钩', 'Python (PyQt5) 上位机', '适配工业自动化现场 Modbus 传感器', '高频串口接收卡顿', 'PyQt5 源码工程与 Modbus 驱动', 'supported', 1, '针对工业软件/自动化/上位机岗位'),
            (iot_proj_id, 2, '工业网关部署与链路打通：负责工业串口服务器（USR-TCP232）现场部署与局域网 IP/端口划分（打通端口 1884/502），配置静态路由与通信参数调优，打通底层传感器与上位机双向高可靠通信链路。', '工程纪律钩', 'USR-TCP232 串口服务器部署', '打通传感器端到端采集通道', '端口冲突与静态IP配置', '网络拓扑与现场配置文档', 'supported', 1, '针对工控/嵌入式网络岗位'),
            (iot_proj_id, 3, 'Wireshark 深度抓包与丢包排障：针对通信过程中的偶发网络丢包与报文冲突，运用 Wireshark 抓包定位参数冲突与 Keepalive 超时；设计指数退避重试算法（1s 渐进重试至 60s），通信在线率由 85% 提升至 99.2%。', '数字钩+机制钩', 'Wireshark 网络抓包排障', '消除网络偶发拥塞与瞬断', '掉线重连风暴导致网关过载', 'Wireshark 抓包报文与重试算法源码', 'supported', 1, '针对网络通信/数据开发/协议分析岗位'),
            (iot_proj_id, 4, '多线程通信隔离与异常容错：上位机采用多线程与队列异步解耦数据采集与 UI 渲染，杜绝高频报文导致的界面卡死；配置心跳健康检测与串口自动重连机制，故障自愈恢复时间压缩在 2 秒以内。', '机制钩+数字钩', '多线程异步队列解耦', '保证 UI 渲染与数据流隔离', '界面无响应与线程安全冲突', 'PyQt5 QThread与事件循环源码', 'supported', 1, '针对系统稳定性/高可用架构岗位'),
            (iot_proj_id, 5, 'Android 原生物联网管控客户端开发：基于 Java 原生研发 Android 移动端应用，采用 MVC 分层架构与自定义仪表盘 UI，实现感知节点实时遥测数据显示、设备异常阈值声光报警与远程继电器控制联动。', '名词钩+机制钩', 'Android Java 原生客户端', '提供现场手持移动端交互能力', '主线程阻塞与界面卡顿', 'Android 源码工程与 UI 布局文件', 'supported', 1, '针对 Android 开发/移动客户端/智能终端岗位'),
            (iot_proj_id, 6, '多感知终端数据统一采集与解析：编写多传感器采集模块，完成温湿度、光照、水浸、RFID 射频与 UWB 定位等异构传感器数据帧的高效解析与时序对齐，配置线程池与环形缓冲区防止移动端 ANR。', '机制钩', '异构传感器数据统一解析', '支持 5+ 种感知终端并发接入', '高频广播导致内存抖动与 ANR', '传感器通信驱动与测试用例', 'supported', 1, '针对嵌入式终端应用/传感器集成岗位'),
            (iot_proj_id, 7, '云端与本地网关双通道通信封装：封装 HTTP RESTful 与 Socket 双通信通道，对接新大陆物联网云平台 API 实现传感器实时数据上报；设计本地 SQLite 离线弱网数据缓存与补偿机制，补偿后数据丢失率压降至 0。', '数字钩+反常细节钩', '云平台 API 对接与弱网补偿', '保障移动端在现场弱网下的数据完整性', '现场无线信号差导致数据丢失', '云平台接口通信类与弱网测试记录', 'supported', 1, '针对端云协同/物联网全栈岗位'),
            (iot_proj_id, 8, '现场通信故障联合攻坚与团队斩获省级荣誉：在紧张赛制环境下排查 Android 端、硬件网关与感知终端间的通信冲突，以毫秒级响应调优通信波特率与数据帧间隔，保障端到端全链路高可靠联调，团队荣获省级技能大赛奖项。', '工程纪律钩', '现场多设备联合排障与协同攻坚', '跨设备通信对齐与综合实操', '软硬件接口规范不一致', '技能大赛获奖证书与现场工程配置', 'supported', 1, '针对综合工程素养/团队攻坚')
        ]
        conn.executemany(
            """
            INSERT INTO resume_evidence_bullets (
                project_id, sort_order, bullet_text, hook_type, what_it_is, why_this_choice, pitfall_detail, evidence_chain, evidence_status, is_public_verifiable, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, sort_order) DO UPDATE SET
                bullet_text = excluded.bullet_text,
                hook_type = excluded.hook_type,
                what_it_is = excluded.what_it_is,
                why_this_choice = excluded.why_this_choice,
                pitfall_detail = excluded.pitfall_detail,
                evidence_chain = excluded.evidence_chain,
                evidence_status = excluded.evidence_status,
                is_public_verifiable = excluded.is_public_verifiable,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
            """,
            bullets_data
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
