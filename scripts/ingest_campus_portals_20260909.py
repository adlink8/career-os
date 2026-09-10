"""幂等写入 2026-09-09 核到的校招门户。只改 companies，不编造岗位 JD。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db  # noqa: E402

PORTALS = [
    {
        "name": "南京南瑞继保电气 (NREC)",
        "alias": "南瑞继保电气",
        "city": "南京/常州",
        "website": "https://www.nrec.com/",
        "campus_url": "https://nrec.zhiye.com/campus",
        "industry": "电力保护/电力自动化",
        "company_type": "央企国企",
        "campus_application_rules": "2027秋招；技术支持/信息运维。与库内国电南瑞(job.sgepri.sgcc.com.cn)不是同一网申。",
    },
    {
        "name": "新华三集团 (H3C)",
        "alias": "新华三",
        "city": "杭州/南京/上海",
        "website": "https://www.h3c.com/",
        "campus_url": "https://career.h3c.com/campus/jobs",
        "industry": "网络/云计算/数字化",
        "company_type": "央企科技总部",
        "campus_application_rules": "2027校招门户；可见技术支持工程师（实施交付/售后）。",
    },
    {
        "name": "深信服 (Sangfor)",
        "alias": "深信服",
        "city": "深圳/南京/上海",
        "website": "https://www.sangfor.com.cn/",
        "campus_url": "https://hr.sangfor.com/campuszp",
        "industry": "网络安全/云",
        "company_type": "上市龙头",
        "campus_application_rules": "2027校招；FAE技术服务/远程技术服务。岗位表 https://hr.sangfor.com/campucompon/schoolRecruitment",
    },
    {
        "name": "帆软软件 (FanRuan)",
        "alias": "帆软",
        "city": "南京/无锡/杭州",
        "website": "https://www.fanruan.com/",
        "campus_url": "https://join.fanruan.com/campus",
        "industry": "商业智能/数据分析",
        "company_type": "民营上市公司",
        "campus_application_rules": "2027校招（毕业窗口约2026-09至2027-08）；实施/技术支持/客户交付。",
    },
    {
        "name": "阳光电源 (Sungrow)",
        "alias": "阳光电源",
        "city": "合肥/上海/南京",
        "website": "https://www.sungrowpower.com/",
        "campus_url": "https://app.mokahr.com/campus-recruitment/sungrow/94416#/",
        "industry": "新能源/光伏逆变器",
        "company_type": "上市龙头",
        "campus_application_rules": "2027全球校招正式批；技术支持/解决方案。入口站 https://jobs.sungrowpower.com/",
    },
    {
        "name": "上交所技术 (SSE Tech)",
        "alias": "上交所技术",
        "city": "上海",
        "website": "https://www.ssetech.com.cn/",
        "campus_url": "https://ssetech2026.zhaopin.com",
        "industry": "金融科技/证券IT",
        "company_type": "央企国企",
        "campus_application_rules": "2027届启事含运维服务与支持类（应用/主机/网络/数据库）。门户域名带2026，投前核届别。",
    },
    {
        "name": "ABB中国",
        "alias": "ABB",
        "city": "上海/南京",
        "website": "https://new.abb.com/cn",
        "campus_url": "https://xy.liepin.com/abb2027",
        "industry": "电气/工业自动化",
        "company_type": "外企",
        "campus_application_rules": "明确2027校园招聘，面向2026/2027届。猎聘岗表可能渲染为空；上海技术支持/售后技术服务见简章。",
    },
    {
        "name": "松下信息系统 (Panasonic IS)",
        "alias": "松下信息系统",
        "city": "无锡/上海",
        "website": "https://panasonic.cn/",
        "campus_url": "https://panasonic.cn/pdsh/campus-recuitment.html",
        "industry": "IT服务/系统集成",
        "company_type": "外企",
        "campus_application_rules": "校园招聘页经验写应届；无锡有系统实施顾问、系统运维顾问。集团另有2027届实习口径。",
    },
    {
        "name": "天合光能 (Trina Solar)",
        "alias": "天合光能",
        "city": "常州/南京",
        "website": "https://www.trinasolar.com/",
        "campus_url": "https://app.mokahr.com/campus-recruitment/trinasolar/126157",
        "industry": "光伏/新能源",
        "company_type": "常州本土上市",
        "campus_application_rules": "Moka校招站已开。2026简章有交付/海外服务/IT；2027岗需在站内再筛。",
    },
    {
        "name": "浪潮集团 (Inspur)",
        "alias": "浪潮",
        "city": "济南/苏州/南京/上海",
        "website": "https://www.inspur.com/",
        "campus_url": "http://career.inspur.com/campus2027/",
        "industry": "云计算/服务器/软件",
        "company_type": "上市老牌IT",
        "campus_application_rules": "2027校招门户已开；实施/技术支持以岗位页为准，列表可能需登录。",
    },
    {
        "name": "满帮集团",
        "alias": "满帮",
        "city": "南京",
        "website": "https://www.fulltruckalliance.com/",
        "campus_url": "https://campus.fulltruckalliance.com",
        "industry": "物流科技",
        "company_type": "纽交所+港股上市",
        "campus_application_rules": "2027校招（毕业约2026-10至2027-09）。安全/研发为主，运维未在表里点名。",
    },
    {
        "name": "软通动力 (iSoftStone)",
        "alias": "软通动力",
        "city": "上海/南京/杭州",
        "website": "https://www.isoftstone.com/",
        "campus_url": "https://career.isoftstone.com/talent/htmls/xiaoyuanzhaopin/index.html",
        "industry": "IT服务/软件交付",
        "company_type": "上市老牌IT",
        "campus_application_rules": "2027校招正式批；技术类/销售咨询/数字运营。实施运维以岗位页为准。",
    },
    {
        "name": "奇安信",
        "alias": "奇安信",
        "city": "北京/上海/南京",
        "website": "https://www.qianxin.com/",
        "campus_url": "https://campus.qianxin.com/campus/graduates",
        "industry": "网络安全",
        "company_type": "科创板上市",
        "campus_application_rules": "2027应届生校招；网申 https://app.mokahr.com/campus_apply/qianxin/29182 。运维/技服正式岗需在Moka再核。",
    },
    {
        "name": "绿盟科技 (NSFOCUS)",
        "alias": "绿盟",
        "city": "北京/南京",
        "website": "https://www.nsfocus.com.cn/",
        "campus_url": "https://www.nsfocus.com.cn/campus/",
        "industry": "网络安全",
        "company_type": "上市龙头",
        "campus_application_rules": "2027校园招聘；网申 https://app.mokahr.com/campus_apply/nsfocus/29118 。岗表JS可能未渲。",
    },
    {
        "name": "用友网络",
        "alias": "用友",
        "city": "北京/南京/上海",
        "website": "https://www.yonyou.com/",
        "campus_url": "https://career.yonyou.com/",
        "industry": "企业软件/ERP云",
        "company_type": "上市老牌IT",
        "campus_application_rules": "2027高潜/友新星实习已启动；实施顾问以实时岗位为准，非完整秋招表。",
    },
    {
        "name": "海柔创新 (Hai Robotics)",
        "alias": "海柔创新",
        "city": "上海/苏州/杭州",
        "website": "https://www.hairobotics.cn/",
        "campus_url": "https://hairobotics.zhiye.com/campus",
        "industry": "仓储机器人",
        "company_type": "独角兽",
        "campus_application_rules": "校招门户可开；仓储机器人现场实施/软件交付。2027批次以岗位页为准。",
    },
    {
        "name": "西门子中国 (Siemens)",
        "alias": "西门子",
        "city": "上海/苏州/南京/常州",
        "website": "https://www.siemens.com.cn/",
        "campus_url": "https://jobs.siemens.com.cn/siemens/position/index?recruitmentType=CAMPUSRECRUITMENT",
        "industry": "工业自动化/数字化",
        "company_type": "外企",
        "campus_application_rules": "校招岗列表已开。落地页仍可能写2026春招，点进JD核届别。IT Support未在校园页单列。介绍页 https://www.siemens.com/cn/zh/company/jobs/campus-recruiting.html",
    },
    {
        "name": "中国三星",
        "alias": "三星",
        "city": "苏州/西安/上海",
        "website": "https://semiconductor.samsung.com/about-us/careers/cn/",
        "campus_url": "http://dearsamsung.zhiye.com",
        "industry": "半导体/电子",
        "company_type": "外企",
        "campus_application_rules": "2027校园招聘（约2026-08启动）。技术工程师可见；IT Support未单列。",
    },
    {
        "name": "利尔达 (Lierda)",
        "alias": "利尔达",
        "city": "杭州/南京/无锡/上海",
        "website": "https://www.lierda.com/",
        "campus_url": "https://app135149.eapps.dingtalkcloud.com/campus-recruitment/lierda/100004103?locale=zh-CN",
        "industry": "物联网模组",
        "company_type": "科创板上市专精特新",
        "campus_application_rules": "2026春招简章面向2026-2027届；技术应用/销售含南京无锡上海。官网campus页已404，用本Moka链。",
    },
    {
        "name": "卡特彼勒中国 (Caterpillar)",
        "alias": "卡特彼勒",
        "city": "徐州",
        "website": "https://www.caterpillar.com/zh.html",
        "campus_url": "https://careers.caterpillar.com/zh/职位/r0000388302/2027校园招聘-制造运营类/",
        "industry": "工程机械/智能制造",
        "company_type": "外企",
        "campus_application_rules": "2027校园招聘-制造运营类（约投至2026-10-30）；设备/AGV现场。城市偏徐州。",
    },
    {
        "name": "菲尼克斯电气中国 (Phoenix Contact)",
        "alias": "菲尼克斯",
        "city": "南京",
        "website": "https://www.phoenixcontact.com.cn/",
        "campus_url": "https://app.mokahr.com/campus-recruitment/phoenixcontact/92633",
        "industry": "工业连接/电气",
        "company_type": "外企",
        "campus_application_rules": "Moka校招站已开。核实到的批次偏2026届；2027岗未在静态页核到。",
    },
    {
        "name": "中控技术 (SUPCON)",
        "alias": "中控",
        "city": "杭州",
        "website": "https://www.supcon.com/",
        "campus_url": "https://app.mokahr.com/campus-recruitment/supcon/148189",
        "industry": "工业自动化/流程工业软件",
        "company_type": "科创板上市",
        "campus_application_rules": "Moka校招站已开。2026简章有解决方案/实施交付；2027岗未核。",
    },
    {
        "name": "和利时 (HollySys)",
        "alias": "和利时",
        "city": "杭州/南京",
        "website": "https://www.hollysys.com/",
        "campus_url": "https://campus.hollysys.net",
        "industry": "工业自动化/轨道交通信号",
        "company_type": "港股上市IT龙头",
        "campus_application_rules": "跳转Moka campus-recruitment/hollysys/182063/。2026全球校招有项目实施；2027岗未核。",
    },
    {
        "name": "正泰集团 (CHINT)",
        "alias": "正泰",
        "city": "杭州/上海/南京",
        "website": "https://www.chint.com/",
        "campus_url": "https://campus.chint.com/campus-recruitment/chint/40745/#/jobs",
        "industry": "电气/新能源",
        "company_type": "民营上市公司",
        "campus_application_rules": "Moka校招站已开。确认过2026届；2027秋招未在静态页确认。",
    },
    {
        "name": "晶科能源 (JinkoSolar)",
        "alias": "晶科",
        "city": "上海/嘉兴",
        "website": "https://www.jinkosolar.com/",
        "campus_url": "https://app.mokahr.com/campus-recruitment/jinkosolar/41896#/home",
        "industry": "光伏",
        "company_type": "上市龙头",
        "campus_application_rules": "Moka校招站已开。2026届确认；2027岗未核。",
    },
    {
        "name": "麦格米特 (Megmeet)",
        "alias": "麦格米特",
        "city": "杭州/常熟",
        "website": "https://www.megmeet.com/",
        "campus_url": "https://megmeet.hotjob.cn",
        "industry": "电力电子/工控",
        "company_type": "民营上市公司",
        "campus_application_rules": "热招门户可开。2026简章有PLC应用/销售；2027岗未核。",
    },
    {
        "name": "台达电子 / 中达电通 (Delta)",
        "alias": "台达",
        "city": "上海/苏州/南京",
        "website": "https://www.delta-china.com.cn/",
        "campus_url": "https://www.delta-china.com.cn/zh-CN/career/campus-recruitment",
        "industry": "电力电子/智能制造",
        "company_type": "外企",
        "campus_application_rules": "校园招聘页对象应届本硕博，地点含上海/苏州/南京。页上未写死2026/2027；投递偏二维码。",
    },
    {
        "name": "SK海力士系统集成电路（无锡）",
        "alias": "SK海力士无锡",
        "city": "无锡",
        "website": "https://www.skhynix.com/",
        "campus_url": "https://job.skhynixsystemic.cn/servlet/recruit_list.view",
        "industry": "半导体",
        "company_type": "外企",
        "campus_application_rules": "有应届生招聘/Intern分类。系统开发与运维曾出现在校招表；本次列表可能为空，投前再筛。",
    },
    {
        "name": "神州数码 (Digital China)",
        "alias": "神州数码",
        "city": "北京/上海/南京",
        "website": "https://www.digitalchina.com/",
        "campus_url": "https://digitalchina.zhiye.com/campus",
        "industry": "IT分销/云计算/数字化",
        "company_type": "上市老牌IT",
        "campus_application_rules": "2027校招门户已开。历史简章含云运维/FAE；本次岗位列表可能无正文，站内再筛。",
    },
    {
        "name": "顺丰集团 / 顺丰科技",
        "alias": "顺丰科技",
        "city": "深圳/上海/南京",
        "website": "https://www.sf-express.com/",
        "campus_url": "https://campus.sf-express.com/",
        "industry": "物流科技",
        "company_type": "上市巨头",
        "campus_application_rules": "2027校招（毕业约2026-10至2027-09）。首页未点名运维；2026科技简章曾有运维开发/IT应用运维。",
    },
    {
        "name": "霍尼韦尔中国 (Honeywell)",
        "alias": "霍尼韦尔",
        "city": "上海/苏州",
        "website": "https://www.honeywell.com.cn/",
        "campus_url": "https://careers.honeywell.com/campaignPost/300002209872357",
        "industry": "自动化/航空电子",
        "company_type": "外企",
        "campus_application_rules": "2027届实习生（转正目标）。苏州有软件工程师实习；不是IT桌面运维。",
    },
]


def _find(conn, name: str, alias: str):
    return conn.execute(
        """
        SELECT id, name, alias, campus_url
        FROM companies
        WHERE name = ? OR alias = ? OR name = ? OR alias = ?
        """,
        (name, name, alias, alias),
    ).fetchone()


def main() -> None:
    conn = get_db()
    inserted = updated = skipped = 0
    for item in PORTALS:
        row = _find(conn, item["name"], item["alias"])
        if row:
            cid, old_name, _alias, old_url = row
            if (old_url or "") != item["campus_url"]:
                conn.execute(
                    """
                    UPDATE companies
                    SET campus_url=?, website=COALESCE(NULLIF(?, ''), website),
                        city=COALESCE(NULLIF(?, ''), city),
                        industry=COALESCE(NULLIF(?, ''), industry),
                        company_type=COALESCE(NULLIF(?, ''), company_type),
                        campus_application_rules=COALESCE(NULLIF(?, ''), campus_application_rules)
                    WHERE id=?
                    """,
                    (
                        item["campus_url"],
                        item["website"],
                        item["city"],
                        item["industry"],
                        item["company_type"],
                        item["campus_application_rules"],
                        cid,
                    ),
                )
                updated += 1
                print(f"[UPDATE] {old_name}: {(old_url or '')} -> {item['campus_url']}")
            else:
                skipped += 1
                print(f"[SKIP] {old_name} 链接已是最新")
            continue
        conn.execute(
            """
            INSERT INTO companies
                (name, alias, city, website, campus_url, industry, company_type, campus_application_rules)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["name"],
                item["alias"],
                item["city"],
                item["website"],
                item["campus_url"],
                item["industry"],
                item["company_type"],
                item["campus_application_rules"],
            ),
        )
        inserted += 1
        print(f"[INSERT] {item['name']} {item['campus_url']}")

    conn.commit()

    print("--- inventory ---")
    tables = [
        "companies",
        "jobs",
        "job_targets",
        "platform_recruitment_leads",
        "applications",
        "application_timeline",
        "job_page_contexts",
        "job_apply_runs",
    ]
    for t in tables:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t}\t{n}")
    print("jobs_by_status")
    for status, n in conn.execute("SELECT COALESCE(status,''), COUNT(*) FROM jobs GROUP BY status"):
        print(f"  {status}\t{n}")
    print("leads_by_status")
    for status, n in conn.execute(
        "SELECT COALESCE(status,''), COUNT(*) FROM platform_recruitment_leads GROUP BY status"
    ):
        print(f"  {status}\t{n}")
    print(f"portals_in_batch\t{len(PORTALS)}")
    print(f"inserted\t{inserted}")
    print(f"updated\t{updated}")
    print(f"skipped\t{skipped}")
    conn.close()


if __name__ == "__main__":
    main()
