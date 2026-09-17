# 简历 Markdown 统一规格

内容红线见 `docs/resume-authority.md` 与 `resume_generation_rules`。本文件只约定 **MD 区块如何被照片双栏生成器读入**。

现用输入只有三份母版：`data/cv/cv-ops.md`、`cv-iot.md`、`cv-semi.md`。投递时先改意向再生成 PDF。

## 固定区块

| Markdown 区块 | PDF 位置 | 必填 |
|---|---|---|
| `# 姓名` | 左栏顶部 | 是 |
| `> 求职意向：官网全称 \| 2027届统招本科` | 左栏意向（单一，禁止兼岗） | 是 |
| `**联系方式**：` | 左栏 | 是 |
| `## 个人概述` | 右栏 | 是 |
| `## 核心项目经历` | 右栏 | 是，恰好 3 个 `###` 项目，每项至少 3 点，STAR |
| `## 教育背景` | 左栏 | 是：常州大学 \| 计算机科学与技术 \| 本科 \| 2027年6月毕业 |
| `## 主要技能` | 左栏 | 是：第一条 AI，一律「熟练」 |
| `## 证书与竞赛` | 左栏或右栏末 | 是：省奖 + 软著 |

省赛只写在证书与竞赛，不进项目经历。

## 生成

```powershell
python scripts/generate-photo-style-cvs.py
python scripts/sync_resume_registry.py --json
```

验收：A4 单页；可见单一求职意向；技能第一条为 AI 且用「熟练」；有省奖；无多意向、无专升本、无「学习中」。
