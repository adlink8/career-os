# -*- coding: utf-8 -*-
"""把整卷里某个 Section C 抽成独立文件，供独立审查/送审。"""
# --- 四级工具根目录：相对路径统一按 cet4/ 解析（在仓库根或 cet4/ 下运行都行）---
import os as _os, sys as _sys, pathlib as _pl
_CET4_ROOT = _pl.Path(__file__).resolve().parents[1]
try:
    _os.chdir(_CET4_ROOT)
except OSError:
    pass
_sys.argv = [a[5:] if a[:5] in ("cet4/", "cet4\\") else a for a in _sys.argv]
import json
import re
import sys
from pathlib import Path

paper = json.loads(Path("var/cet4-daily/demo-whole-paper.json").read_text(encoding="utf-8"))
key = sys.argv[1]
out = Path(sys.argv[2])

sec = paper["reading"][key]
text = sec.get("passage") or " ".join(
    (p.get("en") or "") if isinstance(p, dict) else str(p) for p in (sec.get("paragraphs") or []))
obj = {"title": sec.get("title"), "passage": text,
       "paragraphs": sec.get("paragraphs"), "questions": sec.get("questions"),
       "source": sec.get("source"), "source_url": sec.get("source_url")}
out.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
print(key, "| words", len(re.findall(r"[A-Za-z][A-Za-z'-]*", text)),
      "| paras", len(sec.get("paragraphs") or []),
      "| analysed sentences", sum(len(p.get("sentences") or []) for p in (sec.get("paragraphs") or [])
                                  if isinstance(p, dict)),
      "| questions", [q.get("no") for q in sec.get("questions") or []])
print("written", out)
