# -*- coding: utf-8 -*-
"""给作文范文 / 翻译参考译文生成英文朗读 mp3 + 逐句时间轴。

用法: python bin/cet4_section_tts.py --kind writing|translation
产物: var/cet4-daily/audio/writing.mp3 + writing.timing.json（同理 translation）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "var" / "cet4-daily" / "demo-whole-paper.json"
OUTDIR = ROOT / "var" / "cet4-daily" / "audio"


def split_sentences(block: str) -> list[str]:
    s = re.sub(r"\s+", " ", block or "").strip()
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'\u201c])", s)
    return [p.strip() for p in parts if len(p.split()) >= 3]


def cn_map(kind: str) -> dict[str, str]:
    """从逐句解析结果里取句子 → 中文。"""
    p = ROOT / "var" / "cet4-daily" / f"sent-explain-{kind}.json"
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    out = {}
    for sents in data.values():
        for s in sents:
            out[s.get("en", "").strip()] = s.get("cn") or ""
    return out


async def synth(text: str, out_mp3: Path, voice: str, rate: str, cns: dict[str, str]):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    bounds = []
    with open(out_mp3, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                bounds.append((chunk.get("text", ""), round(chunk["offset"] / 1e7, 3),
                               round((chunk["offset"] + chunk["duration"]) / 1e7, 3)))
    lines = []
    for i, (txt, st, en) in enumerate(bounds, 1):
        cn = cns.get(txt.strip())
        if not cn:
            key = re.sub(r"[^a-z0-9]", "", txt.lower())
            for k, v in cns.items():
                if re.sub(r"[^a-z0-9]", "", k.lower()) == key:
                    cn = v
                    break
        lines.append({"i": i, "en": txt, "cn": cn or "", "start": st, "end": en})
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["writing", "translation"])
    ap.add_argument("--voice", default="en-US-AriaNeural")
    ap.add_argument("--rate", default="-5%")
    args = ap.parse_args()

    paper = json.loads(PAPER.read_text(encoding="utf-8"))
    if args.kind == "writing":
        text = paper["writing"].get("model_essay", "")
    else:
        text = paper["translation"].get("reference", "")
    sents = split_sentences(text)
    if not sents:
        print("no text")
        return 1

    OUTDIR.mkdir(parents=True, exist_ok=True)
    mp3 = OUTDIR / f"{args.kind}.mp3"
    timing = asyncio.run(synth(" ".join(sents), mp3, args.voice, args.rate, cn_map(args.kind)))
    (OUTDIR / f"{args.kind}.timing.json").write_text(
        json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    hit = sum(1 for t in timing if t["cn"])
    print(f"wrote {mp3} ({mp3.stat().st_size} bytes), {len(timing)} lines, cn {hit}/{len(timing)}, "
          f"src_sentences {len(sents)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
