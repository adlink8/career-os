# -*- coding: utf-8 -*-
"""出题老师：只负责按四级阅读契约出 5 道题（不与改写混在一起）。

用法: python bin/cet4_make_questions.py <passage.json> [--out xxx.json]
输入 JSON 需含 passage/paragraphs；输出把 questions 合并回去并校验。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
sys.path.insert(0, str(ROOT / "bin"))
from cet4_validate import check  # noqa: E402

PROMPT = """你是大学英语四级阅读命题老师。给你一篇已改写好的文章，只出 5 道题，不要改文章。
只输出 JSON：{{"questions":[...]}}
每道题：
{{"no":1,"stem":"题干（英文 <=20 词，具体不空泛）","stem_cn":"题干中文（顺流直译）",
 "options":["A) ...","B) ...","C) ...","D) ..."],"options_cn":["A 项中文","B 项中文","C 项中文","D 项中文"],
 "answer":"A|B|C|D",
 "evidence":"原文定位句（必须逐字出现在 passage 中）",
 "paraphrase":{{"original":"原文词句","option":"选项换皮词"}},
 "trap":"无中生有|偷换概念|因果倒置|范围扩大|原词拼接",
 "option_analysis":[{{"letter":"A","correct":false,"why":"具体错因"}} ×4]}}
硬约束：
1) 5 题：细节 2、推断 1、态度/观点 1、词义/指代 1；至少 1 题落在转折处。
2) 答案覆盖至少 3 个不同字母，禁止 5 题同答案。
3) 正确项必须同义替换，不得照抄原文；错误项写具体错因，引用原文或指出缺席/偷换/夸大。
4) 题干不得引入原文没有的概念；不得出现双答案。
5) 每题 evidence 必须逐字出现在 passage。
文章：
{passage}
"""


def parse_json(text: str):
    t = re.sub(r"^```(?:json)?\s*", "", text.strip())
    t = re.sub(r"\s*```$", "", t)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paper")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    src = Path(args.paper)
    paper = json.loads(src.read_text(encoding="utf-8"))
    prompt = PROMPT.format(passage=paper.get("passage", ""))
    proc = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                          capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(ROOT))
    data = parse_json(proc.stdout or "")
    if not data or not data.get("questions"):
        print("writer parse failed:", (proc.stdout or "")[:300])
        return 1
    for q in data["questions"]:
        for oa in q.get("option_analysis") or []:
            oa["correct"] = (oa.get("letter") == q.get("answer"))
    merged = {**paper, "questions": data["questions"]}
    result = check(merged)
    print(f"questions={len(data['questions'])} validate={result['ok']} errors={result['errors'][:5]}")
    out = Path(args.out) if args.out else src.with_name(src.stem + ".q.json")
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
