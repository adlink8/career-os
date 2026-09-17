"""Generate photo dual-column PDFs from Markdown resumes.

Pipeline: finalize Markdown first, then run this generator. It only changes
layout; it does not rewrite claims. Output: ``data/cv/final/photo-style``.
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

# 只从现用三份母版出照片双栏。历史稿仍在 data/cv/，不作为默认输入。
SOURCE_FILES = {
    "cv-ops-photo-style": "cv-ops.md",
    "cv-iot-photo-style": "cv-iot.md",
    "cv-semi-photo-style": "cv-semi.md",
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
        "competitions": [],
        "competition_title": "",
        "experience": [],
        "education": [],
        "certs": [],
        "basic": [],
    }
    section = ""
    project: dict[str, object] | None = None
    experience: dict[str, object] | None = None

    for raw in lines:
        line = raw.strip()
        if not line or line == "---":
            continue
        if line.startswith(">"):
            meta = line.lstrip("> ").strip()
            intent_m = re.match(r"(求职意向|目标岗位)\s*[:：]\s*(.*)$", meta)
            if intent_m and not data["intent"]:
                data["intent"] = strip_markdown(intent_m.group(2))
            continue
        if line.startswith("# "):
            if not data["name"]:
                data["name"] = clean_name(line[2:])
            continue
        if line.startswith("## "):
            section = strip_markdown(line[3:]).strip()
            project = None
            experience = None
            if any(k in section for k in ["成就", "竞赛", "荣誉"]) and "证书" not in section:
                data["competition_title"] = section
            continue
        if line.startswith("### "):
            if "项目" in section:
                title = strip_markdown(line[4:])
                project = {"title": title, "tag": "", "duty": "", "bullets": [], "github": ""}
                data["projects"].append(project)
                continue
            if any(k in section for k in ["成就", "竞赛", "荣誉"]) and "证书" not in section:
                title = strip_markdown(line[4:])
                project = {"title": title, "tag": "", "duty": "", "bullets": [], "github": ""}
                data["competitions"].append(project)
                continue
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

        if section in {"基本信息", "个人信息"}:
            if line.startswith("-"):
                data["basic"].append(strip_markdown(line[1:].strip()))
            continue

        if "教育" in section:
            value = strip_markdown(line.lstrip("- "))
            if value:
                data["education"].append(value)
            continue

        if section in {"证书与竞赛", "证书与荣誉", "证书", "荣誉与证书", "资格证书"}:
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

        if project is not None and ("项目" in section or any(k in section for k in ["成就", "竞赛", "荣誉"])):
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
        label = match.group(1).strip()
        body = match.group(2).strip()
        body = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", body)
        body = body.replace("`", "")
        body = html.escape(body, quote=True)
        body = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", body)
        return f"<b>{esc(label)}：</b>{body}"
    body = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    body = body.replace("`", "")
    body = html.escape(body, quote=True)
    body = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", body)
    return body


def build_css(style: dict[str, object]) -> str:
    colors = style["colors"]
    fonts = style["fonts"]
    metrics = style["metrics"]
    ribbon_pad = metrics.get('ribbon_padding', '3.5px 10px')
    ribbon_mt = metrics.get('ribbon_margin_top_px', 10)
    ribbon_mb = metrics.get('ribbon_margin_bottom_px', 5)
    body_lh = metrics.get('body_line', 1.54)
    bullet_mb = metrics.get('bullet_margin_bottom_px', 4.5)
    bullet_pl = metrics.get('bullet_padding_left_px', 13)
    proj_mt = metrics.get('project_title_margin_top_px', 7.5)
    proj_mb = metrics.get('project_title_margin_bottom_px', 2.5)
    duty_lh = metrics.get('project_duty_line', 1.44)
    duty_mb = metrics.get('project_duty_margin_bottom_px', 3.5)
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
  color: #F8FAFC; margin-bottom: {metrics.get('side_skill_margin_bottom_px', 7)}px; word-break: break-word; }}
.main {{ width: {metrics['main_width_mm']}mm; height: {style['page']['height_mm']}mm;
  padding: {metrics['main_padding']}; display: flex; flex-direction: column; background: #FFFFFF; }}
.sec-ribbon {{ background: {colors['ribbon']}; color: {colors['ribbon_text']};
  font-size: {metrics['ribbon_px']}px; font-weight: bold; padding: {ribbon_pad}; border-radius: 1px;
  margin-top: {ribbon_mt}px; margin-bottom: {ribbon_mb}px; letter-spacing: 1px; display: flex; align-items: center; }}
.first-ribbon {{ margin-top: 0; }}
.exp-header {{ display: flex; justify-content: space-between; font-size: 12px; font-weight: bold;
  color: #1E293B; margin-top: 4px; margin-bottom: 6px; gap: 8px; }}
.exp-header .company {{ flex: 1; margin-left: 10px; }}
.bullet-item {{ font-size: {metrics['body_px']}px; line-height: {body_lh}; color: {colors['main_text']};
  margin-bottom: {bullet_mb}px; position: relative; padding-left: {bullet_pl}px; text-align: justify; }}
.bullet-item::before {{ content: '■'; position: absolute; left: 0; top: 1px; font-size: 7.5px; color: {colors['main_text']}; }}
.bullet-item b {{ color: {colors['main_strong']}; font-weight: bold; }}
.proj-title-row {{ display: flex; justify-content: space-between; align-items: baseline; gap: 8px;
  font-size: {metrics['project_title_px']}px; font-weight: bold; color: #1E293B;
  margin-top: {proj_mt}px; margin-bottom: {proj_mb}px; }}
.proj-github {{ font-size: 9.8px; color: {colors['link']}; font-family: '{fonts['mono']}', monospace;
  font-weight: normal; text-decoration: none; word-break: break-all; }}
.proj-duty {{ font-size: {metrics['project_duty_px']}px; line-height: {duty_lh};
  color: #475569; margin-bottom: {duty_mb}px; padding-left: 2px; }}
.education-line {{ font-size: {metrics['side_item_px']}px; line-height: {metrics['side_item_line']}; margin-bottom: 5px; color: {colors['sidebar_text']}; }}
"""


def build_html(data: dict[str, object], style: dict[str, object], title: str) -> str:
    skills = data["skills"] or [("", "技能信息待补充")]
    education = data["education"] or ["教育信息待补充"]
    certs = data["certs"]
    summary = data["summary"]
    experience = data["experience"]
    projects = data["projects"]
    image_path = _portrait_data_uri()

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

    basic_rows: list[str] = []
    for item in data.get("basic") or []:
        lab, val = split_label(str(item))
        if lab:
            basic_rows.append(f'<div class="side-item"><b>{esc(lab)}：</b>{esc(val)}</div>')
        elif str(item).strip():
            basic_rows.append(f'<div class="side-item">{esc(str(item))}</div>')
    for line in education:
        parts = [part.strip() for part in re.split(r"[|｜]", strip_markdown(line)) if part.strip()]
        if len(parts) >= 3:
            school, major, degree = parts[0], parts[1], parts[2]
            grad = parts[3] if len(parts) > 3 else ""
            basic_rows.extend([
                f'<div class="side-item"><b>学历：</b>{esc(degree)}</div>',
                f'<div class="side-item"><b>专业：</b>{esc(major)}</div>',
                f'<div class="side-item"><b>学校：</b>{esc(school)}</div>',
            ])
            if grad:
                basic_rows.append(f'<div class="side-item"><b>毕业：</b>{esc(grad)}</div>')
        elif parts:
            basic_rows.append(f'<div class="side-item">{esc(" | ".join(parts))}</div>')
    side_basic_title = "基本信息"
    side_basic = "\n".join(basic_rows) or '<div class="side-item">基本信息待补充</div>'
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
    competitions = data.get("competitions", [])
    comp_title = str(data.get("competition_title") or "个人成就与竞赛")
    if competitions:
        right_parts.append(f'<div class="sec-ribbon">{esc(comp_title)}</div>')
        for item in competitions:
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
    {f'<div class="intent">{esc(str(data["intent"]))}</div>' if data.get("intent") else ""}
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


def _portrait_data_uri() -> str:
    import base64

    for cand in (
        CV_ROOT / "final" / "portrait.jpg",
        CV_ROOT / "portrait.jpg",
        CV_ROOT / "final" / "photo-style" / "portrait.jpg",
    ):
        if cand.is_file():
            raw = cand.read_bytes()
            return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    return ""


def generate_one(
    output_stem: str,
    source_name: str,
    style: dict[str, object],
    *,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    source = Path(source_name)
    if not source.is_absolute():
        source = (CV_ROOT / source_name).resolve()
    data = parse_resume(source)
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    html_path = out / f"{output_stem}.html"
    pdf_path = out / f"{output_stem}.pdf"
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
    parser.add_argument("--from-dir", type=Path, help="从目录内全部 .md 生成照片双栏")
    parser.add_argument("--out-dir", type=Path, help="输出目录，默认 data/cv/final/photo-style")
    args = parser.parse_args()
    style = json.loads(STYLE_PATH.read_text(encoding="utf-8"))
    out_dir = args.out_dir.resolve() if args.out_dir else None
    if args.from_dir:
        md_files = sorted(Path(args.from_dir).glob("*.md"))
        if not md_files:
            raise SystemExit(f"目录无 md: {args.from_dir}")
        for md in md_files:
            html_path, pdf_path = generate_one(
                md.stem, str(md.resolve()), style, output_dir=out_dir
            )
            print(f"Generated: {html_path}")
            print(f"Generated: {pdf_path}")
        return 0
    selected = args.only or list(SOURCE_FILES)
    for output_stem in selected:
        html_path, pdf_path = generate_one(
            output_stem, SOURCE_FILES[output_stem], style, output_dir=out_dir
        )
        print(f"Generated: {html_path}")
        print(f"Generated: {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
