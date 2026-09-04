# Roadmap: Career OS

**Created:** 2026-06-10
**Granularity:** Standard

## Phase Summary

| # | Phase | Goal | Requirements |
|---|-------|------|--------------|
| 1 | Audit and Bootstrap | Establish truthful project status and a repeatable verification baseline. | BASE-01, BASE-02, BASE-03, VER-01, VER-02 |
| 2 | Data and Skill Contracts | Make profile, tracker, templates, and existing skills internally consistent. | DATA-01, DATA-02, DATA-03, SKILL-01, SKILL-02, SKILL-03 |
| 3 | Minimum Knowledge Layer | Populate and document the knowledge layer for the user's current job targets. | KNOW-01, KNOW-02, KNOW-03 |
| 4 | Missing Workflow Completion | Create or deliberately defer the missing career-flow skills. | SKILL-04 |

## Phase 1: Audit and Bootstrap

**Goal:** Establish truthful project status and a repeatable verification baseline.

**Requirements:** BASE-01, BASE-02, BASE-03, VER-01, VER-02

**Success Criteria:**
1. A status file lists all skills, knowledge domains, data files, and templates as VERIFIED / PARTIAL / MISSING.
2. README and docs completion claims match the checked filesystem state.
3. A repeatable audit checklist or command exists and can be run before future status claims.
4. `.planning/STATE.md` points to the current focus and next action.

## Phase 2: Data and Skill Contracts

**Goal:** Make profile, tracker, templates, and existing skills internally consistent.

**Requirements:** DATA-01, DATA-02, DATA-03, SKILL-01, SKILL-02, SKILL-03

**Success Criteria:**
1. `config/profile.yml` and `data/tracker.tsv` have documented schemas.
2. Existing skills name their required inputs and expected outputs.
3. A user can follow one documented path to use or install a workspace skill.
4. Template files are safe to reuse without confusing sample placeholders with real user data.

## Phase 3: Minimum Knowledge Layer

**Goal:** Populate and document the knowledge layer for the user's current job targets.

**Requirements:** KNOW-01, KNOW-02, KNOW-03

**Success Criteria:**
1. Every knowledge domain has a README with source, update method, and consuming skills.
2. Current target roles have starter notes for JD keywords, interview topics, learning path, and company checks.
3. Drift-prone data is labeled refresh-required and not treated as permanent truth.

## Phase 4: Missing Workflow Completion

**Goal:** Create or deliberately defer the missing career-flow skills.

**Requirements:** SKILL-04

**Success Criteria:**
1. Industry research, learning path, onboarding prep, and probation survival have either working skill folders or documented deferral notes.
2. README's 16-step matrix reflects the final v1 status.
3. The project has a clean next milestone proposal after v1.

## Phase 5: Operational Layer（v2，2026-09-02 更新）

**Goal:** 让系统从"基础设施完备但从未实战"进入"可追溯地驱动日常求职，并可插拔接入开源工具"状态。

**Requirements:** OPS-01, OPS-02, OPS-03, OPS-04, OPS-05

**Background:** 审计发现 tracker.tsv 真实投递总数仍为 0；本次补上作战层、练习运行时和开源插件契约，但不把模拟记录冒充真实转化。

**Success Criteria:**
1. `career-daily-driver` skill 可触发，读取 tracker.tsv + profile.yml，输出当日行动清单。
2. `data/current-status.md` 存在，记录当前活跃求职线程；至少 3 个 skill 已将其加入"必须读取"。
3. `data/lessons-learned.md` 存在，`career-interview-master` 在准备阶段读取它。
4. `career-english-interview-prep` skill 存在，覆盖英文项目介绍 + 外企行为面试 + 英文简历优化。
5. `career-general-recruit` 包含多版简历决策逻辑，能根据 JD 推荐对应 CV 变体。
6. `AGENTS.md` 和 `PROJECT.md` 的阶段信息与实际状态一致（不再写 Phase 1）。
7. `plugins/<id>/plugin.json` 可发现并按 capability 启用/禁用；岗位/题库导入需人工确认。
8. 笔试和模拟面试结果可追溯到 SQLite 报告表，代码题默认不在主进程执行。

## Coverage

- v1 requirements: 15 total (12 DONE, 3 Deferred)
- v2 requirements: 5 (OPS-01 ~ OPS-05, Phase 5)
- Unmapped requirements: 0

---
*Last updated: 2026-09-02 — 完成 Phase 5 作战层与统一插件适配运行时*
