# -*- coding: utf-8 -*-
"""一个代理只改一篇文章：以真题为样板 + 硬指标对齐（按用户 2026-11-05 的方案）。

每个任务只负责「一篇正文」，输入三样东西：
1. **一篇官方真题正文当样板**（让它照着学句式与信息密度）
2. **硬指标**（来自 baseline.json 的实测中位/区间）
3. 我们自己那篇正文
输出：改好的正文（段落数不变、事实不变）

指标区间（42 篇真题实测）：
  词数 340–367（中位 350）｜平均句长 17.4–20.4｜句长标准差 ≈8.5
  长词(≥9) 9.7–13.7%｜大纲词覆盖 11.5–17.6%｜从句/百词 2.0–3.5
  被动/百词 0.3–1.2｜Flesch 41.8–52.4｜≥30 词长句占比 ≈13%

用法: python cet4/bin/cet4_imitate.py --papers 81,82 --workers 3
      python cet4/bin/cet4_imitate.py --papers all --workers 3
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
PAPERS = ROOT / "var" / "cet4-daily" / "papers"
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """你在按官方真题的写法重写一篇四级阅读正文。**只处理这一篇，不要管别的**。

## 第一步：先读样板（一篇官方真题正文，务必模仿它的句式与信息密度，不要抄它的内容）
--- 样板开始 ---
{exemplar}
--- 样板结束 ---

## 第二步：硬指标（42 篇真题实测，必须落在区间内）
- 词数 340–367
- 平均句长 17.4–20.4 词；句长标准差 ≥8（长短必须悬殊：至少 2 句 ≥30 词，至少 2 句 ≤8 词）
- 长词（≥9 字母）占比 9.7–13.7%
- 大纲四级词覆盖 11.5–17.6%（别堆生僻词）
- 从句密度 2.0–3.5 个/百词；被动 0.3–1.2 个/百词
- Flesch 易读度 41.8–52.4
- 段落 4–7 段，段落长短不齐（最长段约是最短段的 2 倍以上）
- 数字 2–3 个、直接引语 1 处、具名机构或研究者 2–4 个

## 第三步：改我们这篇（事实、结论、段落顺序都不许变）
{passage}

## 硬约束
- **不许改变任何事实、数字、人名、因果关系**
- 段落数与段落顺序不变
- 题目定位句（含答案依据的句子）保持原意，可换句式但信息不许变
- 不许写成议论文爽文，不许升华结尾

只输出 JSON：{{"passage":"...","metrics":{"words":0,"wps":0,"sd":0,"long9":0,"long_sent_pct":0}}}"""


def cb(prompt: str, timeout: int = 2400) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jp(t: str):
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", t or ""):
        try:
            o, _ = dec.raw_decode(t[m.start():])
            if isinstance(o, dict):
                return o
        except json.JSONDecodeError:
            continue
    return {}


def exemplars(n: int = 12) -> list:
    out = []
    for md in sorted(BANK.rglob("*.md")):
        t = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
            body = t[m.end():]
            body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
            cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
            p = re.sub(r"[_*#]", "", (body[:cut.start()] if cut else "")[:4000]).strip()
            if 340 <= len(p.split()) <= 367:
                out.append(p)
    random.Random(7).shuffle(out)
    return out[:n]


def metrics(t: str) -> dict:
    sents = [s for s in re.split(r"(?<=[.!?])\s+", t) if len(s.split()) >= 3]
    L = [len(s.split()) for s in sents] or [0]
    words = re.findall(r"[A-Za-z']+", t)
    return {"words": len(t.split()), "wps": round(st.mean(L), 1),
            "sd": round(st.pstdev(L), 1) if len(L) > 1 else 0,
            "long9": round(100*sum(1 for w in words if len(w) >= 9)/max(1, len(words)), 1),
            "long_pct": round(100*sum(1 for x in L if x >= 30)/len(L), 1)}


def ok(m: dict) -> list:
    bad = []
    if not (335 <= m["words"] <= 372): bad.append(f"词数{m['words']}")
    if not (16.5 <= m["wps"] <= 21.5): bad.append(f"句长{m['wps']}")
    if m["sd"] < 7.5: bad.append(f"标准差{m['sd']}")
    if not (8 <= m["long9"] <= 15): bad.append(f"长词{m['long9']}%")
    if m["long_pct"] < 8: bad.append(f"长句{m['long_pct']}%")
    return bad


def one(task) -> str:
    pid, name, exemplar = task
    f = PAPERS / f"paper-{pid}.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    pp = d["reading"].get(name) or {}
    paras = pp.get("paragraphs") or []
    if not paras:
        return f"paper-{pid}/{name}: 无正文"
    text = "\n\n".join(x.get("en", "") for x in paras)
    m0 = metrics(text)
    prompt = (PROMPT.replace("{exemplar}", exemplar).replace("{passage}", text))
    best = None
    for _ in range(2):
        res = jp(cb(prompt))
        new = (res.get("passage") or "").strip()
        if not new:
            continue
        blocks = [x.strip() for x in re.split(r"\n\s*\n", new) if x.strip()]
        if len(blocks) != len(paras):
            continue
        m1 = metrics(new)
        score = len(ok(m1))
        if best is None or score < best[0]:
            best = (score, blocks, m1, ok(m1))
        if score == 0:
            break
    if not best:
        return f"paper-{pid}/{name}: 失败"
    score, blocks, m1, bad = best
    if score > 2:
        return f"paper-{pid}/{name}: 指标未达标（{','.join(bad)}），保留原稿"
    for para, blk in zip(paras, blocks):
        para["en"] = blk
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return (f"paper-{pid}/{name}: 词{m0['words']}→{m1['words']} 句长{m0['wps']}→{m1['wps']} "
            f"sd {m0['sd']}→{m1['sd']} 长句{m0['long_pct']}%→{m1['long_pct']}%"
            + (f"（残留 {','.join(bad)}）" if bad else ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", default="all")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    if args.papers == "all":
        pids = ["81", "82", "83", "84", "85", "86", "87", "97", "98", "99"]
    else:
        pids = [x for x in re.split(r"[,\s]+", args.papers) if x]
    ex = exemplars(12)
    tasks = []
    for i, pid in enumerate(pids):
        for j, name in enumerate(("passage1", "passage2")):
            tasks.append((pid, name, ex[(i * 2 + j) % len(ex)]))
    print(f"任务 {len(tasks)} 个（每个代理只改一篇），样板池 {len(ex)} 篇")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for msg in pool.map(one, tasks):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
