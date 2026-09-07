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
SCHEMA_VERSION = 15

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
