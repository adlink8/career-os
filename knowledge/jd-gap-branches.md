# JD 缺口分支登记表 (JD-Gap Branch Registry)

> 字段说明：
> - **分诊结论**：`改简历`（词已存在）| `开分支`（能力真缺已立项）| `放弃`（门槛不过）
> - **量化指标**：真实测量值，格式 `指标名=数值`，直接对应引擎 D4
> - **简历落点**：关键词写进了哪份简历的哪个项目正文
> - **状态**：`分诊中` | `开发中` | `已完成待验证` | `已入简历` | `已放弃`
>
> 维护纪律：每开一个分支必须先有登记行；状态变更当天更新；分支永不合并主线、永不删除。

| 日期 | 目标 JD（公司·岗位·job_id） | 缺口词 | 分诊结论 | 宿主项目 / 分支名 | 量化指标 | 简历落点 | 状态 |
|---|---|---|---|---|---|---|---|
| 2026-09-08 | 九号公司·助理IT基础运维工程师·jobs#240 | RAG / Agent / Prompt | **改简历**（能力在 NovelMind 已有：RAG 评估系统+LangChain 无关但 RAG 管道真实存在） | 无需分支 | NovelMind 已有：recall@k 评估、ChromaDB 向量检索 | cv-ops 正文改写稿（待写） | 分诊中 |
| 2026-09-08 | 九号公司·助理IT基础运维工程师·jobs#240 | LangChain | **放弃**（JD 原文只提"大模型+RAG"，LangChain 属锦上添花非 Top5 硬要求；NovelMind 用原生 RAG 管道已覆盖同一能力叙事） | — | — | — | 已放弃 |
| 2026-09-09 | 焦点科技·Java开发工程师（AI应用部）·run#2 | Redis | **开分支**（检索结果缓存是 RAG 自然延伸，时间盒≤1天） | novel-mind / feat/jd-redis-focus @ d03bee6d | hit_ms<5 且快于 miss 路径 | runs/2 resume NovelMind 正文 | 已入简历 |
| 2026-09-09 | 焦点科技·Java开发工程师（AI应用部）·run#2 | LangChain | **开分支**（GitHub 同类最小 RAG 后，落地官方 splitter+Document，单测 2 passed） | novel-mind / feat/jd-langchain-focus @ f0814de8 | 切分≥2 块且保留 chapter_id | runs/2 项目经历正文 | 已入简历 |
| 2026-09-09 | 焦点科技·Java开发工程师（AI应用部）·run#2 | 多模态 | **改简历**（职责写「文本、向量」双路，NovelMind 已有文本向量化入库，属漏写） | 无需分支 | — | runs/2 resume 补「多模态=文本+向量」 | 已入简历 |
| 2026-09-09 | 焦点科技·Java开发工程师（AI应用部）·run#2 | Milvus | **放弃**（GitHub milvus-lite：Windows 不支持；Docker 独立集群超时间盒；Chroma 已覆盖向量闭环，不换品牌名） | — | — | — | 已放弃 |
| 2026-09-09 | 焦点科技·Java开发工程师（AI应用部）·run#2 | Kafka | **放弃**（本机 Docker 可跑但未拉起 broker；无现成消息总线宿主，一天内装不进 NovelMind） | — | — | — | 已放弃 |
| 2026-09-09 | 焦点科技·Java开发工程师（AI应用部）·run#2 | 微服务 | **放弃**（JD 要 Java Spring Cloud；虽有 JDK17+Maven，PetCare 单体拆服务>1天，Python 多进程不算） | — | — | — | 已放弃 |

## 岗位结论

**放弃投递：焦点科技 · Java开发工程师（AI应用部）**（apply-run #2）。  
ATS 补 Redis+LangChain 后 72 WARN 刚过 70，但 Kafka / Milvus / Java 微服务仍是职责里的后端底座，现场跑不通、一天补不上。弹药分支保留，不网申。

完整 Why / 步骤 / 坑：`knowledge/jd-gap-focus-java-ai.md`。开分支写测试必须同时写这类记录。

## 已完成分支（面试弹药库）

### feat/jd-redis-focus（novel-mind @ d03bee6d）
- demo：`cd backend && python -m pytest tests/test_retrieval_cache.py -q`
- 指标：缓存命中 <5ms，且快于 miss
- 话术：检索结果 Redis 缓存，未接 Redis 时内存后端；`NOVELMIND_REDIS_URL` 切真 Redis

### feat/jd-langchain-focus（novel-mind @ f0814de8）
- demo：`cd backend && python -m pytest tests/test_langchain_ingest.py -q`
- 指标：官方 splitter 切出 ≥2 个 Document
- 话术：LangChain 只做切分适配，层级 RAG 仍是自研；不把未跑通的 LLM chain 写进简历
