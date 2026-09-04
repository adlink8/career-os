# 岗位方向技能矩阵

> 供 `career-self-assessment` 模块二「方向匹配」查表用。
> 每个方向列出:对口技能组合、岗位关键词、薪资带、对口项目类型、必须补的技能。
> 薪资为 2026 届应届/实习的中国一二线城市参考值,使用时应刷新(见 KNOW-03)。

## 矩阵总览

| 方向 | 核心技能组合 | 应届薪资带 | 实习薪资带 | 对口项目特征 |
|------|-------------|-----------|-----------|------------|
| 运维/技术支持 | Linux+网络+Shell | 6-10k | 3-6k | 服务器/网络配置 |
| DevOps 助理 | Linux+Docker+CI/CD | 7-12k | 4-7k | 部署流水线 |
| IoT 平台运维 | Linux+MQTT+嵌入式 | 7-11k | 4-7k | 设备接入链路 |
| AI Agent 运维 | Python+Docker+RAG | 8-14k | 5-8k | LLM 管道 |
| 数据工程 | Hadoop+Kafka+Flink | 7-12k | 4-7k | 离线/实时数仓 |
| 网络运维/集成 | 网络+VLAN+抓包 | 5-9k | 3-6k | 组网竞赛/排障 |
| 外企 IT Support | 英语+Windows/Linux | 6-10k | 4-7k | 双语工单经验 |

---

## 1. 运维 / 技术支持(中小公司)

- **对口技能**:Linux(Ubuntu/CentOS)、网络基础、Shell/Bash、Docker
- **岗位关键词**:运维工程师、技术支持、系统管理员、IT 实习
- **必须补**:系统服务(systemd)、监控(Zabbix/Prometheus)、自动化脚本
- **加分项**:Git、Ansible、抓包能力
- **判断信号**:JD 提到"Linux 日常运维""故障响应""系统部署"

## 2. DevOps 助理

- **对口技能**:Linux + Docker + Git + CI/CD(Jenkins/GitHub Actions)
- **岗位关键词**:DevOps 实习、发布工程师、SRE 助理
- **必须补**:Kubernetes、CI/CD pipeline 编写、云平台(阿里云/AWS)
- **加分项**:Terraform、Prometheus+Grafana
- **判断信号**:JD 提到"持续集成""容器编排""流水线"

## 3. IoT 平台运维

- **对口技能**:Linux + MQTT + 嵌入式通信(ESP32/网关)+ 云 IoT(AWS IoT/阿里云 IoT)
- **岗位关键词**:物联网运维、IoT 平台工程师、智能硬件支持
- **必须补**:物联网协议(CoAP/LoRa)、时序数据库(InfluxDB)、边缘计算
- **加分项**:设备管理平台经验、抓包定位 keepalive/QoS 问题
- **判断信号**:JD 提到"设备接入""MQTT""物联网平台"

## 4. AI Agent 运维 / RAG 管道维护

- **对口技能**:Python + Docker + 向量数据库 + RAG + MCP/Agent 工具链
- **岗位关键词**:AI 运维、LLM 工程助理、RAG 管道维护
- **必须补**:LangChain/LlamaIndex、Prompt 工程、向量库(Milvus/Pinecone)
- **加分项**:Kubernetes、模型部署(vLLM/Ollama)、可观测性
- **判断信号**:JD 提到"大模型""RAG""Agent""LLM 部署"

## 5. 数据工程

- **对口技能**:Hadoop + Flume + Kafka + Flink + SQL
- **岗位关键词**:数据工程实习、大数据开发助理、ETL 工程师
- **必须补**:Hive、Spark、数据仓库建模、Airflow
- **加分项**:实时计算、数据质量监控
- **判断信号**:JD 提到"数仓""ETL""离线/实时计算"

## 6. 网络运维 / 系统集成

- **对口技能**:网络(VLAN/路由/交换)+ 抓包(Wireshark)+ 故障排查
- **岗位关键词**:网络工程师、系统集成、网络运维实习
- **必须补**:CCNA/HCIA 知识体系、防火墙配置、VPN
- **加分项**:组网竞赛经历、BGP/OSPF
- **判断信号**:JD 提到"网络规划""综合布线""VLAN/路由"

## 7. 外企 IT Support(差异化方向)

- **对口技能**:英语(书面+口语)+ Windows/Linux 桌面支持 + 工单系统
- **岗位关键词**:IT Support、Helpdesk、Technical Support Analyst
- **必须补**:英语达到 Duolingo 90+ / CET-6、AD 域、Office 365 管理
- **加分项**:日语(N3+)、ITIL 框架、远程支持经验
- **判断信号**:JD 英文撰写、提到"ticketing""end-user support""AD/O365"

---

## 匹配度评估规则

对每个方向打分(0-3),总分越高匹配度越高:

| 维度 | 0 分 | 1 分 | 2 分 | 3 分 |
|------|------|------|------|------|
| 核心技能命中 | 0 个 | 1 个 | 2 个 | 3+ 个 |
| 对口项目存在 | 无 | 类似 | 直接相关 | 有量化成果 |
| 学习中技能可补齐 | 否 | 部分 | 是 | 已接近完成 |
| 城市/薪资匹配 | 不符 | 部分 | 符合 | 完全符合 |

**输出阈值**:
- 总分 ≥ 10 → 匹配度:高
- 总分 7-9 → 匹配度:中高
- 总分 4-6 → 匹配度:中
- 总分 ≤ 3 → 不推荐(避免空泛建议)

---

## 注意事项

- 薪资带每年浮动,使用前必须刷新(`knowledge/salary-data/` 同步后为准)。
- "匹配度:高"只代表技能对口,不代表一定能拿 offer;最终需结合公司背调与面试表现。
- 不要推荐用户明显不想去的方向(如 profile.yml 中未提及的"销售/纯管理岗")。
