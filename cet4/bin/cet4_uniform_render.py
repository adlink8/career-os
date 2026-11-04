# -*- coding: utf-8 -*-
"""统一渲染器：把模拟卷与官方真题都渲染成**同一种试卷文本**，再交给评委配对比较。

为什么需要它：第 21~22 轮的配对评测一直被我自己的抽取方式污染——
模拟档案完整、真题档案被截断或缺指令行，评委于是靠「谁更完整」而不是「谁的写法更像真题」判断。
本模块把两侧都压成同一模板：
    Part I Writing（统一指令行）
    Part III Section A 选词填空（正文空号统一成 ___26___，词库 A-O 每行 5 个）
    Part III Section B 信息匹配（段落 [A]…[L] + 陈述 36-45）
    Part III Section C 仔细阅读（两篇各 5 题，只渲染题干）
    Part IV Translation（中文）
每块字段缺失就整份作废，避免「残档」参与比较。

用法:
  python cet4/bin/cet4_uniform_render.py --show 81      # 看渲染效果
  python cet4/bin/cet4_uniform_render.py --show real   # 看真题渲染效果
"""
from __future__ import annotations

# --- 四级工具根目录：相对路径统一按 cet4/ 解析（在仓库根或 cet4/ 下运行都行）---
import os as _os, sys as _sys, pathlib as _pl
_CET4_ROOT = _pl.Path(__file__).resolve().parents[1]
try:
    _os.chdir(_CET4_ROOT)
except OSError:
    pass
_sys.argv = [a[5:] if a[:5] in ("cet4/", "cet4\\") else a for a in _sys.argv]
import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "var" / "cet4-daily" / "papers"
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"

DIR_CLOZE = ("Directions: In this section, there is a passage with ten blanks. "
             "You are required to select one word for each blank from a list of choices "
             "given in a word bank following the passage.")
DIR_MATCH = ("Directions: In this section, you are going to read a passage with ten statements "
             "attached to it. Each statement contains information given in one of the paragraphs. "
             "Identify the paragraph from which the information is derived.")
DIR_READ = ("Directions: There are two passages in this section. Each passage is followed by "
            "some questions or unfinished statements. For each of them there are four choices "
            "marked A), B), C) and D).")
DIR_TRANS = "Directions: Translate the following passage into English."
DIR_WRITE = ("Directions: You will have 30 minutes to write an essay. "
             "You should write at least 120 words but no more than 180 words.")


def _blank_fix(text: str) -> str:
    """各种空号写法统一成 ___NN___。"""
    t = text or ""
    t = re.sub(r"(?is)<u>\s*&?e?m?s?p?;?\s*(\d{2})\s*(?:&emsp;|\s)*</u>", lambda m: f"___[{m.group(1)}]___", t)
    t = re.sub(r"(?is)<[^>]{1,20}>", "", t)
    for n in range(26, 36):
        t = re.sub(r"_{2,}\s*" + str(n) + r"\s*_{2,}", f"___[{n}]___", t)
        t = re.sub(r"\[\s*" + str(n) + r"\s*\]", f"[{n}]", t)
    return t


def _bank_lines(bank: dict) -> list:
    items = [f"{k}) {v}" for k, v in sorted((bank or {}).items())]
    return ["    ".join(items[i:i + 5]) for i in range(0, len(items), 5)]


def render(profile: dict) -> str:
    out = []
    out.append("Part I  Writing  (30 minutes)")
    out.append(DIR_WRITE)
    w = profile["writing"].strip()
    for dup in (r"(?i)You will have \d+ minutes? (?:for|to) [^.]*\.", r"(?i)You should write at least [\d ]*words?[^.]*\."):
        w = re.sub(dup, "", w)
    out.append(re.sub(r"\s+", " ", w).strip())
    out.append("")
    out.append("Part III  Reading Comprehension  (40 minutes)")
    out.append("Section A")
    out.append(DIR_CLOZE)
    out.append(_blank_fix(profile["cloze"]["passage"]).strip())
    out.append("Word bank:")
    out.extend(_bank_lines(profile["cloze"]["bank"]))
    out.append("")
    out.append("Section B")
    out.append(DIR_MATCH)
    for k, v in sorted((profile["match"]["paragraphs"] or {}).items()):
        out.append(f"[{k}] {v.strip()}")
    out.append("Statements:")
    for st in profile["match"]["statements"]:
        out.append(f"{st['no']}. {st['text'].strip()}")
    out.append("")
    out.append("Section C")
    out.append(DIR_READ)
    for name in ("passage1", "passage2"):
        p = profile["reading"][name]
        out.append(f"Passage {'One' if name == 'passage1' else 'Two'}")
        for q in p["stems"]:
            out.append(f"{q['no']}. {q['stem'].strip()}")
    out.append("")
    out.append("Part IV  Translation  (30 minutes)")
    out.append(DIR_TRANS)
    out.append(profile["translation"].strip())
    return "\n".join(out)


# ---------------- 模拟卷 ----------------
def from_paper(pid: str):
    f = PAPERS / f"paper-{pid}.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    r = d.get("reading") or {}
    cloze = r.get("cloze") or {}
    match = r.get("match") or {}
    p1 = (r.get("passage1") or {}).get("questions") or []
    p2 = (r.get("passage2") or {}).get("questions") or []
    if not (cloze.get("passage") and cloze.get("bank") and (match.get("statements")) and p1 and p2):
        return None
    return {
        "src": f"mock-{pid}",
        "writing": str((d.get("writing") or {}).get("directions") or ""),
        "cloze": {"passage": cloze["passage"], "bank": cloze["bank"]},
        "match": {"paragraphs": match.get("paragraphs") or {}, "statements": match.get("statements") or []},
        "reading": {"passage1": {"stems": [{"no": q["no"], "stem": q["stem"]} for q in p1]},
                    "passage2": {"stems": [{"no": q["no"], "stem": q["stem"]} for q in p2]}},
        "translation": str((d.get("translation") or {}).get("zh") or ""),
    }


# ---------------- 官方真题 ----------------
def from_md(md: Path):
    t = md.read_text(encoding="utf-8", errors="ignore")
    parts = re.split(r"^##\s*Part\s+(I{1,3}V?|IV)\b[^\n]*\n", t, flags=re.M)
    seg = {parts[i].strip(): parts[i + 1] for i in range(1, len(parts), 2)}
    read = seg.get("III", "")
    secs = re.split(r"^###\s*Section\s*([ABC])\b[^\n]*\n", read, flags=re.M)
    sec = {secs[i].strip(): secs[i + 1] for i in range(1, len(secs), 2)}
    a_raw = sec.get("A", "")
    b_raw = sec.get("B", "")

    # 选词填空正文：去掉 Directions 与词库表格
    a_body = re.sub(r"(?is)^.*?more than once\.?", "", a_raw, count=1)
    if a_body == a_raw:
        a_body = re.sub(r"(?is)^.*?given in a word bank following the passage\.?", "", a_raw, count=1)
    bank_rows = re.findall(r"\|\s*([A-O])\)?[.、]?\s*([A-Za-z][A-Za-z'-]*)", a_raw)
    a_body = re.sub(r"\|.*", "", a_body)
    cloze_passage = re.sub(r"(?m)^\s*_+\s*$", "", a_body)
    cloze_passage = re.sub(r"\s+\n", "\n", cloze_passage).strip()
    if not bank_rows or len(bank_rows) < 10 or not cloze_passage:
        return None

    # 匹配：段落 A-L 与陈述 36-45
    paras = {}
    for m in re.finditer(r"^\s*([A-L])[\.\)]\s*(.+?)(?=^\s*[A-L][\.\)]\s|\Z)", b_raw, flags=re.M | re.S):
        body = re.sub(r"\s+", " ", m.group(2)).strip()
        if len(body.split()) >= 8:
            paras[m.group(1)] = body
    sts = [{"no": int(n), "text": re.sub(r"\s+", " ", x).strip()}
           for n, x in re.findall(r"^\s*(3[6-9]|4[0-5])\.\s*(.+)$", b_raw, flags=re.M)]

    # 阅读：两篇各自 5 题干
    c_raw = sec.get("C", "")
    blocks = re.split(r"^####\s*Passage\s+(One|Two)\s*\n", c_raw, flags=re.M)
    stems = {}
    for i in range(1, len(blocks), 2):
        key = blocks[i].strip()
        body = blocks[i + 1]
        found = [(int(n), re.sub(r"\s+", " ", x).strip())
                 for n, x in re.findall(r"^\s*(\d{2})\.\s*(.+)$", body, flags=re.M)]
        found = [(n, x) for n, x in found if 46 <= n <= 55 and len(x.split()) >= 4]
        if len(found) >= 5:
            stems[key] = found[:5]

    write = re.sub(r"(?is)\*\*Directions?:?\*\*", "", seg.get("I", ""))
    write = re.sub(r"\*\*|__|_{1,2}", "", write)
    write = re.sub(r"\s+", " ", write).strip()
    trans = re.sub(r"(?is)\*\*Directions?:?\*\*", "", seg.get("IV", ""))
    trans = re.sub(r"\*\*|__|_{1,2}", "", trans)
    trans = re.sub(r"\s+", " ", trans).strip()

    if len(paras) < 8 or len(sts) < 10 or len(stems) < 2 or not write or not trans:
        return None
    return {
        "src": md.name,
        "writing": write,
        "cloze": {"passage": cloze_passage, "bank": dict(bank_rows[:15])},
        "match": {"paragraphs": paras, "statements": sts},
        "reading": {"passage1": {"stems": [{"no": n, "stem": x} for n, x in stems["One"]]},
                    "passage2": {"stems": [{"no": n, "stem": x} for n, x in stems["Two"]]}},
        "translation": trans,
    }


def all_reals(limit: int = 6, seed: int = 11) -> list:
    out = []
    for md in sorted(BANK.rglob("*.md")):
        p = from_md(md)
        if p:
            out.append(p)
    random.Random(seed).shuffle(out)
    return out[:limit]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", default="81")
    ap.add_argument("--limit", type=int, default=4000)
    args = ap.parse_args()
    if args.show == "real":
        rs = all_reals(1)
        if not rs:
            print("真题渲染失败：没有一份通过字段完整性检查")
            return 1
        text = render(rs[0])
        print(f"（来源 {rs[0]['src']}，{len(text)} 字）\n")
    else:
        p = from_paper(args.show)
        if not p:
            print("模拟卷渲染失败")
            return 1
        text = render(p)
        print(f"（模拟 paper-{args.show}，{len(text)} 字）\n")
    print(text[:args.limit])
    return 0


if __name__ == "__main__":
    sys.exit(main())
