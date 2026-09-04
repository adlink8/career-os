"""Import public platform-backed Jiangsu campus recruitment leads.

This is intentionally a curated evidence import rather than a crawler dump.
Every row keeps the original platform URL, application URL (when present),
explicit referral code, and the text that proves the Jiangsu city/recruitment
claim.  Rows are upserted by a deterministic source/role key so the import is
safe to repeat.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _dedupe_key(row: dict[str, str]) -> str:
    payload = "|".join(
        row[field].strip().casefold()
        for field in (
            "platform",
            "company_name",
            "job_title",
            "city",
            "recruitment_type",
            "source_url",
            "referral_code",
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Checked on 2026-09-04.  Dates are left blank when the public page only shows
# a relative timestamp (for example, "昨天").  Referral codes are copied only
# when the public post states them explicitly; no code is inferred.
LEADS: list[dict[str, str]] = [
    {
        "platform": "牛客网",
        "company_name": "九识智能",
        "job_title": "算法/研发/产品/硬件等校招岗位",
        "job_category": "算法/研发/产品/硬件",
        "city": "苏州",
        "recruitment_type": "校招",
        "graduation_range": "2027届",
        "source_url": "https://www.nowcoder.com/feed/main/detail/6e8cda12ca704e8d94de17bfa32b70df?urlSource=home-api",
        "apply_url": "",
        "referral_code": "NTAdpgL",
        "posted_at": "",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "公开帖明确写明2027校招、工作地点覆盖苏州，并列出算法、研发、产品、硬件等方向；帖子同时给出内推码NTAdpgL。",
        "notes": "岗位城市包含江苏；原帖未给出绝对发布日期，投递前在官网复核岗位是否仍开放。",
    },
    {
        "platform": "牛客网",
        "company_name": "九识智能",
        "job_title": "多传感器标定/模型训练优化/数据闭环/前端实习",
        "job_category": "算法/研发实习",
        "city": "苏州",
        "recruitment_type": "实习",
        "graduation_range": "在校生（帖子同时覆盖2027校招）",
        "source_url": "https://www.nowcoder.com/feed/main/detail/6e8cda12ca704e8d94de17bfa32b70df?urlSource=home-api",
        "apply_url": "",
        "referral_code": "NTAdpgL",
        "posted_at": "",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "同一公开帖明确写出实习方向包括多传感器标定、模型训练优化、数据闭环、前端开发，并说明工作地点覆盖苏州，内推码为NTAdpgL。",
        "notes": "实习岗位是否仍有HC需以九识官网实时列表为准。",
    },
    {
        "platform": "牛客网",
        "company_name": "满帮集团",
        "job_title": "算法/全栈/数据/安全/产品等校招岗位",
        "job_category": "算法/研发/数据/安全/产品",
        "city": "南京/苏州",
        "recruitment_type": "秋招",
        "graduation_range": "2027届（2026.10-2027.09毕业）",
        "source_url": "https://www.nowcoder.com/discuss/924297939046912000",
        "apply_url": "https://app.mokahr.com/campus_apply/manbang/94191?recommendCode=DSQTQNMK#/jobs",
        "referral_code": "DSQTQNMK",
        "posted_at": "2026-08-26",
        "deadline": "2026-11-30",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "公开帖明确列出工作地点南京、苏州，招聘对象为2027届，网申周期8.26-11.30，并给出内推码DSQTQNMK和官方投递链接。",
        "notes": "集团总部不在江苏；此处按岗位城市纳入。",
    },
    {
        "platform": "牛客网",
        "company_name": "合合信息",
        "job_title": "算法/技术/产品/数据等校招岗位",
        "job_category": "算法/研发/产品/数据",
        "city": "苏州",
        "recruitment_type": "秋招",
        "graduation_range": "2027届",
        "source_url": "https://www.nowcoder.com/discuss/914273128614723584?urlSource=sitemap",
        "apply_url": "https://intsig.zhiye.com/campus/jobs?shareId=335dd756-a88c-485c-98cc-83829f5852ec&shareSource=2",
        "referral_code": "ESKMB0",
        "posted_at": "2026-07-28",
        "deadline": "招满即止",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "公开帖写明2027届秋招7.28启动，工作地点上海、苏州、广州，算法、技术、产品、设计、营销、职能等岗位开放，内推码ESKMB0。",
        "notes": "帖子注明职位招满即停，建议优先投递并以官网列表为准。",
    },
    {
        "platform": "牛客网",
        "company_name": "蔚来",
        "job_title": "算法/前后端/自动驾驶/座舱/大模型/硬件/电池等校招岗位",
        "job_category": "算法/软件/自动驾驶/硬件",
        "city": "南京/苏州",
        "recruitment_type": "校招",
        "graduation_range": "2027届（帖子写2024.09-2027.08）",
        "source_url": "https://www.nowcoder.com/feed/main/detail/5fb424da260448299081bdd8ed64fd2e",
        "apply_url": "https://nio.jobs.feishu.cn/s/T4KdUvJ-KXQ",
        "referral_code": "BJP8VZF",
        "posted_at": "2026-08-26",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "公开帖写明8月26日起网申、9月起面试，技术岗位覆盖算法、前后端、自动驾驶、智能座舱、大模型等，工作地点含南京、苏州，内推码BJP8VZF。",
        "notes": "按岗位城市纳入；投递前确认具体岗位的base和志愿限制。",
    },
    {
        "platform": "牛客网",
        "company_name": "CVTE视源股份",
        "job_title": "软件/硬件/算法/制造质量/供应链等校招岗位",
        "job_category": "软件/硬件/算法/制造/供应链",
        "city": "苏州",
        "recruitment_type": "校招",
        "graduation_range": "2027届",
        "source_url": "https://www.nowcoder.com/feed/main/detail/43089483351147aca8900c5d395f9e4f?urlSource=home-api",
        "apply_url": "https://campus.cvte.com/",
        "referral_code": "CVTEGZCKF",
        "posted_at": "2026-08-30",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "公开帖明确列出苏州工作地点、九大岗位类别和官方投递地址campus.cvte.com，并给出内推码CVTEGZCKF。",
        "notes": "帖子未给统一截止时间，需按官网岗位状态复核。",
    },
    {
        "platform": "牛客网",
        "company_name": "小米集团",
        "job_title": "软件研发/算法/硬件/芯片/产品等校招岗位",
        "job_category": "软件/算法/硬件/芯片/产品",
        "city": "南京",
        "recruitment_type": "校招/实习",
        "graduation_range": "2027届（内地毕业时间2027年）",
        "source_url": "https://www.nowcoder.com/feed/main/detail/d7bb128e28a44889810599505012da29?sourceSSR=subject",
        "apply_url": "https://job.mi.com/",
        "referral_code": "QN8KF6Z",
        "posted_at": "2026-08-10",
        "deadline": "2027-01-15",
        "status": "公开近期",
        "evidence_confidence": "中",
        "evidence_text": "公开帖列出南京工作地点，说明内推码QN8KF6Z可用于实习/校招/社招，并写明投递时间即日起至2027年1月15日。",
        "notes": "帖子未列出南京的具体职位名称；请在官网按南京筛选。",
    },
    {
        "platform": "脉脉",
        "company_name": "地平线",
        "job_title": "算法/芯片/软件/硬件/测试等校招岗位",
        "job_category": "算法/芯片/软件/硬件/测试",
        "city": "南京",
        "recruitment_type": "秋招",
        "graduation_range": "2026.09-2027.08毕业",
        "source_url": "https://maimai.cn/article/detail?efid=EkMeTQ_Ab81sVSZOLBdYng&fid=1925106231",
        "apply_url": "https://taou.cn/a/i9uoLB",
        "referral_code": "exnxdy",
        "posted_at": "",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "脉脉公开帖标明地平线2027届秋季校园招聘，招募对象为2026.09-2027.08毕业生，岗位城市含南京，方向含算法、芯片、软件、硬件、测试，内推码exnxdy。",
        "notes": "页面以相对时间展示，投递前确认官网实时岗位。",
    },
    {
        "platform": "牛客网",
        "company_name": "地平线",
        "job_title": "算法/芯片/软件/硬件/测试等校招岗位",
        "job_category": "算法/芯片/软件/硬件/测试",
        "city": "南京",
        "recruitment_type": "秋招",
        "graduation_range": "2026.09-2027.08毕业",
        "source_url": "https://www.nowcoder.com/feed/main/detail/6508d277cc754244a4fb1465cb63b709?sourceSSR=subject",
        "apply_url": "https://horizon-campus.hotjob.cn/",
        "referral_code": "exnxdy",
        "posted_at": "2026-08-23",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "牛客公开帖列出岗位城市北京、上海、南京等，招聘对象为2026.09-2027.08毕业生，并给出官网horizon-campus.hotjob.cn和内推码exnxdy。",
        "notes": "同一招聘项目的第二个平台证据，用于交叉核验；投递前以官网为准。",
    },
    {
        "platform": "高校就业网",
        "company_name": "联想集团",
        "job_title": "技术/产品项目/供应链/设计等校招岗位",
        "job_category": "技术/产品/项目/供应链/设计",
        "city": "南京/昆山",
        "recruitment_type": "秋招",
        "graduation_range": "2027届",
        "source_url": "https://job.xpu.edu.cn/detail/online?id=3536899",
        "apply_url": "https://talent.lenovo.com.cn/home",
        "referral_code": "2027XZLMXX",
        "posted_at": "2026-08-22",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "中",
        "evidence_text": "高校就业网公开招聘页列出联想2027届秋招，工作地点包含南京、昆山等，六大岗位方向开放，官网为talent.lenovo.com.cn，内推码2027XZLMXX。",
        "notes": "昆山属于江苏；内推码填写规则以联想官网提示为准。",
    },
    {
        "platform": "牛客网",
        "company_name": "无锡信捷电气",
        "job_title": "算法/研发/应用技术/职能营销类校招岗位",
        "job_category": "算法/研发/应用技术/营销",
        "city": "无锡",
        "recruitment_type": "秋招",
        "graduation_range": "2027届",
        "source_url": "https://www.nowcoder.com/feed/main/detail/93fd25dfb6134a3587542b723e79fd3b",
        "apply_url": "https://xinje.zhiye.com/",
        "referral_code": "IVKWV2",
        "posted_at": "2026-08-25",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "牛客公开帖明确写明无锡信捷电气2027届校招已开启，岗位含算法、研发、应用技术、职能营销类，并给出官网和内推码IVKWV2。",
        "notes": "江苏本地企业线索；帖子未给截止日期，按官网状态复核。",
    },
    {
        "platform": "牛客网",
        "company_name": "九号公司",
        "job_title": "技术研发/产品/设计/供应链/制造等校招岗位",
        "job_category": "技术研发/产品/供应链/制造",
        "city": "常州",
        "recruitment_type": "校招",
        "graduation_range": "2026/2027届均可投递",
        "source_url": "https://www.nowcoder.com/feed/main/detail/d283da5f89d647f8a2df92e37d4898bc",
        "apply_url": "https://app.mokahr.com/m/campus_apply/ninebot/45627?recommendCode=DSknaq5k#/jobs",
        "referral_code": "DSknaq5k",
        "posted_at": "",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "牛客公开帖列出常州工作地点，说明九号公司2027届校招且26届也可投递，岗位覆盖技术研发、产品、供应链、制造等，并给出内推码DSknaq5k。",
        "notes": "页面以相对时间展示；具体岗位和截止时间以九号官网为准。",
    },
    {
        "platform": "牛客网",
        "company_name": "联影医疗",
        "job_title": "软件/算法/大数据/机器人/芯片/嵌入式等校招岗位",
        "job_category": "软件/算法/大数据/机器人/芯片/嵌入式",
        "city": "常州",
        "recruitment_type": "秋招",
        "graduation_range": "2027届",
        "source_url": "https://www.nowcoder.com/creation/subject/6b6f567d2bf14dd698af013834334089?entranceType_var=%E5%86%85%E5%AE%B9%E6%9D%A1%E7%9B%AE",
        "apply_url": "https://united-imaging.zhiye.com/",
        "referral_code": "IZK6H9",
        "posted_at": "",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "中",
        "evidence_text": "牛客公开主题页的联影员工帖写明2027秋招已启动，工作地点含常州，岗位近170个、涵盖软件算法大数据机器人芯片嵌入式等，并给出内推码IZK6H9。",
        "notes": "帖子正文来自员工分享，具体HC与岗位状态需在官网核验。",
    },
    {
        "platform": "牛客网",
        "company_name": "轻舟智航",
        "job_title": "算法/工程/产品项目类校招岗位",
        "job_category": "算法/工程/产品/项目",
        "city": "苏州",
        "recruitment_type": "秋招",
        "graduation_range": "2027届",
        "source_url": "https://www.nowcoder.com/feed/main/detail/9764176f2a80449b84a1998a349cbc04",
        "apply_url": "https://qcraft.jobs.feishu.cn/s/11tH8fCyewY",
        "referral_code": "MWTTW2R",
        "posted_at": "",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "牛客公开帖写明轻舟智航2027届秋招启动，招聘岗位为算法、工程、产品项目类，工作地点北京、苏州，内推码MWTTW2R。",
        "notes": "页面以相对时间展示，需官网确认苏州具体岗位。",
    },
    {
        "platform": "牛客网",
        "company_name": "禾迈股份",
        "job_title": "研发/产品/智能制造/市场营销等校招岗位",
        "job_category": "研发/产品/智能制造/营销",
        "city": "苏州",
        "recruitment_type": "秋招",
        "graduation_range": "2027届",
        "source_url": "https://www.nowcoder.com/feed/main/detail/673dcd9e5234471a814a7df53dc8b68a?urlSource=home-api",
        "apply_url": "https://app.mokahr.com/m/campus_apply/hoymiles/70377?recommendCode=DSpptKY2#/jobs",
        "referral_code": "DSpptKY2",
        "posted_at": "2026-08-31",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "牛客公开帖写明禾迈股份2027届秋招开启，岗位含研发、产品、智能制造、市场营销，国内工作地点包含苏州，内推码DSpptKY2。",
        "notes": "帖子未给统一截止日期，按官网岗位状态复核。",
    },
    {
        "platform": "牛客网",
        "company_name": "美的集团",
        "job_title": "研发技术/信息技术/制造技术/供应链等秋招岗位",
        "job_category": "研发/信息技术/制造/供应链",
        "city": "无锡/苏州",
        "recruitment_type": "秋招",
        "graduation_range": "2027届",
        "source_url": "https://www.nowcoder.com/discuss/924981670401318912",
        "apply_url": "https://careers.midea.com/recruit-school-wechat/job?mvp_code=M37O45&type=1",
        "referral_code": "M37O45",
        "posted_at": "",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "牛客公开帖写明美的2027届秋招当天开启，七大业务板块和八大职类开放，工作地点包含无锡、苏州，内推码M37O45。",
        "notes": "页面以相对时间展示，投递前确认具体base和岗位截止时间。",
    },
    {
        "platform": "牛客网",
        "company_name": "万得（Wind）",
        "job_title": "人工智能/软件研发/数据/管培等校招岗位",
        "job_category": "人工智能/软件研发/数据/管培",
        "city": "南京/苏州/扬州",
        "recruitment_type": "校招",
        "graduation_range": "2027届",
        "source_url": "https://www.nowcoder.com/feed/main/detail/075fbcb0a7b7439fa166acc8eb3a1a21?urlSource=home-api",
        "apply_url": "https://www.wind.com.cn/mobile/JoinUS/RecruitDetail/zh.html?entry=school",
        "referral_code": "cx2027",
        "posted_at": "2026-07-06",
        "deadline": "",
        "status": "需复核",
        "evidence_confidence": "中",
        "evidence_text": "牛客公开帖写明Wind 2027届校招提前批已启动，岗位含人工智能、软件研发、数据等，工作地点含南京、苏州、扬州，推荐码cx2027。",
        "notes": "帖子较早且未给截止日期，先标需复核；官网实时状态优先。",
    },
    {
        "platform": "牛客网",
        "company_name": "万得（Wind）",
        "job_title": "人工智能/软件研发/数据等实习岗位",
        "job_category": "人工智能/软件研发/数据实习",
        "city": "南京/苏州/扬州",
        "recruitment_type": "实习",
        "graduation_range": "在校生（帖子为2027届项目）",
        "source_url": "https://www.nowcoder.com/feed/main/detail/075fbcb0a7b7439fa166acc8eb3a1a21?urlSource=home-api",
        "apply_url": "https://www.wind.com.cn/mobile/JoinUS/RecruitDetail/zh.html?entry=school",
        "referral_code": "cx2027",
        "posted_at": "2026-07-06",
        "deadline": "",
        "status": "需复核",
        "evidence_confidence": "中",
        "evidence_text": "同一公开帖标题明确包含2027届实习生招聘，并列出人工智能、软件研发、数据等方向及南京、苏州、扬州工作地点，推荐码cx2027。",
        "notes": "实习HC可能随时间变化，需在Wind官网确认当前是否仍开放。",
    },
    {
        "platform": "牛客网",
        "company_name": "三环集团",
        "job_title": "材料研发/机电研发等校招岗位",
        "job_category": "材料研发/机电研发",
        "city": "苏州",
        "recruitment_type": "校招",
        "graduation_range": "2027届",
        "source_url": "https://www.nowcoder.com/feed/main/detail/812574eaaf554095a240c6fc1a30b915?urlSource=home-api",
        "apply_url": "https://hr.cctc.cc/school?sourceCode=861049&isRecommendCode=true",
        "referral_code": "861049",
        "posted_at": "2026-07-12",
        "deadline": "",
        "status": "需复核",
        "evidence_confidence": "中",
        "evidence_text": "牛客公开帖列出三环集团2027届提前批，江苏工作地点为苏州，岗位为材料研发类、机电研发类，内推码861049。",
        "notes": "公开帖时间较早且未给截止日期，需官网复核是否仍有HC。",
    },
    {
        "platform": "牛客网",
        "company_name": "大普微电子（Dapustor）",
        "job_title": "软件开发/软件测试/IC设计验证/后端/算法/技术支持等校招岗位",
        "job_category": "软件/测试/芯片/算法",
        "city": "苏州/南京/无锡",
        "recruitment_type": "秋招",
        "graduation_range": "2027届",
        "source_url": "https://www.nowcoder.com/feed/main/detail/5b375fb1215144629e67088c583fb853?sourceSSR=dynamic",
        "apply_url": "",
        "referral_code": "NTAWmk8",
        "posted_at": "2026-08-18",
        "deadline": "2026-10（帖子写开放至10月，未给具体日）",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "牛客公开帖明确写明大普微电子2027届校招，开放时间为2026年8月至10月，岗位含软件开发、测试、IC设计/验证、后端、算法、技术支持，工作地点包含苏州、南京、无锡，内推码NTAWmk8。",
        "notes": "江苏工作地较多，适合优先核验；具体投递入口需从原帖或官网补齐。",
    },
    {
        "platform": "牛客网",
        "company_name": "众星微（无锡）",
        "job_title": "芯片前后端/IC设计验证校招岗位",
        "job_category": "芯片设计/验证",
        "city": "无锡",
        "recruitment_type": "校招",
        "graduation_range": "2027届（帖子未给具体届别截止）",
        "source_url": "https://www.nowcoder.com/feed/main/detail/480f2376652f484ba721c212b06cff79",
        "apply_url": "",
        "referral_code": "",
        "posted_at": "2026-08-27",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "中",
        "evidence_text": "牛客公开帖标题及正文写明无锡众星微2027校园招聘已启动，方向为芯片前后端、IC设计验证；帖子未公开内推码，投递信息需向原帖确认。",
        "notes": "未发现公开内推码；页面中的邮箱已脱敏，不能据此猜测联系方式。",
    },
    {
        "platform": "牛客网",
        "company_name": "帆软",
        "job_title": "研发/产品/UX/销售工程师/客户成功等校招岗位",
        "job_category": "研发/产品/UX/销售/运营",
        "city": "无锡/南京",
        "recruitment_type": "秋招提前批",
        "graduation_range": "2027届（2026.09-2027.08毕业）",
        "source_url": "https://www.nowcoder.com/feed/main/detail/8181cb0bac1d42deace41fadd2baa882?urlSource=home-api",
        "apply_url": "https://join.fanruan.com/campus",
        "referral_code": "Vi99n7c",
        "posted_at": "2026-08-01",
        "deadline": "2026-08-31",
        "status": "已过期",
        "evidence_confidence": "高",
        "evidence_text": "牛客公开帖明确写明帆软2027届秋招提前批，工作地点含无锡总部、南京，岗位覆盖研发、产品、UX、销售工程师、客户成功、职能运营，内推码Vi99n7c，网申截止8月31日。",
        "notes": "截至2026-09-04提前批截止；可关注帆软正式批/补录，不应把该批次当作当前开放。",
    },
    {
        "platform": "牛客网",
        "company_name": "帆软",
        "job_title": "研发/产品/客户交付运营/市场/销售/设计等校招岗位",
        "job_category": "研发/产品/交付运营/市场/销售",
        "city": "无锡/南京",
        "recruitment_type": "秋招提前批",
        "graduation_range": "2027届",
        "source_url": "https://www.nowcoder.com/discuss/914904434147135488",
        "apply_url": "https://t6ixa9nyl6.jiandaoyun.com/f/65e1a1308ce7672fded0f0cf?ext=NDPGP",
        "referral_code": "NDPGP",
        "posted_at": "",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "中",
        "evidence_text": "较新的公开帖称帆软2027届秋招提前批‘火热进行中’，明确写出无锡、南京工作地点、研发/产品/交付运营等岗位及内推码NDPGP，并称公司为独角兽、2000+员工。",
        "notes": "与旧帖Vi99n7c属于不同公开码/批次；帖子未给绝对截止日，投递前以官网实时状态为准。",
    },
    {
        "platform": "牛客网",
        "company_name": "安克创新",
        "job_title": "技术研发/产品/供应链/职能等全球校招岗位",
        "job_category": "研发/产品/供应链/职能",
        "city": "苏州",
        "recruitment_type": "校招",
        "graduation_range": "2027届全球应届生",
        "source_url": "https://www.nowcoder.com/feed/main/detail/7ae780687a2a4a05b9f2907c947a9b55?urlSource=home-api",
        "apply_url": "https://anker-in.jobs.feishu.cn/s/5bC2bB38QIk",
        "referral_code": "Q2HNA3J",
        "posted_at": "",
        "deadline": "",
        "status": "公开近期",
        "evidence_confidence": "高",
        "evidence_text": "牛客公开帖当天更新，明确写明安克创新2027届全球校园招聘启动，工作地包含苏州，面向2027届全球应届生，并给出官方投递链接和校园大使内推码Q2HNA3J。",
        "notes": "按江苏岗位城市纳入；具体岗位base和截止时间以官方页面为准。",
    },
]


def _base_jd(row: dict[str, str]) -> dict[str, str]:
    """Return an explicit, non-inferred fallback for an aggregate post."""

    return {
        "jd_summary": "公开帖子只列招聘方向，未披露单一岗位的完整 JD。",
        "responsibilities": "原帖未披露具体职责；请打开官方职位详情核对工作内容。",
        "requirements": "原帖未披露统一硬性要求；以具体岗位详情为准。",
        "education_requirement": row.get("graduation_range", "") or "未披露",
        "major_requirement": "未披露",
        "skill_requirement": "与岗位方向匹配的专业基础；具体技能以官方职位为准。",
        "experience_requirement": "应届/在校生条件以该条招聘批次为准；项目或实习要求未披露。",
        "jd_source_url": row["source_url"],
        "jd_evidence_confidence": "低",
    }


def _jd_details(row: dict[str, str]) -> dict[str, str]:
    """Map a curated lead to source-backed JD details.

    The table intentionally stores concise, searchable summaries rather than
    copying whole pages.  When a platform post is only a role collection, the
    text says so explicitly instead of inventing a universal threshold.
    """

    company = row["company_name"]
    title = row["job_title"]
    details = _base_jd(row)

    if company == "九识智能" and row["recruitment_type"] == "实习":
        return {
            "jd_summary": "自动驾驶算法/研发实习，围绕真实车辆数据和城市物流场景做算法迭代。",
            "responsibilities": "多传感器标定；模型训练性能优化；数据闭环与长尾样本挖掘；端到端感知；前端开发（按具体实习岗位分工）。",
            "requirements": "公开帖未披露统一学历和年级硬门槛；需按具体方向具备对应的算法、编程或前端实践。",
            "education_requirement": "在校生；具体毕业年份未统一披露",
            "major_requirement": "计算机、自动化、车辆、电子信息或相关方向（具体岗位为准）",
            "skill_requirement": "按方向匹配 Python/C++、深度学习、传感器标定、数据闭环或前端开发能力",
            "experience_requirement": "有课程项目、科研或实习实践优先；原帖未设统一年限",
            "jd_source_url": "https://www.nowcoder.com/feed/main/detail/cae9e9df7eb843a180c1a8649078c7ed?urlSource=home-api",
            "jd_evidence_confidence": "高",
        }
    if company == "九识智能" and "算法" in title:
        return {
            "jd_summary": "自动驾驶深度学习算法工程师，负责感知模型上线、车端迭代和数据闭环。",
            "responsibilities": "研发点云/图像/radar检测、分割、追踪模型并上线；开发线上后处理（离线 Python、车端 C++）；打通数据打点、4D自动标注和长尾样本挖掘闭环。",
            "requirements": "理解自动驾驶深度学习网络及常见 2D/3D 检测、分割、BEV 车道线、Occ、端到端模型；具备 C++/Python/CUDA 编程、数据结构与算法基础；熟悉 PyTorch/Paddle/TensorFlow 及 OpenMMLab/PaddlePaddle。",
            "education_requirement": "2026届（该具体职位页面）；聚合校招帖另覆盖2027届，需按岗位确认",
            "major_requirement": "计算机、人工智能、自动化、车辆或相关专业（具体职位未单列专业限制）",
            "skill_requirement": "C++、Python、CUDA、PyTorch/Paddle/TensorFlow、OpenMMLab；量化/剪枝/蒸馏和端到端部署为加分项",
            "experience_requirement": "自动驾驶感知或模型工程部署经验加分；无统一工作年限要求",
            "jd_source_url": "https://www.nowcoder.com/jobs/detail/417030",
            "jd_evidence_confidence": "高",
        }
    if company == "满帮集团":
        if "全栈" in title:
            return {
                "jd_summary": "物流平台全栈开发，覆盖 Web、Java 服务、数据库和 AI 应用的端到端交付。",
                "responsibilities": "设计开发 Web 前端、后端接口和数据库；使用 Java/Spring Boot 做微服务与数据处理；使用 Vue/React 完成交互；参与评审、Code Review、测试上线和线上排障；探索 AI Coding、Agent 与大模型 API。",
                "requirements": "计算机基础扎实，掌握数据结构、算法、操作系统、网络、数据库；前端或后端至少一侧可独立开发；了解 REST、Git、CI/CD；逻辑清晰、沟通协作良好。",
                "education_requirement": "本科；2027届，毕业时间2026.10-2027.09",
                "major_requirement": "计算机、软件工程或相关专业",
                "skill_requirement": "Java/Spring Boot/Spring Cloud、MySQL、Redis、消息队列，或 HTML/CSS/JavaScript、Vue/React；有 AI Coding/Agent 经验加分",
                "experience_requirement": "全栈项目、实习、开源项目、算法竞赛经历加分；无统一年限要求",
                "jd_source_url": "https://www.nowcoder.com/jobs/detail/463148",
                "jd_evidence_confidence": "高",
            }
        return {
            "jd_summary": "数字货运平台算法工程师，面向车货匹配、定价、增长、风控和物流大模型。",
            "responsibilities": "参与搜索推荐、车货匹配和排序；建设定价/交易算法；做用户分层、转化预测和营销策略；探索物流大模型、知识库和 Agent；完成数据处理、特征工程、训练、评估、部署和监控全链路。",
            "requirements": "熟悉 Python/Java/C/C++ 至少一门、数据结构算法和 SQL；理解分类/聚类/回归等机器学习基础；能把业务问题抽象成算法问题，具备数据敏感度和协作能力。",
            "education_requirement": "本科；2027届，毕业时间2026.10-2027.09",
            "major_requirement": "计算机、软件工程、统计、应用数学或相关专业",
            "skill_requirement": "Python/Java/C/C++、SQL、机器学习；推荐/搜索/广告/定价/NLP/CV、大数据 Spark/Flink/Hive 经验加分",
            "experience_requirement": "相关实习、项目、竞赛或论文经历加分；无统一年限要求",
            "jd_source_url": "https://www.nowcoder.com/jobs/detail/463165?urlSource=sitemap",
            "jd_evidence_confidence": "高",
        }
    if company == "帆软" and row["recruitment_type"] == "秋招提前批" and "Vi99n7c" in row["referral_code"]:
        details.update({
            "jd_summary": "帆软 FineReport/FineBI/FineDataLink 等数据产品的研发、产品、交付运营和销售方向；该批次已过期。",
            "responsibilities": "公开帖仅列研发、产品、UX、销售工程师、客户成功和职能运营方向，未展开到单岗位职责。",
            "requirements": "公开帖未披露统一硬性要求；该批次网申截止2026-08-31，不能视为当前开放。",
            "education_requirement": "2027届（2026.09-2027.08）",
            "major_requirement": "按具体职位；未统一披露",
            "skill_requirement": "按具体职位；未统一披露",
            "experience_requirement": "应届生；未统一披露工作年限",
            "jd_source_url": row["source_url"],
            "jd_evidence_confidence": "高",
        })
        return details
    if company == "帆软":
        return {
            "jd_summary": "帆软千帆计划后端开发实习，参与 FineReport/FineBI/FineDataLink、简道云和数据分析引擎研发。",
            "responsibilities": "使用 Java 参与 FineReport、FineBI、FineDataLink、九数云服务端功能开发和维护；使用 NodeJS/Java 迭代简道云服务端；推动云原生落地；使用 Spark 做大数据处理；改进 OLAP/自助分析引擎。",
            "requirements": "2027届本科及以上、理工科；Java/NodeJS/Rust/C/C++/Go 任一编程实践；有算法基础、表达沟通和责任心；数据库技能、多人使用的 GitHub 开源项目或技术博客优先。",
            "education_requirement": "2027届本科及以上；实习期满3个月可申请转正",
            "major_requirement": "理工科专业背景",
            "skill_requirement": "Java/NodeJS/Rust/C/C++/Go 任一；数据库、Spark、云原生为岗位工作内容",
            "experience_requirement": "实习；开源项目或持续技术博客优先",
            "jd_source_url": "https://join.fanruan.com/trainee/detail?id=9832",
            "jd_evidence_confidence": "高",
        }
    if company == "无锡信捷电气":
        return {
            "jd_summary": "工业自动化产品研发与应用，岗位覆盖电机/运动/过程控制算法、嵌入式/上位机软件、硬件和系统集成。",
            "responsibilities": "算法岗位负责控制算法研究、优化、仿真、开发和测试；研发岗位完成普通功能、单元/集成测试和问题闭环；系统集成岗位做自动化项目开发调试、产品应用和现场验证；硬件岗位完成器件选型、原理图/PCB、测试整改和客诉分析。",
            "requirements": "按岗位：算法通常硕士及以上、数学基础和 MATLAB/Simulink/C/C++；软件本科及以上，熟悉 C/C++/C#、Qt/Winform、数据结构算法；硬件本科及以上，数模电和 AD/PCB 基础；系统集成要求电子/电气/自动化等相关本科。",
            "education_requirement": "2027届本科及以上；部分控制算法岗位硕士及以上",
            "major_requirement": "控制工程、电子信息、机械、电气、自动化、计算机、通信等相关专业",
            "skill_requirement": "MATLAB/Simulink、C/C++/C#、Qt/Visual Studio、DSP/ARM、AD 原理图与 PCB、英文文献和技术文档",
            "experience_requirement": "应届生；奖学金、相关项目和现场调试经验优先",
            "jd_source_url": "https://job.wzu.edu.cn/campus/view/id/494949",
            "jd_evidence_confidence": "高",
        }
    if company == "轻舟智航":
        return {
            "jd_summary": "自动驾驶规划算法工程师，负责决策、轨迹规划、控制算法和仿真/实车数据闭环。",
            "responsibilities": "设计、实现和优化城市/高速复杂交互场景的决策与轨迹规划；探索优化、机器学习和端到端规划；分析仿真及实车数据，解决真实路况问题。",
            "requirements": "机器人、计算机、车辆、自动化或应用数学硕士以上；数理基础扎实，熟悉数值优化、计算几何、搜索、控制或机器学习；C++ 扎实、熟悉 Python；英文文献阅读和沟通协作良好。",
            "education_requirement": "硕士及以上；2027届",
            "major_requirement": "机器人、计算机、车辆工程、自动化、应用数学等相关专业",
            "skill_requirement": "C++、Python、数值优化/搜索/控制/机器学习；端到端规划、模仿学习或强化学习经验优先",
            "experience_requirement": "智能运动规划、决策控制科研或项目经验优先；无统一工作年限",
            "jd_source_url": "https://www.shushuqiuzhi.com/position/460943",
            "jd_evidence_confidence": "高",
        }
    if company == "禾迈股份":
        return {
            "jd_summary": "光储新能源研发/产品/智能制造/市场营销，苏州岗位重点为电力电子、控制、嵌入式和 EMS 软件。",
            "responsibilities": "公开招聘覆盖功率/控制硬件、电力电子软件、储能系统控制算法、ARM/DSP 嵌入式、EMS 后端软件、算法数据和 AI 等方向；具体职责随岗位而定。",
            "requirements": "面向2027届应届生；具体学历、专业和技能门槛按岗位详情核对，聚合帖未给统一硬性要求。每人最多投递3个岗位。",
            "education_requirement": "2027届，毕业时间2026.09-2027.08；学历按具体岗位",
            "major_requirement": "电力电子、电气、自动化、计算机、软件、控制、数据等相关专业（按岗位）",
            "skill_requirement": "按方向匹配电路/控制、C/C++、ARM/DSP、后端或数据分析能力",
            "experience_requirement": "应届生；相关项目/实习按具体岗位要求",
            "jd_source_url": "https://www.nowcoder.com/feed/main/detail/3c34ad7ff41b4dd7afe91e06b5ed5fd1?urlSource=sitemap",
            "jd_evidence_confidence": "中",
        }
    if company == "九号公司":
        return {
            "jd_summary": "个人出行与服务机器人企业的技术研发、产品、质量、供应链、制造和服务类校招。",
            "responsibilities": "公开简章按技术研发、服务、营销、职能、质量、供应链、设计、产品、生产制造九类招聘；常州岗位以研发、质量、供应链、制造和服务支持为主，具体职责按职位详情。",
            "requirements": "2026/2027届统招本科及以上；面向海内外院校，毕业时间2025.09-2027.08；具体岗位技能未在聚合简章统一展开。",
            "education_requirement": "统招本科及以上；2026/2027届",
            "major_requirement": "按技术研发、产品、制造、供应链等岗位匹配；未统一限定",
            "skill_requirement": "按具体职位；技术岗需对应研发/工程基础，制造与供应链岗需对应专业能力",
            "experience_requirement": "应届生；无统一工作年限",
            "jd_source_url": "https://career.nankai.edu.cn/correcruit/content/id/116982.html",
            "jd_evidence_confidence": "高",
        }
    if company == "万得（Wind）" and row["recruitment_type"] == "实习":
        return {
            "jd_summary": "Wind 金融终端/移动客户端测试与 AI、软件研发、数据方向实习，优秀实习生有转正机会。",
            "responsibilities": "负责金融产品终端和移动客户端功能、性能、安全、内存、电量、弱网络、Monkey 等测试；参与需求评审、测试用例设计、测试报告和流程改进。",
            "requirements": "了解计算机系统结构、操作系统、网络；逻辑严谨，愿意从事 AI 软件测试；学习沟通和团队协作能力良好。每周实习3天以上、连续2个月以上。",
            "education_requirement": "在校生；校招页面同时面向2026.09-2027.08毕业生",
            "major_requirement": "计算机、软件、信息技术或相关专业优先",
            "skill_requirement": "计算机基础、测试方法和 AI 工具学习能力；具体开发语言未统一要求",
            "experience_requirement": "每周3天以上、连续2个月以上；表现优秀有转正机会",
            "jd_source_url": "https://www.wind.com.cn/portal/zh/JoinUs/recruit.html?channelPositionId=1182&positionType=9002",
            "jd_evidence_confidence": "高",
        }
    if company == "万得（Wind）":
        details.update({
            "jd_summary": "Wind 2027 校招人工智能、软件研发、数据和管培方向；江苏城市需按官网岗位筛选。",
            "responsibilities": "聚合帖只列人工智能、软件研发、数据和管培方向；具体职责以 Wind 校招岗位详情为准。",
            "requirements": "面向2026.09-2027.08毕业生；聚合帖未披露统一技能门槛，需按官网具体岗位核对。",
            "education_requirement": "2027届；具体岗位学历以官网为准",
            "major_requirement": "计算机、软件、信息技术、金融/经济等按岗位",
            "skill_requirement": "按 AI、软件研发、数据或管培方向匹配；具体技能未统一披露",
            "experience_requirement": "应届生；实习/项目条件按具体岗位",
            "jd_source_url": "https://www.wind.com.cn/mobile/JoinUS/RecruitHome/zh.html",
            "jd_evidence_confidence": "中",
        })
        return details
    if company == "三环集团":
        details.update({
            "jd_summary": "材料研发与机电研发方向校招，苏州岗位来自2027届提前批公开帖。",
            "responsibilities": "公开帖仅列材料研发类、机电研发类方向，未披露单岗位职责。",
            "requirements": "公开帖未披露统一学历、专业和技能门槛；以三环集团官网岗位详情为准。",
            "education_requirement": "2027届；未披露具体学历",
            "major_requirement": "材料、机械、电气/自动化等相关方向（根据岗位名称匹配，非统一硬门槛）",
            "skill_requirement": "未披露",
            "experience_requirement": "应届生；未披露",
            "jd_source_url": row["source_url"],
            "jd_evidence_confidence": "中",
        })
        return details
    if company == "大普微电子（Dapustor）":
        details.update({
            "jd_summary": "网络存储芯片与系统研发，校招覆盖软件开发/测试、IC 设计验证、后端、算法和技术支持。",
            "responsibilities": "参与芯片/固件/主机端测试软件开发、软件测试、逻辑/FPGA 验证、IC 后端实现、算法或技术支持；具体工作按岗位分配。",
            "requirements": "公开校招帖未披露统一学历和技能门槛；软件/测试需编程和测试基础，IC 岗需数字电路/RTL/EDA 基础，算法岗需算法与数学基础。",
            "education_requirement": "2027届；具体学历按职位详情",
            "major_requirement": "计算机、电子信息、微电子、通信、自动化等相关专业（按岗位）",
            "skill_requirement": "按方向匹配 C/C++/Python、Linux、Verilog/RTL、EDA、数字电路、算法或技术支持能力",
            "experience_requirement": "应届生；芯片设计/验证、软件测试或项目实践优先",
            "jd_source_url": row["source_url"],
            "jd_evidence_confidence": "中",
        })
        return details
    if company == "众星微（无锡）":
        return {
            "jd_summary": "数字/模拟芯片设计与验证，当前公开岗位含无锡数字 IC 后端工程师。",
            "responsibilities": "配合前端完成 RTL 检查和门级仿真；进行逻辑综合、RTL/网表等价检查、静态时序分析；完成布局规划、布局、时钟树、布线和物理验证，推进 GDS 交付。",
            "requirements": "硕士及以上；熟悉 Linux；了解或使用 Design Compiler、Fusion Compiler、Formality、PrimeTime、ICC2、Innovus 等 EDA 工具；掌握 Python/Tcl/Shell 至少一种；数字中/后端实践优先。",
            "education_requirement": "硕士及以上；2027届公开岗位",
            "major_requirement": "计算机、通信、电子信息、软件工程、数据科学、人工智能等相关专业",
            "skill_requirement": "Linux、EDA（DC/FC/Formality/PT/ICC2/Innovus）、Python/Tcl/Shell、RTL/网表/STA/物理实现",
            "experience_requirement": "数字中/后端设计实践优先；无统一年限",
            "jd_source_url": "https://cn.linkedin.com/jobs/view/%E3%80%902027%E3%80%91%E6%95%B0%E5%AD%97ic%E5%90%8E%E7%AB%AF%E5%B7%A5%E7%A8%8B%E5%B8%88-%E6%97%A0%E9%94%A1-j14268-at-%E4%BC%97%E6%98%9F%E5%BE%AE-4455053741",
            "jd_evidence_confidence": "高",
        }
    if company == "安克创新":
        return {
            "jd_summary": "苏州储能产品硬件开发，参与电源/储能硬件设计、测试调试和产品创新。",
            "responsibilities": "参与储能产品硬件设计和项目落地技术问题；负责储能产品测试、调试和设计；学习新储能技术并推动产品创新。",
            "requirements": "2027届本科及以上；电力电子、电路与系统、大功率储能相关专业；有电源项目经验优先。",
            "education_requirement": "2027届本科及以上",
            "major_requirement": "电力电子、电路与系统、大功率储能或相关专业",
            "skill_requirement": "储能/电源硬件设计、测试和调试基础",
            "experience_requirement": "电源项目经验优先；无统一年限",
            "jd_source_url": "https://www.nowcoder.com/jobs/detail/463249",
            "jd_evidence_confidence": "高",
        }
    if company == "联影医疗":
        return {
            "jd_summary": "医疗影像与医疗设备软件/算法/嵌入式研发，常州等地开放多类校招岗位。",
            "responsibilities": "软件岗参与医学系统模块、影像处理、AI 视觉、云化软件开发及需求/设计/编码/测试文档；嵌入式岗完成需求分析、设计、部件验证、集成测试、处理器固件/驱动与质量改进。",
            "requirements": "软件岗本科及以上，掌握 C#/C/C++/Java/Go/Python/JavaScript 至少一种；嵌入式岗硕士及以上，熟悉 C/C++、Linux/VxWorks/QNX、处理器固件和常见总线；医疗影像、CUDA、控制或协议经验优先。",
            "education_requirement": "软件岗本科及以上；嵌入式岗硕士及以上；2027届",
            "major_requirement": "计算机、软件、生物医学工程、电子、测控、自动化、机械、电力电子等相关专业",
            "skill_requirement": "C/C++/Java/Python/Go/JS；Linux、嵌入式系统、Ethernet/CAN/I2C/SPI/UART/PCIe/EtherCAT；医疗影像/深度学习/CUDA 加分",
            "experience_requirement": "项目、科研或医疗软件经验优先；无统一工作年限",
            "jd_source_url": "https://www.nowcoder.com/jobs/detail/459961?urlSource=sitemap",
            "jd_evidence_confidence": "高",
        }
    if company == "地平线":
        return {
            "jd_summary": "AI 芯片与智能驾驶算法/软件/硬件研发，南京岗位覆盖算法、芯片、软件、硬件和测试。",
            "responsibilities": "参与算法、芯片、软件、硬件或测试方向的研发与工程落地；具体岗位职责按地平线校招职位详情。",
            "requirements": "面向2026.09-2027.08毕业生；具体岗位通常要求计算机/电子/自动化等相关专业和编程/算法基础，学历与技能以官网岗位为准。",
            "education_requirement": "2027届；具体岗位本科/硕士要求不同",
            "major_requirement": "计算机、电子信息、自动化、通信、车辆等相关专业（按岗位）",
            "skill_requirement": "按方向匹配 C/C++/Python、Linux、深度学习、芯片/嵌入式或测试能力",
            "experience_requirement": "相关项目、竞赛、论文或实习优先；无统一年限",
            "jd_source_url": row["source_url"],
            "jd_evidence_confidence": "中",
        }
    if company == "蔚来":
        return {
            "jd_summary": "智能电动汽车研发，南京/苏州开放算法、软件、自动驾驶、座舱、大模型、硬件和电池方向。",
            "responsibilities": "公开帖仅列算法、前后端、自动驾驶、智能座舱、大模型、硬件和电池等方向；具体职责按岗位详情。",
            "requirements": "2027届（帖子写2024.09-2027.08）；公开帖未披露统一学历、专业或技能门槛，需按具体岗位核对。",
            "education_requirement": "2027届；学历按具体职位",
            "major_requirement": "计算机、自动化、车辆、电子、电气、材料等按岗位",
            "skill_requirement": "按算法/软件/智驾/硬件/电池方向匹配；未统一披露",
            "experience_requirement": "相关项目/实习按具体岗位",
            "jd_source_url": row["source_url"],
            "jd_evidence_confidence": "中",
        }
    if company == "CVTE视源股份":
        return {
            "jd_summary": "交互显示、智慧家电、汽车座舱和音视频产品的软件、硬件、算法、制造与供应链研发。",
            "responsibilities": "软件岗参与嵌入式系统或应用软件设计、开发、测试和迭代；算法岗开展大模型/视觉/机器人等算法开发；硬件、制造质量和供应链岗按产品交付链路负责对应研发或运营。",
            "requirements": "2027届；官方门户列软件、硬件、研究院/工程院、算法等类别，具体学历、专业和技能以岗位页面为准。",
            "education_requirement": "2027届；具体岗位学历按官网",
            "major_requirement": "计算机、软件、电子、通信、自动化、机械、工业工程等按岗位",
            "skill_requirement": "按方向匹配 C/C++/Linux/嵌入式、Web、算法、硬件或制造供应链能力",
            "experience_requirement": "项目、竞赛、实习或开源经历按岗位加分；无统一年限",
            "jd_source_url": "https://campus.cvte.com/",
            "jd_evidence_confidence": "中",
        }
    if company == "小米集团":
        return {
            "jd_summary": "南京校招/实习入口，公开帖列软件研发、算法、硬件、芯片和产品方向。",
            "responsibilities": "公开帖未列南京单岗位职责；需在小米官网按南京城市筛选后，以具体职位详情为准。",
            "requirements": "公开帖未列统一学历、专业或技能门槛；内推码可用于实习/校招/社招，具体岗位条件以官网为准。",
            "education_requirement": "2027届；具体职位要求不同",
            "major_requirement": "软件、计算机、电子、通信、芯片、产品等按岗位",
            "skill_requirement": "按具体职位；未统一披露",
            "experience_requirement": "校招/实习按具体职位",
            "jd_source_url": row["source_url"],
            "jd_evidence_confidence": "中",
        }
    if company == "联想集团":
        return {
            "jd_summary": "技术、产品项目、供应链和设计等校招，岗位城市含南京/昆山。",
            "responsibilities": "高校就业网公开页列技术、产品项目、供应链、设计等方向，未展开单岗位职责。",
            "requirements": "2027届；具体学历、专业、技能和岗位 base 以联想官网职位详情为准。",
            "education_requirement": "2027届；具体职位学历未统一披露",
            "major_requirement": "计算机、电子、工业设计、供应链、管理等按岗位",
            "skill_requirement": "按具体职位；未统一披露",
            "experience_requirement": "应届生；未统一披露年限",
            "jd_source_url": row["source_url"],
            "jd_evidence_confidence": "中",
        }
    if company == "美的集团":
        return {
            "jd_summary": "研发技术、信息技术、制造技术和供应链等秋招，江苏工作地点含无锡/苏州。",
            "responsibilities": "公开帖仅列七大业务板块和八大职类，具体职责需按美的校招岗位详情核对。",
            "requirements": "2027届；公开帖未披露统一学历、专业和技能门槛。",
            "education_requirement": "2027届；具体职位学历按官网",
            "major_requirement": "计算机、电子、机械、自动化、工业工程、供应链等按岗位",
            "skill_requirement": "按研发/IT/制造/供应链岗位匹配；未统一披露",
            "experience_requirement": "应届生；项目/实习按具体岗位",
            "jd_source_url": row["source_url"],
            "jd_evidence_confidence": "中",
        }
    return details


def apply_leads(leads: list[dict[str, str]]) -> tuple[int, int, int]:
    from bin.career_os_store import get_db

    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = get_db()
    inserted = 0
    updated = 0
    try:
        with conn:
            for original in leads:
                row = dict(original)
                row.update(_jd_details(row))
                row["checked_at"] = checked_at
                row["dedupe_key"] = _dedupe_key(row)
                existing = conn.execute(
                    "SELECT id FROM platform_recruitment_leads WHERE dedupe_key = ?",
                    (row["dedupe_key"],),
                ).fetchone()
                values = tuple(
                    row[field]
                    for field in (
                        "platform",
                        "company_name",
                        "job_title",
                        "job_category",
                        "city",
                        "recruitment_type",
                        "graduation_range",
                        "source_url",
                        "apply_url",
                        "referral_code",
                        "posted_at",
                        "deadline",
                        "status",
                        "evidence_confidence",
                        "evidence_text",
                        "checked_at",
                        "notes",
                        "jd_summary",
                        "responsibilities",
                        "requirements",
                        "education_requirement",
                        "major_requirement",
                        "skill_requirement",
                        "experience_requirement",
                        "jd_source_url",
                        "jd_evidence_confidence",
                        "dedupe_key",
                    )
                )
                if existing is None:
                    conn.execute(
                        """
                        INSERT INTO platform_recruitment_leads (
                            platform, company_name, job_title, job_category, city,
                            recruitment_type, graduation_range, source_url, apply_url,
                            referral_code, posted_at, deadline, status,
                            evidence_confidence, evidence_text, checked_at, notes,
                            jd_summary, responsibilities, requirements,
                            education_requirement, major_requirement, skill_requirement,
                            experience_requirement, jd_source_url, jd_evidence_confidence,
                            dedupe_key
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        values,
                    )
                    inserted += 1
                else:
                    conn.execute(
                        """
                        UPDATE platform_recruitment_leads
                        SET platform = ?, company_name = ?, job_title = ?,
                            job_category = ?, city = ?, recruitment_type = ?,
                            graduation_range = ?, source_url = ?, apply_url = ?,
                            referral_code = ?, posted_at = ?, deadline = ?, status = ?,
                            evidence_confidence = ?, evidence_text = ?, checked_at = ?,
                            notes = ?, jd_summary = ?, responsibilities = ?,
                            requirements = ?, education_requirement = ?,
                            major_requirement = ?, skill_requirement = ?,
                            experience_requirement = ?, jd_source_url = ?,
                            jd_evidence_confidence = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE dedupe_key = ?
                        """,
                        values,
                    )
                    updated += 1
        total = int(
            conn.execute("SELECT COUNT(*) FROM platform_recruitment_leads").fetchone()[0]
        )
    finally:
        conn.close()
    return inserted, updated, total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="写入平台岗位线索表")
    args = parser.parse_args()

    print(f"curated_leads={len(LEADS)}")
    if not args.apply:
        print("dry_run=true (未写入数据库；使用 --apply 执行导入)")
        return 0
    inserted, updated, total = apply_leads(LEADS)
    print(f"inserted={inserted} updated={updated} platform_lead_total={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
