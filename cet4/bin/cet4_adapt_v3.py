# -*- coding: utf-8 -*-
"""结构移植：给模拟稿套上真题的「段落数 + 每段句数 + 逐句词数」骨架。

思路（不是提示词玄学，是可核对的硬结构）：
- 从 42 篇真题正文里抽出骨架：段落数、每段句数、逐句词数、结尾类型（细节/引语/疑问）
- 改写时把骨架当施工图：逐句对齐词数（±2），段落句数必须一致
- 这样句子长短起伏由真题决定，而不是模型自己的"均匀节奏"

用法: python cet4/bin/cet4_adapt_v3.py --src <candidates.json> --n 8 --start 51
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
OUT = ROOT / "var" / "cet4-daily" / "ten-sets"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
SKEL = ROOT / "var" / "cet4-daily" / "skeletons.json"

PROMPT = """把下面这篇外刊报道改写成一篇四级阅读正文，**必须严格按给定的句子骨架写**。

## 骨架（施工图，逐句对齐）
段落数：{paras}
每段句数：{sents_per_para}
逐句词数（按段落顺序列出，允许 ±2 词，不许大幅偏离）：{lens}
结尾类型：{ending}

## 改写规则
1. 专名只保留 2-4 个最核心的（机构/研究者/地名），其余人名、党派人物、头衔一律删或泛化
2. 允许 1 句原文短引语（<=15 词，用引号），其余句子重写，不许整句照抄
3. 全文 348-375 词；按骨架的句数写，句数不够就合并、够了就拆句
4. 结尾按「{ending}」这一类型收住，**不许**总结、升华、劝诫、设问，不许出现 "in the end / only time will tell / 这提醒我们"
5. 美式拼写；四级词汇，超纲术语保留英文原词；**优先用常见词**（大纲词覆盖率要接近真题的 14-15%，别堆生僻词）
6. **必须用 2-3 处转折/因果连接词**（however / therefore / for example / as a result），真题每千词约 3 个，上一版 0.4 个是破绽
7. **至少用 1 处破折号或分号**（真题每千词约 0.9 处，上一版 0 处是破绽）
8. 段落长短适度不齐即可，**不要极端悬殊**（真题段落词数标准差约 5，上一版 21 太夸张）
6. 题材保持科普/健康/教育/社会观察，不加时效锚点（不写"本周/今年/2026"）

## 原文
来源：{source}
标题：{title}
正文：
{text}

## 另外给 5 道题
细节 2、推断 1、词义/句意 1、主旨 1；正确项必须同义替换（不许与原文逐字相同）；4 选项长度接近；每个干扰项给 opt_why（<=20 字）。

只输出 JSON：
{{"title":"<=12 词英文标题","passage":"正文（段落用 \\n\\n 分隔）","cn":"逐段中文直译",
 "skeleton_used":{{"paras":{paras},"sents_per_para":{sents_per_para}}},
 "questions":[{{"no":46,"stem":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","why_correct":"...","opt_why":{{"A":"...","B":"...","C":"...","D":"..."}}}}]}}"""


def build_skeletons() -> list:
    out = []
    for md in sorted(BANK.rglob("*.md")):
        t = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
            body = t[m.end():]
            body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
            cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
            p = re.sub(r"[_*#]", "", (body[:cut.start()] if cut else "")[:4000]).strip()
            if not (330 <= len(p.split()) <= 390):
                continue
            paras = [x.strip() for x in re.split(r"\n\s*\n", p) if x.strip()]
            if len(paras) < 3:          # 段落切不出来的，用句子重新分组（每 3-5 句一段）
                sents = [s for s in re.split(r"(?<=[.!?])\s+", p) if s]
                paras, buf = [], []
                for s in sents:
                    buf.append(s)
                    if len(buf) >= 4:
                        paras.append(" ".join(buf))
                        buf = []
                if buf:
                    paras.append(" ".join(buf))
            lens, spara = [], []
            for para in paras:
                ss = [s for s in re.split(r"(?<=[.!?])\s+", para) if len(s.split()) >= 2]
                spara.append(len(ss))
                lens.extend(len(s.split()) for s in ss)
            if not (4 <= len(paras) <= 7) or not (13 <= len(lens) <= 26):
                continue
            last = lens[-1] if lens else 0
            ending = "具体细节收尾" if last <= 25 else "长句收尾但落在事实上"
            out.append({"src": f"{md.parent.name}/{md.stem}/{m.group(1)}", "paras": len(paras),
                        "sents_per_para": spara, "lens": lens, "words": sum(lens), "ending": ending})
    return out


def cb(prompt: str, timeout: int = 3000) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jparse(txt: str):
    t = re.sub(r"^```(?:json)?\s*", "", (txt or "").strip())
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--start", type=int, default=51)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    skels = build_skeletons()
    SKEL.write_text(json.dumps(skels, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"可用骨架 {len(skels)} 个（段落 {min(s['paras'] for s in skels)}-{max(s['paras'] for s in skels)}，"
          f"句数 {min(len(s['lens']) for s in skels)}-{max(len(s['lens']) for s in skels)}）")

    src = json.loads((ROOT / args.src).read_text(encoding="utf-8"))
    picked = (src.get("picked") or [])[:args.n]
    rng = random.Random(77)

    def one(idx_item):
        idx, it = idx_item
        path = OUT / f"set-{idx:02d}.json"
        if path.exists():
            return f"set-{idx:02d} 已存在，跳过"
        sk = rng.choice(skels)
        prompt = (PROMPT.replace("{paras}", str(sk["paras"]))
                        .replace("{sents_per_para}", json.dumps(sk["sents_per_para"]))
                        .replace("{lens}", json.dumps(sk["lens"]))
                        .replace("{ending}", sk["ending"])
                        .replace("{source}", str(it.get("source")))
                        .replace("{title}", str(it.get("title")))
                        .replace("{text}", (it.get("text") or "")[:7000]))
        d = jparse(cb(prompt))
        if not d or not d.get("questions"):
            return f"set-{idx:02d} 解析失败"
        d["set"] = idx
        d["topic"] = it.get("cat") or "外刊"
        d["writer"] = "adapt-v3-skeleton"
        d["source"], d["source_url"], d["source_title"] = it.get("source"), it.get("url"), it.get("title")
        d["skeleton"] = {"from": sk["src"], "paras": sk["paras"], "sents_per_para": sk["sents_per_para"]}
        path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        # 用实际稿子核一遍骨架吻合度
        paras = [x for x in re.split(r"\n\s*\n", (d.get("passage") or "").strip()) if x.strip()]
        lens = [len(s.split()) for para in paras for s in re.split(r"(?<=[.!?])\s+", para) if s.strip()]
        return (f'set-{idx:02d} {len((d.get("passage") or "").split())}词 段{len(paras)}/{sk["paras"]} '
                f'句{len(lens)}/{len(sk["lens"])} 骨架={sk["src"].split("/")[-1]}')

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for msg in pool.map(one, list(enumerate(picked, args.start))):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
