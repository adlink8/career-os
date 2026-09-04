# AI Agent 运维学习路线(用户差异化方向)

> 来源:综合 LangChain/LlamaIndex 官方文档 + LLMOps 社区实践。
> ⚠️ AI 领域变化快,本路线**每 3 个月需校验一次**(KNOW-03)。

## 路线图

```
阶段 1: 基础(用户部分已具备)
├── ✅ Python(用户熟练)
├── ✅ Docker(用户熟练)
├── ✅ Git(用户熟练)
└── 🔴 LLM 基础概念(Transformer/Token/Prompt)
          ↓
阶段 2: RAG 管道(核心)
├── 🔴 LangChain / LlamaIndex
├── 🔴 向量数据库(Milvus / Pinecone / Chroma)
├── 🔴 Embedding 模型选择
├── 🔴 检索质量优化(rerank / hybrid search)
└── ✅ 用户有 AI-Memory 项目基础(RAG + MCP + Agent)
          ↓
阶段 3: 模型部署
├── 🔴 vLLM / Ollama 本地部署
├── 🔴 推理服务(FastAPI + vLLM)
├── 🔴 GPU 资源管理
└── 🔴 模型量化(GPTQ / AWQ)
          ↓
阶段 4: Agent 平台
├── 🔴 Agent 框架(AutoGen / CrewAI)
├── 🔴 工具调用(Function Calling)
├── 🔴 MCP 协议(用户 AI-Memory 项目已接触)
└── 🔴 多 Agent 协作
          ↓
阶段 5: 可观测性
├── 🔴 LangSmith / LangFuse
├── 🔴 Token 成本监控
└── 🔴 幻觉检测
```

## 用户优势

- **AI-Memory 项目** → Obsidian + MCP + RAG + Agent 完整工具链,直接对口
- 这个项目是用户简历**最大差异化亮点**,skill 推荐时应重点突出

## 优先补齐(按求职紧迫度)

1. **LangChain/LlamaIndex 实战**(1-2 周,面试必备)
2. **向量数据库实操**(Milvus 或 Chroma,1 周)
3. **vLLM/Ollama 本地部署**(2 周,加分项)

## skill 调用提示

- AI 运维岗位**薪资上限高**但**岗位数量少于纯运维**,建议作为**差异化辅线**,不作为唯一主攻
