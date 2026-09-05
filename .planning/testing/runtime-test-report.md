# 运行时测试报告(Runtime Test Report)

> 测试目标:Phase 5 行动清单第 1 条(最高优先级)——在真实 Agent 环境触发 skill,验证 trigger / 知识层读取 / 输出格式,闭合 C1 风险。
> 测试日期:2026-09-05
> 测试方法:并行派发独立子 agent 作为"模拟真实 AI agent 运行时",每个子 agent 完整读取 SKILL.md → 按运行规则读取依赖 → 处理模拟用户请求 → 按输出格式生成响应 → 报告执行障碍。子 agent 与实现者隔离,只读执行,不修改业务文件。

---

## 一、测试覆盖

| # | Skill | 模拟用户请求 | 覆盖的运行时能力 |
|---|-------|------------|----------------|
| 1 | career-daily-driver | "今天我该做点什么?给我安排一下。" | 跨文件状态聚合(current-status + tracker + profile)、行动排序、输出契约 |
| 2 | career-interview-master | "帮我模拟一场运维方向的面试,先出第一道题。"+ 模拟作答 | 题库抽取、逐题评分、lessons-learned 草稿生成 |
| 3 | career-general-recruit | 粘贴 JD("帮我解读这个 JD,我该不该投?") | JD 五维解读、profile 匹配、红旗检测、关键词库对照 |
| 4 | career-general-recruit(复测) | 同上(相同用例) | 验证修复后首次执行体验 |

环境约束说明:测试环境 Bash 工具故障(ENOENT),子 agent 全程使用 Read 工具执行——这意外验证了 skill 流程在"无 shell"受限环境下的可执行性(daily-driver 与 interview-master 无强制 CLI 步骤,纯文件+推理驱动,完整走通)。

---

## 二、测试结果

| Skill | 首测判定 | 复测判定 | 结论 |
|-------|---------|---------|------|
| career-daily-driver | **PASS** | — | 核心流程完整走通;2 处规范瑕疵已修 |
| career-interview-master | **PASS** | — | 全链路可跑通;4 处文档缺陷已修 |
| career-general-recruit | **PARTIAL** | **PASS** | 4 项修复全部验证生效,首次读取命中率 7/7 |

**C1 风险状态:🟠 未缓解 → 🟢 首轮运行时验证通过(3 skill PASS)。**
完全闭环仍需:用户在日常真实 agent 中触发(子 agent 模拟是运行时行为验证的第一层,真实 agent 的 trigger 路由和上下文管理可能存在平台差异)。

---

## 三、发现的问题与修复(13 处,已全部落盘)

### 共性问题(3/3 skill 都有)

| 问题 | 严重度 | 修复 |
|------|--------|------|
| SKILL.md 引用路径无基准声明(references 在 skill 目录、knowledge/config/data/templates 在项目根,两种基准混用,冷启动 agent 首读必失败) | 🔴 高(阻断首次执行) | 3 个 SKILL.md 各加「路径基准」节 |

### skill 专项问题

| Skill | 问题 | 修复 |
|-------|------|------|
| general-recruit | 红旗库只写目录名,无具体文件指针 | 流程第 4 步写明 `red-flags-database.md` |
| general-recruit | trigger 缺"帮我解读"词面 | trigger 第 2 行补充 |
| interview-master | 模块一缺评分反馈输出模板(依赖执行者自由发挥) | 新增「评分反馈输出格式」节(维度表+加权总分+改进建议) |
| interview-master | 选题规则二义性("优先项目题"与实际作答冲突) | 明确"第 1 题固定为项目题;用户直接作答非当前题时按对应题库题目评分" |
| daily-driver | 输出模板缺"预计耗时"槽位(与工作流第 2 条矛盾) | 模板行增加耗时槽位 |
| daily-driver | trigger 缺口语变体 | 补"今天该做点什么/安排一下今天/今天干点啥" |

### knowledge 层问题

| 文件 | 问题 | 修复 |
|------|------|------|
| red-flags-database.md | 无"单休"条目,判定只能靠类比推理 | P1 表新增第 8 条(单休/无双休) |
| ops-keywords.md | "用户状态"列与 profile.yml 形成双事实源 | 文件头声明"以 profile.yml 实时内容为准" |

### 数据层问题

| 文件 | 问题 | 修复 |
|------|------|------|
| tracker.tsv + daily-driver-spec.md | 顶部统计表(企业建档口径)与 spec 统计规则(逐行口径)冲突,无口径说明 | spec 补「待沟通内推」归类 + 双口径声明(冲突以逐行为准);tracker 统计表下加口径注释 |

---

## 四、运行时行为亮点(验证通过的设计)

1. **依赖文件全部真实存在**:3 个 skill 声明的所有依赖(profile/current-status/tracker/题库/红旗库)磁盘上全部存在,知识层引用闭环成立。
2. **输出格式可复现**:3 个子 agent 在无人工干预下均按 SKILL.md 模板生成了结构一致的输出(作战台格式/出题+评分格式/JD 五维格式)。
3. **数据引用真实**:子 agent 的输出直接引用 tracker.tsv 的真实投递记录(新大陆 2 条)和 profile.yml 的证据信号(Linux 263 条/Docker 305 条/Python 534 条),无编造。
4. **受限环境降级正确**:无 Bash 时 skill 纯文件驱动部分完整执行,CLI 依赖被如实标注而非跳过。

---

## 五、遗留问题(不阻塞,待后续)

1. 「启动时读取」第 2/3 项声明为目录而非具体文件名,首次执行需依赖 SKILL.md 后文引用确定成员文件——建议后续细化到文件名。
2. Shell/Bash 双事实源残留:ops-keywords 标"✅ 熟练"但 profile.yml 未单列 Shell(仅 PowerShell)——库头已声明以 profile 为准,但用户应确认 Shell 真实证据后同步 profile。
3. interview-master 与新运行时(bin/ CLI 的 exam/interview 子命令、data/question-bank.*.json)完全脱节,两套题库未声明分工——建议在 SKILL.md 中划界(对话式模拟用 knowledge 题库,机考训练转 CLI)。
4. 真实 agent 触发验证(C1 完全闭环):在用户日常使用的 agent 中触发 3+ skill,确认平台级 trigger 路由正常。

---

*Generated 2026-09-05 by 3+1 subagent runtime test loop. 修复由主 agent 统一执行,复测由独立子 agent 验证。*
