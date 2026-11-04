# -*- coding: utf-8 -*-
"""批量生成单词解析：音标/词性/释义 + 词根词缀 + 同族词 + 搭配 + 例句 + 记忆点。

用法: python cet4/bin/cet4_words.py [--workers 4] [--batch 40] [--force]
输出: var/cet4-daily/words.json
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

ROOT = Path(__file__).resolve().parent.parent
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """你是英语词典编辑。为下列单词逐个产出「便于记忆」的解析，只输出 JSON 数组，不要解释文字。

[{{"word":"","phonetic":"/IPA/","pos":"n./v./adj./adv. 等",
  "cn":"本义与最常用义（<=12 字）",
  "root":"词根或词源，如 port=搬运、spect=看；无词根写'—'",
  "affix":"词缀拆解，如 re-(回)+build(建)；无则写'—'",
  "family":"同族词 1-3 个，逗号分隔；无则写'—'",
  "collocation":"最高频搭配 1-2 个，如 pay attention to",
  "example":"英文例句（<=12 词，用到该搭配）",
  "example_cn":"例句中文",
  "tip":"一句话记忆点或易混提醒（<=20 字）"}}]

硬规则：
- 只处理给定的词，不增不减，顺序不变；词形照抄。
- 功能词（the/of/to 等）root/affix/family 写'—'，但 collocation/example/tip 必须有。
- 音标用英式或美式均可，但必须是真实音标，不能编。
- 释义给这个词在四级语境下的意思，不要抄词典长释义。
- 中文一律简体，例：abandon → /əˈbændən/ v. 放弃；a-（离开）+ bandon（控制）。

单词：
{words}
"""


def parse(text: str):
    t = re.sub(r"^```(?:json)?\s*", "", (text or "").strip())
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("["), t.rfind("]")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return None


def job(chunk):
    prompt = PROMPT.format(words="\n".join(chunk))
    proc = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                          capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(ROOT))
    data = parse(proc.stdout or "")
    if not data:
        print(f"  chunk {chunk[0]}..{chunk[-1]}: parse failed", flush=True)
        return {}
    got = {x["word"].lower(): x for x in data if x.get("word")}
    miss = [w for w in chunk if w not in got]
    print(f"  chunk {chunk[0]}..{chunk[-1]}: {len(got)}/{len(chunk)}"
          + (f" 缺 {miss[:4]}" if miss else ""), flush=True)
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--force", action="store_true", help="忽略已有结果，全部重跑")
    args = ap.parse_args()

    src = ROOT / "var" / "cet4-daily" / "wordlist.json"
    words = [w["word"] for w in json.loads(src.read_text(encoding="utf-8"))]
    out_path = ROOT / "var" / "cet4-daily" / "words.json"
    done = {}
    if out_path.exists() and not args.force:
        done = {x["word"].lower(): x for x in json.loads(out_path.read_text(encoding="utf-8"))}
        done = {k: v for k, v in done.items() if v.get("root")}  # 旧版无词根，视为待补
    todo = [w for w in words if w not in done]
    print(f"words={len(words)} done={len(done)} todo={len(todo)}", flush=True)
    if out_path.exists() and args.force:
        out_path.with_suffix(".bak.json").write_text(out_path.read_text(encoding="utf-8"), encoding="utf-8")

    chunks = [todo[i:i + args.batch] for i in range(0, len(todo), args.batch)]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for got in ex.map(job, chunks):
            done.update(got)
            out_path.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1), encoding="utf-8")

    missing = [w for w in words if w not in done]
    print(f"finished entries={len(done)} missing={len(missing)}")
    if missing:
        (ROOT / "var" / "cet4-daily" / "words-missing.json").write_text(
            json.dumps(missing, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
