# -*- coding: utf-8 -*-
"""补齐逐句解析里缺失的成分标签（role）。

Passage Two 的 82 个意群全部没有 role，导致渲染成灰色括号注而不是彩色主谓宾块。
本脚本把这些片段交给 CB 补 主/谓/宾/表/补/定/状/连，写回 paper JSON。

用法: python cet4/bin/cet4_fix_roles.py [--paper var/cet4-daily/demo-whole-paper.json]
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

PROMPT = """你是四级英语老师。下面每个句子被切成了若干意群，但意群缺成分标签。
请给每个意群补一个标签，只能取：主 谓 宾 表 补 定 状 连
判断规则（按顺流镜头）：
- 主语/谓语/宾语是句子主干；系动词后是表语
- 修饰名词的是定语，修饰动词/整句的是状语，补足主语或宾语的是补语
- 纯连接词、介词短语开头承接上文的可标 连
只输出 JSON 数组，结构照抄输入（id 不变）：
[{"id":"s1","roles":["主","定","谓"]}]

句子清单：
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
    ap.add_argument("--batch", type=int, default=14)
    args = ap.parse_args()

    path = ROOT / args.paper
    data = json.loads(path.read_text(encoding="utf-8"))

    jobs = []   # (target_list, sentence)
    for key in ("passage1", "passage2"):
        for para in data["reading"][key].get("paragraphs") or []:
            for s in para.get("sentences") or []:
                if any(not (c.get("role") or "").strip() for c in (s.get("chunks") or [])):
                    jobs.append(s)
    print(f"待补 role 的句子: {len(jobs)}")
    if not jobs:
        return 0

    filled = 0
    for start in range(0, len(jobs), args.batch):
        chunk = jobs[start:start + args.batch]
        items = []
        for i, s in enumerate(chunk):
            items.append({"id": f"s{i}", "en": s.get("en"),
                          "chunks": [c.get("en") for c in (s.get("chunks") or [])],
                          "cn": s.get("cn")})
        body = json.dumps(items, ensure_ascii=False, indent=1)
        proc = subprocess.run([str(CB), "-p", "--output-format", "text"], input=PROMPT.replace("<<<ITEMS>>>", body),
                              capture_output=True, text=True, encoding="utf-8", timeout=1200, cwd=str(ROOT))
        got = {g.get("id"): g.get("roles") or [] for g in parse(proc.stdout or "")}
        for i, s in enumerate(chunk):
            roles = got.get(f"s{i}") or []
            chunks = s.get("chunks") or []
            if len(roles) != len(chunks):
                print(f"  ! 句子长度不匹配: {len(roles)} vs {len(chunks)} | {s.get('en','')[:60]}")
                continue
            for c, r in zip(chunks, roles):
                if not (c.get("role") or "").strip():
                    c["role"] = (r or "").strip()
                    filled += 1
        print(f"  {start+len(chunk)}/{len(jobs)} 句处理完", flush=True)

    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    left = sum(1 for key in ("passage1", "passage2")
               for para in data["reading"][key].get("paragraphs") or []
               for s in para.get("sentences") or []
               for c in (s.get("chunks") or []) if not (c.get("role") or "").strip())
    print(f"filled={filled} 剩余无 role 的意群={left}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
