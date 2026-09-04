# Requirements: Career OS

**Defined:** 2026-06-10
**Core Value:** Turn job-search work into repeatable, evidence-backed workflows that use the user's real profile and local knowledge instead of one-off chat answers.

## v1 Requirements

### Repository Baseline

- [ ] **BASE-01**: Repository status document reflects actual files, skills, knowledge directories, and gaps.
- [ ] **BASE-02**: README and docs no longer claim skills or knowledge assets are complete unless verified on disk.
- [ ] **BASE-03**: Project has a clear next-step roadmap and state file under `.planning/`.

### Skill System

- [ ] **SKILL-01**: Each existing skill has a valid `SKILL.md` with role, trigger, workflow, inputs, and output format.
- [ ] **SKILL-02**: Each existing skill declares the local files it reads from `config/`, `data/`, `knowledge/`, or `templates/`.
- [ ] **SKILL-03**: A local install or usage path exists for running workspace skills in WorkBuddy/Codex-compatible workflows.
- [ ] **SKILL-04**: Missing v1 skills are created or explicitly deferred with reason.

### Knowledge Layer

- [ ] **KNOW-01**: Each knowledge domain has at least a README that states source, update method, and intended consuming skills.
- [ ] **KNOW-02**: Current target roles have minimum viable knowledge notes for JD keywords, interview topics, and learning gaps.
- [ ] **KNOW-03**: External data that can drift, such as salary and company information, is marked as refresh-required.

### Data Layer

- [ ] **DATA-01**: `config/profile.yml` has a documented schema and required fields.
- [ ] **DATA-02**: `data/tracker.tsv` has a documented column contract and example update workflow.
- [ ] **DATA-03**: Templates distinguish sample placeholders from real personal data.

### Verification

- [ ] **VER-01**: A repeatable audit command or checklist reports VERIFIED / PARTIAL / MISSING for skills, knowledge, and data.
- [ ] **VER-02**: Initialization and future phase completion summaries cite concrete files and checks.

## v2 Requirements

### Automation

- **AUTO-01**: Script can install or sync workspace skills into a target WorkBuddy/Codex skill directory.
- **AUTO-02**: Script can generate a weekly application review from `data/tracker.tsv`.
- **AUTO-03**: Script can produce JD-fit reports from a pasted job description.

### Integrations

- **INT-01**: Optional GitHub issue/project workflow tracks career-system tasks.
- **INT-02**: Optional company-check workflow can call approved external tools when credentials are available.

## Phase 5: Operational Layer（v2 新增，2026-07-05）

> 目标：让系统从"已建好但未用过"进入"真实驱动日常求职"状态。

- **OPS-01**（每日驱动）：新增 `career-daily-driver` skill，读取 `data/tracker.tsv` + `profile.yml` 的 `target_timeline` + 当前日期，输出当日行动清单（投递目标/今日联系/今日练习）。
- **OPS-02**（跨会话状态）：新增 `data/current-status.md`，记录当前活跃求职线程（在投公司、面试进度、等待回复）；所有 skill 的"必须读取"中加入此文件。
- **OPS-03**（反馈回路）：新增 `data/lessons-learned.md`，每次面试复盘后追加教训；`career-interview-master` 在面试准备时读取该文件。
- **OPS-04**（英语面试）：新增 `career-english-interview-prep` skill，覆盖英文项目介绍、外企行为面试答法、英文简历措辞优化，对齐 profile.yml 中外企和日本方向目标。
- **OPS-05**（简历选版）：在 `career-general-recruit` 中补充多版简历决策逻辑，根据 JD 关键词推荐 cv-ops / cv-iot / cv-ai-infra / cv-network / cv-compact 中的对应版本。

## Out of Scope

| Feature | Reason |
|---------|--------|
| Hosted web dashboard | Not needed for the current local-first workflow. |
| Private platform scraping | Account, legal, and stability risk. |
| Automatic public sharing of personal profile | Privacy risk. |
| Real-time salary truth without refresh | Market data changes frequently. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BASE-01 | Phase 1 | ✅ DONE |
| BASE-02 | Phase 1 | ✅ DONE |
| BASE-03 | Phase 1 | ✅ DONE |
| SKILL-01 | Phase 2 | ✅ DONE |
| SKILL-02 | Phase 2 | ✅ DONE |
| SKILL-03 | Phase 2 | Deferred (low priority) |
| SKILL-04 | Phase 4 | ✅ DONE |
| KNOW-01 | Phase 3 | ✅ DONE |
| KNOW-02 | Phase 3 | ✅ DONE |
| KNOW-03 | Phase 3 | ✅ DONE |
| DATA-01 | Phase 2 | Deferred (low priority) |
| DATA-02 | Phase 2 | Deferred (low priority) |
| DATA-03 | Phase 2 | ✅ DONE |
| VER-01 | Phase 1 | ✅ DONE |
| VER-02 | Phase 1 | ✅ DONE |
| OPS-01 | Phase 5 | ✅ DONE |
| OPS-02 | Phase 5 | ✅ DONE |
| OPS-03 | Phase 5 | ✅ DONE |
| OPS-04 | Phase 5 | ✅ DONE |
| OPS-05 | Phase 5 | ✅ DONE |

**Coverage:**
- v1 requirements: 15 total (12 DONE, 3 Deferred)
- v2 requirements: 5 DONE (Phase 5); C1/C3 remain manual quality gates
- Unmapped: 0

---
*Requirements defined: 2026-06-10*
*Last updated: 2026-09-02 — Phase 5 operational skills and plugin runtime implemented*
