# -*- coding: utf-8 -*-
"""长篇匹配段落解析：每段主旨/作用/对应题号 + 逐句意群。

用法: python bin/cet4_match_explain.py [--workers 2]
输出: var/cet4-daily/match-explain.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
PAPER = ROOT / "var" / "cet4-daily" / "demo-whole-paper.json"
OUT = ROOT / "var" / "cet4-daily" / "match-explain.json"

PROMPT = """你是四级长篇匹配（Section B）讲解老师。下面给出若干段原文与全部 10 条陈述。为这些段做解析。

【铁律】
- 不许语法黑话；用「顺流镜头」，意群用 \\ 切开，中文按块 1:1 对应，不增补原文没有的词。
- 解析要落到本段内容，禁止套模板（不要每段都写“本段介绍背景信息”这类空话）。

【只输出 JSON】
{{"paras":[{{"letter":"A","main":"这一段到底讲什么（具体，不空泛）",
  "role":"在全文里起什么作用（如：提出旧观念／给数据／举例／转折）",
  "answers":["36"],
  "sentences":[{{"en":"原句","chunks":"用 \\\\ 切开","cn":"逐块中文","note":"这句为什么是某条陈述的出处（若对应）"}}]}}]}}

【需要解析的段落】
{paras}

【全部陈述】
{statements}

【答案（陈述号→段落字母）】
{answers}
"""


def cb(prompt: str) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(ROOT))
    return p.stdout or ""


def parse_json(text: str):
    t = re.sub(r"^```(?:json)?\s*", "", (text or "").strip())
    t = re.sub(r"\s*```$", "", t)
    for m in re.finditer(r"\{", t):
        i = m.start()
        depth = 0
        in_str = esc = False
        for j in range(i, len(t)):
            ch = t[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(t[i:j + 1])
                    except json.JSONDecodeError:
                        break
                    if isinstance(obj, dict) and obj.get("paras"):
                        return obj
                    break
    return None


def job(chunk):
    data = parse_json(cb(chunk["prompt"]))
    if not data:
        print(f"  chunk {chunk['tag']}: parse failed", flush=True)
        return chunk["tag"], None
    print(f"  chunk {chunk['tag']}: paras={len(data.get('paras') or [])}", flush=True)
    return chunk["tag"], data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--size", type=int, default=4, help="每次解析几段")
    args = ap.parse_args()

    paper = json.loads(PAPER.read_text(encoding="utf-8"))
    m = paper["reading"]["match"]
    paras = m["paragraphs"]
    statements = json.dumps([{"no": s["no"], "text": s["text"]} for s in m["statements"]],
                            ensure_ascii=False)
    answers = json.dumps(m["answers"], ensure_ascii=False)

    letters = list(paras.keys())
    chunks = []
    for i in range(0, len(letters), args.size):
        sub = letters[i:i + args.size]
        prompt = PROMPT.format(
            paras="\n\n".join(f"[{k}] {paras[k]}" for k in sub)[:9000],
            statements=statements, answers=answers)
        chunks.append({"tag": "-".join(sub), "prompt": prompt})

    out = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for tag, data in ex.map(job, chunks):
            if data:
                for p in data["paras"]:
                    out[p.get("letter")] = p
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    missing = [k for k in letters if k not in out]
    print("saved", OUT, "| paragraphs:", len(out), "| missing:", missing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
