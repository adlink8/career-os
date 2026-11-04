# -*- coding: utf-8 -*-
"""难度判定（只由 LLM 做）：把真题正文与模拟正文匿名混排，交给独立 CB 逐段打 band。

脚本只负责收集文本、分批、汇总分布；判定权在 LLM。
用法: python cet4/bin/cet4_diff_judge.py [--batch 8] [--workers 3] [--only sectionC]
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
import random
import re
import statistics as st
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
OUT = ROOT / "var" / "cet4-daily" / "difficulty-judge.json"

PROMPT = """你是大学英语四级命题组成员。下面每段英文都是一篇四级阅读文章正文（约 340-370 词）。
请只凭文本判断：如果把它放进四级真题，难度处于什么位置。

对每段输出：
- id：照抄编号
- band：1-5 整数（1=明显低于真题，2=略低于真题，3=与真题相当，4=略高于真题，5=明显高于真题）
- why：<=25 字，点出主要依据（词汇/句法/信息密度，任选最突出的）

只输出 JSON 数组，不要任何解释文字：
[{"id":"R1","band":3,"why":"..."}]

待判定段落：
<<<ITEMS>>>"""


def parse(txt: str):
    t = (txt or "").strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("["), t.rfind("]")
    if i < 0 or j <= i:
        return []
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return []


def collect_real():
    out = []
    for md in sorted(BANK.rglob("*.md")):
        t = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
            body = t[m.end():]
            body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
            cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
            p = re.sub(r"[_*#]", "", (body[:cut.start()] if cut else body[:4000]).strip())
            if len(p.split()) >= 250:
                out.append({"id": f'{md.parent.name}-{md.stem[-1]}-{m.group(1)[0]}',
                            "text": p, "group": "real"})
    return out


def collect_mock():
    d = json.loads((ROOT / "var" / "cet4-daily" / "demo-whole-paper.json").read_text(encoding="utf-8"))
    out = []
    for k, tag in (("passage1", "MOCK-P1"), ("passage2", "MOCK-P2")):
        text = "\n\n".join((p.get("en") or "").strip() for p in d["reading"][k]["paragraphs"])
        out.append({"id": tag, "text": text, "group": "mock"})
    return out


def judge(chunk):
    body = "\n\n".join(f'[{it["id"]}]\n{it["text"]}' for it in chunk)
    proc = subprocess.run([str(CB), "-p", "--output-format", "text"],
                          input=PROMPT.replace("<<<ITEMS>>>", body),
                          capture_output=True, text=True, encoding="utf-8", timeout=1800, cwd=str(ROOT))
    got = {str(r.get("id")): r for r in parse(proc.stdout or "") if r.get("id")}
    print(f"  batch {chunk[0]['id']}..{chunk[-1]['id']}: {len(got)}/{len(chunk)}", flush=True)
    return got


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    items = collect_real() + collect_mock()
    random.Random(2026).shuffle(items)
    print(f"段数: {len(items)}（真题 {sum(1 for i in items if i['group']=='real')} + 模拟 {sum(1 for i in items if i['group']=='mock')}）")
    chunks = [items[i:i + args.batch] for i in range(0, len(items), args.batch)]
    res = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for got in ex.map(judge, chunks):
            res.update(got)

    real = [int(r["band"]) for r in res.values() if r.get("id", "").startswith(("20", "MOCK") ) is False]
    rows = []
    for it in items:
        r = res.get(it["id"]) or {}
        rows.append({"id": it["id"], "group": it["group"], "band": r.get("band"), "why": r.get("why")})
    rb = [r["band"] for r in rows if r["group"] == "real" and isinstance(r["band"], int)]
    mb = [r["band"] for r in rows if r["group"] == "mock" and isinstance(r["band"], int)]
    print("\n真题 band 分布:", sorted(rb))
    print("模拟 band:", mb)
    if rb:
        print(f"真题均值 {st.mean(rb):.2f} 中位 {st.median(rb)} 范围 {min(rb)}-{max(rb)}")
    if mb:
        print(f"模拟均值 {st.mean(mb):.2f} 中位 {st.median(mb)}")
    for r in rows:
        if r["group"] == "mock":
            print(f'  {r["id"]}: band={r["band"]}  {r["why"]}')
    OUT.write_text(json.dumps({"rows": rows, "real_mean": st.mean(rb) if rb else None,
                               "mock_mean": st.mean(mb) if mb else None}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print("json ->", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
