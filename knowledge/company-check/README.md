# company-check 知识域

> **用途:** 供 `career-company-check` skill 调用,提供公司背调的方法论和行业风险库。
> **更新方式:** 背调方法稳定;风险库半年补充新案例。
> **消费 skill:** `skills/career-company-check/`

## 资料来源

| 来源 | 类型 | 用途 |
|------|------|------|
| 企查查 / 天眼查 MCP | 工商数据 | 核验公司合法性 |
| 脉脉 / 看准网 / 知乎 | 社区口碑 | 员工真实评价 |
| 中国裁判文书网 | 司法数据 | 劳动纠纷核查 |
| [V2EX / linux.do](https://v2ex.com) | 技术社区 | 程序员口碑 |

## 文件清单

- `red-flags-database.md` — 红旗风险库(皮包/欠薪/诈骗特征)
- `background-check-method.md` — 背调方法论(数据源优先级)

## skill 调用提示

- skill 启动时读取本目录的红旗库
- 检测到红旗时输出红/黄/绿三色评分
- 工商数据通过企查查/天眼查 MCP 获取(若已连接),否则提示用户手动查
