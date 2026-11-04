# -*- coding: utf-8 -*-
"""指标稳定性体检：同一批材料重复评测 N 次，算出噪声底线。

为什么先做这个：第 19 轮把分数从 4.07 改到 2.73 又拉回 3.87，
但如果单次评测的噪声就有 ±0.5，那这些「涨跌」根本无法用来判断改动好坏。
先把噪声测出来，之后所有改动都要超过噪声才算数。

用法: python cet4/bin/cet4_metric_noise.py --mock 81,84,97 --real 3 --judges 2 --reps 3
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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "cet4" / "bin"
OUT = ROOT / "var" / "cet4-daily" / "line-compare"

sys.path.insert(0, str(SRC))
import cet4_paper_auth as A  # type: ignore


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="81,84,97")
    ap.add_argument("--real", type=int, default=3)
    ap.add_argument("--judges", type=int, default=2)
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()

    items = [{"id": f"M{p}", "text": A.mock_profile(p), "group": "mock"}
             for p in [x for x in re.split(r"[,\s]+", args.mock) if x]]
    items += [{"id": f"R{i}", "text": t, "group": "real"} for i, t in enumerate(A.real_profiles(args.real), 1)]

    runs = []
    for rep in range(args.reps):
        scores = {it["id"]: [] for it in items}
        for k in range(args.judges):
            order = list(items)
            random.Random(7000 + rep * 10 + k).shuffle(order)
            body = "\n\n=====\n\n".join(f"[{it['id']}]\n{it['text']}" for it in order)
            for g in A.jp(A.cb(A.PROMPT + body)):
                gid = str(g.get("id"))
                if gid in scores and isinstance(g.get("score"), (int, float)):
                    scores[gid].append(g["score"])
        per = {k: round(st.mean(v), 2) if v else None for k, v in scores.items()}
        mock = [v for k, v in per.items() if k.startswith("M") and v is not None]
        real = [v for k, v in per.items() if k.startswith("R") and v is not None]
        runs.append({"rep": rep, "per_item": per,
                     "mock_mean": round(st.mean(mock), 2) if mock else None,
                     "real_mean": round(st.mean(real), 2) if real else None})
        print(f"  第 {rep+1} 次：模拟 {runs[-1]['mock_mean']} / 真题 {runs[-1]['real_mean']}", flush=True)

    mock_series = [r["mock_mean"] for r in runs if r["mock_mean"] is not None]
    real_series = [r["real_mean"] for r in runs if r["real_mean"] is not None]
    print(f"\n模拟组均值序列 {mock_series} → 标准差 {round(st.pstdev(mock_series), 2) if len(mock_series) > 1 else 0}")
    print(f"真题组均值序列 {real_series} → 标准差 {round(st.pstdev(real_series), 2) if len(real_series) > 1 else 0}")
    item_sd = {}
    for iid in runs[0]["per_item"]:
        vals = [r["per_item"].get(iid) for r in runs if r["per_item"].get(iid) is not None]
        if len(vals) > 1:
            item_sd[iid] = round(st.pstdev(vals), 2)
    print("\n逐份标准差（越大越不可靠）：")
    for iid, sd in sorted(item_sd.items(), key=lambda x: -x[1]):
        print(f"  {iid:5} {sd}")
    noise = round(st.mean([v for v in item_sd.values()]), 2) if item_sd else None
    print(f"\n单份平均噪声 ≈ ±{noise}；组均值噪声 ≈ ±{round(st.pstdev(mock_series),2) if len(mock_series)>1 else 0}")
    print("判读规则：改动带来的差 < 噪声 → 不算数")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "metric-noise.json").write_text(json.dumps({"runs": runs, "item_sd": item_sd, "noise": noise},
                                                      ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
