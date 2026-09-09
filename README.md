# Career OS — 求职全流程操作系统

本地优先的中文求职工作台：把「搜岗、改简历、网申填表、笔试面试、投递记录」收成可重复的流程。

国内仓库（本页）：<https://gitee.com/li-shuoya/career-os>  
**只想填网申、不要整套系统？** 用独立插件：<https://gitee.com/li-shuoya/career-os-autofill>

---

## 先选你的用法

| 你想做什么 | 用哪个仓库 | 要不要 Python |
|---|---|---|
| 只把姓名/学校/项目填进北森、Moka | [career-os-autofill](https://gitee.com/li-shuoya/career-os-autofill) | 不要 |
| 拆 JD、定制简历、ATS 打分、会审、题库、投递台账 | **本仓库 Career OS** | 要（3.10+） |

两套可以一起用：全库负责「投不投、简历对不对」；插件负责「打开报名页把格子填上」。**插件不会自动点提交。**

---

## 隐私（请先看）

本仓库**故意不包含**真实个人材料。克隆下来之后，下列文件只在你电脑上生成，不会出现在 Gitee 上：

- 真实求职画像 `config/profile.yml`（请从 `config/profile.example.yml` 复制后自己填）
- 简历 PDF/DOCX、证件照
- 投递数据库 `data/career_jobs.sqlite`、`data/tracker.tsv`
- 网申截图、浏览器登录会话、外联电话清单

提交前会跑 `python bin/scan_privacy.py`。不要把姓名、手机、身份证、个人邮箱写进要公开的文件。

建议本仓库在 Gitee 保持 **私有**。公开给别人用时，让他们用 [填表插件仓库](https://gitee.com/li-shuoya/career-os-autofill) 即可。

---

## 填表插件（独立，可单独发给同学）

仓库：<https://gitee.com/li-shuoya/career-os-autofill>

1. 下载发行版 zip 或仓库 ZIP，解压，能看到 `manifest.json`。
2. Edge 地址栏输入 `edge://extensions`，打开「开发人员模式」。
3. 「加载解压缩的扩展」→ 选中该文件夹。
4. 设置页填写底稿（或拖入 JSON）→「一键导入并启用」。
5. 打开公司报名表，点格子旁的「填入 / 复制」，或 `Alt+Shift+F` 填整页。

插件源码也在本仓库的 `extensions/ats-autofill/`。打包给别人：

```powershell
python scripts/pack_autofill_extension.py
```

生成 `dist/career-os-autofill-*.zip`（不含个人 profile.json）。

全库里的编排器放行后，会写出本岗 `autofill.json`；关掉插件设置页开关时，才会去读这份载荷。只装插件时请保持开关打开。

---

## 全库快速开始

1. 安装 [Python 3.10+](https://www.python.org/downloads/)（安装时勾选 Add to PATH）。
2. 克隆：

```powershell
git clone git@gitee.com:li-shuoya/career-os.git
cd career-os
```

3. 复制画像模板并自己填写（此文件不会被 git 提交）：

```powershell
copy config\profile.example.yml config\profile.yml
```

4. 冒烟（可选）：

```powershell
python scripts/runtime-smoke.py
```

5. 日常入口：

```powershell
python bin/career_jobs_cli.py --help
python bin/career_apply_run.py --help
```

把 JD 和报名表用插件「捕获」后，可用编排器走：拆解 → 对照 → 定制简历 → ATS → 三方会审 → 放行/海投填表。

```powershell
python bin/career_apply_run.py start --job-context <捕获的json> --mode volume
python bin/career_apply_run.py start --job-context <捕获的json> --mode precision
```

- `volume` 海投：选用现成分轨简历 + 官网岗位全称，不走会审。  
- `precision` 专投：完整 ATS + 会审，高匹配岗再用。

权威数据在本地 SQLite：`data/career_jobs.sqlite`（被 gitignore）。文档见 `docs/data-model.md`。

更完整的命令说明：[`docs/how-to-use.md`](docs/how-to-use.md)。

---

## 系统在干什么

```
Skill（操作层）     告诉 AI 按什么步骤做
Knowledge（知识层） 题库、JD 模板、面试口径
Data（数据层）      你的画像、简历版本、投递记录（仅本地）
插件 / CLI          填表、打分、组卷、模拟面试
```

求职 16 步由 `skills/` 覆盖（定位 → 调研 → 搜岗 → 简历 → 投递 → 笔试面试 → 入职）。结构是否齐全以 `.planning/STATUS.md` 为准，可运行 `pwsh scripts/audit.ps1` 复核。

| 步骤 | Skill |
|---|---|
| 自我定位 | `career-self-assessment` |
| 行业 / 学习 | `career-industry-research` / `career-learning-path` |
| 搜岗 / JD / 简历 | `career-general-recruit` |
| 公司背调 | `career-company-check` |
| 投递台账 | `career-app-tracker` |
| 笔试 | `career-assessment-prep` |
| 面试 / 谈薪 / Offer | `career-interview-master` |
| 入职 / 试用期 | `career-onboarding-prep` / `career-probation-survival` |
| 每日行动 | `career-daily-driver` |
| 单岗编排 | `career-apply-orchestrator` |

Skill 正文不绑定某一个 AI 产品，可放到 Cursor / Claude / 其他助手。

---

## 目录（精简）

```
career-os/
├── README.md                 ← 本页
├── skills/                   求职流程 Skill
├── knowledge/                题库与方法论（无个人简历）
├── config/                   profile.example.yml（真实 profile.yml 仅本地）
├── data/                     公开题库快照；sqlite/简历/投递表仅本地
├── bin/                      CLI 与编排器
├── extensions/ats-autofill/  填表插件源码（独立发行见 Gitee 插件仓）
├── plugins/                  可选外部能力（默认关闭）
├── docs/                     architecture / how-to-use / data-model
└── scripts/                  审计、冒烟、插件打包
```

---

## 和填表插件仓库怎么配合

```
本仓库 Career OS                          插件仓库 career-os-autofill
搜岗、拆 JD、改简历、ATS、会审     →     打开北森/Moka 把格子填上
本地 sqlite 记投递                         设置页底稿也可单独填，不依赖本库
```

| 链接 | 用途 |
|---|---|
| <https://gitee.com/li-shuoya/career-os> | 全流程源码（建议私有） |
| <https://gitee.com/li-shuoya/career-os-autofill> | 给别人装的填表插件（可公开） |
| <https://gitee.com/li-shuoya/career-os-autofill/releases> | 插件 zip 下载 |

---

## 许可与数据

题库快照带上游 NOTICE，使用请遵守原仓库许可证。  
你自己的简历、投递记录、账号 Cookie 不属于本仓库，请勿提交。
