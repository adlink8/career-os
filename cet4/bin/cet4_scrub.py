# -*- coding: utf-8 -*-
"""编辑修正（scrub）：只修评委点名的四类缺陷，不重写文章。

四类缺陷（上一轮对抗式判别里评委反复给出的）：
1. 证据链悬空：只有 "studies suggest"，缺机构/研究者/样本量
2. 拼接接缝：同位语黏连、缺逗号/破折号（改写残留）
3. 原地打转：同一个发现在两段里各宣布一次
4. 结尾落点：以评价/设问收尾，而不是具体事实

做法：一次编辑 call，明确"只改这四处，其他句子原样保留"，产出 set-XX.s1.json。

用法: python cet4/bin/cet4_scrub.py --glob "set-8[1-7].json" [--workers 3]
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

PROMPT = """你是四级命题组的文字编辑。下面这篇模拟阅读正文有四个具体问题，请**只修这四处**，其余句子逐字保留。

## 要修的四类问题
1. **证据链悬空**：如果出现 "studies suggest / research shows / experts say" 这类没有主语的表述，补成具体主体（机构名 + 研究者姓名或职称 + 样本量或统计量），信息取自文中已有的内容；文中没有的，就删掉这个悬空句，不要编造新数据
2. **拼接接缝**：凡是两个名词短语硬粘在一起、或从句前缺逗号/破折号的地方，补标点或拆成两句
3. **原地打转**：同一个发现如果在两处各宣布一次，删掉第二次的宣布，只保留后面的具体细节
4. **结尾落点**：最后一句如果是评价、设问或劝诫，改成一句具体事实（可以是研究局限、样本范围、后续安排），不要新增论点

## 硬约束
- 全文必须仍在 348-375 词；改动后超了就删修饰语，不许删事实
- 段落数与段落顺序不变
- 不许新增原文没有的机构、数字、结论
- 不许在结尾加"这提醒我们"这类句子

## 输入正文
{passage}

## 输出
只输出 JSON：{"passage":"改好的正文（段落用 \\n\\n 分隔）","edits":[{"where":"第2段第3句","issue":"拼接接缝","fix":"补了逗号并拆句"}]}"""


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
    ap.add_argument("--glob", default="set-8[1-7].json")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--tag", default="s1")
    args = ap.parse_args()

    files = []
    for pat in args.glob.split("|"):
        files.extend(sorted(SRC.glob(pat)))
    files = [f for f in files if re.fullmatch(r"set-\d{2}\.json", f.name)]

    def one(f: Path):
        out = SRC / f"{f.stem}.{args.tag}.json"
        if out.exists():
            return f"{f.stem}: 已有 {args.tag}，跳过"
        d = json.loads(f.read_text(encoding="utf-8"))
        res = jparse(cb(PROMPT.replace("{passage}", d.get("passage") or "")))
        if not res or not res.get("passage"):
            return f"{f.stem}: 修正失败"
        d2 = dict(d)
        d2["passage"] = res["passage"]
        d2["edits"] = res.get("edits") or []
        d2["writer"] = (d.get("writer") or "") + "+scrub"
        out.write_text(json.dumps(d2, ensure_ascii=False, indent=1), encoding="utf-8")
        n = len(res["passage"].split())
        return f"{f.stem}: {n} 词，改了 {len(d2['edits'])} 处"

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for msg in ex.map(one, files):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
