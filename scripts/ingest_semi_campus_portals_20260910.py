"""幂等写入江苏附近半导体中小厂校招门户。只改 companies，不编造岗位 JD。

范围：江苏 + 紧邻上海。大厂/央企/外企巨头不入库。
对口优先：FAE / 应用 / 技术支持 / 交付；纯 IC 设计仅作门户收录并注明。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db  # noqa: E402

# 半导体超大厂 / 代工封测巨头 / 设备巨头：不入库、重跑也不加回来。
EXCLUDE_NAMES = {
    "中芯国际",
    "华为",
    "海思",
    "台积电",
    "三星",
    "中国三星",
    "SK海力士系统集成电路（无锡）",
    "长江存储",
    "长鑫存储",
    "Intel",
    "NVIDIA中国",
    "高通",
    "ASML",
    "阿斯麦",
    "北方华创",
    "中微公司",
    "中微半导体",
    "长电科技 (JCET)",
    "通富微电",
    "华润微",
    "华虹半导体",
    "京东方",
    "中兴通讯",
    "中兴微电子",
    "联发科技",
    "大疆",
    "新凯来",
    "兆易创新",
    "晶晨半导体 (Amlogic)",
    "中科芯",
}

PORTALS = [
    {
        "name": "纳芯微电子 (NOVOSENSE)",
        "alias": "纳芯微",
        "city": "苏州/上海/南京/深圳",
        "website": "https://www.novosns.com/",
        "campus_url": "https://careers.novosns.com/campus",
        "industry": "模拟/混合信号芯片",
        "company_type": "科创板上市",
        "campus_application_rules": "苏州总部。校招站已开（营销/应用类相对口）。第三方写2027届纳芯微校园招聘已启动，投前在站内核届别与FAE/应用岗。",
    },
    {
        "name": "南芯科技 (Southchip)",
        "alias": "南芯",
        "city": "上海/南京/深圳",
        "website": "https://www.southchip.com/",
        "campus_url": "https://nanxin.zhiye.com/campus/jobs",
        "industry": "电源管理/模拟芯片",
        "company_type": "科创板上市",
        "campus_application_rules": "2027校招已开。可见现场应用工程师、系统应用工程师、技术销售；另有模拟/数字IC设计。本科可投应用/销售，设计岗常硕博。",
    },
    {
        "name": "乐鑫科技 (Espressif)",
        "alias": "乐鑫",
        "city": "上海/苏州",
        "website": "https://www.espressif.com/",
        "campus_url": "https://www.espressif.com/zh-hans/join-us/job-search",
        "industry": "IoT Wi-Fi/蓝牙芯片",
        "company_type": "科创板上市专精特新",
        "campus_application_rules": "2027秋季校园招聘曾启动，岗位偏芯片设计/嵌入式软件。城市含上海苏州。官网筛选校招分类；部分渠道写网申已截止，投前再核。",
    },
    {
        "name": "思瑞浦 (3PEAK)",
        "alias": "思瑞浦",
        "city": "上海/深圳",
        "website": "https://www.3peakic.com.cn/",
        "campus_url": "https://app.mokahr.com/campus-recruitment/3peakic/67894",
        "industry": "模拟芯片",
        "company_type": "科创板上市",
        "campus_application_rules": "2027正式批。可见芯片应用工程师、研发测试；其余多为模拟设计/版图。上海对口应用岗。",
    },
    {
        "name": "卓胜微 (Maxscend)",
        "alias": "卓胜微",
        "city": "无锡",
        "website": "https://www.maxscend.com/",
        "campus_url": "https://maxscend.zhiye.com/campus",
        "industry": "射频芯片",
        "company_type": "无锡本土上市",
        "campus_application_rules": "无锡总部。校招门户在；公开简章多见2026春招。2027批次以站内岗位为准，偏射频/工艺，应用岗需站内再筛。",
    },
    {
        "name": "芯朋微电子 (Chipown)",
        "alias": "芯朋微",
        "city": "无锡/苏州/上海",
        "website": "https://www.chipown.com.cn/",
        "campus_url": "https://www.chipown.com.cn/cn/jobxylist/213.html",
        "industry": "功率/电源芯片",
        "company_type": "科创板上市",
        "campus_application_rules": "无锡总部。校招页2026-07更新，含应用工程师、系统应用工程师（无锡/苏州/上海）。正式校招应用岗写硕博；2027本科可见验证/销售实习。",
    },
    {
        "name": "华兴源创 (HYC)",
        "alias": "华兴源创",
        "city": "苏州",
        "website": "https://www.hyc.cn/",
        "campus_url": "https://szhyc.zhiye.com/Campus",
        "industry": "半导体/显示检测设备",
        "company_type": "科创板上市专精特新",
        "campus_application_rules": "苏州。门户可开；历史有应用开发工程师/销售培训生。确认过2026届；2027岗未在静态页写死，投前核届别。备链钉钉Moka campus-recruitment/hyc。",
    },
    {
        "name": "恒玄科技 (Bestechnic)",
        "alias": "恒玄",
        "city": "上海",
        "website": "https://www.bestechnic.com/",
        "campus_url": "https://bestechnic.zhiye.com/campus/jobs",
        "industry": "AIoT/智能音频芯片",
        "company_type": "科创板上市",
        "campus_application_rules": "上海总部。2027秋招已启动，含产品工程师(PE)/硬件。多数岗偏芯片与嵌入式；PE/硬件相对口。备链 Moka campus_apply/bestechnic/41174。",
    },
    {
        "name": "晶丰明源 (BPS)",
        "alias": "晶丰明源",
        "city": "上海/南京",
        "website": "https://www.bpsemi.com/",
        "campus_url": "https://bpsemi.zhiye.com/campus/jobs",
        "industry": "电源管理/电机驱动芯片",
        "company_type": "科创板上市",
        "campus_application_rules": "上海总部，南京有技术销售/算法。校招门户在。2027届宣讲会已出现；FAE/应用/技术销售相对口。站内核届别。",
    },
    {
        "name": "矽典微 (ICLegend)",
        "alias": "矽典微",
        "city": "南京/苏州/上海",
        "website": "https://www.iclegend.com/",
        "campus_url": "https://www.iclegend.com/",
        "industry": "毫米波/射频芯片",
        "company_type": "专精特新",
        "campus_application_rules": "2027校招第三方已收录（南京/上海/苏州/深圳）。官网投递+hr@iclegend.com。可见应用硬件工程师；其余多为射频/数字IC。无独立ATS子域。",
    },
    {
        "name": "中茵微电子 (JoinSilicon)",
        "alias": "中茵微",
        "city": "南京/上海",
        "website": "https://www.joinsilicon.com/",
        "campus_url": "https://joinsilicon.zhiye.com/campus/jobs",
        "industry": "高速接口IP/SoC",
        "company_type": "专精特新",
        "campus_application_rules": "2027提前批已开。岗位几乎全是SoC/SerDes/数字后端，对口运维/FAE弱，只作门户库存。勿当海投首选。",
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
    inserted = updated = skipped = excluded = 0
    for item in PORTALS:
        if item["name"] in EXCLUDE_NAMES:
            excluded += 1
            print(f"[EXCLUDE 大厂] {item['name']}")
            continue
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
    for t in ("companies", "jobs", "job_targets", "applications"):
        print(f"{t}\t{conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
    print(
        f"inserted\t{inserted}\nupdated\t{updated}\nskipped\t{skipped}\nexcluded\t{excluded}\nbatch\t{len(PORTALS)}"
    )
    conn.close()


if __name__ == "__main__":
    main()
