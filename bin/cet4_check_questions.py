# -*- coding: utf-8 -*-
"""换入前核对：题号/答案分布/证据在正文/选项长度差。"""
import json
import re
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
passage = d.get("passage") or ""
qs = d.get("questions") or []
print("questions:", [q.get("no") for q in qs], "| answers:", [q.get("answer") for q in qs])
print("distinct answers:", len({q.get("answer") for q in qs}))
for q in qs:
    lens = [len(o.split()) for o in q.get("options") or []]
    ev = q.get("evidence") or ""
    inpass = ev and ev[:60] in passage
    print(f"  {q['no']} {q['answer']} len={lens} diff={max(lens) - min(lens)} "
          f"evidence_in_passage={bool(inpass)} | {q['stem'][:70]}")
