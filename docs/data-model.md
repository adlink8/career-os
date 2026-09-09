# 数据库与文档关系图（data-model）

> 结论先行：Career OS 的核心是 `data/career_jobs.sqlite`（schema v22）。
> md 文档分三类：**描述数据库的**（docs/）、**被数据库引用或导出的**（data/*.md）、**与数据库无关的参考层**（knowledge/）。本文是它们与数据库关系的单一事实源。

## 0. 权威原则（2026-09-05 确定）

- `data/career_jobs.sqlite` 是求职全流程的**唯一权威事实源**：企业、岗位、目标、投递、简历版本、题库、测评与模拟面试的状态，一律以库为准。
- md/TSV 文件只承担三种角色：**规范**（描述库怎么用，如 docs/）、**派生视图**（由库导出的报告与清单，可随时重建，不作为事实来源）、**参考层**（knowledge/ 等静态方法论）。
- 文档与库冲突时：以库为准，修文档、不改数据。
- 新功能先设计库表契约（进 `bin/career_os_store.py` 迁移），再写 Skill 和文档；报告类产物一律做成导出物。

## 1. 数据库总览

- **文件**：`data/career_jobs.sqlite`
- **唯一迁移/访问入口**：`bin/career_os_store.py`（`DB_PATH` 常量，可用 `CAREER_OS_DB_PATH` 环境变量覆盖）
- **迁移规则**：只新增表/列，不删除或改写既有求职数据；当前 `career_os_schema_migrations` 已到 v22
- **简历二进制不进库**：PDF/DOCX/MD 原文件留在 `data/cv/`，库里只存元数据（SHA-256 为内容身份），见 `docs/resume-registry.md`

## 2. 业务表分域

### A. 公司 / 岗位 / 投递域（求职主线）

| 表 | 行数(约) | 作用 |
|---|---:|---|
| `companies` | 61 | 企业档案：行业、类型、城市、官网、校招 URL、校招限投数 `max_campus_applications`、投递规则 `campus_application_rules` (v13) |
| `jobs` | 193 | 具体岗位：薪资、要求、匹配度、推荐权重 `recommendation_weight`、企业内推荐排名 `recommendation_rank`、推荐理由 `recommendation_reason` (v13) |
| `job_targets` | 500 | 目标企业清单（打分排序后的建档） |
| `job_target_recruitment_checks` | 214 | 目标企业校招/实习状态核查记录 |
| `platform_recruitment_leads` | 99 | 招聘平台/官网爬取的在招岗位线索 |
| `job_page_contexts` | 0 | 网申页实时快照（v19/v20）：url/JD 正文/硬门槛/表单 schema/`job_ad_id`。同一岗位详情页与报名表按 jobAdId 合流；有快照时 ATS/会审 JD 以本表为准 |
| `job_apply_runs` | 0 | 单岗投递编排器（v21/v22）：`apply_mode=precision|volume`。专投走 ATS/会审后 `released`；海投选分轨简历后 `volume_ready`。LLM 对话不当真相；两种模式都禁止自动点网页提交 |
| `job_apply_run_events` | 0 | 编排器审计：每次 pack/ingest/ats/arbitrate/release 一行 |

| `applications` | 2 | 正式投递记录（关联简历版本与提交物） |
| `application_timeline` | 2 | 投递后流程事件（笔试/面试/offer） |

### B. 简历域

| 表 | 行数(约) | 作用 |
|---|---:|---|
| `resume_versions` | 19 | 简历版本（role/company/label/state） |
| `resume_artifacts` | 158 | 简历文件元数据（SHA-256、file_state: source/draft/ready/submitted） |
| `resume_artifact_locations` | 58 | 文件路径登记（`data/cv/` 中实际位置的映射） |
| `resume_generation_rules` | 14 | 简历生成规则与硬红线契约库（去目标地点、严格A4单页饱满、去夸大几千几万数字、聚焦做了什么与具体提升、AI技能首位去Prompt、禁止强扣AI、禁止虚假MES包装、核心项目四点起步、工程成果真实量化、版面垂直韵律均衡防上半挤下半空等 14 项核心红线）(v15) |
| `resume_layout_templates` | 1 | 简历排版模板与样式契约库（存储 A4 页面尺寸、垂直留白上下限阈值、侧栏/主栏比例、证件照尺寸、全套 CSS 样式表与 JSON 布局参数，默认内置经典双栏照片版-垂直韵律均衡版 v3）(v16) |

### C. 测评 / 面试域

| 表 | 行数(约) | 作用 |
|---|---:|---|
| `mock_questions` | 1167 | 题库（由 `data/question-bank.*.json` 导入） |
| `mock_exam_records` / `mock_exam_answers` | 0 | 笔试模拟：答题记录与逐题作答 |
| `mock_interview_reports` / `interview_turns` | 0 | 模拟面试报告与逐轮问答 |
| `company_interview_guides` | 59 | 企业面试攻略（流程、问题、避坑） |

### D. GitHub 项目挖掘域

| 表 | 行数(约) | 作用 |
|---|---:|---|
| `github_project_candidates` | 8 | 候选开源项目（供简历项目挖掘） |
| `resume_project_proposals` | 0 | 候选项目 → 简历项目条目的提案（待确认） |

### E. GitHub 本人数据域（v9，2026-09-05 首次全量导入）

| 表 | 行数(约) | 作用 |
|---|---:|---|
| `github_profile` | 1 | 账号快照：登录名、公开仓库数、全站署名提交数（search 口径）、抓取时间 |
| `github_repositories` | 30 | 全部仓库（含私有）：语言、topics、license、star/fork、精确提交数、是否 fork |
| `github_commits` | 1559 | 13 个自有非 fork 仓库的逐条提交（sha、作者、时间、message），17 个 fork 只存计数 |

- 同步入口：`python scripts/sync_github_data.py`（走已认证 gh CLI，幂等可重跑：仓库 upsert、提交按 sha 去重）
- 口径说明：`github_commits` 只覆盖**默认分支**；fork 仓库的 `commit_count` 是上游仓库在默认分支的提交总数，不等于本人贡献
- 该域是简历实证数字（如 novel-mind 635 commits）的权威来源，与 memory/文档中的旧数字冲突时以库为准

### F. 简历证据域（v10，2026-09-05 两轮导入：旗舰 3 项目 + 全项目扫荡）

| 表 | 行数(约) | 作用 |
|---|---:|---|
| `resume_evidence_projects` | 15 | 全部仓库的简历价值判定（A/B/C 级 + fork 排雷记录）：定位、时间跨度、规模 |
| `resume_evidence_bullets` | 28 | bullet 候选：钩子类型 + 三层拷打答案（是什么/为什么/踩坑）+ 证据链 + 五档证据状态 |
| `resume_evidence_milestones` | 29 | 开发里程碑（日期 + 会话/commit 证据），按 (project_id, milestone_date) upsert 增量导入 |
| `resume_evidence_numbers` | 23 | 可验证数字清单（验证方式 + 是否公开 + 是否可上简历） |
| `resume_evidence_interview_qa` | 10 | 面试拷打预演：最可能追问 + 回答要点 |

- 来源：两轮并行子 agent 只读挖掘 `D:\ADLINK\数据分析` 会话库（2,569 会话/178k 消息）+ 本地 git + GitHub API，载荷在 `data/analysis/resume-evidence-*.json`
- 导入：`python scripts/import_resume_evidence.py [--input <json>]`（幂等，里程碑只增不清）；筛选标准来自 career-resume-audit / hook-writing / ai-flavor-patterns 三个 skill
- 关键排雷结论：TraceMemo 与 xiaozhi 三件套为**零贡献 fork**（严禁声称参与）；仓库已改名 **pk-core**（旧 personal-data-analysis-system URL 重定向）；博客"91 篇"口径待复核（本地实测 59 篇内容页）

### G. JD 对位证据域（v11，2026-09-05 首次导入）

| 表 | 行数(约) | 作用 |
|---|---:|---|
| `jd_evidence_packages` | 6 | 每个在投/目标 JD 一个证据包：聚焦层面、钩子策略（主钩/次钩/兜底）、缺口台账 |
| `jd_evidence_matches` | 22 | 包内匹配：指向 `resume_evidence_bullets` 的 (project_key, bullet_sort)，标注层面（技术深挖/数据工程/质量测试/工程治理/运维部署/AI 协作）与角色（primary/support/gap） |

- 来源：`data/analysis/jd-evidence-packages-2026-09.json`；导入 `python scripts/import_jd_evidence_packages.py`
- 用法：面试准备时按 `jd_key` 查包，先读 `hook_strategy`，再按 layer 拉对应 bullet 的三层拷打答案；`gap_notes` 是不能硬凑的诚实边界

### H. 面试拷打域（v12，2026-09-05 首次导入 + 同日补挖）

| 表 | 行数(约) | 作用 |
|---|---:|---|
| `interview_drill_points` | 185 | 按项目逐功能下钻的问答卡：feature/phase/depth（1=是什么 2=为什么取舍 3=踩坑细节）/question/answer_points/my_thinking（项目主人当时的原始思考）/evidence（session/commit/ADR 溯源） |

- 覆盖 8 个项目 72 个功能：novel-mind 50 点、数据分析系统 38、t5ai 34、career-os 30、pet-hospital 14、yanzi 7、博客双线各 6；howtocookskills 会话库零命中不硬编
- 185 点中 122 条带 my_thinking（用户原话+会话号）；空缺点位多为 08 月下旬~09 月会话（晚于会话备份截点）或 verifier/编排驱动决策——诚实留白不编造
- 来源：首轮 7 个并行子 agent + 同日补挖 3 个子 agent 与主 Agent 亲挖（t5ai 82 条 user 消息全量人工审读）；载荷 `data/analysis/interview-drill-2026-09.json` 与 `drill-gap-*.json`
- 导入：`python scripts/import_interview_drill.py`（按 project_key+feature+question 幂等，单项目载荷需包 `{"projects":[...]}`）

## 3. md 文档 ↔ 数据库关系

### 3.1 描述数据库的文档（docs/）

| 文档 | 与库的关系 |
|---|---|
| `docs/data-model.md`（本文） | 库结构 + 文档关系的单一事实源 |
| `docs/architecture.md` | 三层模型总览；**注意其"个人数据层"一节仍写 profile.yml + tracker.tsv，库级细节以本文为准** |
| `docs/resume-registry.md` | B 域（resume_* 三表）的操作规范：命名、file_state、SHA-256 口径 |
| `docs/how-to-use.md` | 用户操作入口，含 CLI 与 skill 的使用路径 |
| `docs/personal-data-warehouse.md` | 个人数据仓库 → LLM → `config/profile.yml` 的链路；**仓库数据不直接进 sqlite** |

### 3.2 与数据库同目录的 md / 数据文件（data/）

| 文件 | 与库的关系 |
|---|---|
| `data/question-bank.*.json` | 题库原始 JSON，经 `bin/question_bank_adapter.py` 导入 `mock_questions` |
| `data/NOTICE-*.md` | 各题库的来源与授权说明，与导入的 JSON 一一对应 |
| `data/aispeech_campus_jobs_*.json` | 岗位导入源，经 `scripts/import_aispeech_campus_jobs.py` 进 `jobs` |
| `data/platform_recruitment_jd.md` | `platform_recruitment_leads` 的**导出报告**（由 `scripts/export_platform_recruitment_jd.py` 生成），是库的产物而非事实源 |
| `data/job_target_recruitment_report.json` / `job_target_verification.json` | `job_target_recruitment_checks` / `job_targets` 核查流程的导出物 |
| `data/tracker.tsv` | **派生视图（目标态）**：应从 `applications`/`jobs`/`job_targets` 导出生成；当前仍为手工维护的平行线，改为导出物的迁移工作待放行 |
| `data/current-status.md` / `lessons-learned.md` | 自由笔记，与库无结构化关联 |
| `data/career_os.db` | **空库，遗留物**，无表，可忽略（删除前需用户确认） |
| `data/career_jobs.sqlite.pre-*.bak` | 四次大迁移前的备份快照 |

### 3.3 与数据库无直接读写的文档

- `knowledge/*.md`：参考层（题库策略、模板、清单），被 Skill 读取，不读写库。题库的**结构化数据**在 `data/*.json` → `mock_questions`，knowledge 只放方法论。
- `skills/*/SKILL.md`：操作层定义"何时、如何用库"，本身不含数据。
- `templates/`、`docs/01~04`（求职攻略）：静态参考内容。

## 4. 读写路径

```
skills/*/SKILL.md（操作层，md）
        │ 触发
        ▼
bin/career_jobs_cli.py        scripts/*.py            bin/*_adapter.py
(list/detail/apply/import-…)  (导入/核查/导出/冒烟)     (question_bank / job_source)
        └──────────────┬───────────┴──────────────┘
                       ▼
            bin/career_os_store.py（唯一迁移入口，schema v9）
                       ▼
            data/career_jobs.sqlite（22 张业务表）
                       │ 导出
                       ▼
      data/platform_recruitment_jd.md 等（报告产物）

scripts/sync_github_data.py ──(gh CLI 已认证)──► github_profile / github_repositories / github_commits
```

## 5. 已知缺口

1. `tracker.tsv` 目前仍是手工维护；按权威原则其目标态是库的导出物（生成脚本待实现，实施待放行）。
2. `docs/architecture.md` 的数据层描述已指向本文，三层图仍保留历史措辞。
3. ~~`career_os.db` 空文件与 4 个 `.bak` 属遗留物~~ 已清理（2026-09-05）：空库无表无引用，bak 为 v8 之前的旧 schema 快照，经核验后删除；主库迁移前的备份今后由 `.bak` 之外的机制或用户自行决定。
