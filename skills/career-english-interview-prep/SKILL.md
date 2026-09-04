---
name: career-english-interview-prep
displayName: 英文面试准备
version: 1.0.0
agent_created: true
description: >-
  面向外企、国际化团队和英文技术支持岗位，训练英文自我介绍、项目讲解、
  STAR 行为面试与技术追问，并保持内容来自真实 profile 和项目证据。
trigger:
  - 英文面试 / English interview / 外企面试 / 英文自我介绍
  - 英文项目介绍 / 英文简历 / 日企面试 / 技术支持英文
---

# 英文面试准备 (English Interview Prep)

## 必须读取

1. `config/profile.yml` — 真实教育、技能和项目
2. `data/lessons-learned.md` — 已暴露的回答缺口
3. `references/english-interview-playbook.md` — 话术结构与评分标准

## 工作流

1. 先确认岗位语言场景（自我介绍、项目深挖、行为面或技术支持）。
2. 用真实项目生成 60 秒和 120 秒两个版本；不添加 profile 中不存在的指标。
3. 逐题练习，分别点评 technical accuracy、clarity、evidence、follow-up。
4. 将新缺口写成 lessons-learned 草稿，等待用户确认后再落盘。

## 输出规范

```text
English interview drill — {company/role}
Question: {英文问题}
Suggested structure: {结论 → evidence → trade-off → result}
Candidate answer: {用户回答}
Feedback: {准确性/清晰度/证据/追问，各 1-5}
Next drill: {下一道题或改写任务}
```

## 参考文档

- `references/english-interview-playbook.md` — 英文回答和复盘规范
