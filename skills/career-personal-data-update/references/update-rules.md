# 仓库证据 → Career OS 更新规则

## 可自动建议写入（仍建议确认）

- `skills.proficient|familiar|learning`：仓库高频且与目标方向一致  
- `projects[]`：有可描述亮点与 keywords 的活动簇  
- `tooling` / `work_style`：与记忆层 tooling/preference 一致  
- `evidence_summary`：每次刷新重写计数与信号列表  
- `current_stage` / `target_timeline`：仅当用户对话中明确阶段变化  

## 默认只读、不覆盖

- `personal.name` / `birth_year` / `age`  
- `education.*`  
- 薪资硬约束、城市硬限制：除非用户本轮明确修改  

## 证据质量门槛

| 等级 | 条件 | 动作 |
|------|------|------|
| 高 | 多条记忆/知识单元一致，或用户口头确认 | 可写入 profile |
| 中 | 单次语义命中或模糊标题 | 标「待确认」 |
| 低 | 仅关键词巧合、无上下文 | 不写入 |

## 禁止写入 Career OS 的内容

- API token、cookie、邮箱密码、完整聊天日志  
- 未脱敏的设备序列号、账号 ID  
- 把「学习中」包装成「精通」  

## 推荐 evidence_summary 形状

```yaml
evidence_summary:
  mcp_data_as_of: "YYYY-MM-DD"
  source_counts:
    events: <int>
    memories: <int>
    knowledge_units: <int>
  active_knowledge_collection: "<name or null>"
  high_confidence_signals:
    - "..."
  notes:
    - "证据来自个人数据仓库 MCP；身份字段以 profile 为准"
```
