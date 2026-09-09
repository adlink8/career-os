# -*- coding: utf-8 -*-
"""Generate well-spaced 1-page A4 PDF resumes for AISpeech (思必驰) target roles.
Constraints:
1. 基本信息 (一排一个): 出生年月, 性别, 学历, 专业.
2. AI 技能补充到主要技能中首位.
3. No timelines (时间线已删).
4. Strictly 1 page A4 with balanced ~92% vertical spread.
"""
import os
import shutil
import subprocess
import sys

OUT_DIR = r"D:\ADLINK\Myproject\career-os\data\cv\final"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORTRAIT_PATH = "portrait.jpg"

HTML_DEVOPS_PHOTO = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>张三 - 研发效能与质量平台工程师</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 0;
  }}
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Microsoft YaHei", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1E293B;
    background: #FFFFFF;
    width: 210mm;
    height: 297mm;
    overflow: hidden;
    display: flex;
    margin: 0 auto;
  }}
  .sidebar {{
    width: 65mm;
    height: 297mm;
    background-color: #3E4D5E;
    color: #FFFFFF;
    padding: 15mm 6mm 14mm 7mm;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }}
  .name {{
    font-size: 28px;
    font-weight: bold;
    letter-spacing: 2px;
    color: #FFFFFF;
    margin-bottom: 4px;
  }}
  .intent {{
    font-size: 11.5px;
    color: #E2E8F0;
    margin-bottom: 14px;
    line-height: 1.45;
  }}
  .photo-box {{
    width: 100%;
    display: flex;
    justify-content: flex-start;
    margin-bottom: 14px;
  }}
  .photo-img {{
    width: 45mm;
    height: 58mm;
    object-fit: cover;
    border-radius: 2px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    background-color: #2D3748;
  }}
  .side-sec-title {{
    font-size: 12.5px;
    font-weight: bold;
    color: #FFFFFF;
    margin-top: 13px;
    margin-bottom: 6px;
    letter-spacing: 1px;
    padding-bottom: 2.5px;
    border-bottom: 1.5px solid rgba(255,255,255,0.35);
  }}
  .side-item {{
    font-size: 10px;
    line-height: 1.5;
    color: #F1F5F9;
    margin-bottom: 3.5px;
    word-break: break-word;
  }}
  .side-item b, .side-skill-item b {{
    color: #FFFFFF;
    font-weight: 600;
  }}
  .side-skill-item {{
    font-size: 9.3px;
    line-height: 1.45;
    color: #F8FAFC;
    margin-bottom: 6.5px;
    word-break: break-word;
    text-align: justify;
  }}
  .main {{
    width: 145mm;
    height: 297mm;
    padding: 14mm 10mm 13mm 10mm;
    display: flex;
    flex-direction: column;
    background: #FFFFFF;
  }}
  .sec-ribbon {{
    background: #DDE3EA;
    color: #1E293B;
    font-size: 13px;
    font-weight: bold;
    padding: 4.5px 12px;
    border-radius: 1px;
    margin-top: 11px;
    margin-bottom: 6.5px;
    letter-spacing: 1px;
    display: flex;
    align-items: center;
  }}
  .first-ribbon {{
    margin-top: 0;
  }}
  .bullet-item {{
    font-size: 9.9px;
    line-height: 1.52;
    color: #334155;
    margin-bottom: 5px;
    position: relative;
    padding-left: 11px;
    text-align: justify;
  }}
  .bullet-item::before {{
    content: "■";
    position: absolute;
    left: 0;
    top: 2px;
    font-size: 6.8px;
    color: #475569;
  }}
  .bullet-item b {{
    color: #0F172A;
    font-weight: bold;
  }}
  .proj-title-row {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 11.8px;
    font-weight: bold;
    color: #0F172A;
    margin-top: 8.5px;
    margin-bottom: 2.5px;
  }}
  .proj-github {{
    font-size: 8.8px;
    color: #1D4ED8;
    font-family: 'Consolas', monospace;
    font-weight: normal;
    text-decoration: none;
    white-space: nowrap;
    flex-shrink: 0;
  }}
  .proj-duty {{
    font-size: 9.4px;
    line-height: 1.42;
    color: #475569;
    margin-bottom: 4.5px;
    padding-left: 2px;
  }}
</style>
</head>
<body>

  <!-- LEFT SIDEBAR -->
  <aside class="sidebar">
    <div class="name">张三</div>
    <div class="intent">求职意向：研发效能与质量平台工程师<br>目标城市：苏州 | 2027届校招/实习</div>

    <div class="photo-box">
      <img class="photo-img" src="{PORTRAIT_PATH}" alt="证件照">
    </div>

    <div class="side-sec-title">联系方式</div>
    <div class="side-item"><b>电 话：</b>13800138000</div>
    <div class="side-item"><b>邮 箱：</b>zhangsan@example.com</div>
    <div class="side-item"><b>GitHub：</b>github.com/adlink8</div>

    <div class="side-sec-title">基本信息</div>
    <div class="side-item"><b>出生年月：</b>2003年</div>
    <div class="side-item"><b>性 别：</b>男</div>
    <div class="side-item"><b>学 历：</b>本科</div>
    <div class="side-item"><b>专 业：</b>计算机科学与技术</div>

    <div class="side-sec-title">主要技能</div>
    <div class="side-skill-item">▪ <b>AI 辅助研发与测试：</b>掌握 Codex、Claude Code 与 AI Agent 工作流，运用大模型辅助生成测试用例、代码重构与质量门禁自检。</div>
    <div class="side-skill-item">▪ <b>自动化测试体系：</b>掌握 Pytest 单元/契约/集成测试套件构建与 Playwright E2E 浏览器自动化，推行 Mock 边界隔离。</div>
    <div class="side-skill-item">▪ <b>CI 门禁攻防与自检：</b>推行“门禁逻辑自测”套件；科学回标真实覆盖率，建立依赖漏洞 CVE 显式豁免规则。</div>
    <div class="side-skill-item">▪ <b>工具链与流程标准化：</b>自研命令行提效工具集；推进结构化研发流程规范，把代码静态巡检规则代码化。</div>
    <div class="side-skill-item">▪ <b>Linux / 容器与排障：</b>掌握 Ubuntu/WSL2 系统诊断与 Docker 容器隔离，具备 Wireshark 深度抓包网络排障能力。</div>
    <div class="side-skill-item">▪ <b>数据治理与通信协议：</b>掌握 MQTT 异步消息通信机制，以及 SQLite 复合索引调优、触发器防篡改与外键约束。</div>
  </aside>

  <!-- RIGHT MAIN AREA -->
  <main class="main">
    
    <!-- 个人概述 -->
    <div class="sec-ribbon first-ribbon">个人概述</div>
    <div class="bullet-item"><b>学术背景与目标：</b>常州大学计算机科学与技术本科在读（2027届），专注研发效能工具链建设、自动化测试框架与工程质量门禁。</div>
    <div class="bullet-item"><b>技术能力与实战：</b>掌握 Python、Linux、Docker 与 GitHub Actions CI/CD 流水线；具备分层自动化测试体系搭建经验（覆盖 Pytest 单元/契约测试与 Playwright E2E 场景）。</div>
    <div class="bullet-item"><b>工程理念与习惯：</b>注重工程规范，主导设计由测试校验的 CI 质量门禁自检机制与 Coverage 实测回标策略，具备扎实的 Linux 底层排障与自动化提效闭环能力。</div>

    <!-- 核心工程与效能经历 -->
    <div class="sec-ribbon">核心工程与效能项目经历</div>

    <!-- 1. NovelMind -->
    <div class="proj-title-row">
      <span>1. NovelMind 持续集成流水线与自动化质量门禁</span>
      <a class="proj-github" href="https://github.com/adlink8/novel-mind">https://github.com/adlink8/novel-mind</a>
    </div>
    <div class="proj-duty">Python / GitHub Actions / Pytest / Playwright / Linux | <b>角色职责：</b>持续集成流水线架构与质量门禁设计</div>
    <div class="bullet-item"><b>CI 质量门体系设计与自检机制：</b>基于 GitHub Actions 搭建自动化 CI 流水线；首创“门禁逻辑自测”套件，针对门禁拦截脚本编写专项验证用例，杜绝因门禁自身缺陷导致发布误报或遗漏。</div>
    <div class="bullet-item"><b>真实度覆盖率治理与安全准入：</b>依据实际系统架构科学回标 Coverage 阈值，拒绝形式主义断言；建立依赖漏洞（CVE）显式豁免机制，规范安全审计留痕。</div>
    <div class="bullet-item"><b>Playwright E2E 抗 Flaky 分层设计：</b>引入 Playwright 构建端到端测试套件，严格划分“Mock 隔离验证前端交互，真实环境验证发布准入”的职责边界，将 CI 偶发误报率（Flaky Test Rate）压降至 0%。</div>
    <div class="bullet-item"><b>增量校验与计算缓存提效：</b>设计基于 Checksum 签名的增量计算缓存机制，使未变更模块复用率达 82%，基准回归测试套件执行耗时由 4.5 分钟降至 1.8 分钟（耗时缩减 60%）。</div>

    <!-- 2. PKS -->
    <div class="proj-title-row">
      <span>2. PKS (pk-core) 自动化测试平台与多源数据治理</span>
      <a class="proj-github" href="https://github.com/adlink8/pk-core">https://github.com/adlink8/pk-core</a>
    </div>
    <div class="proj-duty">Python / Pytest / SQLite / Docker / RESTful | <b>角色职责：</b>自动化测试套件搭建、模块解耦与数据清洗管道开发</div>
    <div class="bullet-item"><b>系统解耦与高覆盖回归测试套件：</b>主导核心模块解耦重构，基于 Pytest 搭建覆盖关键业务路径的自动化测试用例集，重构过程中通过全量测试回归确保系统行为一致，核心模块测试覆盖率达 85%+。</div>
    <div class="bullet-item"><b>多源数据清洗与字段标准化管道：</b>针对多客户端长日志格式不一、时序混乱问题，编写 Python 清洗管道，完成时间戳对齐与凭证 100% 脱敏过滤，数据清洗效率提升 3 倍。</div>
    <div class="bullet-item"><b>存储完整性与查询性能压降：</b>在 SQLite 存储层构建实体与原始文本的关系索引映射，验证悬空率 0.00%（100% 有源可溯）；结合复合索引与防篡改触发器，将多表关联检索延迟由 280ms 压降至 38ms（降低 86.4%）。</div>
    <div class="bullet-item"><b>容器化测试环境标准化：</b>使用 Docker 封装隔离测试套件运行环境，消除开发环境差异带来的非预期报错，实现测试环境一键拉起与秒级销毁。</div>

    <!-- 3. 物联网通信排障 -->
    <div class="proj-title-row">
      <span>3. 物联网通信链路与协议排障实战</span>
      <span class="proj-github">Linux / MQTT / Docker / Wireshark</span>
    </div>
    <div class="proj-duty">Linux (Ubuntu) / MQTT / Docker / Python / Wireshark | <b>角色职责：</b>端到端通信链路部署、协议联调与网络故障定位</div>
    <div class="bullet-item"><b>高可靠消息网关部署：</b>在 Ubuntu 上使用 Docker 容器化部署 MQTT 消息网关，打通终端设备到云端的双向通信链路。</div>
    <div class="bullet-item"><b>深度抓包定位与网络参数调优：</b>针对弱网环境下设备频繁偶发掉线问题，分析 Linux 底层日志并配合 Wireshark 深度抓包，精准定位到 Keepalive 心跳超时与 QoS 配置冲突；调优重试与心跳间隔后，设备掉线重连耗时缩短 70%，通信在线率由 85% 稳定提升至 99.2%。</div>

    <!-- 4. 个人技术博客与自动化发布流水线 -->
    <div class="proj-title-row">
      <span>4. 个人技术博客与自动化发布流水线</span>
      <a class="proj-github" href="https://github.com/adlink8/adlink8.github.io">https://github.com/adlink8/adlink8.github.io</a>
    </div>
    <div class="proj-duty">Hugo / GitHub Actions / Playwright / Markdown | <b>角色职责：</b>站点搭建、CI/CD 自动化流水线与技术沉淀</div>
    <div class="bullet-item"><b>自动化构建与增量发布流水线：</b>基于 GitHub Actions 搭建全自动 CI/CD 发布流水线，优化静态资源打包与缓存策略，单次构建发布耗时从 140 秒压缩至 42 秒（提效 70%）。</div>
    <div class="bullet-item"><b>自动化巡检门禁与深度复盘：</b>配置 Playwright 无头浏览器与死链检测自动化门禁，保障站点 100% 可用性；公开发布 20+ 篇深度技术长文（涵盖 CI 质量门禁设计、RAG 架构演进、网络排障实录），注重工程规范与可复现性。</div>

  </main>

</body>
</html>
"""

HTML_OPENSOURCE_PHOTO = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>张三 - 开源技术研发工程师</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 0;
  }}
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Microsoft YaHei", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1E293B;
    background: #FFFFFF;
    width: 210mm;
    height: 297mm;
    overflow: hidden;
    display: flex;
    margin: 0 auto;
  }}
  .sidebar {{
    width: 65mm;
    height: 297mm;
    background-color: #3E4D5E;
    color: #FFFFFF;
    padding: 15mm 6mm 14mm 7mm;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }}
  .name {{
    font-size: 28px;
    font-weight: bold;
    letter-spacing: 2px;
    color: #FFFFFF;
    margin-bottom: 4px;
  }}
  .intent {{
    font-size: 11.5px;
    color: #E2E8F0;
    margin-bottom: 14px;
    line-height: 1.45;
  }}
  .photo-box {{
    width: 100%;
    display: flex;
    justify-content: flex-start;
    margin-bottom: 14px;
  }}
  .photo-img {{
    width: 45mm;
    height: 58mm;
    object-fit: cover;
    border-radius: 2px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    background-color: #2D3748;
  }}
  .side-sec-title {{
    font-size: 12.5px;
    font-weight: bold;
    color: #FFFFFF;
    margin-top: 13px;
    margin-bottom: 6px;
    letter-spacing: 1px;
    padding-bottom: 2.5px;
    border-bottom: 1.5px solid rgba(255,255,255,0.35);
  }}
  .side-item {{
    font-size: 10px;
    line-height: 1.5;
    color: #F1F5F9;
    margin-bottom: 3.5px;
    word-break: break-word;
  }}
  .side-item b, .side-skill-item b {{
    color: #FFFFFF;
    font-weight: 600;
  }}
  .side-skill-item {{
    font-size: 9.3px;
    line-height: 1.45;
    color: #F8FAFC;
    margin-bottom: 6.5px;
    word-break: break-word;
    text-align: justify;
  }}
  .main {{
    width: 145mm;
    height: 297mm;
    padding: 14mm 10mm 13mm 10mm;
    display: flex;
    flex-direction: column;
    background: #FFFFFF;
  }}
  .sec-ribbon {{
    background: #DDE3EA;
    color: #1E293B;
    font-size: 13px;
    font-weight: bold;
    padding: 4.5px 12px;
    border-radius: 1px;
    margin-top: 11px;
    margin-bottom: 6.5px;
    letter-spacing: 1px;
    display: flex;
    align-items: center;
  }}
  .first-ribbon {{
    margin-top: 0;
  }}
  .bullet-item {{
    font-size: 9.9px;
    line-height: 1.52;
    color: #334155;
    margin-bottom: 5px;
    position: relative;
    padding-left: 11px;
    text-align: justify;
  }}
  .bullet-item::before {{
    content: "■";
    position: absolute;
    left: 0;
    top: 2px;
    font-size: 6.8px;
    color: #475569;
  }}
  .bullet-item b {{
    color: #0F172A;
    font-weight: bold;
  }}
  .proj-title-row {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 11.8px;
    font-weight: bold;
    color: #0F172A;
    margin-top: 8.5px;
    margin-bottom: 2.5px;
  }}
  .proj-github {{
    font-size: 8.8px;
    color: #1D4ED8;
    font-family: 'Consolas', monospace;
    font-weight: normal;
    text-decoration: none;
    white-space: nowrap;
    flex-shrink: 0;
  }}
  .proj-duty {{
    font-size: 9.4px;
    line-height: 1.42;
    color: #475569;
    margin-bottom: 4.5px;
    padding-left: 2px;
  }}
</style>
</head>
<body>

  <!-- LEFT SIDEBAR -->
  <aside class="sidebar">
    <div class="name">张三</div>
    <div class="intent">求职意向：开源技术研发工程师<br>目标城市：苏州 | 2027届校招/实习</div>

    <div class="photo-box">
      <img class="photo-img" src="{PORTRAIT_PATH}" alt="证件照">
    </div>

    <div class="side-sec-title">联系方式</div>
    <div class="side-item"><b>电 话：</b>13800138000</div>
    <div class="side-item"><b>邮 箱：</b>zhangsan@example.com</div>
    <div class="side-item"><b>GitHub：</b>github.com/adlink8</div>

    <div class="side-sec-title">基本信息</div>
    <div class="side-item"><b>出生年月：</b>2003年</div>
    <div class="side-item"><b>性 别：</b>男</div>
    <div class="side-item"><b>学 历：</b>本科</div>
    <div class="side-item"><b>专 业：</b>计算机科学与技术</div>

    <div class="side-sec-title">主要技能</div>
    <div class="side-skill-item">▪ <b>AI 辅助工程与智能体：</b>掌握 Codex、Claude Code 与 Agent 工作流辅助复杂架构重构，深度实现 Model Context Protocol (MCP) 标准工具开发。</div>
    <div class="side-skill-item">▪ <b>开源协同与版本控制：</b>严格遵循 Git Flow 分支策略、Conventional Commits 规范与 SemVer 语义化发布。</div>
    <div class="side-skill-item">▪ <b>开放协议与生态服务：</b>掌握 Model Context Protocol (MCP) 开放标准，配合 FastAPI 提供服务与工具暴露。</div>
    <div class="side-skill-item">▪ <b>代码分析与架构设计：</b>掌握 Python AST 静态语法树解析，构建自研 SQLite Unified IR 统一中间表示。</div>
    <div class="side-skill-item">▪ <b>核心架构与性能优化：</b>掌握 Python 模块化设计、异步并发与数据结构，具备增量缓存与索引查询调优实践。</div>
    <div class="side-skill-item">▪ <b>开发者体验 (DevEx)：</b>善于输出架构决策记录 (ADR)、Mermaid 架构图、Runbook 与 Docker 容器化方案。</div>
  </aside>

  <!-- RIGHT MAIN AREA -->
  <main class="main">
    
    <!-- 个人概述 -->
    <div class="sec-ribbon first-ribbon">个人概述</div>
    <div class="bullet-item"><b>学术背景与定位：</b>常州大学计算机科学与技术本科在读（2027届），深耕开源系统研发、开放协议架构与规范化社区工程。</div>
    <div class="bullet-item"><b>核心研发与开源：</b>主导架构并开源 <b>Personal Knowledge & Intelligence System (pk-core)</b> 与 <b>CodeAtlas (code-map)</b> 代码拓扑引擎；深度践行 Model Context Protocol (MCP) 与 FastAPI 开放标准协议。</div>
    <div class="bullet-item"><b>DevEx 与工程规范：</b>严格遵循 Conventional Commits、Git Flow 与 SemVer 语义化发布；坚持撰写 5 份 ADR 架构决策记录、基准评测 Benchmark 与全流程技术文档。</div>

    <!-- 核心开源项目经历 -->
    <div class="sec-ribbon">核心开源研发经历</div>

    <!-- 1. PKS -->
    <div class="proj-title-row">
      <span>1. PKS (pk-core) 开源个人知识与智能基础设施</span>
      <a class="proj-github" href="https://github.com/adlink8/pk-core">https://github.com/adlink8/pk-core</a>
    </div>
    <div class="proj-duty">Python / SQLite / MCP / Docker / FastAPI / Chroma | <b>角色职责：</b>独立开源发起人与核心研发者</div>
    <div class="bullet-item"><b>分层 SSOT 开源架构设计：</b>针对多端对话数据碎片化痛点，设计确定性内容哈希去重机制与单一事实源（SSOT SQLite）存储架构，实现多数据源的规范化归一管理。</div>
    <div class="bullet-item"><b>接入 Model Context Protocol (MCP) 开放标准：</b>基于标准 MCP 规范实现本地服务栈与工具暴露，配合 FastAPI 提供标准 REST 接口，成功将私有知识库解耦为多端智能体的上下文基座。</div>
    <div class="bullet-item"><b>底层存储设计与查询优化：</b>在 SQLite 存储层构建实体与原始文本的关系索引映射，结合复合索引与防篡改触发器设计，将多表关联查询延迟由 280ms 压降至 38ms（降幅 86.4%），悬空率保持 0.00%。</div>
    <div class="bullet-item"><b>开发者体验 (DevEx) 与环境标准化：</b>提供 Docker 容器化一键部署方案与详细中英文设计文档（包含架构图、数据流向与 Runbook）；配套自动化测试套件与前置提交检查，保障外部贡献者开箱即用。</div>

    <!-- 2. NovelMind -->
    <div class="proj-title-row">
      <span>2. NovelMind 开源长文本分层检索系统</span>
      <a class="proj-github" href="https://github.com/adlink8/novel-mind">https://github.com/adlink8/novel-mind</a>
    </div>
    <div class="proj-duty">Python / FastAPI / PostgreSQL / ChromaDB | <b>角色职责：</b>核心研发者，主导分层建模算法研发与性能调优</div>
    <div class="bullet-item"><b>多粒度分层数据建模与决策记录：</b>打破传统单一固定切块方案，设计 L0~L4 五级递进式数据抽象模型（原文证据 → 场景事实 → 章节状态 → 卷纲要 → 全书世界观）；跨章节长程关联实体漏检率降低 45%；撰写 5 份 ADR 决策记录明确工程权衡边界。</div>
    <div class="bullet-item"><b>增量计算优化与缓存策略：</b>针对长文本重复解析的计算开销问题，设计基于 Checksum 签名的增量校验机制，使未变更内容复用率达 82%，基准回归测试执行耗时从 4.5 分钟降至 1.8 分钟（耗时缩减 60%）。</div>
    <div class="bullet-item"><b>开源评测基准 Benchmark 构建：</b>构建覆盖 50+ 个长程复杂场景的基准评测数据集，实测有效解决跨章节长程关联信息漏检问题，并将评测场景接入持续集成流程防性能退化。</div>

    <!-- 3. CodeAtlas -->
    <div class="proj-title-row">
      <span>3. CodeAtlas (code-map) 开源代码拓扑与智能体引擎</span>
      <a class="proj-github" href="https://github.com/adlink8/code-map">https://github.com/adlink8/code-map</a>
    </div>
    <div class="proj-duty">Python / AST / SQLite / MCP / Playwright / CLI | <b>角色职责：</b>开源项目发起人与架构设计</div>
    <div class="bullet-item"><b>AST 静态依赖拓扑与 Unified IR 引擎：</b>基于 Python 标准库 AST 解析代码符号依赖，构建自有的 SQLite Unified IR 统一中间表示；支持全库符号跨文件追踪与变更影响面（Impact Analysis）推理。</div>
    <div class="bullet-item"><b>Model Context Protocol (MCP) 开放服务集成：</b>基于标准 stdio JSON-RPC 实现 MCP 协议服务端，向各类智能体开放 6 项只读分析工具（inspect_symbol, impact_analysis, query_graph 等），符号依赖查询延迟 < 25ms。</div>
    <div class="bullet-item"><b>运行时追踪摄入与端到端质量保障：</b>支持 AppMap 与 VizTracer 运行时链路数据摄入，将静态 AST 与运行时调用频次及耗时指标融合；配置零依赖轻量本地 Web 架构视图与 Playwright E2E 端到端测试，自动化测试覆盖率达 88%+。</div>

    <!-- 4. 技术博客 -->
    <div class="proj-title-row">
      <span>4. 个人技术博客与工程文档沉淀</span>
      <a class="proj-github" href="https://github.com/adlink8/adlink8.github.io">https://github.com/adlink8/adlink8.github.io</a>
    </div>
    <div class="proj-duty">Hugo / GitHub Actions / CI/CD / Markdown | <b>角色职责：</b>技术博主与开源文档创作者</div>
    <div class="bullet-item"><b>全自动 CI/CD 构建与持续发布流水线：</b>基于 GitHub Actions 搭建自动化发布流水线，配置 Webhook 与增量构建策略，站点构建发布耗时从 140 秒压缩至 42 秒（提效 70%）。</div>
    <div class="bullet-item"><b>自动化巡检门禁与开源文档沉淀：</b>配置自动化死链检测与页面构建检查门禁，全站可访问性保持 100%；公开发布 20+ 篇深度技术复盘与架构长文（涵盖 MCP 协议设计、RAG 向量检索优化、Linux 协议排障），秉持开源利他精神沉淀工程实践。</div>

  </main>

</body>
</html>
"""

def generate_pdf(html_content, html_name, pdf_name):
    os.makedirs(OUT_DIR, exist_ok=True)
    html_path = os.path.join(OUT_DIR, html_name)
    pdf_path = os.path.join(OUT_DIR, pdf_name)
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated HTML: {html_path}")
    
    cmd = [
        EDGE_EXE,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path
    ]
    subprocess.run(cmd, check=True)
    print(f"Generated PDF: {pdf_path}")
    return pdf_path

def main():
    print("=== Generating Grounded AISpeech Resumes PDF ===")
    p1 = generate_pdf(HTML_DEVOPS_PHOTO, "cv-aispeech-devops.html", "cv-aispeech-devops.pdf")
    p2 = generate_pdf(HTML_OPENSOURCE_PHOTO, "cv-aispeech-opensource.html", "cv-aispeech-opensource.pdf")
    
    # 工业界校招规范命名副本（方便 HR/面试官识别与直接归档）
    named_copies = [
        (p1, os.path.join(OUT_DIR, "张三-研发效能与质量平台工程师-常州大学-2027届.pdf")),
        (p1, os.path.join(OUT_DIR, "张三-研发效能与质量平台工程师-13800138000.pdf")),
        (p2, os.path.join(OUT_DIR, "张三-开源技术研发工程师-常州大学-2027届.pdf")),
        (p2, os.path.join(OUT_DIR, "张三-开源技术研发工程师-13800138000.pdf")),
    ]
    for src, dst in named_copies:
        shutil.copy2(src, dst)
        print(f"Generated HR-standard copy: {dst}")

    # 自动生成预览图片以供快速检查
    try:
        import fitz
        doc1 = fitz.open(p1)
        doc1[0].get_pixmap(dpi=150).save(os.path.join(OUT_DIR, "cv-aispeech-devops-preview.png"))
        doc2 = fitz.open(p2)
        doc2[0].get_pixmap(dpi=150).save(os.path.join(OUT_DIR, "cv-aispeech-opensource-preview.png"))
        print("Updated preview images.")
    except Exception as e:
        print(f"Preview generation warning: {e}")

    print("All PDFs successfully generated and formatted.")

if __name__ == "__main__":
    main()
