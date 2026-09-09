# 上下文包契约

每个子 Agent 只读 `data/job_discovery/runs/<run_id>/packs/` 下的一个 JSON。主会话禁止把包内容复述进其它角色的 prompt。

## 允许字段

### decompose

`pack_role, run_id, iteration, title, company, jd_text, hard_filters`

禁止：证据库、旧简历、分数、bounce。

### map

`pack_role, run_id, iteration, breakdown, evidence_index`

`evidence_index` 来自 `resume_evidence_*`：项目名、定位、bullet 文本与证据档。禁止 ATS/会审。

### optimize

`pack_role, run_id, iteration, company, title, breakdown, identity, clause_map, current_resume, bounce_facts, open_prompts`

`bounce_facts` 仅含：

```json
{
  "iteration": 2,
  "ats": { "score": 62, "verdict": "FAIL", "missing": ["Kubernetes"], "knockout": [] },
  "review": { "verdict": "WARN", "must_fix": ["first_project_misaligned"] }
}
```

禁止：`hr_impressions`、会审原文、面试口径。

### campus-hr（review-hr.json）

`pack_role, run_id, company, title, jd_text, resume_text`

禁止：matcher missing 词表、bounce、Tech 评分。

### tech-lead（review-tech.json）

`pack_role, run_id, title, jd_text, resume_text`

禁止：HR 印象、优化理由。

### ats-scanner（review-ats.json）

`pack_role, run_id, matcher, jd_text, resume_text`

`matcher` 是 `ats_matcher` 的 JSON。禁止另两方评分。ats-scanner **不得重算五维总分**；加权时 CLI 仍用 matcher 分。

## 校验

`write_pack` 会拒绝会审包出现 `bounce_facts / clause_map / breakdown / evidence_index / hr_impressions / optimize_notes / interview_script`。
