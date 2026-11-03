# -*- coding: utf-8 -*-
"""CET-4 模拟题校验：结构 / 难度 / 答案 / 定位句 / 逐句一致性。"""
import json
import re
import sys

MIN_WORDS, MAX_WORDS = 320, 420
MIN_AVG, MAX_AVG = 15.0, 22.5
MIN_LONG, MAX_LONG = 4.0, 10.0


def words(t):
    return re.findall(r"[A-Za-z][A-Za-z'-]*", t)


def check(payload):
    errs = []
    p = payload.get("passage", "")
    ws = words(p)
    n = len(ws)
    if not (MIN_WORDS <= n <= MAX_WORDS):
        errs.append(f"words={n} not in [{MIN_WORDS},{MAX_WORDS}]")
    sents = [s for s in re.split(r"(?<=[.!?])\s+", p) if len(words(s)) >= 4]
    avg = n / max(1, len(sents))
    if not (MIN_AVG <= avg <= MAX_AVG):
        errs.append(f"avg_sentence={avg:.1f} not in [{MIN_AVG},{MAX_AVG}]")
    long10 = 100 * sum(1 for w in ws if len(w) >= 10) / max(1, n)
    if not (MIN_LONG <= long10 <= MAX_LONG):
        errs.append(f"long10={long10:.1f}% not in [{MIN_LONG},{MAX_LONG}]")
    for s in sents:
        if len(words(s)) > 38:
            errs.append(f"sentence too long ({len(words(s))}w): {s[:50]}")
    qs = payload.get("questions") or []
    if len(qs) != 5:
        errs.append(f"questions={len(qs)} != 5")
    answers = []
    for q in qs:
        no = q.get("no")
        opts = q.get("options") or []
        if len(opts) != 4:
            errs.append(f"Q{no}: options={len(opts)}")
        for o in opts:
            if not re.match(r"^[A-D]\)\s", o):
                errs.append(f"Q{no}: bad option prefix {o[:20]}")
        ans = q.get("answer")
        if ans not in ("A", "B", "C", "D"):
            errs.append(f"Q{no}: answer={ans}")
        answers.append(ans)
        ev = (q.get("evidence") or "").strip()
        if not ev:
            errs.append(f"Q{no}: empty evidence")
        else:
            norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
            if norm(ev) not in norm(p):
                # 允许 evidence 是句子的一部分
                if norm(ev)[:40] not in norm(p):
                    errs.append(f"Q{no}: evidence not in passage")
        if not q.get("paraphrase"):
            errs.append(f"Q{no}: missing paraphrase")
        if not q.get("trap"):
            errs.append(f"Q{no}: missing trap")
        oa = q.get("option_analysis") or []
        if len(oa) != 4:
            errs.append(f"Q{no}: option_analysis={len(oa)} != 4")
        else:
            correct = [x for x in oa if x.get("correct")]
            if len(correct) != 1 or correct[0].get("letter") != q.get("answer"):
                errs.append(f"Q{no}: option_analysis correct flag mismatch")
            for x in oa:
                if not (x.get("why") or "").strip():
                    errs.append(f"Q{no}: option {x.get('letter')} missing why")
    if len(set(answers)) < 3:
        errs.append("answers too concentrated: " + "".join(answers))
    pn = re.sub(r"\s+", " ", p).strip().lower()
    paras = payload.get("paragraphs") or []
    if paras:
        joined = re.sub(r"\s+", " ", " ".join(x.get("en", "") for x in paras)).strip().lower()
        if pn != joined:
            errs.append("paragraphs.en do not concatenate to passage")
        for i, para in enumerate(paras, 1):
            for key in ("cn", "main", "structure"):
                if not (para.get(key) or "").strip():
                    errs.append(f"paragraph {i} missing {key}")
            para_en = re.sub(r"\s+", " ", (para.get("en") or "")).strip().lower()
            for j, sent in enumerate(para.get("sentences") or [], 1):
                sen = re.sub(r"\s+", " ", sent.get("en") or "").strip().lower()
                if not sen:
                    errs.append(f"p{i}s{j}: empty sentence")
                    continue
                if sen not in para_en:
                    errs.append(f"p{i}s{j}: sentence not in paragraph")
                chunks = sent.get("chunks") or []
                if not chunks:
                    errs.append(f"p{i}s{j}: no chunks")
                    continue
                def flat(x):
                    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", x.lower())
                joined = "".join(c.get("en", "") for c in chunks)
                if flat(joined) != flat(sen):
                    errs.append(f"p{i}s{j}: chunks do not rebuild sentence")
                for c in chunks:
                    if not (c.get("cn") or "").strip():
                        errs.append(f"p{i}s{j}: chunk missing cn")
                    if not (c.get("role") or "").strip():
                        errs.append(f"p{i}s{j}: chunk missing role")
        if len(paras) < 3:
            errs.append(f"paragraphs={len(paras)} < 3")
    else:
        ss = payload.get("sentences") or []
        joined = re.sub(r"\s+", " ", " ".join(x.get("en", "") for x in ss)).strip().lower()
        if pn != joined:
            errs.append("sentences.en do not concatenate to passage")
    return {"words": n, "avg_sentence": round(avg, 1), "long10_pct": round(long10, 1),
            "questions": len(qs), "errors": errs, "ok": not errs}


if __name__ == "__main__":
    path = sys.argv[1]
    data = json.load(open(path, encoding="utf-8"))
    print(json.dumps(check(data), ensure_ascii=False, indent=1))
