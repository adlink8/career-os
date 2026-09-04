# Open Quiz Commons 扩展题库来源说明

`question-bank.github-openquiz-python-core.json`、`question-bank.github-openquiz-data.json`、`question-bank.github-openquiz-ops.json`、`question-bank.github-openquiz-ai-js.json`、`question-bank.github-openquiz-devops.json`、`question-bank.github-openquiz-embedded-data-infra.json`、`question-bank.github-openquiz-testing-ops.json`、`question-bank.github-openquiz-data-api.json`、`question-bank.github-openquiz-ai.json` 和 `question-bank.github-openquiz-next-foundations.json` 共收录 678 道来自 [`prahladyeri/open-quiz-commons`](https://github.com/prahladyeri/open-quiz-commons) 的公开选择题（另有 25 道基础快照题）。

- 内容许可：CC BY-SA 4.0，见上游 [`LICENSE`](https://github.com/prahladyeri/open-quiz-commons/blob/main/LICENSE)。再分发或修改时保留上游署名并遵守相同方式共享。
- 上游数据目录：[dataset](https://github.com/prahladyeri/open-quiz-commons/tree/main/dataset)
- 扩展批次按 Career OS 当前 `jobs` 表经 `bin/jd_assessment_mapper.py` 计算的五条轨道选择：软件测试/运维、技术支持/FAE、物联网/嵌入式、数据分析、AI 应用/RAG。该选择是准备建议，不是企业内部题库或录用标准。
- `embedded-data-infra` 批次增加 Rust 嵌入式系统基础、PostgreSQL、异步网络与 Terraform/IaC；Rust 题只能补系统思维，不能替代 C/C++、RTOS 和硬件调试专项。
- `testing-ops` 批次增加 pytest/unittest/mocking/覆盖率/静态检查、文件系统、自动化和环境变量；`data-api` 批次增加事务/迁移/ORM、REST/FastAPI、认证、pandas、可视化和 Jupyter；`ai` 批次增加神经网络与 scikit-learn。它们是通用基础题，不等同于企业专有题或 RAG 专项题。
- `next-foundations` 批次增加 Python 迭代器/标准库/异步、JavaScript/Node.js 网络、Rust 并发/FFI/工具链，以及边缘限流与部署基础；仍不替代 C/C++、RTOS、硬件调试或企业专有题。
- 每道题保留 `source_file`、`source_module`、`source_text` 和 `source_question_id`；导入来源标识为 `github-open-quiz-commons`，统一适配器按来源题号幂等更新。
- 本项目未新增原创题，也未复制北森、SHL 或企业自研平台的专有正式题目。
