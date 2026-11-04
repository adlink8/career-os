# -*- coding: utf-8 -*-
"""把流水线产出的某一节（已通过独立审查）换进整卷 JSON。

用法:
  python bin/cet4_swap_section.py --paper var/cet4-daily/demo-whole-paper.json \
      --section match --from var/cet4-daily/pipeline/match1.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

KEEP = {
    "cloze": ("passage", "bank", "answers"),
    "match": ("title", "paragraphs", "statements", "answers"),
    "passage1": ("title", "paragraphs", "questions"),
    "passage2": ("title", "paragraphs", "questions"),
}
# 溯源信息一起带过去，整卷审查靠它判跨节同源
META = ("source", "source_url", "title_cn", "topic", "date")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", required=True)
    ap.add_argument("--section", required=True, choices=list(KEEP))
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pp = Path(args.paper)
    paper = json.loads(pp.read_text(encoding="utf-8"))
    src = json.loads(Path(args.src).read_text(encoding="utf-8"))
    target = paper["reading"][args.section]

    moved = []
    for k in KEEP[args.section]:
        if src.get(k):
            moved.append(k)
            target[k] = src[k]
    # 段落/题目换了，标题也要跟着换，避免题文不符
    if src.get("title") and "title" not in KEEP[args.section]:
        target["title"] = src["title"]
    for k in META:
        if src.get(k):
            target[k] = src[k]

    print(f"section={args.section} 换入字段: {moved}")
    if args.section == "match":
        dup = [k for k, v in target["answers"].items()
               if list(target["answers"].values()).count(v) > 1]
        print("答案重复的题号:", dup or "无")
    if args.dry_run:
        print("dry-run，未写入")
        return
    pp.write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written", pp)


if __name__ == "__main__":
    main()
