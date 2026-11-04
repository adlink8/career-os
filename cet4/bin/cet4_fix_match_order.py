# -*- coding: utf-8 -*-
"""修「信息匹配」两处命题硬伤（第 23 轮发现）。

1. **陈述顺序跟着段落走**：多数卷的答案序列是 ABCDEFGHIK 这种近乎顺序对应，
   真卷的答案序列是打乱的（如 DBHAFKCJEG）。→ 打乱陈述顺序（题号 36-45 保持连续），
   段落与文章顺序不动（真卷的文章本身是连贯的，打乱的是陈述）。
2. **陈述整句照抄原文**：>=8 词的连续片段与段落逐字相同。→ 只重写这些陈述，保持指向同一段落。

用法: python cet4/bin/cet4_fix_match_order.py --papers 81,82,... [--workers 3]
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
PAPERS = ROOT / "var" / "cet4-daily" / "papers"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """下面一条四级信息匹配陈述与它对应的段落。这条陈述与段落原文有 >=8 个词逐字相同，属于照抄，真题不会这样。
请**重写这条陈述**：
- 意思不变、指向的仍是同一段
- 与段落原文**不许有连续 6 个词相同**
- 10-20 词，一句话，不要加评论
- 不要出现段落字母

段落[{letter}]：
{para}

原陈述：
{stmt}

只输出 JSON：{{"text":"重写后的陈述"}}"""


def cb(prompt: str, timeout: int = 1200) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jp(t: str):
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", t or ""):
        try:
            obj, _ = dec.raw_decode(t[m.start():])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return {}


def words(t: str) -> list:
    return re.sub(r"[^a-z ]", " ", (t or "").lower()).split()


def copied(stmt: str, para: str, n: int = 8) -> bool:
    sw, pw = words(stmt), words(para)
    if len(sw) < n:
        return False
    grams = {" ".join(pw[i:i + n]) for i in range(len(pw) - n + 1)}
    return any(" ".join(sw[i:i + n]) in grams for i in range(len(sw) - n + 1))


def one(pid: str) -> str:
    f = PAPERS / f"paper-{pid}.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    m = d["reading"]["match"]
    paras = m.get("paragraphs") or {}
    sts = m.get("statements") or []
    ans = m.get("answers") or {}
    logs = []

    # 1) 重写照抄的陈述
    fixed = 0
    for st in sts:
        letter = ans.get(str(st["no"]))
        para = paras.get(letter, "")
        if para and copied(st["text"], para):
            res = jp(cb(PROMPT.replace("{letter}", letter).replace("{para}", para)
                            .replace("{stmt}", st["text"])))
            txt = (res.get("text") or "").strip()
            if txt and not copied(txt, para, 6):
                st["text"] = txt
                fixed += 1
    if fixed:
        logs.append(f"重写照抄陈述 {fixed} 条")

    # 2) 打乱陈述顺序（题号连续，答案随之变化）
    seq = "".join(ans.get(str(n), "?") for n in range(36, 46))
    if seq.startswith(("ABC", "BCD", "CDE")) or seq in ("ABCDEFGHIJ",):
        pairs = [(st["text"], ans.get(str(st["no"]))) for st in sts]
        rng = random.Random(int(pid) * 7 + 3)
        for _ in range(20):
            rng.shuffle(pairs)
            new_seq = "".join(p[1] for p in pairs)
            # 不许出现连续 3 个以上的顺序字母
            if not re.search(r"(ABC|BCD|CDE|DEF|EFG|FGH|GHI|HIJ|IJK)", new_seq):
                break
        m["statements"] = [{"no": 36 + i, "text": t} for i, (t, _) in enumerate(pairs)]
        m["answers"] = {str(36 + i): a for i, (_, a) in enumerate(pairs)}
        logs.append("陈述顺序已打乱")
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return f"paper-{pid}: " + ("；".join(logs) if logs else "无需修改")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", default="81,82,83,84,85,86,87,97,98,99")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    pids = [x for x in re.split(r"[,\s]+", args.papers) if x]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for msg in ex.map(one, pids):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
