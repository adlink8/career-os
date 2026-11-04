# -*- coding: utf-8 -*-
"""听力讲解内容生成：逐句双语字幕 + 生词表 + 题目解析。

每个 piece 一次独立 CB 会话；结果写入 var/cet4-daily/listening-explain.json。
用法: python bin/cet4_listen_explain.py [--workers 3] [--force]
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
OUT = ROOT / "var" / "cet4-daily" / "listening-explain.json"

PROMPT = """你是四级听力讲解老师。下面是某段听力音频的逐句转写与题目。产出三样东西。

【翻译铁律】
- 英文思路直译：以英文语序和逻辑推进翻译，不为了中文漂亮而增补原文没有的词，不写成语堆砌。
- 每句中文必须与英文逐块对应，哪个英文词对应哪个中文意思要字字清楚。
- 术语、人名、机构名保留常用译名；数字照原文。

【解析铁律（重要）】
- **一条一句话**，不许连成一大段：正确项 why <= 30 个汉字；每个干扰项 why <= 20 个汉字。
- 干扰项开头必须用四类术语之一：无中生有 / 偷换概念 / 因果倒置 / 范围扩大，然后一句话说清。
- 不复述原文长句，不写"综上所述/需要注意的是"这类废话；能删的字全删。

【输出 JSON，只输出 JSON，不要任何解释文字】
{{"sentences":[{{"i":1,"cn":"第 1 句英文对应的中文"}}],
 "words":[{{"w":"单词","ipa":"/音标/","pos":"n./v./adj.","cn":"该词在本段中的意思"}}],
 "qanalysis":[{{"no":1,"answer":"B","why":"一句话说清为什么对（<=30字）",
   "options":[{{"letter":"A","ok":false,"why":"无中生有：原文没提搬迁"}},
              {{"letter":"B","ok":true,"why":"同义替换：used only once = rarely reused"}},
              {{"letter":"C","ok":false,"why":"偷换概念：出钱的是慈善机构"}},
              {{"letter":"D","ok":false,"why":"因果倒置：原文花钱置办不是削减"}}]}}]}}

【生词表要求】只收四级以上、或本段理解关键、或易混的词；6-15 个；词形用原文出现形式（必要时给原形）。

【本段信息】
标题：{title}
逐句英文（编号即 sentences 里的 i）：
{sents}

题目（含正确答案）：
{questions}
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
                    if isinstance(obj, dict) and obj.get("sentences"):
                        return obj
                    break
    return None


def job(item):
    sec, piece = item
    sents = "\n".join(f'{k + 1}. {s.get("en") or s.get("text") or ""}'
                      for k, s in enumerate(piece.get("timing") or []))
    qs = json.dumps([{"no": q.get("no"), "options": q.get("options"),
                      "answer": q.get("answer")} for q in (piece.get("questions") or [])],
                    ensure_ascii=False)
    prompt = PROMPT.format(title=piece.get("title"), sents=sents[:9000], questions=qs[:4000])
    data = parse_json(cb(prompt))
    key = f"{sec}-{Path(piece.get('audio') or 'x').stem}"
    if not data:
        print(f"  {key}: parse failed", flush=True)
        return key, None
    n_exp = len(piece.get("timing") or [])
    n_got = len(data.get("sentences") or [])
    print(f"  {key}: sentences {n_got}/{n_exp} words={len(data.get('words') or [])} "
          f"qanalysis={len(data.get('qanalysis') or [])}", flush=True)
    return key, data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="", help="只跑某段，如 A-01")
    args = ap.parse_args()

    paper = json.loads(PAPER.read_text(encoding="utf-8"))
    items = []
    for s in paper["listening"]["sections"]:
        for p in s["pieces"]:
            if args.only and args.only not in (p.get("audio") or ""):
                continue
            items.append((s["name"], p))

    out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() and not args.force else {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for key, data in ex.map(job, items):
            if data:
                out[key] = data
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", OUT, "| pieces:", len(out))


if __name__ == "__main__":
    sys.exit(main())
