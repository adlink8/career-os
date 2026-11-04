# -*- coding: utf-8 -*-
"""从整卷 JSON 抽取英文词表（覆盖全部单词，含功能词），供单词解析标注。"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

SKIP_KEYS = ("translation", "timing", "zh", "reference", "model_essay",
             "title_cn", "options_cn", "stem_cn", "cn", "chunks", "ipa", "pos")


def walk_text(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in SKIP_KEYS:
                continue
            walk_text(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_text(v, out)


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "var/cet4-daily/demo-whole-paper.json")
    data = json.loads(src.read_text(encoding="utf-8"))
    texts: list[str] = []
    walk_text(data, texts)
    blob = " ".join(texts)
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", blob.lower())
    counter = Counter(words)
    items = [{"word": w, "count": c} for w, c in counter.most_common()]
    out = Path("var/cet4-daily/wordlist.json")
    out.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print("unique", len(items), "->", out)


if __name__ == "__main__":
    main()
