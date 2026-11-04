# -*- coding: utf-8 -*-
"""整卷盲做：把一套卷的四个板块交给独立“考生”，对照答案键看是否可答。

材料：选词填空（短文+词库）、信息匹配（段落+陈述）、双篇阅读（正文+题目）、听力（脚本+题目，
      因为盲做无法真的听音频，脚本按“音频内容”提供）。
输出：每板块对错题号 + 总正确率；写入 var/cet4-daily/line-compare/paper-solve.json

用法: python cet4/bin/cet4_paper_solve.py --papers 81,84,97
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

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "var" / "cet4-daily" / "papers"
OUT = ROOT / "var" / "cet4-daily" / "line-compare"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """你是四级考生，现在做一套完整试卷。**只依据给出的材料**作答，不许猜、不许用常识替代原文。

材料分四块：
1. Section A 选词填空：短文有 10 个空（26-35），从词库 A-O 中选
2. Section B 信息匹配：10 条陈述（36-45），每条对应 A-L 其中一段
3. Section C 仔细阅读：两篇文章，共 10 题（46-55）
4. 听力：下面是每段录音的文字内容与题目（1-25），按听到的内容作答

只输出 JSON：{"cloze":{"26":"A"},"match":{"36":"D"},"reading":{"46":"B"},"listening":{"1":"C"}}
不确定也要给一个答案，不要留空、不要解释。"""


def cb(prompt: str, timeout: int = 2400) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jp(t: str):
    t = re.sub(r"^```(?:json)?\s*", "", (t or "").strip())
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return {}
    frag = t[i:j + 1]
    for a in (frag, re.sub(r",\s*([}\]])", r"\1", frag)):
        try:
            return json.loads(a)
        except json.JSONDecodeError:
            continue
    return {}


def build_material(d: dict) -> str:
    r = d["reading"]
    parts = ["## Section A 选词填空", f'(词库：{json.dumps(r["cloze"].get("bank") or {}, ensure_ascii=False)})',
             r["cloze"].get("passage") or ""]
    parts += ["", "## Section B 信息匹配"]
    for k, v in (r["match"].get("paragraphs") or {}).items():
        parts.append(f"[{k}] {v}")
    parts.append("陈述：")
    for st in r["match"].get("statements") or []:
        parts.append(f'{st.get("no")}. {st.get("text")}')
    for name in ("passage1", "passage2"):
        p = r.get(name) or {}
        if not p.get("paragraphs"):
            continue
        parts += ["", f"## Section C {name}", p.get("title") or ""]
        parts += [x.get("en", "") for x in p.get("paragraphs") or []]
        parts.append("题目：")
        for q in p.get("questions") or []:
            parts.append(f'{q.get("no")}. {q.get("stem")}')
            parts += list(q.get("options") or [])
    parts += ["", "## 听力（录音文字）"]
    for sec in (d.get("listening") or {}).get("sections") or []:
        for k, pc in enumerate(sec.get("pieces") or [], 1):
            parts.append(f'=== Section {sec["name"]} 第{k}段：{pc.get("title")} ===')
            parts.append(pc.get("script") or "")
            for q in pc.get("questions") or []:
                parts.append(f'{q.get("no")}. {q.get("stem")}')
                parts += list(q.get("options") or [])
    return "\n".join(parts)


def key_of(d: dict) -> dict:
    r = d["reading"]
    key = {"cloze": {}, "match": {}, "reading": {}, "listening": {}}
    for n, a in (r["cloze"].get("answers") or {}).items():
        key["cloze"][str(n)] = str(a).upper()[:1]
    for n, a in (r["match"].get("answers") or {}).items():
        key["match"][str(n)] = str(a).upper()[:1]
    for name in ("passage1", "passage2"):
        for q in (r.get(name) or {}).get("questions") or []:
            key["reading"][str(q["no"])] = str(q.get("answer") or "").upper()[:1]
    for q in (d.get("listening") or {}).get("questions") or []:
        key["listening"][str(q["no"])] = str(q.get("answer") or "").upper()[:1]
    return key


def one(pid: str) -> dict:
    d = json.loads((PAPERS / f"paper-{pid}.json").read_text(encoding="utf-8"))
    mine = jp(cb(PROMPT + "\n\n" + build_material(d)))
    key = key_of(d)
    res = {"pid": pid, "sections": {}}
    for sec in ("cloze", "match", "reading", "listening"):
        got = {str(k): str(v).upper()[:1] for k, v in (mine.get(sec) or {}).items()}
        wrong = [n for n, a in key[sec].items() if got.get(n) != a]
        res["sections"][sec] = {"total": len(key[sec]), "right": len(key[sec]) - len(wrong),
                                "wrong": sorted(wrong, key=lambda x: int(x))}
    tot = sum(v["total"] for v in res["sections"].values())
    right = sum(v["right"] for v in res["sections"].values())
    res["total"], res["right"] = tot, right
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", default="81,84,97")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    pids = [x for x in re.split(r"[,\s]+", args.papers) if x]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(one, pids))
    for r in results:
        detail = "  ".join(f'{k} {v["right"]}/{v["total"]}' for k, v in r["sections"].items())
        print(f'paper-{r["pid"]}: {r["right"]}/{r["total"]} | {detail}')
        for k, v in r["sections"].items():
            if v["wrong"]:
                print(f'    {k} 不符: {v["wrong"]}')
    tot = sum(r["total"] for r in results); right = sum(r["right"] for r in results)
    print(f"\n合计 {right}/{tot} = {100*right/max(1,tot):.1f}%")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "paper-solve.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print("明细:", OUT / "paper-solve.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
