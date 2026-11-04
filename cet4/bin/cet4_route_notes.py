# -*- coding: utf-8 -*-
"""给逐句解析补「路标」note：盲读时该句为什么会被出题人盯上。

四类原生路标：转折（but/however/yet）、研究动词（found/revealed/concluded）、
因果结论（because/so/therefore）、比较极端（more than/only/first）。
缺 note 的句子（阅读正文/匹配段落/选词填空）统一补齐，保证四篇阅读解析长相一致。

用法: python cet4/bin/cet4_route_notes.py [--paper var/cet4-daily/demo-whole-paper.json] [--batch 20]
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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """你是四级阅读老师。给每句补一条「路标」提示：盲读时（没有答案视角）为什么这句话值得停下来。

只能从四类里选最贴的，用一句话说明（<=28 字中文）：
- 转折：but/however/yet/rather 之后的反转信息
- 研究动词：studies found / researchers report / revealed / concluded 后的实证发现
- 因果结论：because / so / therefore / the conclusion 后的定论
- 比较极端：more than / only / first / less than 后的限定
如果这句是普通背景句，写「背景铺垫，可快读」。

只输出 JSON 数组：[{"id":"s1","note":"..."}]

句子：
<<<ITEMS>>>"""


def parse(txt: str):
    t = re.sub(r"^```(?:json)?\s*", "", (txt or "").strip())
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("["), t.rfind("]")
    if i < 0 or j <= i:
        return []
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="var/cet4-daily/demo-whole-paper.json")
    ap.add_argument("--batch", type=int, default=20)
    args = ap.parse_args()

    path = ROOT / args.paper
    data = json.loads(path.read_text(encoding="utf-8"))
    sent_files = {}
    for kind in ("cloze", "match"):
        f = ROOT / "var" / "cet4-daily" / f"sent-explain-{kind}.json"
        if f.exists():
            sent_files[kind] = f

    targets = []      # (container_list, sentence)
    for key in ("passage1", "passage2"):
        for para in data["reading"][key].get("paragraphs") or []:
            for s in para.get("sentences") or []:
                if not (s.get("note") or "").strip():
                    targets.append(s)
    docs = {k: json.loads(v.read_text(encoding="utf-8")) for k, v in sent_files.items()}
    for k, doc in docs.items():
        if k == "cloze":
            for s in doc.get("cloze") or []:
                if not (s.get("note") or "").strip():
                    targets.append(s)
        elif k == "match":
            for _, arr in doc.items():
                for s in arr or []:
                    if not (s.get("note") or "").strip():
                        targets.append(s)
    print(f"缺 note 的句子: {len(targets)}")
    if not targets:
        return 0

    filled = 0
    for start in range(0, len(targets), args.batch):
        chunk = targets[start:start + args.batch]
        body = json.dumps([{"id": f"s{i}", "en": s.get("en")} for i, s in enumerate(chunk)],
                          ensure_ascii=False, indent=1)
        proc = subprocess.run([str(CB), "-p", "--output-format", "text"], input=PROMPT.replace("<<<ITEMS>>>", body),
                              capture_output=True, text=True, encoding="utf-8", timeout=1200, cwd=str(ROOT))
        got = {g.get("id"): (g.get("note") or "").strip() for g in parse(proc.stdout or "")}
        for i, s in enumerate(chunk):
            n = got.get(f"s{i}")
            if n:
                s["note"] = n
                filled += 1
        print(f"  {min(start + len(chunk), len(targets))}/{len(targets)}", flush=True)

    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, f in sent_files.items():
        f.write_text(json.dumps(docs[k], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"filled={filled} 剩余={len(targets) - filled}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
