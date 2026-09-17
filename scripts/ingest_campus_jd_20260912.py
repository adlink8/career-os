"""2026-09-12 用户给定 7 个校招页抓取后的入库。

门禁（全部满足才写 jobs）：
1. 职责+任职资格为门户原文，不编造
2. 江苏可核（南京/苏州/无锡/常州/昆山，或明确含南京/苏州）
3. 校招/实习，非社招年限岗
4. 学历未写死硕士
5. 方向：FAE / 应用 / 技术销售 / 技术支持
6. duty+req 合计 >= 80 字
9. 无 CET-4/六级/雅思/托福硬门槛（见 job_ingest_gate）
10. JD 不过细到像招熟手（见 job_ingest_gate）
7. 公司已在 sme_startup/applied
8. company_id+title+city 去重

未过门禁的门户只打日志，不写岗。
"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db  # noqa: E402

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
SOURCE = "campus-jd-20260912"

JOBS = [
    {
        "alias": "纳芯微",
        "job_title": "【2027届校招】技术销售工程师（ACE计划）(J11371)",
        "city": "上海/南京/苏州",
        "salary_text": "面议",
        "education_req": "本科及以上；理工科优先含计算机，经管复合专业亦欢迎",
        "category": "校园招聘",
        "job_category": "技术销售",
        "recruitment_type": "2027届校招",
        "graduation_range": "2027届",
        "apply_url": "https://www.moseeker.com/position/index/pid/3480876",
        "source_job_id": "moseeker-3480876-J11371",
        "responsibilities": (
            "1. 熟悉公司产品和服务，通过客户拜访及技术交流等方式发掘潜在机会，制定销售计划并引导公司资源投放，从而达成销售目标\n"
            "2. 深刻理解客户痛点、快速响应客户需求，为客户提供产品和服务的解决方案，助力客户商业成功并建立深度合作关系\n"
            "3. 了解市场动态、洞悉行业趋势，挖掘业务增长引擎，制定针对性的推广策略，从而驱动公司产品和解决方案竞争力提升\n"
            "4. 公司客户界面的第一责任人，从项目跟进到售后支持，全流程提高客户服务水准与交易质量，持续提升客户满意度"
        ),
        "requirements": (
            "1.本科及以上学历\n"
            "2.理工科相关专业优先，包括电子、微电子、电气、自动化、通信、计算机等。"
            "经管及复合型专业，如市场营销、国际经济与贸易、管理科学与工程、信息管理与信息系统、"
            "工业工程、商业分析等，如具备较强的技术兴趣、工程实践或科技行业项目、实习经历，"
            "或具有电子相关辅修、双学位背景，同样欢迎申请\n"
            "良好的结果导向意识；较强的逻辑分析和解决问题的能力；良好的沟通及团队协作能力；较强的自驱力、执行力及抗压能力"
        ),
        "notes": "仟寻 cid/5553471 pid/3480876 原文。城市写上海、南京、苏州等地。ACE 同门户 FAE(J11388) 写死硕士，未入库。",
        "weight": 86,
        "reason": "2027技术销售，本科含计算机，城市含南京/苏州。",
    },
    {
        "alias": "晶丰明源",
        "job_title": "应用工程师（硬件）（南京）(J10584)",
        "city": "南京",
        "salary_text": "面议",
        "education_req": "本科及以上，计算机、电子、自动化、机械、电机相关专业",
        "category": "校园招聘",
        "job_category": "应用工程师",
        "recruitment_type": "2027届校招",
        "graduation_range": "校招（CategoryId=2）",
        "apply_url": "https://bpsemi.zhiye.com/campus/detail?jobAdId=de5f89e0-ac01-4f08-96ee-bc8333731d80",
        "source_job_id": "bps-J10584",
        "responsibilities": (
            "1. 负责电机应用方案的研发（电路原理设计、PCB的Layout，PCB板打板制作、单板调试等）；\n"
            "2. 根据客户的需求能创新地提出应用电路设计思路；\n"
            "3. 协助产品线为销售及现场应用提供设计指导及技术支持；\n"
            "4. 负责MCU芯片模拟及电气性能验证与性能测试并输出评估报告及规格书参数评估；\n"
            "5. 设计MCU芯片模拟及电气性能验证的方法、测试流程；"
        ),
        "requirements": (
            "1.   本科及以上计算机、电子、自动化、机械、电机相关专业；\n"
            "2.   熟练使用 Protel、Altium Designer、Cadence (Allegro) 等工具绘制电路原理图及 PCB 图，熟练使用Labview软件更优；\n"
            "3、熟悉模拟电子与数字电子技术，熟悉单片机外围电路设计以及相关性能参数，具有一定的编程基础；\n"
            "4、熟悉电机控制器MCU硬件设计以及功率驱动电路设计更优；\n"
            "5、具有较强分析及解决问题的能力，较强的数据分析能力，良好的英语阅读能力。"
        ),
        "notes": "bpsemi.zhiye.com /api/jobad/getjobadpagelist 2026-09-12。标题自带南京。",
        "weight": 82,
        "reason": "南京校招应用，本科含计算机。",
    },
    {
        "alias": "晶丰明源",
        "job_title": "技术销售工程师（全国）(J10562)",
        "city": "全国",
        "salary_text": "面议",
        "education_req": "电子相关专业本科及以上，也欢迎其他专业优秀毕业生",
        "category": "校园招聘",
        "job_category": "技术销售",
        "recruitment_type": "校招",
        "graduation_range": "校招（CategoryId=2）",
        "apply_url": "https://bpsemi.zhiye.com/campus/detail?jobAdId=ba3a4750-7702-4ab4-8c32-2075a0664390",
        "source_job_id": "bps-J10562",
        "responsibilities": (
            "1、通过对客户市场及公司策略的了解，制定年度销售策略及计划；\n"
            "2、掌握客户的产品知识及公司的产品知识并能够独立进行客户拜访并做产品介绍；\n"
            "3、掌握客户市场、产品及策略，了解客户组织结构及决策人，与客户建立互信；\n"
            "4、负责客户管理、计划和运营，协调公司内部资源来推动产品业务的成长；\n"
            "5、定期客户拜访，寻找新的商业机会，进行产品与方案的推广；\n"
            "6、配合客户完成方案设计，进行价格谈判，以及培养和增进与客户互信关系；\n"
            "7、定期了解客户项目进展，确定准确的订单预测及备货状况分析，确保客户需求得到满足；\n"
            "8、与公司内部资源团队合作协同解决客户可能出现的各种问题和需求；\n"
            "9、按时向相应的管理层提交周/月/季度销售报告和客户状态分析。"
        ),
        "requirements": (
            "1、电子相关专业本科及以上，也欢迎其他专业优秀毕业生；\n"
            "2、学习能力强，愿意接受挑战；\n"
            "3、热爱销售工作，人际敏感度高。"
        ),
        "notes": "bpsemi 列表接口原文。城市写全国，申请时选江苏客户覆盖。上海FAE/系统应用硕士岗未入库。",
        "weight": 78,
        "reason": "校招技术销售，欢迎其他专业；全国岗，江苏可申请。",
    },
]


def dedupe_key(company: str, title: str, city: str) -> str:
    raw = f"{company.strip().lower()}|{title.strip().lower()}|{city.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main() -> None:
    conn = get_db()
    jobs_added = leads_added = skipped = 0
    for item in JOBS:
        crow = conn.execute(
            "SELECT id, name FROM companies WHERE alias=? OR name=?",
            (item["alias"], item["alias"]),
        ).fetchone()
        if not crow:
            print(f"[MISS COMPANY] {item['alias']}")
            continue
        cid, cname = crow
        dkey = dedupe_key(cname, item["job_title"], item["city"])
        exists = conn.execute(
            "SELECT id FROM jobs WHERE company_id=? AND job_title=? AND city=?",
            (cid, item["job_title"], item["city"]),
        ).fetchone()
        if exists:
            skipped += 1
            print(f"[SKIP JOB] {cname} {item['job_title']}")
        else:
            match = "高匹配" if item["weight"] >= 80 else ("匹配" if item["weight"] >= 65 else "待评估")
            prio = 1 if item["weight"] >= 80 else (2 if item["weight"] >= 65 else 3)
            conn.execute(
                """
                INSERT INTO jobs (
                    company_id, company_name, job_title, category, city,
                    salary_text, education_req, english_req, match_level,
                    responsibilities, requirements, application_url, status,
                    priority, source_plugin, source_job_id,
                    recommendation_weight, recommendation_reason, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, '', ?,
                    ?, ?, ?, '待投递',
                    ?, ?, ?,
                    ?, ?, ?
                )
                """,
                (
                    cid,
                    cname,
                    item["job_title"],
                    item["category"],
                    item["city"],
                    item["salary_text"],
                    item["education_req"],
                    match,
                    item["responsibilities"],
                    item["requirements"],
                    item["apply_url"],
                    prio,
                    SOURCE,
                    item["source_job_id"],
                    item["weight"],
                    item["reason"],
                    NOW,
                ),
            )
            jobs_added += 1
            print(f"[JOB] {cname} | {item['job_title']} | {item['city']} | w={item['weight']}")

        lead = conn.execute(
            "SELECT id FROM platform_recruitment_leads WHERE dedupe_key=?",
            (dkey,),
        ).fetchone()
        if lead:
            continue
        conn.execute(
            """
            INSERT INTO platform_recruitment_leads (
                platform, company_name, job_title, job_category, city,
                recruitment_type, graduation_range, source_url, apply_url,
                status, evidence_confidence, evidence_text, checked_at,
                notes, dedupe_key, responsibilities, requirements,
                education_requirement, jd_source_url, created_at, updated_at
            ) VALUES (
                '官网校招', ?, ?, ?, ?,
                ?, ?, ?, ?,
                '在招', '高', ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?
            )
            """,
            (
                cname,
                item["job_title"],
                item["job_category"],
                item["city"],
                item["recruitment_type"],
                item["graduation_range"],
                item["apply_url"],
                item["apply_url"],
                f"2026-09-12 核验：{item['notes']}",
                NOW,
                item["notes"],
                dkey,
                item["responsibilities"],
                item["requirements"],
                item["education_req"],
                item["apply_url"],
                NOW,
                NOW,
            ),
        )
        leads_added += 1

    # 用本次抓到的原文修正已入库但学历写错的南芯系统应用
    cur = conn.execute(
        """
        UPDATE jobs
        SET education_req = ?,
            recommendation_weight = 45,
            recommendation_reason = ?,
            match_level = '待评估',
            priority = 3,
            updated_at = ?
        WHERE source_job_id = 'J11277'
          AND job_title LIKE '%系统应用工程师(J11277)%'
        """,
        (
            "硕士及以上学历，电力电子/电气工程/自动化等相关专业（2026-09-12 门户原文）",
            "门户现文写硕士，本科勿海投。",
            NOW,
        ),
    )
    print(f"[FIX] 南芯 J11277 学历改为硕士 rows={cur.rowcount}")

    conn.commit()
    n_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    n_leads = conn.execute("SELECT COUNT(*) FROM platform_recruitment_leads").fetchone()[0]
    n_new = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE source_plugin=?", (SOURCE,)
    ).fetchone()[0]
    print("---")
    print(f"jobs_added={jobs_added} leads_added={leads_added} skipped={skipped}")
    print(f"jobs_total={n_jobs} leads_total={n_leads} new_source={n_new}")
    conn.close()


if __name__ == "__main__":
    main()
