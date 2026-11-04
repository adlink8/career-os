# -*- coding: utf-8 -*-
"""文体指纹对照：把模拟稿与真题正文放在同一组字面特征上比，找出真正的区分特征。

只用可解释的字面量（不训练分类器），输出每组均值与标准化差距（z），
并按 |z| 排序 —— 谁差距最大，谁就是评委眼里的破绽。
用法: python cet4/bin/cet4_style_diff.py --glob "set-5[2-8].json"
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
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
SRC = ROOT / "var" / "cet4-daily" / "ten-sets"
SYL = ROOT / "knowledge" / "cet4-bank" / "04-高频词汇与大纲词库" / "大学英语四级完整大纲词汇.txt"

ABSTR = re.compile(r"\b\w+(?:tion|sion|ment|ness|ity|ism|ance|ence|ization|isation)\b", re.I)
CONN = re.compile(r"\b(however|therefore|moreover|furthermore|thus|consequently|meanwhile|nevertheless|in addition|as a result|for example|for instance|on the other hand)\b", re.I)
HEDGE = re.compile(r"\b(may|might|could|perhaps|possibly|likely|suggests?|appears?|seems?)\b", re.I)
PASS = re.compile(r"\b(is|are|was|were|be|been|being)\s+\w+(?:ed|en)\b", re.I)


def syllables(w: str) -> int:
    w = re.sub(r"[^a-z]", "", w.lower())
    g = re.findall(r"[aeiouy]+", w)
    n = len(g)
    if w.endswith("e") and n > 1 and not w.endswith(("le", "ee")):
        n -= 1
    return max(1, n)


def feats(text: str, syl: set) -> dict:
    text = re.sub(r"[_*#]", "", text or "")
    sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 3]
    toks = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    n = max(1, len(toks))
    lens = [len(s.split()) for s in sents] or [0]
    raw = text.strip()
    paras = [p for p in re.split(r"\n\s*\n", raw) if p.strip()]
    if len(paras) <= 2:                     # 真题 md 常用单换行分段
        paras = [p for p in re.split(r"\n", raw) if len(p.split()) >= 15]
    paras = paras or [raw]
    lower = [t.lower() for t in toks]
    in_syl = sum(1 for t in lower if t in syl)
    syls = sum(syllables(t) for t in toks) or 1
    f = {
        "words": len(toks),
        "wps": round(len(toks) / max(1, len(sents)), 2),
        "sent_sd": round(st.pstdev(lens), 2) if len(lens) > 1 else 0.0,
        "paras": len(paras),
        "para_sd": round(st.pstdev([len(p.split()) for p in paras]), 1) if len(paras) > 1 else 0.0,
        "wordlen": round(sum(len(t) for t in toks) / n, 2),
        "syl_cov": round(100 * in_syl / n, 1),
        "abstr": round(1000 * len(ABSTR.findall(text)) / n, 1),
        "conn": round(1000 * len(CONN.findall(text)) / n, 1),
        "hedge": round(1000 * len(HEDGE.findall(text)) / n, 1),
        "passive": round(1000 * len(PASS.findall(text)) / n, 1),
        "quotes": text.count('"') + text.count("\u201c"),
        "digits": len(re.findall(r"\b\d[\d,.]*\b", text)),
        "dash_semi": len(re.findall(r"[—;]", text)),
        "flesch": round(206.835 - 1.015 * (len(toks) / max(1, len(sents))) - 84.6 * (syls / n), 1),
    }
    return f


def real_texts() -> list:
    out = []
    for md in sorted(BANK.rglob("*.md")):
        t = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
            body = t[m.end():]
            body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
            cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
            p = re.sub(r"[_*#]", "", (body[:cut.start()] if cut else "")[:4000]).strip()
            if len(p.split()) >= 250:
                out.append(p)
    return out


def mock_texts(pattern: str) -> list:
    files = []
    for pat in pattern.split("|"):
        files.extend(sorted(SRC.glob(pat)))
    files = [f for f in files if re.fullmatch(r"set-\d{2}\.json", f.name)]
    return [json.loads(f.read_text(encoding="utf-8")).get("passage") or "" for f in files]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="set-5[2-8].json")
    args = ap.parse_args()

    syl = set()
    for line in SYL.read_text(encoding="utf-8", errors="ignore").splitlines():
        w = line.split("\t")[0].strip().lower()
        if w and re.fullmatch(r"[a-z][a-z'-]*", w):
            syl.add(w)
            for suf in ("s", "es", "ed", "ing", "d"):
                syl.add(w + suf)

    real = [feats(t, syl) for t in real_texts()]
    mock = [feats(t, syl) for t in mock_texts(args.glob)]
    print(f"真题 {len(real)} 篇 / 模拟 {len(mock)} 篇")
    keys = list(real[0])
    rows = []
    for k in keys:
        r = [x[k] for x in real]
        m = [x[k] for x in mock]
        sd = st.pstdev(r) or 1e-9
        z = (st.mean(m) - st.mean(r)) / sd
        rows.append((abs(z), k, round(st.mean(r), 2), round(st.mean(m), 2), round(z, 2)))
    rows.sort(reverse=True)
    print(f"{'特征':10} {'真题均值':>9} {'模拟均值':>9} {'z(模拟-真题)':>12}")
    for az, k, rm, mm, z in rows:
        flag = "  ← 破绽" if az >= 0.8 else ""
        print(f"{k:10} {rm:>9} {mm:>9} {z:>12}{flag}")
    (ROOT / "var" / "cet4-daily" / "style-diff.json").write_text(
        json.dumps({"real_mean": {k: st.mean([x[k] for x in real]) for k in keys},
                    "mock_mean": {k: st.mean([x[k] for x in mock]) for k in keys},
                    "z": {r[1]: r[4] for r in rows}}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
