# GitHub 专项开放面试题快照

本目录新增两份开放式面试题快照：

- `question-bank.github-seringhong-embedded-interview.json`：12 题，来自 [`Sering-Hong/embedded-interview`](https://github.com/Sering-Hong/embedded-interview)，覆盖 C 指针/内存、FreeRTOS、MQTT；上游 README 声明 MIT。
- `question-bank.github-ather-rag-interview.json`：10 题，来自 [`ather-techie/rag-interview-system`](https://github.com/ather-techie/rag-interview-system)，覆盖 Advanced/Agentic/Graph/Corrective/Structured RAG；上游 `LICENSE` 为 MIT。

这些上游内容是开放式问答，不是选择题。为避免凭空生成选项，快照使用 `schema=interview_questions-v1` 和 `question_type=interview`，保留题干、答案解释、来源文件、来源模块和来源题号。现有线上客观题适配器不能直接把它们当作 choice 题导入；模拟面试适配器应按该 schema 读取，并将来源追溯信息写入面试报告。

新增内容不声称是企业内部正式题或 SHL/北森专有题；嵌入式仓库 README 的“真实面试/生产问题”属于上游作者声明，Career OS 不对其逐题真实性作额外背书。RAG 仓库 README 说明社区贡献优先真实面试信号，但其中仍可能含教学内容，使用时保留该边界。

校验命令：

```powershell
python scripts/specialized-bank-smoke.py
```
