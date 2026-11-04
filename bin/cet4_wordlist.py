# -*- coding: utf-8 -*-
"""从整卷 JSON 抽取英文词表（去重、去功能词），供单词解析标注。"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

STOP = set("""a an the and or but if then than that this these those it its they them their we you your he she his her
is are was were be been being do does did have has had will would can could may might must shall should
of to in on at for with by from as into over under about after before between during without within
not no nor so such only also very more most much many some any each every both all other another
there here what which who whom whose when where why how i me my mine our ours us him
one two three four five six seven eight nine ten first second third
""".split())


def walk_text(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("translation", "timing", "zh", "reference", "model_essay", "title_cn", "options_cn", "stem_cn"):
                continue
            walk_text(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_text(v, out)


def main():
    src = Path(sys.argv[1])
    data = json.loads(src.read_text(encoding="utf-8"))
    texts = []
    walk_text(data, texts)
    blob = " ".join(texts)
    words = re.findall(r"[A-Za-z][A-Za-z'-]+", blob.lower())
    counter = Counter(w for w in words if w not in STOP and len(w) > 2)
    items = [{"word": w, "count": c} for w, c in counter.most_common()]
    out = Path("var/cet4-daily/wordlist.json")
    out.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print("unique", len(items), "->", out)


if __name__ == "__main__":
    main()
