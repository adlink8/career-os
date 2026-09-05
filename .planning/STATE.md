# State: Career OS

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-09-02)

**Core value:** Turn job-search work into repeatable, evidence-backed workflows that use the user's real profile and local knowledge instead of one-off chat answers.

## Current Focus

**v1 workflow + Phase 5 operational slice implemented.** 16-step job-search flow end-to-end covered; runtime adapters now provide traceable practice and imports.

**Codebase mapped:** 2026-06-28 via GSD `map`. See `.planning/codebase/` (STACK / ARCHITECTURE / CONVENTIONS / CONCERNS).

## Final Deliverables (2026-06-14)

### Phase 1: Audit and Bootstrap ✅
- `.planning/STATUS.md`, `scripts/audit.ps1`, `scripts/smoke-test.ps1`
- README + docs corrected for inflated completion claims

### Phase 2: Data and Skill Contracts ✅ (partial)
- DATA-03 resolved (cv-template placeholders + gitignored real CV)
- SKILL-01/02 verified for all 14 skills
- DATA-01, DATA-02, SKILL-03 deferred (low priority)

### Phase 3: Knowledge Layer ✅
- 11 knowledge domains populated, 46 files total
- High-star GitHub sources (roadmap.sh 357K★, devops-exercises 67.9K★, CS-Notes 170K★, etc.)

### Phase 4: Missing Workflow Completion ✅
- Phantom skills created: `career-general-recruit`, `career-interview-master`
- Auxiliary skills created: `career-industry-research`, `career-learning-path`, `career-onboarding-prep`, `career-probation-survival`
- All 14 skills platform-neutral (zero hard-coded agent platform)

## Final Audit

```
audit.ps1     → VERIFIED=37  PARTIAL=0  MISSING=0
smoke-test    → PASS=158     FAIL=0     WARN=0  (14 skills × structure checks + cross-skill + DATA-03)
```

MISSING=0. Static verification passes for all 14 skills; runtime smoke also passes. Deeper profile matching in `career-self-assessment` and real-agent triggering remain manual quality gates.

## v1 Roadmap Coverage (all phases complete)

| Phase | Status |
|-------|--------|
| Phase 1: Audit and Bootstrap | ✅ COMPLETE |
| Phase 2: Data and Skill Contracts | ✅ partial (DATA-01/02/SKILL-03 deferred) |
| Phase 3: Knowledge Layer | ✅ COMPLETE |
| Phase 4: Missing Workflow Completion | ✅ COMPLETE |

## Current Repository Facts

- **14 skills**: all 16 job-search steps covered and pass static structure verification.
- All skills platform-neutral: zero hard-coded agent platform.
- Knowledge layer: 11 domains, 46 files.
- Data layer: `profile.yml`, canonical-v2 `tracker.tsv`, `current-status.md`, `lessons-learned.md`, `data/cv/cv-real.md` (gitignored), `templates/cv-template.md` (placeholder).
- Runtime layer: SQLite report persistence, unified plugin manager, question/job/code/interview adapters, stratified 30-question/30-minute exam assembly, 15-question quick + 120-question IPIP-NEO full personality modes, and opt-in OpenAI-compatible interview scoring; project-native question banks remain available; runtime, expansion, interview, provider and personality smoke tests pass.
- Scripts: `audit.ps1`, `smoke-test.ps1`, `runtime-smoke.py`.

## 16-Step Job-Search Flow (all covered)

```
1.  career-self-assessment         🟡 自我定位
2.  career-industry-research       🟢 行业调研
3.  career-learning-path           🟢 学习路径
4.  career-general-recruit         🟢 岗位搜索
5.  career-general-recruit         🟢 JD 解读
6.  career-company-check           🟢 公司背调
7.  career-general-recruit         🟢 简历定制
8.  career-app-tracker             🟢 投递管理
9.  career-assessment-prep         🟢 笔试测评
10. career-interview-master        🟢 技术面试
11. career-interview-master        🟢 行为面试
12. career-interview-master        🟢 面试复盘
13. career-interview-master        🟢 谈薪
14. career-interview-master        🟢 Offer 决策
15. career-onboarding-prep         🟢 入职准备
16. career-probation-survival      🟢 试用期生存
```

## Current Focus（2026-07-05 更新）

**Phase 5: Operational Layer** — 作战层和可插拔练习运行时已落地；tracker.tsv 真实投递数仍为 0，不能把候选岗位当成转化结果。

详见 `.planning/ROADMAP.md` Phase 5 和 `.planning/REQUIREMENTS.md` OPS-01~OPS-05。

## Phase 5 行动清单（按优先级）

1. **[最高] 实战验证（C1）** — ✅ 2026-09-05 首轮完成：3 个 skill（daily-driver/interview-master/general-recruit）子 agent 运行时测试 PASS（general-recruit 首测 PARTIAL → 13 处修复 → 独立复测 PASS），报告见 `.planning/testing/runtime-test-report.md`；剩余：用户日常 agent 真实触发确认平台级 trigger 路由。
2. **[高] 真实投递回写** — 首批岗位人工核验后，把真实申请状态回写 tracker 和 timeline。
3. **[中] Judge0 服务验证（已实测为 PARTIAL）** — 本机 Docker Desktop 已部署 Judge0 1.13.0，`/system_info`/`/languages` 可达；实际 isolate 因 Windows cgroup 失败，代码题暂不能视为安全执行，保留 trusted-local 边界并建议迁移 Linux/WSL2 VM。
4. **[中] 语音面试插件** — 以 DeepInterview/AI Mock Interviewer 为外部实现，先完成接口和隐私评估，再接浏览器语音。
5. **[低] C3** — 将 `career-self-assessment` 的 profile 匹配从结构通过提升为有证据的质量验证。

## Open Risks（更新）

| 风险 | 严重度 | 缓解状态 |
|------|--------|---------|
| C1：Agent 运行时从未验证 | 🟠 中 | **首轮已缓解**（2026-09-05 子 agent 运行时测试 3 skill PASS + 13 处修复 + 复测 PASS，见 `.planning/testing/runtime-test-report.md`）；待用户日常 agent 真实触发完全闭环 |
| C2：Git 根在父目录，邮箱在 commit 元数据 | 🟠 中 | 未缓解 |
| C3：career-self-assessment 的 profile 匹配可进一步深化 | 🟡 低 | 未缓解 |
| C4：薪资数据最后核对 2026-06 | 🟡 低 | 有 refresh 标签 |
| C5：多 agent 分发手动操作 | 🟡 低 | 未缓解 |
| C7：tracker.tsv = 0，系统未实战 | 🔴 高 | **新增** |
| C8：每日驱动 skill 未在真实 Agent 触发 | 🟠 中 | 已实现，待 C1 |
| C9：反馈回路未积累真实面试样本 | 🟠 中 | 已建文件，待真实数据 |
| C10：英语面试 skill 未做真实语音验证 | 🟠 中 | 文本链路已实现 |
| C11：跨会话状态文件未自动回写 | 🟠 中 | 文件契约已实现，人工确认写入 |
| C12：多版简历决策机制未做真实 JD 回归 | 🟡 低 | 逻辑已实现，待样本 |
| C13：两个 skill 职责过重 | 🟡 低 | **新增** |
| C14：Windows Docker Desktop 的 Judge0 isolate 无法创建 cgroup | 🟠 中 | **已确认；服务可达但代码执行 PARTIAL，需 Linux/WSL2 VM** |

---
*Last updated: 2026-09-05 — C1 首轮运行时验证通过（3 skill PASS + 13 处修复 + 独立复测 PASS），报告见 `.planning/testing/runtime-test-report.md`*
