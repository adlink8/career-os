#!/usr/bin/env python3
"""CET-4 整套模拟卷拼装+实测校验：parts/*.md -> cet4-mock-XX.md + mock-XX-answers.json
校验只信实测，不信子代理自报数据。规则来源：07-整套模拟卷/spec.md"""
import json, re, sys, collections, itertools
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
REAL = ROOT / "knowledge/cet4-bank/01-历年真题-Markdown/2023.06/cet4-2023-06-1.md"
VOCAB = ROOT / "knowledge/cet4-bank/04-高频词汇与大纲词库/大学英语四级完整大纲词汇.txt"
ANSWER_HEADS = ("### 答案与解析", "### 评分要点", "### 参考译文", "### 满分范文", "### 得分点")
ORDER = ["part1-writing.md", "part2-listening.md", "part3-ab.md", "part3-c.md", "part4-translation.md"]

wc = lambda s: re.findall(r"[A-Za-z']+", s)


def fold_answers(text):
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(ANSWER_HEADS)), None)
    if start is None:
        return text
    body = "\n".join(lines[start:])
    m = re.search(r"```json[\s\S]*?```\s*$", body)
    inner, tail = (body[:m.start()], body[m.start():]) if m else (body, "")
    folded = "<details>\n<summary>📖 答案与解析（做完再展开）</summary>\n\n" + inner + "\n</details>\n\n" + tail
    return "\n".join(lines[:start]) + "\n\n" + folded


def extract_json(text):
    blocks = re.findall(r"```json\s*([\s\S]*?)```", text)
    return json.loads(blocks[-1]) if blocks else {}


def norm(s):
    return re.sub(r"\s+", " ", s).replace("*", "").strip()


def load_vocab():
    """大纲词集 = 大纲txt ∪ 核心json ∪ 6 套真题语料（真题出现过的词一律视为纲内）。"""
    v = set()
    for line in VOCAB.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.split()
        if s and re.fullmatch(r"[a-zA-Z]+", s[0]):
            v.add(s[0].lower())
    try:
        d = json.loads((VOCAB.parent / "cet4-core-vocab.json").read_text(encoding="utf-8"))
        for w in d.get("cet4CoreWords", []):
            v.add((w.get("word") if isinstance(w, dict) else w).lower())
    except Exception:
        pass
    for f in (VOCAB.parent.parent / "01-历年真题-Markdown").rglob("*.md"):
        v.update(x.lower() for x in wc(f.read_text(encoding="utf-8")))
    return v


def lemma(w, vocab):
    cand = [w, w.rstrip("s"), re.sub(r"es$", "", w), re.sub(r"ing$", "", w),
            re.sub(r"ing$", "", w) + "e", re.sub(r"ed$", "", w), re.sub(r"ed$", "", w) + "e",
            re.sub(r"ed$", "", w) + "ing", re.sub(r"ly$", "", w), re.sub(r"ily$", "y", w)]
    return any(c in vocab for c in cand if c)


def offsyllabus(text, vocab):
    words = wc(text)
    sentences = re.split(r"[.!?]+", text)
    starts = set(re.sub(r"[.!?]+$", "", s).split()[:1][0].lower() for s in sentences if s.split())
    oov = []
    for i, w in enumerate(words):
        lw = w.lower()
        if len(lw) < 3 or not lw.isalpha() or lw in vocab or lemma(lw, vocab):
            continue
        if w[0].isupper() and lw not in starts:  # 句首大写/专有名词宽判
            continue
        oov.append(w)
    return sorted(set(oov))


def metrics(text, vocab, lo, hi, maxasl=18, maxlong=36, label=""):
    errs = []
    n = len(wc(text))
    if not lo <= n <= hi:
        errs.append(f"[{label}] 实测 {n} 词，超出区间 {lo}-{hi}")
    sents = [s for s in re.split(r"[.!?]+", text) if wc(s)]
    asl = sum(len(wc(s)) for s in sents) / max(len(sents), 1)
    if asl > maxasl:
        errs.append(f"[{label}] 平均句长 {asl:.1f} > {maxasl}")
    longw = {w.lower() for w in wc(text) if len(w) >= 10}
    if len(longw) > maxlong:
        errs.append(f"[{label}] ≥10 字母长词 {len(longw)} 个 > {maxlong}（真题实测 17-31）")
    oov = offsyllabus(text, vocab)
    return n, round(asl, 1), sorted(longw - vocab)[:15], errs


def passage(md, start_pat, end_pat):
    m = re.search(start_pat, md)
    if not m:
        return ""
    rest = md[m.end():]
    e = re.search(end_pat, rest)
    return rest[:e.start()] if e else rest[:4000]


def validate(md, flat, vocab):
    errs, info = [], []
    for q in map(str, range(1, 56)):
        if q not in flat:
            errs.append(f"缺答案 {q}")
    for k, v in flat.items():
        i = int(k)
        ok = v in "ABCD" if (i <= 25 or i >= 46) else v in "ABCDEFGHIJKLMNO" if i <= 35 else v in "ABCDEFGHIJK"
        if not ok:
            errs.append(f"{k}={v} 超出该题型字母域")
    abcd = [flat[k] for k in flat if int(k) <= 25 or int(k) >= 46]
    for L in "ABCD":
        if not 6 <= abcd.count(L) <= 12:
            errs.append(f"ABCD 35 题中 {L} 出现 {abcd.count(L)} 次，超出 6-12")
    lst = [flat[str(i)] for i in range(1, 26)]
    if any(len(list(g)) >= 4 for _, g in itertools.groupby(lst)):
        errs.append("听力出现连续 ≥4 个相同答案")
    for i in range(1, 56):
        if not re.search(rf"(?m)^\s*\**{i}\.\s", md):
            errs.append(f"卷面缺题号 {i}")
    # Directions 逐字对真题（只审 boilerplate 六段；写作/翻译指令含题目内容，允许不同）
    key = lambda d: re.sub(r"[^a-z]", "", d.lower())
    dmock = [norm(x) for x in re.findall(r"\*\*Directions:?\*\*[_\s]*(.+?)(?=\n\n)", md, re.S)]
    dreal = {norm(x) for x in re.findall(r"\*\*Directions:?\*\*[_\s]*(.+?)(?=\n\n)", REAL.read_text(encoding="utf-8"), re.S)}
    boiler = [d for d in dmock if "In this section" in d or "There are 2 passages" in d]
    rkeys = {key(d) for d in dreal}
    for i, d in enumerate(boiler):
        if key(d) not in rkeys:
            errs.append(f"第 {i+1} 条听力/阅读 Directions 与真题不一致 → {d[:60]}")
    # 篇章实测指标（仅 Part III 区域，避免误配听力 Section A）
    p3 = md.split("## Part III", 1)[1] if "## Part III" in md else md
    cloze = passage(p3, r"### Section A\n\n\*\*Directions.*?\n\n", r"\n\n\|")
    m1 = metrics(cloze, vocab, 240, 280, 22, 999, "cloze")
    match = passage(p3, r"\*\*A\)\*\*", r"(?m)^\s*\**36\.\s")
    n, asl, _, e2 = metrics(match, vocab, 900, 1100, 99, 999, "match")
    info.append(f"cloze: {m1[0]} 词 | match: {n} 词, 句长 {asl}")
    p1 = passage(p3, r"Questions 46 to 50 are based on the following passage\.\*?\*?\n+", r"(?m)^\s*\**46\.\s")
    p2 = passage(p3, r"Questions 51 to 55 are based on the following passage\.\*?\*?\n+", r"(?m)^\s*\**51\.\s")
    r1 = metrics(p1, vocab, 330, 380, 18, 36, "passage1")
    r2 = metrics(p2, vocab, 330, 380, 18, 36, "passage2")
    info.append(f"passage1: {r1[0]} 词 句长 {r1[1]} 生僻长词 {r1[2]} | passage2: {r2[0]} 词 句长 {r2[1]} 生僻长词 {r2[2]}")
    # 听力 tapescript 块（按 part2 原始 details 顺序）
    turns = len(re.findall(r"(?m)^M[.:]", md)) + len(re.findall(r"(?m)^W[.:]", md))
    info.append(f"听力对话总话轮数(2篇合计应有 22-26): {turns}")
    errs += m1[3] + e2 + r1[3] + r2[3]
    return errs, info


def dedupe(md, mock_dir):
    """跨套 10-gram 查重：防止批量生成的题材/句子漂移撞车。剔除 boilerplate 后比对。"""
    def grams(text):
        text = re.sub(r"```[\s\S]*?```", " ", text)  # 剔除代码/答案 json 块：元数据键名不算正文重合
        keep = []
        for l in text.splitlines():
            s = l.strip()
            if (not s or s.startswith(("#", ">", "|", "*", "<", "```"))
                    or "Directions" in s or re.match(r"^[A-O]\)", s)):
                continue
            keep.append(s)
        toks = re.findall(r"[a-z]+", " ".join(keep).lower())
        return {" ".join(toks[i:i + 10]) for i in range(max(len(toks) - 9, 0))}
        # 段落标号 **A)** 行被 "*"-前缀剔除，陈述/正文保留
    g_new = grams(md)
    errs = []
    for other in (mock_dir.parent).glob("mock-*/cet4-mock-*.md"):
        if other.parent == mock_dir:
            continue
        hits = g_new & grams(other.read_text(encoding="utf-8"))
        if hits:
            errs.append(f"与 {other.parent.name} 存在 {len(hits)} 处 10-gram 重合，例: {next(iter(hits))[:60]}")
    return errs


def main(mock_dir: Path):
    parts = mock_dir / "parts"
    texts = {p: (parts / p).read_text(encoding="utf-8") for p in ORDER}
    flat, meta, conflicts = {}, {}, []
    for t in texts.values():
        d = extract_json(t)
        meta.update(d.get("word_counts", {}))
        for k, v in d.get("answers", d).items():
            tgt = flat if str(k).isdigit() else meta
            key = str(k) if str(k).isdigit() else k
            if key in tgt and tgt[key] != v:
                conflicts.append(f"跨文件答案键冲突 {key}: {tgt[key]!r} vs {v!r}")
            tgt[key] = v
    c = texts["part3-c.md"].splitlines()
    texts["part3-c.md"] = "\n".join(c[1:]).lstrip("\n")
    stem = mock_dir.name  # e.g. mock-01
    doc = [f"# CET-4 全真模拟卷 {stem}", "",
           "> 严格对标 2023 年真题结构与难度（生成规范见 `../spec.md`）。全卷 125 分钟。", ""]
    for p in ORDER:
        doc.append(fold_answers(texts[p]).rstrip())
        doc.append("\n\n---\n")
    md = "\n".join(doc)
    vocab = load_vocab()
    errs, info = validate(md, flat, vocab)
    errs = conflicts + errs + dedupe(md, mock_dir)
    out = {"listening": [flat[str(i)] for i in range(1, 26)],
           "reading": [flat[str(i)] for i in range(26, 56)],
           "writing_prompt": meta.get("writing_prompt") or meta.get("writing_theme", ""),
           "translation_prompt": meta.get("translation_prompt") or meta.get("translation_theme", "")}
    (mock_dir / f"cet4-{stem}.md").write_text(md, encoding="utf-8")
    (mock_dir / f"{stem}-answers.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("实测信息:")
    for line in info:
        print(" ", line)
    print("校验结果:", "全部通过 ✓" if not errs else "发现问题 ↓\n" + "\n".join(" - " + e for e in errs))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "knowledge/cet4-bank/07-整套模拟卷/mock-01"))
