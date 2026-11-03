# -*- coding: utf-8 -*-
"""edge-tts 生成整卷朗读音频 + 句级时间轴（字幕）。

用法: python bin/cet4_tts.py <paper.json> [--voice en-US-AriaNeural] [--rate -5%]
产物: 同名 .mp3 + .timing.json（[{i,text,start,end}]，秒）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

import edge_tts


def split_sentences(block: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", (block or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 3]


def sentences_of(paper: dict) -> list[str]:
    out = []
    if (paper.get("title") or "").strip():
        out.append(paper["title"].strip())
    for para in paper.get("paragraphs") or []:
        out.extend(split_sentences(para.get("en") or ""))
    if paper.get("questions"):
        out.append("Questions.")
        for q in paper["questions"]:
            out.append(f"Question {q.get('no', 0) + 45}.")
            if q.get("stem"):
                out.extend(split_sentences(q["stem"]))
            for opt in q.get("options") or []:
                out.append(opt.strip())
    return [s for s in out if s]


def ticks(t: int) -> float:
    return round(t / 10_000_000, 3)


async def synth(text: str, out_mp3: Path, voice: str, rate: str, sentences: list[str]):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    bounds = []
    with open(out_mp3, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                bounds.append((chunk.get("text", ""), ticks(chunk["offset"]), ticks(chunk["offset"] + chunk["duration"])))
    timing = []
    for i, (txt, st, en) in enumerate(bounds):
        orig = sentences[i] if i < len(sentences) else txt
        timing.append({"i": i, "text": orig or txt, "start": st, "end": en})
    return timing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paper")
    ap.add_argument("--voice", default="en-US-AriaNeural")
    ap.add_argument("--rate", default="-5%")
    args = ap.parse_args()
    src = Path(args.paper)
    paper = json.loads(src.read_text(encoding="utf-8"))
    sentences = sentences_of(paper)
    text = " ".join(sentences)
    out = src.with_suffix(".mp3")
    timing = asyncio.run(synth(text, out, args.voice, args.rate, sentences))
    src.with_suffix(".timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes) + timing {len(timing)} lines")


if __name__ == "__main__":
    main()
