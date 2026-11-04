# -*- coding: utf-8 -*-
"""把审查意见回灌给 repair：修 → 重审 → 双判据复测（不绕近路）。

阶段：
  --stage repair   逐套把 review findings 的 must_fix 回灌给独立 repair 会话，产出 set-XX.r2.json
  --stage review2  对修复稿重新独立审查（同一套 rubric），产出 set-XX.review2.json
  --stage verify   双判据复测：盲做（对答案键）+ 报错（带答案与解析），产出 .v2.solve/.v2.flag

用法: python cet4/bin/cet4_repair_sets.py --stage repair --workers 3
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
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

REPAIR = """你是这篇模拟阅读的出题人。稿子被独立审查打了回来，下面是审查意见。
请逐条修正，输出**完整的新稿 JSON**（结构同原稿，不要只给补丁，不要解释文字）。

硬要求：
- 正文仍是 348–375 词，5 题，每题 4 选项，答案唯一
- 修完的解析必须与正文一致，不许出现正文没有的事实
- 审查意见里指出的每一条都必须落实；做不到的，在 fix_log 里说明原因

原稿：
<<<PAPER>>>

审查意见：
<<<FINDINGS>>>

输出 JSON：
{"title":"...","passage":"...","cn":"...","questions":[{"no":46,"stem":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","why_correct":"...","opt_why":{"A":"...","B":"...","C":"...","D":"..."}}],"fix_log":["逐条说明改了什么"]}"""

REVIEW = """你是四级命题组的独立审查员，只审查、不改写。下面是一篇模拟阅读（正文+5题+解析）和 3 篇真题正文样本作为难度基线。

审查维度：
1. 难度：与所给真题样本相比，是否同一档（词汇抽象度、句法、信息密度），指出偏难/偏易
2. 语言：是否有中式英语、生硬搭配、语法错误
3. 题目：5 题是否都有唯一正确答案；干扰项是否真的错；题干是否可在文中定位
4. 答案：answer 键与解析是否自洽（正确项的 paraphrase 是否成立）

输出 JSON：
{"verdict":"pass|needs_revision","band":"1-5（与真题比）","findings":[{"id":"F1","severity":"blocker|high|medium|low","where":"...","problem":"...","must_fix":"..."}],"summary":"<=50字"}

规则：宁可判 needs_revision 也不要放过真实错误；findings 必须具体到位置。

<<<PAPER>>>"""

SOLVE = """你是四级考生，正在做阅读题。只给文章和题目，没有答案。
逐题选出唯一最佳答案，一句话理由（<=20 字）。只输出 JSON：
[{"no":46,"answer":"A","why":"..."}]

<<<ITEMS>>>"""

FLAG = """你是四级命题组的校审专家。下面是一篇阅读（正文 + 5 题 + 答案 + 解析）。
请找出真实缺陷：答案错误、选项无唯一解、解析与原文不符、题干无法定位、语言不通。
每条给 {"type":"答案错|选项无唯一解|解析捏造|题干无法定位|语言错误","where":"...","detail":"<=25字"}
只输出 JSON：{"defects":[...],"verdict":"ok|suspicious|broken"}
确定不了就不要报。

<<<ITEMS>>>"""


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


def base_sets() -> list:
    return [f for f in sorted(SRC.glob("set-*.json"))
            if not re.search(r"\.(review|solve|flag|v\d|r\d)", f.name)]


def draft(round_no: int) -> list:
    """round_no=2 时取原稿；>=3 时取上一轮修复稿。"""
    if round_no <= 2:
        return base_sets()
    return [f for f in sorted(SRC.glob(f"set-*.r{round_no - 1}.json"))]


def review_candidates(stem: str, round_no: int) -> list:
    if round_no <= 2:
        return [SRC / f"{stem}.review.json"]
    return [SRC / f"{stem}.review{round_no - 1}.json",
            SRC / f"{stem}.r{round_no - 1}.review{round_no - 1}.json",
            SRC / f"{stem}.r{round_no - 1}.review2.json"]


def review_path(stem: str, round_no: int):
    for c in review_candidates(stem, round_no):
        if c.exists():
            return c
    return None


def findings_text(rev: dict) -> str:
    out = []
    for x in rev.get("findings") or []:
        out.append(f'- [{x.get("severity")}] {x.get("where")}：{x.get("problem")} → 修法：{x.get("must_fix")}')
    return "\n".join(out) or "（审查员没给具体条目，按 summary 修：" + str(rev.get("summary")) + "）"


def real_baseline(n: int = 3) -> str:
    out = []
    for md in sorted(BANK.rglob("*.md")):
        t = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
            body = t[m.end():]
            body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
            cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
            p = re.sub(r"[_*#]", "", (body[:cut.start()] if cut else "")[:4000]).strip()
            if len(p.split()) >= 250:
                out.append(p)
            if len(out) >= n:
                return "\n\n---\n\n".join(f"[真题样本 {i+1}]\n{x}" for i, x in enumerate(out))
    return "\n\n---\n\n".join(f"[真题样本 {i+1}]\n{x}" for i, x in enumerate(out))


def stage_repair(workers: int, round_no: int):
    base = real_baseline(3)

    def one(f: Path):
        stem0 = f.stem.split(".r")[0] if ".r" in f.stem else f.stem
        rev_path = review_path(stem0, round_no)
        if rev_path is None:
            return f"{f.name}: 缺审查意见，跳过"
        out_path = SRC / f"{stem0}.r{round_no}.json"
        if out_path.exists():
            return f"{stem0}: 已有 r{round_no}，跳过"
        paper = json.loads(f.read_text(encoding="utf-8"))
        rev = json.loads(rev_path.read_text(encoding="utf-8"))
        body = json.dumps({k: paper.get(k) for k in ("title", "passage", "cn", "questions")}, ensure_ascii=False, indent=1)
        prompt = (REPAIR.replace("<<<PAPER>>>", body)
                        .replace("<<<FINDINGS>>>", findings_text(rev) + "\n\n难度基线（供对照）：\n" + base[:4000]))
        raw = cb(prompt)
        fixed = jparse(raw)
        if not fixed or not fixed.get("questions"):
            return f"{f.stem}: 修复失败（解析不出 JSON）"
        fixed["set"] = paper.get("set")
        fixed["topic"] = paper.get("topic")
        fixed["round"] = round_no
        out_path.write_text(json.dumps(fixed, ensure_ascii=False, indent=1), encoding="utf-8")
        return (f'{f.stem}: 修完 {len((fixed.get("passage") or "").split())} 词 / '
                f'{len(fixed.get("questions") or [])} 题 / fix_log {len(fixed.get("fix_log") or [])} 条')

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for msg in ex.map(one, draft(round_no)):
            print(" ", msg, flush=True)


def stage_review2(workers: int, round_no: int):
    base = real_baseline(3)

    def one(f: Path):
        paper = json.loads(f.read_text(encoding="utf-8"))
        stem0 = f.stem.split(".r")[0] if ".r" in f.stem else f.stem
        out_path = SRC / f"{stem0}.review{round_no}.json"
        if out_path.exists():
            return f"{f.stem}: 已有 review2，跳过"
        body = json.dumps({k: paper.get(k) for k in ("title", "passage", "questions")}, ensure_ascii=False, indent=1)
        res = jparse(cb(REVIEW.replace("<<<PAPER>>>", base + "\n\n=====\n\n[待审模拟阅读]\n" + body))) or {"verdict": "parse_failed"}
        res["set"] = paper.get("set")
        out_path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        return f'{f.stem}: verdict={res.get("verdict")} band={res.get("band")} findings={len(res.get("findings") or [])}'

    files = draft(round_no)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for msg in ex.map(one, files):
            print(" ", msg, flush=True)


def paper_text(d: dict, with_answers: bool) -> str:
    line = "正文：\n" + (d.get("passage") or "") + "\n\n题目：\n"
    for q in d.get("questions") or []:
        line += f'{q.get("no")}. {q.get("stem")}\n' + "\n".join(q.get("options") or []) + "\n"
        if with_answers:
            why = q.get("opt_why") or {}
            line += f'答案：{q.get("answer")}\n' + "".join(f'  {k}: {v}\n' for k, v in why.items())
    return line


def stage_verify(workers: int, round_no: int):
    files = draft(round_no)

    def one(f: Path):
        d = json.loads(f.read_text(encoding="utf-8"))
        stem = f.stem.split(".r")[0] if ".r" in f.stem else f.stem
        got = jparse_list(cb(SOLVE.replace("<<<ITEMS>>>", paper_text(d, False))))
        mine = {int(g.get("no")): str(g.get("answer") or "").strip().upper()[:1] for g in got if g.get("no")}
        rows = [{"no": int(q["no"]), "key": str(q.get("answer")).upper()[:1], "model": mine.get(int(q["no"]))}
                for q in d.get("questions") or []]
        wrong = [r["no"] for r in rows if r["model"] != r["key"]]
        (SRC / f"{stem}.v{round_no}.solve.json").write_text(json.dumps({"file": f.name, "rows": rows, "mismatch": wrong},
                                                            ensure_ascii=False, indent=1), encoding="utf-8")
        fl = jparse(cb(FLAG.replace("<<<ITEMS>>>", paper_text(d, True)))) or {}
        (SRC / f"{stem}.v{round_no}.flag.json").write_text(json.dumps({"file": f.name, **fl}, ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
        return f'{stem}: 盲做不符 {len(wrong)}｜报错 {len(fl.get("defects") or [])} 条 verdict={fl.get("verdict")}'

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for msg in ex.map(one, files):
            print(" ", msg, flush=True)


def jparse_list(txt: str):
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
    ap.add_argument("--stage", required=True, choices=["repair", "review2", "verify"])
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--round", type=int, default=2)
    args = ap.parse_args()
    if args.stage == "repair":
        stage_repair(args.workers, args.round)
    elif args.stage == "review2":
        stage_review2(args.workers, args.round)
    else:
        stage_verify(args.workers, args.round)
    return 0


if __name__ == "__main__":
    sys.exit(main())
