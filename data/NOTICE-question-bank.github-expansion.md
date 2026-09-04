# GitHub 扩展题库快照

本批次新增三份可追溯快照，均由上游文件直接转换为 Career OS 统一题库格式，不在本项目中原创题干或答案：

- `question-bank.github-embedded-interview-prep.json`：来自 [`Amir7698/embedded-interview-prep`](https://github.com/Amir7698/embedded-interview-prep)，100 道 rapid-fire + 20 道 bug-hunt 开放题，覆盖 C/C++、中断、内存、UART/CAN/Modbus/MQTT、FreeRTOS、嵌入式 Linux、测试与故障调试。上游 README 声明 MIT；当前上游快照未包含独立 LICENSE 文件，故保留该边界，不把作者的“真实面试/生产问题”声明当作企业内部题目证明。
- `question-bank.github-exam-questions-aptitude.json`：来自 [`AdithSuresh2004/exam-questions`](https://github.com/AdithSuresh2004/exam-questions)，仅导入含完整选项、答案和解释的 `cuet_cs_mock1` 与 `nimcet_mock1`，共 175 道数学、逻辑/情景判断、计算机基础客观题。上游 `LICENCE` 为 MIT；未导入缺少答案解释的 `nimcet_mock2`。
- `personality-bank.github-bigfive-web-ipip-neo-120.json`：来自 [`rubynor/bigfive-web`](https://github.com/rubynor/bigfive-web) 的英文 IPIP-NEO-120 条目，共 120 道，保留正反向计分方向，导入后的 `assessment_kind` 为 `career-personality-ipip-neo-120`，默认快测仍是项目自有 `career-personality-v1` 的 15 题。代码仓库为 MIT，条目依据 IPIP public domain；不作临床诊断或录用结论。

候选但未导入：[`imsunilvaghela/TheEmbeDEADInterview`](https://github.com/imsunilvaghela/TheEmbeDEADInterview) 含 Bluetooth、客户沟通和软技能主题，但当前仓库未发现独立许可证文件；在取得明确授权前不复制其题干。

校验命令：

```powershell
python scripts/github-expansion-smoke.py
python scripts/specialized-bank-smoke.py
```

PDF-only 英语题库暂未导入：当前文件没有可靠的结构化题干/答案，避免 OCR 或人工转录造成题目与答案漂移。
