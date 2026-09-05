# 求职全流程使用指南

## 快速开始

### 1. 编辑个人画像

```bash
# 编辑 config/profile.yml，填入你的真实信息
```

**用个人数据仓库 + LLM 更新（推荐）**

数据仓库（见 `config/personal-data-warehouse.yml` 中配置的仓库路径）通过 MCP 给 LLM 供数；LLM 再改 Career OS，不是脚本自动同步。

1. 配置路径：`config/personal-data-warehouse.yml`（可从 example 复制）  
2. 启动仓库 REST + 在客户端挂 MCP（见 `docs/personal-data-warehouse.md`）  
3. 对话触发：`根据我的数据仓库更新 profile` → skill **career-personal-data-update**

### 2. 安装已完成的 Skill

将 `skills/` 下的 Skill 文件夹复制到你所用的 AI 助手的 skill 目录(如 Claude Code 的 `~/.claude/skills/`、各类 agent 的 skill 路径)。skill 正文平台中立,不绑定特定 agent。

**当前实际可用(经文件系统审计核对):**
- `career-daily-driver/` → 每日行动编排 + 状态边界（🟢）
- `career-self-assessment/` → 自我定位 + 方向推荐 + 差距分析（结构审计通过；后续可继续深化 profile 匹配）
- `career-industry-research/` → 行业调研 + 趋势判断 + 决策辅助(🟢)
- `career-learning-path/` → 技能差距诊断 + 学习计划 + 资源推荐(🟢)
- `career-company-check/` → 公司背调 + 风险扫描 + 社区口碑(🟢)
- `career-general-recruit/` → 岗位搜索 + JD 解读 + 简历定制(🟢)
- `career-app-tracker/` → 投递管理 + 进度追踪 + 自动提醒(🟢)
- `career-assessment-prep/` → 笔试测评(北森/智鼎/SHL/赛码)(🟢)
- `career-interview-master/` → 技术面/行为面/复盘/谈薪/Offer 决策(🟢)
- `career-onboarding-prep/` → 入职前准备 + 第一周 + 前 90 天 + 运维专属(🟢)
- `career-probation-survival/` → 试用期生存 + 踩坑应对 + 转正指南(🟢)
- `career-english-interview-prep/` → 外企/国际化团队英文面试训练(🟢)
- `career-resume-audit/` → 简历证据、夸大风险和版本审计(🟢)

**全部 14 个 skill 已创建，16 步求职全流程已覆盖。** 另有本地 CLI 运行时支持题库/岗位导入、答题报告、动态模拟面试和可插拔开源适配器。

> 完整审计见 `.planning/STATUS.md`,重跑审计用 `pwsh scripts/audit.ps1`。

### 运行时与插件

```powershell
python bin/career_jobs_cli.py plugins
python bin/career_jobs_cli.py stats
python bin/career_jobs_cli.py exam [job_id] [--limit N] [--minutes N] [--seed N] [--all]
python bin/career_jobs_cli.py personality [job_id] [--full|--kind quick|full]
python bin/career_jobs_cli.py assessment-intel [企业名]
python bin/career_jobs_cli.py interview <企业ID或名称> [job_id]
python bin/career_jobs_cli.py code-sandbox <题目ID> --trusted-local
python bin/career_jobs_cli.py import-questions <file> --source exameow   # 默认预览
python bin/career_jobs_cli.py import-questions <file> --source exameow --apply
python bin/career_jobs_cli.py import-jobs <file> --source careerdesk   # 默认预览
python bin/career_jobs_cli.py import-jobs <file> --source careerdesk --apply

# 根据数据库 JD 生成 GitHub 项目候选（默认只预览查询，不联网）
python bin/career_jobs_cli.py project-candidates search --job 42
# 明确联网搜索并把候选元数据保存到本地 SQLite
python bin/career_jobs_cli.py project-candidates search --job 42 --live --limit 10
python bin/career_jobs_cli.py project-candidates list --job 42
# 人工核验仓库、许可证和个人证据后，先生成确认提案
python bin/career_jobs_cli.py project-candidates confirm 1 --resume cv-ops --evidence "本地可复现的 IoT 网关联调记录" --claim-level adapted --confirm
python bin/career_jobs_cli.py project-candidates proposals
# 再次明确确认，才追加可审阅块到 data/cv/cv-ops.md
python bin/career_jobs_cli.py project-candidates apply 1 --confirm
```

`exam` 默认按 JD 匹配题池分层抽取 30 题、建议限时 30 分钟，并把题目 ID、来源、种子和题池规模写入报告；`--seed` 用于复现实验，`--all` 仅用于审计全量题池。`personality` 默认运行项目快测 15 题；`--full` 或 `--kind full` 才运行 GitHub/IPIP-NEO-120 的 120 题完整模式。

代码题优先配置自托管 Judge0；`--trusted-local` 只对本人可信代码开放，不是安全沙箱。`personality` 命令运行 GitHub/IPIP 开放题库，结果只作职业准备和复盘参考，不是临床诊断或录用结论。本项目既有题库与外部题库都通过统一适配器导入，岗位/题库导入只做字段映射，不自动投递。

题库来源可重复导入（`--apply` 才写入，按来源题目 ID 幂等更新）：

```powershell
python bin/import_question_bank.py data/personality-bank.github-ipip.json --source github-deep-personality-oss --apply
python bin/import_question_bank.py data/assessment-bank.project.json --source career-os-project --apply
python bin/import_question_bank.py data/question-bank.github-openquiz.json --source github-open-quiz-commons --apply
Get-ChildItem data/question-bank.github-openquiz-*.json | ForEach-Object { python bin/import_question_bank.py $_.FullName --source github-open-quiz-commons --apply }
python bin/import_question_bank.py data/question-bank.github-seringhong-embedded-interview.json --source github-seringhong-embedded-interview --apply
python bin/import_question_bank.py data/question-bank.github-ather-rag-interview.json --source github-ather-rag-interview --apply
python bin/import_question_bank.py data/question-bank.github-embedded-interview-prep.json --source github-embedded-interview-prep --apply
python bin/import_question_bank.py data/question-bank.github-exam-questions-aptitude.json --source github-exam-questions-aptitude --apply
python bin/import_question_bank.py data/personality-bank.github-bigfive-web-ipip-neo-120.json --source github-bigfive-web-ipip-neo-120 --apply
```

`question-bank.github-openquiz*.json` 是 GitHub `prahladyeri/open-quiz-commons` 的 CC BY-SA 4.0 题库快照：基础快照 25 题，按当前 JD 缺口扩展 678 题，合计 703 道技术客观题。另有 142 道 MIT/README-MIT 嵌入式开放式面试题（C/FreeRTOS/MQTT 12 题、RAG/Agent 10 题、embedded-interview-prep 120 题）和 175 道 MIT 数学/逻辑/计算机客观题；IPIP-NEO-120 新增 120 道公开域性格条目。所有快照保留上游题干、答案解释、来源文件、模块、题号和许可证证据；运行 `exam` 时只组客观题，运行 `interview <company> <job_id>` 时会按 JD 轨道消费开放式题。FAE/SJT/客户冲突开放题、英语结构化题库仍未达到“许可清晰 + 可验证答案”的导入门槛；`TheEmbeDEADInterview` 虽覆盖 Bluetooth/客户沟通/软技能，但仓库未提供独立许可证，因此只作为候选来源，不复制其题干。

新增批次的来源边界与未导入文件说明见 `data/NOTICE-question-bank.github-expansion.md`；可运行 `python scripts/github-expansion-smoke.py` 做结构、许可证证据和幂等导入校验。

传入岗位 ID 时，`exam <job_id>` 会复用 `jd_assessment_mapper` 的轨道结果，只从题目的 `company_tags` 里筛选对应方向，再按类别分层抽取；不传 ID 或岗位未命中特定轨道时使用全量客观题池。这样新增题库会实际参与岗位定向组卷，而不是只停留在文件层。

企业/社区测评情报使用：

```powershell
python bin/career_jobs_cli.py assessment-intel
python bin/career_jobs_cli.py assessment-intel 宝洁
python bin/career_jobs_cli.py assessment-intel --job 42
python bin/career_jobs_cli.py assessment-intel --all-jobs
```

该命令只显示官方流程、题型家族、社区报告年份、可信度和来源链接，不复制企业专有原题。社区帖子是历史信号，收到当季测评邮件后应以岗位、地区、供应商和截止时间为准。

`assessment-intel --job <ID>` 会读取 SQLite 当前 JD 的岗位类别、标题、职责、要求和英语要求，输出命中的技能信号、建议题型和训练入口；这是“基于 JD 的推导”，不会伪装成企业内部题库。`--all-jobs` 用于查看当前岗位池的轨道覆盖。

`interview <企业ID或名称> <job_id>` 会把同一份 JD 画像传给模拟面试 Agent；报告中的 `qa_transcript_json.context` 保存轨道、匹配信号、题型族和每题来源。插件默认关闭，启用本地兼容实现：`$env:CAREER_OS_PLUGINS='deepinterview'`。启用真实 OpenAI-compatible Provider：

### JD 驱动的 GitHub 项目候选库

`project-candidates` 读取 `jobs` 表中的岗位职责、要求、类别和标题，由 `jd_assessment_mapper` 生成可解释的搜索关键词。`--live` 使用只读 GitHub REST 搜索；可设置 `GITHUB_TOKEN` 提高 API 配额，但 Token 只从环境变量读取，不写入 SQLite、日志或简历。候选记录保留仓库链接、许可证、活跃时间、Star、匹配关键词和 Provider，重复搜索按“岗位 + Provider + 仓库名”幂等更新。

候选项目不是个人经历。`confirm` 要求人工确认和 `--evidence`，并记录 `reference`（外部参考）、`adapted`（个人改造）或 `implemented`（个人实现）口径；`apply` 还要再次带 `--confirm`，只向指定 `data/cv/*.md` 追加带来源的“开源项目补强（人工确认）”块，重复执行不会重复追加。默认不 clone、fork、提交 PR、自动投递或覆盖已有简历段落。候选和提案表会随 `get_db()` 自动创建，真实数据库文件仍由 `.gitignore` 保护。

启用可拔插 Provider：

```powershell
$env:CAREER_OS_PLUGINS = 'github-project-scout'
python bin/career_jobs_cli.py project-candidates search --job 42 --live
```

未启用插件时 CLI 使用同一只读 REST 实现作为本地回退；后续可把企业内部项目索引或本地静态库实现为 `project_source` 插件。

```powershell
$env:CAREER_OS_PLUGINS = 'openai-compatible-interview'
$env:CAREER_OS_LLM_BASE_URL = 'http://127.0.0.1:8000/v1'
$env:CAREER_OS_LLM_MODEL = 'your-model'
python bin/career_jobs_cli.py interview <企业ID或名称> <job_id>
```

API Key 只从 `CAREER_OS_LLM_API_KEY` 读取，不写入报告；未配置 endpoint 或请求失败时自动回退 `local-rubric`。本地假服务回归见 `python scripts/openai-interview-agent-smoke.py`。

### Docker 本地运行

顶层 Docker 仅封装 Career OS CLI，SQLite 通过 `./data:/app/data` 挂载，避免把个人数据库打进镜像：

```powershell
docker build -t career-os:local .
docker compose run --rm career-os
docker compose run --rm career-os python scripts/docker-healthcheck.py
```

Judge0 仍按 `deploy/judge0/docker-compose.yml` 单独部署；Windows Docker Desktop 的 isolate/cgroup 限制仍保持原有安全边界。

### 3. 对话中触发

在任意支持 skill 触发的 AI 助手中说:
```
  "根据数据仓库更新我的画像"     → career-personal-data-update
  "用 MCP 证据刷新技能和项目"   → career-personal-data-update
  "我适合做什么方向?"           → career-self-assessment
  "运维这行还有前景吗"           → career-industry-research
  "我该学什么补差距"             → career-learning-path
  "帮我搜运维实习岗位,苏州"     → career-general-recruit
  "帮我解读这个JD"               → career-general-recruit
  "帮我改简历投这个岗位"         → career-general-recruit
  "帮我查一下XX公司"             → career-company-check  
  "北森测评怎么准备？"           → career-assessment-prep
  "帮我记录一下投了XX公司"       → career-app-tracker
  "帮我模拟面试"                 → career-interview-master
  "面试完了,复盘一下"           → career-interview-master
  "HR要谈薪,期望多少"           → career-interview-master
  "收到两个offer,选哪个"        → career-interview-master
  "拿到offer,入职前准备什么"    → career-onboarding-prep
  "刚入职,试用期怎么过"         → career-probation-survival
  "快转正了,述职怎么写"         → career-probation-survival
```

## 开发进度

> 以 `pwsh scripts/audit.ps1` 和 `pwsh scripts/smoke-test.ps1` 的当前输出为准；它们验证结构契约，不等同于真实投递效果。

```
🟢 结构审计通过（16 步全流程覆盖）:
  步骤  2   : 行业调研                 (career-industry-research)
  步骤  3   : 学习路径规划             (career-learning-path)
  步骤  4-5  : 岗位搜索 + JD解读        (career-general-recruit)
  步骤  6   : 公司背调                 (career-company-check)
  步骤  7   : 简历定制                 (career-general-recruit)
  步骤  8   : 投递管理                 (career-app-tracker)
  步骤  9   : 笔试测评                 (career-assessment-prep)
  步骤 10-11: 技术 + 行为面试          (career-interview-master)
  步骤  12  : 面试复盘                 (career-interview-master)
  步骤 13-14: 谈薪 + Offer决策         (career-interview-master)
  步骤  15  : 入职准备                 (career-onboarding-prep)
  步骤  16  : 试用期生存               (career-probation-survival)

后续优化：
  步骤  1   : 自我定位                 (继续深化 profile 匹配逻辑)
```

## 知识库同步

knowledge/ 目录下各子目录的参考文档需要从外部仓库定期同步：

| 知识域 | 来源 | 同步方式 |
|--------|------|---------|
| roadmaps/ | developer-roadmap / roadmap.sh | git submodule 或手动 clone |
| assessment-banks/ | CSDN/知乎/B站 拆解文章 | 手动整理为结构化 Markdown |
| interview-banks/ | CS-Notes / system-design-primer | git submodule |
| onboarding/ | awesome-engineer-onboarding | git clone |
| survival/ | software-engineer-survival-guide | git clone |
