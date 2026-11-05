# -*- coding: utf-8 -*-
"""一次性全量校正：把已知的、可对基准检查的问题全部修掉，然后统一验证。

修的内容（每套卷逐项检查，不合规就重做，两次不成就保留并记账）：
  A 选词填空：188-316 词｜词库 15 且词性 4/4/4/3｜无同根词｜答案字母三区间各 2-5｜无答案泄漏
  B 信息匹配：段落 12-15｜段落总词 950-1100｜陈述轻改写（照真题）｜顺序打乱
  C 阅读题干：锚定具体主体｜每篇最多 1 道主旨题｜答案不变
  D 翻译：138-159 汉字｜英文括注 ≤1
  E 写作：directions 45-60 词

验证：渲染 → 词典 → 10 套盲做（550 题）→ 单份盲判（学生口径）

用法: python cet4/bin/cet4_full_fix.py [--papers all] [--workers 3]
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

CLOZE = """出一段四级选词填空（Section A，26-35）。

硬要求：
- 短文 **188-316 词**，10 个空写成 `__26__` … `__35__`（每空一个词）
- 词库 15 词（A-O），**词性配比：名词 4 / 动词 4 / 形容词 4 / 副词 3**
- 词库内**不许有同根词**（不能同时出现 adapt/adaptive、most/mostly、reliable/reliably）
- **答案字母要散开**：A-E、F-J、K-O 三个区间各 2-5 个答案
- **答案词不许在短文别处出现**（含变形），否则该空等于送分
- 每个空只有唯一解；5 个干扰项词性对得上但语义填不进
- 主题：{topic}

只输出 JSON：{{"title":"...","passage":"...","bank":{{"A":"word"}},"answers":{{"26":"D"}},"blanks":[{{"no":26,"answer":"D","word":"...","why":"<=20字"}}]}}"""

MATCH = """出一段四级信息匹配（Section B，36-45）。

硬要求：
- 段落 **12-15 段**（A 起编），段落正文合计 **950-1100 词**，单段 60-120 词
- 10 条陈述（36-45）：**从对应段落里取一句关键句轻微改写**（保留大部分原词，不做深度改写；真题如此）
- 每条只对应一个段落；**10 条陈述的顺序必须打乱**（不许 36→A、37→B 这样顺着走）
- 主题：{topic}

只输出 JSON：{{"title":"...","paragraphs":{{"A":"..."}},"statements":[{{"no":36,"text":"..."}}],"answers":{{"36":"D"}}}}"""

STEMS = """下面是四级阅读正文与题干。请改写题干（选项与答案不许动）。

要求：
- 题干必须**锚定正文里的具体主体**（人名/机构/现象名/研究结论），不许 "the passage / the topic" 这种泛化问法
- **每篇最多 1 道主旨题**；剩余按细节/推断/词义分配
- 题干 8-18 词，问法各不相同；改完原答案仍是正确项

正文：
{passage}

现有题干：
{stems}

只输出 JSON：{{"stems":[{{"no":46,"stem":"..."}}]}}"""

WRITE = """出一道四级写作题（Part I）。

硬要求：
- directions **45-60 词**：一句场景（Suppose your university is seeking students' opinions on whether …）+ 一句任务（You are now to write an essay to express your view.）+ 「You should write at least 120 words but no more than 180 words.」
- 只许一个场景、一条任务，不许叠加其他指令
- 配 140-170 词范文 + 2-3 条扣分点
- 场景提示：{hint}

只输出 JSON：{{"directions":"...","model_essay":"...","deductions":["..."]}}"""

TV = """出一道四级翻译题（Part IV）。

硬要求：
- 中文 **138-159 汉字**；单一文化/社会/教育主题：{domain}
- 首句定义式「X 是……的……」；专有名词后**最多 1 处**英文括注；结尾一句现代回响
- 给参考译文（3-6 句、长短错落）与 4 个踩分点

只输出 JSON：{{"zh":"...","reference":"...","points":["..."]}}"""


def cb(prompt: str, timeout: int = 2400) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jp(t: str):
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", t or ""):
        try:
            o, _ = dec.raw_decode(t[m.start():])
            if isinstance(o, dict):
                return o
        except json.JSONDecodeError:
            continue
    return {}


# ---------- 检查器 ----------
POS_HINT = {"n": (), "v": (), "adj": (), "adv": ("ly",)}


def cloze_issues(c: dict) -> list:
    issues = []
    txt = c.get("passage") or ""
    bank = c.get("bank") or {}
    ans = c.get("answers") or {}
    w = len(txt.split())
    if not (185 <= w <= 320):
        issues.append(f"词数{w}")
    if len(bank) != 15:
        issues.append(f"词库{len(bank)}词")
    vals = [v.lower() for v in bank.values() if v]
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            a, b = vals[i], vals[j]
            if len(a) >= 4 and len(b) >= 4 and (b.startswith(a[:5]) or a.startswith(b[:5])):
                issues.append(f"同根{a}/{b}")
    letters = [ans.get(str(n), "") for n in range(26, 36)]
    bands = [sum(1 for x in letters if x in "ABCDE"), sum(1 for x in letters if x in "FGHIJ"),
             sum(1 for x in letters if x in "KLMNO")]
    if any(b < 2 for b in bands):
        issues.append(f"字母分布{bands}")
    holes = re.sub(r"_{2,}\s*\d{2}\s*_{2,}", " ", txt)
    for n, a in ans.items():
        v = (bank.get(a) or "").lower()
        if v and re.search(rf"\b{re.escape(v)}\w*\b", holes, re.I):
            issues.append(f"泄漏{n}:{v}")
    return issues


def match_issues(m: dict) -> list:
    issues = []
    paras = m.get("paragraphs") or {}
    sts = m.get("statements") or []
    if not (12 <= len(paras) <= 15):
        issues.append(f"段落{len(paras)}")
    tw = sum(len(v.split()) for v in paras.values())
    if not (930 <= tw <= 1110):
        issues.append(f"段落总词{tw}")
    if len(sts) != 10:
        issues.append(f"陈述{len(sts)}")
    seq = "".join((m.get("answers") or {}).get(str(n), "?") for n in range(36, 46))
    if re.search(r"(ABC|BCD|CDE|DEF|EFG|FGH|GHI|HIJ|IJK)", seq):
        issues.append(f"顺序{seq}")
    return issues


def main_idea_count(qs: list) -> int:
    return sum(1 for q in qs if re.search(r"(?i)mainly|main (idea|point)|primarily|concerned with", q.get("stem") or ""))


def cjk(t: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", t or ""))


def glosses(t: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]{2,8}\([A-Za-z][^)]{1,28}\)", t or ""))


DOMAINS = {"81": "二十四节气", "82": "四合院", "83": "中式婚礼", "84": "景德镇瓷器", "85": "书院",
           "86": "中医针灸", "87": "京剧脸谱", "97": "中国书法", "98": "苏州园林", "99": "中国茶文化"}
HINTS = {"81": "the library stays open all night in exam weeks", "82": "sports facilities open to the public",
         "83": "students must take one art course", "84": "more part-time jobs on campus",
         "85": "course papers replace final exams", "86": "students live off campus after year two",
         "87": "the canteen stops using disposable tableware", "97": "one term of community service",
         "98": "a 24-hour study room in each dormitory", "99": "students choose their own roommates"}


def fix_one(pid: str) -> str:
    f = PAPERS / f"paper-{pid}.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    topic = ((d["reading"].get("passage1") or {}).get("title") or "科普")[:60]
    logs = []

    # A 选词填空
    c = d["reading"]["cloze"]
    for _ in range(2):
        iss = cloze_issues(c)
        if not iss:
            break
        res = jp(cb(CLOZE.replace("{topic}", topic)))
        if res.get("passage") and res.get("bank") and res.get("answers"):
            c = {"title": res.get("title") or c.get("title"), "passage": res["passage"],
                 "bank": res["bank"], "answers": res["answers"], "blanks": res.get("blanks") or []}
    d["reading"]["cloze"] = c
    iss = cloze_issues(c)
    logs.append("选词OK" if not iss else f"选词残留({','.join(iss[:3])})")

    # B 信息匹配
    m = d["reading"]["match"]
    for _ in range(2):
        iss = match_issues(m)
        if not iss:
            break
        res = jp(cb(MATCH.replace("{topic}", topic)))
        if res.get("paragraphs") and res.get("statements") and res.get("answers"):
            m = {"title": res.get("title") or m.get("title"), "paragraphs": res["paragraphs"],
                 "statements": [{"no": int(x["no"]), "text": x["text"]} for x in res["statements"]],
                 "answers": {str(k): str(v).upper()[:1] for k, v in res["answers"].items()}}
    d["reading"]["match"] = m
    iss = match_issues(m)
    logs.append("匹配OK" if not iss else f"匹配残留({','.join(iss[:3])})")

    # C 阅读题干
    changed = 0
    for name in ("passage1", "passage2"):
        pp = d["reading"].get(name) or {}
        qs = pp.get("questions") or []
        if not qs:
            continue
        if main_idea_count(qs) <= 1 and all(len((q.get("stem") or "").split()) >= 6 for q in qs):
            continue
        body = "\n\n".join(x.get("en", "") for x in pp.get("paragraphs") or [])
        res = jp(cb(STEMS.replace("{passage}", body)
                        .replace("{stems}", "\n".join(f'{q["no"]}. {q["stem"]}' for q in qs))))
        got = {int(x["no"]): x["stem"].strip() for x in res.get("stems") or [] if x.get("no")}
        for q in qs:
            if int(q["no"]) in got and got[int(q["no"])]:
                q["stem"] = got[int(q["no"])]
                changed += 1
    logs.append(f"题干改{changed}")

    # D 翻译
    tr = d.get("translation") or {}
    zh = str(tr.get("zh") or "")
    if not (136 <= cjk(zh) <= 162) or glosses(zh) > 1:
        res = jp(cb(TV.replace("{domain}", DOMAINS.get(pid, "传统文化"))))
        if res.get("zh"):
            tr = {"zh": res["zh"], "reference": res.get("reference") or tr.get("reference"),
                  "points": res.get("points") or tr.get("points")}
            d["translation"] = tr
    logs.append(f"翻译{cjk(str(tr.get('zh') or ''))}字/括注{glosses(str(tr.get('zh') or ''))}")

    # E 写作
    w = d.get("writing") or {}
    if not (42 <= len(str(w.get("directions") or "").split()) <= 62):
        res = jp(cb(WRITE.replace("{hint}", HINTS.get(pid, "campus facilities"))))
        if res.get("directions"):
            w = {"directions": res["directions"], "model_essay": res.get("model_essay") or w.get("model_essay"),
                 "deductions": res.get("deductions") or w.get("deductions")}
            d["writing"] = w
    logs.append(f"写作{len(str(w.get('directions') or '').split())}词")

    f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return f"paper-{pid}: " + "；".join(logs)


def run(cmd: list, name: str) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT / "cet4"))
    out = (r.stdout or "").strip().splitlines()
    print(f"[{name}] " + (out[-1] if out else (r.stderr or "")[-120:]), flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", default="all")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    pids = ["81", "82", "83", "84", "85", "86", "87", "97", "98", "99"] if args.papers == "all" \
        else [x for x in re.split(r"[,\s]+", args.papers) if x]

    print("=== 1/5 逐套校正 ===", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for msg in ex.map(fix_one, pids):
            print(" ", msg, flush=True)

    print("=== 2/5 渲染 ===", flush=True)
    run([sys.executable, "bin/cet4_papers_build.py", "--stage", "dict"], "dict")
    run([sys.executable, "bin/cet4_papers_build.py", "--stage", "render"], "render")

    print("=== 3/5 盲做复核 ===", flush=True)
    run([sys.executable, "bin/cet4_paper_solve.py", "--papers", ",".join(pids), "--workers", "3"], "solve")

    print("=== 4/5 单份盲判（学生口径）===", flush=True)
    run([sys.executable, "bin/cet4_student_test.py", "--papers", ",".join(pids), "--reals", "10", "--judges", "2"], "student")

    print("=== 5/5 汇总 ===", flush=True)
    rep = ROOT / "var" / "cet4-daily" / "line-compare"
    for name in ("paper-solve.json", "student-test.json"):
        f = rep / name
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        if name == "student-test.json":
            print(f"  学生口径：模拟被判真题 {d['mock'][0]}/{d['mock'][1]}"
                  f" = {round(100*d['mock'][0]/max(1,d['mock'][1]),1)}%  CI {d['mock_ci']}")
            print(f"  对照组：真题被判真题 {d['real'][0]}/{d['real'][1]}"
                  f" = {round(100*d['real'][0]/max(1,d['real'][1]),1)}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
