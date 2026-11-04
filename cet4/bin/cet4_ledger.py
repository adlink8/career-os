# -*- coding: utf-8 -*-
"""成品卷评测台账：10 套模拟卷一次跑完三道尺子，产出可核对账本。

三道尺子：
  1) 盲做一致（答案键 vs 盲做）
  2) 无锚点真题感（3 评委，和真卷均值比）
  3) 审查 verdict（附真卷同审基线：真卷 0/8 通过）

输出: var/cet4-daily/line-compare/ledger.json + ledger.md
用法: python cet4/bin/cet4_ledger.py --sets "set-8[1-7].s2.json|set-9[1-3].s2.json"
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
import statistics as st
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "var" / "cet4-daily" / "ten-sets"
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
OUT = ROOT / "var" / "cet4-daily" / "line-compare"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

RATE = """下面是若干段英语短文（每段约 350 词），都是大学英语四级阅读级别的文章，来源不一。
请逐段打分：作为一篇四级阅读文章，它的「典型真题感」有多强（1=不像四级文章，3=一般，5=就是真题的样子）。
不用判断来源，只按阅读经验打分，并给半句理由。
只输出 JSON：[{"id":"X01","score":4,"reason":"<=18字"}]

"""
SOLVE = """你是四级考生。只给文章和题目，没有答案。逐题选唯一最佳答案，理由<=20字。
只输出 JSON：[{"no":46,"answer":"A","why":"..."}]

"""


def cb(prompt: str, timeout: int = 2400) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jp(t: str, kind="["):
    t = re.sub(r"^```(?:json)?\s*", "", (t or "").strip())
    t = re.sub(r"```$", "", t).strip()
    i, j = (t.find("["), t.rfind("]")) if kind == "[" else (t.find("{"), t.rfind("}"))
    if i < 0 or j <= i:
        return [] if kind == "[" else {}
    frag = t[i:j + 1]
    for a in (frag, re.sub(r",\s*([}\]])", r"\1", frag)):
        try:
            return json.loads(a)
        except json.JSONDecodeError:
            continue
    return [] if kind == "[" else {}


def real_passages(n=10, seed=61) -> list:
    pool = []
    for md in sorted(BANK.rglob("*.md")):
        t = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
            body = t[m.end():]
            body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
            cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
            p = re.sub(r"[_*#]", "", (body[:cut.start()] if cut else "")[:4000]).strip()
            if 330 <= len(p.split()) <= 390:
                pool.append(p)
    random.Random(seed).shuffle(pool)
    return pool[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="set-8[1-7].s2.json|set-9[1-3].s2.json")
    ap.add_argument("--judges", type=int, default=3)
    ap.add_argument("--tag", default="ledger")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    files = []
    for pat in args.sets.split("|"):
        files.extend(sorted(SRC.glob(pat)))
    papers = []
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("passage") and d.get("questions"):
            papers.append({"file": f.name, "stem": f.stem, "data": d})
    print(f"成品卷 {len(papers)} 套")

    # 尺子 1：盲做
    def solve_one(p):
        d = p["data"]
        body = "文章：\n" + d["passage"] + "\n\n题目：\n"
        for q in d["questions"]:
            body += f'{q.get("no")}. {q.get("stem")}\n' + "\n".join(q.get("options") or []) + "\n"
        got = jp(cb(SOLVE + body))
        mine = {int(g.get("no")): str(g.get("answer") or "").upper()[:1] for g in got if g.get("no")}
        wrong = [int(q["no"]) for q in d["questions"] if mine.get(int(q["no"])) != str(q.get("answer")).upper()[:1]]
        return wrong

    with ThreadPoolExecutor(max_workers=3) as ex:
        wrongs = list(ex.map(solve_one, papers))

    # 尺子 2：无锚点真题感
    items = [{"id": f"P{i+1:02d}", "text": p["data"]["passage"], "group": "mock", "idx": i}
             for i, p in enumerate(papers)]
    items += [{"id": f"R{i:02d}", "text": t, "group": "real", "idx": None}
              for i, t in enumerate(real_passages(10), 1)]

    def judge(k):
        order = list(items)
        random.Random(500 + k).shuffle(order)
        body = "\n\n=====\n\n".join(f"[{it['id']}]\n{it['text']}" for it in order)
        return {str(g.get("id")): g.get("score") for g in jp(cb(RATE + body)) if g.get("id")}

    with ThreadPoolExecutor(max_workers=args.judges) as ex:
        votes = list(ex.map(judge, range(args.judges)))

    def score(iid):
        vals = [v.get(iid) for v in votes if isinstance(v.get(iid), (int, float))]
        return round(st.mean(vals), 2) if vals else None

    real_scores = [score(it["id"]) for it in items if it["group"] == "real"]
    real_scores = [s for s in real_scores if s is not None]
    real_mean = round(st.mean(real_scores), 2) if real_scores else None

    rows = []
    for p, wrong in zip(papers, wrongs):
        iid = f"P{papers.index(p)+1:02d}"
        rv = SRC / f"{p['stem'].split('.')[0]}.review2.json"
        if not rv.exists():
            rv = SRC / f"{p['stem'].split('.')[0]}.review.json"
        verdict = None
        if rv.exists():
            verdict = json.loads(rv.read_text(encoding="utf-8")).get("verdict")
        s = score(iid)
        rows.append({"stem": p["stem"], "file": p["file"], "words": len(p["data"]["passage"].split()),
                     "solve_wrong": wrong, "authenticity": s,
                     "delta_vs_real": round(s - real_mean, 2) if (s is not None and real_mean) else None,
                     "review_verdict": verdict})
    rows.sort(key=lambda r: (-(r["authenticity"] or 0)))

    print(f"\n真题无锚点基线：{real_mean}（{len(real_scores)} 篇）")
    print(f"{'卷':18} {'词数':>4} {'真题感':>6} {'比真题':>7} {'盲做':>6} {'审查':>16}")
    for r in rows:
        print(f"{r['stem']:18} {r['words']:>4} {r['authenticity'] if r['authenticity'] is not None else '-':>6} "
              f"{r['delta_vs_real'] if r['delta_vs_real'] is not None else '-':>7} "
              f"{len(r['solve_wrong'])}/5 {'':>1} {str(r['review_verdict']):>16}")

    above = sum(1 for r in rows if r["delta_vs_real"] is not None and r["delta_vs_real"] >= 0)
    zero_wrong = sum(1 for r in rows if not r["solve_wrong"])
    passed = sum(1 for r in rows if str(r["review_verdict"]).startswith("pass"))
    print(f"\n真题感不低于真卷：{above}/{len(rows)}")
    print(f"盲做全对：{zero_wrong}/{len(rows)}")
    print(f"审查通过：{passed}/{len(rows)}（真卷同审基线 0/8）")

    (OUT / f"{args.tag}.json").write_text(json.dumps({"real_mean": real_mean, "rows": rows}, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    md = ["# 成品卷评测台账", "", f"真卷无锚点基线：{real_mean}；审查员对真卷通过率：0/8", "",
          "| 卷 | 词数 | 真题感 | 比真卷 | 盲做 | 审查 |", "|---|---:|---:|---:|---:|---|"]
    for r in rows:
        md.append(f'| {r["stem"]} | {r["words"]} | {r["authenticity"] if r["authenticity"] is not None else "-"} | '
                  f'{r["delta_vs_real"] if r["delta_vs_real"] is not None else "-"} | '
                  f'{5-len(r["solve_wrong"])}/5 | {r["review_verdict"]} |')
    md += ["", f"汇总：真题感 ≥ 真卷 {above}/{len(rows)}；盲做全对 {zero_wrong}/{len(rows)}；审查通过 {passed}/{len(rows)}"]
    (OUT / f"{args.tag}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("台账:", OUT / f"{args.tag}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
