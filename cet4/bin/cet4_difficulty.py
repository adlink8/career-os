# -*- coding: utf-8 -*-
"""难度体检：把模拟卷正文与 21 套真题正文放在同一套客观指标下对比。

指标：词数、句长、长词占比、大纲词覆盖率、从句密度、被动密度、Flesch 易读度。
用法: python cet4/bin/cet4_difficulty.py [--paper var/cet4-daily/demo-whole-paper.json] [--json out.json]
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
SYL = ROOT / "knowledge" / "cet4-bank" / "04-高频词汇与大纲词库" / "大学英语四级完整大纲词汇.txt"

CLAUSE = r"\b(that|which|who|whom|whose|because|although|though|while|whereas|unless|when|since|as if|so that)\b"
PASSIVE = r"\b(is|are|was|were|be|been|being)\s+([a-z]+(?:ed|en))\b"


def syllabus() -> set:
    out = set()
    for line in SYL.read_text(encoding="utf-8", errors="ignore").splitlines():
        w = line.split("\t")[0].strip().lower()
        if w and re.fullmatch(r"[a-z][a-z'-]*", w):
            out.add(w)
            # 常见屈折形式也算认识
            for suf in ("s", "es", "ed", "ing", "d"):
                out.add(w + suf)
    return out


def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and n > 1 and not w.endswith(("le", "ee")):
        n -= 1
    return max(1, n)


def metrics(text: str, syl: set) -> dict:
    text = re.sub(r"[_*#]", "", text or "")
    sents = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if len(s.split()) >= 3]
    toks = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    n_w, n_s = len(toks), max(1, len(sents))
    lower = [t.lower() for t in toks]
    in_syl = sum(1 for t in lower if t in syl)
    long_w = sum(1 for t in toks if len(t) >= 9)
    syls = sum(syllables(t) for t in toks) or 1
    freel = 206.835 - 1.015 * (n_w / n_s) - 84.6 * (syls / max(1, n_w))
    return {
        "words": n_w,
        "sentences": n_s,
        "wps": round(n_w / n_s, 1),
        "wordlen": round(sum(len(t) for t in toks) / max(1, n_w), 2),
        "long9": round(100 * long_w / max(1, n_w), 1),
        "syl_cov": round(100 * in_syl / max(1, n_w), 1),
        "clause100": round(100 * len(re.findall(CLAUSE, text, flags=re.I)) / max(1, n_w), 1),
        "passive100": round(100 * len(re.findall(PASSIVE, text, flags=re.I)) / max(1, n_w), 1),
        "flesch": round(freel, 1),
    }


def real_passages() -> list:
    out = []
    for md in sorted(BANK.rglob("*.md")):
        t = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
            start = m.end()
            body = t[start:]
            # 跳过 Questions 说明行
            body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
            cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
            passage = body[: cut.start()] if cut else body[:4000]
            passage = passage.strip()
            if len(passage.split()) >= 120:
                out.append({"src": f"{md.parent.name}/{md.stem}/{m.group(1)}", "text": passage})
    return out


def mock_passages(paper_path: Path) -> list:
    d = json.loads(paper_path.read_text(encoding="utf-8"))
    out = []
    for key, label in (("passage1", "SectionC-Passage One"), ("passage2", "SectionC-Passage Two")):
        paras = d["reading"][key].get("paragraphs") or []
        text = "\n\n".join((p.get("en") or "").strip() for p in paras)
        out.append({"src": f"MOCK/{label}", "text": text})
    m = d["reading"]["match"]
    mtxt = "\n\n".join(str(v) for k, v in m["paragraphs"].items())
    out.append({"src": "MOCK/SectionB", "text": mtxt})
    c = d["reading"]["cloze"]
    bank, ans = c.get("bank") or {}, c.get("answers") or {}
    ctext = re.sub(r"__(\d+)__", lambda x: bank.get(ans.get(x.group(1), ""), "") or "blank", c["passage"])
    out.append({"src": "MOCK/SectionA", "text": ctext})
    return out


def pct(v: float, arr: list) -> str:
    if not arr:
        return "-"
    below = sum(1 for x in arr if x < v)
    return f"{round(100 * below / len(arr))}%"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="var/cet4-daily/demo-whole-paper.json")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    syl = syllabus()
    print(f"大纲词条: {len(syl)}")
    real = real_passages()
    print(f"真题 Passage 提取: {len(real)} 篇")

    keys = ["words", "sentences", "wps", "wordlen", "long9", "syl_cov", "clause100", "passive100", "flesch"]
    real_m = [metrics(p["text"], syl) for p in real]
    mock = mock_passages(ROOT / args.paper)
    mock_m = [metrics(p["text"], syl) for p in mock]

    def row(name, m, base=None):
        cells = [f"{m[k]:>7}" for k in keys]
        pcts = [f"{pct(m[k], [b[k] for b in base]) if base else '-':>5}" for k in keys]
        print(f"{name:<26}" + " ".join(cells) + "   ‖ 分位 " + " ".join(pcts))

    hdr = f"{'样本':<26}" + " ".join(f"{k:>7}" for k in keys)
    print(hdr)
    print("-" * (len(hdr) + 8))
    for name, m in zip([p["src"].split("/")[0] + "/" + p["src"].split("/")[-1] for p in real], real_m):
        row(name, m)
    med = {k: st.median([m[k] for m in real_m]) for k in keys}
    print("-" * (len(hdr) + 8))
    print(f"{'【真题中位数】(n=%d)' % len(real_m):<24}" + " ".join(f"{med[k]:>7.2f}" for k in keys))
    for p, m in zip(mock, mock_m):
        row(p["src"], m, real_m)

    # ---- 参考视图：只报数，不做通过/不通过 ----
    # 机器指标只用于解释偏差来源，是否「与真题难度相当」由独立 LLM 盲评判定。
    ref_keys = ["words", "wps", "long9", "syl_cov", "flesch"]
    names = {"words": "篇幅", "wps": "句长", "long9": "长词占比", "syl_cov": "大纲词占比", "flesch": "Flesch"}
    print("\n【参考】各段在真题分布中的位置（仅作解释，不作判定）")
    for p_, m in zip(mock, mock_m):
        bits = []
        for k in ref_keys:
            arr = sorted(b[k] for b in real_m)
            n = len(arr)
            pos = sum(1 for x in arr if x < m[k]) / n
            bits.append(f"{names[k]} {pos:.0%}")
        print(f"  {p_['src']:<28}" + " | ".join(bits))
    print("  注：这里是给 LLM 审查员看的证据数字，不设阈值、不自动判负。")

    if args.json:
        Path(args.json).write_text(json.dumps({"real": real_m, "mock": mock_m,
                                               "real_src": [p["src"] for p in real],
                                               "mock_src": [p["src"] for p in mock],
                                               "median": med}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("json ->", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
