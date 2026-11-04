# -*- coding: utf-8 -*-
"""无锚点「真题感」评分：不给"这里有一半是假的"的提示，按正常阅读体验打分。

为什么需要它：强制二选一会逼评委去找差异（对抗任务，必然 100% 找到），
但真实使用场景是「学生拿到卷子读」，没有对照组。两个指标要分开看：
  - 对抗判别（cet4_judge3.py）：测"有没有可被专家定位的痕迹"
  - 无锚点评分（本脚本）：测"读者层面像不像真题"

用法: python cet4/bin/cet4_authenticity.py --glob "set-8[1-7].json" --n-real 10 --judges 3
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
OUT = ROOT / "var" / "cet4-daily" / "discriminate"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """下面是 20 段英语短文（每段约 350 词），都是大学英语四级阅读级别的文章，来源不一。
请**逐段打分**：作为一篇四级阅读文章，它的「典型真题感」有多强（1=不像四级文章，3=一般，5=就是真题的样子）。
不用判断来源，只按阅读经验打分，并给半句理由。
只输出 JSON：[{"id":"X01","score":4,"reason":"<=18字"}]

"""


def cb(prompt: str, timeout: int = 2400) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jparse_list(txt: str):
    t = re.sub(r"^```(?:json)?\s*", "", (txt or "").strip())
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("["), t.rfind("]")
    if i < 0 or j <= i:
        return []
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return []


def load_items(pattern: str, n_real: int, seed: int) -> list:
    mock = []
    files = []
    for pat in pattern.split("|"):
        files.extend(sorted(SRC.glob(pat)))
    for f in [f for f in files if re.fullmatch(r"set-\d{2}\.json", f.name)]:
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("passage"):
            mock.append((f"M{f.stem.split('-')[1]}", d["passage"], "mock"))
    real = []
    for md in sorted(BANK.rglob("*.md")):
        t = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
            body = t[m.end():]
            body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
            cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
            p = re.sub(r"[_*#]", "", (body[:cut.start()] if cut else "")[:4000]).strip()
            if 330 <= len(p.split()) <= 390:
                real.append(p)
    random.Random(seed).shuffle(real)
    items = [(f"R{i:02d}", x, "real") for i, x in enumerate(real[:n_real], 1)] + mock
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="set-8[1-7].json")
    ap.add_argument("--n-real", type=int, default=10)
    ap.add_argument("--judges", type=int, default=3)
    ap.add_argument("--tag", default="no-anchor")
    args = ap.parse_args()

    items = load_items(args.glob, args.n_real, seed=7)
    print(f"材料：真题 {sum(1 for i in items if i[2]=='real')} + 模拟 {sum(1 for i in items if i[2]=='mock')}")

    def judge(k: int):
        order = list(items)
        random.Random(400 + k).shuffle(order)
        body = "\n\n=====\n\n".join(f"[{i}]\n{t}" for i, t, _ in order)
        data = jparse_list(cb(PROMPT + body))
        truth = {i: g for i, _, g in order}
        sc = {"real": [], "mock": []}
        for g in data:
            gid = str(g.get("id")); s = g.get("score")
            if gid in truth and isinstance(s, (int, float)):
                sc[truth[gid]].append(s)
        print(f"  评委{k}: 真题均值 {round(st.mean(sc['real']),2) if sc['real'] else '-'} "
              f"模拟均值 {round(st.mean(sc['mock']),2) if sc['mock'] else '-'} "
              f"模拟≥4 {sum(1 for s in sc['mock'] if s >= 4)}/{len(sc['mock'])}", flush=True)
        return sc

    with ThreadPoolExecutor(max_workers=args.judges) as ex:
        res = list(ex.map(judge, range(args.judges)))
    (OUT / f"{args.tag}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    rm = [st.mean(r["real"]) for r in res if r["real"]]
    mm = [st.mean(r["mock"]) for r in res if r["mock"]]
    hi = [sum(1 for s in r["mock"] if s >= 4) / max(1, len(r["mock"])) for r in res if r["mock"]]
    print(f"\n三评委平均：真题 {round(st.mean(rm),2) if rm else '-'} / 模拟 {round(st.mean(mm),2) if mm else '-'}"
          f"（差 {round(st.mean(mm)-st.mean(rm),2) if rm and mm else '-'}）")
    print(f"模拟稿被判「≥4 = 就是真题的样子」比例：{round(100*st.mean(hi),0) if hi else '-'}%")
    print("明细:", OUT / f"{args.tag}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
