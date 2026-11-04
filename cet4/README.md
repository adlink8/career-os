# CET-4 分库（四级专区）

四级相关的一切都在这个文件夹里，仓库根的 `bin/`、`docs/`、`var/` 不再新增四级文件。

```
cet4/
├─ bin/                       # 全部四级脚本（43 个 cet4_*.py + 3 个播放器/故事生成器）
├─ docs/                      # 四级设计文档（题型规范、整卷蓝图、12 月预测、流水线说明）
├─ knowledge/cet4-bank/       # 真题题库：00-10 共 11 个专题（真题 Markdown/答案/词汇/音频/模拟卷/出题知识库）
└─ var/cet4-daily/            # 运行数据与产物（不入 git）
   ├─ demo-whole-paper.json   # 演示整卷数据
   ├─ words.json              # 全词词典（1778 条）
   ├─ paper-demo/             # 生成的试卷 HTML（explain 讲解版 / plain 纯题版）
   ├─ pipeline/               # 出题-审查-修复的轮次记录
   ├─ _scratch/               # 临时脚本与一次性产物
   └─ audio/                  # 写作/翻译朗读 mp3
```

## 运行方式

在仓库根直接跑即可，脚本内部把相对路径统一按 `cet4/` 解析：

```powershell
# 生成讲解版 + 纯题版
python cet4/bin/cet4_build_paper.py var/cet4-daily/demo-whole-paper.json --mode explain
python cet4/bin/cet4_build_paper.py var/cet4-daily/demo-whole-paper.json --mode plain

# 装配自检（只收集证据，不做通过门）
python cet4/bin/cet4_paper_audit.py var/cet4-daily/demo-whole-paper.json

# 出题/审查/修复（CodeBuddy 会话）
python cet4/bin/cet4_roles.py --type reading --role writer
python cet4/bin/cet4_pipeline.py --type reading --input var/cet4-daily/pipeline/reading1.json --rounds 3
```

路径参数可以写 `var/cet4-daily/xxx.json`（推荐），也可以写 `cet4/var/cet4-daily/xxx.json`，两种都能跑。

## 三条硬规则

1. 通过与否只由独立 CodeBuddy 审查老师的 `verdict` 决定，不用脚本做门。
2. reviewer 的 `must_fix` 必须回灌给 repair 会话。
3. 正文定稿后用 `--qonly` 只迭代题目。

## 文档

- `docs/cet4-question-design-spec.md` — 题型与考点规范
- `docs/cet4-whole-paper-blueprint.md` — 整卷结构蓝图
- `docs/cet4-full-question-analysis.md` — 真题题库分析
- `docs/cet4-daily-mock-pipeline.md` — 每日流水线设计
- `docs/cet4-2026-12-prediction.md` — 12 月考点预测
- `docs/cet4-reading-tool-review.md` — 做题工具评审记录
