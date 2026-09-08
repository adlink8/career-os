#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Career OS — ATS Diagnostic Reporter Service (报告渲染与展示服务层)
负责将引擎诊断数据格式化为终端看板或 JSON 契约，与业务算法完全解耦。
"""

import os
import json
from typing import Dict

def print_report(res: Dict, jd_title: str, resume_path: str):
    """Print visually structured diagnostic report to terminal."""
    s = res["sub_scores"]
    print("\n" + "=" * 75)
    print(" 🎯 Career OS — ATS Preflight Matcher (校招投前模拟打分看板)")
    print("=" * 75)
    print(f"📌 拟投岗位 : {jd_title}")
    print(f"📄 审查简历 : {os.path.basename(resume_path)}")
    print(f"🏆 综合评分 : {res['total_score']} / 100 分")
    print(f"🚦 评审结论 : {res['status_text']}")
    print("-" * 75)
    print("📊 五维评分拆解 (Breakdown):")
    print(f"  1. 硬门槛与求职意向 (Knockout & Intent)     : {s['knockout']['score']:2d} / {s['knockout']['max']} 分")
    print(f"  2. 核心技术词正文落地 (In-Project Grounding) : {s['keywords_grounding']['score']:2d} / {s['keywords_grounding']['max']} 分")
    print(f"  3. 主力项目与JD对位深度 (Project Alignment)  : {s['project_alignment']['score']:2d} / {s['project_alignment']['max']} 分 (项目余弦值: {s['project_alignment']['cosine_sim']})")
    print(f"  4. 项目STAR量化与工程证据 (STAR Evidence)   : {s['star_and_evidence']['score']:2d} / {s['star_and_evidence']['max']} 分")
    print(f"  5. 格式结构与单页密度 (Parsability Score)   : {s['parsability']['score']:2d} / {s['parsability']['max']} 分")
    print("-" * 75)

    if s['knockout']['critical']:
        print("🚨 【一票否决致命告警】:")
        for c in s['knockout']['critical']:
            print(f"   ❌ {c}")
        print()

    if s['keywords_grounding']['suggestions']:
        for sug in s['keywords_grounding']['suggestions']:
            print(f"   {sug}")
        print()

    if s['project_alignment']['notes']:
        for n in s['project_alignment']['notes']:
            print(f"   • {n}")
        print()

    if s['knockout']['warnings'] or s['parsability']['notes']:
        print("⚠️ 【结构与格式警示】:")
        for w in s['knockout']['warnings']:
            print(f"   • {w}")
        for n in s['parsability']['notes']:
            print(f"   • {n}")
        print()

    print(f"✅ 项目正文落地核心词 ({len(s['keywords_grounding']['grounded'])}个):")
    print(f"   {', '.join(s['keywords_grounding']['grounded']) if s['keywords_grounding']['grounded'] else '无'}")
    print()

    if s['keywords_grounding']['skill_only']:
        print(f"⚠️ 仅在技能栏吹水·项目未落地词 ({len(s['keywords_grounding']['skill_only'])}个):")
        print(f"   👉 {', '.join(s['keywords_grounding']['skill_only'])}")
        print("   💡 警示: 面试官极易判定为只背过八股，必须在项目经历中补写该技术的实操动作！")
        print()

    if s['keywords_grounding']['missing']:
        print(f"❌ 全篇致命缺失词 Missing Keywords ({len(s['keywords_grounding']['missing'])}个):")
        print(f"   👉 {', '.join(s['keywords_grounding']['missing'])}")
    else:
        print("🎉 核心技术词完美覆盖！")

    print("=" * 75 + "\n")

def render_json_report(res: Dict) -> str:
    """Format diagnostic result into pretty JSON string."""
    return json.dumps(res, ensure_ascii=False, indent=2)

render_terminal_report = print_report
