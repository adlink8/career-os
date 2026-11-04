# -*- coding: utf-8 -*-
"""写作讲解生成：结构分解 + 逐句意群顺流 + 可复用表达 + 分数档。

用法: python bin/cet4_writing_explain.py
输出: var/cet4-daily/writing-explain.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
PAPER = ROOT / "var" / "cet4-daily" / "demo-whole-paper.json"
OUT = ROOT / "var" / "cet4-daily" / "writing-explain.json"

PROMPT = """你是四级写作讲解老师。下面是题目要求与一篇 165 词的范文，请做讲解。

【铁律】
- 禁止语法黑话（不许出现“先行词”“后置定语回拉”“从句倒装”等逼迫眼球回跳的说法）。
- 用「顺流镜头」：眼睛从左到右走，每个意群一块，用 \\ 切开，中文按块 1:1 对应。
- 中文直译，不增补原文没有的词，不堆成语。

【只输出 JSON】
{{"structure":[{{"para":1,"role":"这一段干什么（如：亮立场+让步）","cn":"这一段中文大意"}}],
 "sentences":[{{"en":"原句","chunks":"用 \\\\ 切分后的英文","cn":"逐块对应的中文","note":"这一句为什么这样写/可复用的地方"}}],
 "expressions":[{{"phrase":"可复用表达","cn":"中文","use":"什么场景用"}}],
 "bands":[{{"score":"13-15","desc":"这一档的要求与本篇差距"}}]}}

【题目要求】
{directions}

【范文】
{essay}
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


def main():
    paper = json.loads(PAPER.read_text(encoding="utf-8"))
    w = paper["writing"]
    prompt = PROMPT.format(directions=w["directions"][:2000], essay=w.get("model_essay", "")[:4000])
    data = parse_json(cb(prompt))
    if not data:
        print("parse failed")
        return 1
    print(f"sentences={len(data.get('sentences') or [])} expressions={len(data.get('expressions') or [])} "
          f"bands={len(data.get('bands') or [])}")
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
