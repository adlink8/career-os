# -*- coding: utf-8 -*-
"""Generate 1-page A4 PDF resumes for AISpeech (思必驰) target roles.
Roles:
1. 研发效能与质量平台工程师 (DevOps & Quality Platform)
2. 开源技术研发工程师 (Open Source R&D)

Formats:
- Dual-column Photo Edition (双栏侧栏标准版式 · 带证件照 · 100% 模板复刻)
- Clean ATS Edition (标准单栏极简商务版 · ATS 友好)
"""
import os
import subprocess
import sys

OUT_DIR = r"D:\ADLINK\Myproject\career-os\data\cv\final"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORTRAIT_PATH = "portrait.jpg"

# ----------------- 1. DEVOPS & QUALITY PLATFORM HTML -----------------
HTML_DEVOPS_PHOTO = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>李硕研 - 研发效能与质量平台工程师</title>
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
    color: #262626;
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
    padding: 13mm 5.5mm 12mm 6.5mm;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }}
  .name {{
    font-size: 26px;
    font-weight: bold;
    letter-spacing: 2px;
    color: #FFFFFF;
    margin-bottom: 3px;
  }}
  .intent {{
    font-size: 11px;
    color: #E2E8F0;
    margin-bottom: 12px;
    line-height: 1.4;
  }}
  .photo-box {{
    width: 100%;
    display: flex;
    justify-content: flex-start;
    margin-bottom: 12px;
  }}
  .photo-img {{
    width: 44mm;
    height: 56mm;
    object-fit: cover;
    border-radius: 2px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    background-color: #2D3748;
  }}
  .side-sec-title {{
    font-size: 13px;
    font-weight: bold;
    color: #FFFFFF;
    margin-top: 13px;
    margin-bottom: 6px;
    letter-spacing: 1px;
    padding-bottom: 3px;
    border-bottom: 1.5px solid rgba(255,255,255,0.35);
  }}
  .side-item {{
    font-size: 10.5px;
    line-height: 1.62;
    color: #F1F5F9;
    margin-bottom: 3.5px;
  }}
  .side-item b {{
    color: #FFFFFF;
    font-weight: 600;
  }}
  .side-skill-item {{
    font-size: 9.6px;
    line-height: 1.52;
    color: #F8FAFC;
    margin-bottom: 6px;
  }}
  .side-skill-item b {{
    color: #FFFFFF;
  }}
  .main {{
    width: 145mm;
    height: 297mm;
    padding: 12mm 8.5mm 10mm 8.5mm;
    display: flex;
    flex-direction: column;
    background-color: #FFFFFF;
  }}
  .sec-ribbon {{
    background-color: #DDE3EA;
    color: #2C3E50;
    font-size: 14px;
    font-weight: bold;
    padding: 4.5px 12px;
    border-radius: 1px;
    margin-top: 13px;
    margin-bottom: 7px;
    letter-spacing: 1px;
    display: flex;
    align-items: center;
  }}
  .first-ribbon {{
    margin-top: 0;
  }}
  .bullet-item {{
    font-size: 10.2px;
    line-height: 1.54;
    color: #334155;
    margin-bottom: 5.5px;
    position: relative;
    padding-left: 13px;
    text-align: justify;
  }}
  .bullet-item::before {{
    content: "■";
    position: absolute;
    left: 0;
    top: 1px;
    font-size: 7px;
    color: #334155;
  }}
  .bullet-item b {{
    color: #0F172A;
    font-weight: bold;
  }}
  .proj-title-row {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 12.2px;
    font-weight: bold;
    color: #1E293B;
    margin-top: 10px;
    margin-bottom: 3px;
  }}
  .proj-github {{
    font-size: 9.5px;
    color: #1D4ED8;
    font-family: Consolas, monospace;
    font-weight: normal;
    text-decoration: none;
  }}
  .proj-duty {{
    font-size: 9.6px;
    line-height: 1.45;
    color: #475569;
    margin-bottom: 4.5px;
    padding-left: 2px;
  }}
</style>
</head>
<body>

  <!-- LEFT SIDEBAR -->
  <aside class="sidebar">
    <div class="name">李硕研</div>
    <div class="intent">求职意向：研发效能与质量平台工程师<br>目标城市：苏州 | 2027届校招/实习</div>

    <div class="photo-box">
      <img class="photo-img" src="{PORTRAIT_PATH}" alt="证件照">
    </div>

    <div class="side-sec-title">联系方式</div>
    <div class="side-item"><b>电 话：</b>13091066808</div>
    <div class="side-item"><b>邮 箱：</b>2448366060@qq.com</div>
    <div class="side-item"><b>GitHub：</b>github.com/adlink8</div>

    <div class="side-sec-title">教育背景</div>
    <div class="side-item"><b>常州大学</b> | 计算机科学与技术</div>
    <div class="side-item">全日制本科 | 2027年6月毕业</div>

    <div class="side-sec-title">主要技能</div>
    <div class="side-skill-item">▪ <b>自动化测试体系：</b>熟练使用 Pytest 构建 280+ 测试模块（覆盖单元/契约/集成/E2E），覆盖率 85%+。</div>
    <div class="side-skill-item">▪ <b>质量门禁与评测：</b>独立设计 13 道 Preflight 强制拦截门禁与三层 Eval Harness 评测框架。</div>
    <div class="side-skill-item">▪ <b>内部 CLI 工具自研：</b>践行 cli-anything 思想，自研命令行工具链，累计 90+ 次实用功能交付。</div>
    <div class="side-skill-item">▪ <b>研发流程标准化：</b>推行 GSD 敏捷研发规范（Spec/Plan/Verify/Audit 闭环），累计 195+ 次实战记录。</div>
    <div class="side-skill-item">▪ <b>Linux / 容器与排障：</b>熟练 Ubuntu/Docker/网络抓包诊断，精通 MQTT 异步通信协议。</div>

    <div class="side-sec-title">竞赛与荣誉</div>
    <div class="side-item">▪ 2024 江苏省职业院校技能大赛 (省级获奖)</div>
    <div class="side-item">▪ 计算机软件著作权 (2 项已获批)</div>
  </aside>

  <!-- RIGHT MAIN AREA -->
  <main class="main">
    
    <!-- 个人概述 -->
    <div class="sec-ribbon first-ribbon">个人概述</div>
    <div class="bullet-item" style="margin-bottom:8px;">
      计算机科学与技术本科在读。聚焦于<b>研发效能工具链建设、自动化测试框架与工程质量门禁</b>。熟练掌握 Python、Linux、Docker 与 Git 工作流；具备内部 CLI 开发者工具自研与流程标准化推进能力；主导搭建过覆盖 280+ 模块的自动化测试体系与 13 道 Preflight 质量拦截门禁；注重测试覆盖率、流水线稳定性与自动化提效。
    </div>

    <!-- 核心项目经历 -->
    <div class="sec-ribbon">核心工程与项目经历</div>
    
    <!-- Project 1: PKS 质量保障 -->
    <div class="proj-title-row">
      <span>PKS (pk-core) 自动化测试平台与质量门禁系统</span>
      <span class="proj-github">🔗 github.com/adlink8/pk-core</span>
    </div>
    <div class="proj-duty"><b>角色职责：</b>质量与效能负责人，主导测试体系设计、代码质量门禁开发及测试数据治理。(2026/06-至今)</div>
    <div class="bullet-item"><b>多层级自动化测试架构搭建：</b>基于 Pytest 构建涵盖<b>单元测试、契约测试、集成测试、端到端 (E2E) 及安全审计</b>的全套测试体系，编写覆盖 <b>280+ 个测试模块</b>，核心模块代码覆盖率达到 <b>85%+</b>。</div>
    <div class="bullet-item"><b>三层 Eval Harness 评测把关：</b>设计并实施面向抽取与检索的三层评测体系（Recall@K、忠实度评估与金标回归集），引入<b>金丝雀灰度（Canary）与版本回滚机制</b>，确保发布与模型更新零质量衰退。</div>
    <div class="bullet-item"><b>强制质量门禁 (Preflight Gates)：</b>设计落地 <b>13 道前置强制准入门禁</b>，在代码提交与入库前自动执行 Schema 校验、外键约束排查、凭证脱敏与静态检查，提交流程中 <b>100% 拦截</b>悬空数据与异常外键。</div>
    <div class="bullet-item"><b>数据血缘与质量溯源保障：</b>在 SQLite 存储层构建 <b>14,031 条</b>结论与源文本的关系映射表，实现数据悬空率 <b>0.00%</b>（结论 100% 有据可溯）；设计存储层触发器防范历史数据误删改。</div>
    <div class="bullet-item"><b>容器化测试环境标准化：</b>使用 Docker 封装隔离运行环境，消除跨环境依赖差异，实现测试套件一键初始化，自动化测试环境拉起耗时减少 <b>60%</b>。</div>

    <!-- Project 2: 研发流程标准化 -->
    <div class="proj-title-row" style="margin-top:10px;">
      <span>研发流程标准化 (GSD) 与内部 CLI 开发者工具链</span>
      <span class="proj-github">🔗 Career OS 效能实践</span>
    </div>
    <div class="proj-duty"><b>角色职责：</b>工程效能架构与工具链研发，负责内部开发者提效与研发流程标准化。(2026/01-至今)</div>
    <div class="bullet-item"><b>内部 CLI 工具矩阵研发：</b>践行 cli-anything 工具化思想，自研开发多款命令行提效工具（如 pk-sync 数据归一化、pk-ku 状态机管理、rag-search 混合检索引擎，累计 <b>90+ 次实用交付</b>），减少 70% 重复性手工操作。</div>
    <div class="bullet-item"><b>研发流程标准化推进 (GSD 闭环)：</b>推行基于“目标明确 → 架构契约 (Spec) → 里程碑实施 (Plan) → 独立验证 (Verify) → 闭环审计 (Audit)”的研发流程（<b>累计实践 195+ 次</b>），建立结构化 Checklists，显著降低失误率。</div>
    <div class="bullet-item"><b>持续集成与静态质量检查：</b>接入 GitHub Actions 构建自动化流水线，配置静态代码检查、模式验证与引用完整性扫描，确保工程配置与知识体系零断链。</div>

    <!-- 实践与排障经历 -->
    <div class="sec-ribbon">系统联调与排障实战</div>
    <div class="exp-header" style="display:flex;justify-content:space-between;font-size:11px;font-weight:bold;color:#1E293B;margin-top:2px;margin-bottom:4px;">
      <span>物联网数据链路与系统排障 (Linux / MQTT / Docker / Python)</span>
      <span>2024 - 2025</span>
    </div>
    <div class="bullet-item"><b>高可靠通信链路调试：</b>在 Ubuntu 上使用 Docker 容器化部署 MQTT 消息网关，打通终端设备到云端的双向通信链路。</div>
    <div class="bullet-item"><b>抓包排障与参数调优：</b>针对设备偶发频繁离线问题，通过分析 Linux 系统底层日志与 Wireshark 抓包，准确定位到网络 Keepalive 心跳超时与 QoS 配置冲突，优化后使通信稳定在线率由 <b>85% 提升至 99%</b>。</div>

  </main>

</body>
</html>
"""

# ----------------- 2. OPEN SOURCE R&D HTML -----------------
HTML_OPENSOURCE_PHOTO = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>李硕研 - 开源技术研发工程师</title>
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
    color: #262626;
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
    padding: 13mm 5.5mm 12mm 6.5mm;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }}
  .name {{
    font-size: 26px;
    font-weight: bold;
    letter-spacing: 2px;
    color: #FFFFFF;
    margin-bottom: 3px;
  }}
  .intent {{
    font-size: 11px;
    color: #E2E8F0;
    margin-bottom: 12px;
    line-height: 1.4;
  }}
  .photo-box {{
    width: 100%;
    display: flex;
    justify-content: flex-start;
    margin-bottom: 12px;
  }}
  .photo-img {{
    width: 44mm;
    height: 56mm;
    object-fit: cover;
    border-radius: 2px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    background-color: #2D3748;
  }}
  .side-sec-title {{
    font-size: 13px;
    font-weight: bold;
    color: #FFFFFF;
    margin-top: 13px;
    margin-bottom: 6px;
    letter-spacing: 1px;
    padding-bottom: 3px;
    border-bottom: 1.5px solid rgba(255,255,255,0.35);
  }}
  .side-item {{
    font-size: 10.5px;
    line-height: 1.62;
    color: #F1F5F9;
    margin-bottom: 3.5px;
  }}
  .side-item b {{
    color: #FFFFFF;
    font-weight: 600;
  }}
  .side-skill-item {{
    font-size: 9.6px;
    line-height: 1.52;
    color: #F8FAFC;
    margin-bottom: 6px;
  }}
  .side-skill-item b {{
    color: #FFFFFF;
  }}
  .main {{
    width: 145mm;
    height: 297mm;
    padding: 12mm 8.5mm 10mm 8.5mm;
    display: flex;
    flex-direction: column;
    background-color: #FFFFFF;
  }}
  .sec-ribbon {{
    background-color: #DDE3EA;
    color: #2C3E50;
    font-size: 14px;
    font-weight: bold;
    padding: 4.5px 12px;
    border-radius: 1px;
    margin-top: 13px;
    margin-bottom: 7px;
    letter-spacing: 1px;
    display: flex;
    align-items: center;
  }}
  .first-ribbon {{
    margin-top: 0;
  }}
  .bullet-item {{
    font-size: 10.2px;
    line-height: 1.54;
    color: #334155;
    margin-bottom: 5.5px;
    position: relative;
    padding-left: 13px;
    text-align: justify;
  }}
  .bullet-item::before {{
    content: "■";
    position: absolute;
    left: 0;
    top: 1px;
    font-size: 7px;
    color: #334155;
  }}
  .bullet-item b {{
    color: #0F172A;
    font-weight: bold;
  }}
  .proj-title-row {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 12.2px;
    font-weight: bold;
    color: #1E293B;
    margin-top: 10px;
    margin-bottom: 3px;
  }}
  .proj-github {{
    font-size: 9.5px;
    color: #1D4ED8;
    font-family: Consolas, monospace;
    font-weight: normal;
    text-decoration: none;
  }}
  .proj-duty {{
    font-size: 9.6px;
    line-height: 1.45;
    color: #475569;
    margin-bottom: 4.5px;
    padding-left: 2px;
  }}
</style>
</head>
<body>

  <!-- LEFT SIDEBAR -->
  <aside class="sidebar">
    <div class="name">李硕研</div>
    <div class="intent">求职意向：开源技术研发工程师<br>目标城市：苏州 | 2027届校招/实习</div>

    <div class="photo-box">
      <img class="photo-img" src="{PORTRAIT_PATH}" alt="证件照">
    </div>

    <div class="side-sec-title">联系方式</div>
    <div class="side-item"><b>电 话：</b>13091066808</div>
    <div class="side-item"><b>邮 箱：</b>2448366060@qq.com</div>
    <div class="side-item"><b>GitHub：</b>github.com/adlink8</div>

    <div class="side-sec-title">教育背景</div>
    <div class="side-item"><b>常州大学</b> | 计算机科学与技术</div>
    <div class="side-item">全日制本科 | 2027年6月毕业</div>

    <div class="side-sec-title">主要技能</div>
    <div class="side-skill-item">▪ <b>开源协同与版本演进：</b>GitHub 深度践行者，累计 1460+ 次提交，精通 Git Flow 与 SemVer 发布。</div>
    <div class="side-skill-item">▪ <b>开放协议与生态集成：</b>率先实现 Model Context Protocol (MCP) 开放标准，提供 8789 端口工具服务。</div>
    <div class="side-skill-item">▪ <b>核心编程与性能攻关：</b>精通 Python 异步高并发、FastAPI，攻坚 Checksum 增量缓存复用 80%+ 计算量。</div>
    <div class="side-skill-item">▪ <b>开发者体验 (DevEx)：</b>提供 100% 完整中英文架构文档、Mermaid 图解与 Docker 一键复现环境。</div>
    <div class="side-skill-item">▪ <b>质量保障与测试基准：</b>熟练使用 Pytest 构建 280+ 测试模块；构建 50+ 复杂场景评测 Benchmark。</div>

    <div class="side-sec-title">竞赛与荣誉</div>
    <div class="side-item">▪ 2024 江苏省职业院校技能大赛 (省级获奖)</div>
    <div class="side-item">▪ 计算机软件著作权 (2 项已获批)</div>
  </aside>

  <!-- RIGHT MAIN AREA -->
  <main class="main">
    
    <!-- 个人概述 -->
    <div class="sec-ribbon first-ribbon">个人概述</div>
    <div class="bullet-item" style="margin-bottom:8px;">
      计算机科学与技术本科在读。深耕<b>开源系统研发、开放协议架构与规范化社区协作</b>。长期在 GitHub 深度践行开源协作，累计沉淀 <b>1,460+ 次 Git 提交与 Issue/PR 协同记录</b>；主导架构并开源 Personal Knowledge & Intelligence System (pk-core) 及 NovelMind 检索系统；熟练掌握 Python、Linux、Docker 与开放生态协议（MCP / RESTful / MQTT）；重视系统可复现性、开发者体验（DevEx）与技术文档建设。
    </div>

    <!-- 核心开源项目经历 -->
    <div class="sec-ribbon">核心开源研发经历</div>
    
    <!-- Project 1: PKS 开源基础设施 -->
    <div class="proj-title-row">
      <span>PKS (pk-core) 开源个人知识与智能基础设施</span>
      <span class="proj-github">🔗 github.com/adlink8/pk-core</span>
    </div>
    <div class="proj-duty"><b>角色职责：</b>独立开源项目发起人与核心研发者，主导 L0~L4 分层 SSOT 架构设计、开放协议接入与性能攻关。(2026/06-至今)</div>
    <div class="bullet-item"><b>L0–L4 分层 SSOT 架构设计：</b>针对多端异构会话数据碎片化痛点，设计统一的确定性哈希去重引擎与单一事实源（SSOT SQLite），构建包含多源数据摄取、9 种认知分类抽取、状态机推进与混合检索引擎的分层开源架构。</div>
    <div class="bullet-item"><b>率先接入 Model Context Protocol (MCP) 开放标准：</b>基于标准 MCP 规范实现本地服务栈（8789 端口提供标准工具暴露，8000 端口提供 REST API），成功将私有知识库挂载为多端智能体的上下文基座。</div>
    <div class="bullet-item"><b>底层存储设计与性能攻关：</b>设计存储层触发器防范历史数据误删改，结合复合索引在 <b>14,031 条</b>事实关系数据上实现 <b>0.00% 悬空率</b>，将跨表关联查询延迟压降至 <b>50ms 以内</b>；引入增量水位线游标（Watermark）避免重复推理。</div>
    <div class="bullet-item"><b>极致的开发者体验 (DevEx) 与可复现工程：</b>提供 Docker 容器化一键部署方案与详细中英文设计文档（架构图、数据流向、环境变量）；配套 <b>280+ 个 Pytest 自动化测试用例</b>（覆盖率 <b>85%+</b>）与 13 道 Preflight 门禁。</div>

    <!-- Project 2: NovelMind -->
    <div class="proj-title-row" style="margin-top:10px;">
      <span>NovelMind 开源长文本分层检索系统</span>
      <span class="proj-github">🔗 github.com/adlink8/novel-mind</span>
    </div>
    <div class="proj-duty"><b>角色职责：</b>核心研发者，负责多尺度分层建模算法研发、性能优化与基准测试集建设。(2026/06-至今)</div>
    <div class="bullet-item"><b>多粒度分层数据建模：</b>打破传统单一固定长度切块方案，设计 L0~L4 五级递进式数据抽象模型（原文证据 → 场景事实 → 章节状态 → 卷纲要 → 全局实体），实现长程语义的无损关联与跨尺度检索。</div>
    <div class="bullet-item"><b>增量计算优化与缓存契约：</b>攻克长文本重复解析算力开销难题，设计基于 Checksum 签名的数据增量校验契约，实现未变更数据 <b>80%+ 的计算结果复用</b>，使大规模文本检索解析速度提升 <b>2 倍以上</b>。</div>
    <div class="bullet-item"><b>开源 Benchmark 基准构建：</b>构建包含 <b>50+ 个长程复杂场景</b>的基准评测数据集，全量接入 CI 测试，以 Precision、Recall@K 与 MRR 客观指标牵引模型迭代，防止版本更新带来的召回衰减。</div>

    <!-- 开源协同与工程实践 -->
    <div class="sec-ribbon">开源工程协作与开发者工具</div>
    <div class="exp-header" style="display:flex;justify-content:space-between;font-size:11px;font-weight:bold;color:#1E293B;margin-top:2px;margin-bottom:4px;">
      <span>Career OS 开发者平台与自动化生态 (Python / Git Flow / Actions)</span>
      <span>2026/01 - 至今</span>
    </div>
    <div class="bullet-item"><b>规范化开源协作流程：</b>严格遵循 Conventional Commits 提交规范与 PR Code Review 机制，沉淀 <b>1,460+ 次 Git 提交记录</b>；推行 GSD 敏捷闭环交付规范（累计 195+ 次），保证版本演进透明可追溯。</div>
    <div class="bullet-item"><b>自研内部 CLI 开发者工具：</b>用 Python 自研系列工程效率工具（pk-sync、pk-ku、rag-search 等，累计 <b>90+ 次实用交付</b>），提供静态依赖分析与自动化构建能力，保障开源仓库的高质量自洽。</div>

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
    print("=== Generating AISpeech Customized Resumes PDF ===")
    p1 = generate_pdf(HTML_DEVOPS_PHOTO, "cv-aispeech-devops.html", "cv-aispeech-devops.pdf")
    p2 = generate_pdf(HTML_OPENSOURCE_PHOTO, "cv-aispeech-opensource.html", "cv-aispeech-opensource.pdf")
    print("All PDFs successfully created.")

if __name__ == "__main__":
    main()
