# -*- coding: utf-8 -*-
"""学生口径验收：一次只看一份卷子，问「这是官方真题还是模拟题」。

为什么要单独做这个：之前的评测都是**对抗式**（告诉评委"这里有一半是假的"，逼他找差异），
而学生做题的场景里没有对照组，是**单份绝对判断**。
用户 2026-11-05 明确：验收口径是「学生做不出差别」，所以必须按这个场景测。

判读：
- 模拟卷被判「真题」的比例 → 学生层面的通过率（≥50% 即与真卷无异）
- 真题被判「真题」的比例 → 对照组（应接近 100%，否则说明判据本身不可靠）

用法: python cet4/bin/cet4_student_test.py --papers 81,82,83,84,85,86,87,97,98,99 --reals 10 --judges 2
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

PROMPT = """下面是一份大学英语四级试卷的摘录。请判断：**这是官方真题，还是培训机构编的模拟题？**
只看命题写法与语言质量，按你平时做题的经验判断，不要过度推理。
只输出 JSON：{"guess":"真题 或 模拟","confidence":1-3,"reason":"<=20字"}

{paper}"""


def cb(prompt: str, timeout: int = 2400) -> str:
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


def one(paper: str) -> tuple:
    text = cb(PROMPT.replace("{paper}", paper))
    res = parse(text)
    g = str(res.get("guess") or "")
    verdict = "真题" if "真题" in g else ("模拟" if "模拟" in g else "")
    return verdict, res.get("reason") or "", res.get("confidence")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", default="81,82,83,84,85,86,87,97,98,99")
    ap.add_argument("--reals", type=int, default=10)
    ap.add_argument("--judges", type=int, default=2)
    args = ap.parse_args()

    pids = [x for x in re.split(r"[,\s]+", args.papers) if x]
    mocks = {}
    for pid in pids:
        prof = U.from_paper(pid)
        if prof:
            mocks[pid] = U.render(prof)
    reals = {r["src"]: U.render(r) for r in U.all_reals(args.reals)}
    print(f"单份盲判：模拟 {len(mocks)} 份 / 真题 {len(reals)} 份 × {args.judges} 位判者，无对照组提示")

    items = [("mock", k, v) for k, v in mocks.items()] + [("real", k, v) for k, v in reals.items()]
    random.Random(20261108).shuffle(items)

    def judge_order(k: int):
        order = list(items)
        random.Random(900 + k).shuffle(order)
        out = []
        for grp, key, paper in order:
            verdict, reason, conf = one(paper)
            out.append({"group": grp, "key": key, "verdict": verdict, "reason": reason, "conf": conf})
        return out

    with ThreadPoolExecutor(max_workers=args.judges) as ex:
        allrows = [r for js in ex.map(judge_order, range(args.judges)) for r in js]

    rows = [r for r in allrows if r["verdict"]]
    mock_pass = [r for r in rows if r["group"] == "mock" and r["verdict"] == "真题"]
    mock_all = [r for r in rows if r["group"] == "mock"]
    real_pass = [r for r in rows if r["group"] == "real" and r["verdict"] == "真题"]
    real_all = [r for r in rows if r["group"] == "real"]

    mk, mn = len(mock_pass), len(mock_all)
    rk, rn = len(real_pass), len(real_all)
    lo, hi = wilson(mk, mn)
    print(f"\n模拟卷被判「真题」的比例（=学生通过率）：{mk}/{mn} = {round(100*mk/max(1,mn),1)}%  95% CI {lo}–{hi}%")
    rlo, rhi = wilson(rk, rn)
    print(f"真题被判「真题」的比例（对照组）：{rk}/{rn} = {round(100*rk/max(1,rn),1)}%  CI {rlo}–{rhi}%")

    from collections import Counter
    c = Counter(r["reason"][:24] for r in mock_all if r["verdict"] == "模拟")
    print("\n模拟被判「模拟」时给的理由（前 6）：")
    for k, v in c.most_common(6):
        print(f"  ×{v}  {k}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "student-test.json").write_text(json.dumps(
        {"rows": allrows, "mock": [mk, mn], "real": [rk, rn], "mock_ci": [lo, hi], "real_ci": [rlo, rhi]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n明细:", OUT / "student-test.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
