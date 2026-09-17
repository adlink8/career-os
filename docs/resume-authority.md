# 简历权威地图

求职数据以 `data/career_jobs.sqlite` 为准。简历**写法红线**以表 `resume_generation_rules` 为准（种子在 `bin/career_os_store.py`）。其它 md/skill/脚本只引用，不得另立口径。

## 权威分层

| 事项 | 权威 | 不是权威 |
|---|---|---|
| 写法红线（意向、3 项目、STAR、AI 首位、熟练、省奖、量化、海投不改正文等） | `resume_generation_rules` | knowledge/、各 Skill 里的复述 |
| 现用母版 | `data/cv/cv-ops.md` 运维交付；`cv-iot.md` 现场支持；`cv-semi.md` 半导体方案与销售 | `cv-network.md`、`cv-compact.md`、`cv-ai-infra.md`、`*-v2-draft.md`、各公司细支稿 |
| 目标城市 | `config/profile.yml` `career_target.cities`（江苏优先、上海其次、无深圳） | 意向行、旧文档里的城市列表 |
| 海投选哪份母版 | `VOLUME_TRACKS`（`bin/services/apply_run.py`） | `career-general-recruit` 旧对照表 |
| 出 PDF | 先定稿上述 MD，再 `python scripts/generate-photo-style-cvs.py` | `generate-cv-layouts.py`、`generate-cv-final.py`（历史 Word 线，不再用于新稿） |
| 身份事实（含专升本） | `config/profile.yml` | 简历正文。档案可留专升本，简历不印 |
| 已投文件 | `applications` + `resume_artifacts`（submitted PDF） | 母版后续改动不回写已投快照 |
| 投岗门禁（CET-4、JD 过细） | `bin/services/job_ingest_gate.py` | 简历红线（两套门，不要混用） |

## 历史稿

`cv-network.md`、`cv-compact.md`、`cv-ai-infra.md`、`cv-*-v2-draft.md` 以及各公司定制 md **留文件、当历史稿，不再当母版、不再作为照片生成默认输入**。已投 PDF 不动。

## 面试 vs 写简历

- 写简历：STAR + 库表红线。
- `knowledge/resume-templates/star-method.md`：STAR 操作说明，服从库表。
- `skills/career-general-recruit/references/hook-writing.md`：只用于面试追问设计，不决定简历要点条数。
