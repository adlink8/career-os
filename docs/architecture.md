# 求职全流程架构设计

## 三层模型

```
┌──────────────────────────────────────────────────┐
│                 Skill 操作层                       │
│  SKILL.md 定义: 角色、流程、判断逻辑、输出格式      │
│  触发词: 关键词自动激活                             │
│  运行时: 读取 config/profile.yml + knowledge/      │
└──────────────────────┬───────────────────────────┘
                       │ 调用
┌──────────────────────▼───────────────────────────┐
│                 知识参考层                          │
│  knowledge/*.md: 题库、模板、框架、清单、案例       │
│  角色: 被 Skill 引用，不独立运行                    │
│  更新: 从 GitHub/社区定期同步                       │
└──────────────────────┬───────────────────────────┘
                       │ 读写
┌──────────────────────▼───────────────────────────┐
│                  个人数据层                         │
│  config/profile.yml: 求职画像                       │
│  data/tracker.tsv: 投递追踪                         │
│  角色: 个性化上下文，Skill 运行的参数来源            │
└──────────────────────────────────────────────────┘
```

## 运行时与插件层

三层资源之上增加一个薄运行时，不改变三层事实源：

```text
Career OS CLI / Skill
        │ capability
        ▼
PluginManager ── discover plugins/*/plugin.json
        │
        ├─ question_bank  → Exameow/自有 JSON-CSV 导入
        ├─ code_runner    → Judge0（无服务时显式 trusted-local）
        ├─ interview_agent→ DeepInterview/本地 rubric
        └─ job_source     → CareerDesk/CareerSail/career-ops 导出
        │
        ▼
SQLite 报告与 application_timeline / tracker.tsv
```

插件只能通过稳定 capability 访问数据；默认关闭，加载失败回退到核心实现。岗位导入和状态变更仍需人工确认，外部项目不得自动登录或提交申请。

## 数据流

```
用户说"帮我分析这个JD"
        │
        ▼
┌─────────────────────┐
│ career-general-recruit Skill │ ← 从 skills/ 加载
│ 1. 读取 profile.yml  │ ← 了解用户背景
│ 2. 读取 knowledge/   │ ← JD 模板、分析框架
│ 3. 执行分析          │
│ 4. 返回结构化建议    │
└─────────────────────┘
```

JD 分析不会自动写入投递表。只有用户确认实际投递后，`career-app-tracker` 才应读取并更新 `data/tracker.tsv`，避免把分析记录误当成真实投递。模拟笔试/面试写入 SQLite 报告表，但不增加真实投递统计。

## 个人数据仓库联动（LLM 中介）

```text
个人数据分析仓库 (只读 MCP/REST)
        │  search_semantic / stats / memory / knowledge_status
        ▼
     LLM Agent
        │  推理 + 用户确认
        ▼
Career OS 个人数据层 (profile.yml / tracker / cv)
```

- 仓库**不**批处理写 Career OS；由 skill `career-personal-data-update` 驱动 LLM 取证并改文件。  
- 详见 `docs/personal-data-warehouse.md`。

## Skill 创建模板

每个 Skill 必须包含：

```
skill-name/
├── SKILL.md          # 主定义：角色、触发词、模块、输出规格
├── references/       # 内嵌参考（与 Skill 逻辑紧耦合的）
│   └── *.md
└── scripts/          # 可执行脚本（可选）
    └── *.py / *.sh
```

知识层文件放在 `knowledge/<domain>/` 下，可以在多个 Skill 间共享。

## 与 career-ops 的对比

| 维度 | career-ops | Career OS (本系统) |
|------|-----------|-------------------|
| AI 引擎 | Claude Code | 平台中立（可用于支持 skill 的 Agent） |
| 语言 | 英文为主 | 中文生态 |
| 目标市场 | 西方/AI 实验室 | 中国中小厂/外企 |
| 知识层 | Skill 内嵌 | 独立 knowledge/ 目录 |
| 数据层 | profile.yml + TSV | 同样设计 ✅ |
| 步骤覆盖 | 14 个 mode | 16 步完整 |
| 笔试题库 | 无 | 有 (北森/智鼎/SHL) |
| 公司背调 | 无 | 企查查/天眼查集成 |
