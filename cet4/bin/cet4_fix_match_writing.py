# -*- coding: utf-8 -*-
"""按真题口径重做「信息匹配陈述」与「写作要求」（第 19 轮诊断结论）。

诊断依据（评委原句对照，见 line-compare/paper-auth-gaps2.json）：
1. 匹配陈述不能 10 条全是「主体+动词+对象」的直陈句，真题里有一半是抽象命题重述/类比
   （like / as if / genetically determined / regarded as），且不带专名和数字这种显眼定位词
2. 写作不能三套一个句式；每 3 套要有 1 套用 "Suppose it is proposed that…" 并给两个评价维度，
   还要带上 "You will have 30 minutes" 与 "at least 120 words but no more than 180 words"

用法: python cet4/bin/cet4_fix_match_writing.py --papers 81,82,... [--workers 3]
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
PAPERS = ROOT / "var" / "cet4-daily" / "papers"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

MATCH = """下面是四级信息匹配题的 12 个段落（A-L）。请重写 **10 条陈述**（36-45），风格照真题：

## 风格配额（必须满足）
- **至少 5 条**是抽象命题重述或类比，含 like / as if / is regarded as / is genetically determined / is taken as 这类结构；
  这类陈述**不带**专有名词和数字（不带 G20、2025、38% 之类一眼能定位的标记）
- **至少 3 条**用研究框架句式：Researchers found that… / Research suggests that… / It is advised that… / Studies show that…
- 其余可以是具体信息，但**每条**都要靠理解段落主旨才能对上，不能靠扫关键词
- 10 条里专有名词总数不超过 3 个

## 硬要求
- 每条只能对应一个段落（不能有两条都说得通的）
- 与段落原句**不许逐字相同**，必须同义改写
- 每条 10-20 词，长度接近

## 段落
{paras}

只输出 JSON：{{"statements":[{{"no":36,"text":"...","para":"D"}}]}}"""

WRITE = """你在出四级写作题的第 {idx} 套。风格必须与前三套不同。

## 三种骨架，本套用第 {kind} 种
1. 「Suppose your university is seeking students' opinions on whether {hint}. You are now to write an essay to express your view.」
2. 「Suppose it is proposed that {hint2}. You are now to write an essay stating what you think of the proposal in terms of its **{dim1} and {dim2}**.」
3. 「Suppose your class is discussing whether {hint}. You are now to write an essay explaining your position and giving one example.」

## 硬要求
- directions 必须包含：场景句 + 任务句 + 「You will have 30 minutes for the task.」+「You should write at least 120 words but no more than 180 words.」
- 只允许**一个**场景、**一句**任务，不许再叠加「至少两个理由」「处理反方观点」「自拟标题」
- 配 140-170 词范文 + 2-3 条扣分点

只输出 JSON：{{"directions":"...","model_essay":"...","deductions":["..."]}}"""


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


def one(item) -> str:
    idx, pid = item
    f = PAPERS / f"paper-{pid}.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    logs = []

    # ---- 信息匹配陈述 ----
    m = d["reading"]["match"]
    paras = m.get("paragraphs") or {}
    if paras:
        txt = "\n\n".join(f'[{k}] {v}' for k, v in paras.items())
        res = jp(cb(MATCH.replace("{paras}", txt)))
        sts = res.get("statements") or []
        if len(sts) == 10 and all(x.get("para") for x in sts):
            m["statements"] = [{"no": int(x["no"]), "text": x["text"].strip()} for x in sts]
            m["answers"] = {str(int(x["no"])): str(x["para"]).upper()[:1] for x in sts}
            abstract = sum(1 for x in sts if re.search(r"\b(like|as if|regarded as|genetically|taken as)\b", x["text"], re.I))
            logs.append(f"匹配重写 10 条（抽象句 {abstract} 条）")
        else:
            logs.append("匹配重写失败")

    # ---- 写作 ----
    hint = {
        "81": "the university library should stay open around the clock during exam weeks",
        "82": "university sports facilities should be open to the public",
        "83": "students should be required to take at least one art course",
        "84": "the university should provide more part-time jobs on campus",
        "85": "final exams should be replaced by course papers",
        "86": "students should live off campus after the second year",
        "87": "the university canteen should stop using disposable tableware",
        "97": "every student should do one term of community service",
        "98": "the university should set up a 24-hour study room in each dormitory",
        "99": "students should be allowed to choose their own roommates",
    }.get(pid, "the university should improve campus facilities")
    hint2 = {
        "81": "all first-year students must take a course on academic writing",
        "82": "every student must complete 40 hours of physical exercise each term",
        "83": "students should be required to learn one art form before graduation",
        "84": "all students must work at least one term in a company before graduating",
        "85": "course papers should replace written final exams",
        "86": "second-year students should move out of campus dormitories",
        "87": "the campus canteen should ban single-use plastic tableware",
        "97": "community service should become a graduation requirement",
        "98": "each dormitory building should have a 24-hour study room",
        "99": "students should be allowed to choose their roommates freely",
    }.get(pid, "the university should change its campus rules")
    kind = (idx % 3) + 1                      # 三套一轮，句式轮换
    dims = [("necessity", "practicality"), ("benefits", "feasibility"), ("fairness", "effectiveness")][idx % 3]
    w = jp(cb(WRITE.replace("{idx}", str(idx + 1)).replace("{kind}", str(kind))
                            .replace("{hint}", hint).replace("{hint2}", hint2)
                            .replace("{dim1}", dims[0]).replace("{dim2}", dims[1])))
    if w.get("directions"):
        d["writing"] = {"directions": w["directions"], "model_essay": w.get("model_essay") or "",
                        "deductions": w.get("deductions") or []}
        logs.append(f"写作骨架 {kind}")
    else:
        logs.append("写作重写失败")

    f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return f"paper-{pid}: " + " / ".join(logs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", default="81,82,83,84,85,86,87,97,98,99")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    pids = [x for x in re.split(r"[,\s]+", args.papers) if x]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for msg in ex.map(one, list(enumerate(pids))):
            print(" ", msg, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
