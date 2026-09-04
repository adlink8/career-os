# Open Quiz Commons 题库来源说明

`question-bank.github-openquiz.json` 收录 25 道来自 GitHub 项目 [`prahladyeri/open-quiz-commons`](https://github.com/prahladyeri/open-quiz-commons) 的 Python、pandas 和 JavaScript 选择题。另有 10 个按当前 JD 缺口选择的扩展快照，共 678 道；导入后 Open Quiz Commons 来源合计 703 道。题干、选项、答案和解释均按上游数据保留；本项目没有新增题目，仅补充 Career OS 字段、中文分类和来源题号。

- 内容许可：CC BY-SA 4.0，见上游 [`LICENSE`](https://github.com/prahladyeri/open-quiz-commons/blob/main/LICENSE)。再分发或修改本题库时应保留署名并遵守相同方式共享。
- 数据目录：[上游 dataset](https://github.com/prahladyeri/open-quiz-commons/tree/main/dataset)
- 本快照实际取自：[Python basics](https://raw.githubusercontent.com/prahladyeri/open-quiz-commons/main/dataset/python/core/basics.json)、[pandas](https://raw.githubusercontent.com/prahladyeri/open-quiz-commons/main/dataset/python/data_science/pandas.json)、[JavaScript basics](https://raw.githubusercontent.com/prahladyeri/open-quiz-commons/main/dataset/javascript/core/basics.json)
- 导入来源标识：`github-open-quiz-commons`
- 扩展快照：`question-bank.github-openquiz-python-core.json`、`question-bank.github-openquiz-data.json`、`question-bank.github-openquiz-ops.json`、`question-bank.github-openquiz-ai-js.json`、`question-bank.github-openquiz-devops.json`、`question-bank.github-openquiz-embedded-data-infra.json`、`question-bank.github-openquiz-testing-ops.json`、`question-bank.github-openquiz-data-api.json`、`question-bank.github-openquiz-ai.json`、`question-bank.github-openquiz-next-foundations.json`
- 扩展选择依据：当前 `jobs` 表经 `bin/jd_assessment_mapper.py` 推导出的 software-testing-ops、technical-support-fae、iot-embedded、data-analysis、ai-rag 题型缺口；扩展文件的 `source_module`、`source_file` 和 `jd_tracks` 保留逐题追溯信息。
- 适用范围：技术岗校招线上客观题练习；不代表任何公司的真实题目或录用标准。
- 复核边界：题库为社区维护，运行前应按当前 Python/JavaScript/pandas 官方文档复核可能变化的知识点。
