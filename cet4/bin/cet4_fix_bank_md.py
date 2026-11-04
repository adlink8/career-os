# -*- coding: utf-8 -*-
"""真题 markdown 的 OCR/标点体检（只生成修正副本，不动原库）。

检出的问题类型（都只影响字符层，不改内容）：
- 英文行里混入全角标点（，。；：！？（）“”）
- 字母后粘连脚注数字（shrinks2 / cells12）
- 连字符后多空格（plant- based）
- 句读后缺空格（word.Next）
- 连续多空格

用法: python cet4/bin/cet4_fix_bank_md.py [--apply]
产物: var/cet4-daily/bank-fixed/<相对路径>（原件不动）；报告打印在控制台
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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
OUT = ROOT / "var" / "cet4-daily" / "bank-fixed"

FULLWIDTH = {"，": ",", "。": ".", "；": ";", "：": ":", "！": "!", "？": "?",
             "（": "(", "）": ")"}          # 引号/撇号保留原排版

CHECKS = [
    ("全角标点", re.compile(r"[\u4e00-\u9fff][，。；：！？（）“”]|[,.;:!?][\u3000-\u303f]")),
    ("粘连脚注数字", re.compile(r"\b[a-z]{3,}\d{1,2}\b")),
    ("连字符多空格", re.compile(r"[A-Za-z]- [A-Za-z]")),
    ("句读后缺空格", re.compile(r"[a-z][.,;:][A-Z][a-z]")),
    ("连续多空格", re.compile(r"\S  +\S")),
]


def english_only(line: str) -> bool:
    stripped = line.lstrip()
    if stripped.startswith(("|", ">", "```", "#", "-", "*")):
        return False
    letters = len(re.findall(r"[A-Za-z]", line))
    cjk = len(re.findall(r"[\u4e00-\u9fff]", line))
    return letters > 6 and cjk <= 2


def scan(text: str) -> dict:
    """只在英文行里扫，避免把中文题干算成问题。"""
    hits = {}
    for line in text.splitlines():
        if not english_only(line):
            continue
        for name, pat in CHECKS:
            for m in pat.finditer(line):
                hits.setdefault(name, []).append(m.group(0))
    return hits


def fix(text: str) -> str:
    lines = text.splitlines()
    out = []
    for line in lines:
        if english_only(line):
            for k, v in FULLWIDTH.items():
                line = line.replace(k, v)
            line = re.sub(r"([A-Za-z])- ([A-Za-z])", r"\1-\2", line)
            line = re.sub(r"([a-z][.,;:])([A-Z])", r"\1 \2", line)
            line = re.sub(r"(\S)  +(\S)", r"\1 \2", line)
            line = re.sub(r"\b([a-z]{4,})(\d{1,2})\b", r"\1", line)
        out.append(line)
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="把修正副本写到 var/cet4-daily/bank-fixed/")
    args = ap.parse_args()

    files = sorted(BANK.rglob("*.md"))
    report = []
    total = {name: 0 for name, _ in CHECKS}
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        hits = scan(text)
        if not hits:
            continue
        fixed = fix(text)
        changed = sum(1 for a, b in zip(text.splitlines(), fixed.splitlines()) if a != b)
        for name, arr in hits.items():
            total[name] += len(arr)
        report.append({"file": str(f.relative_to(BANK)), "changed_lines": changed,
                       "hits": {k: len(v) for k, v in hits.items()},
                       "sample": {k: v[:3] for k, v in hits.items()}})
        if args.apply:
            dst = OUT / f.relative_to(BANK)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(fixed, encoding="utf-8")

    print(f"扫描 {len(files)} 个文件，命中 {len(report)} 个")
    print("按类型汇总:", total)
    for r in report[:12]:
        print(f'  {r["file"]}: 改 {r["changed_lines"]} 行 | ' +
              " ".join(f"{k}×{v}" for k, v in r["hits"].items()) +
              " | 例:" + (next(iter(r["sample"].values()))[0][:40] if r["sample"] else ""))
    if args.apply:
        (OUT / "_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"修正副本写入 {OUT}（原件未改）")
    else:
        print("（只扫描。加 --apply 生成修正副本，原件不动）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
