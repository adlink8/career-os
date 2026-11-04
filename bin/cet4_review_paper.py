# -*- coding: utf-8 -*-
"""整卷审查老师：多票独立审查（默认 3 位，互不可见），取多数 verdict。

脚本只负责拼证据与汇总票数；通过与否**一律由审查老师判定**，不做任何分数硬门。

用法:
  python bin/cet4_review_paper.py var/cet4-daily/demo-whole-paper.json [--voters 3]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CB = Path(r"C:\Users\li\AppData\Roaming\npm\codebuddy.cmd")
PLAIN = ROOT / "var" / "cet4-daily" / "paper-demo" / "plain" / "index.html"
EXPLAIN = ROOT / "var" / "cet4-daily" / "paper-demo" / "explain" / "index.html"

PROMPT = """你是四级（CET-4）整卷审查老师。下面是一套待发布的模拟卷证据包，判断它能否作为**一套完整、可直接用于备考的模拟卷**。

【统一评分标准，必须遵守】score 为 0-100 整数：
- 90-100：结构、题源去重、题目质量、配套齐全全部达标，可直接发。
- 85-89：仅有不影响做题的瑕疵。
- 70-84：存在必须修改的问题（跨节同源、答案失衡、题目不可解、配套缺失）。
- <70：不成立，需重做。
verdict 只能是 pass 或 needs_revision；只有 score>=85 且 must_fix 为空才可 pass。

【必查项】
1. 结构：57 题、听力 25 + 选词 10 + 匹配 10 + 仔细 10 + 翻译 + 写作，配比是否与真题一致。
2. **题源去重：不同大题的原文是否来自同一篇文章（最容易漏的致命问题）**。证据包给了标题、来源、开头段与词汇重合度。
3. 答案分布：客观题字母是否过度集中；匹配题是否有重复段落；选词是否一字母多用。
4. 题目可解性：填空是否唯一、匹配陈述是否有对应段、仔细阅读是否题文同序、正确项是否同义替换。
5. 配套：音频、双语字幕、逐句解析、翻译参考、写作范文是否齐全（证据包给了覆盖率统计）。
6. 一致性：题干、选项、答案、解析四处是否自洽。

【输出格式】只输出一个 JSON 对象，不要任何解释性文字、不要 Markdown 表格：
{{"verdict":"pass|needs_revision","score":0,"must_fix":[{{"id":"M1","severity":"blocker|high|medium","problem":"具体到题号或段落","fix":"具体改法"}}],"pass_items":["通过项"]}}

【证据包】
{dossier}
"""


def cb(prompt: str) -> str:
    p = subprocess.run([str(CB), "-p", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=1200, cwd=str(ROOT))
    return p.stdout or ""


def parse_json(text: str):
    t = re.sub(r"^```(?:json)?\s*", "", (text or "").strip())
    t = re.sub(r"\s*```$", "", t)
    for m in re.finditer(r"\{", t):
        i = m.start()
        depth = 0
        in_str = esc = False
        for j in range(i, len(t)):
            ch = t[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(t[i:j + 1])
                    except json.JSONDecodeError:
                        break
                    if isinstance(obj, dict) and obj.get("verdict"):
                        return obj
                    break
    return None


def flat_paras(p) -> str:
    if isinstance(p, str):
        return p
    if isinstance(p, dict):
        return " ".join(str(x) for x in p.values() if isinstance(x, str))
    if isinstance(p, list):
        return " ".join(flat_paras(x) for x in p)
    return ""


def section_text(sec: dict) -> str:
    return " ".join([sec.get("passage") or "", flat_paras(sec.get("paragraphs"))])


def bow(s: str) -> set:
    return {w.lower() for w in re.findall(r"[A-Za-z]{6,}", s)}


def explain_coverage() -> dict:
    """讲解版实际覆盖：段落解析、题目解析、字幕、词典。"""
    cov = {"explain_html": EXPLAIN.exists(), "plain_html": PLAIN.exists()}
    if EXPLAIN.exists():
        h = EXPLAIN.read_text(encoding="utf-8", errors="ignore")
        cov.update({
            "paragraph_analysis_blocks": h.count('class="pan"'),
            "question_analysis_blocks": h.count('class="qax"'),
            "listening_transcript_sentences": len(re.findall(r'<div class="line" onclick="seek', h)),
            "listening_vocab_tables": h.count('<table class="vt">'),
            "writing_chunked_sentences": h.count("意群："),
            "match_paragraph_analysis": h.count("对应题号："),
            "cloze_blank_rows": len(re.findall(r"<tr><td><b>\d{2}</b></td>", h)),
            "translation_reference": "参考译文" in h,
            "translation_scoring_points": "踩分点与译法" in h,
        })
    return cov


def build_dossier(paper: dict) -> str:
    r = paper.get("reading") or {}
    L = paper.get("listening") or {}
    parts = []

    sections = []
    for k in ("cloze", "match", "passage1", "passage2"):
        sec = r.get(k) or {}
        txt = section_text(sec)
        paras = sec.get("paragraphs")
        plist = list(paras.values()) if isinstance(paras, dict) else (paras or [])
        n_sent = sum(len(p.get("sentences") or []) for p in plist if isinstance(p, dict))
        n_para_an = sum(1 for p in plist if isinstance(p, dict) and p.get("sentences"))
        sections.append({
            "section": k, "title": sec.get("title"),
            "source": sec.get("source") or sec.get("source_url"),
            "words": len(re.findall(r"[A-Za-z][A-Za-z'-]*", txt)),
            "paragraphs": len(plist), "analysed_paragraphs": n_para_an,
            "analysed_sentences": n_sent,
            "opening": re.sub(r"\s+", " ", txt[:520]),
            "_text": txt,
        })

    def obj_answers():
        out = {}
        if r.get("cloze", {}).get("answers"):
            out["cloze(26-35)"] = "".join(str(v) for v in r["cloze"]["answers"].values())
        if r.get("match", {}).get("answers"):
            out["match(36-45)"] = "".join(str(v) for v in r["match"]["answers"].values())
        for k, rng in (("passage1", "46-50"), ("passage2", "51-55")):
            qs = r.get(k, {}).get("questions") or []
            if qs:
                out[f"{k}({rng})"] = "".join(str(q.get("answer")) for q in qs)
        lq = L.get("questions") or []
        if lq:
            out["listening(1-25)"] = "".join(str(q.get("answer")) for q in lq)
        return out

    strings = obj_answers()
    stats = {
        "total_items": paper.get("meta", {}).get("total"),
        "reading_sections": [{k: v for k, v in s.items() if k != "_text"} for s in sections],
        "reading_answer_strings": strings,
        "answer_letter_counts_overall": dict(Counter(
            ch for s in strings.values() for ch in s if ch.isalpha()).most_common()),
    }
    overlap = []
    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):
            A, B = bow(sections[i]["_text"]), bow(sections[j]["_text"])
            if A and B:
                overlap.append({"pair": f'{sections[i]["section"]}~{sections[j]["section"]}',
                                "jaccard": round(len(A & B) / len(A | B), 3),
                                "shared_rare_words": len(A & B)})
    stats["cross_section_word_overlap"] = overlap
    parts.append("## 结构统计\n" + json.dumps(stats, ensure_ascii=False, indent=1)[:5500])

    # 选词填空给全文（判唯一解必需），其余给开头段（判同源足够）
    cloze = r.get("cloze") or {}
    parts.append("## cloze 全文（含 26-35 空）\n"
                 + re.sub(r"\s+", " ", cloze.get("passage") or "")[:3200]
                 + "\n词库：" + json.dumps(cloze.get("bank") or {}, ensure_ascii=False))

    for s in sections:
        if s["section"] == "cloze":
            continue
        parts.append(f'## {s["section"]}｜{s["title"]}\n来源：{s["source"]}\n'
                     f'正文开头：{s["opening"]}')

    m = r.get("match") or {}
    parts.append("## 匹配陈述（36-45，全文不截断）\n" + json.dumps(
        [{"no": x.get("no"), "text": x.get("text") or ""} for x in (m.get("statements") or [])],
        ensure_ascii=False))

    for k in ("passage1", "passage2"):
        qs = (r.get(k) or {}).get("questions") or []
        parts.append(f"## {k} 题目\n" + json.dumps(
            [{"no": q.get("no"), "stem": (q.get("stem") or "")[:110],
              "options": [o[:85] for o in (q.get("options") or [])],
              "answer": q.get("answer"), "evidence": (q.get("evidence") or "")[:110]} for q in qs],
            ensure_ascii=False))

    lq = L.get("questions") or []
    parts.append("## 听力题目（1-25，全部）\n" + json.dumps(
        [{"no": q.get("no"), "options": [o[:70] for o in (q.get("options") or [])],
          "answer": q.get("answer")} for q in lq], ensure_ascii=False))

    lsec = []
    lexp = {}
    lp = ROOT / "var" / "cet4-daily" / "listening-explain.json"
    if lp.exists():
        lexp = json.loads(lp.read_text(encoding="utf-8"))
    for s in L.get("sections") or []:
        for p in s.get("pieces") or []:
            stem = Path(str(p.get("audio") or "x")).stem
            lx = lexp.get(f"{s.get('name')}-{stem}") or {}
            n_cn = len(lx.get("sentences") or [])
            n_en = len(p.get("timing") or [])
            lsec.append({"sec": s.get("name"), "title": p.get("title"),
                         "audio": bool(p.get("audio")), "timing": n_en,
                         "bilingual_subtitle": f"{n_cn}/{n_en}",
                         "vocab": len(lx.get("words") or []),
                         "qanalysis": len(lx.get("qanalysis") or []),
                         "script_words": len((p.get("script") or "").split()),
                         "questions": len(p.get("questions") or [])})
    parts.append("## 听力配套（双语字幕=有中文的句数/总句数）\n"
                 + json.dumps(lsec, ensure_ascii=False))

    tr = paper.get("translation") or {}
    parts.append("## 翻译\n" + json.dumps(
        {"prompt": tr.get("prompt") or tr.get("zh") or tr.get("cn"),
         "reference": (tr.get("reference") or tr.get("en") or "")[:700]}, ensure_ascii=False))
    wr = paper.get("writing") or {}
    parts.append("## 写作\n" + json.dumps(
        {"prompt": (wr.get("prompt") or wr.get("directions") or "")[:500],
         "sample": (wr.get("sample") or wr.get("model_essay") or "")[:500]}, ensure_ascii=False))

    parts.append("## 讲解版实际覆盖（页面实测）\n" + json.dumps(explain_coverage(), ensure_ascii=False)
                 + "\n注：qax 解析块 = 听力 25 题 + 仔细阅读 10 题；选词 10 空见「逐空表」、匹配 10 题见「段落对应题号」，"
                   "均不计入 qax。")
    return "\n\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paper")
    ap.add_argument("--voters", type=int, default=3)
    args = ap.parse_args()

    pp = Path(args.paper)
    paper = json.loads(pp.read_text(encoding="utf-8"))
    dossier = build_dossier(paper)
    print(f"dossier chars={len(dossier)}", flush=True)

    votes = []
    for i in range(1, args.voters + 1):
        raw = cb(PROMPT.format(dossier=dossier[:30000]))
        (pp.with_name(f"{pp.stem}.paperreview.{i}.raw.txt")).write_text(raw, encoding="utf-8")
        v = parse_json(raw)
        if not v:
            print(f"voter {i}: parse failed (raw saved)", flush=True)
            continue
        votes.append(v)
        (pp.with_name(f"{pp.stem}.paperreview.v{i}.json")).write_text(
            json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"voter {i}: verdict={v.get('verdict')} score={v.get('score')} "
              f"fixes={len(v.get('must_fix') or [])}", flush=True)

    if not votes:
        print("no valid votes")
        return 1

    tally = Counter(v.get("verdict") for v in votes)
    final = "pass" if tally.get("pass", 0) * 2 > len(votes) else "needs_revision"
    scores = sorted(v.get("score") or 0 for v in votes)
    summary = {"votes": [{"verdict": v.get("verdict"), "score": v.get("score")} for v in votes],
               "tally": dict(tally), "final_verdict": final, "scores": scores,
               "score_median": scores[len(scores) // 2]}
    pp.with_name(f"{pp.stem}.paperreview.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
