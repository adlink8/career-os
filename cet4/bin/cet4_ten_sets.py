# -*- coding: utf-8 -*-
"""10 套模拟阅读（Section C 双篇）× 写手→独立审查→盲审 的实验脚本。

阶段：
  --stage write   10 位写手各产 1 套（正文 348-375 词 + 5 题 + 逐项解析 + 中文）
  --stage review  独立审查员逐套比对真题基线，给 verdict + findings
  --stage audit   盲审：10 套模拟 + 10 篇真题匿名混排，独立评审只凭文本找错、打难度
用法: python cet4/bin/cet4_ten_sets.py --stage write
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
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
OUT = ROOT / "var" / "cet4-daily" / "ten-sets"

TOPICS = [
    ("教育公平", "农村与城市学生在数字资源上的差距，以及一项由大学牵头的辅导计划"),
    ("职场技能", "雇主对软技能的需求上升，同时实习机会反而减少"),
    ("城市通勤", "某城市用公交专用道与共享单车缓解早晚高峰"),
    ("睡眠与学习", "研究者在大学生中测试推迟上课时间对成绩的影响"),
    ("食品浪费", "超市把临期食品打折上架，减少丢弃"),
    ("老年照护", "社区用志愿者网络为独居老人提供日常探访"),
    ("语言学习", "成年人学外语时听力先于语法的现象"),
    ("可再生能源", "小镇用屋顶光伏和储能平衡用电高峰"),
    ("社交媒体", "青少年使用时长与注意力问题的相关性研究"),
    ("公共图书馆", "图书馆把借阅范围扩展到工具与乐器"),
]

WRITER = """你是四级阅读命题老师。写一篇四级 Section C 阅读文章 + 5 道选择题，输出 JSON。

题材：{topic}
要求（对齐 2025-2026 真题）：
- 正文 348-375 词，5-6 段，每段 2-4 句；四级真题常见难度（不要写科研论文式抽象名词堆叠，不要英式评论文体）
- 句子平均 17-21 词，允许 1-2 句长句，但必须顺流可读
- 5 题覆盖：细节 2、推断 1、词义/句意 1、主旨 1
- 每题 4 选项，干扰项必须用真实陷阱（无中生有/偷换概念/因果倒置/范围扩大），正确项必须同义替换
- 每个干扰项写 why（<=20 字），正确项写 paraphrase（原文→选项的换皮）

只输出 JSON：
{{"title":"英文标题","passage":"正文（段落用 \\n\\n 分隔）","cn":"全文中文直译（逐段，段落用 \\n\\n 分隔）",
 "questions":[{{"no":46,"stem":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A",
 "why_correct":"...","opt_why":{{"A":"...","B":"...","C":"...","D":"..."}}}}],
 "words":整数}}"""

REVIEWER = """你是四级命题组的独立审查员，只审查、不改写。下面给你一篇模拟阅读（正文+5题+解析）和 3 篇真题正文样本作为难度基线。

审查维度：
1. 难度：与所给真题样本相比，是否同一档（词汇抽象度、句法、信息密度），指出偏难/偏易
2. 语言：是否有中式英语、生硬搭配、语法错误
3. 题目：5 题是否都有唯一正确答案；干扰项是否真的错；题干是否可在文中定位
4. 答案：answer 键与解析是否自洽（正确答案项的 paraphrase 是否成立）

输出 JSON：
{"verdict":"pass|needs_revision","band":"1-5（与真题比）","findings":[{"id":"F1","severity":"blocker|high|medium|low","where":"正文/第3题/C选项","problem":"...","must_fix":"..."}],"summary":"<=50字"}

规则：宁可判 needs_revision 也不要放过真实错误；findings 必须具体到位置。

{payload}"""

AUDITOR = """你是四级阅卷组的盲审专家。下面每段是一篇四级阅读文章正文，独立编号，来源未知（部分是历年真题，部分是模拟题）。
请只凭文本与题目判断，找出**任何真实存在的问题**，并按难度打分。

对每篇输出：
- id
- band：1-5（1 明显低于四级真题，3 与真题相当，5 明显高于）
- defects：数组，列出你确信的缺陷；没有就给 []。每条 {"type":"答案错/选项无唯一解/语言错误/逻辑断裂/难度偏离","where":"...","detail":"<=30字"}
- verdict：ok | suspicious | broken

只输出 JSON 数组，不要解释文字：
[{"id":"S1","band":3,"defects":[],"verdict":"ok"}]

待审材料：
<<<ITEMS>>>"""


def cb(prompt: str, timeout: int = 1800) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jparse(txt: str, want: str = "{"):
    t = re.sub(r"^```(?:json)?\s*", "", (txt or "").strip())
    t = re.sub(r"```$", "", t).strip()
    if want == "{":
        i, j = t.find("{"), t.rfind("}")
    else:
        i, j = t.find("["), t.rfind("]")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        return None


def real_passages(n: int, seed: int = 5) -> list:
    out = []
    for md in sorted(BANK.rglob("*.md")):
        t = md.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"####\s*Passage (One|Two)\s*\n", t):
            body = t[m.end():]
            body = re.sub(r"^\s*\n?\*\*Questions[^\n]*\n", "\n", body, count=1)
            cut = re.search(r"^\s*\d{2}\.\s", body, flags=re.M)
            p = re.sub(r"[_*#]", "", (body[:cut.start()] if cut else body[:4000]).strip())
            if len(p.split()) >= 250:
                out.append(p)
    return random.Random(seed).sample(out, min(n, len(out)))


def stage_write(workers: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    def one(idx_topic):
        idx, (name, desc) = idx_topic
        path = OUT / f"set-{idx:02d}.json"
        if path.exists():
            return f"set-{idx:02d} 已存在，跳过"
        raw = cb(WRITER.format(topic=f"{name}：{desc}"))
        data = jparse(raw)
        if not data:
            return f"set-{idx:02d} 解析失败"
        data["topic"] = name
        data["set"] = idx
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return f"set-{idx:02d} {name} {len((data.get('passage') or '').split())}词 {len(data.get('questions') or [])}题"

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for msg in ex.map(one, list(enumerate(TOPICS, 1))):
            print(" ", msg, flush=True)


def stage_review(workers: int) -> None:
    base = real_passages(3)
    baseline = "\n\n---\n\n".join(f"[真题样本 {i+1}]\n{t}" for i, t in enumerate(base))

    def one(path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        payload = baseline + "\n\n=====\n\n[待审模拟阅读]\n" + json.dumps(
            {k: data.get(k) for k in ("title", "passage", "questions")}, ensure_ascii=False, indent=1)
        raw = cb(REVIEWER.replace("{payload}", payload))
        res = jparse(raw) or {"verdict": "parse_failed"}
        res["set"] = data.get("set")
        (OUT / f"set-{data.get('set'):02d}.review.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        return f"set-{data.get('set'):02d} verdict={res.get('verdict')} band={res.get('band')} findings={len(res.get('findings') or [])}"

    files = sorted(OUT.glob("set-*.json"))
    files = [f for f in files if ".review." not in f.name and ".audit." not in f.name]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for msg in ex.map(one, files):
            print(" ", msg, flush=True)


def stage_audit(workers: int, n_real: int = 10) -> None:
    mock = []
    for f in sorted(OUT.glob("set-*.json")):
        if ".review." in f.name or ".audit." in f.name:
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        qs = d.get("questions") or []
        qtxt = "\n".join(
            f'{q.get("no")}. {q.get("stem")}\n' + "\n".join(q.get("options") or []) for q in qs)
        mock.append({"id": f'M{d.get("set"):02d}', "text": (d.get("passage") or "") + "\n\n" + qtxt, "group": "mock"})
    reals = real_passages(n_real, seed=13)
    items = [{"id": f"R{i:02d}", "text": t, "group": "real"} for i, t in enumerate(reals, 1)] + mock
    random.Random(99).shuffle(items)
    print(f"盲审材料: 真题 {len(reals)} 篇 + 模拟 {len(mock)} 套")

    def one(chunk):
        body = "\n\n=====\n\n".join(f'[{it["id"]}]\n{it["text"]}' for it in chunk)
        raw = cb(AUDITOR.replace("<<<ITEMS>>>", body), timeout=2400)
        got = jparse(raw, "[") or []
        print(f"  batch {chunk[0]['id']}..{chunk[-1]['id']}: {len(got)}/{len(chunk)}", flush=True)
        return {str(r.get("id")): r for r in got if r.get("id")}

    chunks = [items[i:i + 5] for i in range(0, len(items), 5)]
    res = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for got in ex.map(one, chunks):
            res.update(got)

    rows = []
    for it in items:
        r = res.get(it["id"]) or {}
        rows.append({"id": it["id"], "group": it["group"], "band": r.get("band"),
                     "verdict": r.get("verdict"), "defects": r.get("defects") or []})
    (OUT / "audit-result.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    def stat(g):
        gs = [r for r in rows if r["group"] == g]
        bands = [r["band"] for r in gs if isinstance(r["band"], (int, float))]
        flagged = [r for r in gs if (r["defects"] or r["verdict"] in ("suspicious", "broken"))]
        return (len(gs), (sum(bands) / len(bands) if bands else None),
                len(flagged), round(100 * len(flagged) / max(1, len(gs))))
    for g, name in (("real", "真题"), ("mock", "模拟")):
        n, mean, flagged, pct = stat(g)
        print(f"{name}: n={n} band均值={mean if mean is None else round(mean,2)} 被标记问题={flagged} ({pct}%)")
    for r in rows:
        if r["group"] == "mock":
            print(f'  {r["id"]} band={r["band"]} verdict={r["verdict"]} defects={len(r["defects"])}')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["write", "review", "audit"])
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--real", type=int, default=10)
    args = ap.parse_args()
    if args.stage == "write":
        stage_write(args.workers)
    elif args.stage == "review":
        stage_review(args.workers)
    else:
        stage_audit(args.workers, args.real)
    return 0


if __name__ == "__main__":
    sys.exit(main())
