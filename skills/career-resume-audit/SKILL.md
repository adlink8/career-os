---
name: career-resume-audit
displayName: 简历自我审计(证据优先)
version: 1.1.0
agent_created: true
description: >-
  用证据优先方法审计自己的简历:拆原子主张、内部一致性检查、
  对照仓库证据定五档状态、排查包装夸大模式、检查 AI 生成感与数字口径。
  投递前防面试官拷打。
  方法论改编自 Claycui828/ASu-resume-skills(MIT,见 references 头部声明)。
trigger:
  - 简历审计 / 简历自查 / 审计我的简历
  - 这个写法会不会被问穿 / 经得起拷打吗 / 防追问
  - 简历夸大检查 / 包装过度 / 证据状态
  - 简历有 AI 味 / 反AI感 / 数字口径 / 数字太假
---

# 简历自我审计(证据优先)

把**自己的**简历当作面试官会逐条核验的主张清单。目标:投递前发现"会被问穿"的写法,改成证据能撑住的口径。与项目"先验证再宣称、不包装"的约束同构。

## 启动时读取

- 待审简历:`data/cv/cv-*.md` 或用户指定的 docx/PDF 文本
- 证据基线:`data/cv/cv-material.md`(仓库取证版素材)、`config/profile.yml`
- 参考:`references/evidence-status.md`、`references/inflation-patterns.md`、`references/ai-flavor-patterns.md`

## 工作流

### 1. 拆原子主张

不把整段经历当一条主张。角色、范围、结果、因果**分开**核验。

> 例:"主导 RAG 平台建设,召回提升 30%" → 拆成:① 主导角色成立?② 平台存在且可展示?③ 召回率口径与基线?④ 提升归因于本人?

### 2. 内部一致性检查(不依赖外部证据,先做)

- 重算所有百分比/倍数的分子分母
- 日期对账:项目时间 vs 在校时间 vs 实习时间有无冲突
- 检查无比较集的最高级:"最强/第一/核心"——和谁比?
- 区分项目整体指标与个人贡献指标
- learning 中技能是否被写成了熟练(profile.yml 三级对照)
- 求职意向单一性与 JD 绝对对齐: 严禁复合意向(如"AI应用与交付工程师"或带"/"、"与"、"及")。求职意向必须单一且 100% 对齐目标 JD 岗位全称,否则直接判定为必改高风险项(防 ATS 秒刷与 HR 海投标签)

### 3. 对照证据定五档状态

每条主张对照 cv-material.md 与 profile.yml 定一档(定义见 references/evidence-status.md):

| 状态 | 含义 | 处置 |
|------|------|------|
| corroborated | 有仓库/公开证据支撑 | 保留 |
| partially_corroborated | 事实存在但角色/幅度超证据 | 收窄口径 |
| unsupported | 无证据但可能为真 | 补证据或删 |
| contradicted | 与证据冲突 | 必须改 |
| unverifiable | 只有口头能讲 | 降级为面试口述,不占简历版面 |

### 4. 包装模式自查

逐条过 references/inflation-patterns.md 的清单(贡献升级、团队成果归个人、分母切换、最高级无比较集、跨平台自授 title 等)。

### 5. AI 生成感与数字口径检查

逐条过 references/ai-flavor-patterns.md 的清单(HR 识别 AI 简历三特征、数字口径、逐句"能否被抄走"自查、AI 应用能力明牌原则):

- 数字口径:每页 ≤5 个、取整、可公开验证且本人能讲出来源;高精度统计数字(如"4,148 个测试函数")标记为必改
- 每条 bullet 至少一个"只有做过才知道"的具体名词;纯"负责/优化/提升"句标记为模板化
- 概述-项目-技能是否一条主线,板块间有无拼凑感

### 6. 输出

```text
## 简历审计报告:{文件名}

### 高风险(必改)
| 原文 | 状态 | 证据缺口 | 建议改写 |

### 中风险(建议改)
...

### 证据充足(可放心被拷打)
...

### 总体:可投递 / 改后投递
```

## 输出规范

- 每条结论给出原文引用 + 状态 + 一句证据说明,不给"感觉有问题"
- 改写建议遵守 `knowledge/resume-templates/owner-scope-writing.md` 的角色强度分级
- 不编造新证据:缺口就标缺口,由用户决定补证据还是删条目
- 审计结果可写入 `data/cv/audit-{文件名}.md`(本地,已 gitignore)

## 与其他 skill 的边界

| Skill | 关系 |
|-------|------|
| `career-general-recruit` | 生成简历;本 skill 审其产出 |
| `career-personal-data-update` | 提供证据基线(数据仓库取证) |
| `career-interview-master` | 审计发现的 unsupported 项 = 面试备战重点 |

## 来源声明

方法论改编自 [Claycui828/ASu-resume-skills](https://github.com/Claycui828/ASu-resume-skills) 的 asu-resume-audit-skill(证据优先审计),剥离其"调查他人"场景,保留自我审计内核。原仓库 License 见其 THIRD_PARTY_LICENSES。
