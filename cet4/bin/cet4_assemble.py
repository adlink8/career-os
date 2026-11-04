# -*- coding: utf-8 -*-
"""把六类单题拼成一整套 57 题卷（结构校验用）。"""
from __future__ import annotations

# --- 四级工具根目录：相对路径统一按 cet4/ 解析（在仓库根或 cet4/ 下运行都行）---
import os as _os, sys as _sys, pathlib as _pl
_CET4_ROOT = _pl.Path(__file__).resolve().parents[1]
try:
    _os.chdir(_CET4_ROOT)
except OSError:
    pass
_sys.argv = [a[5:] if a[:5] in ("cet4/", "cet4\\") else a for a in _sys.argv]
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / "var" / "cet4-daily" / "design" / "samples"
OUT = ROOT / "var" / "cet4-daily" / "demo-whole-paper.json"


def load(name):
    return json.loads((S / name).read_text(encoding="utf-8"))


def main():
    writing_t = load("transwriting-sample.json")
    listening = load("listening-sample.json")
    cloze = load("cloze-sample.json")
    match = load("match-sample.json")
    r1 = json.loads((ROOT / "var" / "cet4-daily" / "out" / "2026-11-03-01.json").read_text(encoding="utf-8"))
    r2 = load("reading2.json")

    lq = [q for s in listening["sections"] for p in s["pieces"] for q in p["questions"]]
    for q in r1["questions"]:
        q["no"] = 46 + (q["no"] - 1) % 5
    for q in r2["questions"]:
        q["no"] = 51 + (q["no"] - 1) % 5

    paper = {
        "meta": {"name": "四级整卷演示（CB 六类 agent 生成）", "date": "2026-11-04", "total": 57},
        "writing": writing_t["writing"],
        "listening": {"sections": listening["sections"], "questions": lq},
        "reading": {
            "cloze": {"passage": cloze["passage"], "bank": cloze["bank"], "answers": cloze["answers"]},
            "match": {"title": match["title"], "paragraphs": match["paragraphs"],
                      "statements": match["statements"], "answers": match["answers"]},
            "passage1": {"title": r1.get("title"), "questions": r1["questions"], "paragraphs": r1.get("paragraphs")},
            "passage2": {"title": r2.get("title"), "questions": r2["questions"], "paragraphs": r2.get("paragraphs")},
        },
        "translation": writing_t["translation"],
    }
    OUT.write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding="utf-8")
    total = 1 + len(lq) + 10 + 10 + 10 + 1
    print("listening", len(lq), "cloze", len(cloze["answers"]), "match", len(match["answers"]),
          "reading", len(r1["questions"]) + len(r2["questions"]), "total", total)


if __name__ == "__main__":
    main()
