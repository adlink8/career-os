# -*- coding: utf-8 -*-
"""外刊改造 v5：科普说明文来源 + 中等幅度改写（保住原文的解释顺序，不做“重写成作文”）。

上一轮结论：新闻稿直贴/大幅改写都不行，唯一有苗头的是 ScienceDaily 科普改造。
本轮规则：
- 只取 ScienceDaily / The Conversation 这类说明文
- 改写照原文顺序走（背景 → 做法 → 发现 → 局限），不重排成议论文
- 只做词汇下沉 + 删枝蔓，不新增论点、不加“双方对称”、不加反思段
- 结尾用原文最后一句事实/保留意见，不写评价句
- 348-375 词，2-4 个真实专名

用法: python cet4/bin/cet4_adapt_v5.py --src <candidates.json> --n 7 --start 81
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

PROMPT = """把下面这篇科普报道改写成 348-375 词的英语短文，用于四级阅读。

## 改写方式（中等幅度，不是重写）
- **保持原文的解释顺序**：先说背景/问题，再说研究者做了什么，再说发现，最后说局限或下一步。段落的推进顺序照原文，不要重排成"观点-论证-结论"作文
- 段落 4-6 段，按原文自然分段，段落长度不必刻意拉平或拉大
- 全文 348-375 词：**靠删掉枝蔓**（记者的题外话、重复的引语、无关细节）压到范围，不要靠压缩每句信息
- 词汇下沉到四级：把 -tion/-ity 这类抽象名词堆叠拆成动词+宾语；一句话超过 30 词就切成两句
- 专名保留 2-4 个最核心的（研究机构、研究者、期刊、关键数字），其余删掉

## 禁止事项（每一条都被评委用原句点过名，逐条对照）
- 不许写"双方各有一半道理"式的平衡段
- **结尾不许用"局限/对冲"式声明**（Because the experiments were only in mice…、The authors acknowledge…、It remains unclear…），这类句子是模型补丁；结尾必须是一个**具体动作或结果**（某人做了什么、某数字变成什么）
- **"不是 A 而是 B"的对偶否定句最多 1 处**（rather than / not…but / instead of 都算），反复用会露
- **不许形容词/副词成串堆**（clear and practical, evidence-based 这种三连），每句最多 1 个评价性形容词
- 引语最多 1 处，且必须带具体细节（人名+数字/动作），**不许用引语来点题或下结论**
- 不许为了衔接硬塞 however / therefore / moreover；原文有几处就留几处
- 不许出现"这提醒我们 / in the end / only time will tell / 未来可期"

## 原文
来源：{source}
标题：{title}
正文：
{text}

## 题目（按真题实测口径）
5 题：细节 2、推断 1、词义/句意 1、主旨 1，且**每篇最多 1 道主旨题**。

每题硬要求：
- 题干必须**锚定正文里的具体主体**（人名/机构/现象名/研究结论），不许出现 "the topic / the passage" 这种泛化问法
- 题干 8-18 词；10 题问法各不相同，避免连续两题同一句式开头
- 4 个选项长度接近（最长不超过最短的 1.8 倍）
- 正确项**同义替换**（不许与原文逐字相同）；干扰项要像真题那四类：无中生有 / 偷换概念 / 因果倒置 / 范围扩大
- **每题只有一个选项成立**，不许出现两个都能选
- 每个干扰项给 opt_why（<=20 字），说明它错在哪一类

只输出 JSON：
{{"title":"<=12 词英文标题","passage":"正文（段落用 \\n\\n 分隔）","cn":"逐段中文直译",
 "kept_entities":["保留的专名"],
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
    ap.add_argument("--n", type=int, default=7)
    ap.add_argument("--start", type=int, default=81)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    d = json.loads((ROOT / args.src).read_text(encoding="utf-8"))
    picked = [p for p in (d.get("picked") or [])
              if re.search(r"ScienceDaily|Conversation", str(p.get("source")))]
    picked = picked[:args.n]
    print(f"说明文候选 {len(picked)} 篇（ScienceDaily / The Conversation）")

    def one(idx_item):
        idx, it = idx_item
        path = OUT / f"set-{idx:02d}.json"
        if path.exists():
            return f"set-{idx:02d} 已存在，跳过"
        prompt = (PROMPT.replace("{source}", str(it.get("source")))
                        .replace("{title}", str(it.get("title")))
                        .replace("{text}", (it.get("text") or "")[:8000]))
        j = jparse(cb(prompt))
        if not j or not j.get("questions"):
            return f"set-{idx:02d} 解析失败"
        j.update({"set": idx, "topic": it.get("cat") or "科普", "writer": "adapt-v5-explainer",
                  "source": it.get("source"), "source_url": it.get("url"), "source_title": it.get("title")})
        path.write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
        kept = j.get("kept_entities") or []
        return (f"set-{idx:02d} {len((j.get('passage') or '').split())}词 专名{len(kept)}个 "
                f"{str(it.get('title'))[:36]}")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for msg in pool.map(one, list(enumerate(picked, args.start))):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
