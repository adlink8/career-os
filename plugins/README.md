# Career OS 插件目录

插件采用统一 manifest：

```text
plugins/<plugin-id>/plugin.json
```

核心只依赖 capability，不直接绑定外部项目。可用 capability：

- `job_source`：读取 CareerDesk、CareerSail、career-ops 等项目导出的岗位数据；只导入，不自动提交。
- `question_bank`：导入 Exameow/PrairieLearn 兼容的自有题库，也支持 `personality`/Likert 题；不复制受版权保护的题目。
- `code_runner`：通过 Judge0/Piston 等受控执行服务运行代码题。
- `interview_agent`：接入 DeepInterview、AI Mock Interviewer 等面试引擎。

插件默认关闭。启用方式：

```powershell
$env:CAREER_OS_PLUGINS = 'judge0'
python bin/career_jobs_cli.py code-sandbox 11
```

真实模型面试适配器（默认不联网）：

```powershell
$env:CAREER_OS_PLUGINS = 'openai-compatible-interview'
$env:CAREER_OS_LLM_BASE_URL = 'http://127.0.0.1:8000/v1'
$env:CAREER_OS_LLM_MODEL = 'your-model'
```

它调用 OpenAI-compatible `/chat/completions`，仅在配置 endpoint 时启用外部服务；未配置或失败会回退核心 `local-rubric`，报告记录 `provider`、`scoring_engine` 和 `external_service`。

插件故障会被隔离并回退到核心能力；插件不得绕过 Career OS 的人工确认、隐私和投递状态契约。

## 最小适配器接口

插件模块暴露 `create_plugin(manifest=None)`，返回实现 `provide(capability)` 的对象：

```python
class MyAdapter:
    def provide(self, capability):
        return self if capability == "job_source" else None

    def load(self, source, *, source_plugin, apply=False):
        # 返回 preview/inserted/updated 等统计；apply=False 时只预览
        ...

def create_plugin(manifest=None):
    return MyAdapter()
```

外部项目只需把自己的导出格式映射到稳定字段，不需要修改 `career_jobs_cli.py` 或 SQLite 核心表。适配器应声明版本、许可证和所需凭据，并在缺少凭据时安全失败。

性格题可使用 `assessment_kind`、`dimension`、`scale_min`、`scale_max` 和 `reverse_scored` 字段；核心评分器负责反向计分、维度汇总和报告留痕，外部题库只需提供这些字段即可插拔替换。

当前题库数据插件还包括 `open-quiz-commons`（CC BY-SA 4.0）。它与 `exameow` 一样复用统一 `question_bank` 适配器；数据快照位于 `data/question-bank.github-openquiz*.json`，基础快照和 6 个 JD 扩展快照可按 `github-open-quiz-commons` 来源 ID 幂等导入。
