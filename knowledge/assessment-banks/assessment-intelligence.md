# 企业与社区测评情报

> 目的：把“这家公司/岗位实际会不会测、通常测什么”变成可追溯的准备线索。
>
> 边界：企业官网能确认流程和题型家族，但通常不会公开正式题库；社区面经是个人在某年度、某岗位的回忆，必须保留年份和“reported”状态。这里不复制企业专有原题、不把历史帖子当成当季保证。

## 证据分级

| 等级 | 含义 | 允许的用法 |
|---|---|---|
| `confirmed` | 企业/平台官方公开说明 | 可作为当前准备入口；仍以实际邮件为准 |
| `reported` | 牛客等社区个人经验或汇总 | 只作为历史题型信号，不能推断当前必考 |
| `unverified` | 转载、无原始链接或无法确认年份 | 不进入默认训练池 |

## 已核实的企业流程与题型家族

| 企业/项目 | 地区/年份 | 官方确认的形式 | 训练重点 | 证据 |
|---|---|---|---|---|
| 字节跳动 | 中国大陆/2026 | 岗位相关在线笔试，非所有职位必有 | 岗位基础、编程/专业题 | [校招 FAQ](https://jobs.bytedance.com/campus/page-6272Gc) |
| 华为 | 中国大陆/2026 | 研发上机考试、综合测评；部分非研发岗含考试/语言测评 | 编程、综合能力、语言 | [校招 FAQ](https://career.huawei.com/reccampportal/next/mini/faq_h5.html) |
| 阿里巴巴 | 校招/2025 页面 | 可能有在线测评和在线笔试，官方举例编程题 | 编程、岗位相关测评 | [招聘流程](https://talent-holding.alibaba.com/campus/notice?lang=zh&tab=delivery)；[开放平台笔试能力说明](https://jaq-doc.alibaba.com/docs/api.htm?apiId=48674) |
| 宝洁 P&G | 全球/2026 | Peak Performance、Interactive、岗位相关 Virtual Job Preview | 工作态度/经历、认知、情景与工作方式 | [招聘流程](https://www.pgcareers.com/global/en/hiring-process)；[测评概览](https://www.pgcareers.com/global/en/assesment-overviews) |
| 联合利华 | 台湾 Graduate Trainee 2026 | blended assessment + digital interview | 性格、动机、数字推理、言语推理 | [项目流程](https://careers.unilever.com/en/taiwan-graduate-trainee-program-2026/) |
| 联合利华 | 英国/爱尔兰工业实习 | IP simulation、数字/言语推理、数字面试 | 情景判断、数字、言语 | [项目流程](https://careers.unilever.com/en/uk-and-ireland-early-careers-industrial-placements) |

## 社区实际遇到的题型信号

| 企业 | 帖子年份 | 社区报告题型 | 可信度边界 |
|---|---:|---|---|
| 宝洁 | 2021 | 性格、计算速度、管道/流程视觉题、圆点/图形视觉题 | 个人经验；只作历史训练线索 |
| 宝洁/联合利华 | 2020 | 情景选择、行为判断、重要性评级、认知闯关 | 社区汇总；不复制其中企业原题 |
| 联合利华 | 2019 | 开放问答、动机与经历、视频面试 | 历史个人面经；适合训练表达结构 |

对应来源和结构化记录见 `data/assessment-intelligence.json`，可以用：

```powershell
python bin/career_jobs_cli.py assessment-intel
python bin/career_jobs_cli.py assessment-intel 宝洁
python bin/career_jobs_cli.py assessment-intel --job 42
python bin/career_jobs_cli.py assessment-intel --all-jobs
```

每次收到企业测评邮件后，优先用邮件中的岗位、地区、测评供应商和截止时间覆盖历史社区信号；答题结果仍写入本地 SQLite，不能把社区题型当成企业录用标准。

岗位级推导读取 `jobs` 表当前 JD：软件测试/运维、技术支持/FAE、物联网/嵌入式、数据分析和 AI 应用/RAG 会分别命中不同的技术、情景和表达训练轨道。推导结果是准备建议，不写回岗位真实性字段，也不取代企业邮件。
