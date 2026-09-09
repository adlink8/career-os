# 焦点 Java AI 岗：缺口分支全流程（Why / 怎么做 / 坑）

> 岗位：焦点科技 · Java开发工程师（AI应用部）  
> apply-run：#2 · jobAdId `d96fd833-7473-49fa-a959-171412a34bee`  
> 日期：2026-09-09  
> 结论：**不投递**。Redis / LangChain 分支保留作面试弹药，不合并 master。

---

## 1. 整条链路（这次实际跑过的）

```text
捕获 JD+表单（Moka 详情页 + 报名页合流）
  → 拆解 / 对照 / 定制简历
  → ATS 55 → 58 → 66 FAIL（缺 Kafka LangChain Milvus Redis 多模态 微服务）
  → 禁止再无脑改简历
  → 缺口分诊（改简历 / 开分支 / 放弃）
  → 能立项的：宿主开 feat/jd-* 、写实现、写测试、提交推送
  → 关键词写进【项目经历】正文（不是技能栏）
  → 再跑 ATS
  → 仍缺的词：GitHub 找同类 + 问原理 + 尝试本机跑
  → 一天内跑不通 → 放弃该岗位
```

ATS 数字：

| 节点 | 总分 | 关键词维 | missing |
|---|---|---|---|
| 优化堆词结束 | 66 FAIL | 12 | Kafka, LangChain, Milvus, Redis, 多模态, 微服务 |
| Redis 入正文 | 67 FAIL | 18 | Kafka, LangChain, Milvus, 微服务 |
| LangChain 入「项目经历」 | **72 WARN** | 20 | Kafka, Milvus, 微服务 |

72 刚过机器门（≥70），过不了「我会做 Java 微服务 + Kafka + Milvus」这场面试。所以停。

---

## 2. 分诊：为什么这么做

原则：**简历缺词的正解不是编词，是把词做进真项目，并能 `pytest` + `git log` 给面试官看。**

立项三门槛（全过才开分支）：

1. JD 权重够（职责/硬要求，不是「优先」）
2. 时间盒 ≤ 1 天
3. 自然宿主：NovelMind / local-llm-lab / career-os（或已有 Java 的 PetCare），不造新仓库

| 词 | 决策 | Why |
|---|---|---|
| 多模态 | 改简历 | JD 写的是「文本、向量」双路，Chroma 入库已经是这件事，属于漏写。 |
| Redis | 开分支 | 检索缓存是 RAG 的自然延伸；不需要新仓库；一天能做出带测试的最小实现。 |
| LangChain | 先放弃、后改开分支 | JD 只写「优先」。后来按你的规则去 GitHub 找同类最小 RAG，用官方 splitter 切出真 Document 并测试通过，才立项。只做切分适配，不替换自研层级 RAG。 |
| Milvus | 放弃 | 向量闭环已在 Chroma。GitHub `milvus-lite` **明确不支持 Windows**。Docker 独立集群超时间盒。换品牌名不算。 |
| Kafka | 放弃 | 原理清楚（分区日志 + 消费组），本机 Docker 在，但没有现成消息总线宿主，一天塞不进 NovelMind。没有 broker 的 import 不算。 |
| 微服务 | 放弃 | JD 要 Java Spring Cloud。JDK17+Maven 有，PetCare 仍是 Spring Boot 单体，拆服务 >1 天。FastAPI+agent-service 是多进程，不能冒充 Java 微服务。 |

---

## 3. Redis 分支：怎么做、测什么、为什么这样设计

**仓库 / 分支：** `novel-mind` · `feat/jd-redis-focus` · `d03bee6d`（已推 origin，不合并 master）  
**从哪开：** `novel-mind-new` 的 `master` 拉 worktree，避免脏工作区 `codex/cleanup-effective-code`。

**做什么：** 在 `_vector_search` 外包一层 `RetrievalCache`。同一 `(novel_id, query, top_k)` 命中则跳过 embedding + Chroma。

**为什么默认内存、Redis 可选：**

- 单测不能依赖本机 Redis 进程，否则 CI/面试笔记本没 Redis 就红。
- 协议对齐 Redis：`setex` / `get`。测里用 FakeRedis，证明走的是 Redis 接口不是另一套 API。
- `NOVELMIND_REDIS_URL` 有则切真 Redis。面试可以先跑内存测试，再视环境接真实例。

**测试（4 passed）：**

```text
cd backend
python -m pytest tests/test_retrieval_cache.py -q
```

- miss 再 set 再 hit
- TTL 过期
- FakeRedis `setex` 真的被调用
- 命中路径 <5ms，且快于带 20ms 模拟检索的 miss

**不做什么：** 不把 Redis 当 Kafka 用；不在简历写「生产集群 Redis」。

---

## 4. LangChain 分支：怎么做、测什么、为什么这样设计

**仓库 / 分支：** `novel-mind` · `feat/jd-langchain-focus` · `f0814de8`（已推 origin，不合并 master）  
**GitHub 对照：** 一类最小 RAG（LangChain + 切分 + 向量库），例如 chromadb-rag-example。我们只复用「官方 splitter → Document」这一层。

**为什么不接完整 LLM chain：**

- 完整 chain 要 embedding 模型或付费 API，本机不一定有。
- NovelMind 已有自研层级 RAG。用 LangChain 换掉内核 = 为关键词推翻主线，面试一问就穿。
- 切分是 LangChain 最稳、可单测、不依赖外网的一层。

**测试（2 passed，导入约 20s）：**

```text
python -m pytest tests/test_langchain_ingest.py -q
```

必须切出 ≥2 个 `Document`，且 `chapter_id` 还在。禁止「import 成功就算」。

---

## 5. 踩过的坑（以后开分支先看）

1. **ATS 不认 `## 项目`，认 `项目经历`。**  
   LangChain 写进了项目 bullet，仍进 `elsewhere`（教育/概述），关键词维不加分。改成「项目经历」后 LangChain 才 grounded，66→72。  
   **以后定制简历：章节名必须是引擎认的「项目经历」。**

2. **技能栏 / 分支名里出现关键词 ≠ 项目落地。**  
   引擎只计项目正文。`feat/jd-langchain-focus` 写在路径里没用。

3. **堆词把 ATS 从 55 拉到 66，过不了 70。**  
   缺的是真能力。再改简历会触发 HR「关键词墙」。正确下一步是分诊开分支，不是第三轮作文。

4. **Windows ≠ Linux 示例。**  
   Milvus Lite 官方不支持 Windows。对着 README 抄 `MilvusClient("./demo.db")` 会装不上或直接炸。不要把 Linux gist 当本机证据。

5. **Docker 在 ≠ 一天能接入。**  
   Kafka 镜像开始拉层，但没有宿主消息总线，跑起来也只是「我启动过容器」。简历不能写 Kafka。

6. **多进程 ≠ 微服务。**  
   NovelMind FastAPI + agent-service、PetCare 前后端分离，都不是 Spring Cloud。Java 岗用 Python 拆服务是硬塞。

7. **不要在脏分支上开 JD 分支。**  
   当时 `novel-mind-new` 停在 `codex/cleanup-effective-code`。JD 分支从 `master` worktree 开，避免把无关清理提交混进面试弹药。

8. **测试必须断言行为，不能只 assert import。**  
   LangChain 第一次 import 就要 20s+；如果测试只检查模块能加载，等于 PPT。要断言切块数量和 metadata。

9. **分支永不合并 master。**  
   合并会污染主线叙事，也把「为这个 JD 加的适配器」变成产品默认，后续岗位说不清。面试 `git checkout` 即可。

10. **机器过 70 ≠ 能投。**  
    72 WARN 仍缺 Kafka / Milvus / Java 微服务，那是岗位底座。会审 Tech 会打第一项目不对口。所以放弃网申。

---

## 6. 面试怎么演示（只演示已提交的）

```bash
# Redis
git -C D:\ADLINK\Myproject\novel-mind-new fetch origin
git -C D:\ADLINK\Myproject\novel-mind-jd-focus checkout feat/jd-redis-focus
cd backend && python -m pytest tests/test_retrieval_cache.py -q

# LangChain
git checkout feat/jd-langchain-focus
python -m pytest tests/test_langchain_ingest.py -q
```

话术边界：

- 可以说：检索链加了 Redis 协议缓存；入库切分用了 LangChain splitter。
- 不可以说：用过 Milvus 集群、Kafka 异步推理、Spring Cloud 微服务。

---

## 7. 固定产出（以后每次开分支都要有）

1. 可运行实现  
2. 带行为断言的测试 + 至少 1 个量化指标  
3. commit + 远程分支（不合并 master）  
4. 简历项目经历改写稿  
5. **本类文档：Why、步骤、坑、演示命令**（交给用户看）
