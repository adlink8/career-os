# -*- coding: utf-8 -*-
"""生成三类题的知识库：统计 + 真题范例 + 出题/审查规范。"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "knowledge" / "cet4-bank" / "10-出题知识库" / "real-exemplars.json"
KB = ROOT / "knowledge" / "cet4-bank" / "10-出题知识库"


def words(s):
    return re.findall(r"[A-Za-z][A-Za-z'-]*", s or "")


def main():
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    for r in rows:
        pass

    # ---- 选词 ----
    a_pass = [r["A"] for r in rows if r["A"]]
    a_words = [len(words(x["passage"])) for x in a_pass]
    a_ans = Counter(v for r in rows for v in r["answers_A"].values())
    a_banks = Counter(len(x["bank"]) for x in a_pass)
    cloze = {
        "count": len(a_pass),
        "passage_words": {"min": min(a_words), "max": max(a_words), "avg": round(sum(a_words)/len(a_words), 1)},
        "bank_sizes": dict(a_banks),
        "answer_distribution": dict(a_ans),
        "examples": [
            {"file": r["file"], "passage": r["A"]["passage"][:1800], "bank": r["A"]["bank"],
             "answers": r["answers_A"]}
            for r in rows if r["A"]
        ][:6],
    }
    (KB / "01-选词填空").mkdir(parents=True, exist_ok=True)
    (KB / "01-选词填空" / "exemplars.json").write_text(json.dumps(cloze, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- 匹配 ----
    b_pass = [r["B"] for r in rows if r["B"]]
    b_paras = [len(x["paragraphs"]) for x in b_pass]
    b_stmts = [len(x["statements"]) for x in b_pass]
    b_words = [sum(len(words(p)) for p in x["paragraphs"]) for x in b_pass]
    b_ans = Counter(v for r in rows for v in r["answers_B"].values())
    match = {
        "count": len(b_pass),
        "paragraphs": dict(Counter(b_paras)),
        "statements": dict(Counter(b_stmts)),
        "passage_words_avg": round(sum(b_words)/len(b_words), 1),
        "answer_distribution": dict(b_ans),
        "examples": [
            {"file": r["file"], "title": r["B"]["title"], "paragraphs": r["B"]["paragraphs"],
             "statements": r["B"]["statements"], "answers": r["answers_B"]}
            for r in rows if r["B"]
        ][:4],
    }
    (KB / "02-长篇匹配").mkdir(parents=True, exist_ok=True)
    (KB / "02-长篇匹配" / "exemplars.json").write_text(json.dumps(match, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- 仔细 ----
    c_qs = [q for r in rows if r["C"] for q in r["C"]["questions"]]
    c_ans = Counter(v for r in rows for v in r["answers_C"].values())
    reading = {
        "count": len(c_qs),
        "answer_distribution": dict(c_ans),
        "examples": [
            {"file": r["file"], "questions": r["C"]["questions"], "answers": r["answers_C"]}
            for r in rows if r["C"] and r["C"]["questions"]
        ][:4],
    }
    (KB / "03-仔细阅读").mkdir(parents=True, exist_ok=True)
    (KB / "03-仔细阅读" / "exemplars.json").write_text(json.dumps(reading, ensure_ascii=False, indent=1), encoding="utf-8")

    stats = [f"# 阅读全卷三类题统计（{len(rows)} 套 × 30 题）", "",
             "| 题型 | 题量 | 关键统计 |", "|---|---:|---|",
             f"| 选词填空 | {sum(len(x['blanks']) for x in a_pass)} | 文章 {cloze['passage_words']['min']}–{cloze['passage_words']['max']} 词，词库 15 选 10 |",
             f"| 长篇匹配 | {sum(b_stmts)} | 段落 {min(b_paras)}–{max(b_paras)} 个，陈述 10 条，全文约 {match['passage_words_avg']} 词 |",
             f"| 仔细阅读 | {len(c_qs)} | 答案 A{c_ans.get('A',0)}/B{c_ans.get('B',0)}/C{c_ans.get('C',0)}/D{c_ans.get('D',0)} |",
             "",
             "选词答案分布：" + json.dumps(dict(a_ans), ensure_ascii=False),
             "",
             "匹配答案分布：" + json.dumps(dict(b_ans), ensure_ascii=False)]
    (KB / "全卷统计.md").write_text("\n".join(stats), encoding="utf-8")
    print("cloze", len(a_pass), "match", len(b_pass), "reading", len(c_qs))
    print("A answers", dict(a_ans))
    print("B answers", dict(b_ans))
    print("C answers", dict(c_ans))


if __name__ == "__main__":
    main()
