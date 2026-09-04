# 简历登记与投递关联

Career OS 的简历原文件继续保存在 `data/cv/`，不把 PDF、DOCX 或 Markdown 的二进制内容复制进 SQLite。`data/career_jobs.sqlite` 只保存可查询的元数据和关系。

## 命名规范

规范名用于数据库的 `canonical_filename`，旧文件名保存在 `original_filename`，因此历史文件无需强制改名：

```text
cv__{role}__v{major}.{minor}__source.md
{company}__{role}__cv__v{major}.{minor}__editable.docx
{company}__{role}__cv__v{major}.{minor}__ready.pdf
{YYYYMMDD}__{company}__{role}__cv__v{major}.{minor}__submitted.pdf
```

文件的内容身份是 SHA-256，而不是文件名或路径。只改名、移动或复制文件不会改变 SHA-256；重新编辑或重新导出则会产生新的哈希。

## 文件分类

| `file_state` | 含义 |
|---|---|
| `source` | 可编辑源文件或原始素材 |
| `draft` | 尚未定稿的版本 |
| `ready` | 已审核、可以投递的版本 |
| `submitted` | 实际投递的不可变快照 |
| `audit` | 简历审计报告 |
| `auxiliary` | 预览图、照片、作品集和测试导出 |

## 数据关系

- `resume_versions`：一个逻辑简历版本，例如 `newland-data-analyst-v1.0`。
- `resume_artifacts`：一个具体文件内容，以 SHA-256 唯一识别。
- `resume_artifact_locations`：文件当前或历史路径，支持改名/移动追踪。
- `applications`：岗位与简历版本、实际投递文件的关联。
- `application_timeline.application_id`：投递过程事件的归属。

## 同步

在项目根目录运行：

```powershell
python scripts/sync_resume_registry.py --json
```

该命令会递归扫描 `data/cv/`、计算 SHA-256、更新分类和路径历史，并按哈希幂等执行。当前已确认的 `cv-newland-photo-edition.pdf` 会作为 `submitted` 快照关联到已有的新大陆“已投递”岗位；不会删除旧文件名。
