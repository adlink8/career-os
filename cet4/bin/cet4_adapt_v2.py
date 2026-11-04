# -*- coding: utf-8 -*-
"""外刊改造 v2：从真实外刊文章改写成四级 Section C 正文，**保留真实实体**。

上一轮实测的病根：改造时把机构名/人名抹成"a company / a city"，评委一眼识破。
本轮规则：原文里的机构名、人名、地名、数字、研究规模、引语一律保留；句子必须重写（不许整句照抄），
段落长短必须不齐，结尾不许升华，全文 348-375 词。

用法: python cet4/bin/cet4_adapt_v2.py --src var/cet4-daily/out_v3/candidates-2026-11-04.json --n 10
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

PROMPT = """把下面这篇外刊报道改写成一篇 348-375 词的英语短文，用来做大学英语四级阅读。

## 必须做到（这是硬要求，上一版失败在这里）
1. **只保留 2-4 个真实专名**：选最核心的机构名/研究者名/地名，其余人名、党派人物、职位头衔一律删掉或改成"a researcher""the agency"。真题专名中位 5 个，但超过 6 个就读成新闻汇编了
2. 允许保留 1 句原文短引语（用引号，<=15 词），其余句子必须重写，不许整句照抄
3. 段落 4-6 段，**长短必须明显不齐**（像 55 / 65 / 110 / 50 / 60 词这样），不要每段一样长
4. 全文 348-375 词（硬上限 375）；**句子必须长短混杂**：至少 1 句 ≤6 词、1 句 ≥35 词（带插入语或破折号），全篇句长标准差 ≥6 词，不要一串 15 词短句
5. 结尾**不许**总结、升华、劝诫、格言，也不许出现 "in the end / only time will tell / it remains to be seen / 这提醒我们" 这类套话；用一个具体细节或一句保留意见收尾
6. 用美式拼写；词汇控制在大纲内（四级），专业术语保留英文原词
7. 不要"总-分-总"，不要"首先/其次/最后"式连接词堆砌
8. **题材要像真题**：科普、健康、教育、社会观察优先；避免党派政治、公司商业新闻、时效性强的时事（不许出现"本周/今年/2026"这类时间锚点）

## 原文
来源：{source}
标题：{title}
正文：
{text}

## 另外给 5 道题
- 细节 2、推断 1、词义/句意 1、主旨 1
- 正确项必须是同义替换（不能与原文逐字相同）；4 个选项长度接近
- 干扰项用真实陷阱（无中生有/偷换概念/因果倒置/范围扩大），每个给 opt_why（<=20 字）

只输出 JSON：
{{"title":"英文标题（<=12 词，不用冒号堆副标题）","passage":"正文（段落用 \\n\\n 分隔）","cn":"逐段中文直译",
 "kept_entities":["你保留的真实机构/人名/数字"],
 "questions":[{{"no":46,"stem":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","why_correct":"...","opt_why":{{"A":"...","B":"...","C":"...","D":"..."}}}}]}}"""


def cb(prompt: str, timeout: int = 2400) -> str:
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
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--start", type=int, default=31)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    src = json.loads((ROOT / args.src).read_text(encoding="utf-8"))
    picked = (src.get("picked") or [])[:args.n]
    print(f"外刊候选 {len(picked)} 篇，输出版本号从 set-{args.start:02d} 起")

    def one(idx_item):
        idx, it = idx_item
        path = OUT / f"set-{idx:02d}.json"
        if path.exists():
            return f"set-{idx:02d} 已存在，跳过"
        prompt = (PROMPT.replace("{source}", str(it.get("source")))
                        .replace("{title}", str(it.get("title")))
                        .replace("{text}", (it.get("text") or "")[:7000]))
        d = jparse(cb(prompt))
        if not d or not d.get("questions"):
            return f"set-{idx:02d} 解析失败（{str(it.get('title'))[:30]}）"
        d["set"] = idx
        d["topic"] = it.get("cat") or "外刊"
        d["writer"] = "adapt-v2"
        d["source"] = it.get("source")
        d["source_url"] = it.get("url")
        d["source_title"] = it.get("title")
        path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        kept = d.get("kept_entities") or []
        return (f"set-{idx:02d} {len((d.get('passage') or '').split())}词 保留实体 {len(kept)} 个"
                f"（{', '.join(map(str, kept[:3]))}）")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for msg in pool.map(one, list(enumerate(picked, args.start))):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
