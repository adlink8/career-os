# Status Audit: Career OS

> Phase 1 baseline audit. Every item below is derived from a checked file, not from a documentation claim.
> Status legend: **VERIFIED** = file present and content matches purpose · **PARTIAL** = present but incomplete · **MISSING** = not on disk.

**Audit date:** 2026-09-03 (refreshed after exam/personality/provider/Docker integration)
**Audit method:** recursive filesystem walk + content read of each asset
**Truth source:** local files under `career-os/`, not README assertions
**Reproduce:** `pwsh scripts/audit.ps1`  ·  `pwsh scripts/smoke-test.ps1`  ·  `python scripts/runtime-smoke.py`  ·  `python scripts/github-expansion-smoke.py`  ·  `python scripts/github-expansion-runtime-smoke.py`  ·  `python scripts/personality-smoke.py`

---

## Summary Counts

| Layer | VERIFIED | PARTIAL | MISSING | Total |
|-------|----------|---------|---------|-------|
| Skills | 14 | 0 | 0 | 14 |
| Knowledge domains | 11 | 0 | 0 | 11 |
| Data files | 6 | 0 | 0 | 6 |
| Templates | 1 | 0 | 0 | 1 |
| Docs | 3 | 0 | 0 | 3 |
| Planning | 6 | 0 | 0 | 6 |
| Scripts | 3 | 0 | 0 | 3 |

**Phase 1 exit gate:** ✅ README and usage docs no longer claim unverified completion.
**Phase 2 partial advance (DATA-03):** ✅ cv-template.md uses placeholders; real data moved to gitignored `data/cv/cv-real.md`.
**Phase 3 knowledge layer:** ✅ All 11 knowledge domains populated with README + content files.
**Phase 4 main link:** ✅ Phantom skills created as `career-general-recruit` and `career-interview-master`.
**Phase 4 auxiliary skills:** ✅ `career-industry-research`, `career-learning-path`, `career-onboarding-prep`, `career-probation-survival` created.
**Phase 5 operational skills:** ✅ `career-daily-driver`, `career-english-interview-prep`; cross-session state, lessons and CV selection logic added.
**Runtime integration:** ✅ SQLite report persistence, JD-aware interview selection/context, realistic 30-question/30-minute stratified exam assembly, 142 GitHub open-ended embedded/RAG interview questions, 175 MIT aptitude questions, 15-question quick + 120-question IPIP-NEO full personality modes, unified plugin manifests, question/job import, dynamic interview rubric, opt-in OpenAI-compatible scoring adapter, personality scoring and code-runner adapter; project-native question banks remain available.
**Provider/Docker evidence (2026-09-03):** ✅ local fake HTTP server exercised 3 real `/chat/completions` calls and no-endpoint fallback; top-level `docker build -t career-os:local .`, `docker compose run --rm career-os python bin/career_jobs_cli.py stats`, and `docker-healthcheck.py` passed. The image mounts `./data` and does not package personal profile/database into the image.
**Deployment evidence (2026-09-02):** Judge0 1.13.0 containers and HTTP API are reachable locally; actual isolate execution is **PARTIAL on Windows Docker Desktop** because `/sys/fs/cgroup/memory` cannot be created. Independent post-deploy E2E also passed interview persistence/adaptive follow-up and plugin failure isolation using a temporary database.
**Multi-agent neutrality:** ✅ All 14 skills are platform-neutral (zero hard-coded agent platform).

**All 16 job-search steps are now covered.**

---

## Skill Layer

### Local skills present on disk

| Skill | SKILL.md | references/ | Status | Covers |
|-------|----------|-------------|--------|--------|
| `career-self-assessment` | ✅ | ✅ `references/direction-matrix.md` | **VERIFIED** | step 1 (self-positioning) |
| `career-daily-driver` | ✅ | ✅ `references/daily-driver-spec.md` | **VERIFIED** | daily action orchestration |
| `career-industry-research` | ✅ | ✅ `references/research-method.md` | **VERIFIED** | step 2 (industry research) |
| `career-learning-path` | ✅ | ✅ `references/learning-strategy.md` | **VERIFIED** | step 3 (learning path) |
| `career-general-recruit` | ✅ | ✅ `references/recruit-workflow.md` | **VERIFIED** | steps 4-7 (search/JD/resume/apply) |
| `career-company-check` | ✅ | ✅ `references/company-check-checklist.md` | **VERIFIED** | step 6 (company background check) |
| `career-app-tracker` | ✅ | ✅ `references/tracker-spec.md` | **VERIFIED** | step 8 (application tracking) |
| `career-assessment-prep` | ✅ | ✅ `references/assessment-systems.md` | **VERIFIED** | step 9 (aptitude test prep) |
| `career-interview-master` | ✅ | ✅ `references/interview-flow.md` | **VERIFIED** | steps 10-14 (interview/review/salary/offer) |
| `career-onboarding-prep` | ✅ | ✅ `references/onboarding-checklist.md` | **VERIFIED** | step 15 (onboarding prep) |
| `career-probation-survival` | ✅ | ✅ `references/survival-playbook.md` | **VERIFIED** | step 16 (probation survival) |
| `career-english-interview-prep` | ✅ | ✅ `references/english-interview-playbook.md` | **VERIFIED** | English interview practice |
| `career-resume-audit` | ✅ | ✅ `references/evidence-status.md` | **VERIFIED** | evidence-bound resume audit |

### Note on `career-self-assessment`

The skill is functionally complete for this static audit: `SKILL.md`, `references/direction-matrix.md`, declared inputs, and output format are all present. Deeper profile matching is a future quality improvement; it is not a missing-file or contract failure.

### Skill contract check (SKILL-01 / SKILL-02)

| Requirement | Result |
|-------------|--------|
| Each skill has a SKILL.md with role/trigger/workflow/output | 14/14 pass (verified by `scripts/smoke-test.ps1`) |
| Each skill declares the local files it reads | 14/14 pass |
| Each skill declares reference files that exist | 14/14 pass |
| Cross-skill schema consistency (TSV ↔ spec) | pass |
| DATA-03 template/real-data separation | pass (`{{name}}` placeholder; real data in gitignored `data/cv/cv-real.md`) |
| Platform neutrality (no agent-platform hard-coding) | 14/14 pass |

---

## Knowledge Layer

Root index `knowledge/README.md` is **VERIFIED** (documents the 11-domain map).

| Domain dir | Domain README | Content files | Status |
|------------|---------------|---------------|--------|
| `self-assessment/` | ✅ | 2 (mbti-holland, skill-stack-grading) | **VERIFIED** |
| `industry-reports/` | ✅ | 2 (iot-outlook, ai-ops-roles) | **VERIFIED** |
| `roadmaps/` | ✅ | 4 (devops, iot-ops, ai-ops, network-ops) | **VERIFIED** |
| `jd-templates/` | ✅ | 3 (analysis-template, ops-keywords, iot-keywords) | **VERIFIED** |
| `company-check/` | ✅ | 2 (red-flags, background-check-method) | **VERIFIED** |
| `resume-templates/` | ✅ | 2 (star-method, ats-optimization) | **VERIFIED** |
| `assessment-banks/` | ✅ | 4 (four-systems, aptitude, personality, mock-questions) | **VERIFIED** |
| `interview-banks/` | ✅ | 4 (ops, iot, behavioral, reverse-questions) | **VERIFIED** |
| `salary-data/` | ✅ | 3 (salary-bands, negotiation, offer-evaluation) | **VERIFIED** |
| `onboarding/` | ✅ | 3 (first-week, first-90-days, ops-onboarding) | **VERIFIED** |
| `survival/` | ✅ | 3 (survival-rules, common-pitfalls, confirmation) | **VERIFIED** |
| `knowledge/README.md` (root) | — | 1 | **VERIFIED** |

**Implication:** Three-layer architecture is now realized end-to-end. Skills can read real knowledge content from `knowledge/<domain>/`, not empty directories.

---

## Data Layer

| File | Status | Notes |
|------|--------|-------|
| `config/profile.yml` | **VERIFIED** | Real profile data (求职画像, 运维/IoT target, 4-7k expectation) |
| `data/tracker.tsv` | **VERIFIED** | canonical-v2 9-column header; statistics currently show 0 real applications and candidate rows |
| `data/cv/cv-real.md` | **VERIFIED** | Real CV migrated from old template; gitignored |
| `templates/cv-template.md` | **VERIFIED** | Now pure placeholder template; DATA-03 resolved |

### Data contract status

- `profile.yml` schema documentation → Phase 2 DATA-01 (still pending a schema doc)
- `tracker.tsv` column contract → documented in `skills/career-app-tracker/references/tracker-spec.md` (DATA-02 partially satisfied)
- `cv-template.md` placeholder separation → **DATA-03 RESOLVED** via `{{}}` placeholders + `data/cv/cv-real.md` + `.gitignore`

---

## Docs Layer

| File | Status | Notes |
|------|--------|-------|
| `docs/architecture.md` | **VERIFIED** | Three-layer model matches actual structure |
| `docs/how-to-use.md` | **VERIFIED** | Updated 2026-09-02: lists 14 skills and runtime/plugin commands |
| `README.md` | **VERIFIED** | Updated 2026-09-02: reflects 14 skills, runtime adapters, 11 knowledge domains, and the remaining live-agent/real-application boundary |

---

## Planning Layer

| File | Status |
|------|--------|
| `.planning/config.json` | **VERIFIED** |
| `.planning/PROJECT.md` | **VERIFIED** |
| `.planning/REQUIREMENTS.md` | **VERIFIED** |
| `.planning/ROADMAP.md` | **VERIFIED** |
| `.planning/STATE.md` | **VERIFIED** |
| `.planning/STATUS.md` | **VERIFIED** (this file) |

---

## v1 Roadmap Requirement Mapping

### Phase 1 (Audit and Bootstrap)

| Req | Description | Status |
|-----|-------------|--------|
| BASE-01 | Status doc reflects actual files/skills/knowledge/gaps | ✅ This file |
| BASE-02 | README/docs no longer claim unverified completion | ✅ Corrected |
| BASE-03 | Clear next-step roadmap + state file | ✅ ROADMAP.md + STATE.md |
| VER-01 | Repeatable audit command reports VERIFIED/PARTIAL/MISSING | ✅ `scripts/audit.ps1` |
| VER-02 | Phase completion cites concrete files/checks | ✅ `scripts/smoke-test.ps1` |

### Phase 2 (Data and Skill Contracts)

| Req | Description | Status |
|-----|-------------|--------|
| DATA-01 | profile.yml has documented schema | ⏳ Pending |
| DATA-02 | tracker.tsv has documented column contract | ✅ Partial (in skill ref) |
| DATA-03 | Templates distinguish placeholders from real data | ✅ Resolved |
| SKILL-01 | Valid SKILL.md with role/trigger/workflow/inputs/output | ✅ 14/14 |
| SKILL-02 | Skills declare local input files | ✅ 14/14 |
| SKILL-03 | Local install/usage path documented | ⏳ Pending |

### Phase 3 (Knowledge Layer)

| Req | Description | Status |
|-----|-------------|--------|
| KNOW-01 | Each knowledge domain has README | ✅ All 11 |
| KNOW-02 | Target roles have starter notes | ✅ All directions covered |
| KNOW-03 | Drift-prone data marked refresh-required | ✅ salary-data + industry-reports |

### Phase 4 (Missing Workflow Completion)

| Req | Description | Status |
|-----|-------------|--------|
| SKILL-04 | Missing v1 skills created or deferred | ✅ All 16 steps now have skills |

---

## Open Risks Carried Forward

1. **Git root drift:** `career-os/` is an untracked subtree; the git root is the parent dir. The new `.gitignore` is in place but not yet committed.
2. **Agent runtime untested:** Smoke-test verifies structure contracts only, not LLM behavior. Live runtime test on any agent (WorkBuddy/Claude/Cursor/etc.) still pending.
3. **Salary data freshness:** `salary-data/ops-salary-bands.md` carries refresh-required tags but actual numbers were last verified 2026-06; must re-WebSearch before any negotiation use.
4. **Multi-agent distribution not engineered:** Skills are platform-neutral by content, but no sync script or per-platform frontmatter adaptation exists yet. Users must manually copy skills to their agent's skill directory.
5. **`career-self-assessment` quality depth:** Static contract passes; profile matching can still be improved through real-use feedback.

---

*Refreshed 2026-09-02 from filesystem audit + smoke-test + runtime-smoke. Re-run the three scripts to refresh.*
