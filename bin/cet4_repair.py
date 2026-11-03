# -*- coding: utf-8 -*-
"""按审查报告 must_fix 重写题目，循环到通过或达到轮数上限。

用法: python bin/cet4_repair.py <paper.json> <review.json> [--rounds 2]
产物: 就地更新 paper.json（备份 .bak），并重跑审查
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

PROMPT = """你是四级命题老师，现在按审查报告修改这套阅读题的 5 道题。只改 questions，不要改 passage/paragraphs。
审查报告（JSON）：
{review}

当前题目：
{questions}

要求：
1) 逐条解决 must_fix 与 faithfulness 里的问题；双答案必须消除。
2) 保持题干具体、选项同质、正确项同义替换、错误项写具体错因。
3) 答案覆盖至少 3 个不同字母；每题 evidence 必须逐字在原文。
4) 题号必须是 46-50；每题给 stem_cn 与 options_cn（顺流直译中文）。
4b) 同题选项长度差 <=3 词，正确项不得总是最长。
4c) 题干必须指向原文的具体对象（哪两个地点/哪类记忆），不得换对象；正确项不得越出原文（如把 may sound like 写成 is）。
4d) 保留可核细节：国家/机构类型、样本量、数据、研究结论，不要只剩抽象概括。
5) 只输出 JSON：{{"questions":[...]}}，结构与原题一致（含 option_analysis）。
"""


def cb(prompt: str) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(ROOT))
    return p.stdout or ""


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



def refresh_difficulty(paper):
    import re as _re
    p = paper.get("passage", "")
    ws = _re.findall(r"[A-Za-z][A-Za-z'-]*", p)
    n = len(ws)
    sents = [x for x in _re.split(r"(?<=[.!?])\s+", p) if len(_re.findall(r"[A-Za-z][A-Za-z'-]*", x)) >= 4]
    avg = round(n / max(1, len(sents)), 1)
    long10 = round(100 * sum(1 for w in ws if len(w) >= 10) / max(1, n), 1)
    paper["difficulty"] = {**(paper.get("difficulty") or {}), "words": n, "avg_sentence": avg, "long10_pct": long10}

def review(paper_path: Path):
    subprocess.run([sys.executable, str(ROOT / "bin" / "cet4_review.py"), str(paper_path)],
                   check=False, capture_output=True, text=True, encoding="utf-8", timeout=1200)
    rp = paper_path.with_suffix(".review.json")
    return json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paper")
    ap.add_argument("review")
    ap.add_argument("--rounds", type=int, default=2)
    args = ap.parse_args()
    pp = Path(args.paper)
    paper = json.loads(pp.read_text(encoding="utf-8"))
    rev = json.loads(Path(args.review).read_text(encoding="utf-8"))
    for r in range(1, args.rounds + 1):
        prompt = PROMPT.format(review=json.dumps(rev, ensure_ascii=False),
                               questions=json.dumps(paper["questions"], ensure_ascii=False))
        data = parse_json(cb(prompt))
        if not data or not data.get("questions"):
            print(f"round {r}: writer parse failed")
            break
        for q in data["questions"]:
            for oa in q.get("option_analysis") or []:
                oa["correct"] = (oa.get("letter") == q.get("answer"))
        paper["questions"] = data["questions"]
        res = check(paper)
        print(f"round {r}: validate={res['ok']} {res['errors'][:3]}")
        refresh_difficulty(paper)
        pp.write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding="utf-8")
        # 题目改了必须重建音频/字幕/HTML，否则纸面与音频不同源
        subprocess.run([sys.executable, str(ROOT / "bin" / "cet4_tts.py"), str(pp)], check=False,
                       capture_output=True, text=True, encoding="utf-8", timeout=600)
        subprocess.run([sys.executable, str(ROOT / "bin" / "cet4_build_html.py"), str(pp),
                        str(pp.with_suffix(".html"))], check=False, capture_output=True, text=True, encoding="utf-8")
        rev = review(pp)
        print(f"round {r}: review verdict={rev.get('verdict')} score={rev.get('score')} fixes={len(rev.get('must_fix') or [])}")
        if rev.get("verdict") == "pass" or (rev.get("score") or 0) >= 80:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
