# -*- coding: utf-8 -*-
"""去精修：把正文的句长分布改到接近真卷（第 31 轮实测的唯一显著差距）。

实测（42 篇真题 vs 20 篇模拟正文）：
| 指标 | 真题 | 模拟 |
|---|---:|---:|
| 平均句长 | 19.24 | 17.61 |
| 句长标准差 | 8.53 | **6.13** |
| ≥30 词长句占比 | 13.67% | **4.34%** |
| ≤8 词短句占比 | 9.17% | 8.72% |

评委原话「语言过于精致统一、像机构精修稿」对应的就是**长句缺失 + 句长过于均匀**。

做法：对每篇正文，挑 2–3 处相邻短句，合并成 30–45 词的复合句（关系从句/分词短语/破折号插入语），
不许改事实、不许动题目定位句；改完校验句长分布与盲做。

用法: python cet4/bin/cet4_depolish.py --papers 81,82,... [--workers 3]
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
import statistics as st
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "var" / "cet4-daily" / "papers"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """下面是一篇四级阅读正文。它现在**句子太短太匀**（句长标准差约 6，真题约 8.5；≥30 词长句几乎没有，真题约 14%）。

请做「去精修」，只调句法，不改事实、不改信息顺序：
1. 挑 3 处**相邻的两三个短句**，合并成 30–45 词的复合句（用关系从句、分词短语、或破折号插入语，句子仍要通顺、口语可读）
2. 再保留 1–2 处很短的句子（≤8 词）不要合，制造长短反差
3. 不许改变任何事实、数字、人名；题目定位句（含答案依据的句子）原样保留
4. 全文词数 348–378，段落数与顺序不变

正文：
{passage}

只输出 JSON：{{"passage":"...","merged":3}}"""


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


def metrics(t: str) -> dict:
    sents = [s for s in re.split(r"(?<=[.!?])\s+", t) if len(s.split()) >= 3]
    if len(sents) < 3:
        return {"sd": 0, "long": 0, "wps": 0}
    L = [len(s.split()) for s in sents]
    return {"wps": round(st.mean(L), 1), "sd": round(st.pstdev(L), 1),
            "long": round(100 * sum(1 for x in L if x >= 30) / len(L), 1)}


def one(pid: str) -> str:
    f = PAPERS / f"paper-{pid}.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    logs = []
    for name in ("passage1", "passage2"):
        pp = d["reading"].get(name) or {}
        paras = pp.get("paragraphs") or []
        if not paras:
            continue
        text = "\n\n".join(x.get("en", "") for x in paras)
        m0 = metrics(text)
        if m0["long"] >= 10 and m0["sd"] >= 7.5:
            logs.append(f"{name} 已达标(sd {m0['sd']})")
            continue
        res = jp(cb(PROMPT.replace("{passage}", text)))
        new = (res.get("passage") or "").strip()
        if not new:
            logs.append(f"{name} 失败")
            continue
        blocks = [x.strip() for x in re.split(r"\n\s*\n", new) if x.strip()]
        wc = len(new.split())
        if len(blocks) != len(paras) or not (340 <= wc <= 382):
            logs.append(f"{name} 结构不合({len(blocks)}段/{wc}词)，放弃")
            continue
        m1 = metrics(new)
        if m1["sd"] < m0["sd"] + 0.8:
            logs.append(f"{name} 提升不足(sd {m0['sd']}→{m1['sd']})，放弃")
            continue
        for para, blk in zip(paras, blocks):
            para["en"] = blk
        logs.append(f"{name} sd {m0['sd']}→{m1['sd']} 长句 {m0['long']}%→{m1['long']}%（{wc} 词）")
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return f"paper-{pid}: " + "；".join(logs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", default="81,82,83,84,85,86,87,97,98,99")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    pids = [x for x in re.split(r"[,\s]+", args.papers) if x]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for msg in ex.map(one, pids):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
