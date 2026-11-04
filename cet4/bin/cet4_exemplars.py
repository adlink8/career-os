# -*- coding: utf-8 -*-
"""从真题库抽取「题干 + 四选项 + 答案」范例，供出题老师模仿（不是规则校验）。"""
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
OUT = ROOT / "var" / "cet4-daily" / "exemplars.json"


def classify(stem: str) -> str:
    s = stem.lower()
    if re.search(r"\binfer|imply|suggest|conclude|likely|probably\b", s):
        return "推断"
    if re.search(r"attitude|view|think of|feel about|author", s):
        return "态度"
    if re.search(r"refer to|means|mean by|word|phrase", s):
        return "词义"
    if re.search(r"why|reason|cause", s):
        return "原因"
    if re.search(r"main idea|mainly about|best title|purpose", s):
        return "主旨"
    return "细节"


def parse_questions(text: str):
    qs = []
    cur = None
    for line in text.splitlines():
        m = re.match(r"^\s*(\d{2})\s*[.、]\s*(.+)$", line)
        if m and 46 <= int(m.group(1)) <= 55:
            if cur:
                qs.append(cur)
            cur = {"no": int(m.group(1)), "stem": m.group(2).strip(), "options": []}
            continue
        m2 = re.match(r"^\s*([A-D])\)\s*(.+)$", line)
        if m2 and cur is not None and len(cur["options"]) < 4:
            cur["options"].append(f"{m2.group(1)}) {m2.group(2).strip()}")
    if cur:
        qs.append(cur)
    return [q for q in qs if len(q["options"]) == 4]


def main():
    answers = json.loads(ANS.read_text(encoding="utf-8"))
    out = []
    for md in sorted(BANK.glob("*/*.md")):
        m = re.search(r"cet4-(\d{4})-(\d{2})-(\d)", md.name)
        if not m:
            continue
        key = f"cet4-{m.group(1)}-{m.group(2)}"
        set_idx = str(int(m.group(3)) - 1)
        table = (answers.get(key) or {}).get(set_idx) or {}
        reading = table.get("reading") or []
        if len(reading) < 30:
            continue
        text = md.read_text(encoding="utf-8", errors="ignore")
        part = text.find("Part III")
        sec = text.find("Section C", part if part >= 0 else 0)
        block = text[sec:] if sec >= 0 else text
        for q in parse_questions(block):
            idx = q["no"] - 26
            if not (0 <= idx < 30):
                continue
            ans = reading[idx]
            if ans not in "ABCD":
                continue
            out.append({"paper": md.name, "no": q["no"], "stem": q["stem"],
                        "options": q["options"], "answer": ans, "type": classify(q["stem"])})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print("exemplars", len(out), Counter(x["type"] for x in out))


if __name__ == "__main__":
    main()
