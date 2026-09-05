# 开源项目统一适配方案

Career OS 保持本地 profile、岗位 SQLite、tracker.tsv 和面试/笔试报告为唯一事实源。外部开源项目以插件方式接入能力，不直接改写核心流程。

## 优先级

| 优先级 | 缺口 | 适配目标 | 当前状态 |
|---|---|---|---|
| P0 | 答题结果无留痕、代码题执行边界不清 | Exameow 题库格式 + Judge0 | 已接入统一题库导入、Judge0 插件和受信本地回退 |
| P0 | 面试分数固定、无法复盘、JD 与面试脱节 | DeepInterview / AI Mock Interviewer 的 prep-live-report 思路 | 已接入 JD 轨道选题、开放式题、追问、四维 rubric、逐题来源和 SQLite 报告 |
| P0 | 外部项目耦合、路径写死 | Career OS Plugin Manager | 已接入 manifest、capability、启用/禁用和故障回退 |
| P0 | 真实模型面试 Provider 缺失 | OpenAI-compatible 本地/托管模型 | 已接入 `openai-compatible-interview`；默认关闭、无 endpoint 不联网、失败回退 local-rubric |
| P0 | 机考不符合真实线上测试节奏 | Exameow/自有题库组卷思路 | 默认 JD 分层抽取 30 题/30 分钟，`--all` 仅审计 |
| P1 | 岗位来源和 ATS 评估缺少统一入口 | CareerDesk、CareerSail、career-ops | 已预留 `job_source` / `resume_evaluation` 插件契约，当前只允许人工确认后的导入 |
| P2 | 语音面试和浏览器 UI | DeepInterview / AI Mock Interviewer | 仅保留适配位；当前文本链路先保证可追溯 |
| P1 | JD 与个人项目素材脱节 | GitHub REST / project-source 插件 | 已接入候选库；人工确认和证据通过后才生成简历提案 |

## 插件契约

每个插件放在 `plugins/<plugin-id>/plugin.json`，声明：

- `capabilities`：`job_source`、`question_bank`、`code_runner`、`interview_agent` 等能力；
- `entrypoint`：延迟加载的 `module:create_plugin`；
- `license`、版本和描述；
- 默认关闭，使用 `CAREER_OS_PLUGINS=judge0,exameow,openai-compatible-interview` 启用所需插件。

核心通过 `bin/career_os_plugins.py` 的 `PluginManager.capability()` 获取能力。插件加载失败会隔离并回退，不阻断本地求职数据。

## 已映射的开源项目

- [CareerDesk](https://github.com/xinhuangcs/CareerDesk)：岗位研究、简历适配、练习记录；映射到 `job_source` 和 `resume_evaluation`。
- [JobHunter](https://github.com/wcanfly/JobHunter--)：中文校招流程、语音模拟面试；映射到 `job_source`、`interview_agent`。
- [CareerSail](https://github.com/genius916/CareerSail)：Playwright/飞书岗位同步；只接收其导出结果，不在 Career OS 中自动登录或提交。
- [career-ops](https://github.com/career-ops-hq/career-ops)：A-H 评估和 ATS PDF；作为 `resume_evaluation` 契约参考。
- [Exameow](https://github.com/heshengtao/exameow)：随机组卷、计时、错题复盘；通过 `bin/question_bank_adapter.py` 导入自有 JSON/CSV 题库。
- [Open Quiz Commons](https://github.com/prahladyeri/open-quiz-commons)：CC BY-SA 4.0 的 Python/pandas/JavaScript/Rust/DevOps MCQ 数据；基础快照和按当前 JD 缺口选择的 10 个扩展快照（678 题）位于 `data/question-bank.github-openquiz*.json`，通过统一题库适配器导入，保留来源题号、模块和许可证说明。新增批次覆盖测试质量、系统自动化、数据库/服务端 API、数据分析、机器学习、异步/FFI/边缘运维基础；Rust 批次只作为嵌入式系统基础，不能替代 C/C++/RTOS 专项题。
- [Sering-Hong/embedded-interview](https://github.com/Sering-Hong/embedded-interview)：MIT 许可的 C 指针、FreeRTOS、MQTT 开放式面试题；12 题快照位于 `data/question-bank.github-seringhong-embedded-interview.json`，保持 `question_type=interview`，不伪造选择题干扰项。
- [ather-techie/rag-interview-system](https://github.com/ather-techie/rag-interview-system)：MIT 许可的 Advanced/Agentic/Graph/CRAG/RAG 评测开放式题；10 题快照位于 `data/question-bank.github-ather-rag-interview.json`，由 AI/RAG JD 轨道选择。
- [Amir7698/embedded-interview-prep](https://github.com/Amir7698/embedded-interview-prep)：上游 README 声明 MIT 的嵌入式 rapid-fire 与 bug-hunt 题；快照 `data/question-bank.github-embedded-interview-prep.json` 共 120 题，补充 CAN/Modbus、FreeRTOS、嵌入式 Linux、测试与现场故障调试。该上游快照未包含独立 LICENSE 文件，保留来源边界，不声称为企业内部题。
- [AdithSuresh2004/exam-questions](https://github.com/AdithSuresh2004/exam-questions)：MIT 结构化题库；从含完整答案解释的 CUET MCA/NIMCET mock 文件导入 175 道数学、逻辑/情景判断、计算机基础题，快照位于 `data/question-bank.github-exam-questions-aptitude.json`。缺少答案解释的 `nimcet_mock2` 未导入。
- [rubynor/bigfive-web](https://github.com/rubynor/bigfive-web)：MIT 代码仓库，使用 IPIP public-domain 条目；新增 `data/personality-bank.github-bigfive-web-ipip-neo-120.json`，补充 120 道英文 IPIP-NEO-120 性格条目，正反向计分方向保留。
- [imsunilvaghela/TheEmbeDEADInterview](https://github.com/imsunilvaghela/TheEmbeDEADInterview)：社区嵌入式题库，覆盖 Bluetooth、客户沟通、软技能和驱动等主题；当前仓库未发现独立许可证文件，因此只登记为候选来源，不复制题干。

企业测评情报另存于 `data/assessment-intelligence.json` / `knowledge/assessment-banks/assessment-intelligence.md`：官方来源只记录公开的流程和题型家族，社区来源记录年份与 `reported` 证据等级；不抓取或复制北森、SHL、企业自研平台的专有正式题目。
- [Judge0](https://github.com/judge0/judge0)：自托管代码执行；通过 `plugins/judge0` 接入，未配置服务时不把本机进程冒充安全沙箱。
- [DeepInterview](https://github.com/ngoanpv/DeepInterview)：prep/live/post 和语音链路；当前由文本 Agent 的报告契约承接，语音作为 P2 插件。
- [AI Mock Interviewer](https://github.com/iarsingh/ai-mock-interviewer)：DevOps/SRE/Cloud 题库和本地模型；可通过题库/面试插件替换本地 rubric。
- [GitHub REST Repository Search](https://docs.github.com/en/rest/search/search#search-repositories)：只读项目候选来源；通过 `github-project-scout` 暴露 `project_source`，保留仓库元数据和来源，不自动 clone/fork 或声称个人贡献。

当前 `deepinterview` 与 `ai-mock-interviewer` 插件是本地兼容适配器：可插拔地提供 `prepare/questions/score/report` 契约，但 `external_service=false`，评分引擎明确记录为 `local-rubric`，未伪装成已接入远程模型。

`openai-compatible-interview` 是真实模型适配器：使用标准库 HTTP 调用用户配置的 `/chat/completions`，结构化解析五维评分；缺少 endpoint、响应不合规或网络失败均在写库前/逐题评分边界回退到 `local-rubric`。回归脚本使用本地假 HTTP 服务，不需要 API Key。

外部题库只允许导入用户有权使用的内容，不复制 Beisen、SHL 等受版权保护的题目。所有岗位导入和申请状态变化保留人工确认。

项目候选也遵循同一边界：GitHub 搜索结果是外部参考，不等于个人经历。候选写入 `github_project_candidates`，人工核验后写入 `resume_project_proposals`；只有两次显式确认（`confirm --confirm`、`apply --confirm`）才会追加到简历 Markdown。`reference`、`adapted`、`implemented` 三种口径必须与可复现的个人证据一致。

## 本机 Judge0 部署

`deploy/judge0/docker-compose.yml` 提供一个仅绑定 `127.0.0.1:2358` 的 Judge0 1.13.0 实例，密码和 API token 由部署脚本随机生成到被忽略的本地文件；不会写入 Career OS SQLite。

```powershell
pwsh -NoProfile -File scripts/deploy-judge0.ps1

# 当前 PowerShell 会话加载本机 token（脚本已生成）
Get-Content deploy/judge0/runtime.env | ForEach-Object {
  if ($_ -match '^([^=]+)=(.*)$') { Set-Item "Env:$($matches[1])" $matches[2] }
}
python bin/career_jobs_cli.py code-sandbox 11
```

该部署使用 Judge0 官方 compose 拓扑（server/worker/Postgres/Redis），但在 Windows Docker Desktop 上属于本地实验运行；Judge0 官方文档提示其发布包主要按 Linux/macOS 测试。若容器或 isolate 在 Windows 上不可用，代码题会明确回退为 `--trusted-local`，不会把普通本机进程标称为安全沙箱。

**本次实测（2026-09-02）：** `/system_info` 与 `/languages` 可用（47 种语言，Python id 71），但实际提交在 Windows Docker Desktop 的 isolate 阶段失败：`Failed to create control group /sys/fs/cgroup/memory/box-1/`，随后 `/box/script.py` 不存在。因此 Judge0 部署状态为 **服务可达 / 代码执行 PARTIAL**；面试报告、追问、插件发现和故障隔离均已通过临时数据库实测。要获得真正的安全代码执行，应迁移到 Linux/WSL2 VM；当前默认保持可信本地回退的显式安全边界。

## 使用示例

```powershell
# 查看插件（默认全部关闭）
python bin/career_jobs_cli.py plugins

# 导入外部项目导出的题库，按 source_plugin 幂等更新
python bin/career_jobs_cli.py import-questions .\export.json --source exameow
python bin/career_jobs_cli.py import-questions .\export.json --source exameow --apply

# 连接自托管 Judge0
$env:CAREER_OS_PLUGINS = 'judge0'
$env:JUDGE0_URL = 'http://127.0.0.1:2358'
python bin/career_jobs_cli.py code-sandbox 11

# 没有 Judge0 时，仅对本人可信代码显式开启本地进程
python bin/career_jobs_cli.py code-sandbox 11 --trusted-local
```
