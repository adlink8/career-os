#!/usr/bin/env python3
"""为 CET-4 mock-01 的阅读篇章合成句子级对齐音频与交互式播放器。
产出：
1. audio/mock-01-reading-cloze.mp3 + srt + player-cloze.html
2. audio/mock-01-reading-passage1.mp3 + srt + player-passage1.html
3. audio/mock-01-reading-passage2.mp3 + srt + player-passage2.html
4. 更新 audio/player.html 加入顶部 4 板块无缝导航栏
"""
import asyncio, json, re, subprocess, sys, tempfile
from pathlib import Path
import edge_tts, imageio_ffmpeg, numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SR = 24000
VOICE_CLOZE = "en-US-ChristopherNeural"
VOICE_P1 = "en-US-AriaNeural"
VOICE_P2 = "en-US-GuyNeural"

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

CLOZE_DATA = [
    {
        "en": "When a winter storm cut Maeve Brennan's power, the first person to check on her was not a paid caregiver but a neighbor she had met days earlier.",
        "zh": "当一场冬季暴风雪切断了梅芙·布伦南家的电源时，第一个前去探望她的人并不是花钱雇来的护工，而是几天前她刚刚认识的一位邻居。",
        "marks": [
            {"p": 59, "l": 8, "t": "detail", "note": "check on: 探望/照看某人"},
            {"p": 82, "l": 32, "t": "signal", "note": "not... but...: 转折对比，破除常规认知"}
        ]
    },
    {
        "en": "The two women had been linked to each other through a local time bank, a scheme matching households needing help with those able to give it.",
        "zh": "两位女性通过当地一家“时间银行”被联系在了一起，这是一个将需要帮助的家庭与能够提供帮助的人进行匹配的项目。",
        "marks": [
            {"p": 24, "l": 6, "t": "answer", "note": "Q26 答案：linked (be linked to 被动语态连结在一起)"}
        ]
    },
    {
        "en": "Every hour spent helping others earns a credit that can be saved and spent later.",
        "zh": "帮助他人所花费的每个小时，都能赚取一个时间积分/信用额度，这个积分可以存起来并在日后消费使用。",
        "marks": [
            {"p": 40, "l": 6, "t": "answer", "note": "Q27 答案：credit (earns a credit 赚取时间信用额度)"}
        ]
    },
    {
        "en": "Time banks are nothing new.",
        "zh": "时间银行并不是什么新鲜事。",
        "marks": [
            {"p": 11, "l": 11, "t": "signal", "note": "nothing new: 历史常识铺垫"}
        ]
    },
    {
        "en": "The idea originated in Japan in the 1970s, when young mothers wanted to share childcare, and has since spread worldwide.",
        "zh": "这一构想于20世纪70年代起源于日本，当时年轻的母亲们希望分担照看孩子的责任，自那以后便在全世界传播开来。",
        "marks": [
            {"p": 9, "l": 10, "t": "answer", "note": "Q28 答案：originated (originated in 起源于...)"}
        ]
    },
    {
        "en": "What is novel about the modern version is its software: an application now handles the matching and reminders once left to exhausted volunteers.",
        "zh": "现代版本的新颖之处在于其软件：现在由一款应用程序来处理匹配和提醒事项，而这些曾经是全由精疲力竭的志愿者们承担的。",
        "marks": [
            {"p": 8, "l": 5, "t": "answer", "note": "Q29 答案：novel (What is novel about... 关键形容词：新颖的/不同寻常的)"}
        ]
    },
    {
        "en": "Such schemes, supporters argue, offer more than practical help.",
        "zh": "支持者认为，这类方案所提供的远不止实际的帮助。",
        "marks": [
            {"p": 40, "l": 9, "t": "signal", "note": "more than: 程度递进"}
        ]
    },
    {
        "en": "Since nobody is paid, the exchange feels more like an act of neighborliness than a commercial transaction; and since time, not money, is the measure of worth, members describe a fresh sense of belonging, of being part of a place rather than merely passing through it.",
        "zh": "由于没有人拿报酬，这种互助感觉更像是一种睦邻行为而非商业交易；而由于衡量价值的是时间而非金钱，成员们描述了一种全新的归属感——真正成为一个地方的一部分，而不仅仅是这里的过客。",
        "marks": [
            {"p": 87, "l": 11, "t": "answer", "note": "Q30 答案：transaction (commercial transaction 商业交易)"},
            {"p": 194, "l": 9, "t": "answer", "note": "Q31 答案：belonging (sense of belonging 归属感)"}
        ]
    },
    {
        "en": "Dutch researchers tracking 400 households found participants reported substantially higher levels of trust in their neighbors than non-members did.",
        "zh": "跟踪了400个家庭的荷兰研究人员发现，参与者报告的对邻居的信任度，明显大幅高于非成员。",
        "marks": [
            {"p": 43, "l": 5, "t": "signal", "note": "found: 实证研究动词路标"},
            {"p": 71, "l": 13, "t": "answer", "note": "Q32 答案：substantially (substantially higher levels 显著大幅更高)"}
        ]
    },
    {
        "en": "Not everyone is convinced.",
        "zh": "并非所有人都信服。",
        "marks": [
            {"p": 0, "l": 12, "t": "signal", "note": "Not everyone: 转折质疑信号词"}
        ]
    },
    {
        "en": "Critics note that reliable volunteers are still notoriously hard to find, and that most work falls on a few organizers.",
        "zh": "批评人士指出，可靠的志愿者仍然是出了名地难找，大部分工作依然落在了少数几个组织者身上。",
        "marks": [
            {"p": 48, "l": 11, "t": "answer", "note": "Q33 答案：notoriously (notoriously hard 众所周知/恶名昭彰地困难)"}
        ]
    },
    {
        "en": "Fairness is another concern: members in remote areas may spend so long traveling that the scheme stops being convenient.",
        "zh": "公平性是另一个令人担忧的问题：偏远地区的成员可能花在路上的时间太长，以至于该方案不再显得便利。",
        "marks": [
            {"p": 40, "l": 6, "t": "answer", "note": "Q34 答案：remote (remote areas 偏远地区)"}
        ]
    },
    {
        "en": "Even so, Brennan, 78, says her life has changed: 'I used to go whole days without speaking to anyone. Now I know somebody will notice if I don't appear.'",
        "zh": "即便如此，78岁的布伦南说她的生活已经改变：'我过去常常一整天都不跟任何人说一句话。现在我知道，如果我没露面，一定会有人察觉到。'",
        "marks": [
            {"p": 133, "l": 6, "t": "answer", "note": "Q35 答案：notice (somebody will notice 有人会察觉到)"}
        ]
    }
]

P1_DATA = [
    {
        "en": "For most of the last century, rich countries saw migration as a way out of poverty.",
        "zh": "在上个世纪的大部分时间里，富裕国家把人口迁移视为摆脱贫困的一条出路。",
        "marks": []
    },
    {
        "en": "A poor family moved to a better city, and its young people left poverty behind.",
        "zh": "一个贫困家庭搬迁到更好的城市，家里的年轻人就此告别了贫穷。",
        "marks": []
    },
    {
        "en": "Recent studies built on income records of tens of millions of families tell a more complicated story.",
        "zh": "而建立在数千万家庭收入记录之上的最新研究，却讲述了一个更为复杂的故事。",
        "marks": [
            {"p": 0, "l": 14, "t": "signal", "note": "Recent studies: 实证研究原生路标"},
            {"p": 67, "l": 32, "t": "signal", "note": "tell a more complicated story: 反转预警"}
        ]
    },
    {
        "en": "Moving does help a poor youngster, the researchers report, but far less than people were once told.",
        "zh": "研究人员报告称，搬迁确实能帮助贫困青年，但帮助的幅度远小于人们曾被告知的那样。",
        "marks": [
            {"p": 35, "l": 22, "t": "signal", "note": "the researchers report: 实证动词路标"},
            {"p": 59, "l": 12, "t": "signal", "note": "but far less: 转折与极端限定词（实测考点极高发）"}
        ]
    },
    {
        "en": "The gains depend on where a family settles, and not on the act of leaving itself.",
        "zh": "收益的多少主要取决于一个家庭落脚定居在何处，而不在于'离开'这一行为本身。",
        "marks": [
            {"p": 10, "l": 32, "t": "answer", "note": "Q46 题眼定位：B 项 Its benefits depend mainly on where a family settles"},
            {"p": 48, "l": 28, "t": "trap", "note": "not on the act of leaving: 排除 A/C/D 项"}
        ]
    },
    {
        "en": "One conclusion is uncomfortable to accept: a good area is not good because of its shops or new houses.",
        "zh": "有一个结论令人难以接受：一个地方好，并不是因为它有商店或新房子。",
        "marks": [
            {"p": 0, "l": 14, "t": "signal", "note": "One conclusion: 核心定论路标"},
            {"p": 69, "l": 26, "t": "trap", "note": "shops or new houses: 诱杀原词党（Q47 错项 A 诱饵）"}
        ]
    },
    {
        "en": "It is good because of the steady groups that meet there: unions, clubs, two-parent homes, employers who keep the same staff for years.",
        "zh": "它之所以好，是因为那里有定期聚拢的稳定群体：工会、俱乐部、双亲家庭，以及多年留用同一批员工的雇主。",
        "marks": [
            {"p": 26, "l": 29, "t": "answer", "note": "Q47 题眼定位：C 项 steady groups there and the expectations of help"}
        ]
    },
    {
        "en": "Where such groups no longer meet, even a move made for good reasons repeats the old poverty.",
        "zh": "在这些群体不再聚拢的地方，哪怕是一次出于良好意图的搬迁，也会重复旧有的贫困。",
        "marks": []
    },
    {
        "en": "A family enters a new neighborhood, but what it really finds is a set of expectations about who gets help.",
        "zh": "一个家庭进入一个新的社区，但它真正遇到的，是一整套关于'谁会得到帮助'的社会预期。",
        "marks": [
            {"p": 67, "l": 32, "t": "answer", "note": "Q47 题眼补充：expectations about who gets help"}
        ]
    },
    {
        "en": "The same studies record what numbers capture poorly: the cost of leaving.",
        "zh": "同一批研究还记录了冷冰冰的数字难以捕捉的东西：离开故土的隐形代价。",
        "marks": [
            {"p": 57, "l": 15, "t": "signal", "note": "the cost of leaving: 核心主题提炼"}
        ]
    },
    {
        "en": "Experts have interviewed hundreds of migrants now in their fifties, and most describe a lasting sense of belonging to neither place.",
        "zh": "专家访谈了数百位如今年过五旬的移民，大多数人描述了一种'两个地方都不完全属于'的持久疏离感。",
        "marks": [
            {"p": 0, "l": 35, "t": "signal", "note": "interviewed hundreds: 访谈实证"},
            {"p": 89, "l": 38, "t": "answer", "note": "Q48 题眼定位：A 项 feel they belong fully to neither their hometown nor their new city"}
        ]
    },
    {
        "en": "Their hometown has changed beyond recognition.",
        "zh": "他们的故乡已经发生巨变、面目全非。",
        "marks": []
    },
    {
        "en": "The city they chose is where they work, but it is rarely the place they picture as home.",
        "zh": "他们选中的城市是他们工作谋生之地，却很少是他们心中勾勒出的那个'家'。",
        "marks": []
    },
    {
        "en": "One man put it plainly: 'I come from two places that no longer exist.'",
        "zh": "一位受访男士直白地感慨：'我来自两个都已经不复存在的地方。'",
        "marks": []
    },
    {
        "en": "Researchers treat that feeling as a measurable loss of social support, not as weakness.",
        "zh": "研究人员把这种感受视为社会支持网络的一种可衡量的实质损失，而不是个人的软弱。",
        "marks": [
            {"p": 37, "l": 32, "t": "detail", "note": "loss of social support: 社会支持网络的损失"}
        ]
    },
    {
        "en": "Officials often forget the practical importance of that finding.",
        "zh": "政府决策者们往往忽视了这一发现所具有的现实重要性。",
        "marks": []
    },
    {
        "en": "If attachment to a hometown is as strong as the evidence shows, a plan aimed only at moving people will keep failing.",
        "zh": "如果人们对故乡的依恋真如实证所表明的那样强烈，那么仅仅旨在'把人搬迁走'的规划就会持续失败。",
        "marks": [
            {"p": 65, "l": 44, "t": "signal", "note": "aimed only at moving people will keep failing: 因果预警"}
        ]
    },
    {
        "en": "Improving transport, universities and hospitals in shrinking places does not keep people in one place, as critics warn.",
        "zh": "改善收缩衰退地区的交通、大学与医院，并不会如批评者警告的那样把人死死困在原地。",
        "marks": []
    },
    {
        "en": "It widens the range of lives a person can picture without leaving home.",
        "zh": "相反，它拓宽了一个人不必背井离乡也能设想的人生可能性范围。",
        "marks": [
            {"p": 3, "l": 30, "t": "answer", "note": "Q49 题眼定位：D 项 gives people more ways to build a life without moving"}
        ]
    },
    {
        "en": "When a move does happen, support that travels with the young person matters more than a grant paid at the start.",
        "zh": "而当搬迁确实不可避免地发生时，能够伴随年轻人一同流动的长效支持，远比出发时一次性发放的那笔补贴更重要。",
        "marks": [
            {"p": 67, "l": 16, "t": "signal", "note": "matters more than: 比较级核心结论"}
        ]
    },
    {
        "en": "The plain conclusion is that opportunity is spread unevenly across the country, and that belonging is stubborn.",
        "zh": "最朴素的结论在于：发展机会在全国范围内分布并不均衡，而故土归属感异常顽固深刻。",
        "marks": [
            {"p": 0, "l": 23, "t": "signal", "note": "The plain conclusion is that: 全文总结论原生路标"},
            {"p": 29, "l": 76, "t": "answer", "note": "Q50 题眼定位：C 项 Policy has to take both uneven opportunity and lasting attachment seriously"}
        ]
    },
    {
        "en": "A generation told to 'just move' is learning that place is harder to shake than a habit.",
        "zh": "曾被教导'只要搬走就能改变命运'的一代人如今正在明白：故土印记比生活习惯更难磨灭。",
        "marks": []
    },
    {
        "en": "The towns people leave never stop raising their youngsters from a distance.",
        "zh": "人们所离开的那些故乡小镇，从未停止过隔着遥远的距离继续养育自家的孩子。",
        "marks": []
    }
]

P2_DATA = [
    {
        "en": "Seen from the air, a soybean field looks flat and even, but the plants themselves would disagree.",
        "zh": "从空中看去，一片大豆田平坦而均匀，可植株自己不会同意。",
        "marks": [
            {"p": 56, "l": 3, "t": "signal", "note": "but: 视角反差转折"}
        ]
    },
    {
        "en": "Within a short distance the soil conditions can change, and one corner may produce half of what the middle does.",
        "zh": "在短短的距离之内，土壤状况就可能发生变化，田地的一角可能只产出田中央一半的收成。",
        "marks": [
            {"p": 26, "l": 27, "t": "detail", "note": "soil conditions can change: 土壤局部差异"}
        ]
    },
    {
        "en": "For most of the machinery era, people who grew crops had no cheap way to act on these differences.",
        "zh": "在机械化时代的大部分时间里，种庄稼的农户没有低成本的办法来应对这些细微差异。",
        "marks": [
            {"p": 49, "l": 16, "t": "signal", "note": "had no cheap way: 传统农耕痛点"}
        ]
    },
    {
        "en": "One treatment covered a wide strip, so a choice for the whole area became a choice for every part of it.",
        "zh": "一次作业覆盖一条很宽的作业带，因此为整片田地做的单一决定，就成了这片田里每一小块的硬性决定。",
        "marks": [
            {"p": 0, "l": 34, "t": "answer", "note": "Q51 题眼定位：机械化粗放作业忽视微观土壤差异"}
        ]
    },
    {
        "en": "Small flying devices have changed that situation: battery-powered drones now cross a field every few days.",
        "zh": "小型飞行装置改变了这种局面：电池驱动的无人机如今每隔几天就掠过田间巡视。",
        "marks": [
            {"p": 0, "l": 49, "t": "signal", "note": "changed that situation: 技术破局标志"}
        ]
    },
    {
        "en": "Their sensors record light from the plants in colors people cannot see.",
        "zh": "它们的传感器记录来自植物的光，那些光的颜色在人眼所能看见的范围之外。",
        "marks": [
            {"p": 6, "l": 7, "t": "detail", "note": "sensors: 多光谱传感器检测"}
        ]
    },
    {
        "en": "A plant short of food or water shows it weeks before someone walking the rows notices.",
        "zh": "缺肥或缺水的植株，在沿田埂行走的人察觉之前几周就已露出明显迹象。",
        "marks": [
            {"p": 40, "l": 12, "t": "detail", "note": "weeks before: 提前数周预警"}
        ]
    },
    {
        "en": "Software turns these readings into a chart, which now goes back to vehicles that treat single plants instead of wide strips.",
        "zh": "软件把这些读数转换成图表，再反馈给作业车辆，由车辆针对单株植物实施精准作业，而非粗放地大面积撒播。",
        "marks": [
            {"p": 86, "l": 35, "t": "answer", "note": "Q52 题眼定位：精准单株变量作业（treat single plants instead of wide strips）"}
        ]
    },
    {
        "en": "The business case is clear, but the results are uneven.",
        "zh": "商业论证是清晰的，但落地效果却参差不齐。",
        "marks": [
            {"p": 27, "l": 3, "t": "signal", "note": "but the results are uneven: 转折提示局限性"}
        ]
    },
    {
        "en": "Researchers at agricultural colleges treated some fields with drones and others in the traditional way.",
        "zh": "农业院校的研究人员用无人机处理一些田块，其余田块仍采用传统作业方式对照。",
        "marks": [
            {"p": 0, "l": 40, "t": "signal", "note": "Researchers... treated: 对照实验路标"}
        ]
    },
    {
        "en": "Chemical use fell by a third, and output rose where the seeds were spaced to suit the soil.",
        "zh": "化学品用量下降了三分之一；在播种间距与土壤相匹配的地方，产量也上升了。",
        "marks": [
            {"p": 0, "l": 27, "t": "detail", "note": "Chemical use fell by a third: 农药化肥减量三分之一"}
        ]
    },
    {
        "en": "Money saved on chemicals arrives immediately, but the tools cost real money: drones, software, and a worker who can fix them.",
        "zh": "省下的化学品开支立竿见影，但购置维护这些工具依然要真金白银：无人机、软件，外加一位能修好它们的专业技工。",
        "marks": [
            {"p": 46, "l": 28, "t": "signal", "note": "but the tools cost real money: 成本阻碍"}
        ]
    },
    {
        "en": "The tools spread fastest among younger farm families, who already walk their fields with a phone in hand, not among the biggest farms.",
        "zh": "这些工具传播最快的是那些下地时手里就拿着手机的年轻农户家庭，而不是规模最大的那些农场。",
        "marks": [
            {"p": 22, "l": 35, "t": "answer", "note": "Q53 题眼定位：年轻家庭接受度最高"}
        ]
    },
    {
        "en": "The farming questions are harder.",
        "zh": "农艺上的实质问题则更为棘手。",
        "marks": []
    },
    {
        "en": "A sensor can show that a plant looks wrong, but it cannot always say why.",
        "zh": "传感器能够显示某株植物'看起来异常'，却未必能解释其根本原因。",
        "marks": [
            {"p": 40, "l": 3, "t": "signal", "note": "but it cannot always say why: 技术盲区"}
        ]
    },
    {
        "en": "A lack of food, root disease, and soil that holds too much water send nearly the same signal.",
        "zh": "缺肥、根部病害，以及积水过多的土壤，发出的光谱反射信号几乎一模一样。",
        "marks": [
            {"p": 0, "l": 62, "t": "detail", "note": "send nearly the same signal: 信号同质性难题"}
        ]
    },
    {
        "en": "The most successful farms therefore use a drone as a first-step tool, narrowing a whole farm to the few parts worth walking through.",
        "zh": "因此，最成功的农场把无人机当作'第一步初筛工具'，把整片农场缩小为少数几处值得亲自下地察看的地方。",
        "marks": [
            {"p": 26, "l": 9, "t": "signal", "note": "therefore: 因果定论路标"},
            {"p": 48, "l": 23, "t": "answer", "note": "Q54 题眼定位：first-step tool 缩小走访范围"}
        ]
    },
    {
        "en": "The device searches, and the person decides; this way of working has lasted longer than the automatic future that companies once described.",
        "zh": "机器负责搜索排查，人类负责定夺决策；这种协同工作模式，比农机公司当年描绘的'全自动未来'更有长久生命力。",
        "marks": [
            {"p": 0, "l": 44, "t": "signal", "note": "The device searches, and the person decides: 人机协同核心哲学"}
        ]
    },
    {
        "en": "The environmental account is still being written.",
        "zh": "生态效益这笔账目前仍在持续评估书写之中。",
        "marks": []
    },
    {
        "en": "Careful application sends less chemical into the streams and protects the helpful insects that older methods destroyed.",
        "zh": "精确施药让更少的化学残留流入溪沟，也保护了那些曾被老旧方式误杀的农田有益昆虫。",
        "marks": []
    },
    {
        "en": "Whether such advantages will continue is another question.",
        "zh": "这些环境优势能否持久延续下去，则是另一个未知数。",
        "marks": [
            {"p": 0, "l": 42, "t": "signal", "note": "Whether... is another question: 批判性审视"}
        ]
    },
    {
        "en": "A few firms now own both the flight data and the seed supply.",
        "zh": "如今少数几家巨头公司同时掌握了无人机飞行航测数据与农田种子供应。",
        "marks": [
            {"p": 0, "l": 60, "t": "answer", "note": "Q55 题眼定位：D 项 A few firms own both flight data and seed supply (数据与种子垄断隐忧)"}
        ]
    },
    {
        "en": "Organizations speaking for farm workers now raise this at meetings where the devices are otherwise welcome.",
        "zh": "为农户发声的社会组织，正是在那些对无人机普遍表示欢迎的研讨会上，郑重指出了这一隐患。",
        "marks": []
    }
]

def mp3_to_pcm(path, ffmpeg_bin):
    wav = subprocess.run(
        [ffmpeg_bin, "-v", "error", "-i", str(path), "-f", "f32le", "-acodec", "pcm_f32le",
         "-ac", "1", "-ar", str(SR), "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(wav, dtype=np.float32)

def pcm_to_mp3(pcm_data, out_path, ffmpeg_bin):
    proc = subprocess.Popen(
        [ffmpeg_bin, "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
         "-codec:a", "libmp3lame", "-b:a", "96k", str(out_path)],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    proc.communicate(input=pcm_data.tobytes())
    assert proc.returncode == 0, "ffmpeg 转 MP3 失败"

def srt_ts(sec):
    ms = int(round(sec * 1000))
    h, r = divmod(ms, 3600000)
    m, r = divmod(r, 60000)
    s, ms = divmod(r, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def write_srt(cues, path):
    out = []
    for i, c in enumerate(cues, 1):
        text = "\n".join(x for x in (c["en"], c["zh"]) if x)
        out.append(f"{i}\n{srt_ts(c['start'])} --> {srt_ts(c['end'])}\n{text}\n")
    path.write_text("\n".join(out), encoding="utf-8")

def render_player(cues, mp3_name, title, subtitle_hint, active_tab, path):
    data = json.dumps(cues, ensure_ascii=False).replace("</", "<\\/")
    
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
#sub{{flex:0 0 auto;text-align:center;padding:14px 30px 6px;min-height:118px}}
#en{{font-size:22px;line-height:1.5;color:#fff}}
#zh{{font-size:18px;line-height:1.4;color:#ffd479;margin-top:5px}}
#tip{{font-size:14px;margin-top:6px;color:#7fc4ff}}
#wrap{{flex:1 1 auto;overflow-y:auto;padding:10px 30px 30px}}
p.line{{margin:6px 0;padding:8px 12px;border-radius:6px;cursor:pointer;line-height:1.6;border-left:3px solid transparent}}
p.line:hover{{background:#1f242c;border-left-color:#3b82f6}}
p.line.on{{background:#2b3548;border-left-color:#60a5fa}}
.zh{{color:#8b93a0;font-size:14px;display:block;margin-top:3px}}
.en{{color:#e8c07d;font-size:15px}}
mark{{color:#10131a;border-radius:3px;padding:1px 4px;font-weight:600}}
.k-answer{{background:#63d68a}} .k-signal{{background:#ff9d5c}}
.k-detail{{background:#7fc4ff}} .k-trap{{background:#d9a2ff;text-decoration:underline wavy #b3541e}}
#transport{{flex:0 0 auto;display:flex;align-items:center;gap:14px;padding:10px 18px 18px}}
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
<header><span id="title">{title}</span><span id="legend">重点标注：<b style="background:#63d68a">答案定位/题眼</b><b style="background:#ff9d5c">原生路标(转折/因果/实证)</b><b style="background:#7fc4ff">核心搭配/细节</b><b style="background:#d9a2ff">陷阱辨析</b>（悬停/点击看考点）</span></header>
<div id="sub"><div id="en"></div><div id="zh"></div><div id="tip"></div></div>
<div id="wrap"></div>
<div id="transport">
 <button id="play">▶</button>
 <div id="bar"><div id="track"><div id="fill"></div><div id="knob"></div></div></div>
 <span id="time">0:00 / -:-</span>
</div>
<audio id="a" src="{mp3_name}" preload="metadata"></audio>
<script>
const CUES={data};
const a=document.getElementById('a'),wrap=document.getElementById('wrap');
const fmt=s=>Math.floor(s/60)+':'+String(Math.floor(s%60)).padStart(2,'0');
function enFrag(c){{
 const f=document.createDocumentFragment();let pos=0;
 (c.marks||[]).forEach(m=>{{
  if(m.p>pos)f.append(document.createTextNode(c.en.slice(pos,m.p)));
  const k=document.createElement('mark');k.className='k-'+m.t;
  k.textContent=c.en.substr(m.p,m.l);if(m.note)k.title=m.note;f.append(k);pos=m.p+m.l;}});
 f.append(document.createTextNode(c.en.slice(pos)));return f;}}
CUES.forEach((c,idx)=>{{
 const p=document.createElement('p');p.className='line';
 const e=document.createElement('span');e.className='en';e.append(document.createTextNode((idx+1)+'. '));e.append(enFrag(c));p.append(e);
 if(c.zh){{const z=document.createElement('span');z.className='zh';z.textContent=c.zh;p.append(z);}}
 p.onclick=()=>{{a.currentTime=c.start+.02;if(a.paused)a.play();}};
 wrap.appendChild(p);c.el=p;
}});
let cur=-1;
function paint(i){{
 const en=document.getElementById('en'),zh=document.getElementById('zh'),tip=document.getElementById('tip');
 en.textContent='';zh.textContent='';tip.textContent='';
 if(i<0)return;const c=CUES[i];
 en.append(enFrag(c));zh.textContent=c.zh||'';
 const notes=(c.marks||[]).filter(m=>m.note).map(m=>m.note);
 if(notes.length)tip.textContent='🎯 '+notes.join(' | ');
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
    path.write_text(html, encoding="utf-8")

async def build_section(data, voice, mp3_name, title, subtitle_hint, active_tab, out_dir):
    cues = []
    pcm_chunks = []
    current_time = 0.0
    gap = np.zeros(int(SR * 0.35), dtype=np.float32)

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        for idx, item in enumerate(data):
            tmp_mp3 = tdp / f"s_{idx}.mp3"
            comm = edge_tts.Communicate(item["en"], voice)
            await comm.save(str(tmp_mp3))
            pcm = mp3_to_pcm(tmp_mp3, ffmpeg)
            dur = len(pcm) / SR
            
            cues.append({
                "start": round(current_time, 3),
                "end": round(current_time + dur, 3),
                "en": item["en"],
                "zh": item["zh"],
                "marks": item.get("marks", [])
            })
            pcm_chunks.append(pcm)
            pcm_chunks.append(gap)
            current_time += dur + 0.35

    all_pcm = np.concatenate(pcm_chunks)
    mp3_path = out_dir / mp3_name
    pcm_to_mp3(all_pcm, mp3_path, ffmpeg)
    print(f"  [OK] {mp3_name} 合成完成: {len(data)} 句, 总时长 {current_time:.1f} 秒")

    # 写 SRT
    srt_name = mp3_name.replace(".mp3", ".srt")
    write_srt(cues, out_dir / srt_name)

    # 写 Player HTML
    player_name = f"player-{active_tab}.html"
    render_player(cues, mp3_name, title, subtitle_hint, active_tab, out_dir / player_name)
    print(f"  [OK] {player_name} 生成完成")

def update_listening_player(out_dir):
    """为原有的 player.html 注入统一顶部导航栏"""
    p = out_dir / "player.html"
    if not p.exists():
        return
    text = p.read_text(encoding="utf-8")
    if 'id="nav-tabs"' in text:
        return
    
    tabs_html = """<nav id="nav-tabs">
  <a href="player.html" class="tab-item active">🎧 Part II 听力全套 (13:17)</a>
  <a href="player-cloze.html" class="tab-item">📖 Section A 选词填空 (时间银行)</a>
  <a href="player-passage1.html" class="tab-item">📖 Section C 仔细阅读一 (代际流动)</a>
  <a href="player-passage2.html" class="tab-item">📖 Section C 仔细阅读二 (农业无人机)</a>
</nav>"""
    css_tabs = """#nav-tabs{display:flex;gap:8px;background:#181b22;padding:10px 18px;border-bottom:1px solid #2a2e35;overflow-x:auto;flex-wrap:nowrap}
.tab-item{color:#9aa3af;text-decoration:none;font-size:13px;padding:6px 14px;border-radius:6px;transition:all 0.2s;background:#222630;white-space:nowrap;display:inline-flex;align-items:center}
.tab-item:hover{color:#fff;background:#2d3340}
.tab-item.active{color:#fff;background:#3b82f6;font-weight:600}
"""
    text = text.replace("<style>", f"<style>\n{css_tabs}")
    text = text.replace("<body>", f"<body>\n{tabs_html}")
    p.write_text(text, encoding="utf-8")
    print("  [OK] player.html 已注入统一顶部导航栏")

async def main():
    out_dir = Path("knowledge/cet4-bank/07-整套模拟卷/mock-01/audio")
    print("🚀 开始为 mock-01 阅读篇章合成精准对齐音频与交互播放器...")
    
    # 1. 选词填空
    await build_section(
        CLOZE_DATA, VOICE_CLOZE, "mock-01-reading-cloze.mp3",
        "mock-01 Section A — 选词填空 (时间银行)",
        "纯美音朗读与考点词性解构", "cloze", out_dir
    )

    # 2. 仔细阅读一
    await build_section(
        P1_DATA, VOICE_P1, "mock-01-reading-passage1.mp3",
        "mock-01 Section C Passage 1 — 代际流动与故乡依恋",
        "纯美音叙事朗读与四大原生路标", "passage1", out_dir
    )

    # 3. 仔细阅读二
    await build_section(
        P2_DATA, VOICE_P2, "mock-01-reading-passage2.mp3",
        "mock-01 Section C Passage 2 — 农业无人机与精准种植",
        "纯美音科技说明与题眼定位", "passage2", out_dir
    )

    # 4. 更新听力播放器
    update_listening_player(out_dir)
    print("🎉 全部 4 套交互播放器与精准对齐音频生成完毕！")

if __name__ == "__main__":
    asyncio.run(main())
