# Career OS — 求职全流程操作系统

> 一个个人求职平台的完整框架：Skill 操作层 × 参考库知识层 × 个人数据层 × 可插拔运行时

## 核心理念

```
Skill (操作层)  = 告诉AI怎么做   →  流程、判断、追问、输出格式
Knowledge (知识层) = 给AI喂什么   →  题库、模板、案例、框架、清单  
Data (数据层)      = 关于你是谁   →  简历、技能栈、求职画像、投递记录
                      ↑ LLM 根据「个人数据仓库」MCP 证据更新（非批处理同步）
```

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Career OS 平台                        │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Skills   │  │Knowledge │  │  Data    │               │
│  │ 操作层   │  │ 知识层   │  │ 数据层   │               │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │             │             │                      │
│  ┌────┴─────────────┴─────────────┴────┐                │
│  │         求职全流程 16 步骤            │               │
│  │  定位 → 投递 → 笔试 → 面试 → 入职    │               │
│  └─────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

运行时通过 `bin/career_os_plugins.py` 按 capability 适配外部开源项目；插件默认关闭、可随时拔出。新增 `project_source` 能力用于把 JD 映射为 GitHub 开源项目候选，人工确认后才进入简历提案。

## 16 步流程 × 三层资源

> 状态以 `.planning/STATUS.md` 审计为准,可通过 `pwsh scripts/audit.ps1` 重新核对。

| # | 步骤 | Skill | 知识库 | 状态 |
|---|------|-------|--------|------|
| 1 | 自我定位 | career-self-assessment | MBTI/霍兰德/技能评估框架 | 🟡 PARTIAL |
| 2 | 行业调研 | career-industry-research | reportcamp 8143篇报告索引 | 🟢 VERIFIED |
| 3 | 学习路径 | career-learning-path | developer-roadmap / roadmap.sh | 🟢 VERIFIED |
| 4 | 岗位搜索 | career-general-recruit | WebSearch 实时搜索 | 🟢 VERIFIED |
| 5 | JD 解读 | career-general-recruit | JD 模板库 | 🟢 VERIFIED |
| 6 | 公司背调 | career-company-check | 企查查/天眼查 MCP | 🟢 VERIFIED |
| 7 | 简历定制 | career-general-recruit | STAR 模板 + JD 关键词库 | 🟢 VERIFIED |
| 8 | 投递管理 | career-app-tracker | job-tracker 开源工具 | 🟢 VERIFIED |
| 9 | 笔试测评 | career-assessment-prep | 北森/智鼎/SHL/赛码 题库 | 🟢 VERIFIED |
| 10 | 技术面试 | career-interview-master | CS-Notes / system-design-primer | 🟢 VERIFIED |
| 11 | 行为面试 | career-interview-master | behavioral_question_bank | 🟢 VERIFIED |
| 12 | 面试复盘 | career-interview-master | 失败案例库 | 🟢 VERIFIED |
| 13 | 谈薪 | career-interview-master | 薪资行情 + 谈判脚本 | 🟢 VERIFIED |
| 14 | Offer 决策 | career-interview-master | 多维度评估框架 | 🟢 VERIFIED |
| 15 | 入职准备 | career-onboarding-prep | awesome-onboarding | 🟢 VERIFIED |
| 16 | 试用期生存 | career-probation-survival | First 90 Days 框架 | 🟢 VERIFIED |

> **结构验证进度：14/14 skill 通过本地结构审计，16 步流程全部覆盖。** 运行时已补上题库导入、代码执行适配、动态面试报告和插件契约；真实投递转化仍待实战验证。

## 目录结构

```
career-os/
├── README.md                    ← 你在这里
├── Dockerfile                   # CLI 运行时镜像
├── docker-compose.yml           # 本地数据挂载与健康检查
├── scripts/
│   ├── audit.ps1                # 可重复审计脚本(VER-01)
│   ├── smoke-test.ps1           # Skill/数据契约冒烟
│   ├── runtime-smoke.py         # SQLite/插件/执行器冒烟
│   ├── personality-smoke.py     # 职业性格测评临时库全链路冒烟
│   ├── jd-assessment-smoke.py   # 当前 JD → 测评轨道映射冒烟
│   ├── github-expansion-smoke.py # 新增 GitHub 快照结构/许可证/幂等校验
│   ├── github-expansion-runtime-smoke.py # 新增题库真实运行器全链路冒烟
│   ├── openai-interview-agent-smoke.py # OpenAI-compatible 本地假服务链路冒烟
│   ├── github-project-candidates-smoke.py # JD→GitHub候选库→简历确认链路冒烟
│   └── docker-healthcheck.py     # 容器内 SQLite 健康检查
├── skills/                      # 操作层: AI 助手 Skill(平台中立)
│   ├── career-personal-data-update/ # 🟢 仓库证据 → LLM → 更新画像
│   ├── career-resume-audit/        # 🟢 简历证据与版本审计
│   ├── career-self-assessment/     # 🟡 自我定位 (步骤 1)
│   ├── career-industry-research/   # 🟢 行业调研 (步骤 2)
│   ├── career-learning-path/       # 🟢 学习路径 (步骤 3)
│   ├── career-general-recruit/     # 🟢 岗位搜索/JD/简历 (步骤 4-5,7)
│   ├── career-company-check/       # 🟢 公司背调 (步骤 6)
│   ├── career-app-tracker/         # 🟢 投递管理 (步骤 8)
│   ├── career-assessment-prep/     # 🟢 笔试测评 (步骤 9)
│   ├── career-interview-master/    # 🟢 面试/谈薪/Offer (步骤 10-14)
│   ├── career-onboarding-prep/     # 🟢 入职准备 (步骤 15)
│   ├── career-probation-survival/  # 🟢 试用期生存 (步骤 16)
│   ├── career-daily-driver/        # 🟢 每日行动编排
│   └── career-english-interview-prep/ # 🟢 英文面试
│
├── knowledge/                   # 知识层: 参考库文档
│   ├── README.md                # 知识层索引
│   └── <11 个领域>/             # 均含 README 与参考内容（46 个文件）
│
├── config/                      # 数据层: 个人配置
│   ├── profile.yml              # 🟢 求职画像
│   └── personal-data-warehouse.yml  # 个人数据仓库路径（LLM 只读源）
│
├── data/                        # 数据层: 投递数据
│   ├── tracker.tsv              # 🟢 投递追踪表（canonical-v2）
│   ├── current-status.md        # 🟢 跨会话状态
│   ├── lessons-learned.md       # 🟢 反馈回路
│   ├── personality-bank.github-ipip.json # 🟢 GitHub/IPIP 开放题库（15题）
│   ├── personality-bank.github-bigfive-web-ipip-neo-120.json # 🟢 GitHub/IPIP-NEO-120（120题）
│   ├── question-bank.github-openquiz.json # 🟢 GitHub/Open Quiz Commons 基础快照（25题）
│   ├── question-bank.github-openquiz-*.json # 🟢 按当前 JD 扩展的公开技术题快照（678题）
│   ├── question-bank.github-seringhong-embedded-interview.json # 🟢 MIT C/FreeRTOS/MQTT 开放式面试题（12题）
│   ├── question-bank.github-ather-rag-interview.json # 🟢 MIT RAG/Agent 开放式面试题（10题）
│   ├── question-bank.github-embedded-interview-prep.json # 🟢 MIT 嵌入式/CAN/RTOS/调试开放题（120题）
│   ├── question-bank.github-exam-questions-aptitude.json # 🟢 MIT 数学/逻辑/计算机客观题（175题）
│   ├── assessment-intelligence.json      # 🟢 企业官方/社区测评情报（不含专有原题）
│   ├── assessment-bank.project.json      # 🟢 本项目既有测评题库（5题）
│   ├── assessment-bank.example.json      # 本项目既有示例题库
│   ├── NOTICE-personality-bank.md        # Big Five/IPIP 上游许可与来源追溯
│   ├── NOTICE-question-bank.github-openquiz.md # Open Quiz Commons 基础快照许可与来源追溯
│   ├── NOTICE-question-bank.github-openquiz-expanded.md # 扩展快照许可与 JD 选择依据
│   └── NOTICE-question-bank.github-expansion.md # 新增 GitHub 扩展题库许可与来源追溯
│
├── templates/                   # 模板
│   └── cv-template.md           # 🟢 简历模板
├── bin/                         # 本地运行时 CLI、适配器和报告引擎
├── plugins/                     # 外部开源项目 capability 插件
│
├── .planning/                   # 项目规划(状态/路线图/需求/审计)
│   ├── PROJECT.md
│   ├── REQUIREMENTS.md
│   ├── ROADMAP.md
│   ├── STATE.md
│   ├── STATUS.md                # 🟢 文件系统审计基线
│   └── config.json
│
└── docs/                        # 文档
    ├── architecture.md          # 系统架构
    ├── how-to-use.md            # 使用指南
    ├── personal-data-warehouse.md  # 仓库×LLM×Career OS 联动
    └── open-source-integration.md  # 开源项目适配矩阵
```

## JD 驱动的项目候选库

```powershell
python bin/career_jobs_cli.py project-candidates search --job 42
python bin/career_jobs_cli.py project-candidates search --job 42 --live --limit 10
python bin/career_jobs_cli.py project-candidates list --job 42
python bin/career_jobs_cli.py project-candidates confirm <候选ID> --resume cv-ops --evidence "个人可复现证据" --claim-level adapted --confirm
python bin/career_jobs_cli.py project-candidates apply <提案ID> --confirm
```

候选库记录 GitHub 仓库链接、许可证、活跃度和 JD 匹配词；`--live` 只读访问 GitHub REST。候选不是个人经历，必须人工核验并提供证据；`apply` 只追加带来源的可审阅 Markdown 块，不自动 clone、fork、投递或覆盖既有简历段落。详见 [`docs/how-to-use.md`](docs/how-to-use.md) 和 [`docs/open-source-integration.md`](docs/open-source-integration.md)。

## 个人数据仓库（LLM 供数）

求职画像的**行为证据**来自本机仓库 `数据分析`，经 MCP 只读暴露给 LLM；由 skill **career-personal-data-update** 更新 `profile.yml` 等，而不是脚本自动覆盖。

详见：`docs/personal-data-warehouse.md`

## 当前状态

- **阶段:** Phase 5 Operational Layer — 将已完成的基础设施用于真实求职
- **结构验证:** 14 个 skill、11 个知识域均通过本地审计；16 步流程已覆盖
- **运行时能力:** 题库导入、JD 定向客观题/开放式面试、30 题/30 分钟模拟组卷、快测/完整性格模式、答题/面试报告、Judge0/trusted-local 代码执行、岗位导入和插件管理均可用；面试报告保留逐题来源，插件默认关闭且明确区分本地评分与外部服务
- **真实模型适配:** `openai-compatible-interview` 默认关闭；配置 `CAREER_OS_LLM_BASE_URL` 后才访问 `/chat/completions`，未配置或请求失败自动回退 `local-rubric`。
- **Docker:** 顶层 `Dockerfile`/`docker-compose.yml` 只封装本地 CLI 与 SQLite；Judge0 仍使用 `deploy/judge0/` 独立 compose，Windows isolate 的 cgroup 边界不被伪装为已解决。
- **实战验证:** tracker 统计仍为 0，Agent 运行时与求职转化效果尚未验证
- **平台中立:** skill 正文不绑定任何特定 AI 助手(WorkBuddy/Claude/Cursor 等),可移植到多种 agent
- **真相来源:** `.planning/STATUS.md`(由 `scripts/audit.ps1` 生成)
- **重审计命令:** `pwsh scripts/audit.ps1`

## 类似项目参考

| 项目 | Stars | 定位 | 与本系统差异 |
|------|-------|------|------------|
| **career-ops** | 48.9K | Claude Code 驱动的 AI 求职管线，含 14 个 skill mode | 西方市场为主，绑定 Claude Code |
| **本系统** | - | 平台中立的中文求职全流程 OS | 16 步完整覆盖 + 参考库独立管理 + 中文生态 + skill 可移植到多种 agent |

开源适配详情见 [`docs/open-source-integration.md`](docs/open-source-integration.md)。

本机 Judge0 部署：`pwsh -NoProfile -File scripts/deploy-judge0.ps1`；凭据只生成到被忽略的 `deploy/judge0/judge0.conf` 与 `runtime.env`。
