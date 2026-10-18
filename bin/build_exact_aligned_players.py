#!/usr/bin/env python3
"""重新生成 mock-01 阅读篇章的 1:1 零脑补、顺流镜头意群断句（\\）对齐播放器。
严格遵循 AGENTS.md 军规：
1. 顺流镜头推进（从左到右，绝不倒译）
2. \\ 意群切分（5-8词呼吸感）
3. 1:1 单词卡点（零脑补，不增补原文不存在的成语或文学词）
4. 交互式双语 Chunk 悬停联动（鼠标移到英文块，对应中文块同步高亮）
"""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_DIR = Path("knowledge/cet4-bank/07-整套模拟卷/mock-01/audio")

CLOZE_PAIRS = [
    {
        "chunks": [
            ("When a winter storm cut Maeve Brennan's power,", "当一场冬季暴风雪切断了梅芙·布伦南家的电源时，"),
            ("the first person to check on her", "第一个前去探望她的人"),
            ("was not a paid caregiver", "并不是花钱雇来的护工，"),
            ("but a neighbor", "而是一位邻居，"),
            ("she had met days earlier.", "她几天前刚刚认识的。")
        ],
        "marks": [
            {"p": 59, "l": 8, "t": "detail", "note": "check on: 探望/照看某人"},
            {"p": 82, "l": 32, "t": "signal", "note": "not... but...: 转折对比，破除常规认知"}
        ]
    },
    {
        "chunks": [
            ("The two women had been linked to each other", "这两位女性被联系在了一起，"),
            ("through a local time bank,", "通过当地一家“时间银行”，"),
            ("a scheme matching households needing help", "一个将需要帮助的家庭"),
            ("with those able to give it.", "与能够提供帮助的人进行匹配的项目。")
        ],
        "marks": [
            {"p": 24, "l": 6, "t": "answer", "note": "Q26 答案：linked (be linked to 被动语态连结在一起)"}
        ]
    },
    {
        "chunks": [
            ("Every hour spent helping others", "帮助他人所花费的每个小时，"),
            ("earns a credit", "都能赚取一个时间积分/额度，"),
            ("that can be saved and spent later.", "能够被存起来并在日后消费使用。")
        ],
        "marks": [
            {"p": 40, "l": 6, "t": "answer", "note": "Q27 答案：credit (earns a credit 赚取时间信用额度)"}
        ]
    },
    {
        "chunks": [
            ("Time banks", "时间银行"),
            ("are nothing new.", "并不是什么新鲜事。")
        ],
        "marks": [
            {"p": 11, "l": 11, "t": "signal", "note": "nothing new: 历史常识铺垫"}
        ]
    },
    {
        "chunks": [
            ("The idea originated in Japan in the 1970s,", "这一构想于20世纪70年代起源于日本，"),
            ("when young mothers wanted to share childcare,", "当时年轻母亲们希望分担育儿，"),
            ("and has since spread worldwide.", "自那以后便在全世界传播开来。")
        ],
        "marks": [
            {"p": 9, "l": 10, "t": "answer", "note": "Q28 答案：originated (originated in 起源于...)"}
        ]
    },
    {
        "chunks": [
            ("What is novel about the modern version", "现代版本的新颖之处"),
            ("is its software:", "在于其软件："),
            ("an application now handles the matching and reminders", "一款应用程序如今处理匹配和提醒事项，"),
            ("once left to exhausted volunteers.", "曾经全留给精疲力竭的志愿者们承担。")
        ],
        "marks": [
            {"p": 8, "l": 5, "t": "answer", "note": "Q29 答案：novel (What is novel about... 关键形容词：新颖的/不同寻常的)"}
        ]
    },
    {
        "chunks": [
            ("Such schemes, supporters argue,", "支持者主张，此类方案"),
            ("offer more than practical help.", "所提供的远不止实际的帮助。")
        ],
        "marks": [
            {"p": 40, "l": 9, "t": "signal", "note": "more than: 程度递进"}
        ]
    },
    {
        "chunks": [
            ("Since nobody is paid,", "由于没有人拿取报酬，"),
            ("the exchange feels more like an act of neighborliness", "这种互助感觉更像是一种睦邻行为，"),
            ("than a commercial transaction;", "而非一场商业交易；"),
            ("and since time, not money, is the measure of worth,", "并且由于时间而非金钱是价值的衡量标准，"),
            ("members describe a fresh sense of belonging,", "成员们描述了一种全新的归属感，"),
            ("of being part of a place", "真正成为一个地方的一部分，"),
            ("rather than merely passing through it.", "而非仅仅是这里的过客。")
        ],
        "marks": [
            {"p": 87, "l": 11, "t": "answer", "note": "Q30 答案：transaction (commercial transaction 商业交易)"},
            {"p": 194, "l": 9, "t": "answer", "note": "Q31 答案：belonging (sense of belonging 归属感)"}
        ]
    },
    {
        "chunks": [
            ("Dutch researchers tracking 400 households", "跟踪了400个家庭的荷兰研究人员"),
            ("found participants reported substantially higher levels of trust", "发现参与者报告了明显大幅更高的信任水平，"),
            ("in their neighbors", "对他们的邻居，"),
            ("than non-members did.", "相比非成员而言。")
        ],
        "marks": [
            {"p": 43, "l": 5, "t": "signal", "note": "found: 实证研究动词路标"},
            {"p": 71, "l": 13, "t": "answer", "note": "Q32 答案：substantially (substantially higher levels 显著大幅更高)"}
        ]
    },
    {
        "chunks": [
            ("Not everyone", "并非所有人"),
            ("is convinced.", "都对此信服。")
        ],
        "marks": [
            {"p": 0, "l": 12, "t": "signal", "note": "Not everyone: 转折质疑信号词"}
        ]
    },
    {
        "chunks": [
            ("Critics note", "批评人士指出，"),
            ("that reliable volunteers are still notoriously hard to find,", "可靠的志愿者依然是出名地难找，"),
            ("and that most work falls on a few organizers.", "并且大部分工作落在了少数几个组织者身上。")
        ],
        "marks": [
            {"p": 48, "l": 11, "t": "answer", "note": "Q33 答案：notoriously (notoriously hard 众所周知/恶名昭彰地困难)"}
        ]
    },
    {
        "chunks": [
            ("Fairness is another concern:", "公平性是另一个关切点："),
            ("members in remote areas", "偏远地区的成员"),
            ("may spend so long traveling", "可能在路上花费如此多的时间，"),
            ("that the scheme stops being convenient.", "以至于该方案不再显得便利。")
        ],
        "marks": [
            {"p": 40, "l": 6, "t": "answer", "note": "Q34 答案：remote (remote areas 偏远地区)"}
        ]
    },
    {
        "chunks": [
            ("Even so, Brennan, 78, says her life has changed:", "即便如此，78岁的布伦南说她的生活改变了："),
            ("\"I used to go whole days without speaking to anyone.", "“我过去常常一整天不跟任何人说话。"),
            ("Now I know somebody will notice", "现在我知道有人会察觉到，"),
            ("if I don't appear.\"", "如果我没有露面的话。”")
        ],
        "marks": [
            {"p": 133, "l": 6, "t": "answer", "note": "Q35 答案：notice (somebody will notice 有人会察觉到)"}
        ]
    }
]

P1_PAIRS = [
    {
        "chunks": [
            ("For most of the last century,", "在上个世纪的大部分时间里，"),
            ("rich countries saw migration", "富裕国家把人口迁移视为"),
            ("as a way out of poverty.", "摆脱贫困的一条出路。")
        ],
        "marks": []
    },
    {
        "chunks": [
            ("A poor family moved to a better city,", "一个贫困家庭搬迁到更好的城市，"),
            ("and its young people left poverty behind.", "家里的年轻人便把贫困甩在身后。")
        ],
        "marks": []
    },
    {
        "chunks": [
            ("Recent studies", "最新的多项研究"),
            ("built on income records of tens of millions of families", "建立在数千万家庭的收入记录之上，"),
            ("tell a more complicated story.", "讲述了一个更为复杂的故事。")
        ],
        "marks": [
            {"p": 0, "l": 14, "t": "signal", "note": "Recent studies: 实证研究原生路标"},
            {"p": 67, "l": 32, "t": "signal", "note": "tell a more complicated story: 反转预警"}
        ]
    },
    {
        "chunks": [
            ("Moving does help a poor youngster,", "搬迁确实有助于贫困年轻人，"),
            ("the researchers report,", "研究人员报告说，"),
            ("but far less", "但幅度远小于"),
            ("than people were once told.", "人们曾经被告知的那样。")
        ],
        "marks": [
            {"p": 35, "l": 22, "t": "signal", "note": "the researchers report: 实证动词路标"},
            {"p": 59, "l": 12, "t": "signal", "note": "but far less: 转折与极端限定词（实测考点极高发）"}
        ]
    },
    {
        "chunks": [
            ("The gains depend on where a family settles,", "收益取决于一个家庭定居在何处，"),
            ("and not on the act of leaving itself.", "而非取决于离开这一行为本身。")
        ],
        "marks": [
            {"p": 10, "l": 32, "t": "answer", "note": "Q46 题眼定位：B 项 Its benefits depend mainly on where a family settles"},
            {"p": 48, "l": 28, "t": "trap", "note": "not on the act of leaving: 排除 A/C/D 项"}
        ]
    },
    {
        "chunks": [
            ("One conclusion is uncomfortable to accept:", "有一个结论令人难以接受："),
            ("a good area is not good", "一个好的区域之所以好"),
            ("because of its shops or new houses.", "并非因为那里的商店或新房子。")
        ],
        "marks": [
            {"p": 0, "l": 14, "t": "signal", "note": "One conclusion: 核心定论路标"},
            {"p": 69, "l": 26, "t": "trap", "note": "shops or new houses: 诱杀原词党（Q47 错项 A 诱饵）"}
        ]
    },
    {
        "chunks": [
            ("It is good because of the steady groups that meet there:", "它之所以好是因为在那里定期聚会的稳定群体："),
            ("unions, clubs, two-parent homes,", "工会、俱乐部、双亲家庭、"),
            ("employers who keep the same staff for years.", "以及多年留用同一批员工的雇主。")
        ],
        "marks": [
            {"p": 26, "l": 29, "t": "answer", "note": "Q47 题眼定位：C 项 steady groups there and the expectations of help"}
        ]
    },
    {
        "chunks": [
            ("Where such groups no longer meet,", "在这些群体不再聚会的地方，"),
            ("even a move made for good reasons", "哪怕一次出于良好意图的搬迁"),
            ("repeats the old poverty.", "也会重复旧有的贫困。")
        ],
        "marks": []
    },
    {
        "chunks": [
            ("A family enters a new neighborhood,", "一个家庭进入一个新的街区，"),
            ("but what it really finds", "但它真正发现的"),
            ("is a set of expectations about who gets help.", "是一整套关于谁能得到帮助的社会预期。")
        ],
        "marks": [
            {"p": 67, "l": 32, "t": "answer", "note": "Q47 题眼补充：expectations about who gets help"}
        ]
    },
    {
        "chunks": [
            ("The same studies record", "这批相同的研究记录了"),
            ("what numbers capture poorly:", "数字难以捕捉的东西："),
            ("the cost of leaving.", "离开故土的代价。")
        ],
        "marks": [
            {"p": 57, "l": 15, "t": "signal", "note": "the cost of leaving: 核心主题提炼"}
        ]
    },
    {
        "chunks": [
            ("Experts have interviewed hundreds of migrants now in their fifties,", "专家访谈了数百名现年五十多岁的移民，"),
            ("and most describe a lasting sense", "大多数人描述了一种持久的感觉——"),
            ("of belonging to neither place.", "两个地方都不完全属于。")
        ],
        "marks": [
            {"p": 0, "l": 35, "t": "signal", "note": "interviewed hundreds: 访谈实证"},
            {"p": 89, "l": 38, "t": "answer", "note": "Q48 题眼定位：A 项 feel they belong fully to neither their hometown nor their new city"}
        ]
    },
    {
        "chunks": [
            ("Their hometown", "他们的故乡"),
            ("has changed beyond recognition.", "已经变化得面目全非。")
        ],
        "marks": []
    },
    {
        "chunks": [
            ("The city they chose is where they work,", "他们所选择的城市是他们工作之地，"),
            ("but it is rarely the place", "但极少会是那个地方——"),
            ("they picture as home.", "他们心中描绘为家园的地方。")
        ],
        "marks": []
    },
    {
        "chunks": [
            ("One man put it plainly:", "一位男士直白地说道："),
            ("\"I come from two places", "“我来自两个地方，"),
            ("that no longer exist.\"", "它们都已经不复存在了。”")
        ],
        "marks": []
    },
    {
        "chunks": [
            ("Researchers treat that feeling", "研究人员把那种感受对待为"),
            ("as a measurable loss of social support,", "社会支持网络的一种可衡量的损失，"),
            ("not as weakness.", "而非个人的软弱。")
        ],
        "marks": [
            {"p": 37, "l": 32, "t": "detail", "note": "loss of social support: 社会支持网络的损失"}
        ]
    },
    {
        "chunks": [
            ("Officials often forget", "政府官员们常常遗忘"),
            ("the practical importance of that finding.", "那个发现所具有的现实重要性。")
        ],
        "marks": []
    },
    {
        "chunks": [
            ("If attachment to a hometown is as strong as the evidence shows,", "如果对故乡的依恋真如证据所表明的那样强烈，"),
            ("a plan aimed only at moving people", "仅仅旨在把人搬迁走的规划"),
            ("will keep failing.", "将会持续失败。")
        ],
        "marks": [
            {"p": 65, "l": 44, "t": "signal", "note": "aimed only at moving people will keep failing: 因果预警"}
        ]
    },
    {
        "chunks": [
            ("Improving transport, universities and hospitals in shrinking places", "改善收缩萎缩地区的交通、大学与医院，"),
            ("does not keep people in one place,", "并不会把人们固定在一个地方，"),
            ("as critics warn.", "像批评人士所警告的那样。")
        ],
        "marks": []
    },
    {
        "chunks": [
            ("It widens the range of lives", "它拓宽了生活的可能范围——"),
            ("a person can picture", "一个人能够去设想的生活，"),
            ("without leaving home.", "无需离开家乡。")
        ],
        "marks": [
            {"p": 3, "l": 30, "t": "answer", "note": "Q49 题眼定位：D 项 gives people more ways to build a life without moving"}
        ]
    },
    {
        "chunks": [
            ("When a move does happen,", "当搬迁确实发生之时，"),
            ("support that travels with the young person", "伴随年轻人一同流动的支持，"),
            ("matters more than a grant paid at the start.", "比出发初始发放的补贴更重要。")
        ],
        "marks": [
            {"p": 67, "l": 16, "t": "signal", "note": "matters more than: 比较级核心结论"}
        ]
    },
    {
        "chunks": [
            ("The plain conclusion is", "最朴素的结论是："),
            ("that opportunity is spread unevenly across the country,", "机会在全国范围内的分布是不均衡的，"),
            ("and that belonging is stubborn.", "并且故土归属感是极其顽固深刻的。")
        ],
        "marks": [
            {"p": 0, "l": 23, "t": "signal", "note": "The plain conclusion is that: 全文总结论原生路标"},
            {"p": 29, "l": 76, "t": "answer", "note": "Q50 题眼定位：C 项 Policy has to take both uneven opportunity and lasting attachment seriously"}
        ]
    },
    {
        "chunks": [
            ("A generation told to \"just move\"", "被告知“只要搬走就好”的一代人"),
            ("is learning", "正在懂得："),
            ("that place is harder to shake than a habit.", "故土印记比生活习惯更难摆脱。")
        ],
        "marks": []
    },
    {
        "chunks": [
            ("The towns people leave", "人们所离开的那些城镇，"),
            ("never stop raising their youngsters", "从未停止过养育自家的孩子，"),
            ("from a distance.", "隔着遥远的距离。")
        ],
        "marks": []
    }
]

P2_PAIRS = [
    {
        "chunks": [
            ("Seen from the air,", "从空中看去，"),
            ("a soybean field looks flat and even,", "一片大豆田显得平坦而均匀，"),
            ("but the plants themselves would disagree.", "但植物自身却会有不同意见。")
        ],
        "marks": [
            {"p": 56, "l": 3, "t": "signal", "note": "but: 视角反差转折"}
        ]
    },
    {
        "chunks": [
            ("Within a short distance the soil conditions can change,", "在短短的距离之内土壤状况就可能改变，"),
            ("and one corner may produce half", "并且田地的一角可能只产出"),
            ("of what the middle does.", "田中央所产出的一半。")
        ],
        "marks": [
            {"p": 26, "l": 27, "t": "detail", "note": "soil conditions can change: 土壤局部差异"}
        ]
    },
    {
        "chunks": [
            ("For most of the machinery era,", "在机械化时代的大部分时间里，"),
            ("people who grew crops", "种植庄稼的人们"),
            ("had no cheap way to act on these differences.", "没有廉价的办法来应对这些差异。")
        ],
        "marks": [
            {"p": 49, "l": 16, "t": "signal", "note": "had no cheap way: 传统农耕痛点"}
        ]
    },
    {
        "chunks": [
            ("One treatment covered a wide strip,", "一次作业覆盖很宽的一条，"),
            ("so a choice for the whole area", "因此对整个区域所做的选择"),
            ("became a choice for every part of it.", "就成了对其中每一个部位的选择。")
        ],
        "marks": [
            {"p": 0, "l": 34, "t": "answer", "note": "Q51 题眼定位：机械化粗放作业忽视微观土壤差异"}
        ]
    },
    {
        "chunks": [
            ("Small flying devices have changed that situation:", "小型飞行装置已经改变了那种局面："),
            ("battery-powered drones", "电池驱动的无人机"),
            ("now cross a field every few days.", "如今每隔几天便掠过农田。")
        ],
        "marks": [
            {"p": 0, "l": 49, "t": "signal", "note": "changed that situation: 技术破局标志"}
        ]
    },
    {
        "chunks": [
            ("Their sensors record light from the plants", "它们的传感器记录来自植物的光线，"),
            ("in colors people cannot see.", "以人类所不能看见的颜色。")
        ],
        "marks": [
            {"p": 6, "l": 7, "t": "detail", "note": "sensors: 多光谱传感器检测"}
        ]
    },
    {
        "chunks": [
            ("A plant short of food or water", "一株缺乏养分或水分的植物"),
            ("shows it weeks before", "提前数周表现出这一点，"),
            ("someone walking the rows notices.", "在沿田垄步行的人注意到之前。")
        ],
        "marks": [
            {"p": 40, "l": 12, "t": "detail", "note": "weeks before: 提前数周预警"}
        ]
    },
    {
        "chunks": [
            ("Software turns these readings into a chart,", "软件把这些读数转变成一张图表，"),
            ("which now goes back to vehicles", "这张图表现在返回给作业车辆，"),
            ("that treat single plants", "由它们针对单株植物实施处理，"),
            ("instead of wide strips.", "而不是覆盖大面积宽条带。")
        ],
        "marks": [
            {"p": 86, "l": 35, "t": "answer", "note": "Q52 题眼定位：精准单株变量作业（treat single plants instead of wide strips）"}
        ]
    },
    {
        "chunks": [
            ("The business case is clear,", "商业论据是清楚的，"),
            ("but the results are uneven.", "但实际结果却不均衡。")
        ],
        "marks": [
            {"p": 27, "l": 3, "t": "signal", "note": "but the results are uneven: 转折提示局限性"}
        ]
    },
    {
        "chunks": [
            ("Researchers at agricultural colleges", "农业学院的研究人员"),
            ("treated some fields with drones", "用无人机处理了一部分田地，"),
            ("and others in the traditional way.", "而用传统方式处理了其余的田地。")
        ],
        "marks": [
            {"p": 0, "l": 40, "t": "signal", "note": "Researchers... treated: 对照实验路标"}
        ]
    },
    {
        "chunks": [
            ("Chemical use fell by a third,", "化学品用量下降了三分之一，"),
            ("and output rose", "并且产量上升了，"),
            ("where the seeds were spaced to suit the soil.", "在种子间距被调整以适应土壤的地方。")
        ],
        "marks": [
            {"p": 0, "l": 27, "t": "detail", "note": "Chemical use fell by a third: 农药化肥减量三分之一"}
        ]
    },
    {
        "chunks": [
            ("Money saved on chemicals arrives immediately,", "在化学品上节省的资金立刻到账，"),
            ("but the tools cost real money:", "但这些工具花费真正的金钱："),
            ("drones, software,", "无人机、软件，"),
            ("and a worker who can fix them.", "以及一名能修理它们的工人。")
        ],
        "marks": [
            {"p": 46, "l": 28, "t": "signal", "note": "but the tools cost real money: 成本阻碍"}
        ]
    },
    {
        "chunks": [
            ("The tools spread fastest", "这些工具传播得最快"),
            ("among younger farm families,", "在更年轻的农户家庭之中，"),
            ("who already walk their fields with a phone in hand,", "他们本就手里拿着手机走过田间，"),
            ("not among the biggest farms.", "而不是在规模最大的农场之中。")
        ],
        "marks": [
            {"p": 22, "l": 35, "t": "answer", "note": "Q53 题眼定位：年轻家庭接受度最高"}
        ]
    },
    {
        "chunks": [
            ("The farming questions", "农艺方面的问题"),
            ("are harder.", "则更为艰难。")
        ],
        "marks": []
    },
    {
        "chunks": [
            ("A sensor can show that a plant looks wrong,", "传感器能够显示某株植物看起来不正常，"),
            ("but it cannot always say why.", "但它并非总能说清为什么。")
        ],
        "marks": [
            {"p": 40, "l": 3, "t": "signal", "note": "but it cannot always say why: 技术盲区"}
        ]
    },
    {
        "chunks": [
            ("A lack of food, root disease,", "养分的缺乏、根部的疾病、"),
            ("and soil that holds too much water", "以及蓄水过多的土壤，"),
            ("send nearly the same signal.", "发出几乎完全相同的反射信号。")
        ],
        "marks": [
            {"p": 0, "l": 62, "t": "detail", "note": "send nearly the same signal: 信号同质性难题"}
        ]
    },
    {
        "chunks": [
            ("The most successful farms therefore use a drone as a first-step tool,", "最成功的农场因此把无人机用作第一步初筛工具，"),
            ("narrowing a whole farm", "把整个农场范围缩小"),
            ("to the few parts worth walking through.", "到值得亲自下地察看的少数几个部位。")
        ],
        "marks": [
            {"p": 26, "l": 9, "t": "signal", "note": "therefore: 因果定论路标"},
            {"p": 48, "l": 23, "t": "answer", "note": "Q54 题眼定位：first-step tool 缩小走访范围"}
        ]
    },
    {
        "chunks": [
            ("The device searches, and the person decides;", "机器负责搜索排查，而人来做出决定；"),
            ("this way of working has lasted longer", "这种工作方式维持得更加长久，"),
            ("than the automatic future that companies once described.", "比农机公司当年描述过的全自动未来。")
        ],
        "marks": [
            {"p": 0, "l": 44, "t": "signal", "note": "The device searches, and the person decides: 人机协同核心哲学"}
        ]
    },
    {
        "chunks": [
            ("The environmental account", "生态效益这笔账"),
            ("is still being written.", "目前仍在持续书写之中。")
        ],
        "marks": []
    },
    {
        "chunks": [
            ("Careful application", "仔细的施用"),
            ("sends less chemical", "送入更少的化学品"),
            ("into the streams", "进入溪流之中，"),
            ("and protects the helpful insects", "并保护了有益的昆虫，"),
            ("that older methods destroyed.", "那些更老旧的方法所消灭的。")
        ],
        "marks": []
    },
    {
        "chunks": [
            ("Whether such advantages will continue", "这些环境优势能否持久延续，"),
            ("is another question.", "则是另一个未知问题。")
        ],
        "marks": [
            {"p": 0, "l": 42, "t": "signal", "note": "Whether... is another question: 批判性审视"}
        ]
    },
    {
        "chunks": [
            ("A few firms now own", "少数几家公司如今拥有"),
            ("both the flight data and the seed supply.", "飞行航测数据和种子供应这两者。")
        ],
        "marks": [
            {"p": 0, "l": 60, "t": "answer", "note": "Q55 题眼定位：D 项 A few firms own both flight data and seed supply (数据与种子垄断隐忧)"}
        ]
    },
    {
        "chunks": [
            ("Organizations speaking for farm workers", "为农场工人发声的社会组织"),
            ("now raise this", "如今郑重提出了这一点，"),
            ("at meetings where the devices are otherwise welcome.", "在那些该设备原本受到欢迎的研讨会上。")
        ],
        "marks": []
    }
]

def render_aligned_player(pairs_data, mp3_name, title, subtitle_hint, active_tab, srt_path, html_path):
    # 读现有 SRT 获取精确的时间轴
    cues_times = []
    if srt_path.exists():
        srt_text = srt_path.read_text(encoding="utf-8")
        import re
        blocks = re.findall(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', srt_text)
        for b in blocks:
            def to_sec(ts):
                h, m, s = ts.split(':')
                s, ms = s.split(',')
                return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0
            cues_times.append((to_sec(b[1]), to_sec(b[2])))

    cues = []
    for idx, item in enumerate(pairs_data):
        en_sentence = " ".join(c[0] for c in item["chunks"])
        zh_sentence = " ".join(c[1] for c in item["chunks"])
        en_chunked = " \\ ".join(c[0] for c in item["chunks"])
        zh_chunked = " \\ ".join(c[1] for c in item["chunks"])

        start_t = cues_times[idx][0] if idx < len(cues_times) else idx * 6.0
        end_t = cues_times[idx][1] if idx < len(cues_times) else (idx + 1) * 6.0

        cues.append({
            "start": start_t,
            "end": end_t,
            "en": en_sentence,
            "zh": zh_sentence,
            "en_chunks": [c[0] for c in item["chunks"]],
            "zh_chunks": [c[1] for c in item["chunks"]],
            "en_chunked": en_chunked,
            "zh_chunked": zh_chunked,
            "marks": item.get("marks", [])
        })

    # 更新 SRT
    srt_out = []
    for i, c in enumerate(cues, 1):
        def srt_ts(sec):
            ms = int(round(sec * 1000))
            h, r = divmod(ms, 3600000)
            m, r = divmod(r, 60000)
            s, ms = divmod(r, 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        srt_out.append(f"{i}\n{srt_ts(c['start'])} --> {srt_ts(c['end'])}\n{c['en_chunked']}\n{c['zh_chunked']}\n")
    srt_path.write_text("\n".join(srt_out), encoding="utf-8")

    tabs = [
        ("player.html", "🎧 Part II 听力全套 (13:17)", "listening"),
        ("player-cloze.html", "📖 Section A 选词填空 (时间银行)", "cloze"),
        ("player-passage1.html", "📖 Section C 仔细阅读一 (代际流动)", "passage1"),
        ("player-passage2.html", "📖 Section C 仔细阅读二 (农业无人机)", "passage2"),
    ]
    tabs_html = "\n".join(
        f'<a href="{t[0]}" class="tab-item{" active" if t[2] == active_tab else ""}">{t[1]}</a>'
        for t in tabs
    )

    data_json = json.dumps(cues, ensure_ascii=False).replace("</", "<\\/")

    html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>CET-4 Player — {title}</title>
<style>
body{{margin:0;background:#14161a;color:#dfe3e8;font-family:'Segoe UI','Microsoft YaHei',sans-serif;display:flex;flex-direction:column;height:100vh}}
#nav-tabs{{display:flex;gap:8px;background:#181b22;padding:10px 18px;border-bottom:1px solid #2a2e35;overflow-x:auto;flex-wrap:nowrap}}
.tab-item{{color:#9aa3af;text-decoration:none;font-size:13px;padding:6px 14px;border-radius:6px;transition:all 0.2s;background:#222630;white-space:nowrap;display:inline-flex;align-items:center}}
.tab-item:hover{{color:#fff;background:#2d3340}}
.tab-item.active{{color:#fff;background:#3b82f6;font-weight:600}}
header{{padding:10px 18px;font-weight:600;border-bottom:1px solid #2a2e35;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}}
#legend{{font-size:12px;font-weight:400;color:#9aa3af}}
#legend b{{padding:1px 8px;border-radius:4px;margin:0 2px}}

/* Top Subtitle Area (Active Sentence) */
#sub{{flex:0 0 auto;text-align:left;padding:14px 28px 12px;min-height:120px;background:#1a1d24;border-bottom:1px solid #282c35}}
#sub-cards{{display:flex;flex-wrap:wrap;align-items:stretch;gap:8px 6px}}
.chunk-card{{display:inline-flex;flex-direction:column;justify-content:space-between;background:#212631;border:1px solid #323b4b;border-radius:8px;padding:8px 12px;box-sizing:border-box;transition:all 0.15s ease}}
.chunk-card:hover{{background:#283142;border-color:#60a5fa;box-shadow:0 4px 12px rgba(59,130,246,0.25)}}
.card-en{{font-size:18px;line-height:1.45;color:#ffffff;font-weight:500;letter-spacing:0.2px}}
.card-zh{{font-size:15px;line-height:1.45;color:#ffd479;margin-top:6px;padding-top:6px;border-top:1px dashed rgba(255,212,121,0.25)}}
.slash-col{{display:inline-flex;align-items:center;color:#64748b;font-size:20px;font-weight:bold;user-select:none;padding:0 2px}}
#tip{{font-size:13.5px;margin-top:10px;color:#93c5fd;background:rgba(59,130,246,0.1);border-left:3px solid #3b82f6;padding:6px 12px;border-radius:4px;display:none}}

/* Scrollable List */
#wrap{{flex:1 1 auto;overflow-y:auto;padding:14px 28px 30px}}
p.line{{margin:10px 0;padding:12px 14px;border-radius:8px;cursor:pointer;line-height:1.5;border-left:4px solid transparent;background:#181b22;border:1px solid #232833;transition:all 0.2s ease}}
p.line:hover{{background:#1d222b;border-color:#333d4e;border-left-color:#3b82f6}}
p.line.on{{background:#1e2638;border-color:#3b82f6;border-left-color:#60a5fa;box-shadow:0 4px 14px rgba(0,0,0,0.35)}}
.line-meta{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;font-size:12px;color:#64748b}}
.line-badge{{font-weight:600;color:#94a3b8;background:#232936;padding:2px 8px;border-radius:4px}}
.line-cards{{display:flex;flex-wrap:wrap;align-items:stretch;gap:6px 4px}}
.m-card{{display:inline-flex;flex-direction:column;justify-content:space-between;background:#12151b;border:1px solid #252b37;border-radius:6px;padding:6px 9px;transition:all 0.15s;box-sizing:border-box}}
.line.on .m-card{{background:#17202e;border-color:#2b3952}}
.m-card:hover{{border-color:#60a5fa;background:#1c2638}}
.m-en{{color:#e2e8f0;font-size:14.5px;line-height:1.45;font-weight:500}}
.m-zh{{color:#ffd479;font-size:13.5px;line-height:1.45;margin-top:4px;padding-top:4px;border-top:1px dashed rgba(255,212,121,0.2)}}
.m-slash{{display:inline-flex;align-items:center;color:#475569;font-size:15px;font-weight:bold;user-select:none;padding:0 1px}}
.line-tip{{margin-top:8px;padding:4px 10px;border-radius:4px;background:rgba(59,130,246,0.1);border-left:2px solid #3b82f6;font-size:13px;color:#93c5fd}}

/* Audio Player Transport */
#transport{{flex:0 0 auto;display:flex;align-items:center;gap:14px;padding:10px 18px 18px;background:#161920;border-top:1px solid #232730}}
#play{{flex:0 0 auto;width:46px;height:46px;border-radius:50%;border:none;background:#3b82f6;color:#fff;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center}}
#play:hover{{background:#2563eb}}
#bar{{flex:1 1 auto;height:26px;display:flex;align-items:center;cursor:pointer;touch-action:none}}
#track{{width:100%;height:10px;border-radius:5px;background:#2a2e35;position:relative}}
#fill{{height:100%;border-radius:5px;background:#3b82f6;width:0}}
#knob{{position:absolute;top:50%;width:18px;height:18px;border-radius:50%;background:#fff;transform:translate(-50%,-50%);left:0;box-shadow:0 1px 4px #0008}}
#time{{flex:0 0 auto;font-variant-numeric:tabular-nums;color:#9aa3af}}
audio{{display:none}}
</style></head><body>
<nav id="nav-tabs">
{tabs_html}
</nav>
<header><span id="title">{title}</span><span id="legend">重点标注：<b style="background:#63d68a">答案定位/题眼</b><b style="background:#ff9d5c">原生路标(转折/因果/实证)</b><b style="background:#7fc4ff">核心搭配/细节</b><b style="background:#d9a2ff">陷阱辨析</b>（1:1 顺流意群卡点对齐）</span></header>
<div id="sub">
 <div id="sub-cards"></div>
 <div id="tip"></div>
</div>
<div id="wrap"></div>
<div id="transport">
 <button id="play">▶</button>
 <div id="bar"><div id="track"><div id="fill"></div><div id="knob"></div></div></div>
 <span id="time">0:00 / -:-</span>
</div>
<audio id="a" src="{mp3_name}" preload="metadata"></audio>
<script>
const CUES={data_json};
const a=document.getElementById('a'),wrap=document.getElementById('wrap');
const fmt=s=>Math.floor(s/60)+':'+String(Math.floor(s%60)).padStart(2,'0');

CUES.forEach((c, idx)=>{{
 const p=document.createElement('p');p.className='line';
 
 const meta=document.createElement('div');meta.className='line-meta';
 const badge=document.createElement('span');badge.className='line-badge';
 badge.textContent='句 ' + (idx+1);
 const tSpan=document.createElement('span');tSpan.textContent=fmt(c.start);
 meta.appendChild(badge);meta.appendChild(tSpan);
 p.appendChild(meta);

 const cardsBox=document.createElement('div');cardsBox.className='line-cards';
 (c.en_chunks||[]).forEach((enText, ci)=>{{
   const mCard=document.createElement('div');mCard.className='m-card';
   const mEn=document.createElement('div');mEn.className='m-en';mEn.textContent=enText;
   const mZh=document.createElement('div');mZh.className='m-zh';mZh.textContent=(c.zh_chunks||[])[ci]||'';
   mCard.appendChild(mEn);mCard.appendChild(mZh);
   cardsBox.appendChild(mCard);
   if(ci < c.en_chunks.length - 1){{
     const slash=document.createElement('span');slash.className='m-slash';slash.textContent=String.fromCharCode(92);
     cardsBox.appendChild(slash);
   }}
 }});
 p.appendChild(cardsBox);

 const notes=(c.marks||[]).filter(m=>m.note).map(m=>m.note);
 if(notes.length){{
   const noteDiv=document.createElement('div');noteDiv.className='line-tip';
   noteDiv.textContent='🎯 ' + notes.join(' | ');
   p.appendChild(noteDiv);
 }}

 p.onclick=()=>{{a.currentTime=c.start+.02;if(a.paused)a.play();}};
 wrap.appendChild(p);c.el=p;
}});

let cur=-1;
function paint(i){{
 const sc=document.getElementById('sub-cards'),tip=document.getElementById('tip');
 sc.innerHTML='';tip.textContent='';tip.style.display='none';
 if(i<0)return;const c=CUES[i];
 (c.en_chunks||[]).forEach((enText, ci)=>{{
   const card=document.createElement('div');card.className='chunk-card';
   const enDiv=document.createElement('div');enDiv.className='card-en';enDiv.textContent=enText;
   const zhDiv=document.createElement('div');zhDiv.className='card-zh';zhDiv.textContent=(c.zh_chunks||[])[ci]||'';
   card.appendChild(enDiv);card.appendChild(zhDiv);
   sc.appendChild(card);
   if(ci < c.en_chunks.length - 1){{
     const slash=document.createElement('span');slash.className='slash-col';slash.textContent=String.fromCharCode(92);
     sc.appendChild(slash);
   }}
 }});
 const notes=(c.marks||[]).filter(m=>m.note).map(m=>m.note);
 if(notes.length){{
   tip.textContent='🎯 '+notes.join(' | ');
   tip.style.display='block';
 }}
}}

a.addEventListener('timeupdate',()=>{{const t=a.currentTime;
 let i=CUES.findIndex(c=>t>=c.start&&t<c.end);
 if(i!==cur){{if(cur>=0)CUES[cur].el.classList.remove('on');
  if(i>=0){{CUES[i].el.classList.add('on');CUES[i].el.scrollIntoView({{block:'center',behavior:'smooth'}});}}
  paint(i);cur=i;}}
 const d=a.duration||1;const r=Math.min(t/d,1);
 document.getElementById('fill').style.width=(r*100)+'%';
 document.getElementById('knob').style.left=(r*100)+'%';
 document.getElementById('time').textContent=fmt(t)+' / '+fmt(a.duration||0);}});

const play=document.getElementById('play');
play.onclick=()=>{{a.paused?a.play():a.pause();}};
a.onplay=()=>play.textContent='⏸';a.onpause=()=>play.textContent='▶';
const bar=document.getElementById('bar');
function seekEv(e){{const r=bar.getBoundingClientRect();
 a.currentTime=Math.min(Math.max((e.clientX-r.left)/r.width,0),1)*(a.duration||0);}}
bar.addEventListener('pointerdown',e=>{{bar.setPointerCapture(e.pointerId);seekEv(e);bar._d=true;}});
bar.addEventListener('pointermove',e=>{{if(bar._d)seekEv(e);}});
bar.addEventListener('pointerup',()=>bar._d=false);
</script></body></html>"""
    html_path.write_text(html, encoding="utf-8")
    print(f"  [OK] {html_path.name} 重新构建完成（1:1 顺流意群卡点版）")

def main():
    print("🚀 开始重新生成 1:1 零脑补、顺流镜头意群对齐播放器...")
    
    # 1. 选词填空
    render_aligned_player(
        CLOZE_PAIRS, "mock-01-reading-cloze.mp3",
        "mock-01 Section A — 选词填空 (时间银行)",
        "纯美音朗读与考点词性解构", "cloze",
        OUT_DIR / "mock-01-reading-cloze.srt",
        OUT_DIR / "player-cloze.html"
    )

    # 2. 仔细阅读一
    render_aligned_player(
        P1_PAIRS, "mock-01-reading-passage1.mp3",
        "mock-01 Section C Passage 1 — 代际流动与故乡依恋",
        "纯美音叙事朗读与四大原生路标", "passage1",
        OUT_DIR / "mock-01-reading-passage1.srt",
        OUT_DIR / "player-passage1.html"
    )

    # 3. 仔细阅读二
    render_aligned_player(
        P2_PAIRS, "mock-01-reading-passage2.mp3",
        "mock-01 Section C Passage 2 — 农业无人机与精准种植",
        "纯美音科技说明与题眼定位", "passage2",
        OUT_DIR / "mock-01-reading-passage2.srt",
        OUT_DIR / "player-passage2.html"
    )

    print("🎉 3 套阅读播放器 1:1 顺流意群联动全面落盘！")

if __name__ == "__main__":
    main()
