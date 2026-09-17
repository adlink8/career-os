# 投递数据规范（库版）

> **状态：2026-09-17 起，投递数据的唯一存储是 `data/career_jobs.sqlite`。**
> 本文原先描述的 `tracker.tsv` 已废弃——它是与库并行的手工账本，无任何写入方，已实测漂移（浩鲸交付岗库内"测评已完成"、TSV 仍"已投递"）。
> 本文保留字段语义，但**存储载体一律改为库表**。

## 字段语义 → 库表映射

| 序号 | 原 TSV 字段 | 库内落点 | 说明 |
|------|------------|---------|------|
| 1 | 日期 | `applications.submitted_at` | 投递日期 |
| 2 | 公司名称 | `jobs.company_name` | 企业全称 |
| 3 | 目标岗位 | `jobs.job_title` | 岗位名 |
| 4 | 目标城市 | `jobs.city` | 工作地 |
| 5 | 薪资范围 | `jobs.salary_text` | 薪资文本 |
| 6 | 企业官网 | `companies` / 岗位来源字段 | 企业主页 |
| 7 | 校招网申直达链接 | `jobs.application_url` | 申请入口 |
| 8 | 当前状态 | `jobs.status` + `applications.status` | 见下方枚举 |
| 9 | 战略定位与项目匹配备注 | `applications.notes` / `jobs.matching_analysis` | 匹配证据 |

## 状态枚举（以库内实际在用为准）

```
待投递              尚未提交申请（jobs.status）
已投递              投递后初始状态
测评已完成          线上测评做完（如浩鲸科技交付工程师岗）
初筛通过            HR 通知简历通过
笔试邀请            收到笔试通知
面试邀请            收到面试通知
Offer               收到录用通知
已接 / 已拒         接受或拒绝 Offer

终止态：
初筛未通过          简历被刷
已淘汰/限2026届     不符合资格被排除（如涂鸦智能实习岗）
已归档(已剔除)      人工剔除出候选池，非投递
已归档/历史         历史归档
```

> 旧 TSV 规范里的「简历过筛 / 一面 / 二面 / HR面 / 无回复 / 被拒」在本库中**从未使用过**，已删除，不得再引用。
> 面试轮次信息记在 `application_timeline` 事件里，不占 `status` 字段。

## 读写入口

**唯一入口：`bin/career_jobs_cli.py`**

```bash
python bin/career_jobs_cli.py list                          # 全量岗位清单
python bin/career_jobs_cli.py track                         # 转化管线看板
python bin/career_jobs_cli.py detail <job_id>               # 岗位详情
python bin/career_jobs_cli.py apply <job_id> --resume <PDF> # 记录投递（含投前门禁）
python bin/career_jobs_cli.py status <job_id> <新状态>       # 更新状态
```

禁止：手工编辑任何 TSV/markdown 形式的投递账本。库是唯一事实源（见 `AGENTS.md` 与 `docs/data-model.md`）。
