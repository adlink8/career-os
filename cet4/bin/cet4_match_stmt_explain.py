# -*- coding: utf-8 -*-
"""给 Section B 的 10 条陈述（36–45）生成解析：句意 / 定位关键词 / 对应原文句 / 易错点。

用法: python cet4/bin/cet4_match_stmt_explain.py [--paper var/cet4-daily/demo-whole-paper.json]
产物: var/cet4-daily/match-stmt-explain.json
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

PROMPT = """你是四级阅读老师。下面每条是「信息匹配题」的陈述句（题干），以及它对应的原文段落。
请逐条给出解析，只输出 JSON 数组，不要解释文字。

[{{"no":36,
  "cn":"题干句意中译（<=40 字，直译为主，不要润色）",
  "key":"定位关键词 3-5 个（英文原词，逗号分隔）",
  "src":"该段落里与题干对应的原句（英文，照抄原文，<=40 词）",
  "trap":"最容易被误选成哪一段、为什么（<=25 字）"}}]

硬规则：
- 只处理给定题号，不增不减；no 用数字。
- src 必须真的出现在给定段落里，逐词照抄，不许改写。
- cn 是题干的中文句意，不是段落主旨。
- trap 要具体到「干扰段字母 + 原因」。

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
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    paper = json.loads((ROOT / args.paper).read_text(encoding="utf-8"))
    m = paper["reading"]["match"]
    paras, ans = m["paragraphs"], m["answers"]
    out_path = ROOT / "var" / "cet4-daily" / "match-stmt-explain.json"
    done = {}
    if out_path.exists() and not args.force:
        done = json.loads(out_path.read_text(encoding="utf-8"))

    todo = [st for st in m["statements"] if str(st["no"]) not in done]
    print(f"statements={len(m['statements'])} done={len(done)} todo={len(todo)}")
    if not todo:
        return 0

    blocks = []
    for st in todo:
        letter = ans.get(str(st["no"]), "")
        text = paras.get(letter, "")
        blocks.append(f'题号 {st["no"]}（正确段落 {letter}）\n题干：{st["text"]}\n段落 {letter}：{text}')
    prompt = PROMPT.format(items="\n\n".join(blocks))
    proc = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                          capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(ROOT))
    got = parse(proc.stdout or "") or []
    for g in got:
        no = str(g.get("no", "")).strip()
        if no:
            done[no] = g
    out_path.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    missing = [st["no"] for st in m["statements"] if str(st["no"]) not in done]
    print(f"filled={len(got)} total={len(done)} missing={missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
