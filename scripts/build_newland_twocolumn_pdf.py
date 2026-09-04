# -*- coding: utf-8 -*-
"""Generate high-aesthetic Two-Column (左右分栏) A4 1-page DOCX and PDF for cv-newland-customized.
Follows Layout Scheme D (左右分栏):
- A4, 1.2cm margins
- Left Sidebar (5.4cm, #F4F6F9 shaded): Contact, Education, Skills
- Right Main (13.0cm): Summary, Core Projects (PKS, NovelMind) with Testing & QA integration
- Strict 1-page fit
"""
import os
import re
import subprocess
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_LINE_SPACING, WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn

MD_PATH = r"D:\ADLINK\Myproject\career-os\data\cv\cv-newland-customized.md"
OUT_DIR = r"D:\ADLINK\Myproject\career-os\data\cv\final"
DOCX_OUT = os.path.join(OUT_DIR, "cv-newland-twocolumn.docx")
PDF_OUT = os.path.join(OUT_DIR, "cv-newland-twocolumn.pdf")
SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"

EAST_FONT = "微软雅黑"
ASCII_FONT = "Arial"
DARK_BLUE = "1F3864"
GRAY_TAG = "595959"
DARK_TEXT = "262626"
LIGHT_BG = "F4F6F9"

def set_run_font(run, size_pt=9.0, bold=False, color_hex=DARK_TEXT, italic=False):
    run.font.name = ASCII_FONT
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = italic
    if color_hex:
        run.font.color.rgb = RGBColor.from_string(color_hex)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:ascii"), ASCII_FONT)
    rFonts.set(qn("w:hAnsi"), ASCII_FONT)
    rFonts.set(qn("w:eastAsia"), EAST_FONT)

def add_p(container, before_pt=0, after_pt=1.0, line_pt=12.5, align=WD_ALIGN_PARAGRAPH.LEFT):
    p = container.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(before_pt)
    pf.space_after = Pt(after_pt)
    if line_pt:
        pf.line_spacing = Pt(line_pt)
        pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    return p

def add_left_heading(cell, title):
    p = add_p(cell, before_pt=5.0, after_pt=2.0, line_pt=14.0)
    r = p.add_run(title)
    set_run_font(r, size_pt=10.0, bold=True, color_hex=DARK_BLUE)
    pBdr = parse_xml(r'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                     r'<w:bottom w:val="single" w:sz="6" w:space="1" w:color="1F3864"/>'
                     r'</w:pBdr>')
    p._element.get_or_add_pPr().append(pBdr)

def add_right_heading(cell, title):
    p = add_p(cell, before_pt=4.5, after_pt=2.0, line_pt=15.0)
    r = p.add_run(title)
    set_run_font(r, size_pt=11.0, bold=True, color_hex=DARK_BLUE)
    pBdr = parse_xml(r'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                     r'<w:bottom w:val="single" w:sz="8" w:space="2" w:color="1F3864"/>'
                     r'</w:pBdr>')
    p._element.get_or_add_pPr().append(pBdr)

def shade_cell(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:val="clear" w:color="auto" w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                      f'<w:top w:w="{top}" w:type="dxa"/>'
                      f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
                      f'<w:left w:w="{left}" w:type="dxa"/>'
                      f'<w:right w:w="{right}" w:type="dxa"/>'
                      f'</w:tcMar>')
    tcPr.append(tcMar)

def clear_cell_borders(table):
    tblPr = table._tbl.tblPr
    tblBorders = parse_xml(r'<w:tblBorders xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                           r'<w:top w:val="none"/>'
                           r'<w:left w:val="none"/>'
                           r'<w:bottom w:val="none"/>'
                           r'<w:right w:val="none"/>'
                           r'<w:insideH w:val="none"/>'
                           r'<w:insideV w:val="none"/>'
                           r'</w:tblBorders>')
    tblPr.append(tblBorders)

def build_twocolumn():
    doc = Document()
    
    # A4: 21.0 x 29.7 cm, tight margins
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(1.1)
    sec.bottom_margin = Cm(1.1)
    sec.left_margin = Cm(1.2)
    sec.right_margin = Cm(1.2)
    
    # 1. Header (Across full width)
    p_name = add_p(doc, before_pt=0, after_pt=1.0, line_pt=20.0)
    r_name = p_name.add_run("[姓名]")
    set_run_font(r_name, size_pt=18.0, bold=True, color_hex="1A1A1A")
    r_slash = p_name.add_run("  |  ")
    set_run_font(r_slash, size_pt=12.0, color_hex="888888")
    r_intent = p_name.add_run("求职意向：数据分析工程师 / 软件测试  (2027届校招)")
    set_run_font(r_intent, size_pt=10.5, bold=True, color_hex=DARK_BLUE)
    
    p_line = add_p(doc, before_pt=0, after_pt=3.0, line_pt=1.0)
    pBdr = parse_xml(r'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                     r'<w:bottom w:val="single" w:sz="12" w:space="1" w:color="1F3864"/>'
                     r'</w:pBdr>')
    p_line._element.get_or_add_pPr().append(pBdr)
    
    # 2. Two-Column Table
    # Widths: left = 5.6cm, right = 13.0cm (Total = 18.6cm)
    table = doc.add_table(rows=1, cols=2)
    clear_cell_borders(table)
    table.autofit = False
    
    row = table.rows[0]
    left_cell, right_cell = row.cells
    left_cell.width = Cm(5.6)
    right_cell.width = Cm(13.0)
    
    shade_cell(left_cell, LIGHT_BG)
    set_cell_margins(left_cell, top=80, bottom=80, left=140, right=140)
    set_cell_margins(right_cell, top=40, bottom=40, left=180, right=40)
    
    # ------------------ LEFT COLUMN ------------------
    # 联系方式
    add_left_heading(left_cell, "联系方式")
    p = add_p(left_cell, before_pt=1, after_pt=0.5, line_pt=11.5)
    r = p.add_run("📱 电话：[手机号]")
    set_run_font(r, size_pt=8.5, color_hex="333333")
    
    p = add_p(left_cell, before_pt=0.5, after_pt=0.5, line_pt=11.5)
    r = p.add_run("✉️ 邮箱：[邮箱]")
    set_run_font(r, size_pt=8.5, color_hex="333333")
    
    p = add_p(left_cell, before_pt=0.5, after_pt=0.5, line_pt=11.5)
    r = p.add_run("🐙 GitHub：github.com/your-username")
    set_run_font(r, size_pt=8.0, color_hex="333333")
    
    p = add_p(left_cell, before_pt=0.5, after_pt=2.0, line_pt=11.5)
    r = p.add_run("📍 意向城市：南京 / 苏州 / 无锡")
    set_run_font(r, size_pt=8.5, color_hex="333333")
    
    # 教育背景
    add_left_heading(left_cell, "教育背景")
    p = add_p(left_cell, before_pt=1, after_pt=0.5, line_pt=12.0)
    r = p.add_run("[毕业院校]")
    set_run_font(r, size_pt=9.0, bold=True, color_hex="1A1A1A")
    set_run_font(r, size_pt=9.0, bold=True, color_hex="1A1A1A")
    
    p = add_p(left_cell, before_pt=0, after_pt=0.5, line_pt=11.5)
    r = p.add_run("计算机科学与技术 (统招本科)")
    set_run_font(r, size_pt=8.0, bold=False, color_hex="333333")
    
    p = add_p(left_cell, before_pt=0, after_pt=2.0, line_pt=11.5)
    r = p.add_run("2027 年 6 月毕业")
    set_run_font(r, size_pt=8.0, color_hex="555555")
    
    # 专业技能
    add_left_heading(left_cell, "专业技能")
    
    skills = [
        ("Python 数据分析", "精通 Python (Pandas/NumPy)，熟练掌握数据清洗、特征提取、探索性数据分析 (EDA) 与自动化分析脚本。"),
        ("SQL 与数据建模", "精通 SQL 复杂关联、窗口函数与分组聚合；掌握 SQLite/MySQL 触发器与索引优化；了解 Hive/Hadoop。"),
        ("算法与挖掘评估", "掌握文本分类、聚类、余弦相似度；熟练掌握数据质量校验及评估指标 (Precision/Recall/F1/MRR)。"),
        ("自动化测试与工程", "熟练使用 Pytest 编写自动化测试矩阵 (280+ 测试套件)；熟悉 Preflight CI/CD 质量门禁拦截机制。"),
        ("系统与容器运维", "熟练使用 Linux、Docker 容器化部署、Git 版本协作与 Shell 自动化运维。")
    ]
    
    for s_title, s_desc in skills:
        p = add_p(left_cell, before_pt=2.0, after_pt=0.5, line_pt=11.5)
        r_t = p.add_run(f"▪ {s_title}")
        set_run_font(r_t, size_pt=8.5, bold=True, color_hex=DARK_BLUE)
        p_d = add_p(left_cell, before_pt=0, after_pt=1.5, line_pt=11.0)
        r_d = p_d.add_run(s_desc)
        set_run_font(r_d, size_pt=7.8, color_hex="444444")
        
    # ------------------ RIGHT COLUMN ------------------
    # 个人概述
    add_right_heading(right_cell, "个人概述")
    p_sum = add_p(right_cell, before_pt=1.0, after_pt=2.5, line_pt=12.5)
    r_sum = p_sum.add_run(
        "计算机科学与技术本科在读，主攻数据分析、文本数据挖掘与自动化质量评估。熟练使用 Python 与 SQL 进行海量异构数据预处理、探索性数据分析（EDA）、统计建模与指标归因；重视数据质量治理、血缘溯源与自动化测试防御闭环。"
    )
    set_run_font(r_sum, size_pt=8.5, color_hex="333333")
    
    # 核心项目经历
    add_right_heading(right_cell, "核心项目经历")
    
    # Project 1: PKS
    p_p1 = add_p(right_cell, before_pt=2.5, after_pt=0.5, line_pt=13.5)
    r_p1_t = p_p1.add_run("PKS — AI 交互数据挖掘系统")
    set_run_font(r_p1_t, size_pt=10.0, bold=True, color_hex=DARK_BLUE)
    r_p1_m = p_p1.add_run("  |  Python · SQL (SQLite) · Chroma · REST | github.com/adlink8/pk-core")
    set_run_font(r_p1_m, size_pt=8.0, color_hex=GRAY_TAG)
    
    p_d1 = add_p(right_cell, before_pt=0, after_pt=1.0, line_pt=12.0)
    r_d1_l = p_d1.add_run("个人职责：")
    set_run_font(r_d1_l, size_pt=8.0, bold=True, color_hex="444444")
    r_d1_v = p_d1.add_run("独立负责多源文本清洗挖掘、EDA 探索分析、聚类去重、防篡改规则及自动化质量门禁。")
    set_run_font(r_d1_v, size_pt=8.0, color_hex="555555")
    
    pks_bullets = [
        ("多源数据预处理与质量治理", "针对 28GB 多源异构长对话日志，编写 Python 管道清洗规范化 17.8 万条对话记录，实现敏感凭据 100% 过滤剥离，形成高质量规范样本。"),
        ("探索性分析与主题特征挖掘", "开展 EDA 统计会话轮次、文本长度分布与主题趋势；运用多标签分类与主题聚类，从 40,000+ 候选事实中提炼 7,400+ 核心知识单元与 44,000+ 实体，完成 470+ 组同主题聚类去重。"),
        ("数据血缘溯源与存储防篡改", "在 SQLite 构建 14,031 条结论与原文句子的关系索引映射（悬空率 0.00% 有据可溯）；设计存储层不可变触发器防范历史数据误删改，复合索引优化查询延迟稳定在 50ms 内。"),
        ("自动化测试防御与发布门禁", "基于 Pytest 构建全套测试矩阵，覆盖数据清洗一致性、数据库并发测试与接口契约校验，覆盖率达 85%+；设计 Preflight 13 道强制门禁，入库前自动拦截非法数据。")
    ]
    for b_title, b_text in pks_bullets:
        p_b = add_p(right_cell, before_pt=0.5, after_pt=1.0, line_pt=12.0)
        r_dot = p_b.add_run("•  ")
        set_run_font(r_dot, size_pt=8.2, bold=True, color_hex=DARK_BLUE)
        r_lbl = p_b.add_run(b_title + "：")
        set_run_font(r_lbl, size_pt=8.2, bold=True, color_hex="1A1A1A")
        r_val = p_b.add_run(b_text)
        set_run_font(r_val, size_pt=8.0, color_hex="333333")
        
    # Project 2: NovelMind
    p_p2 = add_p(right_cell, before_pt=3.5, after_pt=0.5, line_pt=13.5)
    r_p2_t = p_p2.add_run("NovelMind — 长文本分层检索系统")
    set_run_font(r_p2_t, size_pt=10.0, bold=True, color_hex=DARK_BLUE)
    r_p2_m = p_p2.add_run("  |  Python · FastAPI · PostgreSQL · ChromaDB | github.com/adlink8/novel-mind")
    set_run_font(r_p2_m, size_pt=8.0, color_hex=GRAY_TAG)
    
    p_d2 = add_p(right_cell, before_pt=0, after_pt=1.0, line_pt=12.0)
    r_d2_l = p_d2.add_run("个人职责：")
    set_run_font(r_d2_l, size_pt=8.0, bold=True, color_hex="444444")
    r_d2_v = p_d2.add_run("独立负责长文本分层数据建模、检索 A/B 实验设计、基准测试集构建及指标自动化评测。")
    set_run_font(r_d2_v, size_pt=8.0, color_hex="555555")
    
    nm_bullets = [
        ("长文本多粒度分层建模", "针对 10 万字+ 复杂长篇文本，打破单一粗暴切块，构建 L0~L4 五级递进式数据模型（原文证据 → 场景事实 → 章节状态 → 卷纲要 → 全书世界观），实现跨尺度信息因果关联。"),
        ("量化评测体系与 A/B 对比实验", "构建 50+ 个长程场景（跨章节人物演化、时间线、伏笔）基准测试集；对比不同切块粒度与向量策略，通过 Recall@K、MRR 及相关性打分指标驱动策略迭代。"),
        ("自动化回归与增量计算优化", "针对检索失真案例建立错误归因分类漏斗；接入 Pytest 自动化回归测试集，防止调优退化；引入 Checksum 增量校验，未变更部分实现 80%+ 计算复用，大幅减少耗时。")
    ]
    for b_title, b_text in nm_bullets:
        p_b = add_p(right_cell, before_pt=0.5, after_pt=1.0, line_pt=12.0)
        r_dot = p_b.add_run("•  ")
        set_run_font(r_dot, size_pt=8.2, bold=True, color_hex=DARK_BLUE)
        r_lbl = p_b.add_run(b_title + "：")
        set_run_font(r_lbl, size_pt=8.2, bold=True, color_hex="1A1A1A")
        r_val = p_b.add_run(b_text)
        set_run_font(r_val, size_pt=8.0, color_hex="333333")

    os.makedirs(OUT_DIR, exist_ok=True)
    doc.save(DOCX_OUT)
    print(f"Generated Two-Column DOCX: {DOCX_OUT}")
    
    # Convert to PDF
    cmd = [SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", OUT_DIR, DOCX_OUT]
    subprocess.run(cmd, check=True)
    print(f"Generated Two-Column PDF: {PDF_OUT}")

if __name__ == "__main__":
    build_twocolumn()
