# -*- coding: utf-8 -*-
"""配对二选一评测：每次给评委一份模拟卷档案 + 一份真题档案，问「哪一份是官方真题」。

为什么不用 1-5 打分：2026-11-05 实测该指标单份噪声 ±0.46、组均值噪声 ±0.47，
第 1 次评测甚至出现「模拟 4.67 > 真题 3.83」的反向结果 —— 0.5 分以内的涨跌全是噪声。
配对二选一是二元结果，可以用二项分布给置信区间，分辨率高得多。

判读：
  正确率 ≈ 50%  → 分不出来（达标）
  正确率 ≥ 80%  → 专家仍能稳定认出
  报告同时给 Wilson 95% 置信区间。

用法: python cet4/bin/cet4_paired_choice.py --mock 81,84,97 --real 3 --trials 10 --judges 2
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
import cet4_paper_auth as A  # type: ignore

FRAMINGS = {
    "f1": """两段材料，一段是**官方四级真题**的试卷摘录，另一段是**模拟卷**的摘录。
请判断哪一段是官方真题。只能二选一，不要含糊。
只输出 JSON：{"real":"A 或 B","confidence":1-3,"reason":"<=20字"}""",
    "f2": """两段材料都是大学英语四级试卷的摘录（选词填空开头与词库、匹配陈述、阅读题干、翻译、写作要求）。
请判断**哪一段的写法更像一份真实的四级试卷**——只看命题写法与语言质量，
不要因为某段读起来眼熟（像是见过的旧真题）就选它。
只输出 JSON：{"real":"A 或 B","confidence":1-3,"reason":"<=20字"}""",
}

PROMPT = """{framing}

=== A ===
{a}

=== B ===
{b}
"""


def cb(prompt: str, timeout: int = 1800) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


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
    ap.add_argument("--real", type=int, default=3)
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--judges", type=int, default=2)
    ap.add_argument("--framing", default="f1", choices=["f1", "f2"], help="f1=哪份是官方真题；f2=哪份更像真题")
    args = ap.parse_args()

    pids = [x for x in re.split(r"[,\s]+", args.mock) if x]
    mocks = {p: A.mock_profile(p) for p in pids}
    reals = {f"R{i+1}": t for i, t in enumerate(A.real_profiles(args.real))}
    print(f"模拟 {len(mocks)} 份 / 真题 {len(reals)} 份，计划 {args.trials} 组 × {args.judges} 评委")

    rng = random.Random(20261105)
    trials = []
    for t in range(args.trials):
        pid = pids[t % len(pids)]
        rid = list(reals)[t % len(reals)]
        swap = rng.random() < 0.5
        a, b = (reals[rid], mocks[pid]) if swap else (mocks[pid], reals[rid])
        truth = "A" if swap else "B"          # swap=True 时 a 放的是真题，故真题在 A
        trials.append({"no": t + 1, "mock": pid, "real": rid, "a": a, "b": b, "truth": truth})

    def judge(k: int):
        out = []
        for tr in trials:
            text = cb(PROMPT.replace("{framing}", FRAMINGS[args.framing])
                              .replace("{a}", tr["a"]).replace("{b}", tr["b"]))
            res = A.jp(text)
            if isinstance(res, list):
                res = res[0] if res and isinstance(res[0], dict) else {}
            if not isinstance(res, dict):
                res = {}
            guess = str(res.get("real") or "").strip().upper()[:1]
            if guess not in ("A", "B"):
                m = re.search(r"\b([AB])\b", text)
                guess = m.group(1) if m else ""
            out.append({"trial": tr["no"], "guess": guess, "truth": tr["truth"],
                        "ok": guess == tr["truth"], "conf": res.get("confidence"),
                        "reason": res.get("reason") or text[:40].replace("\n", " ")})
        return out

    with ThreadPoolExecutor(max_workers=args.judges) as ex:
        results = list(ex.map(judge, range(args.judges)))

    rows = [r for js in results for r in js]
    n = len([r for r in rows if r["guess"] in ("A", "B")])
    k = len([r for r in rows if r["ok"]])
    lo, hi = wilson(k, n)
    print(f"\n识别正确率 {k}/{n} = {round(100*k/max(1,n),1)}%  （95% CI {lo}%–{hi}%）")
    for j, js in enumerate(results):
        jk = len([r for r in js if r["ok"]]); jn = len([r for r in js if r["guess"] in ("A", "B")])
        print(f"  评委{j+1}: {jk}/{jn}")
    print("判读：≈50% = 分不出来（达标）；≥80% = 专家仍能稳定认出")
    for r in rows[:6]:
        print(f"  第{r['trial']}组 判{r['guess']} 真值{r['truth']} {'✓' if r['ok'] else '✗'} {r.get('reason')}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"paired-choice-{args.framing}.json").write_text(json.dumps({"rows": rows, "accuracy": round(k / max(1, n), 3),
                                                        "ci": [lo, hi]}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
