# -*- coding: utf-8 -*-
"""Generate 100% replica of the template layout (双栏侧栏标准版式)
- Rebalances vertical distribution so content comfortably fills the entire 842pt page (ends at ~770pt)
- Generously relaxes upper and middle spacing with breathing room (padding, margins, line-heights)
- Clear, readable 10.5px font with 1.58 line-height
- Eliminates the awkward empty void at the bottom
- Strict A4 1-page fit
"""
import os
import subprocess

OUT_DIR = r"D:\ADLINK\Myproject\career-os\data\cv\final"
HTML_PATH = os.path.join(OUT_DIR, "cv-template-replica.html")
PDF_PATH = os.path.join(OUT_DIR, "cv-newland-photo-edition.pdf")
PORTRAIT_PATH = "portrait.jpg"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

HTML_TEMPLATE = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>求职简历 - 模板预览</title>
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

  /* ================= LEFT SIDEBAR ================= */
  .sidebar {{
    width: 65mm;
    height: 297mm;
    background-color: #3E4D5E;
    color: #FFFFFF;
    padding: 14mm 5.5mm 12mm 6.5mm;
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
  }}

  .photo-box {{
    width: 100%;
    display: flex;
    justify-content: flex-start;
    margin-bottom: 14px;
  }}

  .photo-img {{
    width: 44mm;
    height: 58mm;
    object-fit: cover;
    border-radius: 2px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    background-color: #2D3748;
  }}

  .side-sec-title {{
    font-size: 13.5px;
    font-weight: bold;
    color: #FFFFFF;
    margin-top: 16px;
    margin-bottom: 7px;
    letter-spacing: 1px;
    position: relative;
    padding-bottom: 3px;
    border-bottom: 1.5px solid rgba(255,255,255,0.35);
  }}

  .side-item {{
    font-size: 10.8px;
    line-height: 1.68;
    color: #F1F5F9;
    margin-bottom: 4px;
  }}

  .side-item b {{
    color: #FFFFFF;
    font-weight: 600;
  }}

  .side-skill-item {{
    font-size: 9.8px;
    line-height: 1.56;
    color: #F8FAFC;
    margin-bottom: 7px;
  }}

  /* ================= RIGHT MAIN AREA ================= */
  .main {{
    width: 145mm;
    height: 297mm;
    padding: 13mm 9mm 12mm 9mm;
    display: flex;
    flex-direction: column;
    background-color: #FFFFFF;
  }}

  .sec-ribbon {{
    background-color: #DDE3EA;
    color: #2C3E50;
    font-size: 14.5px;
    font-weight: bold;
    padding: 5px 12px;
    border-radius: 1px;
    margin-top: 15px;
    margin-bottom: 8px;
    letter-spacing: 1px;
    display: flex;
    align-items: center;
  }}

  .first-ribbon {{
    margin-top: 0;
  }}

  .exp-header {{
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    font-weight: bold;
    color: #1E293B;
    margin-top: 4px;
    margin-bottom: 7px;
  }}

  .exp-header .company {{
    flex: 1;
    margin-left: 10px;
  }}

  .bullet-item {{
    font-size: 10.5px;
    line-height: 1.58;
    color: #334155;
    margin-bottom: 6px;
    position: relative;
    padding-left: 13px;
    text-align: justify;
  }}

  .bullet-item::before {{
    content: "■";
    position: absolute;
    left: 0;
    top: 1px;
    font-size: 7.5px;
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
    font-size: 12.5px;
    font-weight: bold;
    color: #1E293B;
    margin-top: 12px;
    margin-bottom: 3.5px;
  }}

  .proj-github {{
    font-size: 9.8px;
    color: #1D4ED8;
    font-family: Consolas, monospace;
    font-weight: normal;
    text-decoration: none;
  }}

  .proj-duty {{
    font-size: 9.8px;
    line-height: 1.48;
    color: #475569;
    margin-bottom: 5px;
    padding-left: 2px;
  }}

</style>
</head>
<body>

  <!-- LEFT SIDEBAR -->
  <aside class="sidebar">
    <div class="name">[姓名]</div>
    <div class="intent">求职意向：数据分析工程师 / 软件测试</div>

    <div class="photo-box">
      <img class="photo-img" src="{PORTRAIT_PATH}" alt="证件照">
    </div>

    <div class="side-sec-title">联系方式</div>
    <div class="side-item"><b>手 机：</b>[手机号]</div>
    <div class="side-item"><b>邮 箱：</b>[邮箱]</div>
    <div class="side-item"><b>GitHub：</b>github.com/your-username</div>

    <div class="side-sec-title">基本信息</div>
    <div class="side-item"><b>出生年月：</b>XXXX年</div>
    <div class="side-item"><b>性 别：</b>男</div>
    <div class="side-item"><b>学 历：</b>本科</div>
    <div class="side-item"><b>专 业：</b>计算机科学与技术</div>

    <div class="side-sec-title">主要技能</div>
    <div class="side-skill-item">▪ <b>AI 辅助代码工程：</b>熟练运用 OpenAI Codex、Claude Code 与 Agent 工作流辅助重构与开发。</div>
    <div class="side-skill-item">▪ <b>Python / 数据分析：</b>精通 Pandas, NumPy, 熟练数据清洗、EDA 探索分析与脚本编写。</div>
    <div class="side-skill-item">▪ <b>SQL / 数据建模：</b>精通复杂关联、窗口函数与 SQLite 触发器；了解 Hive/Hadoop。</div>
    <div class="side-skill-item">▪ <b>算法与数据挖掘：</b>掌握文本分类、聚类去重、余弦相似度与评估指标 (Recall/MRR/F1)。</div>
    <div class="side-skill-item">▪ <b>自动化测试与门禁：</b>熟练使用 Pytest 构建 280+ 测试矩阵；熟悉 Preflight 门禁拦截。</div>
    <div class="side-skill-item">▪ <b>设备上云与系统运维：</b>精通新大陆 NLECloud 设备接入协议、串口服务器与 Linux/Docker。</div>

    <div class="side-sec-title">个人荣誉</div>
    <div class="side-item">2024 江苏省职业院校技能大赛（省级获奖）</div>
  </aside>

  <!-- RIGHT MAIN AREA -->
  <main class="main">
    
    <!-- 工作经历 -->
    <div class="sec-ribbon first-ribbon">工作经历</div>
    <div class="exp-header">
      <span>2024.06-2025.06</span>
      <span class="company">[实习单位/校企合作项目]</span>
      <span>物联网项目开发实习生</span>
    </div>

    <!-- 工作内容 (高度抽象的设备联通上云与系统集成职责) -->
    <div class="sec-ribbon">工作内容 (设备联通上云与工业系统集成)</div>
    <div class="bullet-item"><b>感知与控制层：异构硬件网络组网与总线配置：</b>负责工业级多参数传感器（环境气象、UWB 定位、RFID、振动测距）与执行机构电气接线；主导 RS-485 Modbus RTU 工业总线与 ZigBee 无线传感器网络的自组网调试，完成从机地址规划与波特率匹配。</div>
    <div class="bullet-item"><b>传输与网关层：边缘网关部署与多源协议转换：</b>负责工业串口服务器（USR-TCP232）、数据采集模块（4150）及 4G 工业通信终端的网络部署；编写协议适配逻辑，实现底层串口 Modbus 二进制数据流与网络层标准 JSON 协议的双向转换与封装。</div>
    <div class="bullet-item"><b>云端接入层：物联网云平台全流程设备上云与反控：</b>严格遵循新大陆物联网云平台（NLECloud）通信规范，完成 $#AT# 握手、设备鉴权与心跳保活；打通 TCP/MQTT 协议通道，实现毫秒级遥测数据上云与基于云端指令的反向控制闭环。</div>
    <div class="bullet-item"><b>运维保障层：上位机监控系统研发与端到端抓包排障：</b>使用 Python (PyQt5) 与 MySQL 开发工业数据监控上位机；负责局域网 IP 网段与交换机 VLAN 划分，运用 Wireshark 抓包深度定位总线冲突、端口占用与无线丢包，系统全流程联调通过率 100%。</div>

    <!-- 核心项目经历 (严格执行用户提供的权威原版文本) -->
    <div class="sec-ribbon">核心项目经历</div>
    
    <!-- Project 1: PKS -->
    <div class="proj-title-row">
      <span>PKS — AI 交互数据挖掘系统</span>
      <span class="proj-github">🔗 https://github.com/adlink8/pk-core</span>
    </div>
    <div class="proj-duty"><b>职务职责：</b>独立负责海量非结构化文本清洗挖掘、探索性数据分析（EDA）、同主题会话聚类去重、数据质量防篡改规则与指标统计分析。(2026/06-至今)</div>
    <div class="bullet-item"><b>多源数据预处理与质量治理：</b>针对 28GB 多源非结构化长对话日志，编写 Python 清洗管道，完成字段标准化、会话时间戳对齐与凭证信息 100% 过滤，形成 17.8 万条高质量规范样本。</div>
    <div class="bullet-item"><b>探索性分析与主题特征挖掘：</b>对清洗后数据开展探索性数据分析（EDA），统计会话轮次、文本长度分布与主题时序趋势；运用文本多标签分类与基于特征的主题聚类，从 40,000+ 候选事实中提炼出 7,400+ 个高密度核心知识单元与 44,000+ 实体，完成 470+ 组同主题事件会话聚类与去重。</div>
    <div class="bullet-item"><b>数据血缘溯源与存储完整性保障：</b>在 SQLite 中构建 14,031 条结论与原始文本句子的关系索引映射，验证悬空率 0.00%（做到结论 100% 有源可溯）；设计存储层触发器防范历史数据误删改，配合复合索引将统计检索延迟压降至 50ms 内。</div>
    <div class="bullet-item"><b>数据资产分析与快照管理：</b>建立“构建 → 校验 → 激活”的周期性数据快照机制，实现数据资产版本化管理，支持秒级异常版本回滚与指标一致性核验。</div>
    <div class="bullet-item"><b>自动化测试与质量门禁：</b>基于 Pytest 构建 280+ 自动化测试用例，覆盖数据一致性、数据库并发测试与接口契约校验，系统覆盖率达 85%+；设计 Preflight 13 道强制门禁，入库前自动拦截非法数据与异常外键。</div>

    <!-- Project 2: NovelMind -->
    <div class="proj-title-row" style="margin-top:12px;">
      <span>NovelMind — 长文本分层检索系统</span>
      <span class="proj-github">🔗 https://github.com/adlink8/novel-mind</span>
    </div>
    <div class="proj-duty"><b>职务职责：</b>独立负责长文本分层数据建模、检索策略 A/B 对比实验设计、基准测试集构建及指标量化评估与归因分析。(2026/06-至今)</div>
    <div class="bullet-item"><b>长文本多粒度分层建模：</b>针对 10 万字+ 复杂长篇文本，打破单一粗暴切块方式，构建 L0~L4 五级递进式数据模型（原文证据 → 场景事实 → 章节状态 → 卷纲要 → 全书世界观），实现跨尺度信息关联分析。</div>
    <div class="bullet-item"><b>量化评测体系与 A/B 对比实验：</b>构建由 50+ 个长程场景（跨章节关系演化、因果时间线、伏笔线索）组成的基准测试集；对比不同切块粒度与向量检索策略，通过 Recall@K、MRR 及相关性打分指标驱动策略选型与参数调优。</div>
    <div class="bullet-item"><b>Bad Case 归因与增量计算优化：</b>针对检索失真案例建立错误归因分类漏斗，针对性迭代过滤规则；引入 Checksum 增量校验契约，实现数据未变更部分 80%+ 的计算结果复用，大幅减少算力与时间开销。</div>
    <div class="bullet-item"><b>自动化回归与质量验证：</b>编写全套自动化回归测试套件，将 50+ 个基准评测场景接入持续集成流程；每次切块参数调整自动执行指标校验，确保检索召回率（Recall@K）与准确率不发生任何性能退化。</div>

  </main>

</body>
</html>
"""

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE)
    print(f"Generated HTML: {HTML_PATH}")
    
    cmd = [
        EDGE_EXE,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_PATH}",
        HTML_PATH
    ]
    subprocess.run(cmd, check=True)
    print(f"Generated PDF: {PDF_PATH}")

if __name__ == "__main__":
    main()
