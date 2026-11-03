# -*- coding: utf-8 -*-
"""CET-4 模拟题校验：结构 / 难度 / 答案 / 定位句 / 逐句一致性。"""
import json
import re
import sys

MIN_WORDS, MAX_WORDS = 320, 420
MIN_AVG, MAX_AVG = 16.0, 22.0
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
    if len(set(answers)) == 1:
        errs.append("all answers identical")
    ss = payload.get("sentences") or []
    joined = re.sub(r"\s+", " ", " ".join(s.get("en", "") for s in ss)).strip().lower()
    if re.sub(r"\s+", " ", p).strip().lower() != joined:
        errs.append("sentences.en do not concatenate to passage")
    return {"words": n, "avg_sentence": round(avg, 1), "long10_pct": round(long10, 1),
            "questions": len(qs), "errors": errs, "ok": not errs}


if __name__ == "__main__":
    path = sys.argv[1]
    data = json.load(open(path, encoding="utf-8"))
    print(json.dumps(check(data), ensure_ascii=False, indent=1))
