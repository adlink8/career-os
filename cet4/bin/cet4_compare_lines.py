# -*- coding: utf-8 -*-
"""产线横向评测：同一把尺子（无锚点真题感 + 盲做一致 + 与真卷基线对照）比 9 条产线。

输出一张排名表：哪条产线的稿子最像真题、答案是否自洽、有哪些硬伤。
用法: python cet4/bin/cet4_compare_lines.py [--judges 3]
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
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
OUT = ROOT / "var" / "cet4-daily" / "line-compare"

LINES = [
    ("v1 自由生成", "set-0[1-3].json"),
    ("v2 外刊改造·全留真名", "set-3[1-3].json"),
    ("v3 外刊改造·收紧", "set-4[1-3].json"),
    ("v4 骨架移植", "set-5[2-4].json"),
    ("v5 科普中等改写", "set-8[1-3].s1.json"),
    ("v5 修后", "set-8[2-4].s2.json"),
    ("v6 证据加固", "set-9[1-3].json"),
    ("v7 事实重建", "set-10[1-3].d1.json"),
    ("人类原文只删不改", "set-11[1-3].json"),
]

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


def real_passages(n=10, seed=7) -> list:
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
    ap.add_argument("--judges", type=int, default=3)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    items = []
    n = 0
    for label, pattern in LINES:
        for f in sorted(SRC.glob(pattern)):
            if not f.exists():
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
            if not d.get("passage"):
                continue
            n += 1
            items.append({"id": f"C{n:02d}", "label": label, "file": f.name,
                          "text": d["passage"], "group": "mock", "data": d})
    reals = real_passages(10)
    items += [{"id": f"R{i:02d}", "label": "真题", "file": "-", "text": t, "group": "real", "data": None}
              for i, t in enumerate(reals, 1)]
    print(f"待评 {len(items)} 段（{len(items)-10} 条产线 + 10 篇真题）")

    def judge(k: int):
        order = list(items)
        random.Random(300 + k).shuffle(order)
        body = "\n\n=====\n\n".join(f"[{it['id']}]\n{it['text']}" for it in order)
        data = jp(cb(RATE + body))
        return {str(g.get("id")): g.get("score") for g in data if g.get("id")}

    with ThreadPoolExecutor(max_workers=args.judges) as ex:
        votes = list(ex.map(judge, range(args.judges)))

    def score_of(iid):
        vals = [v.get(iid) for v in votes if isinstance(v.get(iid), (int, float))]
        return st.mean(vals) if vals else None

    real_scores = [score_of(it["id"]) for it in items if it["group"] == "real"]
    real_scores = [s for s in real_scores if s is not None]
    real_mean = st.mean(real_scores) if real_scores else None
    print(f"真题无锚点均值：{round(real_mean,2) if real_mean else '-'}（{len(real_scores)} 篇）\n")

    rows = []
    def solve_check(it):
        d = it["data"]
        qs = d.get("questions") or []
        if not qs:
            return None
        body = "文章：\n" + it["text"] + "\n\n题目：\n"
        for q in qs:
            body += f'{q.get("no")}. {q.get("stem")}\n' + "\n".join(q.get("options") or []) + "\n"
        got = jp(cb(SOLVE + body))
        mine = {int(g.get("no")): str(g.get("answer") or "").upper()[:1] for g in got if g.get("no")}
        wrong = [int(q["no"]) for q in qs if mine.get(int(q["no"])) != str(q.get("answer")).upper()[:1]]
        return wrong

    with ThreadPoolExecutor(max_workers=3) as ex:
        wrongs = list(ex.map(solve_check, [it for it in items if it["group"] == "mock"]))

    for it, wrong in zip([it for it in items if it["group"] == "mock"], wrongs):
        s = score_of(it["id"])
        rows.append({"label": it["label"], "file": it["file"], "score": s,
                     "delta": (s - real_mean) if (s is not None and real_mean is not None) else None,
                     "solve_wrong": wrong})
    rows.sort(key=lambda r: (-(r["score"] or 0)))

    print(f"{'产线':22} {'真题感':>6} {'比真题':>7} {'盲做不符':>10}")
    for r in rows:
        s = f'{r["score"]:.2f}' if r["score"] is not None else "-"
        dd = f'{r["delta"]:+.2f}' if r["delta"] is not None else "-"
        w = "无题目" if r["solve_wrong"] is None else f'{len(r["solve_wrong"])} 题'
        print(f"{r['label']:22} {s:>6} {dd:>7} {w:>10}")
    (OUT / "line-compare.json").write_text(json.dumps({"real_mean": real_mean, "rows": rows}, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    print("\n明细:", OUT / "line-compare.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
