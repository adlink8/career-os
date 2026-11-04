# -*- coding: utf-8 -*-
"""按题型分派的出题老师 / 审查老师。

用法:
  python bin/cet4_roles.py --type cloze|match|reading --role writer|reviewer --input <json> [--out <json>]

约定：脚本只负责拼 prompt、调 CB、解析 JSON；**不设任何分数/字数硬门**，
通过与否一律以 reviewer 的 verdict 为准。
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
KB = ROOT / "knowledge" / "cet4-bank" / "10-出题知识库"
DIRS = {"cloze": "01-选词填空", "match": "02-长篇匹配", "reading": "03-仔细阅读",
        "listening": "04-听力", "translation": "05-翻译", "writing": "06-写作"}

SOLVER = {
    "reading": """你是四级答题老师。给你文章与 5 道题，独立作答并给出依据。
只输出 JSON：{{"answers":{{"46":"A",...}},"reasons":[{{"no":46,"reason":"为什么选它","evidence":"原文依据"}}]}}
文章：
{article}
题目：
{questions}
""",
}

WRITER = {
    "cloze": """你是四级选词填空命题老师。给你一篇文章，改成 Section A：
输出 JSON：{{"passage":"用 __26__..__35__ 标 10 个空（每空前后保留原句语境）","bank":{{"A":"词","B":"词",...,"O":"词"}},"answers":{{"26":"字母",...}},"translate":[{{"blank":26,"cn":"该空中文"}}]}}
规则：文章 188-267 词；15 词同词性同语义场；10 正确 + 5 干扰；每空唯一答案；答案字母分散。
文章：
{article}
""",
    "match": """你是四级长篇匹配命题老师。给你一篇文章，改成 Section B：
输出 JSON：{{"title":"英文标题","paragraphs":{{"A":"段落原文",...}},"statements":[{{"no":36,"text":"陈述（改写，禁止照抄）"}}],"answers":{{"36":"段落字母",...}}}}
规则：10-11 段、每段 60-120 词；10 条陈述各一个信息点；至少 1 条转折、1 条数据；答案分散；允许 1-2 段不设题。
文章：
{article}
""",
    "reading": """你是四级仔细阅读命题老师。给你一篇文章，出 5 题（46-50）：
输出 JSON：{{"questions":[{{"no":46,"stem":"","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","evidence":"原文句","paraphrase":{{"original":"","option":""}},"trap":"","option_analysis":[{{"letter":"A","correct":false,"why":""}}],"stem_cn":"","options_cn":[]}}]}}
规则：细节 2-3、态度 1、推断 1、原因 1；题文同序；正确项换谓语、连续实词<=4；三个干扰项三种手法；选项等长；答案>=3 字母。
文章：
{article}
""",
}

REPAIR = {
    "cloze": """你是四级选词填空命题老师，现在按审查报告**定点修改**这套题。没被点名的空和句子原样保留，禁止整体重写。
【审查报告】
{review}
【当前成品】
{prev}
【文章原文（改写空时以此为准）】
{article}
要求：
1) 逐条解决 must_fix，每一条都要真的落到成品里，不许只换措辞糊弄。
2) 文章 188-267 词；词库 15 词同词性、同语义场；10 正确 + 5 干扰；每空唯一答案。
3) 答案字母 A-O 分散，不许连续同字母扎堆。
4) 空前后保留足够语境，保证能从上下文唯一推出。
只输出 JSON：{{"passage":"","bank":{{"A":""}},"answers":{{"26":"A"}},"translate":[{{"blank":26,"cn":""}}]}}
""",
    "match": """你是四级长篇匹配命题老师，现在按审查报告**定点修改**这套题。没被点名的段落和陈述原样保留。
【审查报告】
{review}
【当前成品】
{prev}
【文章原文】
{article}
要求：
1) 逐条解决 must_fix。
2) 10-11 段，每段 60-120 词；陈述 36-45 共 10 条，每条只含一个信息点，必须改写（禁止照抄原句）。
3) 答案字母分散，允许 1-2 段不设题。
只输出 JSON：{{"title":"","paragraphs":{{"A":""}},"statements":[{{"no":36,"text":""}}],"answers":{{"36":"A"}}}}
""",
    "reading": """你是四级仔细阅读命题老师，现在按审查报告**定点修改**这 5 道题。只改 questions，passage 一个字都不许动。
【审查报告】
{review}
【当前题目】
{prev}
要求：
1) 逐条解决 must_fix，每一条都要在最终题目里看得见。
2) 题干必须指向原文的具体对象；正确项必须是同义替换（连续实词重合 <=4 词）；三个干扰项三种不同手法。
3) 每题 evidence 必须逐字出现在原文；同题选项长度差 <=3 词；答案覆盖 >=3 个字母。
4) 题号 46-50；每题给 stem_cn、options_cn、option_analysis（四个选项各自的为什么）。
只输出 JSON：{{"questions":[...]}}，结构与原题完全一致。
""",
}

REVIEWER = {
    "cloze": """你是四级选词填空审查老师。对照下面 2 套真题范例，逐空审查候选卷。
只输出 JSON：{{"verdict":"pass|needs_revision","score":0,"must_fix":[{{"id":"F1","severity":"blocker|high|medium","problem":"","fix":""}}]}}
审查点：空白是否可解、干扰项是否同质、答案是否唯一、词库是否 15 词同场、文章是否 188-267 词。
【真题范例】{examples}
【候选卷】{paper}
""",
    "match": """你是四级长篇匹配审查老师。对照下面 2 套真题范例，审查候选卷。
只输出 JSON：{{"verdict":"pass|needs_revision","score":0,"must_fix":[]}}
审查点：每段是否可辨、陈述是否改写（非照抄）、每条是否单一信息点、答案是否分散、是否有 1-2 段纯干扰。
【真题范例】{examples}
【候选卷】{paper}
""",
    "listening": """你是四级听力审查老师。对照 2 套真题，审查候选听力题（音频文本若缺失请指出）。
只输出 JSON：{{"verdict":"pass|needs_revision","score":0,"must_fix":[]}}
【真题范例】{examples}
【候选卷】{paper}
""",
    "translation": """你是四级翻译审查老师。对照 2 套真题，审查候选汉译英段落与参考译文。
只输出 JSON：{{"verdict":"pass|needs_revision","score":0,"must_fix":[]}}
审查点：字数 140-180、句数 6-9、文化负载词、是否有官方提示、参考译文是否准确通顺。
【真题范例】{examples}
【候选卷】{paper}
""",
    "writing": """你是四级写作审查老师。对照 2 套真题，审查候选作文题与范文。
只输出 JSON：{{"verdict":"pass|needs_revision","score":0,"must_fix":[]}}
审查点：情景式命题、话题贴近校园/社会、120-180 词、观点明确、结构完整。
【真题范例】{examples}
【候选卷】{paper}
""",
    "reading": """你是四级仔细阅读审查老师。对照下面 2 套真题范例，逐题审查候选卷。
只输出 JSON：{{"verdict":"pass|needs_revision","score":0,"must_fix":[]}}
审查点：题型配比、题文同序、正确项是否照抄、干扰项手法、双答案、选项长度、答案分布、题干是否加码。
【真题范例】{examples}
【候选卷】{paper}
""",
}


def examples_for(t: str) -> str:
    p = KB / DIRS[t] / "exemplars.json"
    if not p.exists():
        return ""
    data = json.loads(p.read_text(encoding="utf-8"))
    exs = data.get("examples", [])[:2]
    return json.dumps(exs, ensure_ascii=False)[:6000]


def run(prompt: str) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(ROOT))
    return p.stdout or ""


def parse_json(text: str):
    t = re.sub(r"^```(?:json)?\s*", "", (text or "").strip())
    t = re.sub(r"\s*```$", "", t)
    i = t.find("{")
    if i < 0:
        return None
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
                    return json.loads(t[i:j + 1])
                except json.JSONDecodeError:
                    return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", required=True, choices=list(DIRS))
    ap.add_argument("--role", required=True, choices=["writer", "reviewer", "solver", "repair"])
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--prev", default="", help="repair 用：上一轮成品 JSON")
    ap.add_argument("--mustfix", default="", help="repair 用：reviewer 审查报告 JSON")
    args = ap.parse_args()
    src = Path(args.input)
    paper = json.loads(src.read_text(encoding="utf-8"))
    if args.role == "repair":
        if args.type not in REPAIR:
            print("no repair template for", args.type)
            return 1
        if not args.prev or not args.mustfix:
            print("repair needs --prev and --mustfix")
            return 1
        prev = json.loads(Path(args.prev).read_text(encoding="utf-8"))
        rev = json.loads(Path(args.mustfix).read_text(encoding="utf-8"))
        keys = {"reading": ("questions",), "cloze": ("passage", "bank", "answers", "translate"),
                "match": ("title", "paragraphs", "statements", "answers")}[args.type]
        prev_payload = {k: prev.get(k) for k in keys if k in prev}
        prompt = REPAIR[args.type].format(
            review=json.dumps(rev, ensure_ascii=False)[:6000],
            prev=json.dumps(prev_payload, ensure_ascii=False)[:20000],
            article=(paper.get("article") or paper.get("passage") or "")[:8000])
    elif args.role == "writer":
        article = paper.get("article") or paper.get("passage") or ""
        prompt = WRITER[args.type].format(article=article[:8000])
    elif args.role == "solver":
        prompt = SOLVER["reading"].format(article=(paper.get("passage") or "")[:8000],
                                          questions=json.dumps(paper.get("questions") or [], ensure_ascii=False)[:6000])
    else:
        keys = {"reading": ("title", "passage", "questions"),
                "cloze": ("passage", "bank", "answers"),
                "match": ("title", "paragraphs", "statements", "answers"),
                "listening": ("sections",),
                "translation": ("translation",),
                "writing": ("writing",)}[args.type]
        payload = {k: paper.get(k) for k in keys if k in paper}
        prompt = REVIEWER[args.type].format(examples=examples_for(args.type),
                                            paper=json.dumps(payload, ensure_ascii=False)[:24000])
    data = parse_json(run(prompt))
    if not data:
        print("parse failed")
        return 1
    out = Path(args.out) if args.out else src.with_name(f"{src.stem}.{args.type}.{args.role}.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.role == "reviewer":
        print(f"verdict={data.get('verdict')} score={data.get('score')} fixes={len(data.get('must_fix') or [])}")
    elif args.role == "solver":
        print("answers", data.get("answers"))
    else:
        print("keys:", list(data)[:6])
    print("saved", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
