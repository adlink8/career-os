"""Re-scrape and ingest 100% real Ninebot campus jobs from live Moka ATS.

Source portal: https://join.ninebot.com/campus-recruitment/ninebot/45627#/page/%E7%83%AD%E6%8B%9B%E8%81%8C%E4%BD%8D
Single source of truth: data/career_jobs.sqlite.
"""

from __future__ import annotations

import base64
import http.cookiejar
import json
import re
import sqlite3
import sys
import urllib.request
from html import unescape
from pathlib import Path

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ROOT = Path("D:/ADLINK/Myproject/career-os")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db

sys.stdout.reconfigure(encoding="utf-8")


def decrypt_moka(data_b64: str, necromancer: str, aes_iv: str) -> dict:
    key = necromancer.encode("utf-8")
    iv = aes_iv.encode("utf-8")
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    ciphertext = base64.b64decode(data_b64)
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return json.loads((unpadder.update(padded) + unpadder.finalize()).decode("utf-8"))


def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", raw_html)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def split_resp_reqs(text: str) -> tuple[str, str, str]:
    """Split clean JD text into responsibilities, requirements, and education requirement."""
    resp = text
    reqs = ""
    edu_req = "本科及以上"

    if "任职要求" in text or "任职资格" in text:
        parts = re.split(r"任职要求[:：]?|任职资格[:：]?", text, maxsplit=1)
        resp = parts[0].replace("岗位职责：", "").replace("工作职责：", "").strip()
        reqs = parts[1].strip()
    elif "岗位职责" in text:
        resp = text.replace("岗位职责：", "").replace("工作职责：", "").strip()

    if "硕士" in reqs or "研究生" in reqs:
        if "本科" not in reqs:
            edu_req = "硕士及以上"
    elif "大专" in reqs:
        edu_req = "大专及以上"

    return resp, reqs, edu_req


def score_real_job(title: str, city: str, resp: str, reqs: str, edu: str) -> tuple[float, str]:
    text = f"{title} {resp} {reqs}".lower()
    score = 70.0
    reasons = []

    # Domain
    if any(k in text for k in ["测试", "qa", "质量", "自动化", "pytest", "回归"]):
        score += 20.0
        reasons.append("自动化测试与系统质量保障高度契合")
    elif any(k in text for k in ["ai", "大模型", "智能体", "数据分析", "算法"]):
        score += 18.0
        reasons.append("AI 应用开发与数据分析对位")
    elif any(k in text for k in ["嵌入式", "电控", "驱动", "mcu", "单片机"]):
        score += 12.0
        reasons.append("嵌入式软件与系统开发工程对位")
    elif any(k in text for k in ["应用工程师", "信息化", "基础架构", "运维", "it"]):
        score += 14.0
        reasons.append("企业数字化系统与 IT 基础架构支持对口")

    # Location bonus
    if "常州" in city or "武进" in city or "新北" in city:
        score += 8.0
        reasons.append("常州主场优势 (武进/新北研发制造中心，0试错成本)")
    elif "北京" in city:
        score += 2.0
        reasons.append("九号北京总部研发中心")

    # Education check
    if edu == "硕士及以上":
        score -= 10.0
        reasons.append("JD 标明优先/要求硕士，本科竞争难度稍高")
    else:
        score += 4.0
        reasons.append("明确招募统招本科生")

    final_score = min(98.0, max(55.0, score))
    return round(final_score, 1), "；".join(reasons)


def main():
    conn = get_db()

    # 1. Update Ninebot portal URL in companies table
    live_portal = "https://join.ninebot.com/campus-recruitment/ninebot/45627#/page/%E7%83%AD%E6%8B%9B%E8%81%8C%E4%BD%8D"
    rules = "Moka 系统每位候选人最多可申请 2 个职位（第一志愿优先筛选，第一志愿结束后流转第二志愿）"

    comp_row = conn.execute(
        "SELECT id FROM companies WHERE name LIKE '%九号%' OR alias LIKE '%九号%' OR alias LIKE '%Ninebot%'"
    ).fetchone()
    if not comp_row:
        print("Ninebot company not found in companies table!")
        return
    comp_id = comp_row[0]

    conn.execute(
        """
        UPDATE companies 
        SET campus_url=?, max_campus_applications=2, campus_application_rules=?
        WHERE id=?
        """,
        (live_portal, rules, comp_id),
    )
    print(f"Updated Ninebot in companies table (ID: {comp_id}) with live portal: {live_portal}")

    # 2. Setup HTTP Session to fetch Moka
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Referer": "https://join.ninebot.com/campus-recruitment/ninebot/45627",
    }
    opener.open(urllib.request.Request("https://join.ninebot.com/campus-recruitment/ninebot/45627", headers=headers))

    # Read pre-fetched 261 all_jobs
    with open("scratch/ninebot_all_real_jobs.json", "r", encoding="utf-8") as f:
        all_jobs = json.load(f)

    # Filter target engineering / technical / IT jobs
    target_keywords = [
        "测试", "质量", "软件", "嵌入式", "电控", "ai", "数据", "开发", 
        "应用工程师", "基础架构", "运维", "it", "算法", "网络", "系统"
    ]

    selected_raw = []
    for j in all_jobs:
        title = j.get("title", "")
        if any(k in title.lower() for k in target_keywords):
            # Prioritize Changzhou and core tech
            selected_raw.append(j)

    print(f"Total matching real technical jobs to ingest: {len(selected_raw)}")

    # Clear old synthetic Ninebot jobs
    deleted = conn.execute("DELETE FROM jobs WHERE company_id=?", (comp_id,)).rowcount
    print(f"Cleared {deleted} previous synthetic/outdated jobs for Ninebot.")

    # Ingest each real job
    ingested_jobs = []
    for idx, j in enumerate(selected_raw, 1):
        jid = j.get("id")
        title = j.get("title")
        loc_objs = j.get("locations", [])
        city_names = [l.get("cityName") for l in loc_objs if isinstance(l, dict) and l.get("cityName")]
        if any(c in ["武进区", "新北区", "常州"] for c in city_names):
            city_str = f"江苏省·常州市 ({'/'.join(city_names)})"
        elif any(c in ["海淀区", "北京"] for c in city_names):
            city_str = f"北京市 ({'/'.join(city_names)})"
        elif any(c in ["南山区", "深圳"] for c in city_names):
            city_str = f"广东省·深圳市 ({'/'.join(city_names)})"
        else:
            city_str = "/".join(city_names) if city_names else "常州/北京"

        apply_url = f"https://join.ninebot.com/campus-recruitment/ninebot/45627#/job/{jid}"

        # Fetch detailed description from Moka API
        url = "https://join.ninebot.com/api/outer/ats-apply/website/job"
        p = {"jobId": jid, "orgId": "ninebot", "siteId": "45627"}
        try:
            req = urllib.request.Request(url, data=json.dumps(p).encode("utf-8"), headers=headers, method="POST")
            res = opener.open(req)
            resp_obj = json.loads(res.read().decode("utf-8"))
            dec = decrypt_moka(resp_obj["data"], resp_obj["necromancer"], "de7c21ed8d6f50fe")
            raw_desc = dec.get("data", {}).get("jobDescription", "")
            clean_text = clean_html(raw_desc)
            resp, reqs, edu = split_resp_reqs(clean_text)
        except Exception as e:
            print(f"  Warning fetching detail for {title} ({jid}): {e}")
            resp = "详见官方招聘门户 JD 详情"
            reqs = ""
            edu = "本科及以上"

        weight, reason = score_real_job(title, city_str, resp, reqs, edu)
        ingested_jobs.append({
            "jid": jid,
            "title": title,
            "city": city_str,
            "resp": resp,
            "reqs": reqs,
            "edu": edu,
            "url": apply_url,
            "weight": weight,
            "reason": reason,
        })
        print(f"[{idx}/{len(selected_raw)}] Fetched & processed: {title} | {city_str} | 权重: {weight}分")
    ingested_jobs.sort(key=lambda x: x["weight"], reverse=True)

    for rank, item in enumerate(ingested_jobs, 1):

        priority = 1 if rank <= 2 else (2 if rank <= 5 else 3)
        match_lvl = "高匹配" if item["weight"] >= 90 else "匹配"
        conn.execute(

            """
            INSERT INTO jobs (
                company_id, company_name, job_title, category, city,
                salary_text, education_req, english_req, match_level,
                responsibilities, requirements, application_url, status,
                priority, source_plugin, source_job_id,
                recommendation_weight, recommendation_rank, recommendation_reason,
                updated_at
            ) VALUES (
                ?, '九号公司 (Ninebot)', ?, '校园招聘', ?,
                '面议 (常州研发福利)', ?, '', ?,
                ?, ?, ?, '待投递',
                ?, 'ninebot-live-moka', ?,
                ?, ?, ?, CURRENT_TIMESTAMP
            )
            """,
            (
                comp_id,
                item["title"],
                item["city"],
                item["edu"],
                match_lvl,
                item["resp"],
                item["reqs"],
                item["url"],
                priority,
                item["jid"],
                item["weight"],
                rank,
                f"【第{rank}志愿推荐】{item['reason']}",
            ),
        )

    conn.commit()
    conn.close()
    print(f"\nSUCCESS! Ingested {len(ingested_jobs)} 100% REAL Ninebot positions with direct live links.")



if __name__ == "__main__":
    main()
