"""Populate campus application limits for companies and calculate recommendation rankings for jobs.

Single source of truth: data/career_jobs.sqlite.
Schema: v13.
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path("D:/ADLINK/Myproject/career-os")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db

sys.stdout.reconfigure(encoding="utf-8")

# 1. Rules mapping for companies
COMPANY_RULES: dict[str, tuple[int | None, str]] = {
    "九号公司": (None, "【不限投递数】官方2027届校招政策明确不限制岗位投递数量，鼓励候选人根据个人意向投递多个岗位，解锁更多职场可能"),
    "常州快克智能": (2, "官方HR专线直连(hr@quick-global.com)，建议投递1-2个核心方向"),
    "移远通信": (None, "【不设硬性上限】官方平台未明确限制投递数量，支持多岗位投递并按志愿优先级排队"),
    "常州微亿智造": (2, "官网与官方邮箱支持投递 1-2 个岗位，建议聚焦工业 AI 视觉或具身智能规控"),
    "先导智能": (3, "【最多3个志愿】每位候选人最多可同时投递3个岗位；简历被查看后不可修改"),
    "汇川技术": (5, "【最多5个平行志愿】每位同学最多可申请5个不同职位。除第一志愿外为平行志愿，率先面试岗位升级为第一志愿"),
    "科沃斯": (2, "自建招聘系统每位候选人最多申请 2 个职位，苏州吴中总部集中初筛"),
    "苏州天准科技": (2, "谷露 Gllue ATS 系统支持投递 1-2 个职位，HR老师专线跟进"),
    "无锡中科微至": (2, "官网自建人才专栏与直聘通道，建议填报 1-2 个核心意向"),
    "无锡日联科技": (2, "官网人才招聘子系统支持投递 1-2 个岗位，无锡新吴总部直通"),
    "研华科技": (2, "Workday全球平台与北森双通道，建议申请 1-2 个对位方向"),
    "优博讯": (2, "北森系统每人最多可投递 2 个志愿，支持官方邮箱(hr-zhaopin@urovo.com)补充"),
    "涂鸦智能": (2, "统一招聘门户(job.tuya.com)最多支持投递 2 个职位"),
    "美格智能": (2, "官网加入我们专栏与大区HR邮箱直收(hr_sh@meigsmart.com)，建议申请 1-2 个"),
    "长电科技": (2, "51job专属平台“芯火计划”最多可申请 2 个技术志愿"),
    "极智嘉": (2, "Moka系统每位同学最多申请 2 个职位，第一志愿优先，支持服从调剂"),
    "远景科技": (2, "远景专属全球招聘系统最多支持填报 2 个志愿"),
    "极视角": (2, "校招门户支持申请 1-2 个视觉算法与工程职位"),
    "第四范式": (2, "校招官网每人最多投递 2 个职位，企业级大模型与平台优先"),
    "科大讯飞": (2, "北森系统每人最多投递 2 个职位（第一志愿优先初筛，不通过流转第二志愿）"),
    "秘塔科技": (1, "极客扁平团队，无硬性数量限制，官方强烈建议聚焦投递 1 个最匹配方向至官方邮箱"),
    "MiniMax": (2, "飞书招聘系统每位同学最多可申请 2 个职位"),
    "智元机器人": (3, "【建议不超过2-3个核心意向】飞书招聘系统支持多岗位投递，官方建议一次性投递2-3个核心技术意向"),
    "宇树科技": (2, "官网与直招通道最多申请 2 个技术方向"),
    "追觅科技": (3, "【最多3个岗位】官方明确每位同学最多可投递3个岗位，根据第一意愿优先安排筛选及面试"),
    "石头科技": (None, "【不设硬性上限】校招系统未设强制投递数量拦截，官方建议聚焦专业匹配度最高的1-2个岗位"),
    "地平线": (None, "【支持多岗位流转】流程非一次性死锁，前序岗位筛选流程结束后可继续投递其他合适岗位"),
    "Momenta": (2, "飞书校招系统每位候选人最多申请 2 个职位"),
    "网易有道": (2, "网易校招统一平台每位候选人最多投递 2 个职位"),
    "浩鲸科技": (2, "北森系统每届校招最多投递 2 个职位，第一志愿优先推进"),
    "朗新科技": (2, "北森系统每位候选人最多可投递 2 个志愿，按志愿顺序依次初筛"),
    "恒生电子": (2, "校招官网每人最多投递 2 个职位，支持技术平台与交易系统志愿"),
    "招银网络科技": (1, "招行招聘系统每人每批次限投 1 个岗位（投递后流程锁定，不可变更）"),
    "中兴通讯": (2, "中兴全球招聘门户最多可填报 2 个志愿"),
    "中移软件": (2, "中国移动统一招聘平台每位候选人在同一单位(云能力中心)最多填报 2 个岗位"),
    "天翼云科技有限公司": (2, "用友大易 Hotjob 系统每人最多可投递 2 个岗位"),
    "中电莱斯": (2, "Moka 系统最多填报 2 个专业研究部/所方向"),
    "国电南瑞": (2, "国网统一招聘平台每人限报 2 个分部，南瑞限投 2 个岗位"),
    "亚信科技": (2, "51job / 北森系统每人最多投递 2 个职位"),
    "焦点科技": (2, "官方校招门户支持申请 1-2 个岗位，双休外企风"),
    "金蝶软件": (2, "51job专属校招与官网每人最多投递 2 个职位"),
    "东软集团": (2, "北森系统每人最多投递 2 个岗位"),
    "中科创达": (2, "飞书招聘系统每人最多申请 2 个职位"),
    "海康威视": (2, "校招系统每位候选人可投递 2 个职位（第一志愿优先）"),
    "华泰证券": (2, "用友大易 Hotjob 系统每位候选人最多投递 2 个职位"),
    "交通银行": (2, "交行招聘系统总行与分支机构软件中心各可投递 1-2 个岗位"),
    "新大陆科技集团": (2, "北森系统每位候选人最多可投递 2 个岗位（第一志愿优先）"),
    "思必驰科技股份有限公司": (None, "【不设硬性上限】官方未设定硬性数量截断，支持官网与官方邮箱(hr@aispeech.com)直投"),
    "大华股份": (2, "校招系统最多可投递 2 个职位"),
    "凌云光": (2, "北森系统最多可投递 2 个职位"),
    "基恩士": (1, "外企极速直聘，每届校招每人仅限投递 1 个岗位（全中文面试）"),
}


def score_job_match(company_name: str, job_title: str, city: str, resp: str, reqs: str) -> tuple[float, str]:
    """Score candidate job fit (0-100) based on user's profile, skill set, and location."""
    text = f"{job_title} {resp} {reqs}".lower()
    score = 70.0
    reasons = []

    # 1. Domain Match
    # Quality / Testing / CI / Automation (Highest Match)
    if any(k in text for k in ["测试", "qa", "质量", "自动化", "pytest", "playwright", "回归"]):
        score += 18.0
        reasons.append("自动化测试与质量门禁完全对位 (Pytest/Playwright/CI)")
    # AI / Agent / RAG (Highest Match)
    elif any(k in text for k in ["agent", "rag", "大模型", "智能体", "prompt", "fastapi", "llm"]):
        score += 18.0
        reasons.append("AI Agent 编排与 RAG 应用工程完全契合")
    # Data Engineering / Python / ETL
    elif any(k in text for k in ["数据", "etl", "pandas", "sql", "中台"]):
        score += 14.0
        reasons.append("Python 数据工程与清洗分析对位")
    # Linux / DevOps / Cloud / SRE / Technical Support / FAE
    elif any(k in text for k in ["fae", "技术支持", "运维", "sre", "云原生", "docker", "linux", "部署"]):
        score += 12.0
        reasons.append("Linux/Docker 容器与技术支持排障对位")
    # General Backend / Embedded
    elif any(k in text for k in ["嵌入式", "后端", "开发", "软件"]):
        score += 8.0
        reasons.append("通用软件与嵌入式系统工程基础对口")

    # 2. Tech Stack match bonus
    if any(k in text for k in ["python", "shell", "docker", "linux", "api", "git"]):
        score += 5.0

    # 3. Location advantage
    if "常州" in city:
        score += 6.0
        reasons.append("常州主场优势 (常州大学本地, 0通勤与面试成本)")
    elif any(c in city for c in ["无锡", "苏州"]):
        score += 3.0
        reasons.append("苏锡核心都市圈，紧邻常州")
    elif "南京" in city:
        score += 2.0
        reasons.append("南京软件谷/高校集中地")

    # 4. Filter out mismatched positions (negative signals)
    if any(k in text for k in ["硕士及以上", "博士", "预训练模型研发", "底层算子优化", "芯片设计", "layout"]):
        if "硕士" in text and "本科" not in text:
            score -= 15.0
            reasons.append("学历偏好硕博，竞争强度高")
    if any(k in text for k in ["硬件工程师", "射频", "电路原理图", "pcb", "电磁兼容"]):
        score -= 10.0
        reasons.append("偏纯硬件/电路，软硬件跨度较大")

    # Clamp score
    final_score = min(98.0, max(50.0, score))
    reason_str = "；".join(reasons) if reasons else "通用技术岗位匹配"
    return round(final_score, 1), reason_str


def main():
    conn = get_db()

    # 1. Update companies application limits only if empty or unverified
    comps_updated = 0
    for cname, (max_apps, rules) in COMPANY_RULES.items():
        clean_name = cname.split("(")[0].split("（")[0].strip()
        rows = conn.execute(
            "SELECT id, name, campus_application_rules FROM companies WHERE name=? OR alias=? OR name LIKE ? OR alias LIKE ?",
            (cname, cname, f"%{clean_name[:4]}%", f"%{clean_name[:4]}%"),
        ).fetchall()
        for r in rows:
            # 保护已核实的真实规则（包含核实依据），不被硬编码覆盖
            if r["campus_application_rules"] and "核实依据" in r["campus_application_rules"]:
                continue
            conn.execute(
                """
                UPDATE companies 
                SET max_campus_applications=?, campus_application_rules=?
                WHERE id=?
                """,
                (max_apps, rules, r["id"]),
            )
            comps_updated += 1

    # 2. Score and rank jobs per company
    companies = conn.execute("SELECT id, name FROM companies").fetchall()
    jobs_updated = 0

    for comp in companies:
        comp_id = comp["id"]
        comp_name = comp["name"]

        # Get all jobs for this company
        jobs = conn.execute(
            """
            SELECT id, job_title, city, responsibilities, requirements, status
            FROM jobs 
            WHERE company_id=? OR company_name LIKE ?
            """,
            (comp_id, f"%{comp_name[:4]}%"),
        ).fetchall()

        if not jobs:
            continue

        # Score each job
        scored_jobs = []
        for j in jobs:
            weight, reason = score_job_match(
                comp_name,
                j["job_title"],
                j["city"] or "",
                j["responsibilities"] or "",
                j["requirements"] or "",
            )
            scored_jobs.append((j["id"], weight, reason, j["status"]))

        # Sort jobs by weight DESC
        scored_jobs.sort(key=lambda x: x[1], reverse=True)

        # Assign recommendation_rank (1, 2, 3...) and priority
        for rank, (jid, weight, reason, status) in enumerate(scored_jobs, 1):
            priority = 1 if rank <= 2 else (2 if rank <= 4 else 3)
            conn.execute(
                """
                UPDATE jobs 
                SET recommendation_weight=?, 
                    recommendation_rank=?, 
                    recommendation_reason=?,
                    priority=?
                WHERE id=?
                """,
                (weight, rank, f"【第{rank}志愿推荐】{reason}", priority, jid),
            )
            jobs_updated += 1

    conn.commit()
    conn.close()

    print(f"Completed! Updated {comps_updated} companies with application limits, and scored {jobs_updated} jobs with ranking weights.")


if __name__ == "__main__":
    main()
