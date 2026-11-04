# -*- coding: utf-8 -*-
"""统一渲染器版配对评测：两侧都过同一个模板，只比内容写法。

用法: python cet4/bin/cet4_paired_uniform.py --mock 81,84,97 --reals 5 --trials 30 --judges 2 --framing f2
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

FRAMINGS = {
    "f1": "两段材料都是四级试卷摘录，其中一段是**官方真题**，另一段是模拟卷。请指出哪一段是官方真题。",
    "f2": ("两段材料都是四级试卷摘录。请判断**哪一段的写法更像一份真实的四级试卷**——"
           "只看命题写法与语言质量，不要因为某段读起来眼熟（像是见过的旧真题）就选它。"),
}

PROMPT = """{framing}
只能二选一。只输出 JSON：{{"real":"A 或 B","confidence":1-3,"reason":"<=20字"}}

=== A ===
{a}

=== B ===
{b}
"""


def cb(prompt: str, timeout: int = 1800) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def parse(text: str) -> dict:
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", text or ""):
        try:
            obj, _ = dec.raw_decode(text[m.start():])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return {}


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, c - h) * 100, 1), round(min(1.0, c + h) * 100, 1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="81,84,97")
    ap.add_argument("--reals", type=int, default=5)
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--judges", type=int, default=2)
    ap.add_argument("--framing", default="f2", choices=["f1", "f2"])
    args = ap.parse_args()

    pids = [x for x in re.split(r"[,\s]+", args.mock) if x]
    mocks = {}
    for p in pids:
        prof = U.from_paper(p)
        if prof:
            mocks[p] = U.render(prof)
    reals = {r["src"]: U.render(r) for r in U.all_reals(args.reals)}
    print(f"统一渲染：模拟 {len(mocks)} 份（{len(next(iter(mocks.values())))} 字）/ 真题 {len(reals)} 份")

    rng = random.Random(20261106)
    mids = list(mocks)
    rids = list(reals)
    trials = []
    for t in range(args.trials):
        mk = mids[t % len(mids)]
        rk = rids[(t // max(1, len(mids))) % len(rids)]
        swap = rng.random() < 0.5
        a, b = (reals[rk], mocks[mk]) if swap else (mocks[mk], reals[rk])
        trials.append({"no": t + 1, "mock": mk, "real": rk, "a": a, "b": b,
                       "truth": "A" if swap else "B"})

    def judge(k: int):
        rows = []
        for tr in trials:
            text = cb(PROMPT.replace("{framing}", FRAMINGS[args.framing])
                            .replace("{a}", tr["a"]).replace("{b}", tr["b"]))
            res = parse(text)
            g = str(res.get("real") or "").strip().upper()[:1]
            if g not in ("A", "B"):
                m = re.search(r"\b([AB])\b", text)
                g = m.group(1) if m else ""
            rows.append({"trial": tr["no"], "guess": g, "truth": tr["truth"], "ok": g == tr["truth"],
                         "reason": res.get("reason") or ""})
        return rows

    with ThreadPoolExecutor(max_workers=args.judges) as ex:
        results = list(ex.map(judge, range(args.judges)))
    rows = [r for js in results for r in js]
    n = len([r for r in rows if r["guess"] in ("A", "B")])
    k = len([r for r in rows if r["ok"]])
    lo, hi = wilson(k, n)
    print(f"\n识别正确率 {k}/{n} = {round(100*k/max(1,n),1)}%  95% CI {lo}%–{hi}%")
    for j, js in enumerate(results):
        jk = len([r for r in js if r["ok"]]); jn = len([r for r in js if r["guess"] in ("A","B")])
        print(f"  评委{j+1}: {jk}/{jn}")
    bad = [r for r in rows if not r["ok"]]
    print(f"\n模拟被判更像真题 {len(bad)} 次；其中理由样本：")
    for r in bad[:6]:
        print("  -", r["reason"])
    ok_r = [r for r in rows if r["ok"]]
    print("\n判对（认出真题）理由样本：")
    for r in ok_r[:6]:
        print("  -", r["reason"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"paired-uniform-{args.framing}.json").write_text(
        json.dumps({"rows": rows, "accuracy": round(k / max(1, n), 3), "ci": [lo, hi],
                    "framing": args.framing}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
