# 简历 Markdown 统一规格

本规格是 `cv-newland-photo-edition` 风格 PDF 的内容源约定。岗位版本可以有多份，但区块顺序、字段语法、加粗规则和渲染映射保持一致。

## 固定区块

| Markdown 区块 | PDF 位置 | 必填 | 说明 |
|---|---|---:|---|
| `# 姓名` | 左栏顶部 | 是 | 只出现一次 |
| `**联系方式**：...` | 左栏 | 是 | 使用手机、邮箱、GitHub 三个独立字段 |
| `## 个人概述` | 右栏首块 | 是 | 2–4 条 JD 对齐的“粗体标签 + 说明” |
| `## 工作经历` | 右栏 | 否 | 无正式经历时省略 |
| `## 核心项目经历` | 右栏 | 是 | 每个项目用 `###`，按 JD 选择 |
| `## 教育背景` | 左栏基本信息 | 是 | 学校、专业、学历；不写毕业时间 |
| `## 主要技能` | 左栏 | 是 | 4–6 组短说明，必须含 AI 应用能力 |

不默认使用“学习中”和“证书与竞赛”区块；空区块不渲染。

## 顶部元数据

目标岗位、城市和薪资只作为 Markdown 元数据，不进入 PDF 可见区：

```markdown
> 目标岗位：开源技术研发工程师
> 目标城市：苏州
> 期望薪资：5-7k
```

生成器不会显示左上求职意向。

## 左栏字段

```markdown
**联系方式**：手机：{{phone}} | 邮箱：{{email}} | GitHub：{{github}}
```

教育信息使用以下形式，生成 PDF 后显示为“学历 / 专业 / 学校”标签行：

```markdown
## 教育背景

**{{school}}** | {{major}} | {{degree}}
```

不得写毕业时间、“在读”、专科院校或“专升本”等历史教育表述。

## 概述和项目条目

个人概述、职务职责和项目要点都使用粗体标签：

```markdown
## 个人概述

- **岗位定位**：围绕目标 JD 写一句匹配说明。
- **核心能力**：只写有项目证据支持的技术能力。

### 项目名称

`Python / SQLite / Docker` | [GitHub: adlink8/example](https://github.com/adlink8/example) | 2026/06 - 至今
**职务职责**：负责架构、实现和验证。

- **动作/结果**：说明做了什么、使用什么技术、产生什么可验证结果。
```

项目名称、区块标题、`职务职责` 和重点标签由生成器统一加粗。每条说明按“动作 + 技术/范围 + 可验证结果”组织。

思必驰 Agent、开源研发、研发效能三版默认只保留 PKS 与 NovelMind；其他岗位根据 JD 重新选择项目，不复制统一话术。

## 主要技能

```markdown
## 主要技能

- **AI 应用能力**：Codex、WorkBuddy、{{ai_application_skills}}
- **{{skill_group_1}}**：{{short_skill_description}}
- **{{skill_group_2}}**：{{short_skill_description}}
- **{{skill_group_3}}**：{{short_skill_description}}
- **{{skill_group_4}}**：{{short_skill_description}}
```

每份简历必须出现 Codex、WorkBuddy；其余技能随 JD 变化。技能只保留 4–6 组，每组一行，不展开工具教程，不把未验证能力写成“精通”。

## 禁止项

- 不新增“个人优势”“个人定位”“岗位匹配摘要”等平行区块，统一并入“个人概述”。
- 不使用无法映射到 PDF 的表格、文本框或图片化正文。
- 不编造 Issue/PR、性能、覆盖率、招聘人数等量化成果。
- 不在目标岗位版本中恢复已删除的学习中、证书竞赛、毕业时间或历史学历信息。

## 版式与验收

```powershell
python scripts/generate-photo-style-cvs.py
python scripts/sync_resume_registry.py --json
```

版式基准由 `config/resume-style-photo.json` 控制：A4（210×297mm）、左栏 65mm、照片 44×58mm，统一字体、颜色、内边距和行距。验收要求：PDF 单页；左栏结构与 Newland 样式一致；个人概述、职务职责和项目重点标签在 HTML 中使用 `<b>`；HTML/PDF 不出现“求职意向”“学习中”“证书与竞赛”“毕业”“在读”“专科”“专升本”。
