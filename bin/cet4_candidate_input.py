# -*- coding: utf-8 -*-
"""从候选池生成某篇 Section C 的输入文件（清正文、去页面噪声）。"""
import html
import json
import re
import sys

idx = int(sys.argv[1])
out = sys.argv[2]

c = json.load(open("var/cet4-daily/candidates-2026-11-03.json", encoding="utf-8"))
p = c["picked"][idx]
t = p["text"]
t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
t = re.sub(r"<[^>]+>", " ", t)
t = html.unescape(t)
t = re.sub(r"\s+", " ", t).strip()
# 去掉页面头部的署名/图片说明
t = re.sub(r"^(?:Image source[^.]*?\.\s*)+", "", t)
t = re.sub(r"^.*?Published \d+ \w+ ago\s*", "", t)
sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if len(s.split()) >= 6]
art = " ".join(sents)
payload = {"article": art, "title": p["title"], "source": p["source"],
           "source_url": p["url"], "words": len(art.split())}
json.dump(payload, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("words", payload["words"], "| title", p["title"][:70])
print(art[:200])
