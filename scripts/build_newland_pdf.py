# -*- coding: utf-8 -*-
"""Generate high-aesthetic 1-page DOCX and PDF for cv-newland-customized.md.
Follows Layout Scheme B:
- A4, precise margins (1.5cm top/bottom, 1.8cm left/right)
- Dark Blue (#1F3864) section headings with bottom border
- Font: Microsoft YaHei (微软雅黑) for East Asia, Arial for Western
- Clean 1-page fit
"""
import os
import re
import subprocess
import sys
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_LINE_SPACING, WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

MD_PATH = r"D:\ADLINK\Myproject\career-os\data\cv\cv-newland-customized.md"
OUT_DIR = r"D:\ADLINK\Myproject\career-os\data\cv\final"
DOCX_OUT = os.path.join(OUT_DIR, "cv-newland-customized.docx")
PDF_OUT = os.path.join(OUT_DIR, "cv-newland-customized.pdf")
SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"

EAST_FONT = "微软雅黑"
ASCII_FONT = "Arial"
DARK_BLUE = "1F3864"
GRAY_TAG = "595959"
DARK_TEXT = "262626"

def set_run_font(run, size_pt=9.5, bold=False, color_hex=DARK_TEXT, italic=False):
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

def add_p(doc, before_pt=0, after_pt=1.5, line_pt=14.0, align=WD_ALIGN_PARAGRAPH.LEFT):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(before_pt)
    pf.space_after = Pt(after_pt)
    if line_pt:
        pf.line_spacing = Pt(line_pt)
        pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    return p

def add_section_heading(doc, title):
    p = add_p(doc, before_pt=5.0, after_pt=2.0, line_pt=16.0)
    run = p.add_run(title)
    set_run_font(run, size_pt=11.0, bold=True, color_hex=DARK_BLUE)
    
    # Add bottom border to heading paragraph
    pBdr = parse_xml(r'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                     r'<w:bottom w:val="single" w:sz="8" w:space="2" w:color="1F3864"/>'
                     r'</w:pBdr>')
    p._element.get_or_add_pPr().append(pBdr)

def parse_markdown(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    
    lines = text.splitlines()
    data = {
        "name": "[姓名]",
        "intent": "",
        "contact": "",
        "summary": "",
        "skills": [],
        "projects": [],
        "education": ""
    }
    
    current_section = None
    current_project = None
    
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("# "):
            data["name"] = s[2:].strip()
        elif s.startswith("**求职意向**"):
            data["intent"] = s.replace("**求职意向**:", "").replace("**求职意向**：", "").strip()
        elif s.startswith("**联系方式**"):
            data["contact"] = s.replace("**联系方式**:", "").replace("**联系方式**：", "").strip()
        elif s.startswith("## "):
            current_section = s[3:].strip()
            current_project = None
        elif current_section == "个人概述":
            data["summary"] = s
        elif current_section == "技能":
            if s.startswith("- "):
                content = s[2:].strip()
                data["skills"].append(content)
        elif current_section == "项目经历":
            if s.startswith("### "):
                current_project = {"title": s[4:].strip(), "meta": "", "duty": "", "bullets": []}
                data["projects"].append(current_project)
            elif current_project and (s.startswith("`") or "GitHub:" in s):
                current_project["meta"] = s
            elif current_project and s.startswith("**个人职责**"):
                current_project["duty"] = s.replace("**个人职责**：", "").replace("**个人职责**:", "").strip()
            elif current_project and s.startswith("- "):
                current_project["bullets"].append(s[2:].strip())
        elif current_section == "教育背景":
            data["education"] = s
            
    return data

def build_docx(data, out_path):
    doc = Document()
    
    # Page Margins: A4, 1.4cm top/bottom, 1.8cm left/right for pristine 1-page layout
    sections = doc.sections
    for s in sections:
        s.page_width = Cm(21.0)
        s.page_height = Cm(29.7)
        s.top_margin = Cm(1.3)
        s.bottom_margin = Cm(1.3)
        s.left_margin = Cm(1.8)
        s.right_margin = Cm(1.8)
        
    # 1. Header (Name)
    p_name = add_p(doc, before_pt=0, after_pt=1.5, line_pt=22.0, align=WD_ALIGN_PARAGRAPH.CENTER)
    r_name = p_name.add_run(data["name"])
    set_run_font(r_name, size_pt=18.0, bold=True, color_hex="1A1A1A")
    
    # 2. Subheader (Intent, Contact, GitHub)
    p_sub = add_p(doc, before_pt=0, after_pt=4.0, line_pt=13.0, align=WD_ALIGN_PARAGRAPH.CENTER)
    header_text = f"求职意向：{data['intent']}  |  {data['contact']}"
    r_sub = p_sub.add_run(header_text)
    set_run_font(r_sub, size_pt=9.0, bold=False, color_hex="555555")
    
    # 3. 个人概述
    if data["summary"]:
        add_section_heading(doc, "个人概述")
        p_sum = add_p(doc, before_pt=1.5, after_pt=2.0, line_pt=13.5)
        r_sum = p_sum.add_run(data["summary"])
        set_run_font(r_sum, size_pt=9.0, bold=False, color_hex="333333")
        
    # 4. 专业技能
    if data["skills"]:
        add_section_heading(doc, "专业技能")
        for sk in data["skills"]:
            p_sk = add_p(doc, before_pt=0.5, after_pt=1.0, line_pt=13.0)
            # Check for bold prefix: **Label**: Rest
            m = re.match(r"^\*\*(.+?)\*\*:\s*(.*)$", sk)
            if m:
                label, val = m.group(1), m.group(2)
                r_dot = p_sk.add_run("•  ")
                set_run_font(r_dot, size_pt=9.0, bold=True, color_hex=DARK_BLUE)
                r_lbl = p_sk.add_run(label + "：")
                set_run_font(r_lbl, size_pt=9.0, bold=True, color_hex="1A1A1A")
                r_val = p_sk.add_run(val)
                set_run_font(r_val, size_pt=9.0, bold=False, color_hex="333333")
            else:
                r_txt = p_sk.add_run("•  " + sk)
                set_run_font(r_txt, size_pt=9.0, bold=False, color_hex="333333")
                
    # 5. 项目经历
    if data["projects"]:
        add_section_heading(doc, "核心项目经历")
        for proj in data["projects"]:
            # Project Title + Tech Tag / GitHub
            p_title = add_p(doc, before_pt=3.5, after_pt=1.0, line_pt=14.0)
            r_t = p_title.add_run(proj["title"])
            set_run_font(r_t, size_pt=10.0, bold=True, color_hex=DARK_BLUE)
            
            if proj["meta"]:
                meta_clean = proj["meta"].replace("`", "").replace("[pk-core](https://github.com/adlink8/pk-core)", "github.com/adlink8/pk-core").replace("[novel-mind](https://github.com/adlink8/novel-mind)", "github.com/adlink8/novel-mind")
                r_meta = p_title.add_run("  |  " + meta_clean)
                set_run_font(r_meta, size_pt=8.5, bold=False, color_hex=GRAY_TAG)
                
            # Personal Duty
            if proj["duty"]:
                p_duty = add_p(doc, before_pt=0.5, after_pt=1.0, line_pt=12.5)
                r_d_lbl = p_duty.add_run("个人职责：")
                set_run_font(r_d_lbl, size_pt=8.5, bold=True, color_hex="444444")
                r_d_val = p_duty.add_run(proj["duty"])
                set_run_font(r_d_val, size_pt=8.5, bold=False, color_hex="555555")
                
            # Bullets
            for b in proj["bullets"]:
                p_b = add_p(doc, before_pt=0.5, after_pt=1.0, line_pt=12.8)
                m_b = re.match(r"^\*\*(.+?)\*\*：(.*)$", b)
                if m_b:
                    b_lbl, b_val = m_b.group(1), m_b.group(2)
                    r_b_dot = p_b.add_run("•  ")
                    set_run_font(r_b_dot, size_pt=8.5, bold=True, color_hex=DARK_BLUE)
                    r_b_lbl = p_b.add_run(b_lbl + "：")
                    set_run_font(r_b_lbl, size_pt=8.8, bold=True, color_hex="1A1A1A")
                    r_b_val = p_b.add_run(b_val)
                    set_run_font(r_b_val, size_pt=8.5, bold=False, color_hex="333333")
                else:
                    r_b = p_b.add_run("•  " + b)
                    set_run_font(r_b, size_pt=8.5, bold=False, color_hex="333333")

    # 6. 教育背景
    if data["education"]:
        add_section_heading(doc, "教育背景")
        p_edu = add_p(doc, before_pt=1.5, after_pt=0.0, line_pt=13.0)
        r_edu = p_edu.add_run("•  " + data["education"])
        set_run_font(r_edu, size_pt=9.0, bold=True, color_hex="222222")

    doc.save(out_path)
    print(f"Generated DOCX: {out_path}")

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    data = parse_markdown(MD_PATH)
    build_docx(data, DOCX_OUT)
    
    # Convert DOCX to PDF via LibreOffice
    cmd = [SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", OUT_DIR, DOCX_OUT]
    subprocess.run(cmd, check=True)
    print(f"Generated PDF: {PDF_OUT}")

if __name__ == "__main__":
    main()
