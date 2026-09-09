---
name: career-apply-orchestrator
displayName: 单岗投递编排器（纯净上下文闭环）
version: 1.0.0
agent_created: true
description: >-
  把「JD 拆解 → 对照优化 → 出简历 → 模拟 ATS → 三方会审 → 放行登记/一键填写」
  收成一场 job_apply_run。主会话只调度 CLI；拆解/优化/会审必须新开子 Agent，
  每人只读一个 pack。ATS 分数只来自 ats_matcher.py。
trigger:
  - 投岗编排 / 走编排器 / 这场岗位从拆解到投递
  - 捕获完 JD 开始闭环 / 纯净上下文投递
  - apply-run / career_apply_run
---

# 单岗投递编排器

主会话是调度员，不是评审员。阶段、分数、产物以 SQLite `job_apply_runs` 为准。

## 启动时读取

- 本文件与 `references/context-packs.md`、`references/spawn-templates.md`
- CLI：`python bin/career_apply_run.py`
- 会审 prompt（只给对应子 Agent，不给主会话改稿）：
  - `skills/career-multi-agent-eval/references/ats-scanner-prompt.md`
  - `skills/career-multi-agent-eval/references/campus-hr-prompt.md`
  - `skills/career-multi-agent-eval/references/tech-lead-prompt.md`
- 缺口分诊：`skills/career-jd-gap-branch/SKILL.md`（优化轮读 bounce_facts，不读会审原文）

## 红线（违反即停）

- 禁止在主会话里拆 JD、改简历、扮 HR / Tech / ATS。
- 禁止把上一轮对话、会审散文、优化理由贴进 spawn prompt。
- 禁止跳过 `ats` 直接会审。
- 禁止在 `review_passed` 前说「去投吧」。
- 禁止用 LLM 重算五维 ATS 或会审加权总分。
- 测试画像（`profile.test.json` / 「测一填」）禁止 `release`。
- 浏览器不自动点提交。`release` 只写库 + `autofill.json`。

## 标准循环

```text
start → 反复 next
  spawn  → 子 Agent 只读 pack → ingest --file
  ats / arbitrate / release → 只跑 CLI
直到 next.done = true
```

```bash
python bin/career_apply_run.py start --job-context <JobContext.json> [--job-id N]
python bin/career_apply_run.py next <run_id>
python bin/career_apply_run.py ingest <run_id> --role <role> --file <json>
python bin/career_apply_run.py ats <run_id> --resume <pdf或md>
python bin/career_apply_run.py arbitrate <run_id>
python bin/career_apply_run.py release <run_id>
python bin/career_apply_run.py status <run_id>
```

`next` 会按阶段写 pack，并告诉你 `action`：

| action | 主会话做什么 |
|---|---|
| `spawn` | 新开子 Agent，prompt = spawn-templates 对应段 + pack 路径 |
| `spawn_review_parallel` | **同时**开 hr / tech / ats-llm 三个子 Agent |
| `ats` | 只跑 CLI `ats`，不解释分数 |
| `spawn` + `gap-triage` | 读 `career-jd-gap-branch`，缺词分流：改简历 / 开分支 / 放弃 |
| `gap_branch` | 在宿主项目开 `feat/jd-*`，可运行实现+测试+提交，再 `ingest --role gap-done` |
| `arbitrate` | 只跑 CLI `arbitrate` |
| `release` | 只跑 CLI `release` |
| `stop` / `done` | 结束并汇报 stage |

ATS 打回**禁止**直接再改简历。先分诊：词已在项目里 → 漏写改简历；能力真缺且过立项门槛 → 开分支补代码；门槛不过 → 放弃该词。开分支的实现必须能跑测试并提交，禁止只改 README。

## 子 Agent 产物契约（ingest 用）

**decompose** → `artifacts/breakdown.json`

```json
{
  "role": "decompose",
  "one_liner": "",
  "hard_gates": [{"item": "", "pass": true}],
  "must_keywords": [],
  "bonus_keywords": [],
  "abandon": false,
  "abandon_reason": ""
}
```

硬门槛核心栈全空时 `abandon: true`，流水线结束。

**map** → clause-map.json

```json
{
  "role": "map",
  "clauses": [
    {"jd": "", "evidence": "", "status": "corroborated|missing|skip"}
  ]
}
```

**optimize** → resume.md + 可选 PDF 路径

```json
{
  "role": "optimize",
  "resume_md": "...",
  "resume_path": ""
}
```

打回后只根据 pack 里的 `bounce_facts` 改项目正文，禁止只堆技能栏。

**hr / tech / ats-llm** 必须含 `score` 与 `verdict`，结构分别遵循三方 prompt 的 JSON 契约。

## 门禁数字（CLI 已写死）

- ATS：`≥ 70` 且非 `FAIL_KNOCKOUT` 才进会审
- 会审加权：matcher ATS ×0.35 + HR ×0.30 + Tech ×0.35（**不用** ats-llm.score）
- 放行：总分 ≥ 85 且 HR/Tech 均 ≥ 80 且无一票否决
- WARN / FAIL → `review_failed`，只回 bounce_facts
- 最多 3 轮优化，然后 `abandoned`

## 与其它 Skill

| Skill | 关系 |
|---|---|
| `career-multi-agent-eval` | 提供三个会审 prompt；编排器负责隔离派发 |
| `career-jd-gap-branch` | bounce 后漏写 vs 真缺 |
| `career-resume-audit` | 可选，夹在 resume_draft 与 ats 之间；不当第四票 |
| `career-app-tracker` | `release` 已写 `applications` / jobs 状态 |
