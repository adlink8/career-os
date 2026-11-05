# -*- coding: utf-8 -*-
"""把单篇 Section C 稿组装成整卷（补选词填空/匹配/翻译/写作），字段对齐 demo-whole-paper.json。

输入：set-XX.s2.json（只有 passage1 式正文 + 5 题）
输出：paper-XX.json（meta/writing/listening(占位)/reading{cloze,match,passage1,passage2}/translation）

说明：听力不在本脚本范围（需要 TTS 与音轨），先留空数组，渲染时自动跳过。

用法: python cet4/bin/cet4_compose_paper.py --set set-83.s2.json [--out var/cet4-daily/papers]
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
SRC = ROOT / "var" / "cet4-daily" / "ten-sets"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """你在组一份大学英语四级模拟卷，已经有一篇阅读正文（Section C Passage One）。现在请补齐其余部分。

## 已有（不要改）
Section C Passage One 主题：{topic}；标题：{title}

## 请产出（严格遵守四级格式与实测基准）

### 1. 选词填空（Section A，26-35）
- 短文 **188-316 词**，10 空写 `__26__` … `__35__`
- 词库 15 词（A-O），**词性配比 名词 4 / 动词 4 / 形容词 4 / 副词 3**
- **词库内不许有同根词**（不能同时出现 adapt 与 adaptive、most 与 mostly）
- **答案词的字母要散开**：不许 10 个答案全在 A-J，三个区间（A-E / F-J / K-O）各 2-5 个
- **答案词不许在短文别处出现**（同一词或其变形），否则这空等于送分
- 每个空**只有一个词能填**；5 个干扰项必须"词性对得上但语义填不进"
- 给 answers 与每空的 why（<=20 字）

### 2. 信息匹配（Section B，36-45）
- 段落 **12-15 段**（A 起编），段落正文合计 **950-1100 词**，单段 60-120 词
- 10 条陈述（36-45），**做法照真题：从对应段落里取一句关键句，轻微改写（保留大部分原词），不做深度改写**
- 每条**只对应一个段落**；10 条陈述的顺序**不许跟着段落的字母顺序走**（要打乱）

### 3. 翻译（Part IV）
- 中文 **138-159 汉字**（硬区间），题材为单一文化/社会/教育主题
- 首句定义式「X 是……的……」；专有名词后**最多 1 处**英文括注
- 给参考译文（3-6 句、长短错落）与 4 个踩分点

### 4. 写作（Part I）
- directions **45-60 词**：一句场景 + 一句任务 + 「You should write at least 120 words but no more than 180 words.」
- **只许一个场景、一条任务**，不许叠加"至少两个理由""处理反方观点""自拟标题"
- 范文 140-170 词

只输出 JSON：
{{"cloze":{{"title":"英文标题","passage":"含 __26__ … __35__ 的短文","bank":{{"A":"word","B":"word", "...":"..."}},"answers":{{"26":"D","27":"G", "...":"..."}},"blanks":[{{"no":26,"answer":"D","word":"...","why":"<=20字"}}]}},
 "match":{{"title":"英文标题","paragraphs":{{"A":"...","B":"...","...":"..."}},"statements":[{{"no":36,"text":"..."}}],"answers":{{"36":"D","...":"..."}}}},
 "translation":{{"zh":"...","reference":"...","points":["..."]}},
 "writing":{{"directions":"...","model_essay":"...","deductions":["..."]}}}}"""


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


def compose(set_file: Path, out_dir: Path) -> str:
    d = json.loads(set_file.read_text(encoding="utf-8"))
    res = jp(cb(PROMPT.replace("{topic}", str(d.get("topic"))) .replace("{title}", str(d.get("title")))))
    if not res.get("cloze") or not res.get("match"):
        return f"{set_file.stem}: 补齐失败"
    passage = {
        "title": d.get("title"),
        "title_cn": "",
        "topic": d.get("topic"),
        "paragraphs": [{"en": p, "sentences": []} for p in re.split(r"\n\s*\n", d.get("passage") or "") if p.strip()],
        "questions": d.get("questions") or [],
        "source": d.get("source"),
        "source_url": d.get("source_url"),
    }
    paper = {
        "meta": {"name": f"四级模拟整卷（{d.get('topic')}）", "date": "2026-11-04", "total": 57},
        "writing": res.get("writing") or {},
        "listening": {"sections": [], "questions": []},
        "reading": {"cloze": res.get("cloze") or {}, "match": res.get("match") or {},
                    "passage1": passage, "passage2": {"title": "", "paragraphs": [], "questions": []}},
        "translation": res.get("translation") or {},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"paper-{set_file.stem.split('-')[1].split('.')[0]}.json"
    out.write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding="utf-8")
    return (f"{out.name}: 选词 {len(paper['reading']['cloze'].get('answers') or {})} 空 / "
            f"匹配 {len(paper['reading']['match'].get('paragraphs') or {})} 段 "
            f"{len(paper['reading']['match'].get('statements') or [])} 陈述 / "
            f"翻译 {len(str((paper['translation'] or {}).get('zh') or ''))} 字")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, nargs="+")
    ap.add_argument("--out", default="var/cet4-daily/papers")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    out_dir = ROOT / args.out
    files = [SRC / s for s in args.set]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for msg in ex.map(lambda f: compose(f, out_dir), files):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
