# -*- coding: utf-8 -*-
"""以假乱真判别实验：把模拟正文与真题正文匿名混排，让独立评委二选一判断来源。

指标：
  总体准确率（越接近 50% 越说明「分不出来」）
  模拟被识破率（模型被认成真题的比例 = 1 - 识破率）
  真题被误判率
用法: python cet4/bin/cet4_discriminate.py [--round 3] [--n-real 10] [--batch 5]
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

PROMPT = """你是大学英语四级命题组成员，正在做一次盲测。
下面每段英文都是一篇四级阅读文章正文（约 350 词）。其中**一部分是历年官方真题，一部分是模拟题**。
请逐段判断它更像是「真题」还是「模拟」，并给依据。

判据提示（不要过度依赖单一特征）：
- 用词：真题偏爱中性书面语与具体名词，模拟容易出现抽象名词堆叠或过度整齐的连接词
- 句式：真题的句子长短混杂、偶有冗余修饰；模拟容易句式均匀
- 内容：真题常有具体机构/年份/数字与略显随意的插入语；模拟容易泛泛而谈
- 衔接：真题段落推进常有跳跃；模拟容易"总-分-总"过于完整

只输出 JSON 数组：
[{"id":"S1","guess":"真题|模拟","confidence":1-3,"reason":"<=20字"}]

待判断：
<<<ITEMS>>>"""


def cb(prompt: str, timeout: int = 2400) -> str:
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


def mock_items(round_no: int) -> list:
    files = sorted(SRC.glob(f"set-*.r{round_no}.json")) if round_no > 1 else sorted(SRC.glob("set-*.json"))
    files = [f for f in files if not re.search(r"\.(review|solve|flag|v\d)", f.name)]
    out = []
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        p = (d.get("passage") or "").strip()
        if p:
            out.append({"id": f"M{f.stem.split('.')[0].split('-')[1]}", "text": p, "group": "mock", "src": f.name})
    return out


def real_items(n: int, seed: int = 21) -> list:
    pool = []
    for md in sorted(BANK.rglob("*.md")):
        t = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
            body = t[m.end():]
            body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
            cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
            p = re.sub(r"[_*#]", "", (body[:cut.start()] if cut else "")[:4000]).strip()
            if 300 <= len(p.split()) <= 400:
                pool.append(p)
    picked = random.Random(seed).sample(pool, min(n, len(pool)))
    return [{"id": f"R{i:02d}", "text": t, "group": "real", "src": "真题"} for i, t in enumerate(picked, 1)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=3)
    ap.add_argument("--n-real", type=int, default=10)
    ap.add_argument("--batch", type=int, default=5)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    items = mock_items(args.round) + real_items(args.n_real)
    random.Random(2027).shuffle(items)
    print(f"材料：模拟 {sum(1 for i in items if i['group']=='mock')} + 真题 {sum(1 for i in items if i['group']=='real')}")
    OUT.mkdir(parents=True, exist_ok=True)

    def one(chunk):
        body = "\n\n=====\n\n".join(f'[{it["id"]}]\n{it["text"]}' for it in chunk)
        got = jparse(cb(PROMPT.replace("<<<ITEMS>>>", body)))
        print(f"  batch {chunk[0]['id']}..{chunk[-1]['id']}: {len(got)}/{len(chunk)}", flush=True)
        return {str(g.get("id")): g for g in got if g.get("id")}

    chunks = [items[i:i + args.batch] for i in range(0, len(items), args.batch)]
    res = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for got in ex.map(one, chunks):
            res.update(got)

    rows = []
    for it in items:
        g = res.get(it["id"]) or {}
        guess = str(g.get("guess") or "").strip()
        truth = "模拟" if it["group"] == "mock" else "真题"
        rows.append({"id": it["id"], "group": it["group"], "src": it["src"], "guess": guess,
                     "right": guess == truth, "confidence": g.get("confidence"), "reason": g.get("reason")})
    (OUT / f"discriminate-r{args.round}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    def rate(g):
        gs = [r for r in rows if r["group"] == g]
        ok = sum(1 for r in gs if r["right"])
        return ok, len(gs)
    mo, mn = rate("mock")
    ro, rn = rate("real")
    total_ok, total_n = mo + ro, mn + rn
    print(f"\n模拟被判对（=被识破）: {mn - mo}/{mn}  识别率 {100*(mn-mo)/max(1,mn):.0f}%")
    print(f"真题被判对: {ro}/{rn}  {100*ro/max(1,rn):.0f}%")
    print(f"总体准确率: {total_ok}/{total_n} = {100*total_ok/max(1,total_n):.1f}%（50% = 完全分不出来）")
    for r in rows:
        if r["group"] == "mock":
            print(f'  {r["id"]} 判{r["guess"] or "?"} 信{r["confidence"]} {r["reason"]}')
    print("明细:", OUT / f"discriminate-r{args.round}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
