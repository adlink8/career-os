# -*- coding: utf-8 -*-
"""通用逐句解析生成：把任意英文段落切成句子，给每个意群标成分与中文。

用于：选词填空正文、长篇匹配段落、作文范文、翻译参考译文。
输出: var/cet4-daily/sent-explain-<kind>.json

用法: python bin/cet4_sentence_explain.py --kind cloze [--workers 3]
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

PROMPT = """你是四级阅读精读老师。下面是一段英文（{where}）。逐句做「顺流镜头」拆解。

【铁律】
- 只从左到右走，意群按语序切开，**不许把后面的成分拉回前面解释**。
- 每个意群标一个成分：主 / 谓 / 宾 / 表 / 状 / 定 / 补 / 连。
- 中文逐块 1:1 对应，不增补原文没有的词，不写成语；不用“先行词/后置定语”这类术语。
- 一句一条记录，句子必须与原文逐字一致（含标点），不许改写、不许合并、不许漏句。

【只输出 JSON】
{{"sentences":[{{"en":"原句（逐字照抄）",
  "chunks":[{{"en":"意群","role":"主","cn":"该意群中文"}}],
  "cn":"整句顺流中文"}}]}}

【原文】
{text}
"""


def cb(prompt: str) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=1200, cwd=str(ROOT))
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


def split_sents(text: str) -> list[str]:
    s = re.sub(r"\s+", " ", text or "").strip()
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'\u201c])", s)
    return [p.strip() for p in parts if len(p.split()) >= 3]


def collect(kind: str) -> list[dict]:
    paper = json.loads(PAPER.read_text(encoding="utf-8"))
    r = paper["reading"]
    jobs = []
    if kind == "cloze":
        jobs.append({"tag": "cloze", "where": "选词填空正文（含 __26__ 等空格标记，照抄不要还原）",
                     "text": r["cloze"]["passage"]})
    elif kind == "match":
        for k, v in r["match"]["paragraphs"].items():
            jobs.append({"tag": f"match-{k}", "where": f"长篇匹配第 {k} 段", "text": v})
    elif kind == "writing":
        jobs.append({"tag": "writing-directions", "where": "作文题干 Directions",
                     "text": paper["writing"].get("directions", "")})
        jobs.append({"tag": "writing", "where": "作文范文", "text": paper["writing"].get("model_essay", "")})
    elif kind == "translation":
        jobs.append({"tag": "translation", "where": "翻译参考译文", "text": paper["translation"].get("reference", "")})
    elif kind == "listening":
        for sec in paper["listening"]["sections"]:
            for p in sec["pieces"]:
                tag = f"{sec['name']}-{Path(str(p.get('audio') or 'x')).stem}"
                jobs.append({"tag": tag, "where": f"听力 {p.get('title','')} 的逐句转写",
                             "text": p.get("script", ""), "max_words": 140})
    return jobs


def job(item):
    text = item["text"]
    limit = item.get("max_words", 260)
    if len(text.split()) > limit:  # 长文本按句子切块，避免输出被截断
        sents = split_sents(text)
        step = max(1, len(sents) // 2)
        blocks = [" ".join(sents[i:i + step]) for i in range(0, len(sents), step)]
    else:
        blocks = [text]
    out = []
    for bi, blk in enumerate(blocks, 1):
        data = parse_json(cb(PROMPT.format(where=item["where"], text=blk[:6000])))
        if not data:
            print(f"  {item['tag']}#{bi}: parse failed", flush=True)
            continue
        out.extend(data["sentences"])
        print(f"  {item['tag']}#{bi}: {len(data['sentences'])} sentences", flush=True)
    return item["tag"], out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["cloze", "match", "writing", "translation", "listening"])
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    jobs = collect(args.kind)
    print(f"kind={args.kind} units={len(jobs)}", flush=True)
    result = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for tag, sents in ex.map(job, jobs):
            if sents:
                result[tag] = sents
    out = ROOT / "var" / "cet4-daily" / f"sent-explain-{args.kind}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(v) for v in result.values())
    missing = [j["tag"] for j in jobs if j["tag"] not in result]
    print(f"saved {out} | units={len(result)} sentences={total} missing={missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
