# -*- coding: utf-8 -*-
"""给听力题目补英文问句（真题里问题由录音念出，示例音频没念，所以补到卷面）。

用法: python cet4/bin/cet4_listen_stems.py [--paper var/cet4-daily/demo-whole-paper.json]
产物: 直接写回 paper JSON，每题多一个 stem 字段。
"""
from __future__ import annotations

# --- 四级工具根目录：相对路径统一按 cet4/ 解析（在仓库根或 cet4/ 下运行都行）---
import os as _os, sys as _sys, pathlib as _pl
_CET4_ROOT = _pl.Path(__file__).resolve().parents[1]
try:
    _os.chdir(_CET4_ROOT)
except OSError:
    pass
_sys.argv = [a[5:] if a[:5] in ("cet4/", "cet4\\") else a for a in _sys.argv]
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """你是四级听力命题老师。下面是一段听力原文，以及 4 个已定好的选择题（只有选项和答案，没有问句）。
请为每道题写出它对应的【英文问句】（题干），要求：
- 必须能和已给答案对得上，答案选项就是该问句的正确回答
- 四级听力常见问法：What does the speaker say about ...? / Why ...? / What can we learn about ...? / How ...?
- 每题一句，<=14 词，标准美式英语，句末问号
- 只输出 JSON 数组：[{{"no":1,"stem":"..."}}]，不增不减，编号照抄

原文：
{script}

题目：
{items}
"""


def parse(txt: str):
    t = (txt or "").strip()
    i, j = t.find("["), t.rfind("]")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="var/cet4-daily/demo-whole-paper.json")
    ap.add_argument("--force", action="store_true", help="已有 stem 也重写")
    args = ap.parse_args()

    path = ROOT / args.paper
    data = json.loads(path.read_text(encoding="utf-8"))
    total = filled = 0
    for sec in data["listening"]["sections"]:
        for piece in sec["pieces"]:
            qs = piece.get("questions") or []
            todo = [q for q in qs if args.force or not (q.get("stem") or "").strip()]
            if not todo:
                continue
            total += len(todo)
            items = "\n".join(
                f'{q["no"]}. 选项: ' + " | ".join(q.get("options") or []) + f'  答案: {q.get("answer")}'
                for q in todo)
            prompt = PROMPT.format(script=(piece.get("script") or "")[:2500], items=items)
            proc = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                                  capture_output=True, text=True, encoding="utf-8", timeout=600, cwd=str(ROOT))
            got = parse(proc.stdout or "") or []
            by_no = {int(g["no"]): (g.get("stem") or "").strip() for g in got if str(g.get("no", "")).strip().isdigit()}
            for q in todo:
                s = by_no.get(int(q["no"]))
                if s:
                    q["stem"] = s
                    filled += 1
            print(f'  {sec["name"]}-{piece.get("audio")}: {len(by_no)}/{len(todo)}', flush=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"todo={total} filled={filled} -> {path}")
    missing = [q["no"] for sec in data["listening"]["sections"] for p in sec["pieces"]
               for q in (p.get("questions") or []) if not (q.get("stem") or "").strip()]
    if missing:
        print("still missing:", missing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
