# -*- coding: utf-8 -*-
"""真题基准：用官方答案给「判据」做体检（这是盲审实验的校准步骤）。

三件事：
1. solve  真考卷盲做（只给正文+题干+选项，不给答案），与官方答案比对 → 判据的解题能力基线
2. flag   真考卷「找错」（给正文+题目+官方答案），真卷本应无缺陷 → 误报率基线
3. audit  同一批真卷再交给第二位独立评委，看两人是否互相矛盾（一致性）

用法: python cet4/bin/cet4_real_baseline.py --stage solve|flag|all [--workers 3]
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
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
ANS = ROOT / "knowledge" / "cet4-bank" / "02-真题标准答案" / "cet4-answers.json"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
OUT = ROOT / "var" / "cet4-daily" / "real-baseline"
VERIFIED = {"2024.06": "cet4-2024-06", "2024.12": "cet4-2024-12",
            "2025.06": "cet4-2025-06", "2025.12": "cet4-2025-12", "2026.06": "cet4-2026-06"}

SOLVE = """你是四级考生，正在做阅读题。只给文章和题目，没有答案。
逐题选出唯一最佳答案，一句话理由（<=20 字）。只输出 JSON：
[{"no":46,"answer":"A","why":"..."}]

<<<ITEMS>>>"""

FLAG = """你是四级命题组的校审专家。下面是一篇**官方真题**阅读（正文 + 5 题 + 官方答案）。
官方真题原则上不存在答案错误，但可能有历史遗留的排版/语言瑕疵。
请只报告你**非常确信**的真实缺陷；不确定就不要报。
输出 JSON：{"defects":[{"type":"答案错|选项无唯一解|语言错误|逻辑断裂|难度偏离","where":"...","detail":"<=25字"}],"verdict":"ok|suspicious|broken"}

<<<ITEMS>>>"""


def cb(prompt: str, timeout: int = 1800) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jparse(txt: str, want="{"):
    t = re.sub(r"^```(?:json)?\s*", "", (txt or "").strip())
    t = re.sub(r"```$", "", t).strip()
    i, j = (t.find("{"), t.rfind("}")) if want == "{" else (t.find("["), t.rfind("]"))
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return None


def parse_paper(md: Path):
    """返回 [(passage_text, [(no, stem, options), ...]), ...]"""
    t = md.read_text(encoding="utf-8", errors="ignore")
    out = []
    for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
        body = t[m.end():]
        body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
        cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
        passage = re.sub(r"[_*#]", "", (body[:cut.start()] if cut else "").strip())
        rest = (body[cut.start():] if cut else "").split("####")[0]   # 别把下一篇的题算进来
        qs = []
        for qm in re.finditer(r"^\s*(\d{2})\.\s*(.+?)(?=^\s*\d{2}\.\s|\Z)", rest, flags=re.M | re.S):
            no = int(qm.group(1))
            block = re.sub(r"[_*#]", "", qm.group(2)).strip()
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            stem = lines[0] if lines else ""
            opts = [l for l in lines[1:] if re.match(r"^[A-D]\)", l)]
            if len(opts) == 4:
                qs.append((no, stem, opts))
        if len(qs) == 5 and len(passage.split()) >= 120:
            out.append((passage, qs))
    return out


def load_cases():
    keys = json.loads(ANS.read_text(encoding="utf-8"))
    cases = []
    for folder, akey in VERIFIED.items():
        entry = keys.get(akey) or {}
        for md in sorted((BANK / folder).glob("*.md")):
            stem = md.stem                     # cet4-2024-06-1
            m = re.search(r"-(\d)$", stem)
            if not m:
                continue
            setidx = str(int(m.group(1)) - 1)
            rec = entry.get(setidx) or {}
            reading = rec.get("reading") or []
            if len(reading) < 30:
                continue
            keys46 = {no: reading[no - 26] for no in range(46, 56)}
            for pi, (passage, qs) in enumerate(parse_paper(md)):
                cases.append({"id": f"{folder}-{m.group(1)}-P{pi+1}", "passage": passage,
                              "questions": qs, "keys": keys46})
    return cases


def stage_solve(workers: int, cases):
    OUT.mkdir(parents=True, exist_ok=True)

    def one(c):
        block = "文章：\n" + c["passage"] + "\n\n题目：\n" + "\n".join(
            f"{no}. {stem}\n" + "\n".join(opts) for no, stem, opts in c["questions"])
        got = jparse(cb(SOLVE.replace("<<<ITEMS>>>", block)), "[") or []
        mine = {int(g.get("no")): str(g.get("answer") or "").strip().upper()[:1] for g in got if g.get("no")}
        rows = [{"no": no, "key": c["keys"].get(no), "model": mine.get(no), "ok": mine.get(no) == c["keys"].get(no)}
                for no, _, _ in c["questions"]]
        (OUT / f'{c["id"]}.solve.json').write_text(json.dumps({"id": c["id"], "rows": rows}, ensure_ascii=False, indent=1),
                                                   encoding="utf-8")
        right = sum(1 for r in rows if r["ok"])
        return f'{c["id"]} {right}/{len(rows)}'

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for msg in ex.map(one, cases):
            print(" ", msg, flush=True)


def stage_flag(workers: int, cases):
    OUT.mkdir(parents=True, exist_ok=True)

    def one(c):
        block = "文章：\n" + c["passage"] + "\n\n题目与官方答案：\n" + "\n".join(
            f"{no}. {stem}\n" + "\n".join(opts) + f"\n官方答案：{c['keys'].get(no)}"
            for no, stem, opts in c["questions"])
        res = jparse(cb(FLAG.replace("<<<ITEMS>>>", block))) or {}
        (OUT / f'{c["id"]}.flag.json').write_text(json.dumps({"id": c["id"], **res}, ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
        return f'{c["id"]} verdict={res.get("verdict")} defects={len(res.get("defects") or [])}'

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for msg in ex.map(one, cases):
            print(" ", msg, flush=True)


def summarize():
    solves = sorted(OUT.glob("*.solve.json"))
    flags = sorted(OUT.glob("*.flag.json"))
    if solves:
        tot = ok = 0
        per = {}
        for f in solves:
            d = json.loads(f.read_text(encoding="utf-8"))
            r = sum(1 for x in d["rows"] if x["ok"])
            tot += len(d["rows"])
            ok += r
            per[d["id"]] = (r, len(d["rows"]))
        print(f"\n【真卷盲做】{ok}/{tot} = {100*ok/max(1,tot):.1f}%")
        for k, v in per.items():
            print(f"  {k}: {v[0]}/{v[1]}")
    if flags:
        n = len(flags)
        flagged = [f for f in flags if (json.loads(f.read_text(encoding='utf-8')).get("defects") or [])]
        types = {}
        for f in flagged:
            for d in json.loads(f.read_text(encoding="utf-8")).get("defects") or []:
                types[d.get("type")] = types.get(d.get("type"), 0) + 1
        print(f"\n【真卷误报】{len(flagged)}/{n} 篇被判有缺陷 = {100*len(flagged)/max(1,n):.1f}%")
        print("  缺陷类型分布:", types)
    (OUT / "summary.json").write_text(json.dumps({"solves": len(solves), "flags": len(flags)}, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["solve", "flag", "sum", "all"])
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    cases = load_cases()
    print(f"官方答案覆盖的真卷 reading 篇目: {len(cases)}")
    if args.stage in ("solve", "all"):
        stage_solve(args.workers, cases)
    if args.stage in ("flag", "all"):
        stage_flag(args.workers, cases)
    if args.stage in ("sum", "all"):
        summarize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
