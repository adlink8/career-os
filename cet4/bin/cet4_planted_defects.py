# -*- coding: utf-8 -*-
"""植入已知缺陷的检出率实验（这是唯一能测「能不能发现错误」的办法）。

做法：
1. 取 10 套模拟阅读，其中 5 套各植入 2 个已知缺陷（共 10 个真值缺陷，5 种类型 × 2）
2. 两种判据分别盲测：
   - solve：只给正文+题干+选项（不给答案），与答案键比对 → 答案类缺陷应暴露
   - flag ：给正文+题目+答案键+解析，要求报缺陷 → 解析/语言类缺陷应暴露
3. 统计每种缺陷的召回率，以及干净 5 套上的误报率

用法: python cet4/bin/cet4_planted_defects.py [--inject] [--judge solve|flag] [--workers 4]
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
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "var" / "cet4-daily" / "ten-sets"
OUT = ROOT / "var" / "cet4-daily" / "defect-exp"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

SOLVE = """你是四级考生，正在做阅读题。只给文章和题目，没有答案。
逐题选出唯一最佳答案，一句话理由（<=20 字）。只输出 JSON：
[{"no":46,"answer":"A","why":"..."}]

<<<ITEMS>>>"""

FLAG = """你是四级命题组的校审专家。下面是一篇阅读（正文 + 5 题 + 答案 + 解析）。
请找出**任何真实存在的缺陷**：答案错误、选项无唯一解、解析与原文不符、题干无法定位、语言不通。
每条给 {"type":"答案错|选项无唯一解|解析捏造|题干无法定位|语言错误","where":"...","detail":"<=25字"}
只输出 JSON：{"defects":[...],"verdict":"ok|suspicious|broken"}
确定不了就不要报。

<<<ITEMS>>>"""


def cb(prompt: str, timeout: int = 1800) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jparse(txt: str, want="{"):
    t = re.sub(r"^```(?:json)?\s*", "", (txt or "").strip())
    t = re.sub(r"```$", "", t).strip()
    i, j = (t.find("{"), t.rfind("}")) if want == "{" else (t.find("["), t.rfind("]"))
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return None


# ---------------- 注入 ----------------
def inject_all() -> list:
    """5 套各注入 2 个缺陷，记录真值。"""
    OUT.mkdir(parents=True, exist_ok=True)
    srcs = [f for f in sorted(SRC.glob("set-*.json"))
            if ".review." not in f.name and ".solve." not in f.name]
    truth = []
    pick = srcs[:5]
    for idx, f in enumerate(pick, 1):
        d = json.loads(f.read_text(encoding="utf-8"))
        qs = d.get("questions") or []
        kinds = []

        # 缺陷 A：答案键改错（挑第 2 题，键换成另一个字母）
        if len(qs) >= 2:
            q = qs[1]
            old = str(q.get("answer") or "A").strip().upper()[:1]
            new = next(c for c in "ABCD" if c != old)
            q["answer"] = new
            kinds.append({"type": "答案键改错", "where": f'第{q["no"]}题', "from": old, "to": new})

        # 缺陷 B：解析捏造依据（第 4 题正确项解释里加一句原文没有的事实）
        if len(qs) >= 4:
            q = qs[3]
            why = q.get("opt_why") or {}
            letter = str(q.get("answer") or "A").strip().upper()[:1]
            why[letter] = (why.get(letter) or "") + " 原文还提到 2019 年挪威的试点把通勤成本降低了三成。"
            q["opt_why"] = why
            kinds.append({"type": "解析捏造", "where": f'第{q["no"]}题解析'})

        d["set"] = idx
        (OUT / f"d-{idx:02d}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        truth.append({"set": idx, "file": f"d-{idx:02d}.json", "defects": kinds})
    # 干净对照：另外 5 套原样复制
    for idx, f in enumerate(srcs[5:10], 1):
        d = json.loads(f.read_text(encoding="utf-8"))
        d["set"] = 10 + idx
        (OUT / f"c-{idx:02d}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        truth.append({"set": 10 + idx, "file": f"c-{idx:02d}.json", "defects": []})
    (OUT / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"注入完成：缺陷套 5（10 个缺陷）+ 干净套 5")
    for t in truth:
        if t["defects"]:
            print(f'  {t["file"]}: ' + "；".join(f'{x["type"]}@{x["where"]}' for x in t["defects"]))
    return truth


# ---------------- 判据 ----------------
def case_text(d: dict, with_answers: bool) -> str:
    line = "正文：\n" + (d.get("passage") or "") + "\n\n题目：\n"
    for q in d.get("questions") or []:
        line += f'{q.get("no")}. {q.get("stem")}\n' + "\n".join(q.get("options") or []) + "\n"
        if with_answers:
            line += f'答案：{q.get("answer")}\n'
            why = q.get("opt_why") or {}
            for k, v in why.items():
                line += f'  {k}: {v}\n'
    return line


def stage_solve(workers: int):
    files = [f for f in sorted(OUT.glob("[dc]-*.json")) if ".solve." not in f.name and ".flag." not in f.name]
    truth = {t["file"]: t for t in json.loads((OUT / "truth.json").read_text(encoding="utf-8"))}

    def one(f):
        d = json.loads(f.read_text(encoding="utf-8"))
        got = jparse(cb(SOLVE.replace("<<<ITEMS>>>", case_text(d, False))), "[") or []
        mine = {int(g.get("no")): str(g.get("answer") or "").strip().upper()[:1] for g in got if g.get("no")}
        rows = [{"no": int(q["no"]), "key": str(q.get("answer")).upper()[:1], "model": mine.get(int(q["no"]))}
                for q in d.get("questions") or []]
        det = [r["no"] for r in rows if r["model"] != r["key"]]
        res = {"file": f.name, "truth": truth.get(f.name, {}), "rows": rows, "mismatch": det}
        (OUT / f"{f.stem}.solve.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        return f'{f.name}: 与键不符 {len(det)} 题 {det}'

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for m in ex.map(one, files):
            print(" ", m, flush=True)


def stage_flag(workers: int):
    files = [f for f in sorted(OUT.glob("[dc]-*.json")) if ".solve." not in f.name and ".flag." not in f.name]

    def one(f):
        d = json.loads(f.read_text(encoding="utf-8"))
        res = jparse(cb(FLAG.replace("<<<ITEMS>>>", case_text(d, True)))) or {}
        (OUT / f"{f.stem}.flag.json").write_text(json.dumps({"file": f.name, **res}, ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
        return f'{f.name}: verdict={res.get("verdict")} defects={len(res.get("defects") or [])}'

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for m in ex.map(one, files):
            print(" ", m, flush=True)


def summarize():
    truth = json.loads((OUT / "truth.json").read_text(encoding="utf-8"))
    print("\n【盲做判据】")
    tot_def = hit_def = tot_clean = hit_clean = 0
    for t in truth:
        stem = Path(t["file"]).stem
        sf = OUT / f"{stem}.solve.json"
        if not sf.exists():
            continue
        r = json.loads(sf.read_text(encoding="utf-8"))
        if t["defects"]:
            tot_def += 1
            if r["mismatch"]:
                hit_def += 1
            print(f'  {t["file"]}: 不符 {len(r["mismatch"])} 题 {r["mismatch"]}'
                  + ("  ← 抓到缺陷" if r["mismatch"] else "  ← 漏检"))
        else:
            tot_clean += 1
            if not r["mismatch"]:
                hit_clean += 1
    print(f"  有缺陷套被判异常: {hit_def}/{tot_def}；干净套被判正常: {hit_clean}/{tot_clean}")

    print("\n【报错判据】")
    td = hd = tc = hc = 0
    for t in truth:
        stem = Path(t["file"]).stem
        ff = OUT / f"{stem}.flag.json"
        if not ff.exists():
            continue
        r = json.loads(ff.read_text(encoding="utf-8"))
        found = r.get("defects") or []
        if t["defects"]:
            td += 1
            ok = bool(found)
            hd += 1 if ok else 0
            print(f'  {t["file"]}: 报 {len(found)} 条' + ("  ← 抓到" if ok else "  ← 漏检"))
        else:
            tc += 1
            ok = not found
            hc += 1 if ok else 0
            print(f'  {t["file"]}: 报 {len(found)} 条' + ("  ← 正确(无缺陷)" if ok else "  ← 误报"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inject", action="store_true")
    ap.add_argument("--judge", default="", choices=["", "solve", "flag"])
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    if args.inject:
        inject_all()
    if args.judge == "solve":
        stage_solve(args.workers)
    if args.judge == "flag":
        stage_flag(args.workers)
    if not args.inject and not args.judge:
        summarize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
