# -*- coding: utf-8 -*-
"""edge-tts 整卷朗读 + 与语音逐句对齐的字幕（英+中）。

关键点：字幕以 TTS 的 SentenceBoundary 文本为准（说什么是字幕），
再用模糊匹配把纸面句子的「顺流中文」贴上去，避免按序号对齐全错位。

产物: 同名 .mp3 + .timing.json（[{i,en,cn,start,end}]）
"""
from __future__ import annotations

import argparse
import asyncio
import difflib
import json
import re
from pathlib import Path

import edge_tts


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def split_sentences(block: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", (block or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 3]


def paper_sentences(paper: dict) -> list[str]:
    out = []
    if (paper.get("title") or "").strip():
        out.append(paper["title"].strip())
    for para in paper.get("paragraphs") or []:
        out.extend(split_sentences(para.get("en") or ""))
    if paper.get("questions"):
        out.append("Questions.")
        for q in paper.get("questions") or []:
            out.append(f"Question {q.get('no', 0) + 45}.")
            if q.get("stem"):
                out.extend(split_sentences(q["stem"]))
            for opt in q.get("options") or []:
                out.append(opt.strip())
    return [s for s in out if s]


def cn_map(paper: dict) -> list[tuple[str, str]]:
    pairs = []
    if paper.get("title"):
        pairs.append((paper["title"], paper.get("title_cn") or ""))
    for para in paper.get("paragraphs") or []:
        for s in para.get("sentences") or []:
            chunks = s.get("chunks") or []
            cn = " ".join((c.get("cn") or "").strip() for c in chunks if (c.get("cn") or "").strip())
            pairs.append((s.get("en") or "", cn or s.get("meaning") or ""))
    for q in paper.get("questions") or []:
        pairs.append((q.get("stem") or "", q.get("stem_cn") or ""))
        for opt in q.get("options") or []:
            pairs.append((opt, ""))
    return pairs


def attach_cn(en: str, pairs: list[tuple[str, str]]) -> str:
    ne = norm(en)
    if not ne:
        return ""
    best, score = "", 0.0
    for pen, cn in pairs:
        npn = norm(pen)
        if not npn or not cn:
            continue
        if npn == ne:
            return cn
        r = difflib.SequenceMatcher(None, ne, npn).ratio()
        if r > score:
            best, score = cn, r
    return best if score >= 0.72 else ""


async def synth(text: str, out_mp3: Path, voice: str, rate: str, pairs):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    bounds = []
    with open(out_mp3, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                bounds.append((chunk.get("text", ""), round(chunk["offset"] / 1e7, 3),
                               round((chunk["offset"] + chunk["duration"]) / 1e7, 3)))
    return [{"i": i, "en": txt, "cn": attach_cn(txt, pairs), "start": st, "end": en}
            for i, (txt, st, en) in enumerate(bounds)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paper")
    ap.add_argument("--voice", default="en-US-AriaNeural")
    ap.add_argument("--rate", default="-5%")
    args = ap.parse_args()
    src = Path(args.paper)
    paper = json.loads(src.read_text(encoding="utf-8"))
    sentences = paper_sentences(paper)
    pairs = cn_map(paper)
    text = " ".join(sentences)
    out = src.with_suffix(".mp3")
    timing = asyncio.run(synth(text, out, args.voice, args.rate, pairs))
    src.with_suffix(".timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    hit = sum(1 for t in timing if t["cn"])
    print(f"wrote {out} ({out.stat().st_size} bytes), {len(timing)} lines, cn matched {hit}")


if __name__ == "__main__":
    main()
