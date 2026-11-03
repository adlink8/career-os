# 09 · 四级阅读文章来源档案与选材分析

> 数据：2023.06–2026.06 共 **21 套**试卷、**84 个阅读篇章**（每套 Section A/B/C1/C2 各 1 篇）。
> 方法：逐篇抓取「懒笔记」真题精读页（`english-exam.lazynote.cn`）的「本文节选自…」出处说明，正则抽取站点 / 日期 / 原标题；再人工归类。
> 结果：**61 篇拿到出处（73%）**，23 篇页面未标注出处（无法机器确认，不臆造）。
> 原始数据：[sources-raw.json](sources-raw.json)；规整后：[sources.json](sources.json)。

---

## 一、来源分布（61 篇可确认）

| 类别 | 篇数 | 代表来源（篇数） |
| :--- | ---: | :--- |
| 主流媒体 | 14 | The Guardian (3)、The New York Times (2)、The Atlantic (2)、BBC (2)、TIME、NPR、WIRED、Business Insider、The Week |
| 科普 | 11 | Live Science (4)、ScienceDaily (2)、SciTechDaily、Popular Science、Scientific American、Nature、National Geographic |
| 学术 / 高校 / 机构 | 7 | The Conversation (2)、BPS、Penn State、TUM、Berkeley Understanding Science、The British Academy |
| 商业 / 职场 / 行业 | 6 | IEN (2)、Forbes、Entrepreneur、Quartz、Nashville Business Journal |
| 心理 | 2 | Psychology Today (2) |
| 垂类 / 地方 / 企业 / 教育 / UGC | 21 | Reader's Digest (2)、Dezeen、Student Edge、Harappa、Free Lance–Star、Grand National、Equitable、Iberdrola、Morocco Tomorrow、Interesting Engineering、The Ed Advocate、London Daily、wikiHow、Stuff、The Famous People、Happiest Baby、Highland Music、Big Think、Todoist、Greatest Performance |

**关键结论：四级不迷信《经济学人》。** 主流 + 科普只占 41%，另有 **34% 来自长尾站点**（地方报纸、企业博客、教育站、垂类网站）。这解释了为什么部分篇章"不像外刊"——它们本来就不是。

## 二、原文发表年份（61 篇有日期）

| 年份 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| 篇数 | 1 | 1 | 5 | 3 | 8 | 12 | 4 | 6 | 3 | 5 | 6 | 4 | 3 |

- 峰值在 **2018–2021**；从发表到入卷普遍滞后 **1–4 年**，最长 7 年（2016 年文章用于 2023 年）。
- 这说明：做模拟题**不必追当天新闻**，用 1–3 年前的社科/科普长文更接近真实选材口味。

## 三、话题与文体特征（结合 00 号文档 + 本次抽样）

1. **反常识社科**：常识是 A，研究/数据证明是 B（如"父亲休陪产假≠母亲减负"、"运动强度与情绪"）。
2. **生活科学**：睡眠、饮食、运动、塑料、气候、屏幕时间、职场效率。
3. **结构固定**：现象/常识 → 研究或数据 → 转折（However/Yet）→ 结论或建议；转折处必出题。
4. **难度锚点**（本次统计）：仔细阅读单篇约 **350 词**、平均句长 **19.3 词**、≥10 字母长词占 **7.2%**；篇章匹配篇约 **1055 词**；选词填空约 **252 词**。

## 四、对「每日选材管线」的直接约束

| 约束 | 依据 |
| :--- | :--- |
| 来源池优先 Guardian / BBC / NYT / Atlantic / ScienceDaily / LiveScience / The Conversation / Psychology Today / Popular Science | 本次统计的高频来源 |
| 不必每天抓"最新" | 原文滞后 1–4 年；可每周抓一次候选池 |
| 必须保留长尾 | 34% 来自垂类/地方站；但长尾无稳定 RSS，改为"人工/半自动补充"，不强求 |
| 单篇 350±60 词、句长 ≤ 22、长词 ≤ 9% | 本次语料统计 |
| 拒绝付费墙全文 | The Economist / NYT 多数文章需订阅，只能拿摘要，不适合整篇改写 |

## 五、缺口（gaps_source）

- **23 篇未标注**（2023.06 3 篇、2023.12 2 篇、2024.12 2 篇、2025.06 4 篇、2025.12 6 篇、2026.06 5 篇等）：懒笔记页面没有"本文节选自"说明，或页面 404。
- 补法：人工按标题搜原文；或换一个带出处的精读站。**未补之前不要把这些篇章的来源写死。**
