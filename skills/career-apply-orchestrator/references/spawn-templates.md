# 子 Agent spawn 模板

主会话把 `{pack_path}` 换成 `next` 返回的路径。不要附加任何其它文件或聊天摘要。

## decompose

```
你只做 JD 拆解。只读这一个文件，禁止打开仓库其它文件：
{pack_path}

输出一份 JSON（不要 Markdown 包裹以外的解释），字段：
role=decompose, one_liner, hard_gates[{item,pass}], must_keywords, bonus_keywords,
abandon(bool), abandon_reason
硬门槛核心栈全空则 abandon=true。不要写简历、不要打分。
```

## map

```
你只做 JD 条款 × 证据对照。只读：
{pack_path}

输出 JSON：role=map, clauses[{jd, evidence, status}]
status 只能是 corroborated / missing / skip。不要改简历、不要打 ATS 分。
```

## gap-triage

先加载 `skills/career-jd-gap-branch/SKILL.md`，然后只读：

```
{pack_path}
```

输出 JSON 到 artifacts/gap-triage.json：
`role=gap-triage, items[{term, decision, host, branch, reason}]`
decision 只能是 rewrite / branch / skip。
pack 里的 suggested 可作初值，但必须按立项三门槛复核。不要写简历。

## optimize

```
你只改这一岗的简历正文。只读：
{pack_path}

规则：关键词必须落在项目正文（动作+指标）；禁止只堆技能栏；bounce_facts 是事实不是话术。
求职意向必须等于 pack.title（官网 JD 全称）。
若 pack.open_prompts 非空，为每条写 open_answers[{key,label,value}]，不要把开放题糊进自我评价栏。
输出 JSON：role=optimize, resume_md（完整 Markdown 简历）, resume_path（若已有 PDF 则填路径否则空串）, open_answers。
不要自评 ATS，不要扮演 HR/面试官。
```

## campus-hr

先加载 `skills/career-multi-agent-eval/references/campus-hr-prompt.md`，然后：

```
只读 {pack_path}。按该 prompt 的 JSON 契约输出。
禁止讨论技术实现细节，禁止读取其它 pack。
```

## tech-lead

先加载 `skills/career-multi-agent-eval/references/tech-lead-prompt.md`，然后：

```
只读 {pack_path}。按该 prompt 的 JSON 契约输出。
禁止读取 HR pack 或优化理由。
```

## ats-scanner

先加载 `skills/career-multi-agent-eval/references/ats-scanner-prompt.md`，然后：

```
只读 {pack_path}。matcher 字段已是 ats_matcher.py 的结果。
核对其可提取性与意向单一性，输出该 prompt 的 JSON。
不要另打一套五维总分来覆盖 matcher。
```
