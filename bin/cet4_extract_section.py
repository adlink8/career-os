# -*- coding: utf-8 -*-
"""把整卷里某个 Section C 抽成独立文件，供独立审查/送审。"""
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
