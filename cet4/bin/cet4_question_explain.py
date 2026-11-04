# -*- coding: utf-8 -*-
"""给「题目句子」补逐句解析：题干 + 每个选项（顺流意群 + 成分 + 中文）。

覆盖：听力 25 题干 + 100 选项、阅读 46-55 的 10 题干 + 40 选项、匹配 36-45 的 10 条陈述。
用法: python cet4/bin/cet4_question_explain.py [--workers 3] [--batch 16] [--force]
产物: var/cet4-daily/question-explain.json   {id: {cn, chunks:[{en,role,cn}]}}
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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
OUT = ROOT / "var" / "cet4-daily" / "question-explain.json"

PROMPT = """你是四级英语老师。把下面每句英文按「眼睛从左到右」的顺序切成 4-8 词的意群，标出成分，并给整句中文。
只输出 JSON 数组，不要任何解释文字：
[{"id":"题号","cn":"整句中文（直译为主，不加文学修饰）","chunks":[{"en":"英文意群","role":"主","cn":"这一段的中文"}]}]

role 只能取这 8 个之一：主 谓 宾 表 补 定 状 连
规则：
- 意群必须按原文顺序拼接后等于原句（不改写、不增删词）。
- 中文与意群一一对应，不许意译扩写；功能词（to/of/and…）可并进相邻意群。
- 疑问句按正常语序顺读拆解，不要倒装回拉。

待解析句子：
<<<ITEMS>>>"""


def parse(txt: str):
    t = (txt or "").strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("["), t.rfind("]")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return None


def collect(paper: dict) -> list:
    items = []

    def add(i, en):
        en = (en or "").strip()
        if en:
            items.append((i, en))

    for sec in paper["listening"]["sections"]:
        for piece in sec["pieces"]:
            for q in piece.get("questions") or []:
                no = int(q["no"])
                add(f"L{no}S", q.get("stem"))
                for opt in q.get("options") or []:
                    m = re.match(r"^\s*([A-D])\)\s*(.+)$", opt)
                    if m:
                        add(f"L{no}{m.group(1)}", m.group(2))
    for key in ("passage1", "passage2"):
        for q in paper["reading"][key].get("questions") or []:
            no = int(q["no"])
            add(f"R{no}S", q.get("stem"))
            for opt in q.get("options") or []:
                m = re.match(r"^\s*([A-D])\)\s*(.+)$", opt)
                if m:
                    add(f"R{no}{m.group(1)}", m.group(2))
    for st in paper["reading"]["match"].get("statements") or []:
        add(f"M{st['no']}", st.get("text"))
    return items


def job(chunk):
    body = "\n".join(f'{i}. {en}' for i, en in chunk)
    proc = subprocess.run([str(CB), "-p", "--output-format", "text"], input=PROMPT.replace('<<<ITEMS>>>', body),
                          capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(ROOT))
    data = parse(proc.stdout or "") or []
    got = {}
    for d in data:
        i = str(d.get("id") or "").strip()
        if i and d.get("chunks"):
            got[i] = {"cn": (d.get("cn") or "").strip(), "chunks": d["chunks"]}
    miss = [i for i, _ in chunk if i not in got]
    print(f"  chunk {chunk[0][0]}..{chunk[-1][0]}: {len(got)}/{len(chunk)}" + (f" 缺 {miss[:4]}" if miss else ""), flush=True)
    return got


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="var/cet4-daily/demo-whole-paper.json")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    paper = json.loads((ROOT / args.paper).read_text(encoding="utf-8"))
    items = collect(paper)
    done = {}
    if OUT.exists() and not args.force:
        done = json.loads(OUT.read_text(encoding="utf-8"))
    todo = [(i, en) for i, en in items if i not in done]
    print(f"items={len(items)} done={len(done)} todo={len(todo)}", flush=True)
    chunks = [todo[i:i + args.batch] for i in range(0, len(todo), args.batch)]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for got in ex.map(job, chunks):
            done.update(got)
            OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    missing = [i for i, _ in items if i not in done]
    print(f"finished done={len(done)} missing={len(missing)}")
    if missing:
        print("missing sample:", missing[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
