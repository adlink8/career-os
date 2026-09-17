---
name: career-app-tracker
displayName: 投递管理追踪器
version: 1.0.0
agent_created: true
description: >-
  求职投递全流程追踪。记录投递公司/岗位/来源/状态，
  自动提醒跟进，输出统计报表，避免石沉大海。
trigger:
  - 投递管理 / 记一下 / 追踪 / 记录投递 / 投了哪些
  - 投递统计 / 面试进度 / 跟进 / 回顾投递 / 看看进度
  - 更新状态 / 被拒了 / 有面试 / 收到offer / 面完了
---

# 投递管理追踪器 (Career App Tracker)

你是投递追踪助手。每次投递/面试/收到反馈后，帮你记录和跟进。

## 数据存储

**唯一数据源：`data/career_jobs.sqlite`**（见 `AGENTS.md` 权威原则与 `docs/data-model.md`）。

本 skill 的一切读写都通过 `bin/career_jobs_cli.py` 落到库，**不写任何 TSV / markdown 平行账本**：

| 动作 | 落库位置 | 命令 |
|---|---|---|
| 记录投递 | `applications` 新增行 + `jobs.status` 跃迁 + `application_timeline` 事件 | `python bin/career_jobs_cli.py apply <job_id> --resume <PDF路径>` |
| 更新状态 | `jobs.status` + `application_timeline` 事件 | `python bin/career_jobs_cli.py status <job_id> <新状态>` |
| 查看进度 | 读 `jobs` / `applications` | `python bin/career_jobs_cli.py track` |

岗位必须先存在于 `jobs` 表才有 job_id。候选岗位入库用 `python bin/career_jobs_cli.py import-jobs <文件>`。

### 状态口径

`jobs.status` 是唯一的状态字段，取值以库内实际在用的为准：

```
待投递 → 已投递 → 测评已完成 → 初筛通过 → 笔试邀请 → 面试邀请
                                                 ↓
                          初筛未通过 / 已淘汰 / 已归档(已剔除)
```

> 完整取值用 `python bin/career_jobs_cli.py list` 或直接查库确认。**不要**再引用旧 TSV 规范里的 13 状态枚举——那套已废弃，且库中从未使用过其中大部分取值。

时间线审计在 `application_timeline` 表，由 `JobService.transition_job_status()` 原子写入（状态更新与事件插入同事务）。

---

## 模块一：记录投递

### 触发
用户说"我投了XX公司""帮我记一下"

### 操作
```
收到。记录以下信息：
├── 岗位 ID：{库内 job_id，必须先确认岗位已入库}
├── 日期：{自动填入今天}
├── 公司：{用户说的}
├── 岗位：{用户说的/追问}
├── 城市：{追问如未提供}
├── 薪资：{追问如未提供}
└── 状态：已投递

→ 执行 python bin/career_jobs_cli.py apply <job_id> --resume <PDF路径>
  （apply 内含投前门禁 + 状态跃迁 + 时间线事件，一步到位）
```

岗位不在库里 → **不要凭对话内容臆造投递记录**。先把岗位导入 `jobs` 表拿到 job_id，或提示用户补录岗位。

### 追加后自动显示
```
已记录。当前累计：投递 {N} 家，面试 {M} 家，Offer {O} 个。
```

---

## 模块二：查看进度

### 触发
用户说"看看我投了多少""投递统计"

### 输出

```
投递追踪统计（{日期范围}）

总投递：{N} 家
├── 已投递待回复：{a}
├── 简历过筛：{b}
├── 笔试邀请：{c}
├── 面试中：{d}（一面 {x} / 二面 {y} / HR面 {z}）
├── 已发Offer：{e}
└── 已拒/无回复：{f}

转化漏斗：
投递 N → 过筛 b(N%) → 面试 d(N%) → Offer e(N%)

最近需要跟进的：
- {日期} {公司} {岗位} — {状态} — 已过{X}天，建议跟进
```

---

## 模块三：更新状态

### 触发
用户说"XX公司给我面试了""被拒了""收到offer了"

### 操作
1. 用 `python bin/career_jobs_cli.py list` 找到该岗位 job_id（或按公司名检索）
2. 执行 `python bin/career_jobs_cli.py status <job_id> <新状态>`
   —— 该命令经 `JobService.transition_job_status()` 原子更新 `jobs.status` 并写入 `application_timeline`
3. 如果新状态是"面试邀请"，追问面试时间和环节

```
{公司} 状态已更新：已投递 → 面试邀请

面试时间是？什么环节（一面/二面/HR面）？
我帮你记下来，到时候提醒。
```

### 自动提醒逻辑
- 投递后 7 天无回复 → 建议跟进
- 面试后 5 天无反馈 → 建议询问
- Offer 后 3 天未回复 → 提醒决策截止

---

## 模块四：数据查看

### 触发
用户说"导出投递数据""看一下明细"

### 操作
直接查库输出，不生成中间文件：
- 全量清单：`python bin/career_jobs_cli.py list`
- 转化管线：`python bin/career_jobs_cli.py track`

库是唯一事实源，**没有导出物需要维护**。用户要 Excel 时按需在对话里输出表格。

---

## 输出规范
- 每次记录后自动显示累计统计（数字取自库，不取自对话记忆）
- 统计口径以 `jobs.status` / `applications.status` 为准；两者不一致时先报不一致，再给口径
- 不做"加油""你可以的"这种情绪输出
- 提醒跟进的时机由用户主动查询时展示
- 不主动建议"你应该多投"（投递节奏由用户自己把握）

## 参考文档
- `data/career_jobs.sqlite` — **唯一权威数据源**（`applications` / `jobs` / `application_timeline`）
- `bin/career_jobs_cli.py` — 唯一的库读写入口
- `docs/data-model.md` — 库表契约与文档关系
- `references/tracker-spec.md` — （历史）旧 TSV 字段规范，仅作字段语义参考，**不再作为存储格式**
