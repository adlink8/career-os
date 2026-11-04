# -*- coding: utf-8 -*-
"""把整卷里各阅读小节的段落结构归一化。

不同流水线产出的段落字段不一致（`en/cn/main/structure/sentences` 与 `no/topic/sentences`），
不归一化会导致渲染空白 + 整卷审查看到“正文为空”。

用法: python bin/cet4_normalize_sections.py var/cet4-daily/demo-whole-paper.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def norm_sentence(s: dict) -> dict:
    chunks = s.get("chunks") or []
    out_chunks = []
    for c in chunks:
        if isinstance(c, dict):
            out_chunks.append({"en": c.get("en") or "", "role": c.get("role") or "",
                               "cn": c.get("cn") or ""})
        else:
            out_chunks.append({"en": str(c), "role": "", "cn": ""})
    return {"en": (s.get("en") or "").strip(), "chunks": out_chunks,
            "cn": s.get("cn") or "", "note": s.get("note") or s.get("why") or ""}


def norm_paragraph(p: dict) -> dict:
    sents = [norm_sentence(s) for s in (p.get("sentences") or []) if isinstance(s, dict)]
    en = (p.get("en") or "").strip() or " ".join(s["en"] for s in sents if s["en"]).strip()
    cn = (p.get("cn") or "").strip() or " ".join(s["cn"] for s in sents if s["cn"]).strip()
    return {"en": en, "cn": cn,
            "main": p.get("main") or p.get("topic") or "",
            "structure": p.get("structure") or "",
            "sentences": sents}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paper")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pp = Path(args.paper)
    paper = json.loads(pp.read_text(encoding="utf-8"))
    for key, sec in (paper.get("reading") or {}).items():
        paras = sec.get("paragraphs")
        if not isinstance(paras, list):
            continue
        before = [bool(p.get("en")) for p in paras if isinstance(p, dict)]
        sec["paragraphs"] = [norm_paragraph(p) for p in paras if isinstance(p, dict)]
        words = len(re.findall(r"[A-Za-z][A-Za-z'-]*",
                              " ".join(p["en"] for p in sec["paragraphs"])))
        sents = sum(len(p["sentences"]) for p in sec["paragraphs"])
        print(f"{key}: paragraphs={len(sec['paragraphs'])} en_now={sum(1 for p in sec['paragraphs'] if p['en'])}"
              f"/{len(before)} words={words} sentences={sents}")
    if args.dry_run:
        print("dry-run，未写入")
        return
    pp.write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written", pp)


if __name__ == "__main__":
    main()
