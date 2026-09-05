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
2. **左栏结构**：联系方式使用“手机 / 邮箱 / GitHub”独立行；基本信息使用“学历 / 专业 / 学校”标签行；主要技能使用“▪ 粗体技能名：一句短说明”。不显示左上求职意向，不显示空的证书区域。
3. **元数据**：目标岗位、城市和薪资只放在 `>` 元数据行，生成 PDF 时不进入可见正文。
4. **加粗规则**：个人概述、职务职责和项目要点都使用“**重点标签**：说明”；项目名称和区块标题由生成器统一加粗。
5. **JD 对齐**：每个版本的个人概述、技能分组和项目要点必须围绕目标 JD 重写，不复制统一话术。思必驰 Agent、开源研发、研发效能三版默认只保留 PKS 与 NovelMind；其他岗位按 JD 选择项目。
6. **AI 能力**：每份简历的主要技能必须包含“AI 应用能力”，写明 Codex、WorkBuddy，并补充该岗位有证据支持的 AI 应用技能。
7. **技能密度**：主要技能保留 4–6 组，每组一行；不展开工具教程，不设置“学习中”分组，不把未验证技能写成“精通”。
8. **教育信息**：只保留学校、专业和学历，不写毕业时间、“在读”、专科院校或“专升本”等历史教育表述。
9. **项目证据**：每条说明按“动作 + 技术/范围 + 可验证结果”组织；没有证据的数字使用占位符或删除，不编造 Issue/PR、性能和招聘成果。
10. **可选区块**：不使用“个人优势”“个人定位”“岗位匹配摘要”平行区块；证书与竞赛默认删除，确有 JD 强相关且页面有余量时另行确认。
11. **数字口径与反 AI 感**：每页可见数字 ≤5 个，取整书写（如 600+、90+）；只保留可公开验证且本人能讲出来源的数字，删除高精度统计数字（如“4,148 个测试函数”）；每条项目要点至少含一个专属细节（具体决策/踩坑/调优记录），避免“负责开发/优化性能/提升效率”类可被原样抄走的句式。

## 生成与验收

```powershell
python scripts/generate-photo-style-cvs.py
python scripts/sync_resume_registry.py --json
```

验收条件：岗位 PDF 位于 `data/cv/final/photo-style/`；A4 单页；左栏结构和 Newland 样式一致；个人概述、职务职责和项目重点标签在 HTML 中为 `<b>`；不出现“求职意向”“学习中”“证书与竞赛”“毕业”“在读”“专科”“专升本”。
