# -*- coding: utf-8 -*-
"""整卷装配自检（证据收集，不是通过标准）。"""
# --- 四级工具根目录：相对路径统一按 cet4/ 解析（在仓库根或 cet4/ 下运行都行）---
import os as _os, sys as _sys, pathlib as _pl
_CET4_ROOT = _pl.Path(__file__).resolve().parents[1]
try:
    _os.chdir(_CET4_ROOT)
except OSError:
    pass
_sys.argv = [a[5:] if a[:5] in ("cet4/", "cet4\\") else a for a in _sys.argv]
import json
import os
import re
import sys

paper = json.load(open(sys.argv[1], encoding="utf-8"))
base = sys.argv[2] if len(sys.argv) > 2 else "var/cet4-daily/paper-demo/plain"
L = paper["listening"]
R = paper["reading"]

ok = True
for s in L["sections"]:
    for p in s["pieces"]:
        name = os.path.basename(p.get("audio") or "")
        exists = os.path.exists(os.path.join(base, name))
        timing = p.get("timing") or []
        script_words = len((p.get("script") or "").split())
        print(f"{s['name']} {name:10s} file={exists} timing={len(timing)} "
              f"script_words={script_words} q={len(p.get('questions') or [])}")
        ok = ok and exists and len(timing) > 0 and script_words > 60

n_obj = (len(L["questions"]) + len(R["cloze"]["answers"]) + len(R["match"]["answers"])
         + len(R["passage1"]["questions"]) + len(R["passage2"]["questions"]))
print("objective items:", n_obj, "| meta total:", paper["meta"].get("total"))
print("translation chars:", len(paper["translation"]["zh"]),
      "| writing chars:", len(paper["writing"]["directions"]))
print("ALL OK" if ok and n_obj == 55 else "GAPS FOUND")
