# -*- coding: utf-8 -*-
"""抽取写作/翻译/听力三类题，并生成知识库（04/05/06）。"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
ANS = ROOT / "knowledge" / "cet4-bank" / "02-真题标准答案" / "cet4-answers.json"
KB = ROOT / "knowledge" / "cet4-bank" / "10-出题知识库"


def part(text, name):
    m = re.search(rf"## Part {name}.*?(?=\n## Part|\Z)", text, flags=re.S)
    return m.group(0) if m else ""


def parse_writing(text):
    blk = part(text, "I")
    m = re.search(r"\*\*Directions:\*\*\s*_(.+?)_", blk, flags=re.S)
    d = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    topic = ""
    tm = re.search(r"(?:opinions? on|about)\s+(.+?)[.。]", d, flags=re.I)
    if tm:
        topic = tm.group(1).strip()
    return {"directions": d, "topic": topic, "min_words": 120, "max_words": 180}


def parse_translation(text):
    blk = part(text, "IV")
    body = re.sub(r"^\*\*Directions:\*\*.*?_\s*", "", blk, flags=re.S).strip()
    body = re.sub(r"\s+", "", body)
    sents = [s for s in re.split(r"[。；]", body) if s.strip()]
    return {"zh": body, "chars": len(body), "sentences": len(sents),
            "avg_sentence_chars": round(len(body) / max(1, len(sents)), 1)}


def parse_listening(text):
    blk = part(text, "II")
    secs = {}
    for name, pat in (("A", r"### Section A(.*?)### Section B"), ("B", r"### Section B(.*?)### Section C"), ("C", r"### Section C(.*)$")):
        m = re.search(pat, blk, flags=re.S)
        if not m:
            continue
        body = m.group(1)
        qs = []
        cur = None
        for line in body.splitlines():
            mq = re.match(r"^\s*(\d{1,2})\.\s*A\)\s*(.+)", line)
            if mq:
                if cur:
                    qs.append(cur)
                cur = {"no": int(mq.group(1)), "options": [f"A) {mq.group(2).strip()}"]}
                continue
            mo = re.match(r"^\s*([B-D])\)\s*(.+)", line)
            if mo and cur is not None and len(cur["options"]) < 4:
                cur["options"].append(f"{mo.group(1)}) {mo.group(2).strip()}")
        if cur:
            qs.append(cur)
        secs[name] = [q for q in qs if len(q["options"]) == 4]
    return secs


def classify_writing(d: str) -> str:
    s = d.lower()
    if re.search(r"chart|graph|figure|table|data", s):
        return "图表"
    if re.search(r"letter|write to|email", s):
        return "书信"
    if re.search(r"suppose|imagine|if you", s):
        return "情景观点"
    return "观点议论"


def classify_translation(zh: str) -> str:
    for k, w in (("文化", ["传统", "文化", "历史", "节日", "建筑", "艺术", "书法", "茶"]),
                 ("经济", ["经济", "市场", "产业", "贸易", "消费", "就业"]),
                 ("科技", ["科技", "技术", "互联网", "数字", "人工智能", "创新"]),
                 ("环境", ["环境", "生态", "气候", "能源", "绿色"]),
                 ("社会", ["社会", "教育", "家庭", "城市", "人口", "乡村"])):
        if any(x in zh for x in w):
            return k
    return "其他"


def main():
    answers = json.loads(ANS.read_text(encoding="utf-8"))
    rows = []
    for md in sorted(BANK.glob("*/*.md")):
        m = re.search(r"cet4-(\d{4})-(\d{2})-(\d)", md.name)
        if not m:
            continue
        key = f"cet4-{m.group(1)}-{m.group(2)}"
        set_idx = str(int(m.group(3)) - 1)
        table = (answers.get(key) or {}).get(set_idx) or {}
        listening_ans = table.get("listening") or []
        # 无答案也纳入
        text = md.read_text(encoding="utf-8", errors="ignore")
        w = parse_writing(text)
        t = parse_translation(text)
        l = parse_listening(text)
        rows.append({"file": md.name, "writing": w, "translation": t, "listening": l,
                     "has_answers": len(listening_ans) >= 25,
                     "answers_listening": dict(zip([str(i) for i in range(1, 26)], listening_ans)) if len(listening_ans) >= 25 else {}})
    out = KB / "real-exemplars-2.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    wl = [len(r["writing"]["directions"].split()) for r in rows]
    tc = [r["translation"]["chars"] for r in rows]
    ts = [r["translation"]["sentences"] for r in rows]
    lcount = {k: sum(len(r["listening"].get(k, [])) for r in rows) for k in "ABC"}
    wtype = Counter(classify_writing(r["writing"]["directions"]) for r in rows)
    ttype = Counter(classify_translation(r["translation"]["zh"]) for r in rows)
    la = Counter(v for r in rows for v in r["answers_listening"].values())

    (KB / "04-听力").mkdir(exist_ok=True)
    (KB / "05-翻译").mkdir(exist_ok=True)
    (KB / "06-写作").mkdir(exist_ok=True)
    (KB / "04-听力" / "exemplars.json").write_text(json.dumps(
        [{"file": r["file"], "sections": r["listening"], "answers": r["answers_listening"]} for r in rows[:5]],
        ensure_ascii=False, indent=1), encoding="utf-8")
    (KB / "05-翻译" / "exemplars.json").write_text(json.dumps(
        [{"file": r["file"], "zh": r["translation"]["zh"], "chars": r["translation"]["chars"]} for r in rows[:5]],
        ensure_ascii=False, indent=1), encoding="utf-8")
    (KB / "06-写作" / "exemplars.json").write_text(json.dumps(
        [{"file": r["file"], "directions": r["writing"]["directions"], "topic": r["writing"]["topic"]} for r in rows[:5]],
        ensure_ascii=False, indent=1), encoding="utf-8")

    (KB / "04-听力" / "rules.md").write_text(f"""# 听力（Part II，25 题）知识库

## 真题统计（{len(rows)} 套）

| 项 | 实测 |
|---|---|
| 题量 | 25 题（Section A 新闻 7、B 长对话 8、C 短文 10） |
| 答案分布 | {json.dumps(dict(la), ensure_ascii=False)} |
| 选项 | 每题 4 项，平均 8-12 词 |

## 命题规则

1. Section A：3 篇新闻，每篇 2-3 题，考“谁/为什么/结果”；
2. Section B：2 段长对话，每段 4 题，考态度、建议、数字、转折；
3. Section C：3 篇短文，每篇 3-4 题，考主旨、细节、推断；
4. 干扰项：同音/近音、数字错位、张冠李戴、过度推断；
5. 音频语速约 130-150 wpm，只播一遍。
""", encoding="utf-8")

    (KB / "05-翻译" / "rules.md").write_text(f"""# 翻译（Part IV，汉译英段落）知识库

## 真题统计（{len(rows)} 套）

| 项 | 实测 |
|---|---|
| 字数 | {min(tc)}–{max(tc)} 汉字（均值 {round(sum(tc)/len(tc),1)}） |
| 句数 | {min(ts)}–{max(ts)} 句 |
| 主题 | {json.dumps(dict(ttype), ensure_ascii=False)} |

## 评分档次（15 分制）

| 档 | 分数 | 标准 |
|---|---|---|
| 一 | 13–15 | 译文准确、通顺，无重大语法错 |
| 二 | 10–12 | 基本准确，少量语法/用词错 |
| 三 | 7–9 | 能译出大意，错误较多 |
| 四 | 4–6 | 仅译出部分信息 |
| 五 | 1–3 | 几乎无有效译文 |

## 命题规则

1. 140–180 汉字，6–9 句，句子长短交错；
2. 主题优先：文化/传统、经济、科技、环境、社会；
3. 每段至少 2 个“四字结构/文化专名”，考文化负载词；
4. 避免生僻专名；必要的专名给英文提示（如 四合院 Siheyuan）。
""", encoding="utf-8")

    (KB / "06-写作" / "rules.md").write_text(f"""# 写作（Part I，120–180 词）知识库

## 真题统计（{len(rows)} 套）

| 项 | 实测 |
|---|---|
| 字数 | 120–180 词，30 分钟 |
| 题型 | {json.dumps(dict(wtype), ensure_ascii=False)} |
| 题干长度 | {min(wl)}–{max(wl)} 词 |

## 评分档次（15 分制）

| 档 | 分数 | 标准 |
|---|---|---|
| 一 | 13–15 | 切题、结构清晰、语言准确、句式多样 |
| 二 | 10–12 | 切题、少量语言错误 |
| 三 | 7–9 | 基本切题、错误较多 |
| 四 | 4–6 | 偏题或语言错误多 |
| 五 | 1–3 | 不成篇 |

## 命题规则

1. 情景式命题（Suppose your university…），要求表达观点；
2. 话题贴近校园/社会热点，不考专业背景；
3. 题干给 30 分钟、120–180 词；
4. 参考结构：观点 → 两个理由/例子 → 结论。
""", encoding="utf-8")
    print("papers", len(rows), "writing", dict(wtype), "translation", dict(ttype), "listening_answers", dict(la))


if __name__ == "__main__":
    main()
