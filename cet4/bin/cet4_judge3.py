# -*- coding: utf-8 -*-
"""三评委多数投票的判别实验（降低单一评委 ~20% 噪声）。

每场：一次把全部材料匿名投给一位评委，每篇判「真题 / 模拟」。
三位评委看不同顺序 → 每篇取多数票。同时报告评委间一致率（越一致越可信）。

用法: python cet4/bin/cet4_judge3.py [--glob "set-4[1-8].json"] [--n-real 10] [--judges 3]
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
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "var" / "cet4-daily" / "ten-sets"
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
OUT = ROOT / "var" / "cet4-daily" / "discriminate"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """你是大学英语四级命题组成员。下面每段是四级阅读文章正文（约 350 词），**部分是历年官方真题，部分是模拟题**。
逐段判断它更可能是哪一种，并给依据。

判据提示：用词具体性、句长起伏、段落长短、叙事是否完整、有无反思落点、信源是否具名。

只输出 JSON 数组：
[{"id":"S1","guess":"真题|模拟","confidence":1-3,"reason":"<=20字"}]

材料：
<<<ITEMS>>>"""


def cb(prompt: str, timeout: int = 3000) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jparse(txt: str):
    t = re.sub(r"^```(?:json)?\s*", "", (txt or "").strip())
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("["), t.rfind("]")
    if i < 0 or j <= i:
        return []
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return []


def mock_items(pattern: str) -> list:
    files = []
    for pat in pattern.split("|"):
        files.extend(sorted(SRC.glob(pat)))
    files = [f for f in files if re.fullmatch(r"set-\d{2}\.json", f.name)]
    out = []
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        p = (d.get("passage") or "").strip()
        if p:
            out.append({"id": f"M{f.stem.split('-')[1]}", "text": p, "group": "mock", "src": f.name})
    return out


def real_items(n: int, seed: int = 41) -> list:
    pool = []
    for md in sorted(BANK.rglob("*.md")):
        t = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
            body = t[m.end():]
            body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
            cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
            p = re.sub(r"[_*#]", "", (body[:cut.start()] if cut else "")[:4000]).strip()
            if 320 <= len(p.split()) <= 390:
                pool.append(p)
    picked = random.Random(seed).sample(pool, min(n, len(pool)))
    return [{"id": f"R{i:02d}", "text": t, "group": "real", "src": "真题"} for i, t in enumerate(picked, 1)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="set-4[1-8].json")
    ap.add_argument("--n-real", type=int, default=10)
    ap.add_argument("--judges", type=int, default=3)
    ap.add_argument("--tag", default="judge3")
    args = ap.parse_args()

    items = mock_items(args.glob) + real_items(args.n_real)
    truth = {it["id"]: ("模拟" if it["group"] == "mock" else "真题") for it in items}
    print(f"材料：模拟 {sum(1 for i in items if i['group']=='mock')} + 真题 {sum(1 for i in items if i['group']=='real')}，评委 {args.judges} 位")

    def judge(k: int):
        order = list(items)
        random.Random(1000 + k).shuffle(order)
        body = "\n\n=====\n\n".join(f'[{it["id"]}]\n{it["text"]}' for it in order)
        got = jparse(cb(PROMPT.replace("<<<ITEMS>>>", body)))
        print(f"  评委{k}: {len(got)}/{len(order)}", flush=True)
        return {str(g.get("id")): str(g.get("guess") or "").strip() for g in got if g.get("id")}

    with ThreadPoolExecutor(max_workers=args.judges) as ex:
        votes = list(ex.map(judge, range(args.judges)))

    rows = []
    for it in items:
        vs = [v.get(it["id"], "") for v in votes]
        valid = [v for v in vs if v in ("真题", "模拟")]
        majority = max(set(valid), key=valid.count) if valid else ""
        rows.append({"id": it["id"], "group": it["group"], "truth": truth[it["id"]],
                     "votes": vs, "majority": majority, "right": majority == truth[it["id"]],
                     "agree": len(set(valid)) == 1 if valid else False})
    (OUT / f"{args.tag}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    def stat(g):
        gs = [r for r in rows if r["group"] == g]
        return sum(1 for r in gs if r["right"]), len(gs)
    mo, mn = stat("mock")
    ro, rn = stat("real")
    agree = sum(1 for r in rows if r["agree"])
    print(f"\n模拟被判对（识破）: {mn-mo}/{mn} = {100*(mn-mo)/max(1,mn):.0f}%   模拟通过率 {100*mo/max(1,mn):.0f}%")
    print(f"真题被判对: {ro}/{rn} = {100*ro/max(1,rn):.0f}%")
    print(f"总体准确率: {(mo+ro)}/{mn+rn} = {100*(mo+ro)/max(1,mn+rn):.1f}%（50% = 分不出来）")
    print(f"三评委完全一致: {agree}/{len(rows)} = {100*agree/max(1,len(rows)):.0f}%")
    for r in rows:
        if r["group"] == "mock":
            print(f'  {r["id"]} 票={"/".join(r["votes"])} 多数={r["majority"]}')
    print("明细:", OUT / f"{args.tag}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
