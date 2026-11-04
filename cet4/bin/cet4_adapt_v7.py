# -*- coding: utf-8 -*-
"""外刊改造 v7：先抽事实要点，再**从零组织语言**写（不做句级改写）。

依据（2026-11-04 对照实验）：
把 5 篇真题原文交给改写模型，再让判据判断——原文 5/5 判「真题」，改写版 5/5 判「改写」。
说明判据抓的是**改写残留**（生硬同义替换、机械换词），不是"AI 味"。
所以流程必须改成两条腿：
  1) 先把源文抽成「事实要点表」（entities / numbers / findings / sequence），扔掉原句
  2) 只依据要点表，用全新句子组织一篇 348-375 词说明文，不许出现与原文连续 5 词相同的片段

用法: python cet4/bin/cet4_adapt_v7.py --src <candidates.json> --n 6 --start 101
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
OUT = ROOT / "var" / "cet4-daily" / "ten-sets"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

FACTS = """把下面这篇外刊报道抽成「事实要点表」。**只抽事实，不要句子**：
- entities: 机构、人名、地名、产品名（<=6 个）
- numbers: 样本量、比例、时长、金额、年份（有就写，没有就空）
- findings: 研究/报道的核心发现（3-5 条，每条 <=15 字中文）
- sequence: 事件的推进顺序（先做什么、再做什么、最后什么，3-5 步）
- scope: 结论的适用范围与已知局限（1-2 条）

只输出 JSON：{"title_cn":"中文标题","entities":[...],"numbers":[...],"findings":[...],"sequence":[...],"scope":[...]}

原文：
{text}"""

WRITE = """你是一位英语科普作者。请**只用**下面的事实要点表写一篇英语短文（348-375 词），做四级阅读正文。

## 硬规则
1. **不许沿用源文的句子结构或词组**：与源文连续 5 个词相同的片段必须为零。你是在"知道这些事实之后重新写一篇"，不是改写
2. 用你自己的行文：句子长短交错（至少 1 句 <=6 词、1 句 >=35 词带插入语）
3. 段落 4-6 段，按事实推进的自然顺序，不需刻意对称
4. 事实要点表里的 entities / numbers 必须原样用上；findings 全部覆盖；scope 用一句具体事实表达，不要写"需要更多研究"
5. 结尾落在具体动作或结果上（谁做了什么、数字变成多少），不许总结、升华、设问、对冲
6. "not…but / rather than / instead of" 这类对偶句最多 1 处；不许形容词三连；引语 0 处
7. 美式拼写，四级词汇；超纲术语保留英文原词
8. 全文 348-375 词

## 事实要点表
{facts}

## 题目
5 题：细节 2、推断 1、词义/句意 1、主旨 1；正确项必须同义替换；4 选项长度接近；干扰项给 opt_why（<=20 字）。

只输出 JSON：
{"title":"<=12 词英文标题","passage":"正文（段落用 \\n\\n 分隔）","cn":"逐段中文直译",
 "questions":[{"no":46,"stem":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","why_correct":"...","opt_why":{"A":"...","B":"...","C":"...","D":"..."}}]}"""


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


def overlap5(mock: str, src: str) -> int:
    """统计与源文连续 5 词相同的片段数（改写残留的硬指标）。"""
    def norm(s):
        return re.findall(r"[a-z']+", (s or "").lower())
    a, b = norm(mock), norm(src)
    grams = {" ".join(b[i:i + 5]) for i in range(len(b) - 4)}
    return sum(1 for i in range(len(a) - 4) if " ".join(a[i:i + 5]) in grams)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--start", type=int, default=101)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    d = json.loads((ROOT / args.src).read_text(encoding="utf-8"))
    picked = [p for p in (d.get("picked") or []) if re.search(r"ScienceDaily|Conversation", str(p.get("source")))][:args.n]
    print(f"说明文源 {len(picked)} 篇")

    def one(idx_item):
        idx, it = idx_item
        path = OUT / f"set-{idx:02d}.json"
        if path.exists():
            return f"set-{idx:02d} 已存在，跳过"
        text = (it.get("text") or "")[:8000]
        facts = jp(cb(FACTS.replace("{text}", text)))
        if not facts:
            return f"set-{idx:02d} 事实抽取失败"
        out = jp(cb(WRITE.replace("{facts}", json.dumps(facts, ensure_ascii=False, indent=1))))
        if not out or not out.get("questions"):
            return f"set-{idx:02d} 写作失败"
        ov = overlap5(out.get("passage") or "", text)
        out.update({"set": idx, "topic": it.get("cat") or "科普", "writer": "facts-v7",
                    "source": it.get("source"), "source_url": it.get("url"), "source_title": it.get("title"),
                    "facts": facts, "overlap5": ov})
        path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        return (f"set-{idx:02d} {len((out.get('passage') or '').split())}词 与源文5词重叠 {ov} 处 "
                f"{str(it.get('title'))[:30]}")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for msg in pool.map(one, list(enumerate(picked, args.start))):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
