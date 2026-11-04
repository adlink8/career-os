# -*- coding: utf-8 -*-
"""给 10 套整卷补 Passage Two：用 out/*.json 里现成的外刊改造稿（与 Passage One 不同源）。

每套插入：
  passage2 = {title, paragraphs(含解析), questions 51-55, source/url}
做法：选一篇未使用的 out 稿 → 转成段落结构 → CB 补段落级+句子级解析 → 写回 paper JSON。

用法: python cet4/bin/cet4_passage_two.py [--workers 3]
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
PDIR = ROOT / "var" / "cet4-daily" / "papers"
OUTDIR = ROOT / "var" / "cet4-daily" / "out"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

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


def candidates():
    out = []
    for f in sorted(OUTDIR.glob("*.json")):
        if ".q." in f.name or ".timing." in f.name or ".review" in f.name:
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        p = (d.get("passage") or "").strip()
        qs = d.get("questions") or []
        if len(p.split()) >= 300 and len(qs) == 5:
            out.append((f.name, d))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    papers = sorted(PDIR.glob("paper-*.json"))
    cands = candidates()
    print(f"整卷 {len(papers)} 套；可用第二篇素材 {len(cands)} 篇")
    used = set()
    # 先记录已被用作 passage2 的素材
    for f in papers:
        d = json.loads(f.read_text(encoding="utf-8"))
        src = (d.get("reading", {}).get("passage2") or {}).get("source_file")
        if src:
            used.add(src)

    def one(f: Path):
        d = json.loads(f.read_text(encoding="utf-8"))
        p2 = d["reading"].get("passage2") or {}
        if p2.get("paragraphs"):
            return f"{f.stem}: 已有 Passage Two，跳过"
        pick = next(((n, x) for n, x in cands if n not in used), None)
        if not pick:
            return f"{f.stem}: 没有剩余素材"
        name, src = pick
        used.add(name)
        paras = [{"en": x.strip()} for x in re.split(r"\n\s*\n", src["passage"]) if x.strip()]
        if len(paras) < 3:                       # 段落塌成一块的，按句子重新分
            sents = [s for s in re.split(r"(?<=[.!?])\s+", src["passage"]) if s.strip()]
            paras, buf = [], []
            for s in sents:
                buf.append(s)
                if len(buf) >= 3:
                    paras.append({"en": " ".join(buf)})
                    buf = []
            if buf:
                paras.append({"en": " ".join(buf)})
        body = "\n\n".join(f"[{i}]\n{p['en']}" for i, p in enumerate(paras, 1))
        data = jp(cb(ANALYZE.replace("{body}", body)))
        got = {int(x.get("no") or 0): x for x in data.get("paragraphs") or []}
        for i, p in enumerate(paras, 1):
            g = got.get(i) or {}
            p["cn"] = g.get("cn") or ""
            p["main"] = g.get("main") or ""
            p["structure"] = g.get("structure") or ""
            p["sentences"] = g.get("sentences") or []
        qs = []
        for k, q in enumerate(src["questions"], 51):
            qs.append({"no": k, "stem": q.get("stem") or q.get("stem_cn") or "",
                       "options": q.get("options") or [], "answer": str(q.get("answer") or "").upper()[:1],
                       "explain": q.get("explain") or q.get("why_correct") or ""})
        d["reading"]["passage2"] = {"title": src.get("title", ""), "title_cn": src.get("title_cn", ""),
                                    "topic": src.get("topic", ""), "paragraphs": paras, "questions": qs,
                                    "source": src.get("source", ""), "source_url": src.get("source_url", ""),
                                    "source_file": name}
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        return (f'{f.stem}: 用 {name} → {len(paras)} 段 / '
                f'{sum(len(p["sentences"]) for p in paras)} 句 / 5 题')

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for msg in ex.map(one, papers):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
