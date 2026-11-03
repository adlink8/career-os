# -*- coding: utf-8 -*-
"""审查老师：把模拟题与真题对照，逐题挑毛病。

用法: python bin/cet4_review.py <paper.json> [--真题-dir knowledge/cet4-bank/01-历年真题-Markdown]
产物: 同目录 <stem>.review.json
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

PROMPT = """你是大学英语四级命题组的审查老师，熟悉 2020-2026 真题的选材与设问。
下面给你两份材料：
【A. 待审模拟题】（JSON）
【B. 真题样本】（两篇 Section C 原文 + 题目，用于对照）

请对照真题，逐项审查并只输出 JSON：
{{
 "verdict": "pass|needs_revision",
 "faithfulness": [{{"no":46,"issue":"题干/选项/答案与原文不符的具体点","evidence":"原文或选项原文"}}],
 "style_gap": ["与真题风格的具体差距，如题干过长、选项不同质、答案位置规律"],
 "difficulty": {{"words":0,"avg_sentence":0.0,"long10_pct":0.0,"vs_real":"偏难/接近/偏易","why":""}},
 "answer_distribution": {{"issue":"是否符合真题均匀分布","detail":""}},
 "must_fix": [{{"id":"F1","severity":"blocker|high|medium","problem":"","fix":""}}],
 "score": 0
}}
要求：不要客套；每条必须引用具体题号或原文；score 0-100。

【A. 待审模拟题】
{paper}

【B. 真题样本】
{real}
"""


def parse_json(text: str):
    t = re.sub(r"^```(?:json)?\s*", "", (text or "").strip())
    t = re.sub(r"\s*```$", "", t)
    i = t.find("{")
    if i < 0:
        return None
    depth = 0
    in_str = False
    esc = False
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
                frag = t[i:j+1]
                try:
                    return json.loads(frag)
                except json.JSONDecodeError:
                    return None
    return None

def real_excerpts(dir_path: Path, limit=2) -> str:
    out = []
    for p in sorted(dir_path.glob("*/*.md"))[:limit]:
        text = p.read_text(encoding="utf-8", errors="ignore")
        part = text.find("Part III")
        sub = text.find("Section C", part if part >= 0 else 0)
        start = text.find("#### Passage One", sub if sub >= 0 else 0)
        if start < 0:
            start = sub if sub >= 0 else 0
        body = text[start:start + 3000]
        out.append(f"--- {p.name} ---\n{body}")
    return "\n\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paper")
    ap.add_argument("--real-dir", default=str(ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"))
    args = ap.parse_args()
    src = Path(args.paper)
    paper = json.loads(src.read_text(encoding="utf-8"))
    real = real_excerpts(Path(args.real_dir))
    prompt = PROMPT.format(paper=json.dumps(paper, ensure_ascii=False), real=real)
    proc = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                          capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(ROOT))
    data = parse_json(proc.stdout or "")
    if not data:
        print("review parse failed:", (proc.stdout or "")[:300])
        return 1
    out = src.with_suffix(".review.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"verdict={data.get('verdict')} score={data.get('score')} must_fix={len(data.get('must_fix') or [])}")
    for f in (data.get("must_fix") or [])[:6]:
        print(f"  [{f.get('severity')}] {f.get('problem','')[:80]} -> {f.get('fix','')[:60]}")
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
