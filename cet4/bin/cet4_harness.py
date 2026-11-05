# -*- coding: utf-8 -*-
"""固定评测台：同一套模拟卷/真题/试次/评委，每次改动都跑同一套，结果可配对比较。

要点：
- 试次表由配置文件 + 固定种子生成，**每次跑的配对完全相同**，所以两次运行可以按试次配对
- 每位评委独立判，结果按 (mock, real, trial) 记账
- `--baseline` 传入上一次结果，做 McNemar 配对检验（看改动是否真的有效）

配置文件示例（var/cet4-daily/line-compare/harness.json）：
{"mock": ["81","82","85","86","87"], "reals": 5, "trials": 40, "judges": 2,
 "seed": 20261107, "framing": "f2"}

用法:
  python cet4/bin/cet4_harness.py --tag base-2026-11-05      # 跑基线
  python cet4/bin/cet4_harness.py --tag after-fix --baseline base-2026-11-05
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

DEFAULT_CFG = {"mock": ["81", "82", "85", "86", "87"], "reals": 5, "trials": 40,
               "judges": 2, "seed": 20261107, "framing": "f2"}


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


def load_cfg() -> dict:
    p = OUT / "harness.json"
    if p.exists():
        cfg = json.loads(p.read_text(encoding="utf-8"))
        return {**DEFAULT_CFG, **cfg}
    return dict(DEFAULT_CFG)


def build_trials(cfg: dict) -> list:
    mocks, reals = {}, {}
    for pid in cfg["mock"]:
        prof = U.from_paper(pid)
        if prof:
            mocks[pid] = U.render(prof)
    for r in U.all_reals(cfg["reals"]):
        reals[r["src"]] = U.render(r)
    mid, rid = list(mocks), list(reals)
    rng = random.Random(cfg["seed"])
    trials = []
    for t in range(cfg["trials"]):
        mk = mid[t % len(mid)]
        rk = rid[(t // max(1, len(mid))) % len(rid)]
        swap = rng.random() < 0.5
        a, b = (reals[rk], mocks[mk]) if swap else (mocks[mk], reals[rk])
        trials.append({"no": t + 1, "mock": mk, "real": rk, "a": a, "b": b,
                       "truth": "A" if swap else "B"})
    return trials


def run_judge(trials: list, framing: str, k: int) -> list:
    rows = []
    for tr in trials:
        text = cb(PROMPT.replace("{framing}", FRAMINGS[framing])
                        .replace("{a}", tr["a"]).replace("{b}", tr["b"]))
        res = parse(text)
        g = str(res.get("real") or "").strip().upper()[:1]
        if g not in ("A", "B"):
            m = re.search(r"\b([AB])\b", text)
            g = m.group(1) if m else ""
        rows.append({"trial": tr["no"], "mock": tr["mock"], "real": tr["real"],
                     "judge": k, "guess": g, "truth": tr["truth"], "ok": g == tr["truth"],
                     "reason": res.get("reason") or ""})
    return rows


def mcnemar(base: list, cur: list) -> dict:
    """按 (trial, judge) 配对，统计 b=基线对/本次错、c=基线错/本次对。"""
    b = {(r["trial"], r["judge"]): r["ok"] for r in base}
    c = {(r["trial"], r["judge"]): r["ok"] for r in cur}
    common = set(b) & set(c)
    n01 = sum(1 for k in common if b[k] and not c[k])
    n10 = sum(1 for k in common if not b[k] and c[k])
    n = n01 + n10
    if n == 0:
        return {"pairs": len(common), "b": 0, "c": 0, "p": 1.0}
    # 二项检验（小样本精确）
    k = min(n01, n10)
    p = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n) * 2
    return {"pairs": len(common), "b": n01, "c": n10, "p": round(min(1.0, p), 4)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--baseline", default="")
    ap.add_argument("--trials", type=int, default=0, help="覆盖配置里的试次数")
    ap.add_argument("--judges", type=int, default=0)
    ap.add_argument("--mock-csv", default="", help="临时覆盖模拟卷列表，如 171")
    ap.add_argument("--reals", type=int, default=0)
    args = ap.parse_args()

    cfg = load_cfg()
    if args.trials:
        cfg["trials"] = args.trials
    if args.judges:
        cfg["judges"] = args.judges
    if args.mock_csv:
        cfg["mock"] = [x for x in re.split(r"[,\s]+", args.mock_csv) if x]
    if args.reals:
        cfg["reals"] = args.reals
    OUT.mkdir(parents=True, exist_ok=True)
    if not (OUT / "harness.json").exists():
        (OUT / "harness.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")

    trials = build_trials(cfg)
    print(f"固定评测台：模拟 {len(cfg['mock'])} 份 / 真题 {cfg['reals']} 份 / "
          f"{len(trials)} 组 / {cfg['judges']} 评委 / 种子 {cfg['seed']} / 问法 {cfg['framing']}")

    with ThreadPoolExecutor(max_workers=cfg["judges"]) as ex:
        results = list(ex.map(lambda k: run_judge(trials, cfg["framing"], k), range(cfg["judges"])))
    rows = [r for js in results for r in js]
    n = sum(1 for r in rows if r["guess"] in ("A", "B"))
    k = sum(1 for r in rows if r["ok"])
    lo, hi = wilson(k, n)
    print(f"\n本台基线识别率 {k}/{n} = {round(100*k/max(1,n),1)}%  95% CI {lo}%–{hi}%")

    payload = {"config": cfg, "rows": rows,
               "accuracy": round(k / max(1, n), 4), "ci": [lo, hi], "n": n, "k": k}
    path = OUT / f"harness-{args.tag}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("结果:", path)

    if args.baseline:
        bpath = OUT / f"harness-{args.baseline}.json"
        if bpath.exists():
            base = json.loads(bpath.read_text(encoding="utf-8"))
            res = mcnemar(base["rows"], rows)
            print(f"\n与基线 {args.baseline} 配对比较：共 {res['pairs']} 个配对")
            print(f"  基线对/本次错 b={res['b']}  基线错/本次对 c={res['c']}  McNemar p={res['p']}")
            print("  判读：p < 0.05 才算改动有效；否则视作噪声")
        else:
            print(f"\n找不到基线文件 {bpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
