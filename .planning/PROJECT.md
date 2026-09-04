# Career OS

## What This Is

Career OS is a personal job-search operating system for a Chinese CS student preparing for internships and first full-time roles. It organizes the job hunt into three layers: Skills for repeatable AI workflows, Knowledge for reusable reference material, and Data for the user's profile, applications, and decisions.

The current repository is a brownfield documentation-and-skill workspace with a lightweight local Python/SQLite runtime. It contains a profile, tracker, CV variants, templates, 14 local skills, 11 populated knowledge domains, and a capability-based plugin layer.

## Core Value

Turn job-search work into repeatable, evidence-backed workflows that use the user's real profile and local knowledge instead of one-off chat answers.

## Requirements

### Validated

- ✓ Three-layer architecture is documented: skills, knowledge, and data.
- ✓ Personal career profile exists at `config/profile.yml`.
- ✓ Application tracker exists at `data/tracker.tsv`.
- ✓ Fourteen local skills exist under `skills/`, covering all 16 job-search steps plus daily-driver and English interview practice.
- ✓ CV template exists at `templates/cv-template.md`.
- ✓ README and docs aligned with filesystem state (Phase 1 完成).
- ✓ All 14 skills have valid SKILL.md with role / trigger / workflow / inputs / outputs.
- ✓ Knowledge layer populated: 11 domains, 46 files (Phase 3 完成).
- ✓ Missing workflow skills created: `career-general-recruit`, `career-interview-master`, `career-industry-research`, `career-learning-path`, `career-onboarding-prep`, `career-probation-survival` (Phase 4 完成).
- ✓ Verification scripts exist: `scripts/audit.ps1` + `scripts/smoke-test.ps1` (VER-01/VER-02 完成).
- ✓ Local runtime exists: SQLite report persistence, question/job import adapters, objective/personality assessment scoring, dynamic interview rubric, and code-runner adapter.
- ✓ External projects are isolated behind `plugins/<id>/plugin.json`; no automatic login or application submission.
- ✓ Real CV data gitignored, templates use placeholders (DATA-03 完成).
- ✓ 16-step flow 100% covered by 14 skills (Phase 5 operational slice, 2026-09-02).

### Active (Phase 5 — 2026-07-05)

- [x] **OPS-01** 新增 `career-daily-driver` skill — 读取 tracker.tsv + profile.yml 输出每日行动清单
- [x] **OPS-02** 新增 `data/current-status.md` — 跨会话求职状态文件；3 个 skill 已读取
- [x] **OPS-03** 新增 `data/lessons-learned.md` + 更新 `career-interview-master` 读取教训
- [x] **OPS-04** 新增 `career-english-interview-prep` skill — 外企/国际化方向英语面试准备
- [x] **OPS-05** 在 `career-general-recruit` 中补充多版简历决策逻辑
- [x] **P0** 统一插件适配层、题库/岗位导入、答题和面试报告持久化
- [x] **P0** Judge0 code_runner 插件 + trusted-local 明确安全边界
- [ ] **C1** 在真实 Agent 中触发并验证至少3个 skill 的运行时行为
- [ ] **C3** 将 `career-self-assessment` 从 PARTIAL 升级为 VERIFIED

### Out of Scope

- Full web app or SaaS product — current repo is a local workflow and knowledge system.
- Automated scraping of private recruiting platforms — high account and compliance risk.
- Storing secrets, account passwords, or private tokens — should remain outside the repo.
- Treating external market data as static truth — salary, company, and job-posting data must be refreshed when used.

## Context

- User target roles: operations/support, IoT platform operations, cloud platform maintenance, AI agent deployment operations, AI product technical support, network operations, and systems integration.
- Target cities include Suzhou, Wuxi, and Shenzhen; dream direction includes foreign-company IT support and Japan-related roles.
- The repository's docs must distinguish static structure verification from live Agent behavior and job-search outcomes.
- Knowledge layer has 11 populated domains and 46 files including domain README files.
- `gsd-sdk query` is available; its progress output does not yet recognize the hand-maintained roadmap phase structure.

## Constraints

- **Local-first**: The system should work from this folder without requiring hosted infrastructure.
- **Chinese job market**: Outputs should default to Chinese context, Chinese recruiting channels, and Chinese entry-level constraints.
- **Evidence-backed status**: Completion labels must be based on checked files, runnable scripts, or documented manual verification.
- **Privacy**: Personal data is allowed locally but should not be copied to public issues, logs, or generated examples without review.
- **Low overhead**: Prefer small Markdown/YAML/TSV assets and simple scripts over building a heavy platform.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Treat this as brownfield | Existing docs, profile, tracker, skills, and templates already exist. | ✓ Good |
| Use `.planning/` for project control | Matches GSD workflow and keeps roadmap/state separate from user-facing docs. | — Pending |
| Make Phase 1 an audit/bootstrap phase | Current docs initially overstated completion relative to actual files. | ✓ Good |
| Keep the repo local-first | The main value is repeatable personal workflows, not a hosted app. | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

After each phase transition:
1. Move validated requirements to `Validated`.
2. Move invalidated requirements to `Out of Scope` with reason.
3. Add new active requirements discovered during execution.
4. Log decisions that constrain future work.
5. Update "What This Is" if the project changes shape.

After each milestone:
1. Review all sections.
2. Check whether the core value is still correct.
3. Audit out-of-scope items.
4. Update context with current state.

---
*Last updated: 2026-09-02 after Phase 5 runtime/plugin integration*
