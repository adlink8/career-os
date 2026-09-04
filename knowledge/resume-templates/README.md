# resume-templates 知识域

> **用途:** 供简历定制(步骤 7,skill `general-recruit` 待建)调用,提供 STAR 法则和 ATS 优化方法。
> **更新方式:** 方法论稳定;ATS 算法变化时更新。
> **消费 skill:** `skills/general-recruit/`(未创建)

## 资料来源(GitHub 高星)

| 仓库 | 星数 | 用途 |
|------|------|------|
| [WonderCV-com/resume-templates](https://github.com/WonderCV-com/resume-templates) | 高 | 135+ 中文 ATS 友好模板 |
| [dyweb/awesome-resume-for-chinese](https://github.com/dyweb/awesome-resume-for-chinese) | 高 | 适合中文的简历模板集合 |
| [WonderCV-com/resume-guide](https://github.com/WonderCV-com/resume-guide) | 高 | 中文求职知识库(ATS + STAR) |
| [ATQQ/resume](https://github.com/ATQQ/resume) | 中 | 简历在线生成器 |

## 文件清单

- `star-method.md` — STAR 法则应用指南
- `ats-optimization.md` — ATS 关键词优化策略
- `layout-schemes.md` — 4 套排版方案(ATS 版/技术标签版/紧凑版/面谈版)
- `owner-scope-writing.md` — Owner 化写作:角色强度分级与来源映射(改编自 ASu-resume-skills)

## skill 调用提示

- 简历定制时读取本目录 + `templates/cv-template.md`(占位符模板)+ `config/profile.yml`(真实数据)
- 输出落到 `data/cv/cv-{role}.md`(已 gitignore)
- JD 关键词命中参考 `knowledge/jd-templates/`
