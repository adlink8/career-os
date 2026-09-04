# 个人数据仓库 × Career OS × LLM

## 正确联动模型（不是批处理同步）

```text
┌──────────────────────────┐
│  个人数据分析仓库         │
│  <warehouse_root>        │
│  SQLite / Chroma / 知识索引 │
└────────────┬─────────────┘
             │ 只读：MCP / REST / CLI
             ▼
┌──────────────────────────┐
│  LLM Agent（本机）        │
│  检索证据 → 推理 → 提议 diff │
└────────────┬─────────────┘
             │ 写入（确认后）
             ▼
┌──────────────────────────┐
│  Career OS 个人数据层     │
│  config/profile.yml       │
│  data/tracker.tsv         │
│  data/cv/cv-*.md             │
└──────────────────────────┘
```

- **仓库**：给 LLM 提供「你是谁、做过什么、长期偏好」的证据，不直接改 Career OS 文件。
- **LLM**：根据仓库证据 + 用户意图，更新 Career OS 求职画像/投递/简历。
- **Career OS**：求职工作流的落盘与 Skill 输入；身份字段以本地 profile 为准，证据可刷新。

不要做：脚本定时把 stats 糊进 profile（会丢语境、易误写）。

## 启动数据仓库（给 LLM 供数）

在仓库根目录：

```powershell
# 终端 1：REST（MCP 语义检索依赖它）
python integration\scripts\api_server.py

# 终端 2：MCP stdio（由客户端拉起也可）
python integration\scripts\mcp_server.py
```

CLI 抽查：

```powershell
python integration\scripts\unified_search.py knowledge --no-chroma
python integration\scripts\unified_search.py semantic "MQTT 项目" --top-k 3 --json
python integration\scripts\unified_search.py stats --json
```

## 客户端挂 MCP

把仓库 MCP 配进所用 AI 客户端（路径按本机修改）：

```json
{
  "mcpServers": {
    "personal-data": {
      "command": "python",
      "args": [
        "<warehouse_root>/integration/scripts/mcp_server.py"
      ]
    }
  }
}
```

推荐工具：`knowledge_status`、`stats`、`search_semantic`、`get_memory_profile`、`get_memory_by_subject`、`data_list_*`。

路径约定见：`config/personal-data-warehouse.yml`（本地）/ `*.example.yml`（样本）。

## 在 Career OS 里让 LLM 更新个人数据

触发 skill **`career-personal-data-update`**，例如：

- 「根据我的个人数据仓库更新 profile」
- 「用数据仓库证据刷新技能和项目」
- 「对照仓库里的记录，补全求职画像」

Agent 应按 skill 流程：

1. 读 `config/profile.yml` + 本配置  
2. 调仓库 MCP 拉证据  
3. 给出拟修改 diff  
4. 用户确认后写入 Career OS 文件  

## 字段权威性

| 字段类型 | 权威来源 | 仓库证据 |
|----------|----------|----------|
| 姓名/学历/出生年 | profile.yml | 仅交叉核对，默认不覆盖 |
| 技能栈/项目亮点 | profile + 用户确认 | 可提议增补 |
| 投递记录 | tracker.tsv + 用户确认 | 仓库一般不直接产生投递行 |
| 工具偏好/工作方式 | 可被仓库记忆强化 | 可写 work_style / tooling |
| evidence_summary | LLM 根据仓库刷新 | 推荐每次更新后重写 |

## 隐私

- 仓库含历史对话与检索痕迹；MCP 仅本机 loopback。  
- 勿把 token、cookie、完整聊天原文写入 Career OS。  
- `config/profile.yml`、`personal-data-warehouse.yml` 保持本地、不进公开仓库。
