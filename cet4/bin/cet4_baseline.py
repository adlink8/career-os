# -*- coding: utf-8 -*-
"""把真题基线算成一份可复用的文件（结构 + 难度参考值 + 判据能力），不再散落各处。

产物:
  var/cet4-daily/baseline/baseline.json   机读
  var/cet4-daily/baseline/BASELINE.md     人读（给审查员/出题老师看的基线说明）

说明：这里的数字只是「参照」，不是判定门；谁算达标仍由独立 LLM 审查员给 verdict。

用法: python cet4/bin/cet4_baseline.py [--gaps]
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
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "knowledge" / "cet4-bank" / "01-历年真题-Markdown"
ANS = ROOT / "knowledge" / "cet4-bank" / "02-真题标准答案" / "cet4-answers.json"
OUT = ROOT / "var" / "cet4-daily" / "baseline"


def split_parts(text: str) -> dict:
    """按 "## Part X" 切成四大部分。"""
    marks = [(m.start(), m.group(1)) for m in re.finditer(r"^##\s*(Part [IVX]+)[^\n]*$", text, flags=re.M)]
    out = {}
    for i, (pos, key) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        out[key] = text[pos:end]
    return out


def split_sections(part_text: str) -> dict:
    marks = [(m.start(), m.group(1)) for m in re.finditer(r"^###\s*(Section [ABC])[^\n]*$", part_text, flags=re.M)]
    out = {}
    for i, (pos, key) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(part_text)
        out[key] = part_text[pos:end]
    return out


def clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)          # <u>&emsp;35&emsp;</u> 之类
    s = re.sub(r"&[a-z]+;", " ", s)
    s = re.sub(r"^#{1,4}.*$", "", s, flags=re.M)
    return s


def words(s: str) -> int:
    return len(re.findall(r"[A-Za-z][A-Za-z'-]*", s))


def cjk(s: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", s))


def per_file(md: Path) -> dict:
    t = md.read_text(encoding="utf-8", errors="ignore")
    parts = split_parts(t)
    rec = {"file": str(md.relative_to(BANK))}

    # Part I 写作
    rec["writing_words_directions"] = words(clean(parts.get("Part I", "")))

    # Part II 听力
    lsn = parts.get("Part II", "")
    lq = len(re.findall(r"^\s*\d{1,2}[.)]\s", lsn, flags=re.M))
    rec["listening_questions"] = lq if lq else None       # -3 套与第二套共用听力，不单列
    rec["listening_words_script"] = words(clean(lsn))

    # Part III 阅读
    r3 = parts.get("Part III", "")
    secs = split_sections(r3)
    a = secs.get("Section A", "")
    rec["cloze_blanks"] = len({n for n in re.findall(r"\b(2[6-9]|3[0-5])\b", clean(a))})
    body_a = clean(a)
    paras = [x for x in body_a.split("\n\n") if x.strip()]
    while paras and ("Directions" in paras[0] or paras[0].strip().startswith("-")):
        paras.pop(0)                                     # 去掉说明段
    body_a = "\n\n".join(paras)
    cut = re.search(r"^\s*\|", body_a, flags=re.M)      # 词库是 markdown 表格
    rec["cloze_words_passage"] = words(body_a[:cut.start()] if cut else body_a)

    b = secs.get("Section B", "")
    para_lines = [l for l in b.splitlines() if re.match(r"^\s*[A-O]\)\s+\S", l)]
    rec["match_paragraphs"] = len(para_lines)
    rec["match_statements"] = len(re.findall(r"^\s*(3[6-9]|4[0-5])[.)]\s", b, flags=re.M))
    rec["match_words_paragraphs"] = sum(words(clean(l)) for l in para_lines)

    c = secs.get("Section C", "")
    ps = re.split(r"####\s*Passage (?:One|Two)", c)[1:]
    rec["reading_passages"] = len(ps)
    rec["reading_words"] = []
    for p in ps:
        body = clean(p)
        body = body.split("**Questions", 1)[-1]
        body = body.split("\n", 1)[-1] if "based on the following passage" in body.split("\n", 1)[0] else body
        cut2 = re.search(r"^\s*(4[6-9]|5[0-5])[.)]\s", body, flags=re.M)
        rec["reading_words"].append(words(body[:cut2.start()] if cut2 else body))
    rec["reading_questions"] = len(re.findall(r"^\s*(4[6-9]|5[0-5])[.)]\s", c, flags=re.M))

    # Part IV 翻译
    tr = parts.get("Part IV", "")
    rec["translation_cjk"] = cjk(clean(tr).split("**Directions")[-1])
    return rec


def aggregate(rows: list, key: str) -> dict:
    vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
    if not vals:
        return {"n": 0}
    vals_sorted = sorted(vals)
    n = len(vals_sorted)
    return {"n": n, "min": vals_sorted[0], "p25": vals_sorted[int(0.25 * (n - 1))],
            "median": st.median(vals_sorted), "p75": vals_sorted[int(0.75 * (n - 1))], "max": vals_sorted[-1]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gaps", action="store_true", help="只打印数据缺口")
    args = ap.parse_args()

    files = sorted(BANK.rglob("*.md"))
    rows = [per_file(f) for f in files]

    # 难度参考值（来自 cet4_difficulty.py 的产物）
    diff_path = ROOT / "var" / "cet4-daily" / "difficulty.json"
    diff = json.loads(diff_path.read_text(encoding="utf-8")) if diff_path.exists() else {}
    real_m = diff.get("real") or []
    metric_keys = ["words", "wps", "wordlen", "long9", "syl_cov", "clause100", "passive100", "flesch"]
    metrics = {k: aggregate([{k: m[k]} for m in real_m], k) for k in metric_keys}

    # 判据能力（来自 real-baseline 的产物）
    rb = ROOT / "var" / "cet4-daily" / "real-baseline"
    solve_ok = solve_tot = 0
    for f in rb.glob("*.solve.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        solve_ok += sum(1 for r in d["rows"] if r["ok"])
        solve_tot += len(d["rows"])
    flag_files = sorted(rb.glob("*.flag.json"))
    flagged = 0
    types = {}
    for f in flag_files:
        d = json.loads(f.read_text(encoding="utf-8"))
        ds = d.get("defects") or []
        if ds:
            flagged += 1
        for x in ds:
            types[x.get("type")] = types.get(x.get("type"), 0) + 1

    # 答案覆盖
    keys = json.loads(ANS.read_text(encoding="utf-8")) if ANS.exists() else {}
    cov = {}
    for folder in sorted({r["file"].split("\\")[0].split("/")[0] for r in rows}):
        akey = "cet4-" + folder.replace(".", "-")
        entry = keys.get(akey) or {}
        have = sum(1 for s in entry.values() if len((s or {}).get("reading") or []) >= 30)
        cov[folder] = {"sets_with_reading_answers": have, "sets": len(entry)}

    baseline = {
        "generated_at": "2026-11-04",
        "source": {"papers": len(files), "answers_json": str(ANS.relative_to(ROOT))},
        "structure": {k: aggregate(rows, k) for k in (
            "listening_questions", "cloze_blanks", "cloze_words_passage", "match_statements",
            "match_paragraphs", "match_words_paragraphs", "reading_passages", "reading_questions",
            "translation_cjk", "writing_words_directions")},
        "reading_words_per_passage": [w for r in rows for w in r.get("reading_words") or []],
        "difficulty_reference": metrics,
        "judge_capability": {
            "solve_accuracy": round(100 * solve_ok / max(1, solve_tot), 1),
            "solve_n": solve_tot,
            "flag_flagged_ratio": round(100 * flagged / max(1, len(flag_files)), 1),
            "flag_n": len(flag_files),
            "flag_types": types,
        },
        "answer_coverage": cov,
        "caveats": [
            "7 套「-3」卷与第二套共用听力（listening_not_provided），听力题数记 N/A，不参与统计",
            "2023.06 两套选词填空只解析出 9 个空（原文标记格式不同），空数统计按 9–10 区间",
            "2026.06 三套无官方 KEYS 页（answers_unavailable），未纳入判据校准样本",
            "2020-2023 部分为扫描件转写，标点/OCR 噪声未逐字校对（bank-fixed 副本仅覆盖机械问题）",
            "所有指标只是参照值，不构成通过/不通过判定",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "baseline.json").write_text(json.dumps(baseline, ensure_ascii=False, indent=1), encoding="utf-8")

    s = baseline["structure"]
    md = ["# CET-4 真题基线（参照值，非判定门）", "",
          f"来源：{len(files)} 套真题 Markdown；判据校准样本 {solve_tot} 题。生成：2026-11-04", "",
          "## 结构", "", "| 项 | n | 最小 | P25 | 中位 | P75 | 最大 |", "|---|---:|---:|---:|---:|---:|---:|"]
    labels = {"listening_questions": "听力题数", "cloze_blanks": "选词填空空数",
              "cloze_words_passage": "选词正文词数", "match_statements": "匹配陈述数",
              "match_paragraphs": "匹配段落数", "match_words_paragraphs": "匹配段落总词数",
              "reading_passages": "仔细阅读篇数", "reading_questions": "仔细阅读题数",
              "translation_cjk": "翻译汉字数", "writing_words_directions": "写作题干词数"}
    for k, lbl in labels.items():
        a = s[k]
        md.append(f'| {lbl} | {a.get("n",0)} | {a.get("min","-")} | {a.get("p25","-")} | {a.get("median","-")} | {a.get("p75","-")} | {a.get("max","-")} |')
    rw = sorted(baseline["reading_words_per_passage"])
    md += ["", f'仔细阅读单篇词数：n={len(rw)}，最小 {rw[0]}，中位 {st.median(rw)}，最大 {rw[-1]}', "",
           "## 难度参考值（42 篇正文）", "", "| 指标 | 中位 | P25 | P75 |", "|---|---:|---:|---:|"]
    for k, a in baseline["difficulty_reference"].items():
        md.append(f'| {k} | {round(a.get("median",0),2)} | {round(a.get("p25",0),2)} | {round(a.get("p75",0),2)} |')
    jc = baseline["judge_capability"]
    md += ["", "## 判据能力校准（官方真题）", "",
           f'- 盲做正确率：**{jc["solve_accuracy"]}%**（{jc["solve_n"]} 题）',
           f'- 「找错」判据在真卷上的报警率：**{jc["flag_flagged_ratio"]}%**（{jc["flag_n"]} 篇）',
           f'- 报警类型：{jc["flag_types"]}', "",
           "## 数据缺口（gaps）", ""]
    md += [f"- {c}" for c in baseline["caveats"]]
    for folder, c in cov.items():
        md.append(f'- {folder}: 有阅读答案的套数 {c["sets_with_reading_answers"]}/{c["sets"]}')
    (OUT / "BASELINE.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    if args.gaps:
        for c in baseline["caveats"]:
            print("-", c)
        for folder, c in cov.items():
            print(f'- {folder}: {c["sets_with_reading_answers"]}/{c["sets"]}')
        return 0

    print("结构 n / 中位 / 范围：")
    for k, lbl in labels.items():
        a = s[k]
        print(f'  {lbl}: {a.get("n")} / {a.get("median","-")} / {a.get("min","-")}–{a.get("max","-")}')
    print(f'\n判据：盲做 {jc["solve_accuracy"]}%（{jc["solve_n"]} 题）| 找错报警 {jc["flag_flagged_ratio"]}%（{jc["flag_n"]} 篇）')
    print("产物:", OUT / "baseline.json", "|", OUT / "BASELINE.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
