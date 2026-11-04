# -*- coding: utf-8 -*-
"""生成「写作/翻译思维链」：拆题 → 搭框架 → 填充每部分。

思路链不是解析的搬运，而是给出可复用的解题动作：
  审题拆解（把题目要求拆成要素）→ 立意与框架（每段干什么）→ 填充（每段可套的句式与衔接）
  翻译：拆句 → 找主干 → 定译法 → 成句

用法: python bin/cet4_thinkchain.py
输出: var/cet4-daily/thinkchain.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
PAPER = ROOT / "var" / "cet4-daily" / "demo-whole-paper.json"

WRITE_PROMPT = """你是四级写作教练。下面是一道作文题与一篇范文。请写出**解题思维链**：怎么把题拆开、怎么搭框架、怎么往框架里填。

【要求】
- 讲"动作"，不讲空话：学生照着这条链子就能自己写。
- 框架部分给到"每段干什么 + 必须写进去的要素"，不要写成范文内容。
- 填充部分给**句子骨架**（用 ____ 或 [ ] 标出可替换成分），不是抄范文原句。
- 中文说明，英文骨架。

【只输出 JSON】
{{"breakdown":[{{"item":"题目要素（话题/身份/情境/条件/文体/字数）","value":"这道题具体要求什么"}}],
 "stance":"一句话立场（可直接套用的表态句式，英文）",
 "framework":[{{"para":1,"goal":"这一段要完成什么","must":["必须写进去的要素1","要素2"],"skeleton":"这一段的句子骨架（英文，可含 ____）"}}],
 "fill":[{{"para":1,"openers":["开头句骨架"],"supports":["展开句骨架"],"closers":["收尾句骨架"],"connectors":["衔接词"]}}],
 "pitfalls":["最容易扣分的地方（一句话一条）"]}}

【题目】
{directions}

【范文（仅供判断框架，不要抄）】
{essay}
"""

TRANS_PROMPT = """你是四级翻译教练。下面是一段中文与参考译文。请写出**解题思维链**：怎么拆句、怎么找主干、怎么定译法、怎么连成英文。

【要求】
- 每句给：拆出的中文小句 → 主干（谁做什么）→ 难点（文化词/无主句/并列/语序）→ 英文成句。
- 讲动作，不讲空话；英文给可套用的句式。
- 中文说明。

【只输出 JSON】
{{"steps":["解题步骤（3-5 条，讲顺序：先干什么再干什么）"],
 "sentences":[{{"cn":"中文原句","clauses":["拆出的小句"],"spine":"主干（谁做什么）",
   "trap":"这句的难点与处理办法","en":"英文成句"}}],
 "phrases":[{{"cn":"文化负载词/固定搭配","en":"推荐译法","why":"为什么这么译"}}]}}

【中文】
{zh}

【参考译文（仅供核对，不要照抄成模板）】
{ref}
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
                    if isinstance(obj, dict) and len(obj) >= 2:
                        return obj
                    break
    return None


def main():
    paper = json.loads(PAPER.read_text(encoding="utf-8"))
    w = paper["writing"]
    tr = paper["translation"]
    jobs = {
        "writing": WRITE_PROMPT.format(directions=w.get("directions", "")[:2500],
                                       essay=(w.get("model_essay") or "")[:3500]),
        "translation": TRANS_PROMPT.format(zh=tr.get("zh", "")[:1500],
                                           ref=(tr.get("reference") or "")[:2500]),
    }

    def run(item):
        kind, prompt = item
        data = parse_json(cb(prompt))
        if not data:
            print(f"  {kind}: parse failed", flush=True)
            return kind, None
        print(f"  {kind}: keys={list(data)}", flush=True)
        return kind, data

    out = {}
    with ThreadPoolExecutor(max_workers=2) as ex:
        for kind, data in ex.map(run, jobs.items()):
            if data:
                out[kind] = data
    dst = ROOT / "var" / "cet4-daily" / "thinkchain.json"
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", dst, "| parts:", list(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
