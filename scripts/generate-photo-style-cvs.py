"""Generate all Career OS role resumes with the cv-newland-photo-edition style.

The Markdown files remain the content source. This generator only changes layout,
font, spacing and section presentation; it does not rewrite resume claims.
Output is written to ``data/cv/final/photo-style`` so existing and submitted
artifacts are not overwritten.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CV_ROOT = ROOT / "data" / "cv"
OUTPUT_DIR = CV_ROOT / "final" / "photo-style"
STYLE_PATH = ROOT / "config" / "resume-style-photo.json"
EDGE_EXE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

SOURCE_FILES = {
    "cv-ops-photo-style": "cv-ops-v2-draft.md",
    "cv-iot-photo-style": "cv-iot-v2-draft.md",
    "cv-ai-infra-photo-style": "cv-ai-infra-v2-draft.md",
    "cv-network-photo-style": "cv-network.md",
    "cv-compact-photo-style": "cv-compact.md",
    "cv-newland-customized-photo-style": "cv-newland-customized.md",
    "cv-aispeech-devops-photo-style": "cv-aispeech-devops.md",
    "cv-aispeech-opensource-photo-style": "cv-aispeech-opensource.md",
    "cv-aispeech-agent-photo-style": "cv-aispeech-agent.md",
    "cv-unified-template-photo-style": "../../templates/cv-template.md",
}


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def clean_name(value: str) -> str:
    if value.strip().startswith("简历") and "·" in value:
        value = value.split("·", 1)[1]
    value = re.sub(r"\s*\(.*?\)", "", value)
    value = re.sub(r"\s*[·|｜].*$", "", value)
    return value.strip(" #")


def strip_markdown(value: str) -> str:
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = value.replace("`", "")
    value = re.sub(r"\*\*(.+?)\*\*", r"\1", value)
    value = re.sub(r"^\s*[-*+]\s+", "", value)
    value = re.sub(r"^\s*\d+[.)]\s+", "", value)
    return value.strip()


def split_label(value: str) -> tuple[str, str]:
    match = re.match(r"\*\*(.+?)\*\*\s*[:：]\s*(.*)$", value)
    if match:
        return match.group(1).strip(), strip_markdown(match.group(2))
    return "", strip_markdown(value)


def parse_resume(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    data: dict[str, object] = {
        "name": "",
        "intent": "",
        "contact": "",
        "summary": [],
        "skills": [],
        "projects": [],
        "experience": [],
        "education": [],
        "certs": [],
    }
    section = ""
    project: dict[str, object] | None = None
    experience: dict[str, object] | None = None

    for raw in lines:
        line = raw.strip()
        if not line or line == "---" or line.startswith(">"):
            continue
        if line.startswith("# "):
            if not data["name"]:
                data["name"] = clean_name(line[2:])
            continue
        if line.startswith("## "):
            section = strip_markdown(line[3:]).strip()
            project = None
            experience = None
            continue
        if line.startswith("### "):
            if "项目" in section:
                title = strip_markdown(line[4:])
                project = {"title": title, "tag": "", "duty": "", "bullets": [], "github": ""}
                data["projects"].append(project)
            continue

        label, value = split_label(line)
        if label in {"求职意向", "目标岗位"}:
            data["intent"] = value
            continue
        if label in {"联系方式", "联系"}:
            data["contact"] = value
            continue
        if label in {"目标城市", "期望薪资"}:
            suffix = f"{label}: {value}"
            data["intent"] = f"{data['intent']} | {suffix}".strip(" |")
            continue

        if section in {"个人概述", "个人定位", "岗位匹配摘要"}:
            data["summary"].append(re.sub(r"^\s*[-*+]\s+", "", line).strip())
            continue

        if "技能" in section:
            if line.startswith("-"):
                skill_label, skill_value = split_label(line[1:].strip())
                data["skills"].append((skill_label, skill_value))
            continue

        if "教育" in section:
            value = strip_markdown(line.lstrip("- "))
            if value:
                data["education"].append(value)
            continue

        if "证书" in section or "竞赛" in section:
            if line.startswith("-"):
                data["certs"].append(strip_markdown(line[1:].strip()))
            continue

        if "实习" in section or "工作经历" in section:
            if line.startswith("**") and "**" in line[2:]:
                match = re.match(r"\*\*(.+?)\*\*", line)
                title = strip_markdown(match.group(1) if match else line.strip("*"))
                if match:
                    suffix = strip_markdown(line[match.end():].strip(" |"))
                    if suffix:
                        title = f"{title} | {suffix}"
                experience = {"title": title, "bullets": []}
                data["experience"].append(experience)
            elif line.startswith("-"):
                if experience is None:
                    experience = {"title": "经历", "bullets": []}
                    data["experience"].append(experience)
                experience["bullets"].append(strip_markdown(line[1:].strip()))
            continue

        if project is not None and "项目" in section:
            tag_match = re.match(r"`([^`]+)`", line)
            if tag_match:
                project["tag"] = strip_markdown(tag_match.group(1))
                url_match = re.search(r"\]\((https?://[^)]+)\)", line) or re.search(r"(https?://github\.com/[^\s|)]+)", line)
                if url_match:
                    project["github"] = url_match.group(1).rstrip("]")
                continue
            if "GitHub:" in line or "github.com/" in line:
                url = re.search(r"\]\((https?://[^)]+)\)", line) or re.search(r"(https?://github\.com/[^\s|)]+)", line)
                if url:
                    project["github"] = url.group(1).rstrip("]")
            if label in {"个人职责", "职务职责"}:
                project["duty"] = value
                continue
            if line.startswith("-"):
                project["bullets"].append(re.sub(r"^\s*[-*+]\s+", "", line).strip())

    if not data["intent"]:
        data["intent"] = "求职简历"
    return data


def render_bold_label(value: str) -> str:
    match = re.match(r"\*\*(.+?)\*\*\s*[:：]\s*(.*)$", value)
    if match:
        return f"<b>{esc(match.group(1))}：</b>{esc(strip_markdown(match.group(2)))}"
    return esc(strip_markdown(value))


def build_css(style: dict[str, object]) -> str:
    colors = style["colors"]
    fonts = style["fonts"]
    metrics = style["metrics"]
    return f"""
@page {{ size: A4 portrait; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, '{fonts['body']}', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  color: {colors['main_text']}; background: #FFFFFF;
  width: {style['page']['width_mm']}mm; height: {style['page']['height_mm']}mm;
  overflow: hidden; display: flex; margin: 0 auto;
}}
.sidebar {{ width: {metrics['sidebar_width_mm']}mm; height: {style['page']['height_mm']}mm;
  background: {colors['sidebar']}; color: #FFFFFF; padding: {metrics['sidebar_padding']};
  display: flex; flex-direction: column; flex-shrink: 0; }}
.name {{ font-size: {metrics['name_px']}px; font-weight: bold; letter-spacing: 2px;
  color: #FFFFFF; margin-bottom: 4px; }}
.intent {{ font-size: {metrics['intent_px']}px; color: {colors['sidebar_muted']}; margin-bottom: 14px; line-height: 1.5; }}
.photo-box {{ width: 100%; display: flex; justify-content: flex-start; margin-bottom: 14px; }}
.photo-img {{ width: {metrics['photo_width_mm']}mm; height: {metrics['photo_height_mm']}mm; object-fit: cover;
  border-radius: 2px; box-shadow: 0 2px 8px rgba(0,0,0,.25); background: #2D3748; }}
.side-sec-title {{ font-size: {metrics['side_heading_px']}px; font-weight: bold; color: #FFFFFF;
  margin-top: 16px; margin-bottom: 7px; letter-spacing: 1px; padding-bottom: 3px;
  border-bottom: 1.5px solid rgba(255,255,255,.35); }}
.side-item {{ font-size: {metrics['side_item_px']}px; line-height: {metrics['side_item_line']};
  color: {colors['sidebar_text']}; margin-bottom: 4px; word-break: break-word; }}
.side-item b, .side-skill-item b {{ color: #FFFFFF; font-weight: 600; }}
.side-skill-item {{ font-size: {metrics['side_skill_px']}px; line-height: {metrics['side_skill_line']};
  color: #F8FAFC; margin-bottom: 7px; word-break: break-word; }}
.main {{ width: {metrics['main_width_mm']}mm; height: {style['page']['height_mm']}mm;
  padding: {metrics['main_padding']}; display: flex; flex-direction: column; background: #FFFFFF; }}
.sec-ribbon {{ background: {colors['ribbon']}; color: {colors['ribbon_text']};
  font-size: {metrics['ribbon_px']}px; font-weight: bold; padding: 5px 12px; border-radius: 1px;
  margin-top: 15px; margin-bottom: 8px; letter-spacing: 1px; display: flex; align-items: center; }}
.first-ribbon {{ margin-top: 0; }}
.exp-header {{ display: flex; justify-content: space-between; font-size: 12px; font-weight: bold;
  color: #1E293B; margin-top: 4px; margin-bottom: 7px; gap: 8px; }}
.exp-header .company {{ flex: 1; margin-left: 10px; }}
.bullet-item {{ font-size: {metrics['body_px']}px; line-height: {metrics['body_line']}; color: {colors['main_text']};
  margin-bottom: 6px; position: relative; padding-left: 13px; text-align: justify; }}
.bullet-item::before {{ content: '■'; position: absolute; left: 0; top: 1px; font-size: 7.5px; color: {colors['main_text']}; }}
.bullet-item b {{ color: {colors['main_strong']}; font-weight: bold; }}
.proj-title-row {{ display: flex; justify-content: space-between; align-items: baseline; gap: 8px;
  font-size: {metrics['project_title_px']}px; font-weight: bold; color: #1E293B; margin-top: 12px; margin-bottom: 3.5px; }}
.proj-github {{ font-size: 9.8px; color: {colors['link']}; font-family: '{fonts['mono']}', monospace;
  font-weight: normal; text-decoration: none; word-break: break-all; }}
.proj-duty {{ font-size: {metrics['project_duty_px']}px; line-height: {metrics['project_duty_line']};
  color: #475569; margin-bottom: 5px; padding-left: 2px; }}
.education-line {{ font-size: {metrics['side_item_px']}px; line-height: {metrics['side_item_line']}; margin-bottom: 5px; color: {colors['sidebar_text']}; }}
"""


def build_html(data: dict[str, object], style: dict[str, object], title: str) -> str:
    skills = data["skills"] or [("", "技能信息待补充")]
    education = data["education"] or ["教育信息待补充"]
    certs = data["certs"]
    summary = data["summary"]
    experience = data["experience"]
    projects = data["projects"]
    image_path = "../portrait.jpg"

    side_skills = "\n".join(
        f'<div class="side-skill-item">▪ {render_bold_label(f"**{label}**：{value}" if label else value)}</div>'
        for label, value in skills
    )
    contact_items = [item.strip() for item in str(data["contact"] or "").split("|") if item.strip()]
    contact_defaults = ["手 机", "邮 箱", "GitHub"]
    contact_rows: list[str] = []
    for index, item in enumerate(contact_items):
        match = re.match(r"^(.+?)\s*[：:]\s*(.+)$", item)
        if match:
            label, value = match.group(1).strip(), match.group(2).strip()
        else:
            label = contact_defaults[index] if index < len(contact_defaults) else ""
            value = item
        prefix = f'<b>{esc(label)}：</b>' if label else ""
        contact_rows.append(f'<div class="side-item">{prefix}{esc(value)}</div>')
    side_contact = "\n".join(contact_rows) or '<div class="side-item">联系方式待补充</div>'

    is_aispeech = title.startswith("cv-aispeech-") or title == "cv-unified-template-photo-style"
    if is_aispeech:
        basic_rows: list[str] = []
        for line in education:
            parts = [part.strip() for part in re.split(r"[|｜]", strip_markdown(line)) if part.strip()]
            if len(parts) >= 3:
                school, major, degree = parts[:3]
                basic_rows.extend([
                    f'<div class="side-item"><b>学历：</b>{esc(degree)}</div>',
                    f'<div class="side-item"><b>专业：</b>{esc(major)}</div>',
                    f'<div class="side-item"><b>学校：</b>{esc(school)}</div>',
                ])
            elif parts:
                basic_rows.append(f'<div class="side-item">{esc(" | ".join(parts))}</div>')
        side_basic_title = "基本信息"
        side_basic = "\n".join(basic_rows) or '<div class="side-item">基本信息待补充</div>'
    else:
        side_basic_title = "教育背景"
        side_basic = "\n".join(f'<div class="education-line">{esc(strip_markdown(line))}</div>' for line in education)
    side_certs = "\n".join(f'<div class="side-item">{esc(strip_markdown(item))}</div>' for item in certs)
    side_certs_section = (
        f'<div class="side-sec-title">证书与竞赛</div>{side_certs}'
        if certs else ""
    )

    right_parts: list[str] = []
    if summary:
        right_parts.append('<div class="sec-ribbon first-ribbon">个人概述</div>')
        right_parts.extend(f'<div class="bullet-item">{render_bold_label(str(item))}</div>' for item in summary)
    if experience:
        right_parts.append('<div class="sec-ribbon">工作经历</div>')
        for item in experience:
            right_parts.append(f'<div class="exp-header"><span>{esc(str(item["title"]))}</span></div>')
            right_parts.extend(f'<div class="bullet-item">{render_bold_label(str(bullet))}</div>' for bullet in item["bullets"])
    if projects:
        right_parts.append(f'<div class="sec-ribbon{" first-ribbon" if not right_parts else ""}">核心项目经历</div>')
        for item in projects:
            github = str(item.get("github") or "")
            github_html = f'<a class="proj-github" href="{esc(github)}">{esc(github)}</a>' if github else ""
            right_parts.append(f'<div class="proj-title-row"><span>{esc(str(item["title"]))}</span>{github_html}</div>')
            if item.get("tag"):
                right_parts.append(f'<div class="proj-duty">{esc(str(item["tag"]))}</div>')
            if item.get("duty"):
                right_parts.append(f'<div class="proj-duty"><b>职务职责：</b>{esc(str(item["duty"]))}</div>')
            right_parts.extend(f'<div class="bullet-item">{render_bold_label(str(bullet))}</div>' for bullet in item["bullets"])
    if not right_parts:
        right_parts.append('<div class="sec-ribbon first-ribbon">简历内容</div><div class="bullet-item">暂无内容</div>')

    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{esc(title)}</title><style>{build_css(style)}</style></head>
<body>
  <aside class="sidebar">
    <div class="name">{esc(str(data["name"]))}</div>
    <div class="photo-box"><img class="photo-img" src="{image_path}" alt="证件照"></div>
    <div class="side-sec-title">联系方式</div>
    {side_contact}
    <div class="side-sec-title">{side_basic_title}</div>
    {side_basic}
    <div class="side-sec-title">主要技能</div>
    {side_skills}
    {side_certs_section}
  </aside>
  <main class="main">{''.join(right_parts)}</main>
</body></html>'''


def generate_one(output_stem: str, source_name: str, style: dict[str, object]) -> tuple[Path, Path]:
    source = (CV_ROOT / source_name).resolve()
    data = parse_resume(source)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    html_path = OUTPUT_DIR / f"{output_stem}.html"
    pdf_path = OUTPUT_DIR / f"{output_stem}.pdf"
    html_path.write_text(build_html(data, style, output_stem), encoding="utf-8")
    if not EDGE_EXE.exists():
        raise FileNotFoundError(f"Edge 不存在: {EDGE_EXE}")
    subprocess.run(
        [str(EDGE_EXE), "--headless", "--disable-gpu", "--run-all-compositor-stages-before-draw",
         "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", str(html_path)],
        check=True,
        timeout=180,
        capture_output=True,
    )
    return html_path, pdf_path


def main() -> int:
    parser = argparse.ArgumentParser(description="统一生成 cv-newland-photo-edition 风格简历")
    parser.add_argument("--only", choices=sorted(SOURCE_FILES), action="append", help="只生成指定版本，可重复")
    args = parser.parse_args()
    style = json.loads(STYLE_PATH.read_text(encoding="utf-8"))
    selected = args.only or list(SOURCE_FILES)
    for output_stem in selected:
        html_path, pdf_path = generate_one(output_stem, SOURCE_FILES[output_stem], style)
        print(f"Generated: {html_path}")
        print(f"Generated: {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
