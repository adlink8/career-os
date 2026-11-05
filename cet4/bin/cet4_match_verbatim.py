# -*- coding: utf-8 -*-
"""把信息匹配陈述改回「接近照抄」——这是真题的实际做法（第 26 轮实测）。

测量：真题 10 条陈述与对应段落的最长逐字重合为 18–20 词（两份样本均如此），
而我们此前只有 8–13 词；上一轮按评委意见"减少照抄"其实是**背离真卷**。

做法：对每条陈述，从它对应的段落里挑一句与该陈述词重叠最多的原句，
截取到 15–22 词作为新陈述。这样既贴合真卷写法，也保证指向唯一（本来就来自该段）。

用法: python cet4/bin/cet4_match_verbatim.py --papers 81,82,85,86,87
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
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "var" / "cet4-daily" / "papers"


def toks(t: str) -> list:
    return re.findall(r"[A-Za-z0-9'-]+", t or "")


def pick_sentence(stmt: str, para: str) -> str:
    """从段落里挑与陈述词重叠最多的一句，截到 15-22 词。"""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", para or "") if len(s.strip().split()) >= 6]
    if not sents:
        return stmt
    sw = {w.lower() for w in toks(stmt) if len(w) > 3}
    best, best_score = sents[0], -1
    for s in sents:
        pw = {w.lower() for w in toks(s) if len(w) > 3}
        sc = len(sw & pw) / max(1, len(sw))
        if sc > best_score:
            best, best_score = s, sc
    words = best.split()
    if len(words) > 20:
        words = words[:20]
        while words and words[-1].endswith(","):
            words = words[:-1]
        best = " ".join(words).rstrip(",;:") + "."
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", default="81,82,85,86,87")
    args = ap.parse_args()
    for pid in [x for x in re.split(r"[,\s]+", args.papers) if x]:
        f = PAPERS / f"paper-{pid}.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        m = d["reading"]["match"]
        paras, ans = m.get("paragraphs") or {}, m.get("answers") or {}
        changed = 0
        for st in m.get("statements") or []:
            letter = ans.get(str(st["no"]))
            para = paras.get(letter, "")
            if not para:
                continue
            new = pick_sentence(st["text"], para)
            if new and new != st["text"]:
                st["text"] = new
                changed += 1
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"paper-{pid}: 改写陈述 {changed} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
