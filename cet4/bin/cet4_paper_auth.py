# -*- coding: utf-8 -*-
"""整卷级「真题感」评测：按“试卷档案”评，不只看正文。

档案 = 选词填空开头 + 词库、匹配陈述 10 条、两篇阅读题干 10 条、翻译中文、写作要求。
（正文文本另在篇章级评测里已测过，这里专门测题目/翻译/写作是否也像真题。）

对模拟卷与官方真题各取若干份，匿名混排，1-5 打分，输出均值对照。

用法: python cet4/bin/cet4_paper_auth.py --mock 81,84,97 --real 3 --judges 2
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
import statistics as st
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "var" / "cet4-daily" / "papers"
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
OUT = ROOT / "var" / "cet4-daily" / "line-compare"
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")

PROMPT = """下面是若干份「四级试卷档案」，每份摘录了该卷的：选词填空开头与词库、信息匹配的 10 条陈述、两篇阅读的题干、翻译题中文、写作要求。
请逐份打分：作为一份**大学英语四级试卷**，它的「真题感」有多强（1=不像真题，3=一般，5=就是真题的样子）。
只看题目与题干本身（不看正文难度、不看答案）。并给半句理由。
只输出 JSON：[{"id":"X1","score":4,"reason":"<=20字"}]

"""


def cb(prompt: str, timeout: int = 2400) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=str(ROOT))
    return p.stdout or ""


def jp(t: str):
    """从模型输出里抠 JSON：支持 ``` 围栏、前后夹带解释、以及被转义的中文引号。"""
    if not t:
        return {}
    t = t.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"```\s*$", "", t).strip()
    dec = json.JSONDecoder()
    for m in re.finditer(r"[\[{]", t):
        try:
            obj, _ = dec.raw_decode(t[m.start():])
            return obj
        except json.JSONDecodeError:
            continue
    return {}


def mock_profile(pid: str) -> str:
    d = json.loads((PAPERS / f"paper-{pid}.json").read_text(encoding="utf-8"))
    r = d["reading"]
    cloze = r.get("cloze") or {}
    txt = (cloze.get("passage") or "")[:320]
    bank = cloze.get("bank") or {}
    out = [f"【选词填空】{txt}…", f"词库：{' / '.join(f'{k}.{v}' for k, v in bank.items())}"]
    sts = [f'{x.get("no")}. {x.get("text")}' for x in (r.get("match") or {}).get("statements") or []]
    out.append("【信息匹配陈述】" + "；".join(sts))
    stems = []
    for name in ("passage1", "passage2"):
        for q in (r.get(name) or {}).get("questions") or []:
            stems.append(f'{q.get("no")}. {q.get("stem")}')
    out.append("【阅读题干】" + "；".join(stems))
    out.append("【翻译】" + str((d.get("translation") or {}).get("zh") or ""))
    out.append("【写作要求】" + str((d.get("writing") or {}).get("directions") or ""))
    return "\n".join(out)


def real_profiles(n=3, seed=17) -> list:
    """从真题 markdown 抽档案，**字段与截断口径与 mock_profile 完全一致**，
    否则「真题被截断、模拟完整」会让评委靠完整性而不是真题感判断。"""
    out = []
    for md in sorted(BANK.rglob("*.md")):
        t = md.read_text(encoding="utf-8", errors="ignore")
        parts = re.split(r"^##\s*Part\s+(I{1,3}V?|IV)\b", t, flags=re.M)
        seg = {}
        for i in range(1, len(parts), 2):
            seg[parts[i].strip()] = parts[i + 1] if i + 1 < len(parts) else ""
        read = seg.get("III", "")
        secs = re.split(r"^###\s*Section\s*([ABC])\b", read, flags=re.M)
        sec = {secs[i].strip(): secs[i + 1] for i in range(1, len(secs), 2)}
        a_raw = sec.get("A", "")
        # 去掉 Directions 说明块与词库表格，只留正文；词库单独解析
        a_body = re.sub(r"(?is)^.*?\bDirections?\b.*?\n\s*\n", "", a_raw, count=1)
        bank_rows = re.findall(r"\|\s*([A-O])\)?[.、]?\s*([A-Za-z][A-Za-z'-]*)", a_raw)
        if len(bank_rows) < 10:
            a_body = a_raw
        a_body = re.sub(r"\|.*", "", a_body)
        a_body = re.sub(r"(?i)\*\*Questions?.*?\*\*", "", a_body)
        cloze_txt = re.sub(r"\s+", " ", a_body).strip()[:320]
        bank_rows = sorted(dict(bank_rows).items())[:15]
        bank_str = " / ".join(f"{k}.{v}" for k, v in bank_rows) if len(bank_rows) >= 10 else ""
        sts = [x for x in re.findall(r"^\s*(\d{2})\.\s*(.+)$", sec.get("B", ""), flags=re.M)
               if 36 <= int(x[0]) <= 45][:10]
        stems = [x for x in re.findall(r"^\s*(\d{2})\.\s*(.+?[?？])\s*$", sec.get("C", ""), flags=re.M)
                 if 46 <= int(x[0]) <= 55][:10]
        def _clean(x: str) -> str:
            x = re.sub(r"(?is)^\s*/[^/]{0,30}/\s*\(\d+\s*minutes\)", "", x)
            x = re.sub(r"(?is)\*\*Directions?:?\*\*", "", x)
            x = re.sub(r"(?is)_+", "", x)
            return re.sub(r"\s+", " ", x).strip()

        trans = _clean(seg.get("IV", ""))
        write = _clean(seg.get("I", ""))
        if len(sts) < 8 or len(stems) < 8 or not cloze_txt:
            continue
        out.append("\n".join([
            f"【选词填空】{cloze_txt}…" + (f"\n词库：{bank_str}" if bank_str else ""),
            "【信息匹配陈述】" + "；".join(f"{a}. {b.strip()}" for a, b in sts),
            "【阅读题干】" + "；".join(f"{a}. {b.strip()}" for a, b in stems),
            f"【翻译】{trans}",
            f"【写作要求】{write}",
        ]))
    random.Random(seed).shuffle(out)
    return out[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="81,84,97")
    ap.add_argument("--real", type=int, default=3)
    ap.add_argument("--judges", type=int, default=2)
    ap.add_argument("--tag", default="paper-auth")
    args = ap.parse_args()

    items = []
    for pid in [x for x in re.split(r"[,\s]+", args.mock) if x]:
        items.append({"id": f"M{pid}", "text": mock_profile(pid), "group": "mock"})
    for i, t in enumerate(real_profiles(args.real), 1):
        items.append({"id": f"R{i}", "text": t, "group": "real"})
    print(f"档案：模拟 {sum(1 for i in items if i['group']=='mock')} + 真题 {sum(1 for i in items if i['group']=='real')}")

    def judge(k):
        order = list(items)
        random.Random(900 + k).shuffle(order)
        body = "\n\n=====\n\n".join(f"[{it['id']}]\n{it['text']}" for it in order)
        return {str(g.get("id")): g.get("score") for g in jp(cb(PROMPT + body))}

    with ThreadPoolExecutor(max_workers=args.judges) as ex:
        votes = list(ex.map(judge, range(args.judges)))

    def sc(iid):
        v = [x.get(iid) for x in votes if isinstance(x.get(iid), (int, float))]
        return round(st.mean(v), 2) if v else None

    rows = [(i["id"], i["group"], sc(i["id"])) for i in items]
    for iid, grp, s in rows:
        print(f"  {iid:6} {grp:5} {s}")
    mock = [s for _, g, s in rows if g == "mock" and s]
    real = [s for _, g, s in rows if g == "real" and s]
    print(f"\n模拟均值 {round(st.mean(mock),2) if mock else '-'} | 真题均值 {round(st.mean(real),2) if real else '-'} "
          f"| 差 {round(st.mean(mock)-st.mean(real),2) if mock and real else '-'}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{args.tag}.json").write_text(json.dumps({"rows": rows, "votes": votes}, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
