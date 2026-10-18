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
- TSV retirement (2026-09-17): `data/tracker.tsv` 已删除。投递数据（岗位/状态/时间线）一律以库 `jobs` / `applications` / `application_timeline` 为准，唯一读写入口 `bin/career_jobs_cli.py`，**不再保留任何 TSV 或 markdown 形式的平行投递账本**。skill 层引用已全部改指库。
- Resume writing authority (2026-09-12): `resume_generation_rules` + `docs/resume-authority.md`；现用母版仅 `data/cv/cv-ops.md` / `cv-iot.md` / `cv-semi.md`。
- v1 status: 14 skills passed static verification, 11 knowledge domains populated, runtime-smoke passed, 真实投递 43 条申请 / 11 月投递高峰批次进行中（库 `applications` 表，2026-10-16 网申批次 +15、2026-10-18 半导体批次 +4）
- Last audited: 2026-09-02

## Personal data warehouse (LLM-mediated)

- **Warehouse root:** see `config/personal-data-warehouse.yml` (configured locally, e.g. `<warehouse_root>`).
- **Model:** warehouse → MCP/REST (read-only) → **this LLM** → write Career OS `config/profile.yml` / related data files.
- **Not:** batch sync scripts that auto-patch profile from stats.
- **Skill:** `skills/career-personal-data-update/` when user asks to refresh profile from personal history.
- **Identity fields** (name/education/birth_year): do not overwrite from warehouse without explicit user confirm.
- **Docs:** `docs/personal-data-warehouse.md`

## CET-4 试卷解析与英语教学规范 (Pedagogical & Exam Rules)

- **零教条与顺流镜头推进法 (Forward-Flow Visual Reading)**：
  - 严禁教条主义语法黑话（禁止使用“先行词、后置定语回拉、从句倒装、比较级倒装”等逼迫眼球和大脑往回跳读的说教）。
  - 严格遵循“主焦点先行，镜头顺流叠加”：眼睛只从左向右走，将每个切分片段视为连续推进的电影镜头画面，绝不倒着翻译。
- **`\` 意群呼吸切分 (Sense-Group Chunking)**：
  - 遇到标点、逻辑连词（and/but/while/because）、引导词（that/who/which）、长介词短语时以 `\` 切分，保持每块 5~8 词的呼吸感。
- **1:1 零脑补单词卡点 (Exact Literal Word-Anchor Mapping)**：
  - 严禁为了中文优美而随意增补原文不存在的文学词汇或成语，杜绝“过度意译”带来的词义对位认知负荷。
  - 每个英文片段必须与中文释义精准严格对齐，哪个英文词对应哪个中文含义必须字字清晰。
- **考点雷达闭环 (Exam Trap & Paraphrase Radar)**：
  - 精准映射题干定位句，直击选项同义替换（paraphrase），拆解四大常见干扰项陷阱（无中生有、偷换概念、因果倒置、范围扩大）。
- **试卷与音频分工契约 (Paper & Audio Division of Labor)**：
  - **试卷 Markdown（`<details>` 折叠区）**：作为唯一事实源，固化沉淀完整的逐句 `\` 断句、顺流镜头解析、重点词汇音标释义与考点雷达。
  - **音频层**：坚决不制作冗长低效的中文机械念经 TTS；仅制作**纯正美音英文原声朗读 MP3**（用于精读后跟读与听力磨耳朵）及 Part II 听力全套双语交互播放器（`player.html`）。
- **教学互动 SOP**：
  - 先由 AI 带领进行顺流镜头拆解与词义扫盲，再由用户自主完成复读、看解析与听原音跟读。
- **单线贯通与随文技巧点拨 (Single-Stream Integration)**：
  - 严禁割裂为“先快速扫题、再回文精读”的两条线虚耗；严格以“顺流精读”为唯一主线，在阅读推进中随文自然点拨做题技巧。
- **拒绝开天眼，讲透“关键句的盲读识别路标” (Spotting Key Sentences without Hindsight)**：
  - 严禁带着答案事后诸葛亮式地说“看，这个就是关键句”；
  - 必须讲透在没有答案视角时，出题人必然盯上的**四大原生路标**，教学生盲读时触发本能警报：
    1. **转折标志**：`but`, `however`, `rather`, `yet` 之后的反转信息（占考点 50% 以上）；
    2. **研究动词标志**：`studies found`, `researchers report`, `revealed`, `concluded` 后的实证发现；
    3. **因果与结论标志**：`because`, `so`, `therefore`, `the conclusion is that` 后的核心定论；
    4. **比较与极端标志**：`far less than`, `more than`, `first-step`, `only` 后的限定条件。
- **同义替换积累账本 (Daily Paraphrase Ledger)**：
  - 绝不把同义替换当作空洞技巧，每篇必须清晰列出 **【原文词句 ➔ 选项换皮词】** 的 1:1 映射卡片，作为日常不可替代的词汇硬积累。

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
