"""补齐 7 家每家至少 3 岗。放宽：上海可入、硕士可作库存、CS 向校招可入。

仍要求门户原文、不编造、非 3 年+社招。
入库后由 job_ingest_gate 拦截：CET-4 硬门槛、JD 过细不像培养。
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
from bin.services.job_ingest_gate import ingest_gate_reasons  # noqa: E402

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
SOURCE = "campus-jd-20260912"

JOBS = [
    {
        "alias": "纳芯微",
        "job_title": "【2027届校招】AI应用工程师(J11348)",
        "city": "上海",
        "education_req": "2027届统招本科及以上；计算机/软件/人工智能等相关",
        "job_category": "AI应用",
        "apply_url": "https://www.moseeker.com/position/index/pid/3480867",
        "source_job_id": "moseeker-3480867-J11348",
        "responsibilities": (
            "1. 参与公司研发流程、经营闭环及重点业务场景的调研与访谈，协助识别高频、高价值、可衡量的 AI 应用机会，输出场景清单与需求分析初稿。\n"
            "2. 协助将业务问题拆解为标准 Workflow、可复用 Skill、知识库支撑、工具调用等模块，参与 AI 应用架构图、流程图、需求说明及试点方案的绘制与编写。\n"
            "3. 支持重点 AI 场景的试点推进，配合业务方 Owner 与技术团队完成 Agent 工作流搭建、提示词设计、知识库接入、工具/API 配置及基础测试验证。\n"
            "4. 跟踪试点场景的使用数据、准确性与用户反馈，参与问题分析与方案迭代，协助将成熟能力沉淀为 Skill 模板、提示词模板、知识库条目与操作手册。\n"
            "5. 与产品、研发、质量、项目管理等跨部门团队协作，参与案例复盘、内部经验分享与培训材料准备，推动 AI 能力从个人工具走向业务流程。\n"
            "6. 持续学习大模型、Agent、RAG、MCP 等 AI 前沿技术与行业实践，结合公司业务场景形成学习笔记、竞品调研或应用建议。"
        ),
        "requirements": (
            "2027 届应届毕业生，全日制统招本科及以上学历；计算机科学与技术、软件工程、人工智能、数据科学、自动化、电子信息、信息管理、工业工程、管理科学等相关专业。\n"
            "熟悉至少一种编程语言（Python 优先）；接触过 GPT/Claude 等大模型或 Dify/Coze/LangChain 等即可。\n"
            "半导体相关专业优先，但非硬性要求。"
        ),
        "notes": "仟寻 pid/3480867 原文。城市上海。",
        "weight": 88,
        "reason": "2027本科，计算机可投，AI应用对口项目。",
    },
    {
        "alias": "纳芯微",
        "job_title": "【2027届校招】现场应用工程师（ACE计划）(J11388)",
        "city": "上海/苏州",
        "education_req": "硕士及以上，电子相关专业",
        "job_category": "现场应用/FAE",
        "apply_url": "https://www.moseeker.com/position/index/pid/3480899",
        "source_job_id": "moseeker-3480899-J11388",
        "responsibilities": (
            "1. 熟悉公司产品和服务，了解客户应用场景，在客户端提供专业技术支持；\n"
            "2. 快速响应客户需求，拆解分析技术难点，协助解决客户端产品应用问题，推动产品在客户项目的落地量产；\n"
            "3. 归纳总结客户端应用问题及解决方案，形成相关技术文档，助力公司产品的市场推广；\n"
            "4. 了解行业动态，跟踪技术趋势，为新产品定义提供应用相关的技术支持，驱动公司产品竞争力提升。"
        ),
        "requirements": (
            "1. 学历要求：硕士及以上\n"
            "2. 专业要求：电力电子、电气工程、自动化、通讯、微电子、电子信息等电子相关专业\n"
            "扎实的专业技术；良好的沟通表达及团队协作能力；较强的逻辑分析和解决问题的能力；熟练的中英文表达和阅读能力。"
        ),
        "notes": "ACE FAE 写死硕士，仅作库存凑每家 3 岗。本科勿海投。",
        "weight": 52,
        "reason": "2027 FAE，含苏州，但硕士门槛。",
    },
    {
        "alias": "晶丰明源",
        "job_title": "应用工程师（软件）（上海）(J10548)",
        "city": "上海",
        "education_req": "计算机、电子、通信、自动化等相关专业，本科及以上",
        "job_category": "应用工程师",
        "apply_url": "https://bpsemi.zhiye.com/campus/detail?jobAdId=18dc3191-4209-49e3-97d2-016b948100ef",
        "source_job_id": "bps-J10548",
        "responsibilities": (
            "1.负责单片机芯片底层软件驱动的开发与调试，配合硬件工程师协作，完成硬件产品的调试和测试；\n"
            "2.根据产品规划，进行产品软件功能模块的设计编码工作；\n"
            "3.协助与指导测试人员完成产品的相关测试；\n"
            "4.撰写软件相关的技术文档。"
        ),
        "requirements": (
            "1.计算机、电子、通信、自动化等相关专业，本科及以上学历；\n"
            "2.爱好电子开发，在校有实际电子产品设计经历；\n"
            "3.性格开朗、做事细致，对新技术及新产品有较好的学习能力；\n"
            "4.熟悉ARM、STM32、8051其中两款以上MCU芯片编程；\n"
            "5.有一定的电子电路硬件基础，能看懂电路图并设计基本应用电路；\n"
            "6.具备良好的编码风格和文档编写习惯，具有良好的沟通技巧和团队精神。"
        ),
        "notes": "bpsemi 列表接口原文。上海。补齐每家 3 岗。",
        "weight": 80,
        "reason": "校招应用软件，本科含计算机。",
    },
    {
        "alias": "南芯",
        "job_title": "2027校招AI应用工程师(J11461)",
        "city": "上海/南京",
        "education_req": "本科及以上，计算机/软件工程/人工智能等相关，有项目实践者专业不限",
        "job_category": "AI应用",
        "apply_url": "https://nanxin.zhiye.com/campus/detail?jobAdId=82cfcb16-9d0f-4c3a-bd8b-494c80090b00",
        "source_job_id": "nanxin-J11461",
        "responsibilities": (
            "1、参与公司级应用平台及业务系统的设计与开发，协助完成模块实现与接口对接\n"
            "2、在导师指导下完成功能编码与单元自测，参与既有业务系统的日常维护与 Bug 修复\n"
            "3、对接各业务部门需求，协同完成从需求理解到 AI 功能落地的端到端交付\n"
            "4、参与公共组件与技术基建工作，推动可复用能力的沉淀与共享\n"
            "5、撰写接口文档、技术说明等配套资料，参与系统联调与上线\n"
            "6、熟练运用 AI 编程辅助工具，探索 AI 赋能研发提效的实践方法"
        ),
        "requirements": (
            "1、本科及以上学历，计算机、软件工程、人工智能、电子信息、通信工程、自动化等相关专业应届毕业生，有软件开发或 AI 项目实践经验者专业不限\n"
            "2、掌握 Java 或 Python 编程语言，了解 SpringBoot、MyBatis 等开发框架\n"
            "3、掌握 MySQL 基础操作，熟悉 Git/SVN 代码管理工具，了解 Nginx、Tomcat 基础服务\n"
            "4、具备 HTML、CSS、JS 基础，有 Vue、Layui 开发实践经验优先\n"
            "5、了解常用软件设计模式，能够独立完成简单模块方案设计\n"
            "6、有大模型、AI 应用相关项目实践，会使用 AI 编程工具者优先"
        ),
        "notes": "nanxin.zhiye 列表接口原文。LocNames 空，城市按公司档案上海/南京记，投前核门户。",
        "weight": 84,
        "reason": "2027本科计算机可投，AI应用对口。",
    },
    {
        "alias": "南芯",
        "job_title": "2027校招应用工程师(J11464)",
        "city": "上海/南京",
        "education_req": "本科及以上，电力电子/电气/电子信息/自动化/仪器仪表等相关",
        "job_category": "应用工程师",
        "apply_url": "https://nanxin.zhiye.com/campus/detail?jobAdId=73c21894-b969-420f-9ce6-b99b2354c999",
        "source_job_id": "nanxin-J11464",
        "responsibilities": (
            "1. 负责公司产品性能的测试，验证和相关问题；Debug；\n"
            "2. 设计公司产品EVM并撰写推广过程中相关技术文档；\n"
            "3. 为前端销售/FAE团队及客户提供技术培训和技术支持；"
        ),
        "requirements": (
            "1.本科及以上学历，电力电子，电气工程，电子信息，自动化，仪器仪表等相关专业；\n"
            "2.优秀的专业基础知识和学习能力；\n"
            "3.自驱力和执行力强，有好奇心和责任心；"
        ),
        "notes": "列表接口原文。LocNames 空，按公司档案记上海/南京。",
        "weight": 74,
        "reason": "2027校招应用，本科。",
    },
    {
        "alias": "南芯",
        "job_title": "系统应用实习生(J11331)",
        "city": "上海/南京",
        "education_req": "本科及以上，电力电子/电气/电子信息/自动化/仪器仪表等相关",
        "job_category": "系统应用实习",
        "apply_url": "https://nanxin.zhiye.com/campus/detail?jobAdId=01e180b5-0dc4-4afb-842f-5e85f0936334",
        "source_job_id": "nanxin-J11331",
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
        "notes": "校招 CategoryId=2。LocNames 空。",
        "weight": 70,
        "reason": "系统应用实习，本科。",
    },
    {
        "alias": "卓胜微",
        "job_title": "【27届校招】IT工程师",
        "city": "无锡",
        "education_req": "本科及以上，计算机/软件工程/自动化/数学/统计等相关",
        "job_category": "IT运维/开发",
        "apply_url": "https://maxscend.zhiye.com/campus/detail?jobAdId=b6f65a0b-fac4-4c63-90f2-648a367fbb92",
        "source_job_id": "max-IT-27",
        "responsibilities": (
            "1、负责MES、EAP、YMS等生产系统的日常运维、故障处理与on call技术支持；\n"
            "2、负责业务需求收集、系统二次开发、功能测试与上线部署；\n"
            "3、负责生产数据的ETL处理、大数据平台建设与可视化分析；\n"
            "4、负责数据库维护（Oracle/SQL Server）、用户权限管理与项目文档编写。"
        ),
        "requirements": (
            "1、学历专业：本科及以上，计算机、软件工程、自动化、数学、统计等相关专业。\n"
            "2、掌握 Java、C#、C/C++ 中至少两种开发语言；熟悉 Oracle、SQL Server、MySQL 等至少一种数据库；熟悉 Windows、Linux 基本操作；\n"
            "3、能适应产线7×24小时on call支持（轮值）。"
        ),
        "notes": "maxscend 27届校招。无锡总部。运维/on call，城市按总部无锡记，投前核门户。",
        "weight": 78,
        "reason": "无锡校招IT运维，本科计算机。",
    },
    {
        "alias": "卓胜微",
        "job_title": "FAE技术支持工程师（上海/深圳/西安）",
        "city": "上海/深圳/西安",
        "education_req": "本科及以上，电子相关，欢迎应届",
        "job_category": "现场应用/FAE",
        "apply_url": "https://maxscend.zhiye.com/campus/detail?jobAdId=0bfc8986-c65f-4bb2-a8f8-65dd03fe4ade",
        "source_job_id": "max-FAE-sh-sz-xa",
        "responsibilities": (
            "1、针对RF射频小器件开关，PA，LNA，天线调谐产品线支持客户design-in\n"
            "2、解决客户生产中出现的问题\n"
            "3、配合销售进行推广\n"
            "4、新产品的内部应用验证"
        ),
        "requirements": (
            "1、本科及以上学历，电子相关专业，欢迎相关专业应届毕业生应聘\n"
            "2、具有电磁场和微波相关知识背景\n"
            "3、网络分析仪、频谱仪、手机综测仪等相关仪表的使用\n"
            "4、具备良好的沟通能力和优秀的团队协作能力"
        ),
        "notes": "欢迎应届，但城市无无锡。凑每家 3 岗库存，江苏优先勿投此条。",
        "weight": 50,
        "reason": "应届FAE，城市不在江苏。",
    },
    {
        "alias": "卓胜微",
        "job_title": "芯片测试工程师（27届实习）",
        "city": "无锡",
        "education_req": "微电子/集成电路相关，实习可转正",
        "job_category": "芯片测试实习",
        "apply_url": "https://maxscend.zhiye.com/campus/detail?jobAdId=a8069ee1-a5e1-4064-a1e6-c2cac9386c59",
        "source_job_id": "max-test-intern-27",
        "responsibilities": (
            "根据实验室相关规则和任务分配情况，从事实习任务：\n"
            "1、PAMiD相关测试/产品RD NPI相关测试/镭射测试/设备管理\n"
            "2、射频SW/LNA/Module的测试优化、验证、老化测试、MIPI测试、IEC测试、数据处理及实验室调试和debug"
        ),
        "requirements": (
            "1、逻辑思维强，学习能力强，能吃苦\n"
            "2、微电子/集成电路相关专业\n"
            "3、每周出勤5天，实习3个月以上\n"
            "4、可实习至留用（有转正机会）"
        ),
        "notes": "27届实习。城市按无锡总部记。",
        "weight": 58,
        "reason": "无锡实习测试，可转正。",
    },
    {
        "alias": "乐鑫",
        "job_title": "芯片系统测试工程师（校园招聘）",
        "city": "上海/苏州",
        "education_req": "本科及以上，微电子/计算机/自动化等相关",
        "job_category": "芯片系统测试",
        "apply_url": "https://www.espressif.com/zh-hans/join-us/job-search?field_job_classification_tid%5B0%5D=2575&field_job_classification_tid%5B1%5D=2573",
        "source_job_id": "esp-chip-sys-test",
        "responsibilities": (
            "1、芯片回片 Bringup；\n"
            "2、芯片功能 API 接口编写和交付；\n"
            "3、芯片测试计划和测试用例的编写，完成测试以及报告输出；\n"
            "4、芯片相关功能的 ATE 测试计划和测试代码的编写，配合 ATE team 进行调试和数据分析；\n"
            "5、解决相关功能的客户问题。"
        ),
        "requirements": (
            "1、本科及以上学历，微电子/计算机/自动化等相关专业；\n"
            "2、熟悉 Linux，熟练使用 C 以及 Python，理解电路基础知识；\n"
            "3、熟悉示波器/万用表/信号发生器等常用测试仪器；\n"
            "4、良好的沟通能力。"
        ),
        "notes": "espressif 校园招聘页原文。投递 campus@espressif.com。城市按公司档案上海/苏州。",
        "weight": 76,
        "reason": "本科含计算机，Linux/C/Python 测试。",
    },
    {
        "alias": "乐鑫",
        "job_title": "射频系统验证工程师（校园招聘）",
        "city": "上海/苏州",
        "education_req": "本科及以上，微电子/通信/计算机/自动化相关",
        "job_category": "系统验证",
        "apply_url": "https://www.espressif.com/zh-hans/join-us/job-search?field_job_classification_tid%5B0%5D=2575&field_job_classification_tid%5B1%5D=2573",
        "source_job_id": "esp-rf-sys-verify",
        "responsibilities": (
            "1、射频模块参数验证；\n"
            "2、WIFI/BLE 的射频性能测试和优化；\n"
            "3、Python 测试脚本的编写与维护；\n"
            "4、PHY 驱动代码和功能 API 接口的发布与支持；\n"
            "5、ATE 量产测试项目的驱动维护，协助解决量产问题和数据分析；\n"
            "6、协助研发定位和解决验证问题；\n"
            "7、协助解决软件测试和客户应用问题。"
        ),
        "requirements": (
            "1、本科及以上学历，微电子/通信/计算机/自动化相关专业；\n"
            "2、具有良好的沟通和团队合作能力；\n"
            "3、熟悉 C 语言和 Python 编程，有芯片自动化测试平台搭建经验为佳。"
        ),
        "notes": "espressif 校园招聘页原文。",
        "weight": 74,
        "reason": "本科含计算机，Python 验证脚本。",
    },
    {
        "alias": "乐鑫",
        "job_title": "大学生态与产业研究专员（校园招聘）",
        "city": "上海/苏州",
        "education_req": "本科及以上，电子/通信/自动化/软件/计算机/物联网优先",
        "job_category": "校企生态/运营",
        "apply_url": "https://www.espressif.com/zh-hans/join-us/job-search?field_job_classification_tid%5B0%5D=2575&field_job_classification_tid%5B1%5D=2573",
        "source_job_id": "esp-campus-eco",
        "responsibilities": (
            "1、负责推动公司与国内高校的产学研合作、校园黑客松、技术竞赛、开发者沙龙及校园行等项目；\n"
            "2、负责高校活动及赛事的全流程项目管理；\n"
            "3、负责高校教师、学生及校园开发者社群的日常运营与关系维护；\n"
            "4、跟踪 MCU、Wi-Fi、AIoT、RISC-V、边缘 AI、机器人及智能硬件等领域的技术和产业趋势。"
        ),
        "requirements": (
            "1、本科及以上学历，电子工程、通信、自动化、软件工程、计算机、物联网等相关专业优先；\n"
            "2、欢迎优秀应届毕业生及 3 年以内工作经验的候选人；\n"
            "3、具有高校社团活动、技术竞赛、黑客松、开发者社区等项目组织或运营经验者优先。"
        ),
        "notes": "espressif 校园招聘页原文。沟通/活动向，非 FAE。",
        "weight": 66,
        "reason": "本科计算机可投，校企生态运营。",
    },
    {
        "alias": "中茵微",
        "job_title": "数字IC验证工程师（校招）",
        "city": "南京/北京/成都",
        "education_req": "本科及以上，微电子、集成电路、物理、数学等相关",
        "job_category": "数字验证",
        "apply_url": "https://joinsilicon.zhiye.com/campus/jobs",
        "source_job_id": "join-dv-2026",
        "responsibilities": (
            "1、负责模块或系统级验证；\n"
            "2、负责验证方案和策略的制定，验证feature提取，并进行评审；\n"
            "3、负责验证环境搭建，验证用例开发以及验证执行；\n"
            "4、负责验证过程中的问题定位和追踪，与设计配合解决问题；\n"
            "5、负责覆盖率收集及分析，验证质量活动，保证验证的完备性；\n"
            "6、输出验证过程中的评审文档，以及质量活动文档；\n"
            "7、负责或参与验证效率提升工具的开发。"
        ),
        "requirements": (
            "1、本科及以上学历，微电子、集成电路等相关专业；\n"
            "2、熟练掌握C语言，Verilog，SystemVerilog，Python等脚本语言；\n"
            "3、熟练使用vcs、verdi等开发工具；\n"
            "4、工作认真仔细，责任心强，质量意识好，有良好的沟通能力和团队协作精神；\n"
            "5、具备数字电路基础，有设计、验证经验者优先。"
        ),
        "notes": "2026-09-12 门户 campus 列表接口 0 条；2027简章牛企写网申已截止。职责来自南开就业网转载的中茵微校招 JD。投前打开门户确认是否重新开放。",
        "weight": 48,
        "reason": "南京可投、本科、Python/验证；门户当前空窗。",
    },
    {
        "alias": "中茵微",
        "job_title": "数字IC设计工程师（校招）",
        "city": "南京/北京/成都",
        "education_req": "任职资格写本科及以上；部分转载页写硕士/博士",
        "job_category": "数字设计",
        "apply_url": "https://joinsilicon.zhiye.com/campus/jobs",
        "source_job_id": "join-de-2026",
        "responsibilities": (
            "1、参与IP模块或SoC数字设计，根据设计需求，确定设计方案，并负责 RTL 实现；\n"
            "2、配合验证团队完成 IP、芯片验证相关工作；\n"
            "3、配合或参与 FPGA 验证；\n"
            "4、模块级时序约束、综合、STA 检查等；\n"
            "5、配合后端团队完成芯片实现相关工作；\n"
            "6、撰写文档，协助软件验证人员解决设计问题。"
        ),
        "requirements": (
            "1、本科及以上学历，微电子、电子工程、集成电路、通信工程等相关专业；\n"
            "2、具有扎实的数字电路理论基础，具备一定Verilog代码编写和综合经验；\n"
            "3、熟悉 ASIC 设计流程及 EDA 工具；\n"
            "4、有学习新的相关技术和工具的热情，有较强的逻辑思维能力，有一定的英语能力。"
        ),
        "notes": "同上，门户空窗。南开转载 JD。header 学历与正文冲突，以任职资格本科为准并标注。",
        "weight": 42,
        "reason": "南京校招设计；门户空窗。",
    },
    {
        "alias": "中茵微",
        "job_title": "高速接口模拟设计工程师（校招）",
        "city": "南京/上海/北京/成都",
        "education_req": "硕士研究生，微电子相关",
        "job_category": "模拟设计",
        "apply_url": "https://joinsilicon.zhiye.com/campus/jobs",
        "source_job_id": "join-serdes-2026",
        "responsibilities": (
            "1、负责接口类PHY IP的模拟电路微架构设计和实现；\n"
            "2、负责接口类PHY IP的模拟电路的开发和交付，达到相应PPA指标；\n"
            "3、参与市场竞争分析、路线图规划及产品定义；\n"
            "4、协助版图团队完成PHY IP的物理实现，时序收敛。"
        ),
        "requirements": "硕士研究生，微电子相关专业。南开就业网转载页。",
        "notes": "门户空窗；硕士。仅凑每家 3 岗库存。",
        "weight": 35,
        "reason": "南京有岗但硕士+空窗。",
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
        blocked = ingest_gate_reasons(
            item["job_title"], item["responsibilities"], item["requirements"]
        )
        if blocked:
            skipped += 1
            print(f"[GATE] {cname} {item['job_title']} | {';'.join(blocked)}")
            continue
        if exists:
            skipped += 1
            print(f"[SKIP JOB] {cname} {item['job_title']}")
            continue
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
                ?, ?, ?, '校园招聘', ?,
                '面议', ?, '', ?,
                ?, ?, ?, '待投递',
                ?, ?, ?,
                ?, ?, ?
            )
            """,
            (
                cid, cname, item["job_title"], item["city"],
                item["education_req"], match,
                item["responsibilities"], item["requirements"], item["apply_url"],
                prio, SOURCE, item["source_job_id"],
                item["weight"], item["reason"], NOW,
            ),
        )
        jobs_added += 1
        print(f"[JOB] {cname} | {item['job_title']} | {item['city']} | w={item['weight']}")
        lead = conn.execute(
            "SELECT id FROM platform_recruitment_leads WHERE dedupe_key=?", (dkey,)
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
                '2027届校招/实习', '2027届', ?, ?,
                '在招', '中', ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?
            )
            """,
            (
                cname, item["job_title"], item["job_category"], item["city"],
                item["apply_url"], item["apply_url"],
                f"2026-09-12 补齐：{item['notes']}", NOW,
                item["notes"], dkey,
                item["responsibilities"], item["requirements"],
                item["education_req"], item["apply_url"], NOW, NOW,
            ),
        )
        leads_added += 1
    conn.commit()
    print("---")
    print(f"jobs_added={jobs_added} leads_added={leads_added} skipped={skipped}")
    print("jobs_total", conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])
    print("\n=== per company pending from these 7 ===")
    aliases = ("纳芯微", "晶丰明源", "南芯", "卓胜微", "乐鑫", "中茵微", "焦点科技")
    for a in aliases:
        rows = conn.execute(
            """
            SELECT j.id, j.job_title, j.city, j.recommendation_weight
            FROM jobs j JOIN companies c ON c.id=j.company_id
            WHERE c.alias=? AND COALESCE(j.status,'')='待投递'
            ORDER BY COALESCE(j.recommendation_weight,0) DESC
            """,
            (a,),
        ).fetchall()
        print(f"{a} n={len(rows)}")
        for r in rows[:6]:
            print(f"  {r[0]} w={r[3]} {r[2]} | {r[1]}")
    conn.close()


if __name__ == "__main__":
    main()
