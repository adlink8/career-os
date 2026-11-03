# -*- coding: utf-8 -*-
"""出题老师：只负责按四级阅读契约出 5 道题（不与改写混在一起）。

用法: python bin/cet4_make_questions.py <passage.json> [--out xxx.json]
输入 JSON 需含 passage/paragraphs；输出把 questions 合并回去并校验。
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
sys.path.insert(0, str(ROOT / "bin"))
from cet4_validate import check  # noqa: E402

PROMPT = """你是大学英语四级阅读命题老师。下面是真题范例，先模仿它们的设问方式与干扰项设计，再动笔。
【真题范例】
{examples}

给你一篇已改写好的文章，只出 5 道题，不要改文章。
只输出 JSON：{{"questions":[...]}}
每道题：
{{"no":1,"stem":"题干（英文 <=20 词，具体不空泛）","stem_cn":"题干中文（顺流直译）",
 "options":["A) ...","B) ...","C) ...","D) ..."],"options_cn":["A 项中文","B 项中文","C 项中文","D 项中文"],
 "answer":"A|B|C|D",
 "evidence":"原文定位句（必须逐字出现在 passage 中）",
 "paraphrase":{{"original":"原文词句","option":"选项换皮词"}},
 "trap":"无中生有|偷换概念|因果倒置|范围扩大|原词拼接",
 "option_analysis":[{{"letter":"A","correct":false,"why":"具体错因"}} ×4]}}
硬约束（来自 120 道真题统计）：
1) 5 题：细节 2-3、态度 1、推断 1、原因/词义 1；至少 1 题落在转折处；按原文出现顺序排 46-50。
1b) 题干 <=15 词，以 What 开头为主；Why 只用于因果考点。
1c) 正确项连续实词与原文重合 <=4，谓语必须换说法；禁止整句照搬。
1d) 三个干扰项分别用：无中生有、偷换概念、范围扩大/绝对化；禁止双答案。
1e) 同题四项长度差 <=3 词，正确项不得总是最长；答案至少覆盖 3 个字母。
2) 答案覆盖至少 3 个不同字母，禁止 5 题同答案。
3) 正确项必须同义替换，不得照抄原文；错误项写具体错因，引用原文或指出缺席/偷换/夸大。
4) 题干不得引入原文没有的概念；不得出现双答案。
5) 每题 evidence 必须逐字出现在 passage。
6) 正确项不得与原文连续 4 词重合；不得直接照抄原文谓语动词短语，必须同义替换。
7) 题号直接写 46、47、48、49、50（Section C Passage One 固定编号），不要写 1-5。
8) 同题四个选项长度差 <=3 词；正确答案不能总是最长项。
9) 先定考点再写题：优先从转折句、研究结论句、因果句、比较句里选考点。
考点候选句（必须各题对应其中一句，按顺序）：
{candidates}

文章：
{passage}
"""


def parse_json(text: str):
    t = re.sub(r"^```(?:json)?\s*", "", text.strip())
    t = re.sub(r"\s*```$", "", t)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paper")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    src = Path(args.paper)
    paper = json.loads(src.read_text(encoding="utf-8"))
    ex_path = ROOT / "var" / "cet4-daily" / "exemplars.json"
    examples = ""
    if ex_path.exists():
        pool = json.loads(ex_path.read_text(encoding="utf-8"))
        by = defaultdict(list)
        for x in pool:
            by[x.get("type")].append(x)
        picked = []
        for t in ("细节", "推断", "态度", "原因", "细节"):
            if by.get(t):
                picked.append(by.get(t).pop(0))
        examples = "\n\n".join(
            f"[{x['type']}] {x['stem']}\n" + "\n".join(x["options"]) + f"\n答案：{x['answer']}" for x in picked)
        cand = []
    for sent in re.split(r"(?<=[.!?])\s+", paper.get("passage", "")):
        low = sent.lower()
        if re.search(r"\b(but|however|yet|instead|rather)\b", low) or re.search(r"\b(found|suggest|show|reveal|conclude)\b", low) \
           or re.search(r"\b(because|so|therefore|lead to|result in)\b", low) or re.search(r"\b(more than|only|first|most)\b", low):
            cand.append(sent.strip())
    cand = cand[:8]
    prompt = PROMPT.format(passage=paper.get("passage", ""), examples=examples,
                           candidates="\n".join(f"{i+1}. {c}" for i, c in enumerate(cand)))
    proc = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                          capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(ROOT))
    data = parse_json(proc.stdout or "")
    if not data or not data.get("questions"):
        print("writer parse failed:", (proc.stdout or "")[:300])
        return 1
    for q in data["questions"]:
        for oa in q.get("option_analysis") or []:
            oa["correct"] = (oa.get("letter") == q.get("answer"))
    merged = {**paper, "questions": data["questions"]}
    result = check(merged)
    print(f"questions={len(data['questions'])} validate={result['ok']} errors={result['errors'][:5]}")
    out = Path(args.out) if args.out else src.with_name(src.stem + ".q.json")
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
