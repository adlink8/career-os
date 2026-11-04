# -*- coding: utf-8 -*-
"""抽取整套阅读卷三类题（选词/匹配/仔细）的原文、题干、答案，建立出题知识库。"""
from __future__ import annotations

# --- 四级工具根目录：相对路径统一按 cet4/ 解析（在仓库根或 cet4/ 下运行都行）---
import os as _os, sys as _sys, pathlib as _pl
_CET4_ROOT = _pl.Path(__file__).resolve().parents[1]
try:
    _os.chdir(_CET4_ROOT)
except OSError:
    pass
_sys.argv = [a[5:] if a[:5] in ("cet4/", "cet4\\") else a for a in _sys.argv]
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
ANS = ROOT / "knowledge" / "cet4-bank" / "02-真题标准答案" / "cet4-answers.json"
OUT = ROOT / "knowledge" / "cet4-bank" / "10-出题知识库" / "real-exemplars.json"


def part3(text: str) -> str:
    i = text.find("## Part III")
    return text[i:] if i >= 0 else text


def parse_section_a(block: str):
    m = re.search(r"### Section A(.*?)### Section B", block, flags=re.S)
    if not m:
        return None
    body = m.group(1)
    table = re.search(r"(\|\s*A\).*?)(?:\n\n|\Z)", body, flags=re.S)
    bank = {}
    if table:
        for line in table.group(1).splitlines():
            for cell in line.split("|"):
                mm = re.match(r"\s*([A-O])\)\s*(.+?)\s*$", cell.strip())
                if mm:
                    bank[mm.group(1)] = mm.group(2)
        passage = body[: table.start()].strip()
    else:
        passage = body.strip()
    intro_end = passage.find("_\n\n")
    if intro_end > 0:
        passage = passage[intro_end + 3:]
    blanks = [int(x) for x in re.findall(r"<u>&emsp;(\d+)&emsp;</u>", passage)]
    passage = re.sub(r"<u>&emsp;(\d+)&emsp;</u>", r"__\1__", passage).strip()
    passage = re.sub(r"^\*\*Directions:\*\*.*?\n\n", "", passage, flags=re.S)
    return {"passage": passage, "bank": bank, "blanks": blanks}


def parse_section_b(block: str):
    m = re.search(r"### Section B(.*?)### Section C", block, flags=re.S)
    if not m:
        return None
    body = m.group(1)
    title_m = re.search(r"\*\*(.+?)\*\*", body)
    first_q = re.search(r"\n(\d{2})\.\s", body)
    text_end = first_q.start() if first_q else len(body)
    passage = body[:text_end]
    passage = re.sub(r"^\*\*Directions:\*\*.*?\n\n", "", passage.strip(), flags=re.S)
    paragraphs = re.findall(r"^([A-O])\)\s*(.+?)(?=\n[A-O]\)|\Z)", passage, flags=re.S | re.M)
    statements = []
    for mm in re.finditer(r"^(\d{2})\.\s*(.+?)(?=\n\d{2}\.\s|\Z)", body[text_end:], flags=re.S | re.M):
        statements.append({"no": int(mm.group(1)), "text": re.sub(r"\s+", " ", mm.group(2)).strip()})
    return {"title": title_m.group(1).strip() if title_m else "", "paragraphs": [p[1].strip() for p in paragraphs],
            "statements": statements}


def parse_section_c(block: str):
    m = re.search(r"### Section C(.*)$", block, flags=re.S)
    if not m:
        return None
    body = m.group(1)
    passages = re.split(r"#### Passage (?:One|Two)", body)
    qs = []
    for chunk in passages[1:]:
        cur = None
        for line in chunk.splitlines():
            mm = re.match(r"^\s*(\d{2})\.\s+(.+)", line)
            if mm and 46 <= int(mm.group(1)) <= 55:
                if cur:
                    qs.append(cur)
                cur = {"no": int(mm.group(1)), "stem": mm.group(2).strip(), "options": []}
                continue
            mo = re.match(r"^\s*([A-D])\)\s*(.+)", line)
            if mo and cur is not None and len(cur["options"]) < 4:
                cur["options"].append(f"{mo.group(1)}) {mo.group(2).strip()}")
        if cur:
            qs.append(cur)
    qs = [q for q in qs if len(q["options"]) == 4]
    return {"passage": passages[1][:3000] if len(passages) > 1 else "", "questions": qs}


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
        reading = table.get("reading") or []
        # 无答案也纳入统计（后续由答题 CB 产出推荐答案）
        block = part3(md.read_text(encoding="utf-8", errors="ignore"))
        a = parse_section_a(block)
        b = parse_section_b(block)
        c = parse_section_c(block)
        row = {"file": md.name, "set": set_idx, "A": a, "B": b, "C": c,
               "has_answers": len(reading) >= 30,
               "answers_A": dict(zip([str(i) for i in range(26, 36)], reading[0:10])) if len(reading) >= 30 else {},
               "answers_B": dict(zip([str(i) for i in range(36, 46)], reading[10:20])) if len(reading) >= 30 else {},
               "answers_C": dict(zip([str(i) for i in range(46, 56)], reading[20:30])) if len(reading) >= 30 else {}}
        rows.append(row)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    okA = sum(1 for r in rows if r["A"] and len(r["A"]["bank"]) >= 14 and len(r["A"]["blanks"]) == 10)
    okB = sum(1 for r in rows if r["B"] and len(r["B"]["statements"]) == 10)
    okC = sum(1 for r in rows if r["C"] and len(r["C"]["questions"]) == 10)
    print(f"papers={len(rows)} A_ok={okA} B_ok={okB} C_ok={okC}")


if __name__ == "__main__":
    main()
