#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Career OS — ATS 网申自动填表数据同步
从 config/profile.yml 编译 extensions/ats-autofill/profile.json。
单一求职意向，不再生成多岗位轨道。联系方式只复制 yaml 里已有字段，不编造。
"""

import json
import re
import sys
from pathlib import Path

import yaml

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
PROFILE_YAML = ROOT_DIR / "config" / "profile.yml"
OUTPUT_DIR = ROOT_DIR / "extensions" / "ats-autofill"
OUTPUT_JSON = OUTPUT_DIR / "profile.json"

def load_profile():
    if not PROFILE_YAML.exists():
        print(f"[Error] 未找到画像文件: {PROFILE_YAML}")
        print("请先复制 config/profile.example.yml 为 config/profile.yml")
        sys.exit(1)
    with open(PROFILE_YAML, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def single_job_title(career_target) -> str:
    """取主攻方向的第一个可独立填写的岗位名，丢掉斜杠拼接的分类。"""
    primary = (career_target or {}).get("primary") or []
    if not primary:
        return ""
    raw = str(primary[0]).strip()
    parts = [p.strip() for p in re.split(r"[/／、|]", raw) if p.strip()]
    if not parts:
        return ""

    def _score(part: str) -> int:
        score = 0
        if any(h in part for h in ("工程师", "运维", "支持", "实习", "开发")):
            score += 2
        if re.search(r"[\u4e00-\u9fa5]", part):
            score += 1
        return score

    return sorted(parts, key=_score, reverse=True)[0]


def _join(items, sep="、"):
    return sep.join(str(x).strip() for x in (items or []) if str(x).strip())


def _personal_block(profile):
    personal = profile.get("personal") or {}
    # 只搬 yaml 已有键；缺省留空，由扩展跳过填写。禁止在脚本里写死手机/邮箱/身份证。
    return {
        "name": personal.get("name") or "",
        "gender": personal.get("gender") or "",
        "birth_year": str(personal.get("birth_year") or ""),
        "birth_date": str(personal.get("birth_date") or ""),
        "age": str(personal.get("age") or ""),
        "phone": str(personal.get("phone") or ""),
        "email": str(personal.get("email") or ""),
        "id_card": str(personal.get("id_card") or ""),
        "current_city": personal.get("current_city") or "",
        "current_address": personal.get("current_address") or "",
        "native_province": personal.get("native_province") or "",
        "native_city": personal.get("native_city") or "",
        "native_place": personal.get("native_place") or personal.get("hukou") or "",
        "political_status": personal.get("political_status") or "",
        "marriage": personal.get("marriage") or "",
        "ethnicity": personal.get("ethnicity") or "",
        "health": personal.get("health") or "",
        "emergency_contact": personal.get("emergency_contact") or "",
        "emergency_phone": str(personal.get("emergency_phone") or ""),
        "emergency_relation": personal.get("emergency_relation") or "",
        "github": personal.get("github") or "",
        "blog": personal.get("blog") or "",
        "available_time": personal.get("available_time") or "",
        "internship_duration": personal.get("internship_duration") or "",
        "days_per_week": personal.get("days_per_week") or "",
    }


def _education_block(edu):
    prev_list = edu.get("previous") or []
    prev = prev_list[0] if prev_list else {}
    period = str(prev.get("period") or "")
    prev_start, prev_end = "", ""
    if "~" in period:
        a, b = [x.strip() for x in period.split("~", 1)]
        prev_start, prev_end = a, b
    return {
        "undergraduate": {
            "school": edu.get("school") or "",
            "degree": edu.get("degree") or "",
            "major": edu.get("major") or "",
            "graduation": edu.get("graduation") or "",
            "start_date": edu.get("start_date") or "",
            "end_date": edu.get("graduation") or "",
            "education_type": edu.get("current") or "",
        },
        "junior_college": {
            "school": prev.get("school") or "",
            "degree": "大专" if prev else "",
            "major": prev.get("focus") or prev.get("major") or "",
            "start_date": prev_start,
            "end_date": prev_end,
            "graduation": prev_end,
        },
    }


def _projects(profile):
    out = []
    for item in profile.get("projects") or []:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        year = item.get("year")
        keywords = _join(item.get("keywords") or [])
        highlight = (item.get("highlight") or item.get("description") or "").strip()
        start_date = str(item.get("start_date") or "")
        end_date = str(item.get("end_date") or "")
        full_text = (
            f"【项目名称】：{name}\n"
            f"【核心技术】：{keywords}\n"
            f"【职责与业绩】：{highlight}"
        ).strip()
        out.append(
            {
                "name": name,
                "year": str(year or ""),
                "start_date": start_date,
                "end_date": end_date,
                "role": item.get("role") or "",
                "keywords": keywords,
                "description": item.get("description") or highlight,
                "duty": highlight,
                "achievement": item.get("highlight") or "",
                "full_text": full_text,
            }
        )
    return out


def build_application(profile):
    skills = profile.get("skills") or {}
    career = profile.get("career_target") or {}
    edu = profile.get("education") or {}
    proficient = _join(skills.get("proficient") or [])
    familiar = _join(skills.get("familiar") or [])
    target = single_job_title(career)
    school = edu.get("school") or ""
    major = edu.get("major") or ""
    degree = edu.get("degree") or ""
    projects = _projects(profile)
    highlights = "；".join(
        f"{p['name']}：{p['duty']}" for p in projects[:3] if p.get("duty")
    )
    self_eval_parts = [
        f"{school}{degree}在读，专业{major}。" if school else "",
        f"求职意向：{target}。" if target else "",
        f"熟练技能：{proficient}。" if proficient else "",
        f"项目经历：{highlights}。" if highlights else "",
    ]
    return {
        "target_position": target,
        "target_cities": _join(career.get("cities") or []),
        "expected_salary": "",
        "self_evaluation": "".join(self_eval_parts).strip(),
        "skills_summary": (
            (f"【熟练】{proficient}\n" if proficient else "")
            + (f"【熟悉】{familiar}" if familiar else "")
        ).strip(),
        "skills_proficient": proficient,
        "skills_familiar": familiar,
        "projects": projects,
    }


def build_payload(profile):
    personal = _personal_block(profile)
    edu = _education_block(profile.get("education") or {})
    application = build_application(profile)
    return {
        "version": "3.0-single-intent",
        "universal": {
            "personal": personal,
            "education": edu,
            "hobbies": (profile.get("personal") or {}).get("hobbies") or "",
            "awards": (profile.get("personal") or {}).get("awards") or "",
            "certificates": (profile.get("personal") or {}).get("certificates") or "",
            "languages": profile.get("english_level") or "",
        },
        "application": application,
    }


def main():
    print(f"[1/3] 读取配置文件: {PROFILE_YAML}")
    profile = load_profile()

    print("[2/3] 编译单一意向填表画像（不生成岗位轨道）...")
    payload = build_payload(profile)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    app = payload["application"]
    print(f"[3/3] 已写入: {OUTPUT_JSON}")
    print("=" * 60)
    print("[OK] 数据同步完成！")
    print(f"候选人: {payload['universal']['personal']['name']}")
    print(f"单一求职意向: {app['target_position'] or '(yaml 未提供可解析岗位名)'}")
    print(f"项目条数: {len(app['projects'])}")
    print("联系方式仅在 profile.yml 的 personal.phone/email 有值时才会填入网申。")
    print("=" * 60)


if __name__ == "__main__":
    main()
