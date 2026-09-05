---
name: career-daily-driver
displayName: 每日求职作战台
version: 1.0.0
agent_created: true
description: >-
  将当前状态、个人画像和投递记录转换为今日可执行的求职行动清单，
  区分候选岗位与真实投递，避免把规划当成结果。
trigger:
  - 今日求职做什么 / 每日求职计划 / 今天投什么 / 求职作战台
  - 看看当前进度 / 下一步怎么安排 / 秋招日程
  - 今天该做点什么 / 安排一下今天 / 今天干点啥
---

# 每日求职作战台 (Career Daily Driver)

## 路径基准
- `data/`、`config/` 相对**项目根目录**(career-os/)
- `references/` 相对**本 SKILL.md 所在目录**

## 必须读取

1. `data/current-status.md` — 跨会话状态和阻塞项
2. `data/tracker.tsv` — canonical-v2 岗位与当前状态
3. `config/profile.yml` — 目标岗位、城市、时间约束
4. `references/daily-driver-spec.md` — 行动排序与输出契约

## 工作流

1. 以今天日期为准，先识别已投递/面试/Offer，再识别待投递候选。
2. 对每个行动给出证据来源、预计耗时和完成定义。
3. 每日最多输出 3 个主行动 + 1 个复盘行动；没有真实投递时明确显示“转化仍为 0”。
4. 不自动提交申请、不把搜索结果改写成已投递。

## 输出规范

```text
今日求职作战台（YYYY-MM-DD）
状态边界：真实投递 N 家；候选岗位 M 条

P0 主行动
1. {动作} — 证据：{文件/岗位} — 预计耗时：{X 分钟} — 完成定义：{可检查结果}
P1 主行动
2. ...
P2 主行动
3. ...
复盘：{今天记录什么}
阻塞：{需要用户确认的事项}
```

## 参考文档

- `references/daily-driver-spec.md` — 排序和统计规则
