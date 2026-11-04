# -*- coding: utf-8 -*-
"""10 套整卷流水线编排：组装 → 补解析 → 补词典 → 渲染 → 体检。

阶段：
  compose  8 套未组装的 Section C 稿 → paper-XX.json（补 A/B/翻译/写作）
  analyze  每套 Passage One 的段落级 + 句子级解析（段落中文/主旨/作用/逐句意群）
  dict     收集所有卷面的词，补全缺失释义
  render   渲染 explain/plain 并输出体检数字

用法: python cet4/bin/cet4_papers_build.py --stage compose|analyze|dict|render|all
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
PDIR = ROOT / "var" / "cet4-daily" / "papers"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

SETS = ["set-81.s2.json", "set-82.s2.json", "set-83.s2.json", "set-84.s2.json", "set-85.s2.json",
        "set-86.s2.json", "set-87.s2.json", "set-91.s2.json", "set-92.s2.json", "set-93.s2.json"]

COMPOSE = """你在组一份大学英语四级模拟卷，已经有一篇阅读正文（Section C Passage One）。请补齐其余部分。

已有：Section C Passage One 主题「{topic}」，标题「{title}」。

## 产出（严格四级格式）
1. **选词填空**（Section A，26-35）：188-316 词短文，10 空写成 `__26__`…`__35__`；15 个候选词 A-O（10 正确 5 干扰）；answers；每空 why（<=20 字）
2. **信息匹配**（Section B，36-45）：12 段 A-L（合计 950-1100 词，单段 60-120 词）+ 10 条陈述；answers（陈述号→段落字母）
3. **翻译**（Part IV）：**138-159 汉字**（不要超），中国文化/社会/教育题材；参考译文；3-5 踩分点
4. **写作**（Part I）：英文 directions（要求 120-180 词）+ 140-170 词范文 + 2-3 条扣分点

只输出 JSON：
{{"cloze":{{"title":"...","passage":"...","bank":{{"A":"..."}},"answers":{{"26":"D"}},"blanks":[{{"no":26,"answer":"D","word":"...","why":"..."}}]}},
 "match":{{"title":"...","paragraphs":{{"A":"..."}},"statements":[{{"no":36,"text":"..."}}],"answers":{{"36":"D"}}}},
 "translation":{{"zh":"...","reference":"...","points":["..."]}},
 "writing":{{"directions":"...","model_essay":"...","deductions":["..."]}}}}"""

ANALYZE = """给下面每段英文做两件事，用于四级阅读讲解：
1. 段落级：cn（逐句中文直译合并成一段）、main（主旨 <=20 字）、structure（作用：提出背景/给出证据/转折/解释机制/说明局限 之一）
2. 句子级：每句切成意群（每块 4-8 词），每块标成分（主 谓 宾 表 补 定 状 连）+ 该块中文；再给整句中文

只输出 JSON：
{"paragraphs":[{"no":1,"cn":"...","main":"...","structure":"...","sentences":[{"en":"原句","cn":"整句中文","chunks":[{"en":"意群","role":"主","cn":"中文"}]}]}]}

段落：
{body}"""


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


def paper_id(set_name: str) -> str:
    return set_name.split("-")[1].split(".")[0]


def stage_compose(workers: int):
    PDIR.mkdir(parents=True, exist_ok=True)

    def one(name):
        out = PDIR / f"paper-{paper_id(name)}.json"
        if out.exists():
            d = json.loads(out.read_text(encoding="utf-8"))
            if d.get("reading", {}).get("cloze"):
                return f"paper-{paper_id(name)}: 已组装，跳过"
        d = json.loads((SRC / name).read_text(encoding="utf-8"))
        res = jp(cb(COMPOSE.replace("{topic}", str(d.get("topic"))).replace("{title}", str(d.get("title")))))
        if not res.get("cloze") or not res.get("match"):
            return f"paper-{paper_id(name)}: 组装失败"
        zh = str((res.get("translation") or {}).get("zh") or "")
        paper = {
            "meta": {"name": f"四级模拟整卷（{d.get('topic')}）", "date": "2026-11-04", "total": 57},
            "writing": res.get("writing") or {},
            "listening": {"sections": [], "questions": []},
            "reading": {"cloze": res["cloze"], "match": res["match"],
                        "passage1": {"title": d.get("title"), "title_cn": "", "topic": d.get("topic"),
                                     "paragraphs": [{"en": p, "sentences": []} for p in re.split(r"\n\s*\n", d.get("passage") or "") if p.strip()],
                                     "questions": d.get("questions") or [],
                                     "source": d.get("source"), "source_url": d.get("source_url")},
                        "passage2": {"title": "", "paragraphs": [], "questions": []}},
            "translation": res.get("translation") or {},
        }
        out.write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding="utf-8")
        return (f"paper-{paper_id(name)}: 选词 {len(res['cloze'].get('answers') or {})} 空 / "
                f"匹配 {len(res['match'].get('paragraphs') or {})} 段 / 翻译 {len(zh)} 字")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for msg in ex.map(one, SETS):
            print(" ", msg, flush=True)


def stage_analyze(workers: int):
    def one(name):
        pid = paper_id(name)
        path = PDIR / f"paper-{pid}.json"
        if not path.exists():
            return f"paper-{pid}: 缺卷子"
        d = json.loads(path.read_text(encoding="utf-8"))
        paras = d["reading"]["passage1"].get("paragraphs") or []
        if paras and all(p.get("sentences") for p in paras):
            return f"paper-{pid}: 已有解析，跳过"
        body = "\n\n".join(f"[{i}]\n{p['en']}" for i, p in enumerate(paras, 1))
        data = jp(cb(ANALYZE.replace("{body}", body)))
        got = {int(p.get("no") or 0): p for p in data.get("paragraphs") or []}
        filled = 0
        for i, p in enumerate(paras, 1):
            g = got.get(i) or {}
            if g.get("sentences"):
                p.update({"cn": g.get("cn") or "", "main": g.get("main") or "",
                          "structure": g.get("structure") or "", "sentences": g["sentences"]})
                filled += 1
        path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        return f"paper-{pid}: 解析 {filled}/{len(paras)} 段，句 {sum(len(p.get('sentences') or []) for p in paras)}"

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for msg in ex.map(one, SETS):
            print(" ", msg, flush=True)


def stage_dict():
    """收集所有卷面词，把缺释义的写进 wordlist 并调用 cet4_words.py。"""
    words = set()
    for name in SETS:
        path = PDIR / f"paper-{paper_id(name)}.json"
        if not path.exists():
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        txt = json.dumps(d, ensure_ascii=False)
        words.update(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'-]{1,}", txt))
    vocab_path = ROOT / "var" / "cet4-daily" / "words.json"
    have = set()
    if vocab_path.exists():
        have = {x["word"].lower() for x in json.loads(vocab_path.read_text(encoding="utf-8")) if x.get("word")}
    todo = sorted(w for w in words if w not in have)
    print(f"卷面词 {len(words)}，词典已有 {len(have)}，待补 {len(todo)}")
    if not todo:
        return
    (ROOT / "var" / "cet4-daily" / "wordlist.json").write_text(
        json.dumps([{"word": w} for w in todo], ensure_ascii=False, indent=1), encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "bin" / "cet4_words.py"), "--workers", "3", "--batch", "40"],
                   cwd=str(ROOT))


def stage_render():
    for name in SETS:
        pid = paper_id(name)
        src = PDIR / f"paper-{pid}.json"
        if not src.exists():
            continue
        out = ROOT / "var" / "cet4-daily" / f"paper-{pid}"
        r = subprocess.run([sys.executable, str(ROOT / "bin" / "cet4_build_paper.py"),
                            str(src), "--mode", "explain", "--out", str(out)],
                           capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
        ok = "wrote" in (r.stdout or "")
        print(f"  paper-{pid}: {'渲染成功' if ok else '渲染失败'} {(r.stdout or r.stderr or '')[:80].strip()}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["compose", "analyze", "dict", "render", "all"])
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    if args.stage in ("compose", "all"):
        print("[compose]")
        stage_compose(args.workers)
    if args.stage in ("analyze", "all"):
        print("[analyze]")
        stage_analyze(args.workers)
    if args.stage in ("dict", "all"):
        print("[dict]")
        stage_dict()
    if args.stage in ("render", "all"):
        print("[render]")
        stage_render()
    return 0


if __name__ == "__main__":
    sys.exit(main())
