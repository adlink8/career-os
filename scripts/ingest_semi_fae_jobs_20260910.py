"""把半导体门户里已核到的 FAE/应用/技术销售岗写入 jobs + platform_recruitment_leads。

只收录江苏附近城市、有公开职责原文的校招岗。不编造 JD。
未在本次抓到 2027 应用岗正文的公司（乐鑫/华兴源创/卓胜微/矽典微/中茵微/纳芯微/恒玄）不写 jobs。
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

# company_alias -> jobs
JOBS = [
    {
        "alias": "南芯",
        "job_title": "2027校招现场应用工程师(J11375)",
        "city": "上海",
        "salary_text": "面议",
        "education_req": "本科及以上，电子类相关专业",
        "category": "校园招聘",
        "job_category": "现场应用/FAE",
        "recruitment_type": "2027届校招",
        "graduation_range": "2027届",
        "apply_url": "https://nanxin.zhiye.com/campus/jobs",
        "source_job_id": "J11375",
        "responsibilities": (
            "1. 深入了解公司产品，推广公司方案，挖掘客户需求，配合销售一起实现产品DIN；\n"
            "2. 在客户端定位技术问题、分析问题，独立进行相关电路测试以及调试工作；\n"
            "3. 参考设计电路评审、软件编写和调试、整理推广资料及编写使用手册；\n"
            "4. 与研发、品质等部门进行有效沟通，准确传递客户需求，协调内外部资源，完成新产品的定制开发；\n"
            "5. 为代理商、客户工程师提供技术培训和技术交流；\n"
            "6. 收集市场和竞争对手的信息，为公司市场策略的制定提供参考。"
        ),
        "requirements": (
            "1. 本科及以上学历，电子类相关专业；\n"
            "2. 扎实的电路专业知识和较强的动手能力；\n"
            "3. 熟练使用PCB绘图软件；\n"
            "4. 工作态度积极进取，乐于迎接挑战和压力；\n"
            "5. 出色的沟通交流能力，信息收集和分析能力，高度的责任感及团队合作精神。"
        ),
        "notes": "门户城市还列深圳/北京；本次只记上海。来源 nanxin.zhiye.com/campus/jobs 2026-06-09。",
        "weight": 82,
        "reason": "2027正式校招FAE，本科可投，城市含上海。",
    },
    {
        "alias": "南芯",
        "job_title": "2027校招技术销售工程师(J11376)",
        "city": "上海",
        "salary_text": "面议",
        "education_req": "本科及以上（门户未写死专业）",
        "category": "校园招聘",
        "job_category": "技术销售",
        "recruitment_type": "2027届校招",
        "graduation_range": "2027届",
        "apply_url": "https://nanxin.zhiye.com/campus/jobs",
        "source_job_id": "J11376",
        "responsibilities": (
            "1. 根据公司年度业绩目标，制定销售计划，执行并完成销售任务；\n"
            "2. 推广公司产品，跟进支持客户项目，挖掘产品机会点；\n"
            "3. 协调并推动内部研发及FAE资源，完成技术支持，制定价格策略，实现产品DIN。"
        ),
        "requirements": "门户列表页未给出完整任职资格原文。投前点进 JD 核专业与学历。",
        "notes": "门户城市还列深圳/北京；本次只记上海。任职资格原文不完整，不补写。",
        "weight": 70,
        "reason": "2027技术销售，上海可投；职责已核，任职资格不全。",
    },
    {
        "alias": "南芯",
        "job_title": "2027校招系统应用工程师(J11277)",
        "city": "上海/南京",
        "salary_text": "面议",
        "education_req": "本科及以上，电力电子/电气/电子信息/自动化/仪器仪表等相关专业",
        "category": "校园招聘",
        "job_category": "系统应用",
        "recruitment_type": "2027届校招",
        "graduation_range": "2027届",
        "apply_url": "https://nanxin.zhiye.com/campus/jobs",
        "source_job_id": "J11277",
        "responsibilities": (
            "1. 参与市场调研，新产品的具体定义和后续Roadmap规划；\n"
            "2. 负责公司产品性能的测试、验证和相关问题Debug；\n"
            "3. 设计公司产品EVM并撰写推广过程中相关技术文档；\n"
            "4. 为前端销售/FAE团队及客户提供技术培训和技术支持。"
        ),
        "requirements": (
            "1. 本科及以上学历，电力电子、电气工程、电子信息、自动化、仪器仪表等相关专业；\n"
            "2. 优秀的专业基础知识和学习能力；\n"
            "3. 自驱力和执行力强，有好奇心和责任心。"
        ),
        "notes": "门户还列成都/北京/深圳珠海/西安；本次只记上海/南京。",
        "weight": 80,
        "reason": "2027系统应用，含南京/上海，本科可投。",
    },
    {
        "alias": "芯朋微",
        "job_title": "应用工程师（校招）",
        "city": "无锡/苏州/上海",
        "salary_text": "面议",
        "education_req": "硕士/博士",
        "category": "校园招聘",
        "job_category": "应用工程师",
        "recruitment_type": "校招正式岗",
        "graduation_range": "应届校招（学历写硕博）",
        "apply_url": "https://www.chipown.com.cn/cn/applyxy/213/137.html",
        "source_job_id": "chipown-213-137",
        "responsibilities": (
            "1）以扎实的电力电子专业理论知识,全面评估分析IC新品，并协助设计部门Debug；\n"
            "2）搭建功率类芯片的系统级模型，进行系统仿真，分析和设计芯片应用参考方案;\n"
            "3）负责功率类IC的DEMO系统、应用系统的调试和优化;\n"
            "4）根据相关应用设备的系统架构和技术特点，制定新IC产品开发规格;\n"
            "5）协同处理与芯片自身有关的技术客诉问题。"
        ),
        "requirements": "官网校招页写学历：硕士/博士。本科 CS 不匹配，勿海投。",
        "notes": "官网 2026-07-31 发布。本科请看同司销售实习。",
        "weight": 45,
        "reason": "应用岗对口但写死硕博，本科仅作库存。",
    },
    {
        "alias": "芯朋微",
        "job_title": "系统应用工程师（校招）",
        "city": "无锡/苏州/上海",
        "salary_text": "面议",
        "education_req": "硕士/博士",
        "category": "校园招聘",
        "job_category": "系统应用",
        "recruitment_type": "校招正式岗",
        "graduation_range": "应届校招（学历写硕博）",
        "apply_url": "https://www.chipown.com.cn/cn/applyxy/213/139.html",
        "source_job_id": "chipown-213-139",
        "responsibilities": (
            "1）负责电源芯片系统级方案架构设计，针对工控、家电、快充、储能、适配器等场景输出整体系统解决方案；\n"
            "2）研究行业新标准、新拓扑、能效规范、EMC安规要求，开展前沿技术预研与方案迭代；\n"
            "3）负责多芯片组合应用、系统性能优化、整机功耗/温升/稳定性评估，输出高端系统化技术方案；\n"
            "4）对接重点大客户、头部项目，负责核心项目的系统方案定义、技术评审、关键难点攻关；\n"
            "5）联动研发、产品、AE团队，制定产品应用路线图，指导AE落地客户端技术导入，沉淀标准化系统方案库。"
        ),
        "requirements": "官网校招页写学历：硕士/博士。",
        "notes": "官网 2026-07-31 发布。",
        "weight": 40,
        "reason": "系统应用对口但硕博门槛。",
    },
    {
        "alias": "芯朋微",
        "job_title": "销售实习生",
        "city": "无锡",
        "salary_text": "面议",
        "education_req": "2027届应届生(本科)",
        "category": "校园招聘",
        "job_category": "技术销售实习",
        "recruitment_type": "实习",
        "graduation_range": "2027届本科",
        "apply_url": "https://www.chipown.com.cn/cn/applyxy/417/178.html",
        "source_job_id": "chipown-417-178",
        "responsibilities": (
            "1）根据公司销售策略目标，突破终端客户的商务关系，推动内部相关部门满足客户需求;\n"
            "2）按年度销售目标，深挖细分标杆客户的项目机会，依据标杆客户拓展细分市场份额占比（行业标杆衍生机会）;\n"
            "3）代理商的管理：落实报备制度、合理报价、财务风险把控、及时回款、做好需求计划;\n"
            "4）日常销售工作管理（客户拜访、合同谈判、订单对接、重点项目推动）;\n"
            "5）其他上级指派工作。"
        ),
        "requirements": "学历：2027届应届生(本科)。实习时间：6-12个月。",
        "notes": "官网 2026-07-09 发布。本科可投的本地销售入口。",
        "weight": 78,
        "reason": "无锡本地、2027本科、销售实习，门槛对齐。",
    },
    {
        "alias": "思瑞浦",
        "job_title": "芯片应用工程师（2027校招）",
        "city": "上海/苏州",
        "salary_text": "面议",
        "education_req": "2027届本硕博；历史校招应用岗常见硕士",
        "category": "校园招聘",
        "job_category": "芯片应用",
        "recruitment_type": "2027届校招",
        "graduation_range": "2027届",
        "apply_url": "https://app.mokahr.com/campus-recruitment/3peakic/67894",
        "source_job_id": "3peak-ae-2027",
        "responsibilities": (
            "2027届简章研发类含芯片应用工程师。历史校招JD：公司模拟芯片产品参数指标调研，产品问题分析与调试，应用问题的解决；"
            "设计模拟芯片产品推广中配套的评估板；参与模拟芯片的测试验证，包括建立软、硬件测试与平台。"
        ),
        "requirements": (
            "2027简章面向海内外应届本科、硕士、博士。历史应用岗常见：电子技术/计算机/自动化/微电子等相关专业硕士及以上；"
            "掌握 AD、Tina、Labview、Python 等；有电路测试与示波器等仪器经验。"
        ),
        "notes": "岗位名来自2027简章（上海本地宝/牛企）。详细职责来自既往校招JD，投前以 Moka 当前正文为准。网申窗口第三方写到2026-08-31，可能滚动。",
        "weight": 72,
        "reason": "2027简章明确有应用岗，上海/苏州在范围内。",
    },
    {
        "alias": "思瑞浦",
        "job_title": "现场应用工程师（2027校招）",
        "city": "上海/苏州",
        "salary_text": "面议",
        "education_req": "2027届本硕博",
        "category": "校园招聘",
        "job_category": "现场应用/FAE",
        "recruitment_type": "2027届校招",
        "graduation_range": "2027届",
        "apply_url": "https://app.mokahr.com/campus-recruitment/3peakic/67894",
        "source_job_id": "3peak-fae-2027",
        "responsibilities": "2027届简章销售类含现场应用工程师。具体职责以 Moka 岗位页为准，本次未抓到逐条 JD。",
        "requirements": "2027届海内外应届本科、硕士、博士。投前打开 Moka 核城市与专业。",
        "notes": "仅简章级确认，无逐条职责原文。",
        "weight": 68,
        "reason": "2027简章销售类FAE，城市含上海/苏州。",
    },
    {
        "alias": "思瑞浦",
        "job_title": "技术销售管培生（2027校招）",
        "city": "上海/苏州",
        "salary_text": "面议",
        "education_req": "2027届本硕博",
        "category": "校园招聘",
        "job_category": "技术销售",
        "recruitment_type": "2027届校招",
        "graduation_range": "2027届",
        "apply_url": "https://app.mokahr.com/campus-recruitment/3peakic/67894",
        "source_job_id": "3peak-tse-2027",
        "responsibilities": "2027届简章销售类含技术销售管培生。具体职责以 Moka 岗位页为准。",
        "requirements": "2027届海内外应届本科、硕士、博士。",
        "notes": "仅简章级确认。",
        "weight": 66,
        "reason": "2027技术销售管培，本科可尝试。",
    },
    {
        "alias": "晶丰明源",
        "job_title": "技术销售工程师（2027校招）",
        "city": "上海",
        "salary_text": "15000-25000",
        "education_req": "本科可投（宣讲会列微电子/电子信息等，不限写死）",
        "category": "校园招聘",
        "job_category": "技术销售",
        "recruitment_type": "2027届校招",
        "graduation_range": "2027届",
        "apply_url": "https://bpsemi.zhiye.com/campus/jobs",
        "source_job_id": "bps-tse-2027-sh",
        "responsibilities": (
            "1、通过对客户市场及公司策略的了解，制定年度销售策略及计划；\n"
            "2、掌握客户的产品知识及公司的产品知识并能够独立进行客户拜访并做产品介绍；\n"
            "3、掌握客户市场、产品及策略，了解客户组织结构及决策人，与客户建立互信；\n"
            "4、负责客户管理、计划和运营，协调公司内部资源来推动产品业务的成长；\n"
            "5、定期客户拜访，寻找新的商业机会，进行产品与方案的推广。"
        ),
        "requirements": "电子相关专业本科及以上，也欢迎其他专业优秀毕业生；学习能力强，愿意接受挑战；热爱销售工作，人际敏感度高。",
        "notes": "2027届宣讲会职位表（厦大就业网）给出口径与薪资。职责原文来自公司历年校招简章同名岗，投前以智联当前JD为准。",
        "weight": 84,
        "reason": "2027宣讲会明确技术销售，上海，本科，薪资可见。",
    },
    {
        "alias": "晶丰明源",
        "job_title": "现场应用工程师（FAE）（2027校招）",
        "city": "上海",
        "salary_text": "13000-20000",
        "education_req": "硕士（宣讲会专业列集成电路/电子信息）",
        "category": "校园招聘",
        "job_category": "现场应用/FAE",
        "recruitment_type": "2027届校招",
        "graduation_range": "2027届",
        "apply_url": "https://bpsemi.zhiye.com/campus/jobs",
        "source_job_id": "bps-fae-2027-sh",
        "responsibilities": (
            "1、协助市场部参与芯片的定义、评估和市场推广；\n"
            "2、协同销售团队，完成客户项目的选型，验证，测试，设计、及量产；\n"
            "3、解决客户反馈的各种技术问题；\n"
            "4、重要客户的项目设计及协助电源产品的生产；\n"
            "5、代理商的 FAE 培训及管理；\n"
            "6、完成销售部申请的 Demo 板。"
        ),
        "requirements": "宣讲会该岗专业列为硕士集成电路/电子信息方向。历年硬件FAE要求电气/电力电子/自动控制等本科及以上。",
        "notes": "2027宣讲会职位表确认上海FAE。职责来自历年同名岗。宣讲会写硕士，本科勿硬投。",
        "weight": 55,
        "reason": "2027 FAE 在上海，但宣讲会学历偏硕士。",
    },
    {
        "alias": "晶丰明源",
        "job_title": "应用工程师（2027校招）",
        "city": "上海",
        "salary_text": "15000-25000",
        "education_req": "本科可投（宣讲会列微电子/电子信息）",
        "category": "校园招聘",
        "job_category": "应用工程师",
        "recruitment_type": "2027届校招",
        "graduation_range": "2027届",
        "apply_url": "https://bpsemi.zhiye.com/campus/jobs",
        "source_job_id": "bps-ae-2027-sh",
        "responsibilities": (
            "历年应用工程师口径：完成芯片验证和性能测试，为芯片研发提供支持；"
            "完成芯片评估报告、芯片规格书和电气参数定义；给销售FAE提供设计指导和技术支持；设计芯片验证的实验方法和测试流程。"
        ),
        "requirements": "2027宣讲会该岗本科微电子/电子信息可投。",
        "notes": "2027宣讲会确认有应用工程师（上海）。逐条职责用历年同名岗，投前核智联正文。",
        "weight": 76,
        "reason": "2027应用岗，上海，本科，薪资可见。",
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
                    ?, 'semi-campus-20260910', ?,
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
                '在招', '中', ?, ?,
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
                f"2026-09-10 核验：{item['notes']}",
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

    conn.commit()
    n_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    n_leads = conn.execute("SELECT COUNT(*) FROM platform_recruitment_leads").fetchone()[0]
    n_semi = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE source_plugin='semi-campus-20260910'"
    ).fetchone()[0]
    print("---")
    print(f"jobs_added={jobs_added} leads_added={leads_added} skipped={skipped}")
    print(f"jobs_total={n_jobs} leads_total={n_leads} semi_jobs={n_semi}")
    conn.close()


if __name__ == "__main__":
    main()
