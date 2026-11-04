# -*- coding: utf-8 -*-
"""给「零数据」的正文补具体数字与具名来源（第 24 轮）。

依据：真卷正文每百词有 1.6–2.2 个数字、7–9 个具名实体；
我们 5 套（81/82/85/86/87）数字密度 <1.0，评委原话是「段段格言化、零数据」。

约束（很关键，不能为了加数据把题做废）：
- 只改**没有被任何题目定位**的句子；题目定位句原样保留
- 补的数字必须与文中已有事实一致，不许编造新结论
- 词数仍保持 348–375
- 改完必须重跑盲做，10/10 才算数

用法: python cet4/bin/cet4_add_data.py --papers 81,82,85,86,87 [--workers 2]
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
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """下面是一篇四级阅读正文（{words} 词）与它的 5 道题。这篇正文**几乎没有数字和具名来源**，
读起来像泛泛而谈，而真题正文每百词约有 2 个数字、7-9 个具名实体。

请只做一件事：**在不妨碍做题的前提下补数据**。
硬规则：
1. 题目定位句、以及含答案依据的句子**原样不动**
2. 在其余句子里插入 2-3 处具体信息：数字（样本量/比例/年份/时长）、机构名、研究者姓名、期刊名
3. 插入的信息必须与正文已有事实一致，不许新增结论、不许改主题
4. 全文仍 348-375 词；段落数与段落顺序不变
5. 输出完整正文，不要只给改动片段

正文：
{passage}

题目：
{qs}

只输出 JSON：{{"passage":"...","added":["新增了什么"]}}"""


def cb(prompt: str, timeout: int = 2400) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jp(t: str):
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", t or ""):
        try:
            obj, _ = dec.raw_decode(t[m.start():])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return {}


def density(t: str) -> float:
    w = max(1, len((t or "").split()))
    return round(100 * len(re.findall(r"\b\d[\d,.]*\b", t or "")) / w, 2)


def one(pid: str) -> str:
    f = PAPERS / f"paper-{pid}.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    logs = []
    for name in ("passage1", "passage2"):
        p = d["reading"].get(name) or {}
        paras = p.get("paragraphs") or []
        if not paras:
            continue
        text = "\n\n".join(x.get("en", "") for x in paras)
        if density(text) >= 1.0:
            logs.append(f"{name} 密度已够 {density(text)}")
            continue
        qs = "\n".join(f'{q["no"]}. {q["stem"]}\n' + "\n".join(q.get("options") or [])
                       for q in p.get("questions") or [])
        res = jp(cb(PROMPT.replace("{words}", str(len(text.split())))
                        .replace("{passage}", text).replace("{qs}", qs)))
        new = (res.get("passage") or "").strip()
        if not new:
            logs.append(f"{name} 补数据失败")
            continue
        wc = len(new.split())
        if not (340 <= wc <= 382):
            logs.append(f"{name} 词数越界 {wc}，放弃")
            continue
        blocks = [x.strip() for x in re.split(r"\n\s*\n", new) if x.strip()]
        if len(blocks) != len(paras):
            logs.append(f"{name} 段数变了 {len(blocks)}≠{len(paras)}，放弃")
            continue
        for para, blk in zip(paras, blocks):
            para["en"] = blk
        logs.append(f"{name} 密度 {density(text)}→{density(new)}（{wc} 词）")
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return f"paper-{pid}: " + "；".join(logs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", default="81,82,85,86,87")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    pids = [x for x in re.split(r"[,\s]+", args.papers) if x]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for msg in ex.map(one, pids):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
