# -*- coding: utf-8 -*-
"""统计真题出题规律：题型、题干开头、选项长度、答案分布、干扰项特征、同义替换距离。"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "var" / "cet4-daily" / "exemplars.json"
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"

STOP = set("the a an of to in on for and or but with by from as at is are was were be been being that this these those it its their his her our your my we you they he she i not no can could may might will would should do does did have has had more most much many some any such than then there here what which who whom whose when where why how".split())


def words(s):
    return re.findall(r"[A-Za-z][A-Za-z'-]*", s.lower())


def content(s):
    return [w for w in words(s) if w not in STOP]


def passage_of(md: Path) -> str:
    text = md.read_text(encoding="utf-8", errors="ignore")
    i = text.find("Part III")
    j = text.find("Section C", i if i >= 0 else 0)
    k = text.find("#### Passage One", j if j >= 0 else 0)
    return text[k: k + 6000] if k >= 0 else text


def main():
    pool = json.loads(EX.read_text(encoding="utf-8"))
    papers = {p.name: passage_of(p) for p in BANK.glob("*/*.md")}
    type_c = Counter()
    head_c = Counter()
    ans_c = Counter()
    len_correct, len_distract = [], []
    overlap_correct = []
    absolute = 0
    not_in_passage = 0
    for q in pool:
        stem = q["stem"]
        type_c[q.get("type")] += 1
        head_c[stem.split()[0].lower() if stem.split() else ""] += 1
        ans_c[q["answer"]] += 1
        opts = q["options"]
        correct = next((o for o in opts if o.startswith(q["answer"] + ")")), "")
        dists = [o for o in opts if not o.startswith(q["answer"] + ")")]
        len_correct.append(len(words(correct)))
        len_distract.append(sum(len(words(d)) for d in dists) / max(1, len(dists)))
        psg = papers.get(q["paper"], "")
        pw = set(content(psg))
        cw = content(correct)
        if cw:
            hit = sum(1 for w in cw if w in pw) / len(cw)
            overlap_correct.append(hit)
            if not any(w in pw for w in cw):
                not_in_passage += 1
        if any(re.search(r"\b(all|never|only|always|completely|entirely|must|impossible)\b", d.lower()) for d in dists):
            absolute += 1
    n = len(pool)
    print("题数", n)
    print("题型", dict(type_c))
    print("题干开头", head_c.most_common(6))
    print("答案分布", dict(ans_c))
    print("正确项平均词数 %.1f  干扰项平均 %.1f" % (sum(len_correct)/n, sum(len_distract)/n))
    print("正确选项内容词在原文出现比例 均值 %.2f  中位 %.2f" % (sum(overlap_correct)/n, sorted(overlap_correct)[n//2]))
    print("含绝对化词的干扰项题数", absolute)
    print("正确项内容词完全不在原文的题数", not_in_passage)
    # 题干长度
    sl = [len(words(q["stem"])) for q in pool]
    print("题干平均词数 %.1f  最长 %d" % (sum(sl)/n, max(sl)))


if __name__ == "__main__":
    main()
