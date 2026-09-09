PRAGMA foreign_keys=OFF;

CREATE TABLE application_timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    company_name TEXT,
    job_title TEXT,
    event_date DATE,
    event_type TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, application_id INTEGER,
    FOREIGN KEY(job_id) REFERENCES jobs(id)
);

CREATE TABLE applications (
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
        );

CREATE TABLE career_os_schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );

CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    alias TEXT,
    industry TEXT,
    company_type TEXT,
    city TEXT,
    website TEXT,
    campus_url TEXT,
    welfare_summary TEXT,
    english_req TEXT,
    rating TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
, max_campus_applications INTEGER, campus_application_rules TEXT);

CREATE TABLE company_interview_guides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER UNIQUE,
    company_name TEXT NOT NULL,
    recruitment_process TEXT NOT NULL,
    resume_criteria TEXT NOT NULL,
    interview_rounds TEXT NOT NULL,
    typical_questions TEXT NOT NULL,
    score_weights TEXT NOT NULL,
    avoid_pitfalls TEXT NOT NULL,
    authentic_sources TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE github_commits (
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
        );

CREATE TABLE github_profile (
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
        );

CREATE TABLE github_project_candidates (
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
        );

CREATE TABLE github_repositories (
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
        );

CREATE TABLE interview_drill_points (
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
        );

CREATE TABLE interview_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            turn_no TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            score_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES mock_interview_reports(id)
        );

CREATE TABLE jd_evidence_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER NOT NULL,
            project_key TEXT NOT NULL,
            bullet_sort INTEGER NOT NULL,
            layer TEXT NOT NULL,
            match_role TEXT NOT NULL DEFAULT 'support',
            rationale TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (package_id) REFERENCES jd_evidence_packages(id),
            UNIQUE (package_id, project_key, bullet_sort, layer)
        );

CREATE TABLE jd_evidence_packages (
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
        );

CREATE TABLE job_apply_run_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            actor TEXT NOT NULL,
            artifact_path TEXT NOT NULL DEFAULT '',
            input_sha256 TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES job_apply_runs(id)
        );

CREATE TABLE job_apply_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            context_id INTEGER,
            job_ad_id TEXT NOT NULL DEFAULT '',
            stage TEXT NOT NULL DEFAULT 'captured',
            iteration INTEGER NOT NULL DEFAULT 1,
            resume_path TEXT NOT NULL DEFAULT '',
            resume_version_id INTEGER,
            ats_score REAL,
            ats_verdict TEXT NOT NULL DEFAULT '',
            ats_json_path TEXT NOT NULL DEFAULT '',
            review_score REAL,
            review_verdict TEXT NOT NULL DEFAULT '',
            hr_json_path TEXT NOT NULL DEFAULT '',
            tech_json_path TEXT NOT NULL DEFAULT '',
            ats_llm_json_path TEXT NOT NULL DEFAULT '',
            bounce_json_path TEXT NOT NULL DEFAULT '',
            autofill_json_path TEXT NOT NULL DEFAULT '',
            context_json_path TEXT NOT NULL DEFAULT '',
            application_id INTEGER,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, apply_mode TEXT NOT NULL DEFAULT 'precision',
            FOREIGN KEY (context_id) REFERENCES job_page_contexts(id)
        );

CREATE TABLE job_page_contexts (
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
        , job_ad_id TEXT);

CREATE TABLE job_target_recruitment_checks (
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
        );

CREATE TABLE job_targets (
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
        );

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    company_name TEXT,
    job_title TEXT NOT NULL,
    category TEXT,
    city TEXT,
    salary_text TEXT,
    education_req TEXT,
    english_req TEXT,
    match_level TEXT,
    responsibilities TEXT,
    requirements TEXT,
    matching_analysis TEXT,
    application_url TEXT,
    status TEXT DEFAULT '待投递',
    priority INTEGER DEFAULT 3,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP, source_plugin TEXT, source_job_id TEXT, recommendation_weight REAL, recommendation_rank INTEGER, recommendation_reason TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE mock_exam_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_record_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_answer TEXT,
            correct INTEGER NOT NULL DEFAULT 0,
            response_ms INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exam_record_id) REFERENCES mock_exam_records(id),
            FOREIGN KEY (question_id) REFERENCES mock_questions(id)
        );

CREATE TABLE mock_exam_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_type TEXT NOT NULL,        -- '2027综合机考', '专项手撕代码', '企业定制笔试'
    score INTEGER NOT NULL,
    total_score INTEGER NOT NULL,
    pass_rate REAL,
    details_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
, job_id INTEGER, provider TEXT, rubric_version TEXT, started_at TEXT, completed_at TEXT);

CREATE TABLE mock_interview_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    interview_type TEXT NOT NULL,   -- '技术一面', '架构深挖', '压力面', 'HR面'
    score_tech INTEGER,
    score_expression INTEGER,
    score_depth INTEGER,
    final_grade TEXT,               -- 'S (极力推荐)', 'A (通过)', 'B (待定)', 'C (淘汰)'
    summary_evaluation TEXT,
    qa_transcript_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
, job_id INTEGER, provider TEXT, rubric_version TEXT, started_at TEXT, completed_at TEXT);

CREATE TABLE mock_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,         -- '计算机网络', 'Linux/运维', '数据库/SQL', '手撕代码/算法', '物联网/嵌入式'
    difficulty TEXT NOT NULL,       -- '基础', '进阶', '大厂真题'
    company_tags TEXT,              -- '新大陆, 焦点科技, 招银, 九号'
    question_type TEXT NOT NULL,    -- 'choice' (选择题) / 'code' (编程题)
    title TEXT NOT NULL,
    options_json TEXT,              -- 选择题选项 ["A. xxx", "B. xxx", "C. xxx", "D. xxx"]
    correct_answer TEXT,            -- 正确答案 'B'
    test_cases_json TEXT,           -- 编程题测试用例 [{"input": "...", "expected": "..."}]
    starter_code TEXT,              -- 编程题初始模板代码
    explanation TEXT,               -- 解析与面试考察点
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
, source_plugin TEXT, source_question_id TEXT, assessment_kind TEXT NOT NULL DEFAULT 'general', dimension TEXT, reverse_scored INTEGER NOT NULL DEFAULT 0, scale_min INTEGER NOT NULL DEFAULT 1, scale_max INTEGER NOT NULL DEFAULT 5);

CREATE TABLE platform_recruitment_leads (
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
        , jd_summary TEXT NOT NULL DEFAULT '', responsibilities TEXT NOT NULL DEFAULT '', requirements TEXT NOT NULL DEFAULT '', education_requirement TEXT NOT NULL DEFAULT '', major_requirement TEXT NOT NULL DEFAULT '', skill_requirement TEXT NOT NULL DEFAULT '', experience_requirement TEXT NOT NULL DEFAULT '', jd_source_url TEXT NOT NULL DEFAULT '', jd_evidence_confidence TEXT NOT NULL DEFAULT '中', salary_text TEXT NOT NULL DEFAULT '', screenshot_path TEXT NOT NULL DEFAULT '', capture_method TEXT NOT NULL DEFAULT 'manual', captured_at TEXT NOT NULL DEFAULT '');

CREATE TABLE resume_artifact_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artifact_id INTEGER NOT NULL,
            relative_path TEXT NOT NULL UNIQUE,
            original_filename TEXT NOT NULL,
            is_current INTEGER NOT NULL DEFAULT 1,
            first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            missing_at TEXT,
            FOREIGN KEY (artifact_id) REFERENCES resume_artifacts(id),
            UNIQUE (relative_path, artifact_id)
        );

CREATE TABLE resume_artifacts (
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
        );

CREATE TABLE resume_evidence_bullets (
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
        );

CREATE TABLE resume_evidence_interview_qa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            question TEXT NOT NULL,
            answer_points TEXT NOT NULL,
            related_bullet_sort INTEGER,
            FOREIGN KEY (project_id) REFERENCES resume_evidence_projects(id),
            UNIQUE (project_id, sort_order)
        );

CREATE TABLE resume_evidence_milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            milestone_date TEXT NOT NULL,
            description TEXT NOT NULL,
            session_evidence TEXT NOT NULL DEFAULT '',
            commit_evidence TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (project_id) REFERENCES resume_evidence_projects(id)
        );

CREATE TABLE resume_evidence_numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            number_display TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            verification_method TEXT NOT NULL DEFAULT '',
            is_public INTEGER NOT NULL DEFAULT 0,
            usable_on_resume INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (project_id) REFERENCES resume_evidence_projects(id),
            UNIQUE (project_id, number_display)
        );

CREATE TABLE resume_evidence_projects (
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
        , priority TEXT NOT NULL DEFAULT 'normal');

CREATE TABLE resume_generation_rules (
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
        );

CREATE TABLE resume_layout_templates (
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
        );

CREATE TABLE resume_project_proposals (
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
        );

CREATE TABLE resume_versions (
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
        );

CREATE INDEX idx_application_timeline_application ON application_timeline(application_id, event_date);

CREATE INDEX idx_applications_job ON applications(job_id, status);

CREATE UNIQUE INDEX idx_applications_job_artifact ON applications(job_id, submitted_artifact_id);

CREATE INDEX idx_applications_resume ON applications(resume_version_id, submitted_artifact_id);

CREATE INDEX idx_github_commits_author ON github_commits(author_login, committed_at);

CREATE INDEX idx_github_commits_repo_date ON github_commits(repo_full_name, committed_at);

CREATE INDEX idx_github_project_candidates_job ON github_project_candidates(job_id, status, relevance_score DESC);

CREATE INDEX idx_github_repositories_language ON github_repositories(primary_language, is_fork);

CREATE INDEX idx_github_repositories_pushed ON github_repositories(repo_pushed_at DESC);

CREATE INDEX idx_interview_drill_project ON interview_drill_points(project_key, feature, depth);

CREATE INDEX idx_interview_turns_report ON interview_turns(report_id);

CREATE INDEX idx_jd_evidence_matches_package ON jd_evidence_matches(package_id, match_role);

CREATE INDEX idx_jd_evidence_packages_company ON jd_evidence_packages(company_name);

CREATE INDEX idx_job_apply_run_events_run ON job_apply_run_events(run_id, id);

CREATE INDEX idx_job_apply_runs_job_ad ON job_apply_runs(job_ad_id, id);

CREATE INDEX idx_job_apply_runs_stage ON job_apply_runs(stage, updated_at);

CREATE INDEX idx_job_page_contexts_job_ad ON job_page_contexts(job_ad_id);

CREATE INDEX idx_job_page_contexts_url ON job_page_contexts(url, captured_at);

CREATE INDEX idx_job_target_checks_autumn ON job_target_recruitment_checks(autumn_status);

CREATE INDEX idx_job_target_checks_internship ON job_target_recruitment_checks(internship_status);

CREATE INDEX idx_job_targets_city ON job_targets(city);

CREATE INDEX idx_job_targets_company ON job_targets(company_name);

CREATE INDEX idx_job_targets_source ON job_targets(source_file, source_company_id);

CREATE INDEX idx_job_targets_verification ON job_targets(verification_status, application_status);

CREATE INDEX idx_jobs_company_rank ON jobs(company_id, recommendation_rank);

CREATE INDEX idx_mock_exam_answers_record ON mock_exam_answers(exam_record_id);

CREATE INDEX idx_mock_questions_assessment ON mock_questions(question_type, assessment_kind);

CREATE INDEX idx_platform_leads_city ON platform_recruitment_leads(city);

CREATE INDEX idx_platform_leads_company_name ON platform_recruitment_leads(company_name);

CREATE INDEX idx_platform_leads_dedupe_key ON platform_recruitment_leads(dedupe_key);

CREATE INDEX idx_platform_leads_platform ON platform_recruitment_leads(platform);

CREATE INDEX idx_platform_leads_recruitment_type ON platform_recruitment_leads(recruitment_type);

CREATE INDEX idx_platform_leads_referral_code ON platform_recruitment_leads(referral_code);

CREATE INDEX idx_platform_leads_status ON platform_recruitment_leads(status);

CREATE INDEX idx_resume_artifact_locations_artifact ON resume_artifact_locations(artifact_id, is_current);

CREATE INDEX idx_resume_artifacts_version ON resume_artifacts(resume_version_id, file_state);

CREATE INDEX idx_resume_evidence_bullets_project ON resume_evidence_bullets(project_id, sort_order);

CREATE INDEX idx_resume_evidence_bullets_status ON resume_evidence_bullets(evidence_status);

CREATE INDEX idx_resume_evidence_numbers_project ON resume_evidence_numbers(project_id, usable_on_resume);

CREATE INDEX idx_resume_evidence_qa_project ON resume_evidence_interview_qa(project_id, sort_order);

CREATE INDEX idx_resume_project_proposals_status ON resume_project_proposals(status, resume_key);

CREATE INDEX idx_resume_rules_category ON resume_generation_rules(rule_category, is_active);

CREATE INDEX idx_resume_versions_role ON resume_versions(role_slug, state);
