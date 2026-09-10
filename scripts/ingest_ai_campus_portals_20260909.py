"""幂等写入 AI 创业 / AI 应用 / 智驾具身 校招门户。只改 companies。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db  # noqa: E402

# 目标是中小厂/创业，互联网超大厂不入库、重跑也不要加回来。
EXCLUDE_NAMES = {
    "字节跳动",
    "腾讯",
    "阿里巴巴集团",
    "阿里云",
    "百度",
    "美团",
    "拼多多 (PDD)",
    "蚂蚁集团",
    "滴滴",
    "NVIDIA中国",
    "小红书",
    "哔哩哔哩",
    "蔚来 (NIO)",
    "小鹏汽车",
    "理想汽车",
    "商汤科技 (SenseTime)",
}

PORTALS = [
    {
        "name": "商汤科技 (SenseTime)",
        "alias": "商汤",
        "city": "上海/深圳/北京",
        "website": "https://www.sensetime.com/",
        "campus_url": "https://hr.sensetime.com/campus",
        "industry": "人工智能/大模型应用",
        "company_type": "港股上市AI龙头",
        "campus_application_rules": "2027校园招聘（毕业约2026.9–2027.12）。职位 https://hr-jobs.sensetime.com/edu/ 投前核届别。方向含多模态/智能体。",
    },
    {
        "name": "阶跃星辰 (StepFun)",
        "alias": "阶跃星辰",
        "city": "上海/北京",
        "website": "https://www.stepfun.com/",
        "campus_url": "https://app.mokahr.com/campus-recruitment/step/94905#/jobs",
        "industry": "大模型/Agent",
        "company_type": "明星独角兽",
        "campus_application_rules": "2027 StepStar。可见LLM/多模态/Agent/语音；部分为实习岗。",
    },
    {
        "name": "月之暗面 (Moonshot / Kimi)",
        "alias": "月之暗面",
        "city": "北京/上海/深圳",
        "website": "https://www.moonshot.cn/",
        "campus_url": "https://app.mokahr.com/campus-recruitment/moonshot/148507",
        "industry": "大模型/AI助手",
        "company_type": "明星独角兽",
        "campus_application_rules": "校招Moka已开，当前多见实习（Agent Development等）。2027正式批专题未写死。社招 https://app.mokahr.com/apply/moonshot/148506",
    },
    {
        "name": "百川智能",
        "alias": "百川",
        "city": "北京",
        "website": "https://www.baichuan-ai.com/",
        "campus_url": "https://cq6qe6bvfr6.jobs.feishu.cn/baichuanzhaopin",
        "industry": "大模型",
        "company_type": "明星独角兽",
        "campus_application_rules": "星耀计划-实习生在招（后训练/RL Infra/Agent Harness）。未见标注2027正式校招专题。",
    },
    {
        "name": "智谱AI (Zhipu / GLM)",
        "alias": "智谱",
        "city": "北京",
        "website": "https://www.zhipuai.cn/",
        "campus_url": "https://zhipu-ai.jobs.feishu.cn/zhipucampus/",
        "industry": "大模型/行业应用",
        "company_type": "明星独角兽",
        "campus_application_rules": "飞书校招站FAQ可能仍写旧届。2027届实习含行业应用算法/Infra/Java，可转正。",
    },
    {
        "name": "面壁智能 (ModelBest)",
        "alias": "面壁智能",
        "city": "上海/深圳/北京",
        "website": "https://www.modelbest.cn/",
        "campus_url": "https://modelbest.jobs.feishu.cn/career",
        "industry": "大模型/端侧",
        "company_type": "明星科创",
        "campus_application_rules": "春招文面向约2026.8–2028.8硕博（覆盖2027硕博）；本科是否开放未写。方向含智能体/行业应用/AI Infra。",
    },
    {
        "name": "无问芯穹 (Infini-AI)",
        "alias": "无问芯穹",
        "city": "上海/北京/杭州",
        "website": "https://www.infini-ai.com/",
        "campus_url": "https://infinigence.jobs.feishu.cn/infinigence",
        "industry": "AI Infra/大模型系统",
        "company_type": "明星科创",
        "campus_application_rules": "滚动实习/应届，非完整2027专场。可见推理框架实习、运维工程师、AI云平台测试。",
    },
    {
        "name": "追一科技",
        "alias": "追一",
        "city": "深圳/上海/南京",
        "website": "https://www.zhuiyi.ai/",
        "campus_url": "https://zhuiyi.ai/talent/",
        "industry": "对话AI/智能客服",
        "company_type": "独角兽",
        "campus_application_rules": "人才页有校园招聘入口。Moka https://app.mokahr.com/campus_apply/wezhuiyi/3440 。2027届别未在人才页写明。",
    },
    {
        "name": "零一万物 (01.AI)",
        "alias": "零一万物",
        "city": "北京",
        "website": "https://www.lingyiwanwu.com/",
        "campus_url": "https://www.lingyiwanwu.com/careers.html",
        "industry": "大模型应用",
        "company_type": "明星独角兽",
        "campus_application_rules": "官网跳转飞书 https://01ai.jobs.feishu.cn/index/ 。届别未核，偏研究/工程/大模型应用。",
    },
    {
        "name": "旷视科技 (Megvii)",
        "alias": "旷视",
        "city": "北京/上海/南京",
        "website": "https://www.megvii.com/",
        "campus_url": "https://app.mokahr.com/campus-recruitment/megviihr/146855",
        "industry": "计算机视觉/多模态",
        "company_type": "独角兽",
        "campus_application_rules": "公开信息多为2026届；实习含上海/南京。官方2027批次未在本次页面核到。",
    },
    {
        "name": "深度求索 (DeepSeek)",
        "alias": "DeepSeek",
        "city": "北京/杭州",
        "website": "https://www.deepseek.com/",
        "campus_url": "https://app.mokahr.com/social-recruitment/high-flyer/140576#/",
        "industry": "大模型/Agent",
        "company_type": "明星独角兽",
        "campus_application_rules": "无独立2027校招专题。滚动社招+实习（幻方Moka）。报道含运维/Agent Infra/服务端。邮箱 talent@deepseek.com。城市不在江苏核心圈。",
    },
    {
        "name": "字节跳动",
        "alias": "字节",
        "city": "上海/深圳/杭州/北京",
        "website": "https://www.bytedance.com/",
        "campus_url": "https://jobs.bytedance.com/campus",
        "industry": "互联网/大模型应用",
        "company_type": "明星独角兽",
        "campus_application_rules": "2027校园招聘（毕业约2026.9–2027.8）。可见大模型应用、AI Agent、飞书算法、扣子Coze实习（RAG/Agent）。全年约4次投递。",
    },
    {
        "name": "腾讯",
        "alias": "腾讯",
        "city": "深圳/上海/北京",
        "website": "https://www.tencent.com/",
        "campus_url": "https://join.qq.com/",
        "industry": "互联网/混元应用",
        "company_type": "上市巨头",
        "campus_application_rules": "2027校园招聘（毕业约2026.1–2027.12）。选应届-2027。口径含AI全栈/Agent/AI应用。云智研发 https://join.tencent-cloud.com",
    },
    {
        "name": "阿里巴巴集团",
        "alias": "阿里",
        "city": "杭州/上海/深圳/北京",
        "website": "https://www.alibaba.com/",
        "campus_url": "https://campus-talent.alibaba.com/?lang=zh",
        "industry": "互联网/通义应用",
        "company_type": "上市巨头",
        "campus_application_rules": "2027应届（毕业约2026.11.1–2027.10.31）。含全栈AI/Agent/通义。瓴羊AgentOne走集团校招筛自定义部门。钉钉走悟空事业部。",
    },
    {
        "name": "阿里云",
        "alias": "阿里云",
        "city": "杭州/上海/深圳/北京",
        "website": "https://www.aliyun.com/",
        "campus_url": "https://careers.aliyun.com/campus/home?lang=zh",
        "industry": "云计算/大模型应用",
        "company_type": "上市巨头",
        "campus_application_rules": "2027云校招。通知 https://careers.aliyun.com/campus/notice?code=1&lang=zh&tab=notice 。方向含灵码/通义应用。",
    },
    {
        "name": "百度",
        "alias": "百度",
        "city": "北京/上海/深圳",
        "website": "https://www.baidu.com/",
        "campus_url": "https://talent.baidu.com/jobs/",
        "industry": "互联网/文心应用",
        "company_type": "上市巨头",
        "campus_application_rules": "2027届（约2026.9–2027.8）。上海可见大模型研发（RAG/Agent）、智能体算法。日程 https://talent.baidu.com/jobs/trend",
    },
    {
        "name": "小红书",
        "alias": "小红书",
        "city": "上海/深圳/北京/杭州",
        "website": "https://www.xiaohongshu.com/",
        "campus_url": "https://campus.xiaohongshu.com/",
        "industry": "社区/AI应用",
        "company_type": "独角兽",
        "campus_application_rules": "2027校园招聘+REDstar。方向含基座大模型、AI Agent、AI Infra、AI Coding。",
    },
    {
        "name": "哔哩哔哩",
        "alias": "B站",
        "city": "上海/深圳/北京",
        "website": "https://www.bilibili.com/",
        "campus_url": "https://jobs.bilibili.com/campus",
        "industry": "互联网/多模态",
        "company_type": "港股上市IT龙头",
        "campus_application_rules": "2027秋招。实习可见多模态智能体、LLM、AI Infra（上海）。",
    },
    {
        "name": "拼多多 (PDD)",
        "alias": "拼多多",
        "city": "上海",
        "website": "https://www.pinduoduo.com/",
        "campus_url": "https://careers.pddglobalhr.com/campus",
        "industry": "电商/大模型应用",
        "company_type": "上市巨头",
        "campus_application_rules": "2027届。本科可关注AI Agent研发；云弧计划大模型/AI Infra偏硕博。",
    },
    {
        "name": "美团",
        "alias": "美团",
        "city": "北京/上海/深圳/南京",
        "website": "https://www.meituan.com/",
        "campus_url": "https://campus.meituan.com/",
        "industry": "生活服务/大模型应用",
        "company_type": "上市巨头",
        "campus_application_rules": "2027应届（约2026.11–2027.10），网申约至10-31。新增AI全栈/AI产品；北斗含大模型应用。",
    },
    {
        "name": "作业帮",
        "alias": "作业帮",
        "city": "北京/上海",
        "website": "https://www.zybang.com/",
        "campus_url": "https://app.mokahr.com/campus-recruitment/zuoyebang/150514?locale=zh-CN",
        "industry": "教育科技/AI应用",
        "company_type": "独角兽",
        "campus_application_rules": "核实到2027暑期实习可转正，含AI应用算法（Agent/RAG）。正式批以Moka实时为准。",
    },
    {
        "name": "得物",
        "alias": "得物",
        "city": "上海",
        "website": "https://www.dewu.com/",
        "campus_url": "https://campus.dewu.com/",
        "industry": "电商/算法",
        "company_type": "独角兽",
        "campus_application_rules": "2027暑期实习可转正已核实。正式批以官网列表为准。实习飞书 https://poizon.jobs.feishu.cn/s/M8kOAZUefq4",
    },
    {
        "name": "蚂蚁集团",
        "alias": "蚂蚁",
        "city": "杭州/上海/深圳/北京",
        "website": "https://www.antgroup.com/",
        "campus_url": "https://talent.antgroup.com/campus/home",
        "industry": "金融科技/AI应用",
        "company_type": "独角兽",
        "campus_application_rules": "2027校园招聘。官方称技术岗AI相关占比高：应用/Infra/安全/具身。毕业窗口约2026.11–2027.10。",
    },
    {
        "name": "NVIDIA中国",
        "alias": "NVIDIA",
        "city": "北京/上海/深圳",
        "website": "https://www.nvidia.cn/",
        "campus_url": "https://app.mokahr.com/campus-recruitment/nvidia/47111?locale=zh-CN#/",
        "industry": "GPU/AI Infra",
        "company_type": "外企",
        "campus_application_rules": "2027校园招聘Moka。方向含LLM推理优化、AI与HPC、强化学习、AI基础设施。",
    },
    {
        "name": "寒武纪",
        "alias": "寒武纪",
        "city": "北京/上海/深圳/南京",
        "website": "https://www.cambricon.com/",
        "campus_url": "https://www.cambricon.com/index.php?m=content&c=index&a=lists&catid=7",
        "industry": "AI芯片/软件栈",
        "company_type": "科创板上市",
        "campus_application_rules": "报道称2027届已启动。软件类含AI软件/大模型优化/AI应用。岗位列表可能走公众号或邮箱 campus@cambricon.com。",
    },
    {
        "name": "蔚来 (NIO)",
        "alias": "蔚来",
        "city": "上海/深圳/南京",
        "website": "https://www.nio.com/",
        "campus_url": "https://campus.nio.com",
        "industry": "智能电动车/智驾",
        "company_type": "港股上市",
        "campus_application_rules": "2027全职（窗口含往届）。数字技术含算法/智驾/大模型；有技术运维类。网申约至10月。",
    },
    {
        "name": "小鹏汽车",
        "alias": "小鹏",
        "city": "上海/深圳",
        "website": "https://www.xiaopeng.com/",
        "campus_url": "https://xiaopeng.jobs.feishu.cn/campus",
        "industry": "智能电动车/具身",
        "company_type": "港股上市",
        "campus_application_rules": "2027探索者计划。镜像 https://campus.xiaopeng.com/ 。含通用智能/智能机器人/物理AI。",
    },
    {
        "name": "理想汽车",
        "alias": "理想",
        "city": "上海/深圳/北京",
        "website": "https://www.lixiang.com/",
        "campus_url": "https://www.lixiang.com/employ/campus.html?fromJob=1",
        "industry": "智能电动车/自动驾驶",
        "company_type": "港股上市",
        "campus_application_rules": "官网写2027校园招聘。大类含算法与软件。",
    },
    {
        "name": "文远知行 (WeRide)",
        "alias": "文远知行",
        "city": "上海/深圳/南京",
        "website": "https://www.weride.ai/",
        "campus_url": "https://app.mokahr.com/campus_apply/jingchi/2137#/",
        "industry": "自动驾驶",
        "company_type": "独角兽",
        "campus_application_rules": "2027秋招已启动。算法含CV/感知/SLAM。公告 https://www.weride.ai/zh/posts/gjekqtwayx4acykbjqdt2eyi",
    },
    {
        "name": "小马智行 (Pony.ai)",
        "alias": "小马智行",
        "city": "上海/北京",
        "website": "https://www.pony.ai/",
        "campus_url": "https://campus.pony.ai",
        "industry": "自动驾驶",
        "company_type": "独角兽",
        "campus_application_rules": "2027校园招聘。投递 https://ponyai.jobs.feishu.cn/ponycampus 。研发Generalist，含感知/端到端。每人最多2岗。",
    },
    {
        "name": "元戎启行 (DeepRoute)",
        "alias": "元戎启行",
        "city": "深圳/上海/北京",
        "website": "https://www.deeproute.ai/",
        "campus_url": "https://app.mokahr.com/campus-recruitment/deeproute/145894#/",
        "industry": "自动驾驶/AI Agent",
        "company_type": "独角兽",
        "campus_application_rules": "2027秋招。含大模型/AI Agent/感知/AI Infra。每人仅1岗。截止以官网为准。",
    },
    {
        "name": "银河通用 (Galbot)",
        "alias": "银河通用",
        "city": "深圳/苏州/北京",
        "website": "https://www.galbot.com/",
        "campus_url": "https://app.mokahr.com/campus-recruitment/yinhetongyong/165930?locale=zh-CN#/page/2027%E5%B1%8A%E6%A0%A1%E5%9B%AD%E6%8B%9B%E8%81%98",
        "industry": "具身智能",
        "company_type": "独角兽",
        "campus_application_rules": "2027秋招「具身领航者」。算法简章偏硕博；软件系统可看本科。",
    },
    {
        "name": "奥比中光",
        "alias": "奥比中光",
        "city": "深圳",
        "website": "https://www.orbbec.com.cn/",
        "campus_url": "http://job.orbbec.com.cn/campus",
        "industry": "3D视觉/机器人感知",
        "company_type": "科创板上市",
        "campus_application_rules": "27届校招在第三方仍更新。算法多硕以上；软件开发本科以上。门户JS可能无正文。",
    },
    {
        "name": "轻舟智航 (QCraft)",
        "alias": "轻舟智航",
        "city": "苏州/上海",
        "website": "https://www.qcraft.ai/",
        "campus_url": "https://qcraft.jobs.feishu.cn/campus",
        "industry": "自动驾驶",
        "company_type": "独角兽",
        "campus_application_rules": "岗墙现多为26届全职+2027实习（世界模型/端到端）。适合先实习。苏州本地。",
    },
    {
        "name": "节卡机器人 (JAKA)",
        "alias": "节卡",
        "city": "上海/常州/深圳",
        "website": "https://www.jaka.com/",
        "campus_url": "https://www.jaka.com/zh/position",
        "industry": "协作机器人/具身",
        "company_type": "科创板上市专精特新",
        "campus_application_rules": "官网有校园招聘入口。具身智能交付工程师（培训/二次开发/现场支持）对口应用层；销售应届写2026–2027毕业。",
    },
    {
        "name": "滴滴",
        "alias": "滴滴",
        "city": "北京/上海",
        "website": "https://www.didiglobal.com/",
        "campus_url": "https://campus.didiglobal.com",
        "industry": "出行/自动驾驶",
        "company_type": "独角兽",
        "campus_application_rules": "跳转Moka https://campus.didiglobal.com/campus_apply/didiglobal/96064 。2027未来精英含感知/规划；自动驾驶精英岗简章常写北京。",
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
        if item["name"] in EXCLUDE_NAMES:
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
    for t in ("companies", "jobs", "job_targets", "platform_recruitment_leads", "applications"):
        print(f"{t}\t{conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
    n_url = conn.execute(
        "SELECT COUNT(*) FROM companies WHERE TRIM(COALESCE(campus_url,''))!=''"
    ).fetchone()[0]
    print(f"campus_url_filled\t{n_url}")
    print(f"inserted\t{inserted}\nupdated\t{updated}\nskipped\t{skipped}\nbatch\t{len(PORTALS)}")
    conn.close()


if __name__ == "__main__":
    main()
