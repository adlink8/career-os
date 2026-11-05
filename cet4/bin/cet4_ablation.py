# -*- coding: utf-8 -*-
"""逐块消融：拿一份官方真题，每次只把其中一块换成我们的机器产物，
再问评委「这两份，哪一份更像官方真题」。

如果某一块被换掉后评委就稳定选未改动那份，说明**该块是决定性线索**。

块：Section C 正文 / 选词填空 / 信息匹配 / 翻译 / 写作

用法: python cet4/bin/cet4_ablation.py --reals 2 --mock 81 --judges 2
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
import math
import random
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "var" / "cet4-daily" / "line-compare"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

sys.path.insert(0, str(ROOT / "bin"))
import cet4_uniform_render as U  # type: ignore

PROMPT = """下面是两份大学英语四级试卷的摘录，都是同一份官方真题，但**其中一份的某一部分被替换成了模拟卷的内容**。
请判断：**哪一份更接近未被动过的官方真题**（即哪一份的「真题感」更强）。
只看命题写法与语言质量，不要因为读到眼熟内容就选它。
只输出 JSON：{"real":"A 或 B","reason":"<=20字"}

=== A ===
{a}

=== B ===
{b}
"""

BLOCKS = ["cloze", "match", "reading", "translation", "writing"]


def cb(prompt: str, timeout: int = 1800) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def parse(t: str) -> dict:
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", t or ""):
        try:
            o, _ = dec.raw_decode(t[m.start():])
            if isinstance(o, dict):
                return o
        except json.JSONDecodeError:
            continue
    return {}


def wilson(k: int, n: int):
    if not n:
        return (0.0, 1.0)
    p = k / n
    z = 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0, c - h) * 100, 1), round(min(1, c + h) * 100, 1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reals", type=int, default=2)
    ap.add_argument("--mock", default="81")
    ap.add_argument("--judges", type=int, default=2)
    args = ap.parse_args()

    reals = U.all_reals(args.reals)
    mocks = [U.from_paper(p) for p in args.mock.split(",")]
    mocks = [m for m in mocks if m]
    if not reals or not mocks:
        print("材料不足"); return 1
    print(f"真题 {len(reals)} 份 / 模拟 {len(mocks)} 份；每种替换比 {len(reals)*len(BLOCKS)} 组")

    trials = []
    for ri, r in enumerate(reals):
        for bi, blk in enumerate(BLOCKS):
            m = mocks[(ri + bi) % len(mocks)]
            ab = json.loads(json.dumps(r))
            ab[blk] = json.loads(json.dumps(m[blk]))
            swap = random.Random(1000 + ri * 10 + bi).random() < 0.5
            a, b = (ab, r) if swap else (r, ab)
            trials.append({"real": r["src"], "block": blk,
                           "a": U.render(a), "b": U.render(b),
                           "truth": "A" if swap else "B",   # 未改动那份的位置
                           "which": "A" if swap else "B"})

    def one(t):
        res = parse(cb(PROMPT.replace("{a}", t["a"]).replace("{b}", t["b"])))
        g = str(res.get("real") or "").strip().upper()[:1]
        if g not in ("A", "B"):
            m = re.search(r"\b([AB])\b", PROMPT)
            g = ""
        # 判"未改动那份更像真题" = 该块是决定性线索
        decisive = (g == t["which"])
        return {**{k: t[k] for k in ("real", "block", "which")}, "guess": g, "decisive": decisive,
                "reason": res.get("reason") or ""}

    with ThreadPoolExecutor(max_workers=args.judges) as ex:
        rows = []
        for chunk in ex.map(lambda k: [one(t) for t in trials], range(args.judges)):
            rows.extend(chunk)

    agg = {}
    for blk in BLOCKS:
        sub = [r for r in rows if r["block"] == blk and r["guess"] in ("A", "B")]
        k = sum(1 for r in sub if r["decisive"])
        agg[blk] = (k, len(sub))
    print(f"\n{'被替换的块':12} {'判出「未改动更像真题」':>20} {'比例':>7}  CI")
    for blk, (k, n) in sorted(agg.items(), key=lambda x: -(x[1][0] / max(1, x[1][1]))):
        lo, hi = wilson(k, n)
        print(f"{blk:12} {k:>10}/{n:<8} {round(100*k/max(1,n),1):>6}%  {lo}–{hi}%")
    print("\n判读：比例越高 = 该块越容易暴露；≈50% = 该块不是决定性线索")
    for r in rows:
        if r["decisive"]:
            print(f'  [{r["block"]}] {r["reason"]}')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ablation.json").write_text(json.dumps({"rows": rows, "agg": agg}, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
