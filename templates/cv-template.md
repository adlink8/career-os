# {{name}}

> 目标岗位：{{target_primary}}
> 目标城市：{{target_cities}}
> 期望薪资：{{salary_min}}-{{salary_max}}k

**联系方式**：手机：{{phone}} | 邮箱：{{email}} | GitHub：{{github}}

## 个人概述

- **岗位定位**：{{role_position}}
- **匹配能力**：{{jd_match_summary}}
- **工程特点**：{{evidence_based_strength}}

## 工作经历

### {{employer}} | {{role}} | {{period}}

- **职责**：{{responsibility_1}}
- **成果**：{{result_1}}

## 核心项目经历

### {{project_1_name}}

`{{tech_stack}}` | [GitHub: {{github_url}}]({{github_url}}) | {{period}}

**职务职责**：{{project_role}}

- **{{focus_label}}**：{{action_and_result}}
- **{{focus_label}}**：{{action_and_result}}

### {{project_2_name}}

`{{tech_stack}}` | [GitHub: {{github_url}}]({{github_url}}) | {{period}}

**职务职责**：{{project_role}}

- **{{focus_label}}**：{{action_and_result}}
- **{{focus_label}}**：{{action_and_result}}

## 教育背景

**{{school}}** | {{major}} | {{degree}}

## 主要技能

- **AI 应用能力**：Codex、WorkBuddy、{{ai_application_skills}}
- **{{skill_group_1}}**：{{short_skill_description}}
- **{{skill_group_2}}**：{{short_skill_description}}
- **{{skill_group_3}}**：{{short_skill_description}}
- **{{skill_group_4}}**：{{short_skill_description}}

## 模板约束

1. **统一版式**：使用 `cv-newland-photo-edition` 双栏样式；A4（210×297mm），左栏 65mm，照片 44×58mm，字体、颜色、内边距和行距由 `config/resume-style-photo.json` 统一控制。
2. **左栏结构**：联系方式使用“手机 / 邮箱 / GitHub”独立行；基本信息使用“学历 / 专业 / 学校”标签行；主要技能使用“▪ 粗体技能名：一句短说明”。可显示单一求职意向（官网岗位全称，禁止多意向）。证书区出省级奖与软著。
3. **元数据**：目标岗位、城市和薪资只放在 `>` 元数据行，生成 PDF 时不进入可见正文。
4. **加粗规则**：个人概述、职务职责和项目要点都使用“**重点标签**：说明”；项目名称和区块标题由生成器统一加粗。
5. **JD 对齐**：固定 3 个项目；每项至少 3 点，条数按 JD。海投只改意向/技能排序，不改正文，除非方向差距过大。先定稿 MD，再生成照片双栏。
6. **AI 能力**：每份简历技能第一条必须是 AI 应用能力（Codex、Claude Code、Gemini、MCP），且每份都放。
7. **技能密度**：主要技能 4–6 组，每组一行；一律写「熟练」，不设「学习中」，无佐证不上。
8. **教育信息**：只保留常州大学、计算机科学与技术、本科。不写专升本、专科、四六级。
9. **项目证据**：每条说明按“动作 + 技术/范围 + 可验证结果”组织；没有证据的数字使用占位符或删除，不编造 Issue/PR、性能和招聘成果。
10. **竞赛**：必须出现江苏省物联网技能大赛省级获奖；软著 ×2。
11. **数字口径与反 AI 感**：每页可见数字 ≤5 个，取整书写（如 600+、90+）；只保留可公开验证且本人能讲出来源的数字，删除高精度统计数字（如“4,148 个测试函数”）；每条项目要点至少含一个专属细节（具体决策/踩坑/调优记录），避免“负责开发/优化性能/提升效率”类可被原样抄走的句式。

## 生成与验收

```powershell
python scripts/generate-photo-style-cvs.py
python scripts/sync_resume_registry.py --json
```

验收条件：先有定稿 MD，再出 `data/cv/final/photo-style/` PDF；A4 单页；左栏结构和 Newland 样式一致；可见单一求职意向；技能第一条为 AI 且用「熟练」；有省奖；不出现多意向、「学习中」、专科、专升本。
