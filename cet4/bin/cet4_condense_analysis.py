# -*- coding: utf-8 -*-
"""把整卷里 reading 的 option_analysis/trap 压成一句话（只改解析文字，不动题干/选项/答案）。

用法: python cet4/bin/cet4_condense_analysis.py var/cet4-daily/demo-whole-paper.json
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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """你是四级阅读解析编辑。把下面 5 道题的解析压缩成**一句话**。不许改题干、选项、答案字母。

【硬规则】
- 正确项的 why <= 22 个汉字，说清"原文哪句 → 哪个词换成了哪个词"。
- 每个干扰项的 why <= 18 个汉字，开头用四类术语之一：无中生有 / 偷换概念 / 因果倒置 / 范围扩大。
- trap 字段 <= 15 个汉字，只写干扰手法组合。
- 删掉"综上所述/需要注意的是/考生应"这类废话；不复述整句原文。
- 保留原有 letter 与 correct 标记，顺序不变。

【只输出 JSON】
{{"questions":[{{"no":46,"trap":"","option_analysis":[{{"letter":"A","correct":false,"why":""}}]}}]}}

【题目】
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
                    if isinstance(obj, dict) and obj.get("questions"):
                        return obj
                    break
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paper")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pp = Path(args.paper)
    paper = json.loads(pp.read_text(encoding="utf-8"))
    before = {k: paper["reading"][k]["questions"] for k in ("passage1", "passage2")}
    payload = []
    for k in ("passage1", "passage2"):
        for q in paper["reading"][k]["questions"]:
            payload.append({"no": q["no"], "answer": q["answer"], "stem": q["stem"][:120],
                            "trap": q.get("trap", ""),
                            "option_analysis": [{"letter": x.get("letter"), "correct": x.get("correct"),
                                                 "why": x.get("why", "")}
                                                for x in (q.get("option_analysis") or []) if isinstance(x, dict)]})

    data = parse_json(cb(PROMPT.format(questions=json.dumps(payload, ensure_ascii=False)[:14000])))
    if not data:
        print("parse failed")
        return 1

    by_no = {q["no"]: q for q in data["questions"]}
    changed = 0
    for k in ("passage1", "passage2"):
        for q in paper["reading"][k]["questions"]:
            new = by_no.get(q["no"])
            if not new:
                continue
            old_letters = [x.get("letter") for x in (q.get("option_analysis") or []) if isinstance(x, dict)]
            new_letters = [x.get("letter") for x in (new.get("option_analysis") or [])]
            if sorted(old_letters) != sorted(new_letters):
                print(f"  Q{q['no']} 选项字母不匹配，跳过")
                continue
            for x in new["option_analysis"]:
                x["correct"] = (x.get("letter") == q.get("answer"))
            q["option_analysis"] = new["option_analysis"]
            if new.get("trap"):
                q["trap"] = new["trap"]
            changed += 1

    # 答案与选项不可变
    for k in ("passage1", "passage2"):
        for a, b in zip(before[k], paper["reading"][k]["questions"]):
            assert a["answer"] == b["answer"] and a["options"] == b["options"], "答案/选项被改动"

    lens = [len(x.get("why") or "") for k in ("passage1", "passage2")
            for q in paper["reading"][k]["questions"]
            for x in (q.get("option_analysis") or [])]
    print(f"condensed {changed} questions | why 长度 max={max(lens)} mean={sum(lens)//len(lens)}")
    if args.dry_run:
        print("dry-run，未写入")
        return 0
    pp.write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written", pp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
