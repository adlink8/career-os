# -*- coding: utf-8 -*-
"""写作提示词 v2：把「真题长什么样」的实测结构写进约束，并用真题原文当风格样板。

依据（42 篇真题实测，见 var/cet4-daily/real-style-stats.json）：
- 段落 4-8 段，长短悬殊（常见 50-70 / 100-120 / 45-60 词混排）
- 句长均值 18.5 词，标准差中位 8.1（必须长短混杂：至少 1 句 ≤6 词、1 句 ≥35 词）
- 42 篇里 26 篇**完全没有年份**，25 篇含一处引语，数字中位 1 个
- 结尾极少总结升华（这条正是之前被判"模拟"的主因）

用法: python cet4/bin/cet4_writer_v2.py --n 10 --start 11 [--workers 3]
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
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
OUT = ROOT / "var" / "cet4-daily" / "ten-sets"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

TOPICS = [
    ("循环经济", "某二手平台把退货商品重新分级销售，试点数据与商家反应"),
    ("高校食堂", "一所大学取消一次性餐盒后，学生与后勤的成本账"),
    ("城市绿化", "街道换种耐旱树种后，浇水维护费用与居民评价的变化"),
    ("远程办公", "一家中型企业允许混合办公半年后的人员流动与协作问题"),
    ("运动损伤", "业余跑者过度训练与受伤率之间的一项跟踪观察"),
    ("老年再就业", "退休技工返聘到社区维修站的用工与培训安排"),
    ("儿童阅读", "社区图书馆把借书与讲故事活动绑定后的借阅变化"),
    ("地方特产", "某县把小作坊食品做成标准包装后遇到的质检与销路问题"),
    ("宿舍噪音", "高校宿舍夜间噪音投诉的变化与隔音改造的实际效果"),
    ("共享停车", "写字楼车位夜间向居民开放试点的使用率与纠纷"),
]

WRITER = """你是四级阅读命题老师，任务：写一篇**可以被当成历年真题**的四级 Section C 正文 + 5 道选择题。

## 真题是什么样（下面是 42 篇真题的实测结构，必须照做）
- **全文 348-375 词，硬上限 375，写超就删句子**（这是真题实测区间，超了就不像）
- 段落 4-6 段，长短悬殊：按 60/70/110/55/60 词左右分配，**不要每段一样长**
- 全文 13-25 句，句长均值 18-20 词，但**必须长短混杂**：至少 1 句 ≤6 词，至少 1 句 ≥35 词（允许插入语、破折号、括号补充）
- 42 篇真题里 **26 篇完全没有年份**，所以不要硬塞年份；可以有机构名、人名、职位，允许一处引语（用引号）
- 数字不要取整：像 "about 4,000"、"one in five"、"roughly 12 percent" 这种，全篇 0-3 个
- 结尾**不许总结升华、不许劝诫、不许格言**：以具体细节、一处保留意见或一个未解的问题收尾
- 用美式拼写（organization / program / center），不用英式
- 语言要像记者或科普作者写的，能读出具体场景（谁、在哪、做了什么），不要"总-分-总"作文腔

## 风格样板（真实真题原文，只学语感，不要抄句子）
{exemplars}

## 这次要写的话题
{topic}

## 题目要求
- 5 题：细节 2、推断 1、词义/句意 1、主旨 1
- 每题 4 选项，正确项必须是**同义替换**（不能与原文逐字相同），干扰项用真实陷阱（无中生有/偷换概念/因果倒置/范围扩大）
- 4 个选项长度要接近，不要让正确项明显更长
- 每题给 opt_why（每个选项 <=20 字说明）

只输出 JSON：
{{"title":"英文标题（不用冒号堆副标题）","passage":"正文（段落用 \\n\\n 分隔）","cn":"逐段中文直译","questions":[{{"no":46,"stem":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","why_correct":"...","opt_why":{{"A":"...","B":"...","C":"...","D":"..."}}}}]}}"""


def exemplars(n: int = 2, seed: int = 33) -> str:
    pool = []
    for md in sorted(BANK.rglob("*.md")):
        if md.parent.name < "2024":
            continue
        t = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
            body = t[m.end():]
            body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
            cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
            p = re.sub(r"[_*#]", "", (body[:cut.start()] if cut else "")[:4000]).strip()
            if 300 <= len(p.split()) <= 380:
                pool.append(p)
    picked = random.Random(seed).sample(pool, n)
    return "\n\n---\n\n".join(picked)


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
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--start", type=int, default=11)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    ex = exemplars(2)

    def one(idx_topic):
        idx, (name, desc) = idx_topic
        path = OUT / f"set-{idx:02d}.json"
        if path.exists():
            return f"set-{idx:02d} 已存在，跳过"
        raw = cb(WRITER.replace("{exemplars}", ex).replace("{topic}", f"{name}：{desc}"))
        d = jparse(raw)
        if not d or not d.get("questions"):
            return f"set-{idx:02d} 解析失败"
        d["set"] = idx
        d["topic"] = name
        d["writer"] = "v2"
        path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        return f"set-{idx:02d} {name} {len((d.get('passage') or '').split())}词 {len(d['questions'])}题"

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for msg in pool.map(one, list(enumerate(TOPICS[:args.n], args.start))):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
