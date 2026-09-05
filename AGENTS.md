# Codex GSD Routing

This Codex environment is configured to work with the installed Get Shit Done (GSD) framework.

## Default Behavior

- Prefer GSD workflows for complex, multi-step work.
- Do not use GSD for trivial questions, short explanations, or very small one-step edits.
- Keep responses concise and execution-focused.
- Prefer doing the work over extended planning unless the task is ambiguous or high risk.

## When To Use GSD

Use GSD when the task involves one or more of the following:

- multi-step implementation
- debugging with investigation and verification
- milestone or phase planning
- code review, audit, or validation work
- roadmap or backlog shaping
- tasks that benefit from planner/executor/verifier separation

## GSD Priority

When GSD is appropriate, prefer its workflow-oriented skills and agents over ad hoc execution.

- Use GSD planning workflows before large implementations.
- Use GSD execution workflows for planned work.
- Use GSD verification and review workflows before declaring completion on substantial tasks.

## Lightweight Tasks

Do not route through GSD when the user is:

- asking a simple factual question
- asking for a brief explanation
- requesting a tiny isolated change
- asking for a quick command or lookup

In these cases, respond directly and keep overhead low.

## Project Context

- Project: Career OS
- Planning files: `.planning/`
- Current phase: Phase 5, Operational Layer（作战层与统一插件运行时已实现；当前重点是真实 Agent/真实投递验证）
- Truth source: checked local files and smoke verification, not README completion claims.
- Data authority (2026-09-05): `data/career_jobs.sqlite` 是求职全流程唯一权威事实源；md/TSV 文档只是库的规范描述或派生视图，冲突以库为准。新功能先定库表契约（`bin/career_os_store.py` 迁移），再写 Skill 与文档。详见 `docs/data-model.md`。
- v1 status: 14 skills passed static verification, 11 knowledge domains populated, runtime-smoke passed, tracker.tsv 尚无真实投递记录
- Last audited: 2026-09-02

## Personal data warehouse (LLM-mediated)

- **Warehouse root:** see `config/personal-data-warehouse.yml` (configured locally, e.g. `<warehouse_root>`).
- **Model:** warehouse → MCP/REST (read-only) → **this LLM** → write Career OS `config/profile.yml` / related data files.
- **Not:** batch sync scripts that auto-patch profile from stats.
- **Skill:** `skills/career-personal-data-update/` when user asks to refresh profile from personal history.
- **Identity fields** (name/education/birth_year): do not overwrite from warehouse without explicit user confirm.
- **Docs:** `docs/personal-data-warehouse.md`

## Working Style

- Prefer the smallest correct change.
- Verify meaningful work before finishing.
- Do not invent extra phases, documents, or process when the task does not need them.
- If a GSD workflow would add more overhead than value, skip it.

## Output Style

- Default to Chinese.
- Conclusion first.
- Then list key paths, commands, or changes.
- End with at most 3 next-step suggestions.
