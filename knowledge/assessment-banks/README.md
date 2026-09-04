# assessment-banks 知识域

> **用途:** 供 `career-assessment-prep` skill 调用,提供中国校招四大测评系统的题型拆解与策略。
> **更新方式:** 题型结构稳定;题库示例随校招季更新。
> **消费 skill:** `skills/career-assessment-prep/`

## 资料来源

| 来源 | 类型 | 用途 |
|------|------|------|
| 北森/智鼎/SHL/赛码 官方说明 | 一手 | 题型结构 |
| CSDN/知乎/B站 拆解文章 | 社区 | 解题策略 |
| 牛客网 笔试经 | 社区 | 真题回忆 |

## 文件清单

- `four-systems-comparison.md` — 四大测评系统对比(题型/限时/难度)
- `aptitude-strategies.md` — 行测五大题型解题策略
- `personality-test-guide.md` — 性格测评策略(校招重点)
- `mock-questions.md` — 各系统模拟题示例
- `../../data/personality-bank.github-ipip.json` — GitHub `jpeslar1/deep-personality-oss` 的 Big Five/IPIP 开放题库（15 题，中文翻译；IPIP 题目为 public domain）
- `../../data/NOTICE-personality-bank.md` — 上游仓库、IPIP 许可和来源追溯说明
- `../../data/question-bank.github-openquiz.json` — GitHub `prahladyeri/open-quiz-commons` 基础快照（25 题，CC BY-SA 4.0）
- `../../data/question-bank.github-openquiz-*.json` — 按当前 JD 轨道扩展的 Python 工程、测试质量、数据库/数据分析、系统/网络、服务端 API、AI/JavaScript、CI/CD/容器、嵌入式系统基础/IaC、异步/FFI/边缘运维快照（678 题；加 25 题基础快照）
- `../../data/NOTICE-question-bank.github-openquiz.md`、`../../data/NOTICE-question-bank.github-openquiz-expanded.md` — Open Quiz Commons 署名、同许可和来源追溯说明
- `assessment-intelligence.md` — 企业官方流程与社区面经题型信号（带年份、证据等级和版权边界）
- `../../data/assessment-intelligence.json` — 可供 CLI 查询的结构化测评情报
- `mock-questions.md`、`../../data/assessment-bank.example.json` 与 `../../data/assessment-bank.project.json` — Career OS 本项目既有题库，继续作为通用题库来源

## 当前可用边界（2026-09-02）

| JD 轨道 | 已达到可训练规模的部分 | 当前状态 | 仍未覆盖的专向维度 |
|---|---|---|---|
| 软件测试 / 运维 / SRE | Python 测试、覆盖率、静态检查、系统自动化、网络、容器、CI/CD、可观测性（按标签计 580 题） | 基础训练可用 | Linux 命令/权限/进程专项、真实故障场景 SJT |
| 数据分析 | SQL、事务/迁移、ORM、pandas、统计、可视化、Jupyter（252 题） | 基础训练可用 | 业务案例、指标推导、资料分析整套题 |
| AI 应用 / RAG / Agent | Python/API、机器学习、神经网络、数据库、异步与服务端基础（471 题） | 工程基础可用 | chunking、向量库、rerank、Agent 状态/工具、Prompt 注入与 RAG 评测 |
| 技术支持 / FAE | Python/网络/API/系统基础（325 题） | 基础训练可用 | C/C++、硬件接口、现场排障和客户冲突情景 |
| 物联网 / 嵌入式 | Rust 嵌入式系统、并发、FFI 与工具链基础（133 题） | 系统基础可用 | C/C++、RTOS、UART/CAN/MQTT/BLE、硬件调试 |

这里的“可用”表示题目能通过统一适配器导入、按 JD 标签组卷并留下答题记录，不表示覆盖任何企业的专有正式题库或录用标准。

## skill 调用提示

- skill 启动时读取本目录
- `four-systems-comparison.md` 是诊断模块的依据
- 模拟题从 `mock-questions.md` 抽取
- 职业性格模拟使用 `python bin/career_jobs_cli.py personality [job_id]`；题库来源为 GitHub/IPIP，不使用原创题
- 技术客观题已并入通用 `exam` 题池；题目来源可通过 `stats` 和 `mock_questions.source_plugin` 追溯
- `mock-questions.md` 的 Q6 是本项目已有的“最符合/最不符合”强迫选择示例，继续由 skill 读取；当前 CLI 性格评分器只接收 1-5 Likert 题，不会把强迫选择题伪装成量表分数
- 详细系统对比另见 `skills/career-assessment-prep/references/assessment-systems.md`
