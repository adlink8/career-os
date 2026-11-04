# -*- coding: utf-8 -*-
"""v5 链路收口：审查→回灌修复→复审→盲做，一次跑完并记账。

命名：输入 set-XX.s1.json（scrub 后稿）
     review1  set-XX.s1.review.json
     repair   set-XX.s2.json
     review2  set-XX.s2.review.json
     solve    set-XX.s2.solve.json

用法: python cet4/bin/cet4_chain_v5.py --glob "set-8[1-7].s1.json" [--workers 3]
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
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "var" / "cet4-daily" / "ten-sets"
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

REVIEW = """你是四级命题组的独立审查员，只审查不改写。下面先给 3 篇真题正文作为难度与文体基线，再给一篇待审模拟阅读（正文+5题+解析）。

审查维度：难度是否同档、语言是否地道、5 题是否唯一解、答案与解析是否自洽。
输出 JSON：
{"verdict":"pass|needs_revision","band":"1-5","findings":[{"severity":"blocker|high|medium|low","where":"...","problem":"...","must_fix":"..."}],"summary":"<=40字"}

{BASE}

=====

{PAYLOAD}"""

REPAIR = """你是这篇模拟阅读的出题人。稿子被独立审查打回，下面是意见。请逐条修正，输出完整新稿 JSON。

硬要求：正文 348-375 词、5 题、答案唯一、解析与正文一致、不编造正文没有的事实。
原稿：
{PAPER}

审查意见：
{FINDINGS}

输出 JSON：{"title":"...","passage":"...","cn":"...","questions":[{"no":46,"stem":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","why_correct":"...","opt_why":{"A":"...","B":"...","C":"...","D":"..."}}],"fix_log":["..."]}"""

SOLVE = """你是四级考生。只给文章和题目，没有答案。逐题选唯一最佳答案，理由<=20字。
只输出 JSON：[{"no":46,"answer":"A","why":"..."}]

"""


def cb(prompt: str, timeout: int = 2400) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jp(t: str, kind="{"):
    t = re.sub(r"^```(?:json)?\s*", "", (t or "").strip())
    t = re.sub(r"```$", "", t).strip()
    i, j = (t.find("{"), t.rfind("}")) if kind == "{" else (t.find("["), t.rfind("]"))
    if i < 0 or j <= i:
        return {} if kind == "{" else []
    frag = t[i:j + 1]
    for attempt in (frag, re.sub(r",\s*([}\]])", r"\1", frag)):
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            continue
    return {} if kind == "{" else []


def baseline(n=3) -> str:
    out = []
    for md in sorted(BANK.rglob("*.md")):
        t = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
            body = t[m.end():]
            body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
            cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
            p = re.sub(r"[_*#]", "", (body[:cut.start()] if cut else "")[:4000]).strip()
            if len(p.split()) >= 300:
                out.append(p)
            if len(out) >= n:
                return "\n\n---\n\n".join(f"[真题基线 {i+1}]\n{x}" for i, x in enumerate(out))
    return "\n\n---\n\n".join(out)


def paper_text(d: dict, with_ans=True) -> str:
    s = "正文：\n" + (d.get("passage") or "") + "\n\n题目：\n"
    for q in d.get("questions") or []:
        s += f'{q.get("no")}. {q.get("stem")}\n' + "\n".join(q.get("options") or []) + "\n"
        if with_ans:
            s += f'答案：{q.get("answer")}\n' + "".join(f'  {k}: {v}\n' for k, v in (q.get("opt_why") or {}).items())
    return s


def finding_text(rev: dict) -> str:
    rows = []
    for x in rev.get("findings") or []:
        rows.append(f'- [{x.get("severity")}] {x.get("where")}：{x.get("problem")} → 修法：{x.get("must_fix")}')
    return "\n".join(rows) or f'（按 summary 修：{rev.get("summary")}）'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="set-8[1-7].s1.json")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    files = []
    for pat in args.glob.split("|"):
        files.extend(sorted(SRC.glob(pat)))
    base = baseline(3)
    print(f"待跑 {len(files)} 套")

    def one(f: Path):
        d = json.loads(f.read_text(encoding="utf-8"))
        stem = f.stem
        r1p = SRC / f"{stem}.review.json"
        if r1p.exists():
            rev1 = json.loads(r1p.read_text(encoding="utf-8"))
        else:
            rev1 = jp(cb(REVIEW.replace("{BASE}", base).replace("{PAYLOAD}", paper_text(d, False))))
            r1p.write_text(json.dumps(rev1, ensure_ascii=False, indent=1), encoding="utf-8")

        out = {"stem": stem, "verdict1": rev1.get("verdict"), "band1": rev1.get("band"),
               "findings1": len(rev1.get("findings") or [])}
        if rev1.get("verdict") == "pass":
            out["verdict2"] = "pass(unchanged)"
        else:
            r2 = jp(cb(REPAIR.replace("{PAPER}", json.dumps({k: d.get(k) for k in ("title", "passage", "cn", "questions")},
                                                           ensure_ascii=False, indent=1))
                             .replace("{FINDINGS}", finding_text(rev1))))
            if not r2 or not r2.get("questions"):
                out["verdict2"] = "repair_failed"
            else:
                r2["set"] = d.get("set")
                r2["writer"] = (d.get("writer") or "") + "+repair"
                (SRC / f"{stem.split('.')[0]}.s2.json").write_text(json.dumps(r2, ensure_ascii=False, indent=1), encoding="utf-8")
                rev2 = jp(cb(REVIEW.replace("{BASE}", base).replace("{PAYLOAD}", paper_text(r2, False))))
                (SRC / f"{stem.split('.')[0]}.s2.review.json").write_text(json.dumps(rev2, ensure_ascii=False, indent=1), encoding="utf-8")
                out["verdict2"] = rev2.get("verdict")
                out["band2"] = rev2.get("band")
                out["findings2"] = len(rev2.get("findings") or [])
                sol = jp(cb(SOLVE + paper_text(r2, False)), "[")
                mine = {int(g.get("no")): str(g.get("answer") or "").upper()[:1] for g in sol if g.get("no")}
                wrong = [int(q["no"]) for q in r2.get("questions") or []
                         if mine.get(int(q["no"])) != str(q.get("answer")).upper()[:1]]
                out["solve_wrong"] = wrong
        return out

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(one, files))
    for r in results:
        print(f'  {r["stem"]}: 审1 {r["verdict1"]}(band {r["band1"]}, {r["findings1"]} 条)'
              f' → 审2 {r.get("verdict2")}(band {r.get("band2")}, {r.get("findings2")} 条)'
              f' | 盲做不符 {r.get("solve_wrong")}')
    passed = sum(1 for r in results if str(r.get("verdict2", "")).startswith("pass"))
    print(f"\n修复后通过 {passed}/{len(results)}")
    (SRC / "chain-v5-result.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
