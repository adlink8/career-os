# -*- coding: utf-8 -*-
"""选词填空逐空解析：空位语法槽 + 为什么填它 + 其它候选为什么不行。

用法: python cet4/bin/cet4_cloze_explain.py
输出: var/cet4-daily/cloze-explain.json
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
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
PAPER = ROOT / "var" / "cet4-daily" / "demo-whole-paper.json"
OUT = ROOT / "var" / "cet4-daily" / "cloze-explain.json"

PROMPT = """你是四级选词填空讲解老师。下面是一篇带 10 个空的文章、15 词词库和答案。逐个空做讲解。

【铁律】
- 不许语法黑话（禁止“先行词/后置定语回拉”之类）。用「顺流镜头」：从左到右，意群用 \\ 切开，中文按块 1:1 对应。
- 中文直译，不增补原文没有的词。
- **一条一句话，能删的字全删**：slot <= 30 汉字，why <= 30 汉字，reject <= 25 汉字（只点名 2 个干扰字母，不逐个展开）。
- 不写"综上所述/由此可见"这类废话；讲解要落到这个空本身。

【只输出 JSON】
{{"blanks":[{{"no":26,"answer":"D","word":"intelligence",
  "slot":"这个空在句子里充当什么（<=30字）",
  "why":"为什么只能填它（<=30字，指出搭配/并列/复现线索）",
  "reject":"哪 2 个候选为什么不行（<=25字）",
  "cn":"填好之后这句的顺流中文"}}],
 "passage_cn":["第 1 句中文","第 2 句中文"]}}

【文章（__26__..__35__ 为空）】
{passage}

【词库】
{bank}

【答案】
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
                    if isinstance(obj, dict) and obj.get("blanks"):
                        return obj
                    break
    return None


def main():
    paper = json.loads(PAPER.read_text(encoding="utf-8"))
    c = paper["reading"]["cloze"]
    prompt = PROMPT.format(passage=c["passage"][:4000],
                           bank=json.dumps(c["bank"], ensure_ascii=False),
                           answers=json.dumps(c["answers"], ensure_ascii=False))
    data = parse_json(cb(prompt))
    if not data:
        print("parse failed")
        return 1
    print(f"blanks={len(data.get('blanks') or [])} passage_cn={len(data.get('passage_cn') or [])}")
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
